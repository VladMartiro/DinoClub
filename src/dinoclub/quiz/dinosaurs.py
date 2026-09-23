"""The dinosaur library: fixed ideal profiles in trait space."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from .traits import DEFAULT_DATASET, TraitSpace, Vector, data_dir


@dataclass(frozen=True)
class Dinosaur:
    id: str
    name: str
    tagline: str
    blurb: str
    traits: Vector

    def coords(self, space: TraitSpace) -> List[float]:
        return [self.traits[k] for k in space.keys]


class DinosaurSet:
    def __init__(self, dinosaurs: Sequence[Dinosaur], space: TraitSpace):
        if not dinosaurs:
            raise ValueError("need at least one dinosaur")
        self.space = space
        self._dinosaurs = tuple(dinosaurs)
        self._by_id: Dict[str, Dinosaur] = {}
        for d in self._dinosaurs:
            if d.id in self._by_id:
                raise ValueError("duplicate dinosaur id: {}".format(d.id))
            space.validate(d.traits, where="dinosaur {}".format(d.id))
            self._by_id[d.id] = d

    @classmethod
    def load(
        cls,
        space: Optional[TraitSpace] = None,
        path: Optional[Path] = None,
        *,
        dataset: str = DEFAULT_DATASET,
    ) -> "DinosaurSet":
        space = space or TraitSpace.load(dataset=dataset)
        raw = json.loads(Path(path or data_dir(dataset) / "dinosaurs.json").read_text())
        return cls(
            [
                Dinosaur(
                    id=d["id"],
                    name=d["name"],
                    tagline=d.get("tagline", ""),
                    blurb=d.get("blurb", ""),
                    traits={k: float(v) for k, v in d["traits"].items()},
                )
                for d in raw["dinosaurs"]
            ],
            space,
        )

    def __len__(self) -> int:
        return len(self._dinosaurs)

    def __iter__(self) -> Iterator[Dinosaur]:
        return iter(self._dinosaurs)

    def __getitem__(self, dinosaur_id: str) -> Dinosaur:
        return self._by_id[dinosaur_id]

    def __contains__(self, dinosaur_id: object) -> bool:
        return dinosaur_id in self._by_id

    @property
    def ids(self) -> List[str]:
        return [d.id for d in self._dinosaurs]

    def separation(self) -> float:
        """Mean pairwise distance -- how spread out the library is."""
        distances = self._pairwise()
        return sum(d for _, _, d in distances) / len(distances) if distances else 0.0

    def closest_pair(self) -> Tuple[str, str, float]:
        """The two dinosaurs hardest to tell apart. If this gets small, the
        quiz cannot separate them no matter how good the questions are."""
        return min(self._pairwise(), key=lambda t: t[2])

    def norms(self) -> Dict[str, float]:
        """Each dinosaur's distance from the neutral centre.

        This matters more than it looks. Matching minimises
        |u - v|^2 = |u|^2 - 2(u . v) + |v|^2, and |u|^2 is the same for every
        candidate -- so the |v|^2 term acts as a fixed penalty on extreme
        dinosaurs. A dinosaur far from the origin needs a user who commits
        hard in its direction; a dinosaur near the origin collects everyone
        who answers moderately. See `analysis.py`, which measures the damage.
        """
        zero = self.space.zero()
        return {d.id: self.space.distance(d.traits, zero) for d in self._dinosaurs}

    def _pairwise(self) -> List[Tuple[str, str, float]]:
        return [
            (a.id, b.id, self.space.distance(a.traits, b.traits))
            for i, a in enumerate(self._dinosaurs)
            for b in self._dinosaurs[i + 1 :]
        ]
