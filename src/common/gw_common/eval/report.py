"""Markdown rendering of a run. Accuracy and cost always appear in the same table."""

from __future__ import annotations

from pathlib import Path

from gw_common.schemas import RunManifest


def _fmt(v, spec: str = ".4f") -> str:
    return "n/a" if v is None else format(v, spec)


def write_report(run_dir: Path, manifest: RunManifest, results: dict[str, dict]) -> Path:
    lines = [f"# {manifest.run_id}", ""]
    if manifest.label_source == "llm_pre":
        lines += [
            "> **Development numbers only.** Gold labels are `llm_pre` (pre-filled by an LLM, not human",
            "> majority). Nothing here may be quoted in the report; re-run with `--labels human_majority`",
            "> once the pilot is adjudicated.",
            "",
        ]
    lines += [
        f"- system: `{manifest.system}` · task: `{manifest.task}`",
        f"- dataset: `{manifest.dataset_id}` @ `{manifest.dataset_hash}` · n = {manifest.n_items}"
        f" · labels: `{manifest.label_source}`",
        f"- git: `{manifest.git_sha[:8]}`{' (dirty)' if manifest.git_dirty else ''}"
        + (f" · wall: {manifest.wall_seconds:.1f}s" if manifest.wall_seconds else ""),
        "",
        "| condition | macro-F1 (actions) | acc | pairdet F1 | Δ vs sentence_only | net flips |"
        " p (McNemar) | p50 ms | p95 ms | LLM calls |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cond, block in results.items():
        if block.get("status") != "ok":
            lines.append(f"| {cond} | n/a | | | | | | | | |")
            continue
        a, pd_, ops = block["action"], block["pairdet"], block["ops"]
        vs = block.get("vs_sentence_only", {})
        lines.append(
            f"| {cond} | {_fmt(a['macro_f1'])} | {_fmt(a['accuracy'])} | {_fmt(pd_['f1'])} "
            f"| {_fmt(vs.get('delta_macro_f1'), '+.4f') if vs else '—'} "
            f"| {vs.get('flips', {}).get('net', '—')} "
            f"| {_fmt(vs.get('mcnemar', {}).get('p_value'), '.3f') if vs else '—'} "
            f"| {ops['p50_ms']:.1f} | {ops['p95_ms']:.1f} | {ops['llm_calls']} |"
        )
    lines += ["", "## Per-label F1 (actions)", "", "| condition | implemented | planning | indeterminate |",
              "|---|---|---|---|"]
    for cond, block in results.items():
        if block.get("status") != "ok":
            continue
        pl = block["action"]["per_label"]
        lines.append(
            f"| {cond} | {_fmt(pl.get('implemented', {}).get('f1'))} "
            f"| {_fmt(pl.get('planning', {}).get('f1'))} "
            f"| {_fmt(pl.get('indeterminate', {}).get('f1'))} |"
        )
    lines += ["", "## Bootstrap 95 % CI on macro-F1", "",
              "| condition | mean | lo | hi |", "|---|---|---|---|"]
    for cond, block in results.items():
        if block.get("status") != "ok":
            continue
        b = block["bootstrap"]
        lines.append(f"| {cond} | {_fmt(b['mean'])} | {_fmt(b['lo'])} | {_fmt(b['hi'])} |")
    out = run_dir / "report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
