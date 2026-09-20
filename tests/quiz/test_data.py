"""Guardrails on the hand-authored trait data.

This is what a human edits most often and what no type checker covers, so
these are the tests most likely to actually fire.
"""

import pytest


def test_dinosaur_vectors_are_complete_and_in_range(quiz):
    for dinosaur in quiz.dinosaurs:
        quiz.space.validate(dinosaur.traits, where=dinosaur.id)


def test_dinosaur_ids_are_unique_and_slug_like(quiz):
    ids = quiz.dinosaurs.ids
    assert len(ids) == len(set(ids))
    for dinosaur_id in ids:
        assert dinosaur_id == dinosaur_id.lower()
        assert " " not in dinosaur_id


def test_every_dinosaur_has_copy_for_the_results_page(quiz):
    for dinosaur in quiz.dinosaurs:
        assert dinosaur.name.strip()
        assert dinosaur.tagline.strip()
        assert len(dinosaur.blurb) > 60


def test_dinosaurs_are_distinguishable(quiz):
    """If two vectors collapse, no set of answers can separate them."""
    a, b, distance = quiz.dinosaurs.closest_pair()
    assert distance > 3.0, "{} and {} are only {:.2f} apart".format(a, b, distance)


def test_every_option_has_an_effect_and_text(quiz):
    for question in quiz.bank:
        assert len(question.options) >= 2
        for option in question.options:
            assert option.text.strip()
            assert any(option.effect(k) != 0 for k in quiz.space.keys), (
                "{}/{} moves nothing".format(question.id, option.id)
            )


def test_every_axis_is_moved_by_some_question(quiz):
    """An axis no question touches stays pinned at 0, which silently makes one
    quarter of the distance metric a constant."""
    for key in quiz.space.keys:
        assert any(q.reach(key) > 0 for q in quiz.bank), "nothing moves {}".format(key)


def test_each_question_discriminates(quiz):
    """A question whose options all say the same thing is just a click."""
    for question in quiz.bank:
        spread = max(
            max(o.effect(k) for o in question.options)
            - min(o.effect(k) for o in question.options)
            for k in quiz.space.keys
        )
        assert spread >= 4, "{} barely separates anyone".format(question.id)


def test_bank_is_not_leaning(quiz):
    """Where does a coin-flip answerer land? It should be near the origin.

    A lean here is a bias no downstream rescaling can undo, because it moves
    the centre of the user cloud rather than its scale.
    """
    for key in quiz.space.keys:
        lean = sum(
            sum(o.effect(key) for o in q.options) / len(q.options) for q in quiz.bank
        )
        assert abs(lean) < 1.0, "bank leans {:+.2f} on {}".format(lean, key)


def test_effects_stay_on_the_scale(quiz):
    for question in quiz.bank:
        for option in question.options:
            for key, value in option.effects.items():
                assert quiz.space.min <= value <= quiz.space.max
