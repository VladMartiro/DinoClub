"""The dinosaur personality test.

    from dinoclub.quiz import DinoQuiz

    quiz = DinoQuiz.load()
    session = quiz.start()
    while not session.done:
        question = session.next_question()
        session.answer(question.id, question.options[0].id)
    print(session.result().to_dict())

Four behavioral axes, ten questions, ten dinosaurs, and an ordinary Euclidean
distance. The whole algorithm is in `scoring.py` and is about forty lines; the
part worth reading is why step 2 exists. `analysis.py` audits the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .dinosaurs import Dinosaur, DinosaurSet
from .questions import Option, Question, QuestionBank
from .scoring import (
    DEFAULT_TEMPERATURE,
    Match,
    Result,
    accumulate,
    axis_scales,
    normalize,
    rank,
)
from .session import QuizSession
from .traits import Trait, TraitSpace

__all__ = [
    "DinoQuiz",
    "Trait", "TraitSpace",
    "Dinosaur", "DinosaurSet",
    "Option", "Question", "QuestionBank",
    "QuizSession", "Result", "Match",
    "accumulate", "axis_scales", "normalize", "rank", "DEFAULT_TEMPERATURE",
]


@dataclass
class DinoQuiz:
    """The whole test, wired together. The only object a web backend needs."""

    space: TraitSpace
    dinosaurs: DinosaurSet
    bank: QuestionBank

    @classmethod
    def load(cls, space: Optional[TraitSpace] = None) -> "DinoQuiz":
        space = space or TraitSpace.load()
        return cls(
            space=space,
            dinosaurs=DinosaurSet.load(space),
            bank=QuestionBank.load(space),
        )

    def start(self, **kwargs) -> QuizSession:
        return QuizSession(self.bank, self.dinosaurs, **kwargs)

    def score(self, answers, **kwargs) -> Result:
        """Score a set of (question_id, option_id) pairs without a session --
        the path a stateless web backend takes when the frontend collected the
        answers itself."""
        return Result.build(answers, self.bank, self.dinosaurs, **kwargs)

    def questions_payload(self):
        """The question bank as JSON, for a frontend that renders it itself.

        Effects are deliberately included. Anyone can read them in the public
        repo anyway, and hiding them would imply the quiz is a secret rather
        than a design worth showing.
        """
        return [
            {
                "id": q.id,
                "text": q.text,
                "options": [
                    {"id": o.id, "text": o.text, "effects": dict(o.effects)}
                    for o in q.options
                ],
            }
            for q in self.bank
        ]
