"""Synthetic users, so the system can be evaluated before it has real ones.

A simulated user is a persona anchor plus Gaussian noise -- a real person who
is *mostly* a Thrill-Seeker but has a soft spot for animated dinosaurs. They
answer questions by softmax over how well each option matches their true
vector, with a noise temperature standing in for the fact that people answer
quizzes inconsistently.

Note the deliberate asymmetry: the quiz's information-gain estimate reasons
about persona *anchors*, while simulated users answer from their *own noisy
vector*. If those were the same model the evaluation would be circular. They
are not, so the numbers at least measure robustness to users who do not sit
exactly on an archetype -- which is every user.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..catalog import Catalog
from ..personas import PersonaSet
from ..profile import Profile
from ..survey import Question, QuizBank, QuizSession
from ..spaces import Vector

#: How inconsistently simulated users answer. 0 = always pick the best-matching
#: option; higher = noisier. 0.3 is roughly "picks the best option ~70% of the
#: time on a four-option question".
ANSWER_NOISE = 0.3


@dataclass
class SimulatedUser:
    id: str
    persona_id: str
    true_vector: Vector

    def profile(self, space) -> Profile:
        """A fully-confident profile at the true vector -- the oracle we grade against."""
        return Profile.from_vector(space, self.true_vector, weight=20.0)

    def choose(self, question: Question, rng: random.Random, noise: float = ANSWER_NOISE) -> str:
        """Sample an answer given the user's true taste."""
        logits = []
        for opt in question.options:
            weights = {k: 1.0 for k in opt.evidence}
            num = sum(
                weights[k] * (opt.evidence[k] - self.true_vector[k]) ** 2 for k in opt.evidence
            )
            d = (num / sum(weights.values())) ** 0.5
            logits.append((opt.id, -d / max(noise, 1e-6)))
        top = max(v for _, v in logits)
        weights_ = [(oid, math.exp(v - top)) for oid, v in logits]
        total = sum(w for _, w in weights_)
        draw = rng.random() * total
        acc = 0.0
        for oid, w in weights_:
            acc += w
            if draw <= acc:
                return oid
        return weights_[-1][0]

    def relevant_movies(self, catalog: Catalog, m: int = 5) -> List[str]:
        """Ground truth: the m movies this user would actually like best."""
        oracle = self.profile(catalog.space)
        scored = [(mv.id, oracle.similarity_to(mv.axes)) for mv in catalog]
        scored.sort(key=lambda ms: (-ms[1], ms[0]))
        return [mid for mid, _ in scored[:m]]


def sample_users(
    personas: PersonaSet,
    n: int = 200,
    *,
    sigma: float = 0.12,
    seed: int = 7,
) -> List[SimulatedUser]:
    """Draw n users, spread evenly across personas, jittered by `sigma`."""
    rng = random.Random(seed)
    space = personas.space
    ids = personas.ids
    users = []
    for i in range(n):
        persona = personas[ids[i % len(ids)]]
        vec = {
            k: min(1.0, max(0.0, persona.anchor[k] + rng.gauss(0.0, sigma)))
            for k in space.keys
        }
        users.append(
            SimulatedUser(id="sim-{:04d}".format(i), persona_id=persona.id, true_vector=vec)
        )
    return users


def take_quiz(
    user: SimulatedUser,
    bank: QuizBank,
    personas: PersonaSet,
    *,
    strategy: str = "adaptive",
    max_questions: int = 6,
    min_questions: Optional[int] = None,
    confidence_target: float = 1.01,
    noise: float = ANSWER_NOISE,
    seed: int = 0,
) -> QuizSession:
    """Run one simulated user through the quiz.

    `confidence_target` defaults above 1.0 so the session always asks exactly
    `max_questions` -- which is what the length ablation needs. Pass a real
    target to measure early stopping instead.
    """
    rng = random.Random(seed)
    session = QuizSession(
        bank,
        personas,
        strategy=strategy,
        max_questions=max_questions,
        min_questions=max_questions if min_questions is None else min_questions,
        confidence_target=confidence_target,
    )
    while not session.done:
        question = session.next_question()
        if question is None:
            break
        session.answer(question.id, user.choose(question, rng, noise))
    return session
