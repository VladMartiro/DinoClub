"""The four behavioral axes, and the geometry that operates on them.

Every answer option and every dinosaur is a point in the same 4D box,
[-5, +5]^4. That shared box is the entire trick: it is what lets a user's
accumulated answers and a dinosaur's ideal profile be compared with an
ordinary Euclidean distance and have the comparison mean something.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence

DATA_DIR = Path(__file__).parent / "data"

Vector = Dict[str, float]


@dataclass(frozen=True)
class Trait:
    key: str
    name: str
    negative: str
    positive: str
    question: str = ""

    def pole(self, value: float) -> str:
        """Which end of the axis a coordinate sits on."""
        return self.positive if value >= 0 else self.negative

    def describe(self, value: float) -> str:
        """Render a coordinate as a phrase for the results page."""
        magnitude = abs(value)
        label = self.pole(value)
        if magnitude < 0.75:
            return "balanced between {} and {}".format(self.negative, self.positive)
        if magnitude < 2.0:
            return "leans {}".format(label)
        if magnitude < 3.5:
            return "clearly {}".format(label)
        return "strongly {}".format(label)


class TraitSpace:
    """An ordered set of axes plus the vector helpers built on them."""

    def __init__(self, traits: Sequence[Trait], minimum: float = -5.0, maximum: float = 5.0):
        if not traits:
            raise ValueError("TraitSpace needs at least one trait")
        if minimum >= maximum:
            raise ValueError("scale minimum must be below maximum")
        self._traits = tuple(traits)
        self._by_key = {t.key: t for t in self._traits}
        if len(self._by_key) != len(self._traits):
            raise ValueError("duplicate trait keys")
        self.min = float(minimum)
        self.max = float(maximum)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "TraitSpace":
        raw = json.loads(Path(path or DATA_DIR / "traits.json").read_text())
        scale = raw.get("scale", {"min": -5, "max": 5})
        return cls(
            [Trait(**t) for t in raw["traits"]],
            minimum=scale["min"],
            maximum=scale["max"],
        )

    @property
    def keys(self) -> List[str]:
        return [t.key for t in self._traits]

    @property
    def half_range(self) -> float:
        """Distance from the centre of the box to either end -- 5.0 by default."""
        return (self.max - self.min) / 2.0

    def __len__(self) -> int:
        return len(self._traits)

    def __iter__(self) -> Iterator[Trait]:
        return iter(self._traits)

    def __getitem__(self, key: str) -> Trait:
        return self._by_key[key]

    def __contains__(self, key: object) -> bool:
        return key in self._by_key

    def zero(self) -> Vector:
        """The neutral profile every user starts from."""
        return {k: 0.0 for k in self.keys}

    def validate(self, vec: Mapping[str, float], *, where: str = "vector") -> None:
        missing = set(self.keys) - set(vec)
        unknown = set(vec) - set(self.keys)
        if missing:
            raise ValueError("{}: missing traits {}".format(where, sorted(missing)))
        if unknown:
            raise ValueError("{}: unknown traits {}".format(where, sorted(unknown)))
        for key, value in vec.items():
            if not self.min <= float(value) <= self.max:
                raise ValueError(
                    "{}: {} = {} outside [{}, {}]".format(where, key, value, self.min, self.max)
                )

    def clamp(self, vec: Mapping[str, float]) -> Vector:
        return {k: min(self.max, max(self.min, float(vec[k]))) for k in self.keys}

    def distance(self, a: Mapping[str, float], b: Mapping[str, float]) -> float:
        """Plain Euclidean distance.

        Unweighted on purpose. Weighting an axis here would silently make one
        trait matter more than another, and the place to express that belief
        is the question bank -- where it is visible and auditable -- not buried
        in the metric.
        """
        return math.sqrt(sum((float(a[k]) - float(b[k])) ** 2 for k in self.keys))

    @property
    def max_distance(self) -> float:
        """Corner to opposite corner: sqrt(n) * (max - min).

        With four axes on a [-5, +5] scale this is sqrt(4 * 100) = 20, which is
        what turns a raw distance into a presentable match percentage.
        """
        return math.sqrt(len(self._traits) * (self.max - self.min) ** 2)

    def match_percent(self, distance: float) -> float:
        """Distance mapped onto 0-100 for the results page."""
        return 100.0 * (1.0 - distance / self.max_distance)
