"""One LLM / embedding client for every system, configured from `.env`.

Why it lives in gw_common: the classifier, the agentic arm and canonicalisation all call models, and
03-eval-contract.md requires token counts, latency and reproducible re-runs for every arm. Putting the
calls behind one client is what makes those numbers comparable.

Guarantees:

- **Offline re-runs.** Every request is keyed by a hash of its full payload (model, messages or
  inputs, temperature, response format) and the response is cached in `artifacts/cache/llm.sqlite`.
  A re-run of an evaluation reads the cache and makes no network call (02-repo-and-tooling.md §3).
- **Accounting.** Each call returns input/output tokens, latency and whether it was a cache hit, so
  `Prediction.input_tokens` etc. are measured, not estimated.
- **Explicit models.** No model name is hard-coded as a silent default for chat; the `.env` must say
  which model runs, and the name is echoed into every result.

Environment (see `.env.example`):

    OPENAI_API_KEY        required for the openai provider
    OPENAI_BASE_URL       optional, for a compatible gateway
    GW_CHAT_MODEL         chat model id, required before any chat call
    GW_EMBED_MODEL        embedding model id (default text-embedding-3-small)
    GW_LLM_TEMPERATURE    default 0
    GW_LLM_CACHE          1 (default) to cache, 0 to bypass
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
CACHE_PATH = REPO_ROOT / "artifacts" / "cache" / "llm.sqlite"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"


def load_env() -> None:
    """Load `.env` from the repo root if python-dotenv is available; never overrides real env vars."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependency is declared, this is only defensive
        return
    load_dotenv(REPO_ROOT / ".env", override=False)


@dataclass(slots=True)
class LLMSettings:
    api_key: str | None = None
    base_url: str | None = None
    chat_model: str | None = None
    embed_model: str = DEFAULT_EMBED_MODEL
    temperature: float = 0.0
    use_cache: bool = True
    timeout_s: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> LLMSettings:
        load_env()
        return cls(
            api_key=os.getenv("OPENAI_API_KEY") or None,
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            chat_model=os.getenv("GW_CHAT_MODEL") or None,
            embed_model=os.getenv("GW_EMBED_MODEL") or DEFAULT_EMBED_MODEL,
            temperature=float(os.getenv("GW_LLM_TEMPERATURE", "0")),
            use_cache=os.getenv("GW_LLM_CACHE", "1") != "0",
        )

    def describe(self) -> dict[str, Any]:
        """What goes into run manifests. Never includes the key."""
        return {"chat_model": self.chat_model, "embed_model": self.embed_model,
                "temperature": self.temperature, "base_url": self.base_url or "api.openai.com",
                "cache": self.use_cache}


@dataclass(slots=True)
class ChatResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


class _Cache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path)
        self.con.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, kind TEXT, body TEXT)")

    def get(self, key: str) -> dict | None:
        row = self.con.execute("SELECT body FROM responses WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, kind: str, body: dict) -> None:
        self.con.execute("INSERT OR REPLACE INTO responses VALUES (?, ?, ?)", (key, kind, json.dumps(body)))
        self.con.commit()


def _request_key(kind: str, payload: dict) -> str:
    blob = json.dumps({"kind": kind, **payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class LLMClient:
    def __init__(
        self, settings: LLMSettings | None = None, cache_path: Path = CACHE_PATH, client=None
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self._cache = _Cache(cache_path) if self.settings.use_cache else None
        self._client = client  # injectable for tests
        self.usage = {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0}

    # ----------------------------------------------------------------- transport
    def _openai(self):
        if self._client is None:
            if not self.settings.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set (add it to .env)")
            from openai import OpenAI

            self._client = OpenAI(api_key=self.settings.api_key, base_url=self.settings.base_url,
                                  timeout=self.settings.timeout_s, max_retries=self.settings.max_retries)
        return self._client

    # ----------------------------------------------------------------- chat
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> ChatResult:
        model = model or self.settings.chat_model
        if not model:
            raise RuntimeError("no chat model configured: set GW_CHAT_MODEL in .env")
        payload = {"model": model, "messages": messages,
                   "temperature": self.settings.temperature if temperature is None else temperature,
                   "max_tokens": max_tokens, "response_format": response_format}
        key = _request_key("chat", payload)
        if self._cache and (hit := self._cache.get(key)):
            self.usage["cache_hits"] += 1
            return ChatResult(**{**hit, "cached": True, "latency_ms": 0.0})

        t0 = time.perf_counter()
        kwargs = {k: v for k, v in payload.items() if v is not None}
        resp = self._openai().chat.completions.create(**kwargs)
        latency = (time.perf_counter() - t0) * 1000
        usage = getattr(resp, "usage", None)
        result = ChatResult(
            text=resp.choices[0].message.content or "",
            model=getattr(resp, "model", model),
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency,
        )
        self.usage["calls"] += 1
        self.usage["input_tokens"] += result.input_tokens
        self.usage["output_tokens"] += result.output_tokens
        if self._cache:
            self._cache.put(key, "chat", {"text": result.text, "model": result.model,
                                          "input_tokens": result.input_tokens,
                                          "output_tokens": result.output_tokens})
        return result

    # ----------------------------------------------------------------- embeddings
    def embed(self, texts: list[str], *, model: str | None = None, batch_size: int = 512) -> np.ndarray:
        """L2-normalised embeddings, one row per text, cached per (model, text)."""
        model = model or self.settings.embed_model
        out: list[np.ndarray | None] = [None] * len(texts)
        todo: list[int] = []
        for i, t in enumerate(texts):
            key = _request_key("embed", {"model": model, "input": t})
            if self._cache and (hit := self._cache.get(key)):
                out[i] = np.asarray(hit["vector"], dtype=np.float32)
                self.usage["cache_hits"] += 1
            else:
                todo.append(i)
        for start in range(0, len(todo), batch_size):
            batch = todo[start:start + batch_size]
            resp = self._openai().embeddings.create(model=model, input=[texts[i] for i in batch])
            self.usage["calls"] += 1
            self.usage["input_tokens"] += getattr(getattr(resp, "usage", None), "prompt_tokens", 0) or 0
            for i, item in zip(batch, resp.data, strict=True):
                vec = np.asarray(item.embedding, dtype=np.float32)
                out[i] = vec
                if self._cache:
                    self._cache.put(_request_key("embed", {"model": model, "input": texts[i]}), "embed",
                                    {"vector": vec.tolist()})
        mat = np.vstack(out) if texts else np.zeros((0, 0), dtype=np.float32)
        return mat / np.linalg.norm(mat, axis=1, keepdims=True).clip(min=1e-12)
