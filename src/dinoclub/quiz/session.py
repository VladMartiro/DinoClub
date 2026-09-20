"""Taking the quiz: one person, one pass through the questions.

Deliberately dumb. The questions are asked in bank order, because a
personality quiz is something people screenshot and compare, and two users who
picked the same answers should have been asked the same things in the same
order. (The movie recommender in `dinoclub.recommend` does the opposite --
it picks each question adaptively -- because there the goal is accuracy per
question asked, not comparability.)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .dinosaurs import DinosaurSet
from .questions import Question, QuestionBank
from .scoring import DEFAULT_TEMPERATURE, Result, accumulate, normalize
from .traits import TraitSpace, Vector


class QuizSession:
    def __init__(
        self,
        bank: QuestionBank,
        dinosaurs: DinosaurSet,
        *,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.bank = bank
        self.dinosaurs = dinosaurs
        self.temperature = temperature
        self.answers: List[Tuple[str, str]] = []

    @property
    def space(self) -> TraitSpace:
        return self.bank.space

    @property
    def answered(self) -> List[str]:
        return [question_id for question_id, _ in self.answers]

    @property
    def remaining(self) -> List[Question]:
        done = set(self.answered)
        return [q for q in self.bank if q.id not in done]

    @property
    def done(self) -> bool:
        return not self.remaining

    @property
    def progress(self) -> Tuple[int, int]:
        return len(self.answers), len(self.bank)

    def next_question(self) -> Optional[Question]:
        remaining = self.remaining
        return remaining[0] if remaining else None

    def answer(self, question_id: str, option_id: str) -> "QuizSession":
        if question_id in set(self.answered):
            raise ValueError("question {} already answered".format(question_id))
        # Raises if either id is unknown, before any state changes.
        self.bank[question_id][option_id]
        self.answers.append((question_id, option_id))
        return self

    def profile(self) -> Vector:
        """The user's calibrated position, valid at any point mid-quiz."""
        return normalize(accumulate(self.answers, self.bank), self.bank, self.dinosaurs)

    def result(self) -> Result:
        if not self.answers:
            raise ValueError("no answers yet")
        return Result.build(
            self.answers, self.bank, self.dinosaurs, temperature=self.temperature
        )
