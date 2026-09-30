"""Hierarchical agglomerative clustering of aspect phrases, following CESI (WWW 2018, section 6):

- cosine similarity over phrase embeddings;
- **complete linkage**, which CESI prefers because it "gives smaller sized clusters, compared to
  single and average linkage criterion", appropriate when true clusters are small;
- a distance threshold tuned on held-out validation data, not fixed a priori;
- the representative of each cluster is the member closest to the cluster mean.

[project] additions: clustering is blocked by A3CG category, so two phrases in different categories
can never merge; and it runs on morphologically normalised keys, so exact duplicates are collapsed
before the O(n^2) step.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist


@dataclass(slots=True)
class Phrase:
    key: str            # morph-normalised key, the unit being clustered
    category: str
    weight: int = 1     # number of mentions behind the key, used to pick a readable canonical form
    display: str = ""   # a surface form to show for the key


def hac_clusters(
    phrases: list[Phrase], vectors: np.ndarray, similarity_threshold: float
) -> list[list[int]]:
    """Indices of `phrases` grouped into clusters, blocked by category."""
    if not 0.0 < similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be in (0, 1]")
    by_cat: dict[str, list[int]] = {}
    for i, p in enumerate(phrases):
        by_cat.setdefault(p.category, []).append(i)

    clusters: list[list[int]] = []
    for _, idx in sorted(by_cat.items()):
        if len(idx) == 1:
            clusters.append(idx)
            continue
        dist = pdist(vectors[idx], metric="cosine")
        np.clip(dist, 0.0, 2.0, out=dist)
        tree = linkage(dist, method="complete")
        labels = fcluster(tree, t=1.0 - similarity_threshold, criterion="distance")
        groups: dict[int, list[int]] = {}
        for local, lab in enumerate(labels):
            groups.setdefault(int(lab), []).append(idx[local])
        clusters.extend(groups.values())
    return clusters


def representative(members: list[int], phrases: list[Phrase], vectors: np.ndarray) -> int:
    """CESI: the member closest to the mean embedding; ties go to the most-mentioned phrase."""
    if len(members) == 1:
        return members[0]
    mean = vectors[members].mean(axis=0)
    sims = vectors[members] @ (mean / max(np.linalg.norm(mean), 1e-12))
    order = sorted(
        range(len(members)), key=lambda j: (-round(float(sims[j]), 6), -phrases[members[j]].weight)
    )
    return members[order[0]]
