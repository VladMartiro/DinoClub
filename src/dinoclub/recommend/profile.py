"""The user side: a taste profile built incrementally from evidence.

A profile is a posterior, not a point. Each axis carries both an estimate and
a confidence, starting from an uninformative prior at 0.5 and moving as
answers arrive. Tracking confidence separately is what makes the adaptive quiz
possible -- you cannot ask "what don't I know yet?" of a bare vector.

The update is the standard conjugate mean update for a Gaussian with known
variance: posterior mean is a precision-weighted average of the prior and the
observations, and precision adds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from .spaces import AxisSpace, Vector

PRIOR_MEAN = 0.5
PRIOR_WEIGHT = 1.0
#: Floor on per-axis weight when matching, so an axis we know nothing about
#: still contributes a little rather than dropping out of the distance entirely.
WEIGHT_FLOOR = 0.15


@dataclass
class Evidence:
    """One observation: 'this answer suggests axis `key` sits near `value`'."""

    key: str
    value: float
    weight: float = 1.0
    source: str = ""


@dataclass
class Profile:
    """A user's position in taste space, with per-axis confidence."""

    space: AxisSpace
    _sum: Dict[str, float] = field(default_factory=dict)
    _weight: Dict[str, float] = field(default_factory=dict)
    history: List[Evidence] = field(default_factory=list)

    @classmethod
    def empty(cls, space: AxisSpace) -> "Profile":
        return cls(
            space=space,
            _sum={k: 0.0 for k in space.keys},
            _weight={k: 0.0 for k in space.keys},
        )

    @classmethod
    def from_vector(cls, space: AxisSpace, vec: Mapping[str, float], weight: float = 8.0) -> "Profile":
        """Build a fully-determined profile. Used by the simulator and tests."""
        space.validate(vec, where="profile vector")
        p = cls.empty(space)
        for k, v in vec.items():
            p.observe(Evidence(key=k, value=float(v), weight=weight, source="seed"))
        return p

    def copy(self) -> "Profile":
        return Profile(
            space=self.space,
            _sum=dict(self._sum),
            _weight=dict(self._weight),
            history=list(self.history),
        )

    def observe(self, evidence: Evidence) -> "Profile":
        if evidence.key not in self.space:
            raise ValueError("unknown axis {}".format(evidence.key))
        if evidence.weight < 0:
            raise ValueError("evidence weight must be non-negative")
        self._sum[evidence.key] += evidence.weight * float(evidence.value)
        self._weight[evidence.key] += evidence.weight
        self.history.append(evidence)
        return self

    def observe_all(self, evidence: List[Evidence]) -> "Profile":
        for e in evidence:
            self.observe(e)
        return self

    @property
    def vector(self) -> Vector:
        """Posterior mean per axis, shrunk toward the 0.5 prior."""
        return {
            k: (PRIOR_MEAN * PRIOR_WEIGHT + self._sum[k]) / (PRIOR_WEIGHT + self._weight[k])
            for k in self.space.keys
        }

    @property
    def confidence(self) -> Dict[str, float]:
        """Per-axis confidence in [0, 1): the share of posterior precision that
        came from evidence rather than from the prior."""
        return {
            k: self._weight[k] / (PRIOR_WEIGHT + self._weight[k])
            for k in self.space.keys
        }

    @property
    def match_weights(self) -> Dict[str, float]:
        """Confidence with a floor, for use as distance weights."""
        c = self.confidence
        return {k: WEIGHT_FLOOR + (1.0 - WEIGHT_FLOOR) * c[k] for k in self.space.keys}

    @property
    def total_evidence(self) -> float:
        return sum(self._weight.values())

    def distance_to(self, other: Mapping[str, float]) -> float:
        return self.space.distance(self.vector, other, self.match_weights)

    def similarity_to(self, other: Mapping[str, float], tau: float = 0.35) -> float:
        """Distance mapped into (0, 1]. `tau` controls how sharply score falls
        off with distance; 0.35 keeps the full catalog meaningfully ranked
        instead of collapsing everything past the top few to zero."""
        import math

        return math.exp(-self.distance_to(other) / tau)

    def salient(self, n: int = 3, min_confidence: float = 0.25) -> List[Tuple[str, float]]:
        """The axes this user is most distinctive on, for explanations.

        Distinctiveness is |value - 0.5| scaled by confidence, so a strong
        opinion we are sure about outranks a strong opinion we guessed.
        """
        vec = self.vector
        conf = self.confidence
        scored = [
            (k, abs(vec[k] - PRIOR_MEAN) * conf[k])
            for k in self.space.keys
            if conf[k] >= min_confidence
        ]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [(k, vec[k]) for k, _ in scored[:n]]

    def explain(self, n: int = 3) -> List[str]:
        return [self.space[k].describe(v) for k, v in self.salient(n)]
