import pytest

from dinoclub.recommend.profile import Evidence, Profile
from dinoclub.recommend.survey import QuizSession, expected_information_gain, option_likelihoods


def test_information_gain_is_non_negative(engine):
    """Entropy cannot increase in expectation under a correct Bayesian update.
    A negative value here means the likelihood model and the posterior model
    have drifted apart."""
    profile = Profile.empty(engine.space)
    for question in engine.bank:
        gain = expected_information_gain(question, profile, engine.personas)
        assert gain >= -1e-9, "{} produced negative EIG: {}".format(question.id, gain)


def test_information_gain_discriminates_between_questions(engine):
    """If every question looks equally informative, adaptive selection is a
    no-op and we should stop paying for it."""
    profile = Profile.empty(engine.space)
    gains = [expected_information_gain(q, profile, engine.personas) for q in engine.bank]
    assert max(gains) > 2 * min(gains)


def test_option_likelihoods_are_distributions(engine):
    question = engine.bank[engine.bank.ids[0]]
    likelihoods = option_likelihoods(question, engine.personas)
    assert set(likelihoods) == set(engine.personas.ids)
    for row in likelihoods.values():
        assert sum(row.values()) == pytest.approx(1.0)


def test_adaptive_picks_the_highest_gain_question_first(engine):
    session = QuizSession(engine.bank, engine.personas)
    gains = {q.id: expected_information_gain(q, session.profile, engine.personas)
             for q in engine.bank}
    assert session.next_question().id == max(gains, key=gains.get)


def test_static_strategy_follows_bank_order(engine):
    session = QuizSession(engine.bank, engine.personas, strategy="static")
    assert session.next_question().id == engine.bank.ids[0]


def test_session_never_repeats_a_question(engine):
    session = QuizSession(engine.bank, engine.personas, max_questions=len(engine.bank))
    seen = []
    while not session.done:
        question = session.next_question()
        seen.append(question.id)
        session.answer(question.id, question.options[0].id)
    assert len(seen) == len(set(seen))


def test_session_stops_at_max_questions(engine):
    session = QuizSession(engine.bank, engine.personas, max_questions=3, confidence_target=1.01)
    while not session.done:
        question = session.next_question()
        session.answer(question.id, question.options[0].id)
    assert len(session.asked) == 3


def test_session_stops_early_once_confident(engine):
    session = QuizSession(
        engine.bank, engine.personas, max_questions=10, min_questions=2, confidence_target=0.2
    )
    while not session.done:
        question = session.next_question()
        session.answer(question.id, question.options[0].id)
    assert 2 <= len(session.asked) < 10


def test_answering_twice_is_rejected(engine):
    session = QuizSession(engine.bank, engine.personas)
    question = session.next_question()
    session.answer(question.id, question.options[0].id)
    with pytest.raises(ValueError):
        session.answer(question.id, question.options[0].id)


def test_unknown_strategy_is_rejected(engine):
    with pytest.raises(ValueError):
        QuizSession(engine.bank, engine.personas, strategy="vibes")


def test_posterior_sums_to_one_throughout(engine):
    session = QuizSession(engine.bank, engine.personas, max_questions=5, confidence_target=1.01)
    while not session.done:
        posterior = engine.personas.posterior(session.profile)
        assert sum(posterior.values()) == pytest.approx(1.0)
        question = session.next_question()
        session.answer(question.id, question.options[0].id)
    assert sum(engine.personas.posterior(session.profile).values()) == pytest.approx(1.0)


def test_answers_actually_change_the_outcome(engine):
    """Two users with opposite answers must not land on the same persona."""
    def run(pick_first):
        session = QuizSession(engine.bank, engine.personas, max_questions=6,
                              confidence_target=1.01, strategy="static")
        while not session.done:
            question = session.next_question()
            index = 0 if pick_first else len(question.options) - 1
            session.answer(question.id, question.options[index].id)
        return engine.personas.best(session.profile)[0].id

    assert run(True) != run(False)
