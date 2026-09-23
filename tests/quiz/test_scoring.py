"""The algorithm itself: accumulate, calibrate, measure, rank."""

import math

import pytest

from dinoclub.quiz.scoring import accumulate, axis_scales, normalize, rank


def _all_first(quiz):
    return [(q.id, q.options[0].id) for q in quiz.bank]


def test_no_answers_is_the_origin(quiz):
    profile = normalize(accumulate([], quiz.bank), quiz.bank, quiz.dinosaurs)
    assert all(v == 0.0 for v in profile.values())


def test_accumulate_sums_effects(quiz):
    question = quiz.bank[quiz.bank.ids[0]]
    option = question.options[0]
    totals = accumulate([(question.id, option.id)], quiz.bank)
    for key in quiz.space.keys:
        assert totals[key] == pytest.approx(option.effect(key))


def test_accumulate_is_order_independent(quiz):
    answers = _all_first(quiz)
    assert accumulate(answers, quiz.bank) == accumulate(list(reversed(answers)), quiz.bank)


def test_calibration_lands_inside_the_dinosaurs_box(quiz):
    """The property the radar chart and the match percentage both depend on."""
    for answers in (_all_first(quiz), [(q.id, q.options[-1].id) for q in quiz.bank]):
        profile = normalize(accumulate(answers, quiz.bank), quiz.bank, quiz.dinosaurs)
        quiz.space.validate(profile, where="calibrated profile")


def test_calibration_is_linear_before_clamping(quiz):
    """Doubling every effect should double the coordinates, or the scale
    factors are not scale factors."""
    answers = [(q.id, q.options[0].id) for q in list(quiz.bank)[:3]]
    raw = accumulate(answers, quiz.bank)
    once = normalize(raw, quiz.bank, quiz.dinosaurs)
    twice = normalize({k: 2 * v for k, v in raw.items()}, quiz.bank, quiz.dinosaurs)
    for key in quiz.space.keys:
        if abs(twice[key]) < quiz.space.max:  # not clamped
            assert twice[key] == pytest.approx(2 * once[key])


def test_scales_are_positive_and_shrink_the_user(quiz):
    scales = axis_scales(quiz.bank, quiz.dinosaurs)
    assert set(scales) == set(quiz.space.keys)
    for key, value in scales.items():
        assert 0 < value < 1, "{} scale {} is implausible".format(key, value)


def test_scales_match_the_two_clouds(quiz):
    """The defining property: after scaling, user spread equals dinosaur spread."""
    scales = axis_scales(quiz.bank, quiz.dinosaurs)
    for key in quiz.space.keys:
        user_variance = sum(
            sum((o.effect(key) - sum(x.effect(key) for x in q.options) / len(q.options)) ** 2
                for o in q.options) / len(q.options)
            for q in quiz.bank
        )
        coords = [d.traits[key] for d in quiz.dinosaurs]
        mean = sum(coords) / len(coords)
        dino_sd = math.sqrt(sum((c - mean) ** 2 for c in coords) / len(coords))
        assert math.sqrt(user_variance) * scales[key] == pytest.approx(dino_sd)


def test_rank_is_sorted_and_complete(quiz):
    profile = normalize(accumulate(_all_first(quiz), quiz.bank), quiz.bank, quiz.dinosaurs)
    matches = rank(profile, quiz.dinosaurs)
    assert len(matches) == len(quiz.dinosaurs)
    assert [m.distance for m in matches] == sorted(m.distance for m in matches)


def test_confidence_is_a_distribution(quiz):
    profile = normalize(accumulate(_all_first(quiz), quiz.bank), quiz.bank, quiz.dinosaurs)
    matches = rank(profile, quiz.dinosaurs)
    assert sum(m.confidence for m in matches) == pytest.approx(1.0)
    assert all(0.0 <= m.confidence <= 1.0 for m in matches)
    assert matches[0].confidence == max(m.confidence for m in matches)


def test_standing_on_a_dinosaur_gives_that_dinosaur(quiz):
    """Distance zero must win, for every dinosaur. This is both a correctness
    check and a reachability proof: no dinosaur is shadowed by another."""
    for dinosaur in quiz.dinosaurs:
        matches = rank(dinosaur.traits, quiz.dinosaurs)
        assert matches[0].dinosaur.id == dinosaur.id
        assert matches[0].distance == pytest.approx(0.0)
        assert matches[0].match_percent == pytest.approx(100.0)


def test_match_percent_spans_the_box_diagonal(quiz):
    assert quiz.space.max_distance == pytest.approx(math.sqrt(len(quiz.space) * 100))
    assert quiz.space.match_percent(0.0) == pytest.approx(100.0)
    assert quiz.space.match_percent(quiz.space.max_distance) == pytest.approx(0.0)


def test_ties_are_broken_deterministically(quiz):
    """Integer coordinates make exact ties reachable, and a quiz that returned
    a different dinosaur on reload would be worse than a stable loser."""
    profile = quiz.space.zero()
    first = [m.dinosaur.id for m in rank(profile, quiz.dinosaurs)]
    for _ in range(5):
        assert [m.dinosaur.id for m in rank(profile, quiz.dinosaurs)] == first


def test_temperature_must_be_positive(quiz):
    with pytest.raises(ValueError):
        rank(quiz.space.zero(), quiz.dinosaurs, temperature=0)


def test_lower_temperature_is_more_confident(quiz):
    profile = normalize(accumulate(_all_first(quiz), quiz.bank), quiz.bank, quiz.dinosaurs)
    peaky = rank(profile, quiz.dinosaurs, temperature=0.5)[0].confidence
    flat = rank(profile, quiz.dinosaurs, temperature=8.0)[0].confidence
    assert peaky > flat
