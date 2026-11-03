"""Greenwash-RAG demo: one dev-split item at a time through a registered system, against the gold.

    uv sync --group frontend
    uv run streamlit run frontend/app.py

The sidebar switches the research question and shows its definition; the page draws one item of that
question's dev split, runs it through the chosen system step by step (retrieval, then the shared
classifier or judge) with the time each step took, and shows the answer against the gold with the
evidence, the citations, the tokens and the cost. Every run lands in a session log for the course's
"five queries and their speed". `frontend/README.md` has the details.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import core
import pandas as pd
import streamlit as st
from gw_common.schemas import EvidenceCondition, GoldItem

RQ1, RQ2, TASKS = core.RQ1, core.RQ2, core.TASKS
COLOUR = {
    "implemented": "green",
    "planning": "blue",
    "indeterminate": "orange",
    "none": "gray",
    "achieved": "green",
    "failed": "red",
    "unclear": "orange",
    "disappeared": "gray",
    "revised": "violet",
}
TEXT_CHARS = 700

st.set_page_config(page_title="Greenwash-RAG demo", page_icon="🌱", layout="wide")


def badge(label: str | None) -> str:
    return f":{COLOUR.get(label or '', 'gray')}[**{label or '—'}**]"


# --------------------------------------------------------------------------- cached loads
@st.cache_data(show_spinner=False)
def items_of(task: str) -> list:
    return core.load_items(task)


@st.cache_data(show_spinner=False)
def systems_of(task: str) -> tuple[dict[str, list[str]], dict[str, str]]:
    return core.systems_for(task)


@st.cache_resource(show_spinner=False)
def system_of(name: str, replay: bool):
    """The System object; its retriever and classifier are built on first use, inside a timed step."""
    os.environ["GW_LLM_CACHE"] = "1" if replay else "0"
    return core.load_system(name)


@st.cache_resource(show_spinner=False)
def judge_client(replay: bool):
    os.environ["GW_LLM_CACHE"] = "1" if replay else "0"
    return core.LLMClient()


@st.cache_data(show_spinner=False)
def facts() -> dict:
    return {
        "kb": core.kb_facts(),
        "git": core.git_sha(),
        "llm": core.settings().describe(),
        "urls": core.source_urls(),
    }


@st.cache_data(show_spinner=False)
def page_image(pdf: str, page: int) -> bytes | None:
    return core.page_png(Path(pdf), page)


@st.cache_data(show_spinner=False)
def published(task: str) -> list[dict]:
    return core.published_runs(task)


# --------------------------------------------------------------------------- timing a step
def timed(box, label: str, fn):
    """Run `fn` in a worker thread, showing the elapsed time while it runs; (result, milliseconds)."""
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        while not future.done():
            box.markdown(f"⏳ {label} · {time.perf_counter() - t0:.1f} s")
            time.sleep(0.1)
    ms = (time.perf_counter() - t0) * 1000
    try:
        return future.result(), ms
    except Exception:
        box.markdown(f"❌ {label} failed after {ms:.0f} ms")
        raise


# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🌱 Greenwash-RAG")
    st.caption("Evidence-grounded, cross-year tracking of sustainability claims in SGX reports")
    task = st.radio(
        "Research question", [RQ1, RQ2], format_func=lambda t: TASKS[t]["short"], horizontal=True, key="task"
    )
    st.markdown(TASKS[task]["definition"])
    st.caption(f"Data: {TASKS[task]['dataset']}.")
    st.divider()

    systems, failed = systems_of(task)
    if not systems:
        st.error("No registered system can take part in this task.")
        st.stop()
    preferred = next((n for n in ("baseline-rag", "graph-rag") if n in systems), next(iter(systems)))
    system_name = st.selectbox("System", list(systems), index=list(systems).index(preferred))
    if task == RQ1:
        offered = systems[system_name]
        default = next(
            (c for c in ("cross_year_rrf", "cross_year_fused", "sentence_only") if c in offered), offered[0]
        )
        condition = EvidenceCondition(
            st.selectbox("Evidence condition", offered, index=offered.index(default))
        )
    else:
        condition = EvidenceCondition.PROMISE_WINDOW
        st.selectbox("Evidence condition", [condition.value], disabled=True)
    k = int(
        st.number_input(
            "Evidence spans the model may see (k)", min_value=1, max_value=40, value=TASKS[task]["k"]
        )
    )
    runs = int(
        st.slider(
            "Model runs on the same evidence (majority vote)",
            1,
            3,
            1,
            help="The model re-samples: the evaluation runs every item three times and votes.",
        )
    )
    replay = st.toggle(
        "Replay cached model responses",
        value=False,
        help="Off: every run calls the model afresh and the timings are real. On: a request "
        "already in artifacts/cache/llm.sqlite is answered from there, offline.",
    )
    if st.session_state.get("replay_was") not in (None, replay):
        system_of.clear()
        judge_client.clear()
    st.session_state["replay_was"] = replay
    os.environ["GW_LLM_CACHE"] = "1" if replay else "0"
    for name, why in failed.items():
        st.caption(f"`{name}` unavailable: {why}")

    info = facts()
    llm, kb = info["llm"], info["kb"]
    if not core.settings().chat_api_key and not replay:
        st.warning("No LLM_API_KEY in .env: runs will fail unless replaying cached responses.")
    with st.expander("Setup", expanded=False):
        prices = llm.get("prices_usd_per_mtok") or {}
        st.markdown(
            f"- chat model `{llm.get('chat_model')}`, effort `{llm.get('reasoning_effort')}`, "
            f"temperature {llm.get('temperature')}\n"
            f"- embeddings `{llm.get('embed_model')}`\n"
            f"- prices USD/M tokens: in {prices.get('chat_in')}, out {prices.get('chat_out')}, "
            f"embed {prices.get('embed')}\n"
            + (
                f"- knowledge base `{kb.get('build_id')}`: {kb.get('chunks', 0):,} statements, "
                f"{kb.get('companies')} issuers, {kb.get('reports')} reports, {kb.get('words', 0):,} words, "
                f"hash `{kb.get('chunks_sha256')}`\n"
                if kb
                else "- knowledge base: store not found\n"
            )
            + f"- git `{info['git']}`"
        )

# --------------------------------------------------------------------------- the query
st.header(TASKS[task]["title"])
items = items_of(task)
key = f"item_{task}"
if key not in st.session_state:
    st.session_state[key] = core.pick(items, task)
item = st.session_state[key]
current_id = core.item_id(task, item)

card, side = st.columns([5, 1], vertical_alignment="top")
with side:
    if st.button("🎲 Another one", width="stretch", help="Draw another item of the dev split"):
        st.session_state[key] = core.pick(items, task, current_id)
        st.session_state.pop("result", None)
        st.rerun()
    wanted = st.text_input("…or by id", key=f"jump_{task}", placeholder="42 or P00042")
    if st.button("Go", width="stretch") and wanted:
        found = core.find(items, task, wanted)
        if found is None:
            st.caption(f"no dev item `{wanted.strip()}`")
        else:
            st.session_state[key] = found
            st.session_state.pop("result", None)
            st.rerun()
    st.caption(f"{len(items)} items in the dev split")

with card:
    if task == RQ1:
        it: GoldItem = item
        st.markdown(
            f"**{it.company} · {it.year} report · p.{it.page}** · aspect: *{it.aspect or '(none proposed)'}*"
            f"{f' ({it.category})' if it.category else ''} · item `{it.item_id}`"
            f"{' · pilot row' if it.pilot else ''}"
        )
        st.markdown(f"> {it.text}")
        with st.expander("Neighbouring sentences (what the `local` condition shows)"):
            st.markdown(f"*before:* {it.context_prev or '—'}\n\n*after:* {it.context_next or '—'}")
    else:
        p = item["promise"]
        o = p["origin"]
        year_from, year_to = core.window_of(p)
        quantity = ""
        if p.get("quantity") is not None:
            quantity = f" · {p.get('direction') or 'target'} {p['quantity']:g}{p.get('unit') or ''}"
        st.markdown(
            f"**{p['company']} · commitment stated in the {o['year']} report, p.{o['page']}** · "
            f"deadline **{p['target_year']}** · `{item['promise_id']}`"
        )
        st.markdown(f"> {o.get('text') or o.get('target_text')}")
        st.markdown(
            f"Targeted: *{p['metric']}*{quantity}"
            f"{f' (baseline {p["baseline_year"]})' if p.get('baseline_year') else ''} · {p.get('kind')}"
            f"{' · recurring annual target' if p.get('recurring') else ''} · "
            f"window the retriever may read: **{year_from}–{year_to}** reports"
            f"{f' · {len(p.get("related", []))} linked target(s)' if p.get('related') else ''}"
        )

use_custom = st.toggle("Use a query of my own instead (no gold label)", value=False, key=f"custom_{task}")
query_item = item
if use_custom:
    names = core.companies(items, task)
    if task == RQ1:
        it = item
        c1, c2, c3 = st.columns([2, 1, 1])
        text = c1.text_area("Sentence", value=it.text, height=90)
        aspect = c2.text_input("Aspect", value=it.aspect or "")
        company = c3.selectbox("Company", names, index=names.index(it.company) if it.company in names else 0)
        year = c3.number_input("Report year", 2020, 2025, int(it.year))
        query_item = core.custom_rq1(text, aspect, company, int(year))
    else:
        p = item["promise"]
        c1, c2 = st.columns([2, 1])
        sentence = c1.text_area("Commitment sentence", value=p["origin"].get("text") or "", height=90)
        metric = c1.text_input("What is targeted (metric)", value=p["metric"])
        company = c2.selectbox(
            "Company", names, index=names.index(p["company"]) if p["company"] in names else 0
        )
        origin_year = c2.number_input("Stated in the report of", 2020, 2024, int(p["origin"]["year"]))
        target_year = c2.number_input("Deadline year", 2021, 2025, int(p["target_year"]))
        recurring = c2.checkbox("Recurring annual target", value=bool(p.get("recurring")))
        query_item = core.custom_promise(
            company, sentence, metric, int(origin_year), int(target_year), recurring
        )
    st.caption("A custom query is judged the same way; there is no gold label to score it against.")

run = st.button("▶ Run with this query", type="primary")


# --------------------------------------------------------------------------- running
def run_rq1(system_name: str, cond: EvidenceCondition, k: int, runs: int, replay: bool, item) -> dict:
    item_key = core.item_id(RQ1, item)
    system = system_of(system_name, replay)
    with st.status("Running…", expanded=True) as status:
        t_all = time.perf_counter()
        b_load, b_ret = st.empty(), st.empty()
        needs_retriever = cond not in core.NO_RETRIEVAL
        _, ms_load = timed(
            b_load, f"Loading `{system_name}` (first use reads the store)", lambda: core.warm_up(system, cond)
        )
        b_load.markdown(f"✅ `{system_name}` ready · {ms_load:.0f} ms")
        embed_before = core.embed_tokens(system)
        if needs_retriever:
            (spans, dropped), ms_ret = timed(
                b_ret,
                f"Retrieving evidence ({cond.value}, k = {k})",
                lambda: core.retrieve_rq1(system, item, cond, k),
            )
            b_ret.markdown(
                f"✅ Retrieval · {ms_ret:.0f} ms · {len(spans)} span(s)"
                + (f" · {dropped} target span dropped" if dropped else "")
            )
        else:
            spans, dropped, ms_ret = [], 0, 0.0
            b_ret.markdown(f"➖ No retrieval under `{cond.value}`")
        embed_used = core.embed_tokens(system) - embed_before
        preds, ms_runs = [], []
        for i in range(runs):
            box = st.empty()
            pred, ms = timed(
                box,
                f"Classifying (run {i + 1} of {runs})",
                lambda: core.classify_rq1(system, item, cond, spans),
            )
            box.markdown(
                f"✅ Classification run {i + 1} · {ms:.0f} ms · {badge(pred.label.value)} · "
                f"{pred.input_tokens} / {pred.output_tokens} tokens in / out"
                + (" · from cache" if pred.llm_calls == 0 and pred.input_tokens else "")
            )
            preds.append(pred)
            ms_runs.append(ms)
        total = time.perf_counter() - t_all
        status.update(label=f"Done in {total:.1f} s", state="complete", expanded=False)
    vote = core.vote_rq1(preds).value
    tokens_in, tokens_out = sum(p.input_tokens for p in preds), sum(p.output_tokens for p in preds)
    return {
        "task": RQ1,
        "item_id": item_key,
        "system": system_name,
        "condition": cond.value,
        "k": k,
        "gold": core.gold_of(RQ1, item),
        "vote": vote,
        "labels": [p.label.value for p in preds],
        "predictions": [p.model_dump(mode="json") for p in preds],
        "spans": [s.model_dump(mode="json") for s in spans],
        "dropped": dropped,
        "retrieval_ms": ms_ret,
        "generate_ms": sum(ms_runs),
        "run_ms": ms_runs,
        "total_s": total,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "embed_tokens": embed_used,
        "cost": core.settings().cost_usd(tokens_in, tokens_out, embed_used),
        "item": item.model_dump(mode="json"),
    }


def run_rq2(system_name: str, k: int, runs: int, replay: bool, row: dict) -> dict:
    promise = row["promise"] if "promise" in row else row
    item_key = row["promise_id"]
    system = system_of(system_name, replay)
    client = judge_client(replay)
    with st.status("Running…", expanded=True) as status:
        t_all = time.perf_counter()
        b_load, b_ret = st.empty(), st.empty()
        _, ms_load = timed(
            b_load,
            f"Loading `{system_name}` (first use reads the store)",
            lambda: core.warm_up(system, core.R.CONDITION),
        )
        b_load.markdown(f"✅ `{system_name}` ready · {ms_load:.0f} ms")
        embed_before = core.embed_tokens(system)
        year_from, year_to = core.window_of(promise)
        evidence, ms_ret = timed(
            b_ret,
            f"Retrieving the window {year_from}–{year_to} (k = {k})",
            lambda: core.retrieve_rq2(system, promise, k),
        )
        years = sorted({e["year"] for e in evidence})
        b_ret.markdown(
            f"✅ Retrieval · {ms_ret:.0f} ms · {len(evidence)} statement(s) from "
            f"{len(years)} report year(s){f' {years}' if years else ''}"
        )
        embed_used = core.embed_tokens(system) - embed_before
        judgements, ms_runs, usage = [], [], []
        for i in range(runs):
            box = st.empty()
            before = dict(client.usage)
            res, ms = timed(
                box, f"Judging (run {i + 1} of {runs})", lambda: core.judge_rq2(promise, evidence, client)
            )
            spent = core.usage_delta(client.usage, before)
            reported = core.J.reported(res["outcome"])
            box.markdown(
                f"✅ Judge run {i + 1} · {ms:.0f} ms · {badge(reported)}"
                + (f" (as `{res['outcome']}`)" if res["outcome"] != reported else "")
                + f" · {spent['input_tokens']} / {spent['output_tokens']} tokens in / out"
                + (" · from cache" if spent["cache_hits"] and not spent["calls"] else "")
                + ("" if res["parse_ok"] else " · reply incomplete")
            )
            judgements.append(res)
            ms_runs.append(ms)
            usage.append(spent)
        total = time.perf_counter() - t_all
        status.update(label=f"Done in {total:.1f} s", state="complete", expanded=False)
    tokens_in = sum(u["input_tokens"] for u in usage)
    tokens_out = sum(u["output_tokens"] for u in usage)
    return {
        "task": RQ2,
        "item_id": item_key,
        "system": system_name,
        "condition": core.R.CONDITION.value,
        "k": k,
        "gold": core.gold_of(RQ2, row),
        "vote": core.vote_rq2([j["outcome"] for j in judgements]),
        "labels": [core.J.reported(j["outcome"]) for j in judgements],
        "judgements": judgements,
        "evidence": evidence,
        "retrieval_ms": ms_ret,
        "generate_ms": sum(ms_runs),
        "run_ms": ms_runs,
        "total_s": total,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "embed_tokens": embed_used,
        "cost": core.settings().cost_usd(tokens_in, tokens_out, embed_used),
        "promise": promise,
        "gold_row": {k_: v for k_, v in row.items() if k_ != "promise"},
    }


if run:
    try:
        if task == RQ1:
            result = run_rq1(system_name, condition, k, runs, replay, query_item)
        else:
            result = run_rq2(system_name, k, runs, replay, query_item)
    except Exception as exc:  # noqa: BLE001 - show the failure on the page instead of a blank screen
        st.exception(exc)
        st.stop()
    st.session_state["result"] = result
    st.session_state.setdefault("log", []).append(
        {
            "at": datetime.now().strftime("%H:%M:%S"),
            "task": task,
            "system": system_name,
            "condition": result["condition"],
            "item": result["item_id"],
            "gold": result["gold"],
            "answer": result["vote"],
            "correct": (None if result["gold"] is None else result["vote"] == result["gold"]),
            "retrieval ms": round(result["retrieval_ms"]),
            "generation ms": round(result["generate_ms"]),
            "runs": runs,
            "tokens in": result["tokens_in"],
            "tokens out": result["tokens_out"],
            "USD": (None if result["cost"] is None else round(result["cost"], 5)),
        }
    )


# --------------------------------------------------------------------------- the answer
def verdict(res: dict) -> None:
    gold, vote = res["gold"], res["vote"]
    if gold is None:
        st.info(f"System answer: {badge(vote)} · custom query, no gold label", icon="ℹ️")
    elif vote == gold:
        st.success(f"**Correct** · system {badge(vote)} · gold {badge(gold)}", icon="✅")
    else:
        st.error(f"**Wrong** · system {badge(vote)} · gold {badge(gold)}", icon="❌")
    if len(res["labels"]) > 1:
        st.caption(
            "Runs: "
            + " · ".join(badge(lab) for lab in res["labels"])
            + f" → vote {badge(vote)}"
            + (
                "  (the runs disagree: this item is one the evaluation counts as unstable)"
                if len(set(res["labels"])) > 1
                else ""
            )
        )
    cols = st.columns(6)
    cols[0].metric("retrieval", f"{res['retrieval_ms']:.0f} ms")
    cols[1].metric(
        "generation",
        f"{res['generate_ms']:.0f} ms",
        help="The model call(s); the per-run times are in the log above",
    )
    cols[2].metric("end to end", f"{res['total_s']:.1f} s", help="Including the first-use load of the system")
    cols[3].metric("tokens in / out", f"{res['tokens_in']} / {res['tokens_out']}")
    cols[4].metric("embedding tokens", f"{res['embed_tokens']}")
    cols[5].metric("cost", "no prices set" if res["cost"] is None else f"${res['cost']:.5f}")


def page_preview(options: list[tuple[str, str | None, int | None]], urls: dict[str, str]) -> None:
    """A selectbox over the sources of the answer; the chosen page is rendered from the raw report."""
    labels = ["—"] + [label for label, _, _ in options]
    choice = st.selectbox("Open the page a source comes from", labels, index=0)
    if choice == "—":
        return
    _, file, page = next(o for o in options if o[0] == choice)
    pdf = core.resolve_pdf(file)
    url = urls.get(file or "")
    if url:
        st.markdown(f"Report fetched from <{url}>")
    if pdf is None:
        st.caption("The raw report is not on this machine (`kb/raw/` holds the PDFs and is never shared).")
        return
    if not page:
        st.caption("No page number recorded for this source.")
        return
    png = page_image(str(pdf), int(page))
    if png is None:
        st.caption(f"Page {page} could not be rendered from `{pdf.name}`.")
    else:
        st.image(png, caption=f"{pdf.relative_to(core.KB_DIR).as_posix()} · page {page}")


def show_rq1(res: dict) -> None:
    verdict(res)
    it, pred = res["item"], res["predictions"][-1]
    cited = {c["ref"] for c in pred["citations"]}
    left, right = st.columns([3, 2])
    with left:
        st.subheader("What the classifier said")
        if pred["rationale"]:
            st.markdown(f"**Rationale** · {pred['rationale']}")
        else:
            st.caption(
                "No rationale (this classifier returns a label only)."
                if res["system"] in ("majority", "random")
                else "No rationale: the reply was not in the asked format."
            )
        if pred["citations"]:
            st.markdown("**Sources cited**")
            for c in pred["citations"]:
                st.markdown(
                    f"- `{c['ref']}` {c['company']} {c['year']}, p.{c['page']} — *{c['quote'][:200]}…*"
                )
        if pred["invalid_citations"]:
            st.caption(f"{pred['invalid_citations']} cited tag(s) named no shown source.")
        if not pred["parse_ok"]:
            st.caption("The reply was not the asked JSON; the label was read from the text.")
        st.subheader("Evidence shown to the classifier")
        if not res["spans"]:
            st.caption(
                "None under this condition."
                if res["condition"] in ("sentence_only", "local")
                else "The retriever returned nothing inside the condition's filters."
            )
        for n, s in enumerate(res["spans"], 1):
            pin = "📌 " if f"E{n}" in cited else ""
            st.markdown(
                f"{pin}`E{n}` **{s['company']} {s['year']}, p.{s['page']}** · via `{s['why']}` · "
                f"score {s['score']:.3f}"
            )
            st.markdown(f"> {s['text'][:TEXT_CHARS]}{'…' if len(s['text']) > TEXT_CHARS else ''}")
        if res["dropped"]:
            st.caption(f"{res['dropped']} returned span(s) were the target sentence itself and were dropped.")
    with right:
        st.subheader("The gold label and its context")
        meta = it.get("meta") or {}
        if res["gold"] is None:
            st.caption("Custom query: nothing to compare against.")
        else:
            st.markdown(
                f"Gold {badge(res['gold'])} from `{it.get('label_source')}`"
                + (f" · {meta['n_annotators']} annotator(s)" if meta.get("n_annotators") else "")
                + (f" · agreement {meta['agreement']:.2f}" if meta.get("agreement") is not None else "")
                + (" · adjudicated" if meta.get("adjudicated") else "")
            )
            if meta.get("llm_pre"):
                st.caption(
                    "Pre-annotations (never an input): "
                    + ", ".join(f"{m} {badge(v)}" for m, v in meta["llm_pre"].items())
                )
            if meta.get("row_type") == "no_aspect":
                st.caption("A row with no proposed aspect: `none` unless the annotators saw one.")
        st.markdown(f"**Target** `T` · {it['company']} {it['year']}, p.{it.get('page') or '?'}")
        st.markdown(f"> {it['text']}")
        if it.get("context_prev") or it.get("context_next"):
            with st.expander("Neighbouring sentences `C`", expanded=res["condition"] == "local"):
                st.markdown(
                    f"*before:* {it.get('context_prev') or '—'}\n\n*after:* {it.get('context_next') or '—'}"
                )
        sources = [
            (f"T · {it['company']} {it['year']} p.{it.get('page') or '?'}", it.get("file"), it.get("page"))
        ]
        sources += [
            (f"E{n} · {s['company']} {s['year']} p.{s['page']}", s.get("file"), s.get("page"))
            for n, s in enumerate(res["spans"], 1)
        ]
        page_preview(sources, facts()["urls"])


def show_rq2(res: dict) -> None:
    verdict(res)
    p, rows, gold_row = res["promise"], res["evidence"], res["gold_row"]
    # the judgement whose outcome carried the vote, for the per-statement labels shown
    judgement = next(
        (j for j in res["judgements"] if core.J.reported(j["outcome"]) == res["vote"]), res["judgements"][-1]
    )
    labels = {lab["ref"]: lab for lab in judgement.get("labels", [])}
    rests_on = set(judgement.get("evidence_refs", []))
    left, right = st.columns([3, 2])
    with left:
        st.subheader("What the judge read")
        st.markdown(
            f"Outcome by rule {badge(core.J.reported(judgement['outcome']))}"
            + (
                f" (`{judgement['outcome']}`)"
                if judgement["outcome"] != core.J.reported(judgement["outcome"])
                else ""
            )
            + (
                f" · the model's own call {badge(judgement['model_outcome'])}"
                if judgement.get("model_outcome")
                else ""
            )
            + f" · read as {'an annual target' if judgement.get('annual') else 'a one-off commitment'}"
            + ("" if judgement.get("parse_ok", True) else " · reply incomplete, so `unclear`")
        )
        if judgement.get("rationale"):
            st.markdown(f"**Rationale** · {judgement['rationale']}")
        if not rows:
            st.caption("No statement came back for the window, so the commitment counts as disappeared.")
        for year in sorted({e["year"] for e in rows}):
            st.markdown(f"**{year} report**")
            for e in (e for e in rows if e["year"] == year):
                lab = labels.get(e["ref"], {})
                marks = []
                if lab.get("relation") == "this_target":
                    marks.append(":green[this target]")
                elif lab.get("relation") == "same_metric":
                    marks.append(":orange[same metric]")
                if lab.get("deadline_result") == "met":
                    marks.append(":green[deadline met]")
                elif lab.get("deadline_result") == "missed":
                    marks.append(":red[deadline missed]")
                if lab.get("change") == "later":
                    marks.append(":violet[moved later]")
                pin = "📌 " if e["ref"] in rests_on else ""
                via = (e.get("via") or "").replace("trajectory:", "")
                st.markdown(
                    f"{pin}`{e['ref']}` p.{e['page']} · via `{via}`"
                    + (f" · follows `{e['follows']}`" if e.get("follows") else "")
                    + " "
                    + " ".join(marks)
                )
                st.markdown(f"> {e['text'][:TEXT_CHARS]}{'…' if len(e['text']) > TEXT_CHARS else ''}")
    with right:
        st.subheader("The gold outcome and its context")
        if res["gold"] is None:
            st.caption("Custom query: nothing to compare against.")
        else:
            source = gold_row.get("label_source")
            st.markdown(
                f"Gold {badge(res['gold'])} · "
                + (
                    "two group members, independently"
                    if source == "human_pair"
                    else "two model annotators of different families, calibrated on the group's rows"
                )
                + (" · agreed" if gold_row.get("agreed") else " · disagreed, adjudicated")
            )
            for who in ("a1", "a2"):
                if gold_row.get(who):
                    st.markdown(
                        f"- annotator {who[-1]}: {badge(gold_row[who])} — {gold_row.get(who + '_note') or ''}"
                    )
            if gold_row.get("adjudicate"):
                st.markdown(f"- adjudication: {gold_row['adjudicate']}")
        o = p["origin"]
        st.markdown(f"**The commitment** · {p['company']} {o['year']}, p.{o.get('page')}")
        st.markdown(f"> {o.get('text') or o.get('target_text')}")
        if p.get("restatements"):
            st.caption(f"Restated in {', '.join(str(y) for y in p.get('stated_in_years', []))}.")
        sources = [(f"Promise · {p['company']} {o['year']} p.{o.get('page')}", o.get("file"), o.get("page"))]
        sources += [(f"{e['ref']} · {e['year']} p.{e['page']}", e.get("file"), e.get("page")) for e in rows]
        page_preview(sources, facts()["urls"])


result = st.session_state.get("result")
if result and result["task"] == task and (use_custom or result["item_id"] == current_id):
    st.divider()
    (show_rq1 if task == RQ1 else show_rq2)(result)

# --------------------------------------------------------------------------- the log and the record
st.divider()
log = st.session_state.get("log", [])
with st.expander(f"Session log · {len(log)} run(s)", expanded=bool(log)):
    if not log:
        st.caption("Every run lands here: the course asks for a handful of queries and their speed.")
    else:
        df = pd.DataFrame(log)
        scored = df[df["correct"].notna()]
        st.caption(
            f"{len(df)} run(s) · retrieval {df['retrieval ms'].mean():.0f} ms and generation "
            f"{df['generation ms'].mean():.0f} ms on average"
            + (
                f" · {int(scored['correct'].sum())} of {len(scored)} right against the gold"
                if len(scored)
                else ""
            )
            + (f" · USD {df['USD'].dropna().sum():.4f} in all" if df["USD"].notna().any() else "")
        )
        st.dataframe(df, hide_index=True, width="stretch")
        st.download_button(
            "Download as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="greenwash-rag-session.csv",
            mime="text/csv",
        )
        if st.button("Clear the log"):
            st.session_state["log"] = []
            st.rerun()

with st.expander("Published runs on the dev split (results/)", expanded=False):
    runs_table = published(task)
    if not runs_table:
        st.caption("No published run for this task.")
    else:
        st.caption(
            "Majority vote over the repeats, scored by the evaluation harness; "
            "compare systems paired on the same items (`gw-eval --compare`), not by these means."
        )
        st.dataframe(pd.DataFrame(runs_table), hide_index=True, width="stretch")
