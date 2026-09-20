import pytest

from dinoclub.recommend.eval.harness import run_condition
from dinoclub.recommend.eval.metrics import (
    coverage, hit_rate, ndcg_at_k, personalization, precision_at_k, recall_at_k,
)
from dinoclub.recommend.eval.simulate import sample_users, take_quiz


def test_metrics_on_known_rankings():
    recs = ["a", "b", "c", "d", "e"]
    assert hit_rate(recs, {"c"}, 5) == 1.0
    assert hit_rate(recs, {"z"}, 5) == 0.0
    assert recall_at_k(recs, {"a", "b"}, 2) == 1.0
    assert precision_at_k(recs, {"a"}, 5) == pytest.approx(0.2)
    assert ndcg_at_k(recs, {"a"}, 5) == pytest.approx(1.0)
    assert ndcg_at_k(recs, {"e"}, 5) < ndcg_at_k(recs, {"a"}, 5)


def test_metrics_handle_empty_relevant_sets():
    assert recall_at_k(["a"], [], 5) == 0.0
    assert ndcg_at_k(["a"], [], 5) == 0.0
    assert coverage([], 10) == 0.0
    assert personalization([["a"]]) == 0.0


def test_personalization_extremes():
    assert personalization([["a", "b"], ["a", "b"]]) == pytest.approx(0.0)
    assert personalization([["a", "b"], ["c", "d"]]) == pytest.approx(1.0)


def test_simulated_users_are_spread_across_personas(engine):
    users = sample_users(engine.personas, 80)
    assert {u.persona_id for u in users} == set(engine.personas.ids)
    for user in users:
        engine.space.validate(user.true_vector, where=user.id)


def test_simulation_is_reproducible(engine):
    a = sample_users(engine.personas, 20, seed=3)[0].true_vector
    b = sample_users(engine.personas, 20, seed=3)[0].true_vector
    assert a == b


def test_take_quiz_asks_the_requested_number(engine):
    user = sample_users(engine.personas, 8)[0]
    session = take_quiz(user, engine.bank, engine.personas, max_questions=4, seed=1)
    assert len(session.asked) == 4


def test_quiz_beats_random_on_persona_recovery(engine):
    """The floor that makes every other number meaningful."""
    result = run_condition(
        catalog=engine.catalog, personas=engine.personas, bank=engine.bank,
        strategy="adaptive", n_questions=6, n_users=120, seed=11,
    )
    chance = 1.0 / len(engine.personas)
    assert result["persona_acc@1"] > 2 * chance
    assert result["persona_acc@3"] > 3 * chance


def test_more_questions_do_not_hurt(engine):
    """Monotonicity check. Extra evidence making the answer worse points at a
    miscalibrated question rather than at noise."""
    kwargs = dict(catalog=engine.catalog, personas=engine.personas, bank=engine.bank,
                  strategy="adaptive", n_users=160, seed=5)
    short = run_condition(n_questions=2, **kwargs)
    long = run_condition(n_questions=6, **kwargs)
    assert long["persona_acc@3"] >= short["persona_acc@3"] - 0.02
    assert long["ndcg@5"] >= short["ndcg@5"] - 0.02


def test_recommendations_are_not_a_popularity_chart(engine):
    result = run_condition(
        catalog=engine.catalog, personas=engine.personas, bank=engine.bank,
        strategy="adaptive", n_questions=6, n_users=120, seed=11,
    )
    assert result["personalization"] > 0.5
    assert result["coverage"] > 0.4
