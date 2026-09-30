"""Speed, cost and grounding of a run: the operational half of the evaluation.

The course brief asks for latency, records per second, cost and scalability next to quality. These are
computed from what the harness already observes (per-call latency and tokens, wall-clock time, retrieval
time), so every system gets them for free and on the same terms.

Two caveats the numbers carry with them:

- **Cached calls are not speed.** A cache hit returns in microseconds and bills nothing. `cached_calls`
  is reported; speed and cost figures are meaningful when it is 0 (any run with `--repeats > 1`).
- **Cost needs prices.** Tokens are always reported. Dollars are reported only when
  `LLM_PRICE_IN_PER_MTOK` / `LLM_PRICE_OUT_PER_MTOK` (and optionally `EMB_PRICE_PER_MTOK`) are set,
  because prices change and depend on the gateway; the prices used are written into the manifest.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from gw_common.eval import metrics as M
from gw_common.schemas import EvidenceSpan, Prediction


def speed_and_cost(
    preds: Sequence[Prediction],
    wall_s: float,
    retrieval_ms: Mapping[str, float] | None = None,
    settings=None,
    embed_tokens: int = 0,
) -> dict:
    """Operational metrics of one repeat of one condition."""
    n = len(preds)
    retrieval_ms = retrieval_ms or {}
    latencies = [p.latency_ms for p in preds]
    end_to_end = [p.latency_ms + retrieval_ms.get(p.item_id, 0.0) for p in preds]
    tokens_in = sum(p.input_tokens for p in preds)
    tokens_out = sum(p.output_tokens for p in preds)
    calls = sum(p.llm_calls for p in preds)
    cost = settings.cost_usd(tokens_in, tokens_out, embed_tokens) if settings is not None else None
    return {
        **M.latency_summary(latencies),                       # one classification call
        "end_to_end": M.latency_summary(end_to_end),          # retrieval + classification, per item
        "classify_wall_s": wall_s,
        "items_per_s": n / wall_s if wall_s > 0 else None,    # throughput at the classifier's concurrency
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "input_tokens_per_item": tokens_in / n if n else 0.0,
        "output_tokens_per_item": tokens_out / n if n else 0.0,
        "embed_tokens": embed_tokens,
        "llm_calls": calls,
        "cached_calls": n - calls,
        "graph_hops": sum(p.graph_hops for p in preds),
        "cost_usd": cost,
        "cost_per_1k_items_usd": cost / n * 1000 if cost is not None and n else None,
    }


def retrieval_speed(retrieval_ms: Mapping[str, float]) -> dict:
    values = list(retrieval_ms.values())
    if not values:
        return {}
    total_s = sum(values) / 1000
    return {**M.latency_summary(values), "total_s": total_s,
            "queries_per_s": len(values) / total_s if total_s > 0 else None}


def grounding(
    preds: Sequence[Prediction], evidence: Mapping[str, list[EvidenceSpan]] | None = None
) -> dict:
    """How the classifier used its sources: did it answer in the asked form, cite, and cite validly.

    `evidence_use_rate` is the share of items that *had* retrieved evidence and cited at least one of
    it: a retriever can return spans the classifier never relies on, and this tells the two apart.
    """
    evidence = evidence or {}
    n = len(preds)
    if n == 0:
        return {}
    with_rationale = [p for p in preds if p.rationale]
    had_evidence = [p for p in preds if evidence.get(p.item_id)]
    used = [p for p in had_evidence if any(c.ref.startswith("E") for c in p.citations)]
    cited_evidence = sum(sum(c.ref.startswith("E") for c in p.citations) for p in preds)
    shown = sum(len(evidence.get(p.item_id, [])) for p in preds)
    return {
        "parse_ok_rate": sum(p.parse_ok for p in preds) / n,
        "rationale_rate": len(with_rationale) / n,
        "mean_rationale_words": (
            sum(len(p.rationale.split()) for p in with_rationale) / len(with_rationale)
            if with_rationale else 0.0
        ),
        "cites_target_rate": sum(any(c.ref == "T" for c in p.citations) for p in preds) / n,
        "mean_citations": sum(len(p.citations) for p in preds) / n,
        "items_with_evidence": len(had_evidence),
        "evidence_use_rate": len(used) / len(had_evidence) if had_evidence else None,
        "evidence_spans_cited_share": cited_evidence / shown if shown else None,
        "invalid_citations": sum(p.invalid_citations for p in preds),
    }


def mean_of(reps: Sequence[dict], *path: str) -> float | None:
    """Mean over repeats of a nested numeric field, skipping repeats where it is missing."""
    values = []
    for rep in reps:
        node = rep
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, (int, float)):
            values.append(float(node))
    return sum(values) / len(values) if values else None
