"""An interactive run of the quiz in the terminal: `python -m dinoclub.recommend.demo`.

Useful for feeling out whether the questions and results are actually fun,
which no metric in `dinoclub.recommend.eval` can tell you.
"""

from __future__ import annotations

import argparse
import random
from typing import Optional, Sequence

from . import DinoRec


def _bar(value: float, width: int = 24) -> str:
    filled = int(round(value * width))
    return "#" * filled + "." * (width - filled)


def run(auto: bool = False, seed: int = 0, questions: int = 6) -> int:
    engine = DinoRec.load()
    session = engine.start_quiz(max_questions=questions)
    rng = random.Random(seed)

    print("\n  DINO CLUB PERSONALITY TEST")
    print("  {} movies, {} personas, up to {} questions\n".format(
        len(engine.catalog), len(engine.personas), questions))

    while not session.done:
        question = session.next_question()
        if question is None:
            break
        print("  {}".format(question.text))
        for i, opt in enumerate(question.options, 1):
            print("    {}) {}".format(i, opt.label))
        if auto:
            choice = rng.randrange(len(question.options))
            print("    > {} (auto)".format(choice + 1))
        else:
            while True:
                raw = input("    > ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(question.options):
                    choice = int(raw) - 1
                    break
                print("    pick 1-{}".format(len(question.options)))
        session.answer(question.id, question.options[choice].id)
        print()

    result = session.result()
    print("=" * 62)
    print("  YOU ARE: {}".format(result.persona.name.upper()))
    print("  {}".format(result.persona.tagline))
    print()
    print("  {}".format(result.persona.blurb))
    print()
    print("  Your taste, in three words: {}".format("; ".join(result.profile_summary)))
    print()
    print("  How sure we are (after {} questions):".format(result.questions_asked))
    for pid, prob in sorted(result.posterior.items(), key=lambda kv: -kv[1]):
        print("    {:<18} {} {:>5.1f}%".format(engine.personas[pid].name, _bar(prob), prob * 100))
    print()
    print("  WATCH NEXT")
    for i, rec in enumerate(result.recommendations, 1):
        print("    {}. {:<38} {:.2f}".format(i, rec.movie.display, rec.score))
        if rec.reasons:
            print("       because it is {}".format(", and ".join(rec.reasons)))
    print("=" * 62)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Take the dinosaur personality test.")
    parser.add_argument("--auto", action="store_true", help="answer at random (for CI/smoke tests)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--questions", type=int, default=6)
    args = parser.parse_args(argv)
    return run(auto=args.auto, seed=args.seed, questions=args.questions)


if __name__ == "__main__":
    raise SystemExit(main())
