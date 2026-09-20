"""The matching algorithm, in four steps.

  1. Accumulate  -- sum the effects of every option the user picked.
  2. Calibrate   -- rescale each axis so the user cloud and the dinosaur
                    cloud occupy the same region of the box.
  3. Measure     -- Euclidean distance from the user to each dinosaur.
  4. Rank        -- nearest wins; a softmax over the distances gives the
                    confidence breakdown for the results page.

Step 2 is the one that is easy to leave out, and it is subtler than it looks.

The raw totals are unbounded. With ten questions that can each move `social`
by up to 5, a raw `social` coordinate ranges over roughly [-41, +41], while
every dinosaur sits in [-5, +5]. Two separate things break.

First, the axes stop being comparable. Each axis has a different reachable
range, so a disagreement worth one question on the widest axis outweighs the
same disagreement on the narrowest. The metric quietly decides that one trait
matters more than another, and nobody chose that.

Second, and less obvious, matching minimises

    |u - v|^2  =  |u|^2  -  2(u . v)  +  |v|^2

where |u|^2 is identical across candidates. So the winner maximises
2(u . v) - |v|^2, and that |v|^2 is a fixed penalty on dinosaurs far from the
origin. The size of u relative to v decides which term rules:

  * u much larger than v  -> |v|^2 is negligible, only direction matters, and
    how *strongly* someone answered stops carrying any information.
  * u much smaller than v -> |v|^2 dominates, and everyone collapses onto
    whichever dinosaurs sit nearest the origin.

Both regimes are real, and the second one bit hard here. The first version of
this function rescaled by each axis's theoretical span -- the largest total a
user could possibly reach. That looks right and is wrong: no real answer set
maxes out every axis at once, so the user cloud came out with a standard
deviation of about 1.1 per axis against the dinosaurs' 3.7. An exhaustive
audit showed Velociraptor and Ankylosaurus -- the two most extreme profiles,
both at |v| = 9.54 -- becoming *literally unreachable*, win share correlating
with |v| at -0.67, and evenness dropping from 0.899 to 0.797. Normalising by
the span made the quiz worse than not normalising at all.

The fix is to calibrate against the distribution that actually occurs rather
than the one that theoretically could. `axis_scales` matches moments: it
scales each axis so the spread of user coordinates equals the spread of
dinosaur coordinates on that axis. The user spread is computed analytically
rather than sampled -- a raw total is a sum of independent per-question
contributions, so its variance is just the sum of the per-question variances.

`analysis.py` measures all of this on the real bank, exhaustively.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .dinosaurs import Dinosaur, DinosaurSet
from .questions import QuestionBank
from .traits import TraitSpace, Vector

#: Softmax temperature over distances, in trait-space units. Smaller is
#: peakier. 2.6 was picked so a decisive quiz puts roughly 30-45% on the
#: winner across the dinosaur library -- confident enough to feel like an
#: answer, honest enough that the runner-up is visibly in the running.
DEFAULT_TEMPERATURE = 2.6

#: Global multiplier on the calibrated axis scales. 1.0 is pure moment
#: matching. See `axis_scales` for why this knob exists and what it trades.
DEFAULT_SPREAD = 1.0


def accumulate(
    answers: Sequence[Tuple[str, str]], bank: QuestionBank
) -> Vector:
    """Step 1. Sum the effects of the chosen options.

    `answers` is a sequence of (question_id, option_id). Returns raw totals,
    which are NOT yet comparable with dinosaur vectors.
    """
    totals = {key: 0.0 for key in bank.space.keys}
    for question_id, option_id in answers:
        option = bank[question_id][option_id]
        for key, value in option.effects.items():
            totals[key] += float(value)
    return totals


def axis_scales(
    bank: QuestionBank, dinosaurs: DinosaurSet, *, spread: float = DEFAULT_SPREAD
) -> Vector:
    """Per-axis multiplier that puts user totals on the dinosaurs' scale.

        scale[a] = sd(dinosaur coordinates on a) / sd(user totals on a)

    The user standard deviation is exact, not sampled. A raw total is a sum
    of independent per-question contributions, so its variance is the sum of
    the per-question variances, each taken over that question's options under
    the assumption that a user picks uniformly among them.

    That assumption is the one real approximation here. Real users do not
    answer uniformly, so if the quiz ever collects response data, these
    variances should be recomputed from the observed option frequencies --
    nothing else about the pipeline has to change.

    `spread` scales the whole thing up or down. It exists because matching
    standard deviations cannot match *shapes*: the dinosaur coordinates are
    bimodal, piled up at +-4 and +-5, while user totals bell around zero. Any
    linear map that gives a bell the same spread as a barbell pushes its tails
    past the box edge, so roughly half of all answer sets clamp on at least
    one axis. Turning `spread` down reduces clamping and makes the corner
    dinosaurs rarer; turning it up does the reverse. `analysis.py --sweep`
    prints the trade-off. The default is 1.0 -- honest moment matching, with
    no tuned constant hiding in it.
    """
    space = bank.space
    scales: Vector = {}
    for key in space.keys:
        user_variance = 0.0
        for question in bank:
            values = [option.effect(key) for option in question.options]
            mean = sum(values) / len(values)
            user_variance += sum((v - mean) ** 2 for v in values) / len(values)
        user_sd = math.sqrt(user_variance)

        coords = [d.traits[key] for d in dinosaurs]
        dino_mean = sum(coords) / len(coords)
        dino_sd = math.sqrt(sum((c - dino_mean) ** 2 for c in coords) / len(coords))

        # No variation on an axis means no information about it; leave the
        # user at 0 rather than dividing by zero or inventing a position.
        scales[key] = 0.0 if user_sd == 0 else spread * dino_sd / user_sd
    return scales


def normalize(
    raw: Mapping[str, float],
    bank: QuestionBank,
    dinosaurs: DinosaurSet,
    *,
    spread: float = DEFAULT_SPREAD,
) -> Vector:
    """Step 2. Apply the calibrated scales and clamp into the box.

    At the default spread about half of all answer sets clamp on at least one
    axis, which is a real loss of resolution in the tail: two users who both
    answered hard in the same direction become identical on that axis.
    Truncating is still the right call -- they are already past every
    dinosaur, and letting them run further would inflate distances without
    changing the ordering -- but it is a cost, not a free move.
    """
    scales = axis_scales(bank, dinosaurs, spread=spread)
    return bank.space.clamp({k: raw[k] * scales[k] for k in bank.space.keys})


@dataclass(frozen=True)
class Match:
    dinosaur: Dinosaur
    distance: float
    match_percent: float
    confidence: float


def rank(
    profile: Mapping[str, float],
    dinosaurs: DinosaurSet,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
) -> List[Match]:
    """Steps 3 and 4. Distance to every dinosaur, nearest first.

    Ties are broken by id so the result is deterministic. The claim that ties
    are impossible is not quite true here: effects and dinosaur coordinates
    are both integers, so exact ties are uncommon but entirely reachable, and
    a quiz that returned a different answer on reload would be worse than one
    that picked a stable loser.
    """
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    space = dinosaurs.space
    distances = [(d, space.distance(profile, d.traits)) for d in dinosaurs]

    # Softmax over negative distance, shifted for numerical stability.
    nearest = min(dist for _, dist in distances)
    weights = {d.id: math.exp(-(dist - nearest) / temperature) for d, dist in distances}
    total = sum(weights.values())

    matches = [
        Match(
            dinosaur=d,
            distance=dist,
            match_percent=space.match_percent(dist),
            confidence=weights[d.id] / total,
        )
        for d, dist in distances
    ]
    matches.sort(key=lambda m: (m.distance, m.dinosaur.id))
    return matches


@dataclass(frozen=True)
class Result:
    """Everything the results page needs, including the radar chart."""

    profile: Vector
    raw_totals: Vector
    matches: Sequence[Match]
    answers: Sequence[Tuple[str, str]]
    space: TraitSpace

    @property
    def winner(self) -> Dinosaur:
        return self.matches[0].dinosaur

    @property
    def runner_up(self) -> Optional[Match]:
        return self.matches[1] if len(self.matches) > 1 else None

    @classmethod
    def build(
        cls,
        answers: Sequence[Tuple[str, str]],
        bank: QuestionBank,
        dinosaurs: DinosaurSet,
        *,
        temperature: float = DEFAULT_TEMPERATURE,
        spread: float = DEFAULT_SPREAD,
    ) -> "Result":
        raw = accumulate(answers, bank)
        profile = normalize(raw, bank, dinosaurs, spread=spread)
        return cls(
            profile=profile,
            raw_totals=raw,
            matches=rank(profile, dinosaurs, temperature=temperature),
            answers=list(answers),
            space=bank.space,
        )

    def radar(self) -> List[Dict[str, object]]:
        """Per-axis rows for the spider chart: the user's coordinate laid over
        the winning dinosaur's ideal profile."""
        winner = self.winner
        return [
            {
                "trait": trait.key,
                "label": trait.name,
                "negative": trait.negative,
                "positive": trait.positive,
                "you": round(self.profile[trait.key], 2),
                "dinosaur": winner.traits[trait.key],
                "gap": round(abs(self.profile[trait.key] - winner.traits[trait.key]), 2),
            }
            for trait in self.space
        ]

    def summary(self) -> List[str]:
        """The user's two most pronounced traits, in words."""
        ordered = sorted(self.space, key=lambda t: abs(self.profile[t.key]), reverse=True)
        return [t.describe(self.profile[t.key]) for t in ordered[:2]]

    def to_dict(self) -> Dict[str, object]:
        """JSON-ready, for handing straight to a frontend."""
        return {
            "winner": {
                "id": self.winner.id,
                "name": self.winner.name,
                "tagline": self.winner.tagline,
                "blurb": self.winner.blurb,
                "match_percent": round(self.matches[0].match_percent, 1),
                "distance": round(self.matches[0].distance, 3),
                "confidence": round(self.matches[0].confidence, 4),
            },
            "runner_up": (
                {
                    "id": self.runner_up.dinosaur.id,
                    "name": self.runner_up.dinosaur.name,
                    "match_percent": round(self.runner_up.match_percent, 1),
                    "confidence": round(self.runner_up.confidence, 4),
                }
                if self.runner_up
                else None
            ),
            "profile": {k: round(v, 2) for k, v in self.profile.items()},
            "raw_totals": {k: round(v, 1) for k, v in self.raw_totals.items()},
            "summary": self.summary(),
            "radar": self.radar(),
            "leaderboard": [
                {
                    "id": m.dinosaur.id,
                    "name": m.dinosaur.name,
                    "distance": round(m.distance, 3),
                    "match_percent": round(m.match_percent, 1),
                    "confidence": round(m.confidence, 4),
                }
                for m in self.matches
            ],
            "answers": [{"question": q, "option": o} for q, o in self.answers],
        }
