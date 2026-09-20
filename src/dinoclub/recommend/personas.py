"""Viewer archetypes: named regions of movie-taste space.

These are the RECOMMENDER's clusters, not the dinosaurs in `dinoclub.quiz`.
They are named differently on purpose, so that "Velociraptor" means exactly
one thing in this repository.

An anchor is the centroid of the persona's exemplar movies, optionally nudged
toward a hand-authored emphasis. Deriving anchors from the catalog rather than
writing them by hand means the personas stay consistent with the items we
actually recommend -- if a persona's anchor drifts away from every movie in the
catalog, nobody can ever be told they are that dinosaur and score well.

`posterior` returns a distribution rather than a single label, which is what
the adaptive quiz optimizes against and what lets the UI say "you are 60%
The Thrill-Seeker, 25% The Maximalist".
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

from .catalog import Catalog
from .profile import Profile
from .spaces import DATA_DIR, AxisSpace, Vector

#: Softmax temperature over persona distances. Lower = more confident/peaky.
#: 0.09 was chosen so a fully-answered quiz typically puts 45-70% on the top
#: persona -- decisive enough to be fun, soft enough to be honest.
DEFAULT_TEMPERATURE = 0.09


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    tagline: str
    blurb: str
    anchor: Vector
    exemplars: Sequence[str] = field(default_factory=tuple)


class PersonaSet:
    def __init__(self, personas: Sequence[Persona], space: AxisSpace):
        if not personas:
            raise ValueError("need at least one persona")
        self.space = space
        self._personas = tuple(personas)
        self._by_id: Dict[str, Persona] = {}
        for p in self._personas:
            if p.id in self._by_id:
                raise ValueError("duplicate persona id: {}".format(p.id))
            space.validate(p.anchor, where="persona {}".format(p.id))
            self._by_id[p.id] = p

    @classmethod
    def load(cls, catalog: Catalog, path: Optional[Path] = None) -> "PersonaSet":
        """Build personas against a catalog, resolving exemplars to an anchor."""
        space = catalog.space
        path = path or DATA_DIR / "personas.json"
        raw = json.loads(Path(path).read_text())
        personas = []
        for p in raw["personas"]:
            exemplars = list(p["exemplars"])
            missing = [e for e in exemplars if e not in catalog]
            if missing:
                raise ValueError(
                    "persona {} references movies not in catalog: {}".format(p["id"], missing)
                )
            anchor = catalog.centroid(exemplars)
            emphasis = p.get("emphasis")
            if emphasis:
                anchor = space.blend(anchor, emphasis, float(p.get("emphasis_strength", 0.3)))
            personas.append(
                Persona(
                    id=p["id"],
                    name=p["name"],
                    tagline=p.get("tagline", ""),
                    blurb=p.get("blurb", ""),
                    anchor=anchor,
                    exemplars=tuple(exemplars),
                )
            )
        return cls(personas, space)

    def __len__(self) -> int:
        return len(self._personas)

    def __iter__(self) -> Iterator[Persona]:
        return iter(self._personas)

    def __getitem__(self, persona_id: str) -> Persona:
        return self._by_id[persona_id]

    def __contains__(self, persona_id: object) -> bool:
        return persona_id in self._by_id

    @property
    def ids(self) -> List[str]:
        return [p.id for p in self._personas]

    def posterior(
        self, profile: Profile, temperature: float = DEFAULT_TEMPERATURE
    ) -> Dict[str, float]:
        """Softmax over negative weighted distance from profile to each anchor."""
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        logits = {p.id: -profile.distance_to(p.anchor) / temperature for p in self._personas}
        top = max(logits.values())
        exps = {k: math.exp(v - top) for k, v in logits.items()}
        total = sum(exps.values())
        return {k: v / total for k, v in exps.items()}

    def ranked(
        self, profile: Profile, temperature: float = DEFAULT_TEMPERATURE
    ) -> List[Tuple[Persona, float]]:
        post = self.posterior(profile, temperature)
        pairs = [(self[pid], prob) for pid, prob in post.items()]
        pairs.sort(key=lambda pp: pp[1], reverse=True)
        return pairs

    def best(self, profile: Profile, temperature: float = DEFAULT_TEMPERATURE) -> Tuple[Persona, float]:
        return self.ranked(profile, temperature)[0]

    def separation(self) -> float:
        """Mean distance between distinct anchors -- a health check on the
        persona set. If this collapses, the quiz cannot tell them apart no
        matter how many questions it asks."""
        ds = [
            self.space.distance(a.anchor, b.anchor)
            for i, a in enumerate(self._personas)
            for b in self._personas[i + 1 :]
        ]
        return sum(ds) / len(ds) if ds else 0.0

    def closest_pair(self) -> Tuple[str, str, float]:
        best = None
        for i, a in enumerate(self._personas):
            for b in self._personas[i + 1 :]:
                d = self.space.distance(a.anchor, b.anchor)
                if best is None or d < best[2]:
                    best = (a.id, b.id, d)
        return best
