"""The taste space: a small set of named, human-readable axes.

Everything in dinoclub.recommend -- movies, quiz answers, user profiles, dinosaur
personas -- lives in the same vector space. Keeping the axes interpretable
(rather than opaque embedding dimensions) is a deliberate trade: we lose some
representational capacity and gain the ability to say *why* someone got the
answer they got, which is most of what makes the result fun to read.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

DATA_DIR = Path(__file__).parent / "data"

Vector = Dict[str, float]


@dataclass(frozen=True)
class Axis:
    key: str
    label: str
    low: str
    high: str

    def describe(self, value: float) -> str:
        """Render a coordinate as a phrase, e.g. 'strongly enormous set-pieces'."""
        if value >= 0.75:
            return "strongly {}".format(self.high)
        if value >= 0.58:
            return "leans {}".format(self.high)
        if value <= 0.25:
            return "strongly {}".format(self.low)
        if value <= 0.42:
            return "leans {}".format(self.low)
        return "balanced on {}".format(self.label.lower())


class AxisSpace:
    """An ordered, immutable set of axes plus vector helpers."""

    def __init__(self, axes: Sequence[Axis]):
        if not axes:
            raise ValueError("AxisSpace needs at least one axis")
        self._axes = tuple(axes)
        self._by_key = {a.key: a for a in self._axes}
        if len(self._by_key) != len(self._axes):
            raise ValueError("duplicate axis keys")

    @classmethod
    def load(cls, path: Path = None) -> "AxisSpace":
        path = path or DATA_DIR / "axes.json"
        raw = json.loads(Path(path).read_text())
        return cls([Axis(**a) for a in raw["axes"]])

    @property
    def keys(self) -> List[str]:
        return [a.key for a in self._axes]

    def __len__(self) -> int:
        return len(self._axes)

    def __iter__(self) -> Iterable[Axis]:
        return iter(self._axes)

    def __getitem__(self, key: str) -> Axis:
        return self._by_key[key]

    def __contains__(self, key: object) -> bool:
        return key in self._by_key

    def validate(self, vec: Mapping[str, float], *, where: str = "vector") -> None:
        missing = set(self.keys) - set(vec)
        unknown = set(vec) - set(self.keys)
        if missing:
            raise ValueError("{}: missing axes {}".format(where, sorted(missing)))
        if unknown:
            raise ValueError("{}: unknown axes {}".format(where, sorted(unknown)))
        for k, v in vec.items():
            if not 0.0 <= float(v) <= 1.0:
                raise ValueError("{}: axis {} = {} outside [0, 1]".format(where, k, v))

    def centroid(self, vectors: Sequence[Mapping[str, float]]) -> Vector:
        if not vectors:
            raise ValueError("centroid of no vectors")
        return {k: sum(float(v[k]) for v in vectors) / len(vectors) for k in self.keys}

    def blend(self, base: Mapping[str, float], toward: Mapping[str, float], strength: float) -> Vector:
        """Move `base` a fraction `strength` of the way toward `toward`.

        `toward` may be sparse; axes it omits are left alone.
        """
        if not 0.0 <= strength <= 1.0:
            raise ValueError("strength must be in [0, 1]")
        out = {k: float(base[k]) for k in self.keys}
        for k, target in toward.items():
            if k not in self._by_key:
                raise ValueError("unknown axis {}".format(k))
            out[k] = (1.0 - strength) * out[k] + strength * float(target)
        return out

    def distance(
        self,
        a: Mapping[str, float],
        b: Mapping[str, float],
        weights: Mapping[str, float] = None,
    ) -> float:
        """Weighted RMS distance in [0, 1].

        Weights let an axis the user has told us nothing about count for less
        than one they answered three questions about. RMS (rather than plain
        Euclidean) keeps the scale comparable as the number of axes changes.
        """
        num = 0.0
        den = 0.0
        for k in self.keys:
            w = 1.0 if weights is None else max(0.0, float(weights.get(k, 0.0)))
            if w == 0.0:
                continue
            d = float(a[k]) - float(b[k])
            num += w * d * d
            den += w
        if den == 0.0:
            return 0.0
        return (num / den) ** 0.5
