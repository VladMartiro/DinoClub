#!/usr/bin/env python3
"""Refit movie axis values from real ratings, anchored to the hand-authored
prior and to users' quiz answers.

This is the bridge between "the catalog is one person's opinion" and "the
catalog is fit to what the club actually thinks" -- step two of the
progression in `docs/axes.md`.

## The model

    rating_hat(u, i) = mu + b_u + b_i + <p_u, q_i>

`q_i` is movie i's position in axis space (centered at 0.5, so the dot product
is signed). `p_u` is the user's taste in that same space.

## Why p_u is *not* free

The obvious move is to fit `p_u` and `q_i` jointly by alternating least
squares. That does not work here, and the failure is instructive: with both
sides free, the model is only identified up to an invertible linear transform.
Any rotation of `q` can be undone by the matching rotation of `p` at identical
loss, so there is no reason the third fitted coordinate means `camp` rather
than some blend of camp, retro and grit. Every downstream component -- the
quiz evidence, the persona anchors, the explanations -- depends on those
coordinates keeping their meaning.

Measured, on synthetic data with a known ground truth: with `p` free, loosening
the prior made axis recovery monotonically *worse* (-66% at the weakest
regularization). The prior was the only thing holding the coordinates in
place, and "improvement" was just "refused to move".

So we fix `p_u` to the user's quiz-derived profile. We know it: the site
already collected their answers. That makes the item fit an ordinary ridge
regression with a known design matrix, identified and convex. Only `q` and the
biases are free.

The ridge on `q` shrinks toward the hand-authored prior rather than toward
zero, so a movie with three ratings barely moves and a movie with forty moves
a lot -- the club-scale data problem, handled with one interpretable knob.

## Usage

    python scripts/refit_axes.py --self-test
    python scripts/refit_axes.py --ratings data/ratings.csv \
        --answers data/answers.csv --out catalog.refit.json

Requires the `learn` extra:  pip install -e ".[learn]"
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    import numpy as np
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("refit_axes needs numpy:  pip install -e '.[learn]'")

from dinoclub.recommend.catalog import Catalog  # noqa: E402
from dinoclub.recommend.profile import Profile  # noqa: E402
from dinoclub.recommend.survey import QuizBank  # noqa: E402

Rating = Tuple[str, str, float]
UserVectors = Dict[str, Dict[str, float]]

#: Ridge strength on item vectors, shrinking toward the hand-authored prior.
#: 4.0 sits at the bottom of the recovery curve across every data scale in
#: --self-test; re-check it once real ratings exist.
ITEM_LAMBDA = 4.0
BIAS_LAMBDA = 6.0
ITERATIONS = 15


def load_ratings(path: Path, catalog: Catalog) -> List[Rating]:
    """Read `movie_id,user_id,rating`, dropping rows for unknown movies."""
    out: List[Rating] = []
    skipped = 0
    with Path(path).open() as fh:
        for row in csv.DictReader(fh):
            movie_id = row["movie_id"].strip()
            if movie_id not in catalog:
                skipped += 1
                continue
            out.append((movie_id, row["user_id"].strip(), float(row["rating"])))
    if skipped:
        print("  dropped {} rating(s) for movies not in the catalog".format(skipped))
    return out


def load_user_vectors(path: Path, catalog: Catalog) -> UserVectors:
    """Rebuild taste profiles by replaying stored quiz answers.

    Expects `user_id,question_id,option_id` -- the same option ids the site
    stores. Replaying through `QuizBank` rather than storing vectors directly
    means a change to the question bank's calibration propagates to old
    responses instead of silently disagreeing with them.
    """
    bank = QuizBank.load(catalog.space)
    by_user: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    with Path(path).open() as fh:
        for row in csv.DictReader(fh):
            by_user[row["user_id"].strip()].append(
                (row["question_id"].strip(), row["option_id"].strip())
            )

    vectors: UserVectors = {}
    for user_id, answers in by_user.items():
        profile = Profile.empty(catalog.space)
        for question_id, option_id in answers:
            try:
                option = bank[question_id][option_id]
            except KeyError:
                print("  skipping unknown answer {}/{}".format(question_id, option_id))
                continue
            profile.observe_all(option.as_evidence(source=question_id))
        vectors[user_id] = profile.vector
    return vectors


def refit(
    ratings: Sequence[Rating],
    user_vectors: UserVectors,
    catalog: Catalog,
    *,
    iterations: int = ITERATIONS,
    item_lambda: float = ITEM_LAMBDA,
    bias_lambda: float = BIAS_LAMBDA,
) -> Dict[str, Dict[str, float]]:
    """Alternate between biases and item vectors. Returns {movie_id: {axis: value}}."""
    keys = catalog.space.keys
    dim = len(keys)

    usable = [r for r in ratings if r[1] in user_vectors]
    dropped = len(ratings) - len(usable)
    if dropped:
        print("  dropped {} rating(s) from users with no quiz answers".format(dropped))
    if not usable:
        raise ValueError("no ratings from users with quiz profiles; nothing to fit")

    prior = {m.id: np.array([m.axes[k] - 0.5 for k in keys]) for m in catalog}
    p = {uid: np.array([v[k] - 0.5 for k in keys]) for uid, v in user_vectors.items()}

    mu = float(np.mean([r[2] for r in usable]))
    b_u: Dict[str, float] = defaultdict(float)
    b_i: Dict[str, float] = defaultdict(float)
    by_user: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    by_item: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for movie_id, user_id, rating in usable:
        by_user[user_id].append((movie_id, rating))
        by_item[movie_id].append((user_id, rating))

    q = {m.id: prior[m.id].copy() for m in catalog}
    eye = np.eye(dim)

    for _ in range(iterations):
        for user_id, rows in by_user.items():
            resid = [rt - mu - b_i[mid] - float(p[user_id] @ q[mid]) for mid, rt in rows]
            b_u[user_id] = sum(resid) / (len(rows) + bias_lambda)
        for movie_id, rows in by_item.items():
            resid = [rt - mu - b_u[uid] - float(p[uid] @ q[movie_id]) for uid, rt in rows]
            b_i[movie_id] = sum(resid) / (len(rows) + bias_lambda)
        for movie_id, rows in by_item.items():
            design = np.array([p[uid] for uid, _ in rows])
            target = np.array([rt - mu - b_u[uid] - b_i[movie_id] for uid, rt in rows])
            gram = design.T @ design + item_lambda * eye
            rhs = design.T @ target + item_lambda * prior[movie_id]
            q[movie_id] = np.linalg.solve(gram, rhs)

    # Back into [0, 1]. Clipping is a genuine approximation -- the fit has no
    # notion of the box constraint, so a strongly-moved axis is truncated.
    return {
        mid: {k: round(float(np.clip(vec[j] + 0.5, 0.0, 1.0)), 4) for j, k in enumerate(keys)}
        for mid, vec in q.items()
    }


def _mean_axis_error(a: UserVectors, b: UserVectors, keys: Sequence[str]) -> float:
    errs = [abs(a[mid][k] - b[mid][k]) for mid in a for k in keys]
    return sum(errs) / len(errs)


def _synthetic(
    catalog: Catalog, n_users: int, per_user: int, noise: float, seed: int
) -> Tuple[List[Rating], UserVectors, UserVectors]:
    """Ratings drawn from a known perturbation of the catalog, using the same
    functional form the model assumes. Returns (ratings, user_vectors, truth)."""
    rng = random.Random(seed)
    keys = catalog.space.keys
    truth = {
        m.id: {k: min(1.0, max(0.0, m.axes[k] + rng.gauss(0.0, 0.18))) for k in keys}
        for m in catalog
    }
    users: UserVectors = {}
    ratings: List[Rating] = []
    for u in range(n_users):
        user_id = "sim-{:04d}".format(u)
        taste = {k: rng.random() for k in keys}
        users[user_id] = taste
        for movie_id in rng.sample(catalog.ids, min(per_user, len(catalog))):
            affinity = sum((taste[k] - 0.5) * (truth[movie_id][k] - 0.5) for k in keys)
            score = 3.0 + affinity + rng.gauss(0.0, noise)
            ratings.append((movie_id, user_id, min(5.0, max(1.0, score))))
    return ratings, users, truth


SCALES = [
    (40, 10, "club scale today"),
    (120, 14, "a few semesters in"),
    (400, 20, "if this outgrows the club"),
]


def self_test(seed: int = 3) -> int:
    """Does the fit recover axes we perturbed on purpose, at realistic scales?

    Passing means the refit lands closer to the truth than the prior it
    started from. Note that the synthetic users' taste vectors are handed to
    the fit exactly, whereas real quiz profiles are noisy estimates -- so
    these numbers are an upper bound on what real data will do.
    """
    catalog = Catalog.load()
    keys = catalog.space.keys
    prior = {m.id: dict(m.axes) for m in catalog}
    print("axis recovery vs. the hand-authored prior (lambda={})\n".format(ITEM_LAMBDA))
    print("  {:<26} {:>7} {:>9} {:>9} {:>9}".format(
        "scale", "rows", "prior", "refit", "change"))
    print("  " + "-" * 64)

    passes = 0
    for n_users, per_user, label in SCALES:
        ratings, users, truth = _synthetic(catalog, n_users, per_user, 0.35, seed)
        fitted = refit(ratings, users, catalog)
        before = _mean_axis_error(prior, truth, keys)
        after = _mean_axis_error(fitted, truth, keys)
        change = (before - after) / before if before else 0.0
        print("  {:<26} {:>7} {:>9.4f} {:>9.4f} {:>+8.1%}".format(
            label, len(ratings), before, after, change))
        passes += 1 if after < before else 0

    print()
    if passes == len(SCALES):
        print("PASS -- refitting moves the catalog toward the truth at every scale.")
        print("        The gain is small at club scale and grows with data, which is")
        print("        the expected shape: the prior is doing most of the work today.")
        return 0
    print("FAIL -- refitting made the catalog worse at {}/{} scales."
          .format(len(SCALES) - passes, len(SCALES)))
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ratings", type=Path, help="CSV: movie_id,user_id,rating")
    parser.add_argument("--answers", type=Path,
                        help="CSV: user_id,question_id,option_id (quiz responses)")
    parser.add_argument("--out", type=Path, help="where to write the refit catalog")
    parser.add_argument("--self-test", action="store_true",
                        help="validate the fit on synthetic data with known truth")
    parser.add_argument("--item-lambda", type=float, default=ITEM_LAMBDA)
    parser.add_argument("--min-ratings", type=int, default=200,
                        help="refuse to fit on fewer rows than this")
    parser.add_argument("--seed", type=int, default=3)
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test(seed=args.seed)
    if not args.ratings or not args.answers:
        parser.error("pass both --ratings and --answers, or --self-test to try it "
                     "without data")

    catalog = Catalog.load()
    ratings = load_ratings(args.ratings, catalog)
    user_vectors = load_user_vectors(args.answers, catalog)
    print("loaded {} ratings from {} users; {} quiz profiles".format(
        len(ratings), len({u for _, u, _ in ratings}), len(user_vectors)))

    if len(ratings) < args.min_ratings:
        print("\nOnly {} ratings. Below --min-ratings ({}) the fit mostly reproduces "
              "the prior with extra noise -- see --self-test for how the gain scales. "
              "Keep collecting.".format(len(ratings), args.min_ratings))
        return 1

    fitted = refit(ratings, user_vectors, catalog, item_lambda=args.item_lambda)
    moved = sorted(
        ((sum(abs(fitted[m.id][k] - m.axes[k]) for k in catalog.space.keys), m.display)
         for m in catalog),
        reverse=True,
    )[:5]
    print("\nmovies that moved most (total axis shift):")
    for delta, title in moved:
        print("  {:.3f}  {}".format(delta, title))

    payload = {
        "schema_version": 1,
        "note": "Refit from {} ratings by scripts/refit_axes.py. Review the diff "
                "before replacing src/dinoclub/recommend/data/catalog.json.".format(len(ratings)),
        "movies": [
            {"id": m.id, "title": m.title, "year": m.year, "kind": m.kind,
             "axes": fitted[m.id]}
            for m in catalog
        ],
    }
    out = args.out or REPO_ROOT / "catalog.refit.json"
    out.write_text(json.dumps(payload, indent=2))
    print("\nwrote {}".format(out))
    print("This file is a proposal, not a drop-in. Read the diff -- an axis that "
          "moved a long way usually means a miscalibrated question, not a "
          "misjudged movie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
