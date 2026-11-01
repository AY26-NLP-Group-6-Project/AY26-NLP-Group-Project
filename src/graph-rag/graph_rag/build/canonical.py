"""Stage 2b: aspect canonicalisation.

Three methods, all written to the same `aspect_canon` table so derive/chains/subgraph are unchanged:

- `exact`: identity on the normalised aspect key (the first build's behaviour, kept as the reference arm);
- `morph`: morphological normalisation within category (the CESI "Morph Norm" baseline);
- `hac`:   morph keys, then phrase embeddings + complete-linkage HAC within category (CESI section 6).

The threshold for `hac` is tuned on the validation pools of the gold clustering (`gw-graph
canon-tune`) and passed in explicitly; nothing is merged by an untuned default in a reported build.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

from graph_rag.canonical.cluster import Phrase, hac_clusters, representative
from graph_rag.canonical.normalise import morph_key
from graph_rag.config import GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

METHODS = ("exact", "morph", "hac")


def load_phrases(store: DuckDBGraphStore) -> tuple[list[Phrase], dict[str, list[str]], dict[str, str]]:
    """Unique (category, morph key) phrases, the aspect ids behind each, and one example sentence."""
    rows = store.con.execute(
        """
        SELECT a.aspect_id, a.canonical, a.category, count(m.stmt_id) AS n,
               any_value(s.text) AS example
        FROM aspects a
        LEFT JOIN mentions m USING (aspect_id)
        LEFT JOIN statements s USING (stmt_id)
        GROUP BY a.aspect_id, a.canonical, a.category
        """
    ).fetchall()
    weight: Counter[tuple[str, str]] = Counter()
    display: dict[tuple[str, str], tuple[int, str]] = {}
    members: dict[str, list[str]] = defaultdict(list)
    examples: dict[str, str] = {}
    for aspect_id, surface, category, n, example in rows:
        key = morph_key(surface) or aspect_id
        cat = category or "uncategorised"
        k = (cat, key)
        weight[k] += int(n)
        if k not in display or int(n) > display[k][0]:
            display[k] = (int(n), surface)
        fid = f"{cat}|{key}"
        members[fid].append(aspect_id)
        if example and fid not in examples:
            examples[fid] = example[:240]
    phrases = [Phrase(key=k[1], category=k[0], weight=w, display=display[k][1])
               for k, w in sorted(weight.items())]
    return phrases, members, examples


def run(
    cfg: GraphConfig,
    store: DuckDBGraphStore,
    verbose: bool = True,
    method: str = "exact",
    threshold: float | None = None,
) -> dict:
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    store.clear("aspect_canon")
    phrases, members, _ = load_phrases(store)
    model_name = None
    rows: list[tuple] = []

    if method == "exact":
        for aspect_ids in members.values():
            for aid in aspect_ids:
                rows.append((aid, aid, aid, "exact", None, None))
    else:
        if method == "morph":
            groups = [[i] for i in range(len(phrases))]
            reps = {tuple(g): g[0] for g in groups}
        else:
            if threshold is None:
                raise ValueError("hac needs an explicit --threshold (tune it with canon-tune first)")
            from graph_rag.canonical.embed import PhraseEmbedder

            embedder = PhraseEmbedder()
            model_name = embedder.label
            vectors = embedder.embed([p.key for p in phrases])
            groups = hac_clusters(phrases, vectors, threshold)
            reps = {tuple(g): representative(g, phrases, vectors) for g in groups}
        for n, g in enumerate(sorted(groups, key=lambda g: (phrases[g[0]].category, phrases[g[0]].key))):
            rep = phrases[reps[tuple(g)]]
            canon_id = f"{rep.category}|c{n:05d}"
            for i in g:
                for aid in members[f"{phrases[i].category}|{phrases[i].key}"]:
                    rows.append((aid, canon_id, rep.display or rep.key, method, threshold, model_name))

    store.insert_many("aspect_canon", rows, 6)
    n_canon = len({r[1] for r in rows})
    sizes = Counter(Counter(r[1] for r in rows).values())
    stats = {
        "method": method,
        "threshold": threshold,
        "model": model_name,
        "aspect_ids": len(rows),
        "morph_phrases": len(phrases),
        "canonical_aspects": n_canon,
        "cluster_size_histogram": dict(sorted(sizes.items())[:10]),
    }
    (cfg.out_dir / "canonical_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    if verbose:
        print(f"  {method}: {len(rows)} aspect ids -> {n_canon} canonical aspects "
              f"(from {len(phrases)} morph phrases)")
    return stats
