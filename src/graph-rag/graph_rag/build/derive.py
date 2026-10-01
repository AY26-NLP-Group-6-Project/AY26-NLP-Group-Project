"""Stage 3: derived edges.

`follows_up` links consecutive years for the same (company, aspect). These edges are the product of
the graph, not an input: they are what a cross-year query traverses and what the trajectory task
is scored against.
"""

from __future__ import annotations

import json
from collections import defaultdict

from graph_rag.config import GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore


def run(cfg: GraphConfig, store: DuckDBGraphStore, verbose: bool = True) -> dict:
    store.clear("follows_up")
    rows = store.con.execute(
        """
        SELECT s.company, COALESCE(c.canon_id, m.aspect_id) AS gid, s.year, s.stmt_id, s.norm_text
        FROM mentions m JOIN statements s USING (stmt_id)
        LEFT JOIN aspect_canon c ON c.aspect_id = m.aspect_id
        ORDER BY s.company, gid, s.year, s.stmt_id
        """
    ).fetchall()

    by_group: dict[tuple[str, str], dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    norm_of: dict[str, str] = {}
    for company, aspect_id, year, stmt_id, norm_text in rows:
        by_group[(company, aspect_id)][year].append(stmt_id)
        norm_of[stmt_id] = norm_text

    edges: list[tuple] = []
    for (company, aspect_id), by_year in by_group.items():
        years = sorted(by_year)
        for earlier, later in zip(years, years[1:], strict=False):
            # one edge per consecutive year pair, anchored on the first statement of each year:
            # enough to walk a timeline without exploding the edge count
            a, b = by_year[earlier][0], by_year[later][0]
            # Templated reports copy whole paragraphs year to year. An edge between two identical
            # sentences is not progress on the aspect, it is unchanged boilerplate — flag it so the
            # trajectory task and the greenwashing read can treat it differently.
            edges.append((a, b, aspect_id, company, later - earlier, norm_of[a] == norm_of[b]))
    store.insert_many("follows_up", edges, 6)

    verbatim = sum(1 for e in edges if e[5])
    canon = store.con.execute("SELECT any_value(method), any_value(threshold) FROM aspect_canon").fetchone()
    stats = {
        "grouping": {"method": canon[0] or "raw aspect_id", "threshold": canon[1]},
        "groups": len(by_group),
        "follows_up_edges": len(edges),
        "verbatim_repeat_edges": verbatim,
        "verbatim_repeat_share": round(verbatim / len(edges), 4) if edges else 0.0,
    }
    (cfg.out_dir / "derive_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    if verbose:
        print(f"  {len(edges)} follows_up edges over {len(by_group)} (company, aspect) groups; "
              f"{verbatim} link verbatim repeats")
    return stats
