"""The three retrieval stages the course asks for: sparse, dense, fusion — plus a reranker.

Each stage is small and separate so the ablation can switch one off at a time (`bm25`, `dense`,
`rrf`, `rrf+rerank`). Nothing here knows about evaluation conditions; filtering by company and year
happens in `retrieve.py`.
"""

from __future__ import annotations

import math
import threading
from collections import Counter, defaultdict
from collections.abc import Sequence

import numpy as np
from gw_common.text import tokens

RRF_K = 60          # Cormack et al.'s constant, the usual default
CANDIDATES = 50     # per retriever, before fusion
RERANK_DEPTH = 20   # how deep the cross-encoder looks
RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


class BM25:
    """Okapi BM25 over an in-memory inverted index (about 100k chunks here)."""

    def __init__(self, documents: Sequence[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs = [tokens(d) for d in documents]
        self.lengths = np.array([len(d) for d in self.docs], dtype=np.float32)
        self.avgdl = float(self.lengths.mean()) if len(self.docs) else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, doc in enumerate(self.docs):
            for term, tf in Counter(doc).items():
                self.postings[term].append((i, tf))
        self.n = len(self.docs)

    def search(self, query: str, allowed: set[int] | None = None,
               k: int = CANDIDATES) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term in set(tokens(query)):
            posting = self.postings.get(term)
            if not posting:
                continue
            idf = math.log(1 + (self.n - len(posting) + 0.5) / (len(posting) + 0.5))
            for i, tf in posting:
                if allowed is not None and i not in allowed:
                    continue
                norm = 1 - self.b + self.b * self.lengths[i] / (self.avgdl or 1.0)
                scores[i] += idf * tf * (self.k1 + 1) / (tf + self.k1 * norm)
        return sorted(scores.items(), key=lambda kv: -kv[1])[:k]


class Dense:
    """Cosine search over pre-computed, L2-normalised embeddings."""

    def __init__(self, vectors: np.ndarray) -> None:
        self.vectors = vectors.astype(np.float32, copy=False)

    def search(self, query_vector: Sequence[float], allowed: set[int] | None = None,
               k: int = CANDIDATES) -> list[tuple[int, float]]:
        q = np.asarray(query_vector, dtype=np.float32)
        norm = float(np.linalg.norm(q))
        if norm:
            q = q / norm
        scores = self.vectors @ q
        if allowed is not None:
            if not allowed:
                return []
            idx = np.fromiter(allowed, dtype=np.int64, count=len(allowed))
            top = idx[np.argsort(-scores[idx])[:k]]
        else:
            top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]


def rrf(*rankings: Sequence[tuple[int, float]], k0: int = RRF_K) -> list[tuple[int, float]]:
    """Reciprocal rank fusion: rank position matters, incomparable score scales do not."""
    fused: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, (doc_id, _score) in enumerate(ranking, start=1):
            fused[doc_id] += 1.0 / (k0 + rank)
    return sorted(fused.items(), key=lambda kv: -kv[1])


class CrossEncoderReranker:
    """ONNX cross-encoder via fastembed: no GPU, no torch, and it loads once per process.

    Thread-safe under the eval harness's retrieval pool: the ONNX runtime releases the GIL and
    `InferenceSession.run` is safe to call concurrently, so only the one-time lazy load needs a lock.
    """

    def __init__(self, model: str = RERANKER_MODEL) -> None:
        self.model_name = model
        self._model = None
        self._load_lock = threading.Lock()

    def _load(self):
        if self._model is None:
            with self._load_lock:
                if self._model is None:      # double-checked: parallel retrievals share one model
                    from fastembed.rerank.cross_encoder import TextCrossEncoder

                    self._model = TextCrossEncoder(model_name=self.model_name)
        return self._model

    def rerank(self, query: str, documents: Sequence[str]) -> list[float]:
        if not documents:
            return []
        return list(self._load().rerank(query, list(documents)))
