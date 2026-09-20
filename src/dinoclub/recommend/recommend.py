"""Ranking, diversity, and explanation.

Pure relevance ranking on a 28-item catalog produces a very boring list: the
top five are all sequels from one franchise, because they sit in nearly the
same place in taste space. So the final list is re-ranked with MMR (maximal
marginal relevance), trading a little relevance for coverage:

    MMR(i) = lambda * rel(i) - (1 - lambda) * max_{j in selected} sim(i, j)

That knob is the difference between "here are five Jurassic World films" and a
list someone actually discovers something from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .catalog import Catalog, Movie
from .personas import Persona, PersonaSet
from .profile import Profile

#: Relevance/diversity trade-off. 1.0 = pure relevance, 0.0 = pure diversity.
DEFAULT_DIVERSITY_LAMBDA = 0.72


@dataclass(frozen=True)
class Recommendation:
    movie: Movie
    score: float
    reasons: Sequence[str]


def score_all(
    profile: Profile,
    catalog: Catalog,
    *,
    exclude: Sequence[str] = (),
) -> List[Tuple[Movie, float]]:
    """Every candidate, scored by similarity to the profile, best first."""
    blocked = set(exclude)
    scored = [
        (m, profile.similarity_to(m.axes)) for m in catalog if m.id not in blocked
    ]
    scored.sort(key=lambda ms: (-ms[1], ms[0].id))
    return scored


def explain_match(profile: Profile, movie: Movie, n: int = 2) -> List[str]:
    """Why this movie, in the user's own strongest terms.

    We look at the axes where the user has a confident opinion *and* the movie
    agrees, which is more useful than listing the movie's own extremes.
    """
    space = profile.space
    vec = profile.vector
    conf = profile.confidence
    hits = []
    for k in space.keys:
        strength = abs(vec[k] - 0.5) * conf[k]
        agreement = 1.0 - abs(vec[k] - movie.axes[k])
        hits.append((k, strength * agreement))
    hits.sort(key=lambda kv: kv[1], reverse=True)
    return [space[k].describe(movie.axes[k]) for k, s in hits[:n] if s > 0.05]


def recommend(
    profile: Profile,
    catalog: Catalog,
    *,
    k: int = 5,
    exclude: Sequence[str] = (),
    diversity: float = DEFAULT_DIVERSITY_LAMBDA,
    candidate_pool: int = 20,
) -> List[Recommendation]:
    """Top-k with MMR re-ranking over the top `candidate_pool` by relevance."""
    if not 0.0 <= diversity <= 1.0:
        raise ValueError("diversity must be in [0, 1]")
    scored = score_all(profile, catalog, exclude=exclude)
    pool = scored[: max(k, candidate_pool)]
    if not pool:
        return []

    space = catalog.space
    selected: List[Tuple[Movie, float]] = []
    remaining = list(pool)
    while remaining and len(selected) < k:
        best = None
        for movie, rel in remaining:
            if selected:
                redundancy = max(
                    1.0 - space.distance(movie.axes, chosen.axes) for chosen, _ in selected
                )
            else:
                redundancy = 0.0
            mmr = diversity * rel - (1.0 - diversity) * redundancy
            if best is None or mmr > best[0]:
                best = (mmr, movie, rel)
        _, movie, rel = best
        selected.append((movie, rel))
        remaining = [(m, r) for m, r in remaining if m.id != movie.id]

    return [
        Recommendation(movie=m, score=r, reasons=explain_match(profile, m))
        for m, r in selected
    ]


@dataclass(frozen=True)
class Result:
    """Everything the website needs to render one finished quiz."""

    persona: Persona
    confidence: float
    runner_up: Optional[Tuple[Persona, float]]
    posterior: Mapping[str, float]
    profile_summary: Sequence[str]
    recommendations: Sequence[Recommendation]
    questions_asked: int

    @classmethod
    def build(cls, session, *, k: int = 5, catalog: Optional[Catalog] = None) -> "Result":
        catalog = catalog or Catalog.load(space=session.bank.space)
        personas: PersonaSet = session.personas
        ranked = personas.ranked(session.profile, session.persona_temperature)
        top_persona, top_prob = ranked[0]
        # A persona's own exemplars are its definition, not a discovery; they
        # make a poor recommendation list, so they are excluded.
        recs = recommend(
            session.profile,
            catalog,
            k=k,
            exclude=top_persona.exemplars,
        )
        return cls(
            persona=top_persona,
            confidence=top_prob,
            runner_up=ranked[1] if len(ranked) > 1 else None,
            posterior=personas.posterior(session.profile, session.persona_temperature),
            profile_summary=session.profile.explain(3),
            recommendations=recs,
            questions_asked=len(session.asked),
        )

    def to_dict(self) -> Dict:
        """JSON-serializable, for handing to a web frontend."""
        return {
            "persona": {
                "id": self.persona.id,
                "name": self.persona.name,
                "tagline": self.persona.tagline,
                "blurb": self.persona.blurb,
            },
            "confidence": round(self.confidence, 4),
            "runner_up": (
                {"id": self.runner_up[0].id,
                 "name": self.runner_up[0].name,
                 "confidence": round(self.runner_up[1], 4)}
                if self.runner_up else None
            ),
            "posterior": {k: round(v, 4) for k, v in self.posterior.items()},
            "profile_summary": list(self.profile_summary),
            "questions_asked": self.questions_asked,
            "recommendations": [
                {
                    "id": r.movie.id,
                    "title": r.movie.title,
                    "year": r.movie.year,
                    "score": round(r.score, 4),
                    "reasons": list(r.reasons),
                }
                for r in self.recommendations
            ],
        }
