"""The quiz, as an active-learning problem.

The naive version of a personality quiz asks all ten questions in a fixed
order. That wastes the user's attention: after three answers, most questions
tell us nothing we do not already know, and one question is far more
informative than the rest.

So instead we treat each question as an experiment and greedily pick the one
with the highest expected information gain about the persona posterior:

    EIG(q) = H(P) - E_{o ~ P(o)}[ H(P | o) ]

where P(o) is marginalized over who we currently think the user might be:

    P(o) = sum_k P(persona=k) * P(o | persona=k)

and P(o | persona=k) is a softmax over how well each option's implied position
matches persona k's anchor. This is one-step-lookahead, not the optimal
sequential policy -- but the optimal policy is intractable and greedy EIG gets
most of the benefit. `docs/adaptive-quiz.md` has the measured ablation.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

from .personas import DEFAULT_TEMPERATURE, PersonaSet
from .profile import Evidence, Profile
from .spaces import DATA_DIR, AxisSpace

#: How deterministically a persona picks its best-matching option. Lower means
#: we assume people answer more predictably given their type, which makes EIG
#: estimates more confident (and more wrong if the assumption is off).
RESPONSE_TEMPERATURE = 0.25


@dataclass(frozen=True)
class Option:
    id: str
    label: str
    evidence: Mapping[str, float]
    weight: float = 1.0

    def as_evidence(self, source: str) -> List[Evidence]:
        return [
            Evidence(key=k, value=float(v), weight=self.weight, source=source)
            for k, v in self.evidence.items()
        ]


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    options: Sequence[Option]

    def __getitem__(self, option_id: str) -> Option:
        for o in self.options:
            if o.id == option_id:
                return o
        raise KeyError("no option {} on question {}".format(option_id, self.id))


class QuizBank:
    def __init__(self, questions: Sequence[Question], space: AxisSpace):
        self.space = space
        self._questions = tuple(questions)
        self._by_id: Dict[str, Question] = {}
        for q in self._questions:
            if q.id in self._by_id:
                raise ValueError("duplicate question id: {}".format(q.id))
            if len(q.options) < 2:
                raise ValueError("question {} needs at least two options".format(q.id))
            for o in q.options:
                unknown = set(o.evidence) - set(space.keys)
                if unknown:
                    raise ValueError(
                        "question {} option {}: unknown axes {}".format(q.id, o.id, sorted(unknown))
                    )
                if not o.evidence:
                    raise ValueError("question {} option {} carries no evidence".format(q.id, o.id))
            self._by_id[q.id] = q

    @classmethod
    def load(cls, space: Optional[AxisSpace] = None, path: Optional[Path] = None) -> "QuizBank":
        space = space or AxisSpace.load()
        path = path or DATA_DIR / "questions.json"
        raw = json.loads(Path(path).read_text())
        questions = [
            Question(
                id=q["id"],
                text=q["text"],
                options=tuple(
                    Option(
                        id=o["id"],
                        label=o["label"],
                        evidence={k: float(v) for k, v in o["evidence"].items()},
                        weight=float(o.get("weight", 1.0)),
                    )
                    for o in q["options"]
                ),
            )
            for q in raw["questions"]
        ]
        return cls(questions, space)

    def __len__(self) -> int:
        return len(self._questions)

    def __iter__(self) -> Iterator[Question]:
        return iter(self._questions)

    def __getitem__(self, question_id: str) -> Question:
        return self._by_id[question_id]

    @property
    def ids(self) -> List[str]:
        return [q.id for q in self._questions]


def _entropy(dist: Mapping[str, float]) -> float:
    return -sum(p * math.log(p) for p in dist.values() if p > 0.0)


def option_likelihoods(
    question: Question,
    personas: PersonaSet,
    temperature: float = RESPONSE_TEMPERATURE,
) -> Dict[str, Dict[str, float]]:
    """P(option | persona), as {persona_id: {option_id: prob}}.

    An option's "implied position" is just its evidence values, and we compare
    it to the anchor only on the axes it actually speaks to -- an option about
    camp should not be penalized for saying nothing about kaiju.
    """
    space = personas.space
    out: Dict[str, Dict[str, float]] = {}
    for persona in personas:
        logits = {}
        for opt in question.options:
            weights = {k: 1.0 for k in opt.evidence}
            d = space.distance(opt.evidence, persona.anchor, weights)
            logits[opt.id] = -d / temperature
        top = max(logits.values())
        exps = {k: math.exp(v - top) for k, v in logits.items()}
        total = sum(exps.values())
        out[persona.id] = {k: v / total for k, v in exps.items()}
    return out


def expected_information_gain(
    question: Question,
    profile: Profile,
    personas: PersonaSet,
    *,
    persona_temperature: float = DEFAULT_TEMPERATURE,
    response_temperature: float = RESPONSE_TEMPERATURE,
) -> float:
    """Expected reduction in persona-posterior entropy, in nats."""
    prior = personas.posterior(profile, persona_temperature)
    prior_entropy = _entropy(prior)
    likelihoods = option_likelihoods(question, personas, response_temperature)

    expected_posterior_entropy = 0.0
    for opt in question.options:
        p_opt = sum(prior[pid] * likelihoods[pid][opt.id] for pid in personas.ids)
        if p_opt <= 0.0:
            continue
        hypothetical = profile.copy().observe_all(opt.as_evidence(source=question.id))
        expected_posterior_entropy += p_opt * _entropy(
            personas.posterior(hypothetical, persona_temperature)
        )
    return prior_entropy - expected_posterior_entropy


class QuizSession:
    """One person taking the quiz.

    Strategies:
      "adaptive" -- greedy expected information gain (the default)
      "static"   -- bank order, for ablation
    """

    def __init__(
        self,
        bank: QuizBank,
        personas: PersonaSet,
        *,
        strategy: str = "adaptive",
        max_questions: int = 6,
        confidence_target: float = 0.65,
        min_questions: int = 3,
        persona_temperature: float = DEFAULT_TEMPERATURE,
    ):
        if strategy not in ("adaptive", "static"):
            raise ValueError("unknown strategy: {}".format(strategy))
        if min_questions > max_questions:
            raise ValueError("min_questions cannot exceed max_questions")
        self.bank = bank
        self.personas = personas
        self.strategy = strategy
        self.max_questions = max_questions
        self.min_questions = min_questions
        self.confidence_target = confidence_target
        self.persona_temperature = persona_temperature
        self.profile = Profile.empty(bank.space)
        self.asked: List[str] = []
        self.answers: List[Tuple[str, str]] = []

    @property
    def remaining(self) -> List[Question]:
        return [q for q in self.bank if q.id not in set(self.asked)]

    @property
    def done(self) -> bool:
        if len(self.asked) >= self.max_questions or not self.remaining:
            return True
        if len(self.asked) < self.min_questions:
            return False
        top = max(self.personas.posterior(self.profile, self.persona_temperature).values())
        return top >= self.confidence_target

    def next_question(self) -> Optional[Question]:
        if self.done:
            return None
        candidates = self.remaining
        if self.strategy == "static":
            return candidates[0]
        scored = [
            (
                expected_information_gain(
                    q,
                    self.profile,
                    self.personas,
                    persona_temperature=self.persona_temperature,
                ),
                q,
            )
            for q in candidates
        ]
        # Ties broken by bank order, which `max` preserves by scanning in order.
        return max(scored, key=lambda sq: sq[0])[1]

    def answer(self, question_id: str, option_id: str) -> "QuizSession":
        if question_id in set(self.asked):
            raise ValueError("question {} already answered".format(question_id))
        question = self.bank[question_id]
        option = question[option_id]
        self.profile.observe_all(option.as_evidence(source=question_id))
        self.asked.append(question_id)
        self.answers.append((question_id, option_id))
        return self

    def result(self):
        from .recommend import Result

        return Result.build(self)
