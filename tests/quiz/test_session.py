import pytest

from dinoclub.quiz import QuizSession


def _finish(session):
    while not session.done:
        question = session.next_question()
        session.answer(question.id, question.options[0].id)
    return session


def test_session_asks_every_question_in_bank_order(quiz):
    session = _finish(quiz.start())
    assert session.answered == quiz.bank.ids


def test_progress_tracks_answers(quiz):
    session = quiz.start()
    assert session.progress == (0, len(quiz.bank))
    question = session.next_question()
    session.answer(question.id, question.options[0].id)
    assert session.progress == (1, len(quiz.bank))


def test_answering_twice_is_rejected(quiz):
    session = quiz.start()
    question = session.next_question()
    session.answer(question.id, question.options[0].id)
    with pytest.raises(ValueError):
        session.answer(question.id, question.options[0].id)


def test_unknown_ids_are_rejected_without_changing_state(quiz):
    session = quiz.start()
    with pytest.raises(KeyError):
        session.answer(quiz.bank.ids[0], "not-an-option")
    assert session.answers == []


def test_result_needs_at_least_one_answer(quiz):
    with pytest.raises(ValueError):
        quiz.start().result()


def test_partial_profile_is_valid_midway(quiz):
    """The frontend may want a live radar while the user is still answering."""
    session = quiz.start()
    for question in list(quiz.bank)[:4]:
        session.answer(question.id, question.options[0].id)
    quiz.space.validate(session.profile(), where="partial profile")


def test_different_answers_give_different_dinosaurs(quiz):
    first = _finish(quiz.start()).result().winner.id
    session = quiz.start()
    while not session.done:
        question = session.next_question()
        session.answer(question.id, question.options[-1].id)
    assert session.result().winner.id != first


def test_stateless_scoring_matches_a_session(quiz):
    """The path a web backend takes must agree with the session path."""
    session = _finish(quiz.start())
    assert quiz.score(session.answers).winner.id == session.result().winner.id


def test_result_serialises_for_a_frontend(quiz):
    payload = _finish(quiz.start()).result().to_dict()
    assert payload["winner"]["id"] in quiz.dinosaurs.ids
    assert 0.0 <= payload["winner"]["match_percent"] <= 100.0
    assert len(payload["leaderboard"]) == len(quiz.dinosaurs)
    assert len(payload["radar"]) == len(quiz.space)
    assert sum(row["confidence"] for row in payload["leaderboard"]) == pytest.approx(1.0, abs=1e-3)


def test_radar_rows_are_plottable(quiz):
    """Both markers must sit inside the axis range, or the chart is broken."""
    for row in _finish(quiz.start()).result().radar():
        assert quiz.space.min <= row["you"] <= quiz.space.max
        assert quiz.space.min <= row["dinosaur"] <= quiz.space.max


def test_questions_payload_round_trips(quiz):
    payload = quiz.questions_payload()
    assert [q["id"] for q in payload] == quiz.bank.ids
    for question in payload:
        assert question["options"] and all(o["effects"] for o in question["options"])
