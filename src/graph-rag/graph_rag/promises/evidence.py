"""Evidence for a promise's outcome: which statements of the company's later reports the judge sees.

Two modes.

`deadline` is the first version, kept for reference: hybrid top-6 over the reports of the deadline
year and the year after. Its recorded results were produced when the dense index covered only the
sentence-shaped statements (65 % of all), and most result sentences ("... was 61 kwh per square foot
(FY2020: 68 kwh per square foot)") were outside it. A statement that scores in one of the two fused
rankings only is put by RRF below statements that are mediocre in both: of eight answer statements found
by hand (`docs/case-studies.md`), four ranked first to third on BM25 and were still cut. The one-year
window and the single budget remain its limits.

`trajectory` (default) follows the promise through every report after the one that made it, up to the
year after the deadline:

- every statement of a report is ranked by BM25 and by dense similarity; vectors the store lacks
  (statements under five words) are embedded on demand (cached), so RRF fuses two complete rankings;
- each report year has its own budget, the first report at or after the deadline the largest. A delay
  announced two years early is in an earlier report, not in the deadline one;
- the neighbours of the best hits in that report are added: a target table is parsed into one statement
  per cell, and the result ("Requires improvement as ...") sits beside the target, not in it;
- targets the extractor linked to this promise, the same metric with another deadline or level
  (`related`), are added whatever their rank. That is the join on (company, metric) the promise graph
  already holds, and where a moved goalpost shows.

Statements come back in report order, so the judge and the annotator read a timeline.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np
from baseline_rag import chunks as chunk_store
from baseline_rag.index import BM25, rrf
from gw_common.evidence import normalise
from gw_common.llm import LLMClient
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query

from graph_rag.config import GraphConfig
from graph_rag.promises.extract import out_dir
from graph_rag.store.duckdb_store import DuckDBGraphStore

MODES = ("deadline", "trajectory")
EVIDENCE_K = 6
CANDIDATES = 40
MIN_WORDS = 5
STORE = chunk_store.DEFAULT_BUILD
K_DEADLINE = 6          # the first report at or after the deadline: where the outcome should be reported
K_AFTER = 3             # the report after that
K_BEFORE = 2            # each report between the promise and the deadline
NEIGHBOURS_OF = 2       # hits of the deadline report whose adjacent statements are added
LINKED = 3              # related targets taken from the promise graph
EMBED_CHARS = 2000      # a flattened table can run to pages; its head is enough to place it


def evidence_path(cfg: GraphConfig, mode: str) -> Path:
    return out_dir(cfg) / f"evidence.{mode}.jsonl"


def query_of(promise: dict) -> str:
    return f"{promise['metric']}. {promise['origin']['target_text']}"


class EvidenceFinder:
    """Mode `deadline`."""

    def __init__(self, cfg: GraphConfig, client: LLMClient, store: str = STORE) -> None:
        self.store = DuckDBGraphStore(cfg.db_path, read_only=True)
        self.client = client
        try:
            chunks, self.vectors, _ = chunk_store.load(store)
            self.row_of = {c.chunk_id: i for i, c in enumerate(chunks)}
        except FileNotFoundError:        # dense is an improvement, not a requirement
            self.vectors, self.row_of = None, {}

    @lru_cache(maxsize=256)  # noqa: B019 - one finder per run
    def _index(self, company: str, years: tuple[int, ...]):
        placeholders = ",".join("?" * len(years))
        rows = self.store.con.execute(
            f"SELECT stmt_id, year, page, sha256, text FROM statements "
            f"WHERE company = ? AND year IN ({placeholders}) ORDER BY year, page, idx",
            [company, *years],
        ).fetchall()
        docs, seen = [], set()
        for stmt_id, year, page, sha, text in rows:
            key = (year, normalise(text))
            if len(text.split()) < MIN_WORDS or key in seen:
                continue
            seen.add(key)
            docs.append({"stmt_id": stmt_id, "year": year, "page": page, "file": sha, "text": text})
        return docs, BM25([d["text"] for d in docs])

    def find(self, promise: dict, k: int = EVIDENCE_K) -> list[dict]:
        years = tuple(promise["outcome_years"])
        if not years:
            return []
        docs, bm25 = self._index(promise["company"], years)
        if not docs:
            return []
        query = query_of(promise)
        sparse = bm25.search(query, None, CANDIDATES)
        rankings = [sparse]
        if self.vectors is not None:
            rows = [(i, self.row_of[d["stmt_id"]]) for i, d in enumerate(docs) if d["stmt_id"] in self.row_of]
            if rows:
                qv = np.asarray(self.client.embed([query])[0], dtype=np.float32)
                scores = self.vectors[[r for _, r in rows]] @ qv
                order = np.argsort(-scores)[:CANDIDATES]
                rankings.append([(rows[j][0], float(scores[j])) for j in order])
        fused = rrf(*rankings)[:k]
        return [{"ref": f"E{n}", **docs[i]} for n, (i, _) in enumerate(fused, 1)]


class TrajectoryFinder(EvidenceFinder):
    """Mode `trajectory`."""

    def __init__(self, cfg: GraphConfig, client: LLMClient, promises: dict[str, dict],
                 store: str = STORE) -> None:
        super().__init__(cfg, client, store)
        self.promises = promises
        self.embedded = 0

    @lru_cache(maxsize=128)  # noqa: B019
    def _years(self, company: str) -> tuple[int, ...]:
        rows = self.store.con.execute(
            "SELECT DISTINCT year FROM statements WHERE company = ? ORDER BY year", [company]).fetchall()
        return tuple(y for (y,) in rows)

    def _vectors(self, docs: list[dict]) -> np.ndarray:
        """One row per statement: from the sentence store where it has one, embedded now otherwise."""
        known = [self.row_of.get(d["stmt_id"]) for d in docs]
        missing = [i for i, row in enumerate(known) if row is None]
        fresh = self.client.embed([docs[i]["text"][:EMBED_CHARS] for i in missing]) if missing else None
        self.embedded += len(missing)
        dim = self.vectors.shape[1] if self.vectors is not None else fresh.shape[1]
        out = np.zeros((len(docs), dim), dtype=np.float32)
        for i, row in enumerate(known):
            if row is not None:
                out[i] = self.vectors[row]
        if missing:
            out[missing] = fresh
        return out

    @lru_cache(maxsize=12)  # noqa: B019 - a year of one company; promises are visited company by company
    def _year_index(self, company: str, year: int):
        rows = self.store.con.execute(
            "SELECT stmt_id, page, sha256, text FROM statements WHERE company = ? AND year = ? "
            "ORDER BY page, idx", [company, year]).fetchall()
        raw = [{"stmt_id": s, "year": year, "page": page, "file": sha, "text": text}
               for s, page, sha, text in rows]
        position = {r["stmt_id"]: n for n, r in enumerate(raw)}
        docs, seen = [], set()
        for r in raw:
            key = normalise(r["text"])
            if len(r["text"].split()) < MIN_WORDS or key in seen:
                continue
            seen.add(key)
            docs.append(r)
        if not docs:
            return raw, position, docs, None, None
        return raw, position, docs, BM25([d["text"] for d in docs]), self._vectors(docs)

    def window(self, promise: dict) -> list[int]:
        """Report years after the promise's own, up to the year after the deadline."""
        first, last = promise["origin"]["year"], promise["target_year"] + 1
        return [y for y in self._years(promise["company"]) if first < y <= last]

    def find(self, promise: dict, k: int = K_DEADLINE) -> list[dict]:
        years = self.window(promise)
        if not years:
            return []
        deadline = promise["target_year"]
        outcome_year = next((y for y in years if y >= deadline), None)
        query = query_of(promise)
        qv = np.asarray(self.client.embed([query])[0], dtype=np.float32)
        picked: dict[tuple[int, str], dict] = {}

        def add(row: dict, via: str) -> None:
            if row["text"].strip():
                picked.setdefault((row["year"], normalise(row["text"])), {**row, "via": via})

        for year in years:
            raw, position, docs, bm25, vectors = self._year_index(promise["company"], year)
            if not docs:
                continue
            scores = vectors @ qv
            dense = [(int(j), float(scores[j])) for j in np.argsort(-scores)[:CANDIDATES]]
            ranked = [i for i, _ in rrf(bm25.search(query, None, CANDIDATES), dense)]
            budget = k if year == outcome_year else K_AFTER if year > deadline else K_BEFORE
            for i in ranked[:budget]:
                add(docs[i], "retrieved")
            if year == outcome_year:
                for i in ranked[:NEIGHBOURS_OF]:
                    at = position[docs[i]["stmt_id"]]
                    for nb in (at - 1, at + 1):
                        if 0 <= nb < len(raw) and raw[nb]["page"] == docs[i]["page"]:
                            add(raw[nb], "neighbour")

        related = (self.promises.get(r["promise_id"]) for r in promise["related"])
        later = sorted((p for p in related if p and years[0] <= p["origin"]["year"] <= years[-1]),
                       key=lambda p: (p["origin"]["year"], p["target_year"]))
        for other in later[:LINKED]:
            o = other["origin"]
            add({"stmt_id": o["stmt_id"], "year": o["year"], "page": o["page"], "file": o["file"],
                 "text": o["text"]}, "linked")

        def place(e: dict) -> tuple[int, int]:
            return e["year"], self._year_index(promise["company"], e["year"])[1].get(e["stmt_id"], -1)

        ordered = sorted(picked.values(), key=place)
        evidence = [{"ref": f"E{n}", **e} for n, e in enumerate(ordered, 1)]
        for before, after in zip(evidence, evidence[1:], strict=False):
            (year, at), (next_year, next_at) = place(before), place(after)
            if year == next_year and next_at == at + 1:        # one passage, or one row of a table
                after["follows"] = before["ref"]
        return evidence


def where(e: dict) -> str:
    """'2024 report, p.9' and, when the statement comes right after the previous one shown, that too."""
    follows = f", directly follows {e['follows']}" if e.get("follows") else ""
    return f"{e['year']} report, p.{e['page']}{follows}"


def load(path: Path) -> dict[str, list[dict]]:
    """promise_id -> evidence, from an evidence file or from any outcomes file (which embeds it)."""
    rows = (json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line)
    return {r["promise_id"]: r["evidence"] for r in rows}


def build(cfg: GraphConfig, mode: str = "trajectory", client: LLMClient | None = None,
          limit: int | None = None) -> dict:
    """Find the evidence of every checkable promise once and keep it, so judges can be re-run on it."""
    client = client or LLMClient()
    base = out_dir(cfg)
    lines = (base / "promises.jsonl").read_text(encoding="utf-8").splitlines()
    promises = {p["promise_id"]: p for p in (json.loads(line) for line in lines if line)}
    todo = [p for p in promises.values() if p["checkable"]]
    if limit:
        todo = todo[:limit]
    finder = TrajectoryFinder(cfg, client, promises) if mode == "trajectory" else EvidenceFinder(cfg, client)
    found = {}
    for p in sorted(todo, key=lambda p: (p["company"], p["origin"]["year"])):   # keeps the year cache warm
        found[p["promise_id"]] = finder.find(p)
    return _write(cfg, mode, todo, found, {"embedded_on_demand": getattr(finder, "embedded", 0)})


def _write(cfg: GraphConfig, mode: str, todo: list[dict], found: dict[str, list[dict]], extra: dict) -> dict:
    out = evidence_path(cfg, mode)
    with out.open("w", encoding="utf-8") as f:
        for p in todo:
            f.write(json.dumps({"promise_id": p["promise_id"], "evidence": found[p["promise_id"]]},
                               ensure_ascii=False) + "\n")
    sizes = [len(found[p["promise_id"]]) for p in todo]
    stats = {
        "mode": mode,
        "promises": len(todo),
        "statements": sum(sizes),
        "mean_evidence": sum(sizes) / max(1, len(sizes)),
        "max_evidence": max(sizes, default=0),
        "without_evidence": sum(s == 0 for s in sizes),
        "by_source": dict(Counter(e.get("via", "retrieved") for ev in found.values() for e in ev)),
        "report_years_per_promise": (sum(len({e["year"] for e in found[p["promise_id"]]}) for p in todo)
                                     / max(1, len(todo))),
        **extra,
        "out": str(out),
    }
    (out_dir(cfg) / f"evidence_stats.{mode}.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


# --------------------------------------------------------------------------- any system's retriever
K_WINDOW = 20           # statements per promise asked of a retriever; the finder's own budgets stay under it
_IDX = re.compile(r"p(\d+)s(\d+)$")


def promise_query(promise: dict) -> Query:
    """A promise as a `promise_window` query: the window on the query, the record under `meta`."""
    o = promise["origin"]
    return Query(text=query_of(promise), company=promise["company"], aspect=promise["metric"],
                 year_from=o["year"] + 1, year_to=promise["target_year"] + 1, anchor_year=o["year"],
                 target_text=o.get("text") or o.get("target_text"),
                 condition=EvidenceCondition.PROMISE_WINDOW, meta={"promise": promise})


def promise_of(query: Query) -> dict:
    """The promise a `promise_window` query carries, or one rebuilt from the query's fields."""
    carried = query.meta.get("promise") if query.meta else None
    if isinstance(carried, dict):
        return carried
    origin_year = query.anchor_year if query.anchor_year is not None else (query.year_from or 1) - 1
    return {"promise_id": None, "company": query.company, "metric": query.aspect or query.text,
            "target_year": (query.year_to or 0) - 1, "related": [],
            "origin": {"year": origin_year, "target_text": query.target_text or query.text}}


def spans_of(evidence: list[dict], company: str) -> list[EvidenceSpan]:
    """The finder's rows as evidence spans; `why` keeps how each was reached."""
    return [EvidenceSpan(statement_id=e["stmt_id"], text=e["text"], company=company, year=e["year"],
                         page=e.get("page"), file=e.get("file"), score=0.0,
                         why=f"trajectory:{e.get('via', 'retrieved')}") for e in evidence]


def _position(stmt_id: str | None) -> int:
    m = _IDX.search(stmt_id or "")
    return int(m.group(2)) if m else -1


def evidence_of(spans: list[EvidenceSpan]) -> list[dict]:
    """Spans back into the rows the judge and the sheets read: report order, E-tags, and `follows` where
    one statement comes right after the previous one on the same page."""
    rows = sorted(({"stmt_id": s.statement_id, "year": s.year, "page": s.page, "file": s.file,
                    "text": s.text, "via": s.why} for s in spans),
                  key=lambda r: (r["year"], r["file"] or "", r["page"] or 0, _position(r["stmt_id"])))
    out = [{"ref": f"E{n}", **r} for n, r in enumerate(rows, 1)]
    for before, after in zip(out, out[1:], strict=False):
        if (before["year"], before["file"], before["page"]) == (after["year"], after["file"], after["page"]) \
                and _position(after["stmt_id"]) == _position(before["stmt_id"]) + 1:
            after["follows"] = before["ref"]
    return out


def build_from_system(cfg: GraphConfig, system, k: int = K_WINDOW, limit: int | None = None) -> dict:
    """Evidence for every checkable promise from a registered system's retriever under `promise_window`,
    written as `evidence.<system>.jsonl`, so the shared judge can be run on it like on the finder's."""
    if isinstance(system, str):
        from gw_common.registry import load as load_system

        system = load_system(system)
    if EvidenceCondition.PROMISE_WINDOW not in system.supported_conditions():
        raise ValueError(f"{system.name} does not support the promise_window condition")
    retriever = system.retriever()
    if retriever is None:
        raise ValueError(f"{system.name} has no retriever")
    base = out_dir(cfg)
    lines = (base / "promises.jsonl").read_text(encoding="utf-8").splitlines()
    promises = [json.loads(line) for line in lines if line]
    todo = [p for p in promises if p["checkable"]]
    if limit:
        todo = todo[:limit]
    found = {}
    for p in sorted(todo, key=lambda p: (p["company"], p["origin"]["year"])):
        found[p["promise_id"]] = evidence_of(retriever.retrieve(promise_query(p), k=k))
    extra = {"system": system.name, "k": k}
    if hasattr(retriever, "describe"):
        extra["retriever"] = retriever.describe()
    return _write(cfg, system.name, todo, found, extra)
