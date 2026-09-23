"""The question bank.

An option does not point at a dinosaur. It moves the user along behavioral
axes, and which dinosaur they are falls out of the geometry at the end. That
indirection is what lets two people reach the same dinosaur by different
routes, and it is why adding a dinosaur does not require rewriting any
questions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence

from .traits import DEFAULT_DATASET, TraitSpace, Vector, data_dir


@dataclass(frozen=True)
class Option:
    id: str
    text: str
    effects: Mapping[str, float]

    def effect(self, key: str) -> float:
        return float(self.effects.get(key, 0.0))


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    options: Sequence[Option]

    def __getitem__(self, option_id: str) -> Option:
        for option in self.options:
            if option.id == option_id:
                return option
        raise KeyError("no option {} on question {}".format(option_id, self.id))

    def reach(self, key: str) -> float:
        """The largest absolute move this question can make on one axis."""
        return max(abs(option.effect(key)) for option in self.options)


class QuestionBank:
    def __init__(self, questions: Sequence[Question], space: TraitSpace):
        if not questions:
            raise ValueError("need at least one question")
        self.space = space
        self._questions = tuple(questions)
        self._by_id: Dict[str, Question] = {}
        for question in self._questions:
            if question.id in self._by_id:
                raise ValueError("duplicate question id: {}".format(question.id))
            if len(question.options) < 2:
                raise ValueError("question {} needs at least two options".format(question.id))
            seen = set()
            for option in question.options:
                if option.id in seen:
                    raise ValueError(
                        "duplicate option {} on question {}".format(option.id, question.id)
                    )
                seen.add(option.id)
                unknown = set(option.effects) - set(space.keys)
                if unknown:
                    raise ValueError(
                        "question {} option {}: unknown traits {}".format(
                            question.id, option.id, sorted(unknown)
                        )
                    )
                for key, value in option.effects.items():
                    if not space.min <= float(value) <= space.max:
                        raise ValueError(
                            "question {} option {}: {} = {} outside the scale".format(
                                question.id, option.id, key, value
                            )
                        )
            self._by_id[question.id] = question

    @classmethod
    def load(
        cls,
        space: Optional[TraitSpace] = None,
        path: Optional[Path] = None,
        *,
        dataset: str = DEFAULT_DATASET,
    ) -> "QuestionBank":
        space = space or TraitSpace.load(dataset=dataset)
        raw = json.loads(Path(path or data_dir(dataset) / "questions.json").read_text())
        return cls(
            [
                Question(
                    id=q["id"],
                    text=q["text"],
                    options=tuple(
                        Option(
                            id=o["id"],
                            text=o["text"],
                            effects={k: float(v) for k, v in o["effects"].items()},
                        )
                        for o in q["options"]
                    ),
                )
                for q in raw["questions"]
            ],
            space,
        )

    def __len__(self) -> int:
        return len(self._questions)

    def __iter__(self) -> Iterator[Question]:
        return iter(self._questions)

    def __getitem__(self, question_id: str) -> Question:
        return self._by_id[question_id]

    def __contains__(self, question_id: object) -> bool:
        return question_id in self._by_id

    @property
    def ids(self) -> List[str]:
        return [q.id for q in self._questions]

    def spans(self) -> Vector:
        """Per axis, the furthest a user could possibly travel from neutral.

        span[a] = sum over questions of the largest |effect| on axis a.

        This is the denominator that makes the raw totals comparable with the
        dinosaur vectors, and it is computed from the bank rather than
        hardcoded so that editing a question cannot silently invalidate it.
        """
        return {
            key: sum(question.reach(key) for question in self._questions)
            for key in self.space.keys
        }

    def balance(self) -> Dict[str, Dict[str, float]]:
        """Per axis, how far a user can go in each direction.

        The two should be close. A bank where `social` can reach -48 but only
        +34 has a built-in lean toward the pack end, which no normalisation
        can undo -- it has to be fixed in the questions.
        """
        report = {}
        for key in self.space.keys:
            upward = sum(max(0.0, max(o.effect(key) for o in q.options)) for q in self._questions)
            downward = sum(min(0.0, min(o.effect(key) for o in q.options)) for q in self._questions)
            report[key] = {
                "max_positive": upward,
                "max_negative": downward,
                "skew": upward + downward,
            }
        return report
