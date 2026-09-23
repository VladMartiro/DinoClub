"""Tests for the audit itself.

These use `--sample` so the suite stays fast; the CLI enumerates all
1,048,576 answer sets by default.
"""

import pytest

from dinoclub.quiz.analysis import (
    entropy_ratio,
    magnitude_sensitivity,
    presentation_validity,
    total_answer_space,
    _tabulate,
)

SAMPLE = 4000


def _norms_all_equal(quiz) -> bool:
    """With every dinosaur the same distance from centre, |v|^2 is a constant
    across candidates and the winner depends on direction alone -- so no
    rescaling of the user vector can change it. Tests that expect calibration
    to *change* outcomes have to know this."""
    norms = list(quiz.dinosaurs.norms().values())
    return max(norms) - min(norms) < 1e-9


def test_answer_space_size(quiz):
    assert total_answer_space(quiz.bank) == 4 ** len(quiz.bank)


def test_entropy_ratio_extremes():
    assert entropy_ratio({"a": 1, "b": 1, "c": 1, "d": 1}) == pytest.approx(1.0)
    assert entropy_ratio({"a": 10, "b": 0}) == pytest.approx(0.0)
    assert entropy_ratio({}) == 0.0


def test_no_dinosaur_is_unreachable(quiz):
    """The headline property. A result nobody can ever get is a bug."""
    wins = _tabulate(quiz.bank, quiz.dinosaurs, apply_normalisation=True,
                     sample=40000, seed=1)
    unreachable = [k for k, v in wins.items() if v == 0]
    assert not unreachable, "unreachable: {}".format(unreachable)


def test_win_distribution_is_reasonably_even(quiz):
    wins = _tabulate(quiz.bank, quiz.dinosaurs, apply_normalisation=True,
                     sample=SAMPLE, seed=1)
    assert entropy_ratio(wins) > 0.85


def test_calibration_keeps_everyone_inside_the_box(quiz):
    """The property that makes the radar chart and match percentage possible,
    and the one raw totals fail outright."""
    raw = presentation_validity(quiz.bank, quiz.dinosaurs,
                                apply_normalisation=False, sample=SAMPLE, seed=1)
    calibrated = presentation_validity(quiz.bank, quiz.dinosaurs,
                                       apply_normalisation=True, sample=SAMPLE, seed=1)
    assert raw["out_of_box"] > 0.8
    assert calibrated["out_of_box"] == 0.0
    assert raw["negative_match"] > 0.0
    assert calibrated["negative_match"] == 0.0


def test_calibration_brings_the_clouds_together(quiz):
    calibrated = presentation_validity(quiz.bank, quiz.dinosaurs,
                                       apply_normalisation=True, sample=SAMPLE, seed=1)
    dinosaur_norm = sum(quiz.dinosaurs.norms().values()) / len(quiz.dinosaurs)
    assert 0.5 < calibrated["mean_norm"] / dinosaur_norm < 1.5


def test_calibration_preserves_magnitude_information(quiz):
    """Raw totals dwarf the dinosaur vectors, so the |v|^2 term washes out and
    matching drifts toward pure direction. Calibration should recover it."""
    raw = magnitude_sensitivity(quiz.bank, quiz.dinosaurs,
                                apply_normalisation=False, sample=SAMPLE, seed=1)
    calibrated = magnitude_sensitivity(quiz.bank, quiz.dinosaurs,
                                       apply_normalisation=True, sample=SAMPLE, seed=1)
    if _norms_all_equal(quiz):
        # Direction-only matching: scale is invisible, so both must agree.
        assert calibrated == pytest.approx(raw)
    else:
        assert calibrated > raw


def test_spread_trades_clamping_against_rarity(quiz):
    """The documented trade-off must actually hold, or the knob is a lie."""
    low = presentation_validity(quiz.bank, quiz.dinosaurs, apply_normalisation=True,
                                spread=0.55, sample=SAMPLE, seed=1)
    high = presentation_validity(quiz.bank, quiz.dinosaurs, apply_normalisation=True,
                                 spread=1.15, sample=SAMPLE, seed=1)
    assert low["clamped"] < high["clamped"]

    low_wins = _tabulate(quiz.bank, quiz.dinosaurs, apply_normalisation=True,
                         spread=0.55, sample=40000, seed=1)
    high_wins = _tabulate(quiz.bank, quiz.dinosaurs, apply_normalisation=True,
                          spread=1.15, sample=40000, seed=1)
    if _norms_all_equal(quiz):
        assert low_wins == high_wins
    else:
        assert min(low_wins.values()) < min(high_wins.values())


def test_default_spread_is_plain_moment_matching(quiz):
    """No tuned constant in the default path."""
    from dinoclub.quiz.scoring import DEFAULT_SPREAD
    assert DEFAULT_SPREAD == 1.0
