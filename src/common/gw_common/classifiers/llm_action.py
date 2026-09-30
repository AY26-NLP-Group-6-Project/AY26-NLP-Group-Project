"""Zero-shot LLM action classifier shared by every system (03-eval-contract.md: "same classifier").

One classifier, one prompt; systems differ only in the evidence they hand it. That keeps the RQ1
comparison about retrieval, not about who wrote the better prompt.
"""

from __future__ import annotations

import re
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gw_common.llm import REPO_ROOT, LLMClient
from gw_common.schemas import EvalItem, EvidenceCondition, EvidenceSpan, Label, Prediction

PROMPT_PATH = REPO_ROOT / "configs" / "prompts" / "action_classifier.md"
# One evidence budget for every system. Sentence retrievers (graph) use a fraction of it; passage
# retrievers (the hybrid baseline, ~290-word chunks) need the room, and cutting them to a sentence's
# length would hand the comparison to whoever picked the smaller unit.
EVIDENCE_CHARS = 800
_LABEL_RE = re.compile(r"\b(implemented|planning|indeterminate|none)\b", re.I)


def _sections(path: Path = PROMPT_PATH) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (system|user)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def parse_label(text: str) -> Label:
    """First label word in the reply; anything unparseable is `indeterminate`, the non-committal class."""
    m = _LABEL_RE.search(text or "")
    return Label(m.group(1).lower()) if m else Label.INDETERMINATE


class LLMActionClassifier:
    def __init__(self, client: LLMClient | None = None, workers: int = 8, max_evidence: int = 3) -> None:
        self.client = client or LLMClient()
        self.workers = workers
        self.max_evidence = max_evidence
        self._prompt = _sections()

    def build_messages(
        self, item: EvalItem, condition: EvidenceCondition, evidence: list[EvidenceSpan]
    ) -> list[dict[str, str]]:
        context_block = ""
        if condition is EvidenceCondition.LOCAL and (item.context_prev or item.context_next):
            context_block = (f"Context before: {item.context_prev[-400:]}\n"
                             f"Context after: {item.context_next[:400]}\n")
        evidence_block = ""
        if evidence:
            lines = [f"- ({e.company}, {e.year}, p.{e.page}) {e.text[:EVIDENCE_CHARS]}"
                     for e in evidence[: self.max_evidence]]
            evidence_block = ("Evidence from the same company's reports in other years:\n"
                              + "\n".join(lines) + "\n")
        user = self._prompt["user"].format(
            # A3CG items carry no provenance; say so rather than inventing a company or year.
            company=item.company or "(not given)", year=item.year or "year not given",
            aspect=item.aspect or "(none proposed)", text=item.text,
            context_block=context_block, evidence_block=evidence_block,
        )
        return [{"role": "system", "content": self._prompt["system"]}, {"role": "user", "content": user}]

    def classify(
        self,
        items: Sequence[EvalItem],
        *,
        condition: EvidenceCondition,
        evidence: Mapping[str, list[EvidenceSpan]] | None = None,
    ) -> list[Prediction]:
        evidence = evidence or {}

        def one(item: EvalItem) -> Prediction:
            ev = evidence.get(item.item_id, [])
            t0 = time.perf_counter()
            r = self.client.chat(self.build_messages(item, condition, ev), max_tokens=512)
            return Prediction(
                item_id=item.item_id,
                label=parse_label(r.text),
                evidence_ids=[e.statement_id for e in ev[: self.max_evidence]],
                latency_ms=r.latency_ms if not r.cached else (time.perf_counter() - t0) * 1000,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                llm_calls=0 if r.cached else 1,
            )

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(one, items))
