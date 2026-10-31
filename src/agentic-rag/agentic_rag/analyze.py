"""Where an RQ1 arm's labels move: the pre-registered slice of sentences that depend on their context.

The rule below was frozen before any full RQ1 run of the agent, so it cannot be fitted to the outcome. It is
a crude text rule with false positives and misses, and it reads only the sentence. The hypothesis, from the
proposal: evidence should help sentences with an unresolved reference or a third-party actor, and leave the
rest alone. `uv run python -m agentic_rag.analyze <run_dir> --base sentence_only --conditions a,b`.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from gw_common import datasets
from gw_common.eval import metrics as M
from gw_common.llm import REPO_ROOT
from gw_common.schemas import Label

_NOUNS = (
    r"target|targets|goal|goals|initiative|initiatives|measure|measures|programme|programmes|program|programs|"
    r"effort|efforts|policy|policies|plan|plans|commitment|commitments|project|projects|system|systems|"
    r"framework|practice|practices|approach|strategy|strategies|action|actions|step|steps|activity|activities"
)
REFERENCE = re.compile(
    rf"\b(this|these|those|such|the above|aforementioned|said)\s+({_NOUNS})\b"
    r"|^(it|they|these|such|as such|therefore)\b|^this\b(?!\s+(year|report|section|page|chapter))",
    re.I,
)
ACTOR = re.compile(
    r"\b(tenants?|suppliers?|vendors?|contractors?|regulators?|government|authorit(y|ies)|parent|"
    r"holding company|industry players?|customers?|subsidiar(y|ies)|joint venture)\b",
    re.I,
)


def depends_on_context(text: str) -> bool:
    return bool(REFERENCE.search(text) or ACTOR.search(text))


def votes(run_dir: Path) -> dict[str, dict[str, Label]]:
    per: dict[str, dict[str, list[Label]]] = defaultdict(lambda: defaultdict(list))
    for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            p = json.loads(line)
            per[p["condition"]][p["item_id"]].append(Label(p["label"]))
    return {c: {i: Counter(v).most_common(1)[0][0] for i, v in items.items()} for c, items in per.items()}


def table(run_dir: Path, base: str, conditions: list[str]) -> str:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    items, _ = datasets.load(manifest["dataset_id"], manifest["label_source"])
    by_id = {it.item_id: it for it in items}
    v = votes(run_dir)
    ids = sorted(v[base], key=lambda i: int(i) if i.isdigit() else i)
    rows = ["| condition | slice | n | base macro-F1 | arm macro-F1 | flips right / wrong | p (McNemar) |",
            "|---|---|---|---|---|---|---|"]
    for cond in conditions:
        for name, keep in (("depends on context", True), ("reads alone", False)):
            chosen = [i for i in ids if depends_on_context(by_id[i].text) is keep]
            gold = [by_id[i].gold_label for i in chosen]
            a, b = [v[base][i] for i in chosen], [v[cond][i] for i in chosen]
            flips = M.flip_analysis(gold, a, b)
            rows.append(
                f"| {cond} | {name} | {len(chosen)} | {M.action_metrics(gold, a)['macro_f1']:.4f} "
                f"| {M.action_metrics(gold, b)['macro_f1']:.4f} "
                f"| +{flips['wrong_to_right']} / -{flips['right_to_wrong']} "
                f"| {M.mcnemar(gold, a, b)['p_value']:.3f} |"
            )
    return "\n".join(rows)


def routed(run_dir: Path, base: str, arm: str, *, gate_of=None) -> dict:
    """An arm that reads `arm` where the rule (or `gate_of`, item -> bool) says so and `base` elsewhere,
    composed from the run's own labels. Where it stays on `base` the input is exactly the base's, so no new
    call is needed and the only differences are the routed items."""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    items, _ = datasets.load(manifest["dataset_id"], manifest["label_source"])
    by_id = {it.item_id: it for it in items}
    v = votes(run_dir)
    ids = sorted(v[base], key=lambda i: int(i) if i.isdigit() else i)
    gold = [by_id[i].gold_label for i in ids]
    chose = gate_of or (lambda it: depends_on_context(it.text))
    a = [v[base][i] for i in ids]
    b = [v[arm][i] if chose(by_id[i]) else v[base][i] for i in ids]
    flips = M.flip_analysis(gold, a, b)
    return {"routed": sum(chose(by_id[i]) for i in ids), "n": len(ids),
            "base_macro_f1": M.action_metrics(gold, a)["macro_f1"],
            "routed_macro_f1": M.action_metrics(gold, b)["macro_f1"],
            "flips_right": flips["wrong_to_right"], "flips_wrong": flips["right_to_wrong"],
            "p": M.mcnemar(gold, a, b)["p_value"]}


def gate_opened(run_dir: Path, condition: str = "company_agentic"):
    """item -> did the agent's gate find a gap, from the run's trace file."""
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    trace_file = REPO_ROOT / "artifacts" / "agentic" / manifest["config"]["retriever"]["trace_file"]
    opened = {}
    for line in trace_file.read_text(encoding="utf-8").splitlines():
        t = json.loads(line)
        if t["condition"] == condition:
            opened[t["target"]] = bool(t["steps"] and t["steps"][0].get("gaps"))
    return lambda it: opened.get(it.text, False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--base", default="sentence_only")
    ap.add_argument("--conditions", required=True)
    args = ap.parse_args()
    conditions = [c.strip() for c in args.conditions.split(",")]
    print(table(args.run_dir, args.base, conditions))
    if "local" in conditions:
        print("\nrule -> local, else base:", json.dumps(routed(args.run_dir, args.base, "local")))
    if "company_agentic" in conditions:
        gate = gate_opened(args.run_dir)
        agent = routed(args.run_dir, args.base, "company_agentic", gate_of=gate)
        print("gate -> agent, else base:", json.dumps(agent))
        if "local" in conditions:
            local = routed(args.run_dir, args.base, "local", gate_of=gate)
            print("gate -> local, else base:", json.dumps(local))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
