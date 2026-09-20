"""Offline evaluation: metrics, a synthetic-user simulator, and a harness.

There are no real users yet, so every number here comes from simulated ones.
That is a real limitation and it is stated rather than hidden: the simulator
shares a response model with the quiz's own information-gain estimate, so
these results measure *internal consistency*, not accuracy against humans.
They are still useful -- they catch a broken anchor, a dead question, or a
regression in the ranker -- and they give a baseline to compare real data
against once `data/ratings.csv` exists.
"""

from .metrics import coverage, hit_rate, ndcg_at_k, recall_at_k
from .simulate import SimulatedUser, sample_users, take_quiz

__all__ = [
    "coverage",
    "hit_rate",
    "ndcg_at_k",
    "recall_at_k",
    "SimulatedUser",
    "sample_users",
    "take_quiz",
]
