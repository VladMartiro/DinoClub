"""The item side of the recommender: what we can recommend, and where it sits.

The catalog is deliberately a plain JSON file with hand-authored axis values.
That is a *prior*, not a ceiling -- see `scripts/refit_axes.py` for replacing
these numbers with values fit from real ratings once there are enough of them.
Starting from a hand-authored prior is what lets the system work on day one
with zero users, which is the whole cold-start problem in miniature.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence

from .spaces import DATA_DIR, AxisSpace, Vector


@dataclass(frozen=True)
class Movie:
    id: str
    title: str
    year: int
    kind: str
    axes: Vector
    tags: Sequence[str] = field(default_factory=tuple)

    @property
    def display(self) -> str:
        return "{} ({})".format(self.title, self.year)


class Catalog:
    """An ordered collection of movies, indexed by id."""

    def __init__(self, movies: Sequence[Movie], space: AxisSpace):
        self.space = space
        self._movies = tuple(movies)
        self._by_id: Dict[str, Movie] = {}
        for m in self._movies:
            if m.id in self._by_id:
                raise ValueError("duplicate movie id: {}".format(m.id))
            space.validate(m.axes, where="movie {}".format(m.id))
            self._by_id[m.id] = m

    @classmethod
    def load(cls, path: Optional[Path] = None, space: Optional[AxisSpace] = None) -> "Catalog":
        space = space or AxisSpace.load()
        path = path or DATA_DIR / "catalog.json"
        raw = json.loads(Path(path).read_text())
        movies = [
            Movie(
                id=m["id"],
                title=m["title"],
                year=int(m["year"]),
                kind=m.get("kind", "film"),
                axes={k: float(v) for k, v in m["axes"].items()},
                tags=tuple(m.get("tags", ())),
            )
            for m in raw["movies"]
        ]
        return cls(movies, space)

    def __len__(self) -> int:
        return len(self._movies)

    def __iter__(self) -> Iterator[Movie]:
        return iter(self._movies)

    def __getitem__(self, movie_id: str) -> Movie:
        return self._by_id[movie_id]

    def __contains__(self, movie_id: object) -> bool:
        return movie_id in self._by_id

    @property
    def ids(self) -> List[str]:
        return [m.id for m in self._movies]

    def get(self, movie_id: str, default: Optional[Movie] = None) -> Optional[Movie]:
        return self._by_id.get(movie_id, default)

    def subset(self, movie_ids: Sequence[str]) -> "Catalog":
        return Catalog([self[i] for i in movie_ids], self.space)

    def centroid(self, movie_ids: Sequence[str]) -> Vector:
        return self.space.centroid([self[i].axes for i in movie_ids])

    def vectors(self) -> Mapping[str, Vector]:
        return {m.id: m.axes for m in self._movies}
