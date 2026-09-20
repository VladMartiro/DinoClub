"""dinoclub.recommend -- a small, explainable recommender for a very specific taste.

Quickstart:

    from dinoclub.recommend import DinoRec

    engine = DinoRec.load()
    session = engine.start_quiz()
    while not session.done:
        question = session.next_question()
        session.answer(question.id, question.options[0].id)
    print(session.result().to_dict())
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .catalog import Catalog, Movie
from .personas import Persona, PersonaSet
from .profile import Evidence, Profile
from .survey import Option, Question, QuizBank, QuizSession
from .recommend import Recommendation, Result, recommend, score_all
from .spaces import Axis, AxisSpace

__version__ = "0.1.0"

__all__ = [
    "DinoRec",
    "Axis", "AxisSpace",
    "Catalog", "Movie",
    "Persona", "PersonaSet",
    "Evidence", "Profile",
    "Option", "Question", "QuizBank", "QuizSession",
    "Recommendation", "Result", "recommend", "score_all",
]


@dataclass
class DinoRec:
    """The whole system, wired together. This is the only object a web
    backend should need to touch."""

    catalog: Catalog
    personas: PersonaSet
    bank: QuizBank

    @classmethod
    def load(cls, catalog: Optional[Catalog] = None) -> "DinoRec":
        catalog = catalog or Catalog.load()
        return cls(
            catalog=catalog,
            personas=PersonaSet.load(catalog),
            bank=QuizBank.load(catalog.space),
        )

    @property
    def space(self) -> AxisSpace:
        return self.catalog.space

    def start_quiz(self, **kwargs) -> QuizSession:
        return QuizSession(self.bank, self.personas, **kwargs)

    def recommend_for(self, profile: Profile, k: int = 5, **kwargs):
        return recommend(profile, self.catalog, k=k, **kwargs)
