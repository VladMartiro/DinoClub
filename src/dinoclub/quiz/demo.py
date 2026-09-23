"""Take the test in a terminal: `python -m dinoclub.quiz.demo`.

Also renders the radar comparison as ASCII, which is the fastest way to see
whether the calibration is doing its job: your marker and the dinosaur's
marker should land near each other on most axes, and both should stay inside
the bar.
"""

from __future__ import annotations

import argparse
import random
from typing import Optional, Sequence

from . import DEFAULT_DATASET, DinoQuiz
from .scoring import Result, axis_scales

WIDTH = 33  # odd, so there is an exact centre cell for 0


def _axis_bar(space, trait, you: float, dino: float) -> str:
    """One row of the radar, flattened into a line.

    'O' is you, 'X' is the dinosaur, '*' is both in the same cell.
    """
    def cell(value: float) -> int:
        fraction = (value - space.min) / (space.max - space.min)
        return max(0, min(WIDTH - 1, int(round(fraction * (WIDTH - 1)))))

    slots = [" "] * WIDTH
    slots[WIDTH // 2] = "|"
    you_at, dino_at = cell(you), cell(dino)
    slots[dino_at] = "X"
    slots[you_at] = "*" if you_at == dino_at else "O"
    return "".join(slots)


def render_radar(result: Result) -> str:
    space = result.space
    winner = result.winner
    lines = [
        "  TRAIT RADAR      O = you    X = {}    * = both".format(winner.name),
        "",
    ]
    for trait in space:
        you = result.profile[trait.key]
        theirs = float(winner.traits[trait.key])
        lines.append("  {:<26} {}".format(trait.negative[:26], ""))
        lines.append("  {:<26} [{}]  you {:+.2f}  vs {:+.0f}".format(
            "", _axis_bar(space, trait, you, theirs), you, theirs))
        lines.append("  {:>26}".format(trait.positive[:26]))
        lines.append("")
    return "\n".join(lines)


def run(auto: bool = False, seed: int = 0, show_math: bool = False,
        dataset: str = DEFAULT_DATASET) -> int:
    quiz = DinoQuiz.load(dataset=dataset)
    session = quiz.start()
    rng = random.Random(seed)

    print("\n  WHAT TYPE OF DINOSAUR ARE YOU?")
    print("  {} questions, {} dinosaurs, {} trait axes\n".format(
        len(quiz.bank), len(quiz.dinosaurs), len(quiz.space)))

    while not session.done:
        question = session.next_question()
        answered, total = session.progress
        print("  [{}/{}] {}".format(answered + 1, total, question.text))
        for index, option in enumerate(question.options, 1):
            print("     {}) {}".format(index, option.text))
        if auto:
            choice = rng.randrange(len(question.options))
            print("     > {} (auto)".format(choice + 1))
        else:
            while True:
                raw = input("     > ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(question.options):
                    choice = int(raw) - 1
                    break
                print("     pick 1-{}".format(len(question.options)))
        session.answer(question.id, question.options[choice].id)
        print()

    result = session.result()
    top = result.matches[0]

    print("=" * 72)
    print("  YOU ARE: {}".format(result.winner.name.upper()))
    print("  {}".format(result.winner.tagline))
    print()
    print("  {}".format(result.winner.blurb))
    print()
    print("  {:.0f}% match  (distance {:.2f} of a possible {:.0f})".format(
        top.match_percent, top.distance, result.space.max_distance))
    print("  You are {} and {}.".format(*result.summary()))
    print()

    if show_math:
        print("  THE ARITHMETIC")
        print("  {:<14} {:>10} {:>10} {:>10} {:>10}".format(
            "trait", "raw", "scale", "you", result.winner.name[:10]))
        scales = axis_scales(quiz.bank, quiz.dinosaurs)
        for trait in result.space:
            print("  {:<14} {:>+10.0f} {:>10.3f} {:>+10.2f} {:>+10.0f}".format(
                trait.key, result.raw_totals[trait.key], scales[trait.key],
                result.profile[trait.key], result.winner.traits[trait.key]))
        print()

    print(render_radar(result))

    print("  HOW CLOSE THE OTHERS CAME")
    for match in result.matches[1:5]:
        bar = "#" * int(round(match.confidence * 40))
        print("    {:<22} {:>5.1f}%  {}".format(
            match.dinosaur.name, match.match_percent, bar))
    print("=" * 72)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Take the dinosaur personality test.")
    parser.add_argument("--auto", action="store_true", help="answer at random")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--show-math", action="store_true",
                        help="print the raw totals, scale factors and final coordinates")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    args = parser.parse_args(argv)
    return run(auto=args.auto, seed=args.seed, show_math=args.show_math, dataset=args.dataset)


if __name__ == "__main__":
    raise SystemExit(main())
