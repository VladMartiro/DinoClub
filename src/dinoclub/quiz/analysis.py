"""Audit the quiz: `python -m dinoclub.quiz.analysis`.

A personality quiz has no ground truth, so it cannot be scored for accuracy.
It can still be wrong in ways that are perfectly measurable, and this is what
stands in for an eval harness:

  * Is every dinosaur reachable? A result nobody can ever get is a bug.
  * Is the win distribution anywhere near even, or does one dinosaur
    swallow half the users?
  * Does normalisation actually change any of that, or is it ceremony?

Because there are only 4^10 ways to answer, these are not estimates. The
audit enumerates the entire answer space by default, so "this dinosaur is
unreachable" is a proof rather than a sample that missed it.
"""

from __future__ import annotations

import argparse
import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

from .dinosaurs import DinosaurSet
from .questions import QuestionBank
from .scoring import axis_scales
from .traits import TraitSpace


def _make_matcher(bank: QuestionBank, dinosaurs: DinosaurSet, *,
                  apply_normalisation: bool, spread: float = 1.0):
    """Returns (effects, winner_fn). `winner_fn(totals, gain)` gives the
    winning dinosaur id with the user vector multiplied by `gain`."""
    keys = bank.space.keys
    effects = [[tuple(o.effect(k) for k in keys) for o in q.options] for q in bank]
    calibrated = axis_scales(bank, dinosaurs, spread=spread)
    scale = tuple(calibrated[k] if apply_normalisation else 1.0 for k in keys)

    dino_ids = dinosaurs.ids
    dino_vecs = [tuple(dinosaurs[d].traits[k] for k in keys) for d in dino_ids]
    dino_sq = [sum(c * c for c in v) for v in dino_vecs]
    lo, hi = bank.space.min, bank.space.max

    def winner(totals, gain: float = 1.0) -> str:
        # The raw path deliberately does not clamp: clamping would itself be a
        # crude normalisation, and the point is to measure the naive pipeline
        # exactly as written.
        if apply_normalisation:
            u = [min(hi, max(lo, totals[i] * scale[i] * gain)) for i in range(len(keys))]
        else:
            u = [totals[i] * gain for i in range(len(keys))]
        top_id, top_score = None, None
        for idx, vec in enumerate(dino_vecs):
            # maximise 2(u.v) - |v|^2  ==  minimise |u - v|^2
            score = 2.0 * sum(u[i] * vec[i] for i in range(len(u))) - dino_sq[idx]
            if top_score is None or score > top_score:
                top_score, top_id = score, dino_ids[idx]
        return top_id

    return effects, winner


def _walk(effects, n_axes: int, visit, sample: Optional[int] = None, seed: int = 0) -> None:
    """Call `visit(totals)` for every answer set, or for `sample` random ones."""
    if sample is not None:
        rng = random.Random(seed)
        for _ in range(sample):
            totals = [0.0] * n_axes
            for q_effects in effects:
                chosen = q_effects[rng.randrange(len(q_effects))]
                for i, delta in enumerate(chosen):
                    totals[i] += delta
            visit(totals)
        return

    def recurse(depth: int, totals: List[float]) -> None:
        if depth == len(effects):
            visit(totals)
            return
        for chosen in effects[depth]:
            for i, delta in enumerate(chosen):
                totals[i] += delta
            recurse(depth + 1, totals)
            for i, delta in enumerate(chosen):
                totals[i] -= delta

    recurse(0, [0.0] * n_axes)


def magnitude_sensitivity(
    bank: QuestionBank,
    dinosaurs: DinosaurSet,
    *,
    apply_normalisation: bool,
    gain: float = 2.0,
    spread: float = 1.0,
    sample: Optional[int] = None,
    seed: int = 0,
) -> float:
    """How often does answering *more strongly* change the answer?

    This is the property raw totals quietly destroy, and the one evenness
    cannot see. Matching minimises |u|^2 - 2(u.v) + |v|^2 with |u|^2 constant
    across candidates, so when |u| is large relative to |v| the |v|^2 term
    vanishes and only the direction of u survives. Two users who lean the same
    way then get the same dinosaur no matter how hard either of them leaned.

    We measure it by comparing each answer set's winner against the winner for
    the same answers scaled by `gain`. A system that respects magnitude will
    sometimes disagree with itself; one that has thrown magnitude away never
    will.
    """
    effects, winner = _make_matcher(bank, dinosaurs,
                                    apply_normalisation=apply_normalisation, spread=spread)
    counts = [0, 0]

    def visit(totals):
        counts[0] += 1
        if winner(totals, 1.0) != winner(totals, gain):
            counts[1] += 1

    _walk(effects, len(bank.space.keys), visit, sample=sample, seed=seed)
    return counts[1] / counts[0] if counts[0] else 0.0


def _tabulate(
    bank: QuestionBank,
    dinosaurs: DinosaurSet,
    *,
    apply_normalisation: bool,
    spread: float = 1.0,
    sample: Optional[int] = None,
    seed: int = 0,
) -> Dict[str, int]:
    """Win counts over the answer space, exhaustive unless `sample` is given."""
    effects, winner = _make_matcher(bank, dinosaurs,
                                    apply_normalisation=apply_normalisation, spread=spread)
    wins = {d: 0 for d in dinosaurs.ids}
    _walk(effects, len(bank.space.keys), lambda t: wins.__setitem__(winner(t), wins[winner(t)] + 1),
          sample=sample, seed=seed)
    return wins


def entropy_ratio(wins: Dict[str, int]) -> float:
    """Distribution evenness in [0, 1]. 1.0 = every dinosaur equally likely,
    0.0 = one dinosaur always wins."""
    total = sum(wins.values())
    if total == 0 or len(wins) < 2:
        return 0.0
    probs = [c / total for c in wins.values() if c > 0]
    return -sum(p * math.log(p) for p in probs) / math.log(len(wins))


def total_answer_space(bank: QuestionBank) -> int:
    product = 1
    for question in bank:
        product *= len(question.options)
    return product


def presentation_validity(
    bank: QuestionBank,
    dinosaurs: DinosaurSet,
    *,
    apply_normalisation: bool,
    spread: float = 1.0,
    sample: Optional[int] = None,
    seed: int = 0,
) -> Dict[str, float]:
    """Can the result actually be shown to the user?

    The design calls for a radar chart with the user's four coordinates laid
    over the winning dinosaur's ideal profile, and a match percentage. Both
    require the two to live on the same scale. This measures whether they do:

      out_of_box     -- share of answer sets landing outside [-5, +5] on some
                        axis, which cannot be plotted against a dinosaur
      negative_match -- share whose distance exceeds the box diagonal, making
                        100 * (1 - d / 20) come out below zero
      clamped        -- share whose calibrated coordinates had to be
                        truncated at the box edge, losing resolution there
      mean_norm      -- typical |u|, to compare against typical |v|
    """
    space = bank.space
    keys = space.keys
    effects, _ = _make_matcher(bank, dinosaurs, apply_normalisation=apply_normalisation)
    calibrated = axis_scales(bank, dinosaurs, spread=spread)
    scale = tuple(calibrated[k] if apply_normalisation else 1.0 for k in keys)
    zero = space.zero()

    stats = {"n": 0, "out_of_box": 0, "negative_match": 0, "clamped": 0,
             "norm_sum": 0.0, "match_sum": 0.0}

    def visit(totals):
        vec = {k: totals[i] * scale[i] for i, k in enumerate(keys)}
        stats["n"] += 1
        if any(abs(v) > space.max for v in vec.values()):
            stats["clamped"] += 1
        if apply_normalisation:
            vec = space.clamp(vec)
        if any(abs(v) > space.max for v in vec.values()):
            stats["out_of_box"] += 1
        nearest = min(space.distance(vec, d.traits) for d in dinosaurs)
        percent = space.match_percent(nearest)
        if percent < 0:
            stats["negative_match"] += 1
        stats["norm_sum"] += space.distance(vec, zero)
        stats["match_sum"] += percent

    _walk(effects, len(keys), visit, sample=sample, seed=seed)
    n = stats["n"] or 1
    return {
        "out_of_box": stats["out_of_box"] / n,
        "clamped": stats["clamped"] / n,
        "negative_match": stats["negative_match"] / n,
        "mean_norm": stats["norm_sum"] / n,
        "mean_match": stats["match_sum"] / n,
    }


def _report(title: str, wins: Dict[str, int], dinosaurs: DinosaurSet) -> None:
    total = sum(wins.values())
    norms = dinosaurs.norms()
    print("\n{}".format(title))
    print("-" * 66)
    print("  {:<22} {:>10} {:>9}  {:>7}".format("dinosaur", "wins", "share", "|v|"))
    for dino_id, count in sorted(wins.items(), key=lambda kv: -kv[1]):
        flag = "   <- unreachable" if count == 0 else ""
        print("  {:<22} {:>10,} {:>8.2%}  {:>7.2f}{}".format(
            dinosaurs[dino_id].name, count, count / total if total else 0.0,
            norms[dino_id], flag))
    unreachable = sum(1 for c in wins.values() if c == 0)
    print("  {:<22} {:>10} {:>8}".format("", "", ""))
    print("  evenness (normalised entropy): {:.3f}   unreachable: {}/{}".format(
        entropy_ratio(wins), unreachable, len(wins)))


def _correlation(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else 0.0


def sweep(
    bank: QuestionBank,
    dinosaurs: DinosaurSet,
    *,
    spreads: Sequence[float] = (0.55, 0.65, 0.75, 0.85, 1.0, 1.15),
    sample: Optional[int] = None,
    seed: int = 0,
) -> None:
    """The calibration trade-off, measured.

    Matching standard deviations cannot match shapes -- the dinosaurs are
    bimodal at the box edges, users bell around zero -- so there is no spread
    that both keeps everyone inside the box and keeps the corner dinosaurs
    common. This prints the curve so the choice is made with numbers.
    """
    print("  {:>7} {:>9} {:>11} {:>10} {:>16}".format(
        "spread", "clamped", "evenness", "rarest", "magnitude-sens"))
    for value in spreads:
        wins = _tabulate(bank, dinosaurs, apply_normalisation=True,
                         spread=value, sample=sample, seed=seed)
        pres = presentation_validity(bank, dinosaurs, apply_normalisation=True,
                                     spread=value, sample=sample, seed=seed)
        sensitivity = magnitude_sensitivity(bank, dinosaurs, apply_normalisation=True,
                                            spread=value, sample=sample, seed=seed)
        total = sum(wins.values()) or 1
        marker = "   <- default" if value == 1.0 else ""
        print("  {:>7.2f} {:>8.1%} {:>11.3f} {:>9.2%} {:>15.1%}{}".format(
            value, pres["clamped"], entropy_ratio(wins),
            min(wins.values()) / total, sensitivity, marker))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the dinosaur quiz.")
    parser.add_argument("--sample", type=int, default=None,
                        help="sample N answer sets instead of enumerating all of them")
    parser.add_argument("--gain", type=float, default=2.0,
                        help="multiplier used for the magnitude-sensitivity check")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--sweep", action="store_true",
                        help="print the calibration trade-off curve and exit")
    args = parser.parse_args(argv)

    space = TraitSpace.load()
    dinosaurs = DinosaurSet.load(space)
    bank = QuestionBank.load(space)
    common = {"sample": args.sample, "seed": args.seed}

    total = total_answer_space(bank)
    print("{} questions, {} dinosaurs, {:,} possible answer sets".format(
        len(bank), len(dinosaurs), total))
    a, b, distance = dinosaurs.closest_pair()
    print("closest dinosaur pair: {} / {} at {:.2f} (mean pairwise {:.2f})".format(
        a, b, distance, dinosaurs.separation()))
    print("mode: {}".format(
        "sampled {:,}".format(args.sample) if args.sample else "exhaustive"))

    if args.sweep:
        print("\nCALIBRATION TRADE-OFF (`spread` in dinoclub.quiz.scoring)")
        print("-" * 70)
        sweep(bank, dinosaurs, sample=args.sample, seed=args.seed)
        print("\n  No spread wins outright. Lower keeps users inside the box; higher")
        print("  makes the corner dinosaurs reachable. 1.00 is plain moment matching,")
        print("  chosen so the default has no tuned constant in it.")
        return 0

    # ---- 1. is the question bank itself balanced? -------------------------
    print("\n1. QUESTION BANK BALANCE")
    print("-" * 70)
    print("  {:<14} {:>7} {:>10} {:>10} {:>9} {:>8}".format(
        "trait", "span", "max +", "max -", "skew", "lean"))
    balance = bank.balance()
    spans = bank.spans()
    leans = {}
    for key in space.keys:
        row = balance[key]
        lean = sum(
            sum(o.effect(key) for o in q.options) / len(q.options) for q in bank
        )
        leans[key] = lean
        print("  {:<14} {:>7.0f} {:>10.0f} {:>10.0f} {:>+9.0f} {:>+8.2f}".format(
            key, spans[key], row["max_positive"], row["max_negative"], row["skew"], lean))
    print("  `lean` is where a coin-flip answerer lands. Far from 0 means the bank")
    print("  itself is biased, which no amount of rescaling downstream can undo.")
    worst = max(abs(v) for v in leans.values())
    print("  worst axis lean: {:+.2f}  ->  {}".format(
        worst, "OK" if worst < 1.0 else "FIX THE QUESTIONS"))

    # ---- 2. can the result be displayed at all? ---------------------------
    print("\n2. PRESENTATION VALIDITY  (the reason calibration is not optional)")
    print("-" * 70)
    raw_pres = presentation_validity(bank, dinosaurs, apply_normalisation=False, **common)
    cal_pres = presentation_validity(bank, dinosaurs, apply_normalisation=True, **common)
    print("  {:<28} {:>14} {:>14}".format("", "raw totals", "calibrated"))
    print("  {:<28} {:>13.1%} {:>14.1%}".format(
        "outside the [-5,+5] box", raw_pres["out_of_box"], cal_pres["out_of_box"]))
    print("  {:<28} {:>13.1%} {:>14.1%}".format(
        "negative match percentage", raw_pres["negative_match"], cal_pres["negative_match"]))
    print("  {:<28} {:>13.1%} {:>14.1%}".format(
        "clamped on >=1 axis", raw_pres["clamped"], cal_pres["clamped"]))
    print("  {:<28} {:>13.1f} {:>14.1f}".format(
        "mean match percentage", raw_pres["mean_match"], cal_pres["mean_match"]))
    print("  {:<28} {:>13.2f} {:>14.2f}".format(
        "typical |u|", raw_pres["mean_norm"], cal_pres["mean_norm"]))
    print("  {:<28} {:>13.2f} {:>14.2f}".format(
        "typical |v| (dinosaurs)",
        sum(dinosaurs.norms().values()) / len(dinosaurs),
        sum(dinosaurs.norms().values()) / len(dinosaurs)))
    print("\n  A user outside the box cannot be drawn on the same radar chart as a")
    print("  dinosaur, and a negative match percentage cannot be shown to anyone.")

    # ---- 3. does how hard you answer matter? ------------------------------
    print("\n3. MAGNITUDE SENSITIVITY  (does answering more strongly change anything?)")
    print("-" * 70)
    for label, flag in (("raw totals", False), ("calibrated", True)):
        rate = magnitude_sensitivity(
            bank, dinosaurs, apply_normalisation=flag, gain=args.gain, **common)
        print("  {:<28} {:>6.2%} of answer sets change at {}x".format(label, rate, args.gain))
    print("  Higher is better here: it means intensity carries information rather")
    print("  than washing out into pure direction.")

    # ---- 4. where does everybody land? ------------------------------------
    print("\n4. WIN DISTRIBUTION")
    raw = _tabulate(bank, dinosaurs, apply_normalisation=False, **common)
    scaled = _tabulate(bank, dinosaurs, apply_normalisation=True, **common)
    _report("   raw totals matched straight against the dinosaur vectors", raw, dinosaurs)
    _report("   calibrated so the user cloud matches the dinosaur cloud", scaled, dinosaurs)

    norms = dinosaurs.norms()
    ids = dinosaurs.ids
    raw_total = sum(raw.values()) or 1
    scaled_total = sum(scaled.values()) or 1
    print("\n  correlation between a dinosaur's |v| and its win share")
    print("    raw        {:+.3f}".format(_correlation(
        [norms[i] for i in ids], [raw[i] / raw_total for i in ids])))
    print("    calibrated {:+.3f}".format(_correlation(
        [norms[i] for i in ids], [scaled[i] / scaled_total for i in ids])))
    print("\n  The negative correlation is the |v|^2 penalty, and it is a real cost:")
    print("  corner dinosaurs get rarer once the user cloud stops dwarfing them.")
    print("  For a personality quiz that is arguably a feature -- a rare result")
    print("  should feel rare -- but it is a data decision. Pull an extreme")
    print("  dinosaur's coordinates inward if you want it to come up more often.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
