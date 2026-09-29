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
- **Explicit models.** No chat model is hard-coded; the `.env` names it and every result echoes it.
- **Honest temperature.** Some models reject a non-default temperature. The client then retries
  without it and records `temperature_applied=False` instead of pretending the setting took effect.

Environment (see `.env.example`). Chat and embeddings are configured separately, because they may use
different gateways or keys; each falls back to the generic OpenAI variables.

    LLM_API_KEY / LLM_BASE_URL / LLM_MODEL      chat        (fallback OPENAI_API_KEY, OPENAI_BASE_URL)
    EMB_API_KEY / EMB_BASE_URL / EMB_MODEL      embeddings  (fallback LLM_*, then OPENAI_*)
    GW_LLM_TEMPERATURE    default 0
    GW_LLM_CACHE          1 (default) to cache, 0 to bypass
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
CACHE_PATH = REPO_ROOT / "artifacts" / "cache" / "llm.sqlite"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
# Reasoning models bill and think per effort level; the project fixes it so runs stay comparable.
DEFAULT_EFFORT = "low"


def load_env() -> None:
    """Load `.env` from the repo root; never overrides variables already set in the environment."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependency is declared, this is only defensive
        return
    load_dotenv(REPO_ROOT / ".env", override=False)


def _first(*names: str) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None


def embeddings_configured() -> bool:
    load_env()
    return bool(_first("EMB_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"))


@dataclass(slots=True)
class LLMSettings:
    chat_api_key: str | None = None
    chat_base_url: str | None = None
    chat_model: str | None = None
    embed_api_key: str | None = None
    embed_base_url: str | None = None
    embed_model: str = DEFAULT_EMBED_MODEL
    temperature: float = 0.0
    reasoning_effort: str | None = DEFAULT_EFFORT
    use_cache: bool = True
    timeout_s: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> LLMSettings:
        load_env()
        chat_key = _first("LLM_API_KEY", "OPENAI_API_KEY")
        chat_url = _first("LLM_BASE_URL", "OPENAI_BASE_URL")
        return cls(
            chat_api_key=chat_key,
            chat_base_url=chat_url,
            chat_model=_first("LLM_MODEL", "GW_CHAT_MODEL"),
            embed_api_key=_first("EMB_API_KEY") or chat_key,
            embed_base_url=_first("EMB_BASE_URL") or chat_url,
            embed_model=_first("EMB_MODEL", "GW_EMBED_MODEL") or DEFAULT_EMBED_MODEL,
            temperature=float(os.getenv("GW_LLM_TEMPERATURE", "0")),
            reasoning_effort=_first("LLM_REASONING_EFFORT", "GW_LLM_EFFORT") or DEFAULT_EFFORT,
            use_cache=os.getenv("GW_LLM_CACHE", "1") != "0",
        )

    def describe(self) -> dict[str, Any]:
        """What goes into run manifests. Never includes a key."""
        return {"chat_model": self.chat_model, "chat_base_url": self.chat_base_url,
                "embed_model": self.embed_model, "embed_base_url": self.embed_base_url,
                "temperature": self.temperature, "reasoning_effort": self.reasoning_effort,
                "cache": self.use_cache}


@dataclass(slots=True)
class ChatResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    temperature_applied: bool = True
    effort_applied: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


class _Cache:
    """SQLite response cache, safe to share across the worker threads of a batched run."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, kind TEXT, body TEXT)")

    def get(self, key: str) -> dict | None:
        with self._lock:
            row = self.con.execute("SELECT body FROM responses WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, kind: str, body: dict) -> None:
        with self._lock:
            self.con.execute("INSERT OR REPLACE INTO responses VALUES (?, ?, ?)",
                             (key, kind, json.dumps(body)))
            self.con.commit()


def _request_key(kind: str, payload: dict) -> str:
    blob = json.dumps({"kind": kind, **payload}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class LLMClient:
    def __init__(
        self,
        settings: LLMSettings | None = None,
        cache_path: Path = CACHE_PATH,
        client=None,
        embed_client=None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self._cache = _Cache(cache_path) if self.settings.use_cache else None
        self._chat_client = client            # injectable for tests
        self._embed_client = embed_client or client
        self.usage = {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0}
        self._usage_lock = threading.Lock()

    # ----------------------------------------------------------------- transport
    def _make(self, api_key: str | None, base_url: str | None, what: str):
        if not api_key:
            var = "LLM_API_KEY" if what == "chat" else "EMB_API_KEY"
            raise RuntimeError(f"no API key for {what}: set {var} (or OPENAI_API_KEY) in .env")
        from openai import OpenAI

        return OpenAI(api_key=api_key, base_url=base_url, timeout=self.settings.timeout_s,
                      max_retries=self.settings.max_retries)

    def _chat_transport(self):
        if self._chat_client is None:
            self._chat_client = self._make(self.settings.chat_api_key, self.settings.chat_base_url, "chat")
        return self._chat_client

    def _embed_transport(self):
        if self._embed_client is None:
            self._embed_client = self._make(self.settings.embed_api_key, self.settings.embed_base_url,
                                            "embeddings")
        return self._embed_client

    # ----------------------------------------------------------------- chat
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
        reasoning_effort: str | None = None,
    ) -> ChatResult:
        model = model or self.settings.chat_model
        if not model:
            raise RuntimeError("no chat model configured: set LLM_MODEL in .env")
        temp = self.settings.temperature if temperature is None else temperature
        effort = self.settings.reasoning_effort if reasoning_effort is None else reasoning_effort
        payload = {"model": model, "messages": messages, "temperature": temp,
                   "max_completion_tokens": max_tokens, "response_format": response_format,
                   "reasoning_effort": effort}
        key = _request_key("chat", payload)
        if self._cache and (hit := self._cache.get(key)):
            with self._usage_lock:
                self.usage["cache_hits"] += 1
            return ChatResult(**{**hit, "cached": True, "latency_ms": 0.0})

        kwargs = {k: v for k, v in payload.items() if v is not None}
        t0 = time.perf_counter()
        # Models differ in which knobs they accept. Drop the rejected one and record that it did not
        # apply, rather than reporting a setting the model never honoured.
        applied = {"temperature": True, "reasoning_effort": effort is not None}
        for _ in range(len(applied) + 1):
            try:
                resp = self._chat_transport().chat.completions.create(**kwargs)
                break
            except Exception as exc:  # noqa: BLE001 - only unsupported-parameter errors are retried
                rejected = next((p for p in applied if p in kwargs and p in str(exc).lower()), None)
                if rejected is None:
                    raise
                kwargs.pop(rejected)
                applied[rejected] = False
        temperature_applied, effort_applied = applied["temperature"], applied["reasoning_effort"]
        latency = (time.perf_counter() - t0) * 1000
        usage = getattr(resp, "usage", None)
        result = ChatResult(
            text=resp.choices[0].message.content or "",
            model=getattr(resp, "model", model),
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency,
            temperature_applied=temperature_applied,
            effort_applied=effort_applied,
        )
        with self._usage_lock:
            self.usage["calls"] += 1
            self.usage["input_tokens"] += result.input_tokens
            self.usage["output_tokens"] += result.output_tokens
        if self._cache:
            self._cache.put(key, "chat", {"text": result.text, "model": result.model,
                                          "input_tokens": result.input_tokens,
                                          "output_tokens": result.output_tokens,
                                          "temperature_applied": temperature_applied,
                                          "effort_applied": effort_applied})
        return result

    # ----------------------------------------------------------------- embeddings
    def embed(self, texts: list[str], *, model: str | None = None, batch_size: int = 512) -> np.ndarray:
        """L2-normalised embeddings, one row per text, cached per (model, text)."""
        model = model or self.settings.embed_model
        out: list[np.ndarray | None] = [None] * len(texts)
        todo: list[int] = []
        for i, t in enumerate(texts):
            key = _request_key("embed", {"model": model, "input": t})
            hit = self._cache.get(key) if self._cache else None
            if hit:
                out[i] = np.asarray(hit["vector"], dtype=np.float32)
                self.usage["cache_hits"] += 1
            else:
                todo.append(i)
        for start in range(0, len(todo), batch_size):
            batch = todo[start:start + batch_size]
            resp = self._embed_transport().embeddings.create(model=model, input=[texts[i] for i in batch])
            self.usage["calls"] += 1
            self.usage["input_tokens"] += getattr(getattr(resp, "usage", None), "prompt_tokens", 0) or 0
            for i, item in zip(batch, resp.data, strict=True):
                vec = np.asarray(item.embedding, dtype=np.float32)
                out[i] = vec
                if self._cache:
                    self._cache.put(_request_key("embed", {"model": model, "input": texts[i]}), "embed",
                                    {"vector": vec.tolist()})
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        mat = np.vstack(out)
        return mat / np.linalg.norm(mat, axis=1, keepdims=True).clip(min=1e-12)
