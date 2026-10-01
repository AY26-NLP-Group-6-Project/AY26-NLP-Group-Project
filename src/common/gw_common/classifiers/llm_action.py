"""Zero-shot LLM action classifier shared by every system (03-eval-contract.md: "same classifier").

One classifier, one prompt; systems differ only in the evidence they hand it. That keeps the RQ1
comparison about retrieval, not about who wrote the better prompt.

Two output styles, same label definitions:

- `cited` (default): a label, a short rationale and the sources it rests on. Sources are tagged in the
  prompt (`[T]` target sentence, `[C]` neighbouring context, `[E1]`… retrieved evidence); the tags the
  model cites are resolved back to company, year, page and file, so an answer can be checked against
  the page it came from. This is what the UI shows and what faithfulness metrics read.
- `label`: the v1 prompt, one word. Kept so earlier runs can be reproduced and so "does asking for a
  rationale change the label?" can be measured instead of assumed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gw_common.llm import REPO_ROOT, LLMClient
from gw_common.schemas import Citation, EvalItem, EvidenceCondition, EvidenceSpan, Label, Prediction

PROMPTS = {
    "label": REPO_ROOT / "configs" / "prompts" / "action_classifier.md",
    "cited": REPO_ROOT / "configs" / "prompts" / "action_classifier_cited.md",
}
DEFAULT_STYLE = "cited"
# One evidence budget for every system. Sentence retrievers (graph) use a fraction of it; passage
# retrievers (the hybrid baseline, ~200-word chunks) need the room, and cutting them to a sentence's
# length would hand the comparison to whoever picked the smaller unit.
EVIDENCE_CHARS = 800
CONTEXT_CHARS = 400
QUOTE_CHARS = 300
_LABEL_RE = re.compile(r"\b(implemented|planning|indeterminate|none)\b", re.I)
_JSON_RE = re.compile(r"\{.*\}", re.S)
_REF_RE = re.compile(r"^\[?\s*([TC]|E\d+)\s*\]?$", re.I)


def _sections(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (system|user)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def parse_label(text: str) -> Label:
    """First label word in the reply; anything unparseable is `indeterminate`, the non-committal class."""
    m = _LABEL_RE.search(text or "")
    return Label(m.group(1).lower()) if m else Label.INDETERMINATE


def parse_cited(text: str) -> tuple[Label, str, list[str], bool]:
    """(label, rationale, cited tags, parsed). A reply that is not the asked JSON still yields a label
    if one can be read from it, with `parsed=False` so the run can count how often that happened."""
    match = _JSON_RE.search(text or "")
    if match:
        try:
            obj = json.loads(match.group(0))
            label = Label(str(obj["label"]).strip().lower())
            refs = obj.get("evidence") or []
            refs = [str(r) for r in (refs if isinstance(refs, list) else [refs])]
            return label, str(obj.get("rationale") or "").strip(), refs, True
        except (ValueError, KeyError, TypeError):
            pass
    return parse_label(text), "", [], False


def resolve_citations(
    refs: Sequence[str], item: EvalItem, evidence: Sequence[EvidenceSpan], has_context: bool
) -> tuple[list[Citation], int]:
    """Turn cited tags into sources a reader can open. Unknown or unavailable tags are counted, not kept."""
    out, invalid, seen = [], 0, set()
    for raw in refs:
        m = _REF_RE.match(raw.strip())
        tag = m.group(1).upper() if m else None
        if tag is None or tag in seen:
            invalid += tag is None
            continue
        if tag == "T":
            out.append(Citation(ref="T", company=item.company, year=item.year, page=item.page,
                                file=item.file, quote=item.text[:QUOTE_CHARS]))
        elif tag == "C" and has_context:
            quote = f"{item.context_prev[-CONTEXT_CHARS:]} … {item.context_next[:CONTEXT_CHARS]}".strip(" …")
            out.append(Citation(ref="C", company=item.company, year=item.year, page=item.page,
                                file=item.file, quote=quote[:QUOTE_CHARS]))
        elif tag.startswith("E") and 1 <= int(tag[1:]) <= len(evidence):
            e = evidence[int(tag[1:]) - 1]
            out.append(Citation(ref=tag, statement_id=e.statement_id, company=e.company, year=e.year,
                                page=e.page, file=e.file, quote=e.text[:QUOTE_CHARS]))
        else:
            invalid += 1
            continue
        seen.add(tag)
    return out, invalid


class LLMActionClassifier:
    def __init__(self, client: LLMClient | None = None, workers: int = 8, max_evidence: int = 3,
                 style: str | None = None) -> None:
        self.client = client or LLMClient()
        self.workers = workers
        self.max_evidence = max_evidence
        self.style = style or os.getenv("GW_CLASSIFIER_STYLE", DEFAULT_STYLE)
        if self.style not in PROMPTS:
            raise ValueError(f"classifier style must be one of {sorted(PROMPTS)}")
        self._prompt = _sections(PROMPTS[self.style])

    def describe(self) -> dict[str, object]:
        """What a run manifest records about the classifier: the style and the exact prompt used."""
        path = PROMPTS[self.style]
        return {"style": self.style, "prompt": path.name,
                "prompt_sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:12],
                "workers": self.workers, "max_evidence": self.max_evidence,
                "evidence_chars": EVIDENCE_CHARS}

    def build_messages(
        self, item: EvalItem, condition: EvidenceCondition, evidence: list[EvidenceSpan]
    ) -> list[dict[str, str]]:
        cited = self.style == "cited"
        context_block = ""
        if condition is EvidenceCondition.LOCAL and (item.context_prev or item.context_next):
            tag = "[C] " if cited else ""
            context_block = (f"{tag}Context before: {item.context_prev[-CONTEXT_CHARS:]}\n"
                             f"{tag}Context after: {item.context_next[:CONTEXT_CHARS]}\n")
        evidence_block = ""
        if evidence:
            lines = [
                (f"[E{i}] " if cited else "- ")
                + f"({e.company}, {e.year}, p.{e.page}) {e.text[:EVIDENCE_CHARS]}"
                for i, e in enumerate(evidence[: self.max_evidence], 1)
            ]
            evidence_block = ("Evidence retrieved from the same company's reports:\n" if cited else
                              "Evidence from the same company's reports in other years:\n")
            evidence_block += "\n".join(lines) + "\n"
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
            ev = list(evidence.get(item.item_id, []))[: self.max_evidence]
            t0 = time.perf_counter()
            r = self.client.chat(self.build_messages(item, condition, ev), max_tokens=512)
            if self.style == "cited":
                label, rationale, refs, parsed = parse_cited(r.text)
                has_context = condition is EvidenceCondition.LOCAL and bool(
                    item.context_prev or item.context_next)
                citations, invalid = resolve_citations(refs, item, ev, has_context)
            else:
                label, rationale, citations, invalid, parsed = parse_label(r.text), "", [], 0, True
            return Prediction(
                item_id=item.item_id,
                label=label,
                evidence_ids=[e.statement_id for e in ev],
                rationale=rationale,
                citations=citations,
                invalid_citations=invalid,
                parse_ok=parsed,
                latency_ms=r.latency_ms if not r.cached else (time.perf_counter() - t0) * 1000,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                llm_calls=0 if r.cached else 1,
            )

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(one, items))
