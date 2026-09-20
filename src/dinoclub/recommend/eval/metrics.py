"""Standard top-k ranking metrics, plus two that matter for a small catalog.

With 28 items and 8 personas, a recommender can score well on recall while
recommending the same six crowd-pleasers to everyone. `coverage` and
`personalization` are there to catch exactly that failure.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Set


def hit_rate(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """1.0 if any of the top k is relevant."""
    rel = set(relevant)
    return 1.0 if any(r in rel for r in recommended[:k]) else 0.0


def recall_at_k(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    hits = sum(1 for r in recommended[:k] if r in rel)
    return hits / min(len(rel), k)


def precision_at_k(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    if k <= 0:
        return 0.0
    rel = set(relevant)
    return sum(1 for r in recommended[:k] if r in rel) / k


def ndcg_at_k(recommended: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Binary-relevance NDCG. Ideal DCG assumes all relevant items ranked first."""
    rel = set(relevant)
    if not rel:
        return 0.0
    dcg = sum(
        1.0 / math.log2(i + 2) for i, r in enumerate(recommended[:k]) if r in rel
    )
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(rel), k)))
    return dcg / ideal if ideal > 0 else 0.0


def coverage(all_recommendations: Sequence[Sequence[str]], catalog_size: int) -> float:
    """Share of the catalog that appears in *anybody's* list."""
    if catalog_size <= 0:
        return 0.0
    seen: Set[str] = set()
    for recs in all_recommendations:
        seen.update(recs)
    return len(seen) / catalog_size


def personalization(all_recommendations: Sequence[Sequence[str]]) -> float:
    """Mean pairwise dissimilarity between users' lists, in [0, 1].

    0.0 means everyone got an identical list; 1.0 means no two users shared a
    single item. A high-accuracy recommender with near-zero personalization is
    just a popularity chart wearing a costume.
    """
    lists = [set(r) for r in all_recommendations if r]
    if len(lists) < 2:
        return 0.0
    total = 0.0
    pairs = 0
    for i, a in enumerate(lists):
        for b in lists[i + 1 :]:
            union = a | b
            overlap = len(a & b) / len(union) if union else 0.0
            total += 1.0 - overlap
            pairs += 1
    return total / pairs


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def summarize(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    """Average a list of per-user metric dicts."""
    if not rows:
        return {}
    keys: List[str] = list(rows[0].keys())
    return {k: mean(r[k] for r in rows if k in r) for k in keys}
