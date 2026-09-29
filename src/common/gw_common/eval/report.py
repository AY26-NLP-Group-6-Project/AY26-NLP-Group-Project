"""Markdown rendering of a run. Accuracy, stability and cost always appear in the same table."""

from __future__ import annotations

from pathlib import Path

from gw_common.schemas import RunManifest

SLICE_SECTIONS = {"row_type": "Row type", "aspect_source": "Aspect source",
                  "agreement": "Annotator agreement", "category": "Aspect category"}


def _fmt(v, spec: str = ".4f") -> str:
    return "n/a" if v is None else format(v, spec)


def _mean_sd(block: dict, key: str) -> str:
    agg = block.get("aggregate", {}).get(key)
    if not agg:
        return "n/a"
    sd = f" ±{agg['sd']:.3f}" if agg.get("sd") else ""
    return f"{agg['mean']:.4f}{sd}"


def write_report(run_dir: Path, manifest: RunManifest, results: dict[str, dict]) -> Path:
    lines = [f"# {manifest.run_id}", ""]
    if manifest.label_source != "human_majority":
        lines += [
            f"> **Development numbers only.** Gold labels are `{manifest.label_source}`, not the human",
            "> majority. Nothing here may be quoted in the report; re-run with `--labels human_majority`.",
            "",
        ]
    if manifest.config.get("split") == "test":
        lines += ["> **Test split.** Open it once, for the final report; tune on `dev`.", ""]
    llm = manifest.llm or {}
    lines += [
        f"- system: `{manifest.system}` · task: `{manifest.task}`",
        f"- dataset: `{manifest.dataset_id}` @ `{manifest.dataset_hash}` · n = {manifest.n_items}"
        f" · labels: `{manifest.label_source}` · split: `{manifest.config.get('split')}`"
        f" · repeats: {manifest.repeats}",
        f"- model: `{llm.get('chat_model', 'n/a')}` · effort: `{llm.get('reasoning_effort', 'n/a')}`"
        f" · temperature: {llm.get('temperature', 'n/a')} · cache: {llm.get('cache', 'n/a')}",
        f"- git: `{manifest.git_sha[:8]}`{' (dirty)' if manifest.git_dirty else ''}"
        + (f" · wall: {manifest.wall_seconds:.1f}s" if manifest.wall_seconds else ""),
    ]
    if manifest.config.get("slices"):
        lines.append(f"- slices: `{manifest.config['slices']}`")
    lines += [
        "",
        "| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base"
        " | flips (pooled) | p (McNemar) | p95 ms | LLM calls |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cond, block in results.items():
        if block.get("status") != "ok":
            lines.append(f"| {cond} | n/a | | | | | | | | | |")
            continue
        vs = block.get("vs_baseline", {})
        flips = vs.get("flips_pooled", {})
        agg = block["aggregate"]
        ops = block["reps"][0]["ops"]
        unstable = agg.get("unstable_items")
        flip_cell = "—" if not flips else (
            f"+{flips.get('wrong_to_right', 0)}/-{flips.get('right_to_wrong', 0)}"
        )
        lines.append(
            f"| {cond} | {_mean_sd(block, 'macro_f1')} | {_mean_sd(block, 'micro_f1')} "
            f"| {_mean_sd(block, 'accuracy')} | {_fmt(block['majority']['action']['macro_f1'])} "
            f"| {'n/a' if unstable is None else unstable} "
            f"| {_fmt(vs.get('delta_macro_f1_mean'), '+.4f') if vs else '—'} "
            f"| {flip_cell} "
            f"| {_fmt(vs.get('mcnemar_majority', {}).get('p_value'), '.3f') if vs else '—'} "
            f"| {ops['p95_ms']:.1f} | {sum(r['ops']['llm_calls'] for r in block['reps'])} |"
        )
    ev_rows = [(c, b["evidence"]) for c, b in results.items()
               if b.get("status") == "ok" and b.get("evidence")]
    if ev_rows:
        lines += ["", "## Evidence", "",
                  "| condition | coverage | mean spans | target dropped | by source |",
                  "|---|---|---|---|---|"]
        for cond, ev in ev_rows:
            lines.append(f"| {cond} | {ev['coverage']:.2f} | {ev['mean_spans']:.2f} "
                         f"| {ev['target_dropped']} | {ev['by_source']} |")

    lines += ["", "## Per-label F1 (majority vote over repeats)", "",
              "| condition | implemented | planning | indeterminate | none (detection F1) |",
              "|---|---|---|---|---|"]
    for cond, block in results.items():
        if block.get("status") != "ok":
            continue
        pl = block["majority"]["action"]["per_label"]
        none_f1 = block["majority"]["all_labels"]["per_label"].get("none", {}).get("f1")
        lines.append(
            f"| {cond} | {_fmt(pl.get('implemented', {}).get('f1'))} "
            f"| {_fmt(pl.get('planning', {}).get('f1'))} "
            f"| {_fmt(pl.get('indeterminate', {}).get('f1'))} | {_fmt(none_f1)} |"
        )

    lines += ["", "## Bootstrap 95 % CI on macro-F1 (majority vote)", "",
              "| condition | mean | lo | hi |", "|---|---|---|---|"]
    for cond, block in results.items():
        if block.get("status") == "ok":
            b = block["bootstrap"]
            lines.append(f"| {cond} | {_fmt(b['mean'])} | {_fmt(b['lo'])} | {_fmt(b['hi'])} |")

    for key, title in SLICE_SECTIONS.items():
        rows = [(c, b["slices"][key]) for c, b in results.items()
                if b.get("status") == "ok" and b.get("slices", {}).get(key)]
        if not rows:
            continue
        buckets = sorted({b for _, s in rows for b in s})
        lines += ["", f"## {title} (macro-F1, majority vote)", "",
                  "| condition | " + " | ".join(f"{b} (n={rows[0][1].get(b, {}).get('n', 0)})"
                                                for b in buckets) + " |",
                  "|---" * (len(buckets) + 1) + "|"]
        for cond, s in rows:
            # A bucket with no action rows (e.g. gold `none` only) has no macro-F1 to show.
            cells = ["n/a" if not s.get(b, {}).get("n_action_rows") else _fmt(s[b]["macro_f1"])
                     for b in buckets]
            lines.append(f"| {cond} | " + " | ".join(cells) + " |")

    out = run_dir / "report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
