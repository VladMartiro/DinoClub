"""The experiment runner: `python -m dinoclub.recommend.eval.harness`.

Two questions this answers:

  1. Does the quiz recover the persona a user was drawn from, and how fast?
  2. Does the recommender surface the movies that user would actually rank
     highest, given only their quiz answers?

The adaptive-vs-static comparison at matched quiz length is the headline
number, because it isolates the value of the question-selection policy from
everything else.
"""

from __future__ import annotations

import argparse
import json
from typing import Dict, List, Optional, Sequence

from ..catalog import Catalog
from ..personas import PersonaSet
from ..survey import QuizBank
from ..recommend import recommend
from .metrics import coverage, ndcg_at_k, personalization, recall_at_k, summarize
from .simulate import sample_users, take_quiz


def run_condition(
    *,
    catalog: Catalog,
    personas: PersonaSet,
    bank: QuizBank,
    strategy: str,
    n_questions: int,
    n_users: int,
    k: int = 5,
    relevant_m: int = 5,
    seed: int = 7,
) -> Dict[str, float]:
    users = sample_users(personas, n_users, seed=seed)
    rows: List[Dict[str, float]] = []
    all_lists: List[List[str]] = []

    for i, user in enumerate(users):
        session = take_quiz(
            user, bank, personas, strategy=strategy, max_questions=n_questions, seed=seed + i
        )
        ranked = personas.ranked(session.profile)
        predicted = [p.id for p, _ in ranked]
        recs = [r.movie.id for r in recommend(session.profile, catalog, k=k)]
        all_lists.append(recs)
        relevant = user.relevant_movies(catalog, relevant_m)
        rows.append(
            {
                "persona_acc@1": 1.0 if predicted[0] == user.persona_id else 0.0,
                "persona_acc@3": 1.0 if user.persona_id in predicted[:3] else 0.0,
                "persona_conf": ranked[0][1],
                "recall@5": recall_at_k(recs, relevant, k),
                "ndcg@5": ndcg_at_k(recs, relevant, k),
            }
        )

    out = summarize(rows)
    out["coverage"] = coverage(all_lists, len(catalog))
    out["personalization"] = personalization(all_lists)
    out["n_questions"] = float(n_questions)
    return out


def random_baseline(
    *, catalog: Catalog, personas: PersonaSet, n_users: int, k: int = 5,
    relevant_m: int = 5, seed: int = 7,
) -> Dict[str, float]:
    """What you get by shuffling the catalog. Every number above this line has
    to beat it or the model is doing nothing."""
    import random

    rng = random.Random(seed)
    users = sample_users(personas, n_users, seed=seed)
    rows, all_lists = [], []
    for user in users:
        recs = rng.sample(catalog.ids, k)
        all_lists.append(recs)
        relevant = user.relevant_movies(catalog, relevant_m)
        rows.append(
            {
                "persona_acc@1": 1.0 / len(personas),
                "persona_acc@3": 3.0 / len(personas),
                "persona_conf": 1.0 / len(personas),
                "recall@5": recall_at_k(recs, relevant, k),
                "ndcg@5": ndcg_at_k(recs, relevant, k),
            }
        )
    out = summarize(rows)
    out["coverage"] = coverage(all_lists, len(catalog))
    out["personalization"] = personalization(all_lists)
    out["n_questions"] = 0.0
    return out


COLUMNS = [
    ("n_questions", "Qs", "{:>3.0f}"),
    ("persona_acc@1", "acc@1", "{:>6.3f}"),
    ("persona_acc@3", "acc@3", "{:>6.3f}"),
    ("persona_conf", "conf", "{:>6.3f}"),
    ("recall@5", "rec@5", "{:>6.3f}"),
    ("ndcg@5", "ndcg@5", "{:>7.3f}"),
    ("coverage", "cover", "{:>6.3f}"),
    ("personalization", "person", "{:>7.3f}"),
]


def _print_table(title: str, rows: Sequence[Dict[str, float]], labels: Sequence[str]) -> None:
    width = max(len(l) for l in labels) if labels else 0
    header = " " * (width + 2) + "  ".join(h.rjust(len(f.format(0))) for _, h, f in COLUMNS)
    print("\n{}".format(title))
    print("-" * len(header))
    print(header)
    for label, row in zip(labels, rows):
        cells = "  ".join(f.format(row.get(key, 0.0)) for key, _, f in COLUMNS)
        print("{}  {}".format(label.ljust(width), cells))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline evaluation for the movie recommender.")
    parser.add_argument("--users", type=int, default=240, help="simulated users per condition")
    parser.add_argument("--max-questions", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args(argv)

    catalog = Catalog.load()
    personas = PersonaSet.load(catalog)
    bank = QuizBank.load(catalog.space)

    print("catalog: {} movies | personas: {} | questions: {}".format(
        len(catalog), len(personas), len(bank)))
    print("persona anchor separation: mean {:.3f}, closest pair {} / {} at {:.3f}".format(
        personas.separation(), *personas.closest_pair()))

    lengths = list(range(1, min(args.max_questions, len(bank)) + 1))
    results = {"adaptive": [], "static": []}
    for strategy in ("adaptive", "static"):
        for n in lengths:
            results[strategy].append(
                run_condition(
                    catalog=catalog, personas=personas, bank=bank,
                    strategy=strategy, n_questions=n, n_users=args.users, seed=args.seed,
                )
            )

    baseline = random_baseline(
        catalog=catalog, personas=personas, n_users=args.users, seed=args.seed
    )

    if args.json:
        print(json.dumps({"baseline": baseline, **results}, indent=2))
        return 0

    _print_table("random baseline", [baseline], ["random"])
    _print_table(
        "adaptive question selection (greedy expected information gain)",
        results["adaptive"], ["adaptive"] * len(lengths),
    )
    _print_table("static question order (ablation)", results["static"], ["static"] * len(lengths))

    print("\nadaptive minus static, by quiz length")
    print("-" * 44)
    for n, a, s in zip(lengths, results["adaptive"], results["static"]):
        print("  {} question(s): acc@1 {:+.3f}   ndcg@5 {:+.3f}".format(
            n, a["persona_acc@1"] - s["persona_acc@1"], a["ndcg@5"] - s["ndcg@5"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
