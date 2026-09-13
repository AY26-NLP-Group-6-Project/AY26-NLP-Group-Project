"""Phrase embeddings for canonicalisation, with two interchangeable backends.

- `openai`    — `text-embedding-3-small` (or `GW_EMBED_MODEL`) through the shared `gw_common.llm`
               client; responses are cached in `artifacts/cache/llm.sqlite`, so re-runs are offline.
- `fastembed` — `BAAI/bge-small-en-v1.5` locally through ONNX runtime (no torch, ~130 MB). Used when
               no API key is configured, and used to build the annotation pools so the gold is not
               shaped by the embedding model that the clustering is evaluated with.

Select with `GW_EMBED_BACKEND=openai|fastembed` (default: `openai` if `OPENAI_API_KEY` is set,
otherwise `fastembed`). The backend and model name are written into every canonical build.
"""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np

from graph_rag.config import REPO_ROOT

FASTEMBED_MODEL = "BAAI/bge-small-en-v1.5"
CACHE_DIR = REPO_ROOT / "artifacts" / "cache" / "embeddings"


def default_backend() -> str:
    from gw_common.llm import load_env

    load_env()
    explicit = os.getenv("GW_EMBED_BACKEND")
    if explicit:
        return explicit
    return "openai" if os.getenv("OPENAI_API_KEY") else "fastembed"


class PhraseEmbedder:
    def __init__(self, backend: str | None = None, model: str | None = None, batch_size: int = 128) -> None:
        self.backend = backend or default_backend()
        if self.backend not in ("openai", "fastembed"):
            raise ValueError(f"unknown embedding backend {self.backend!r}")
        self.batch_size = batch_size
        self._client = None
        self._model = None
        if self.backend == "openai":
            from gw_common.llm import LLMClient

            self._client = LLMClient()
            self.model_name = model or self._client.settings.embed_model
        else:
            self.model_name = model or FASTEMBED_MODEL
            slug = self.model_name.replace("/", "__")
            self.cache_path = CACHE_DIR / f"{slug}.npz"
            self.index_path = CACHE_DIR / f"{slug}.json"
            self._keys: list[str] = []
            self._vecs = np.zeros((0, 0), dtype=np.float32)
            if self.cache_path.exists() and self.index_path.exists():
                self._keys = json.loads(self.index_path.read_text(encoding="utf-8"))
                self._vecs = np.load(self.cache_path)["vecs"]
            self._pos = {k: i for i, k in enumerate(self._keys)}

    @property
    def label(self) -> str:
        return f"{self.backend}:{self.model_name}"

    # ----------------------------------------------------------------- public
    def embed(self, texts: list[str]) -> np.ndarray:
        """L2-normalised vectors, one row per text."""
        if self.backend == "openai":
            return self._client.embed(texts, model=self.model_name)
        return self._embed_local(texts)

    # ----------------------------------------------------------------- fastembed
    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def _embed_local(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if self._key(t) not in self._pos]
        if missing:
            if self._model is None:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self.model_name)
            new = np.asarray(list(self._model.embed(missing, batch_size=self.batch_size)), dtype=np.float32)
            new /= np.linalg.norm(new, axis=1, keepdims=True).clip(min=1e-12)
            start = len(self._keys)
            self._keys.extend(self._key(t) for t in missing)
            self._vecs = new if self._vecs.size == 0 else np.vstack([self._vecs, new])
            self._pos.update({self._key(t): start + i for i, t in enumerate(missing)})
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(self.cache_path, vecs=self._vecs)
            self.index_path.write_text(json.dumps(self._keys), encoding="utf-8")
        return self._vecs[[self._pos[self._key(t)] for t in texts]]
