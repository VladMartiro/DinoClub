"""Tests for scripts/refit_axes.py.

Skipped unless the `learn` extra is installed, since the core library has no
numpy dependency and `pip install -e .` alone must still give a green suite.
"""

import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy", reason="refitting needs the [learn] extra")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import refit_axes  # noqa: E402


def test_fit_recovers_perturbed_axes(engine):
    """The central claim: the fit beats the prior it started from."""
    ratings, users, truth = refit_axes._synthetic(engine.catalog, 120, 14, 0.35, seed=3)
    fitted = refit_axes.refit(ratings, users, engine.catalog)
    prior = {m.id: dict(m.axes) for m in engine.catalog}
    keys = engine.space.keys
    before = refit_axes._mean_axis_error(prior, truth, keys)
    after = refit_axes._mean_axis_error(fitted, truth, keys)
    assert after < before


def test_more_data_recovers_better(engine):
    """If accuracy did not improve with more ratings, the fit would be
    ignoring the data and just echoing the prior."""
    keys = engine.space.keys
    errors = []
    for n_users, per_user in ((40, 10), (400, 20)):
        ratings, users, truth = refit_axes._synthetic(
            engine.catalog, n_users, per_user, 0.35, seed=3
        )
        fitted = refit_axes.refit(ratings, users, engine.catalog)
        errors.append(refit_axes._mean_axis_error(fitted, truth, keys))
    assert errors[1] < errors[0]


def test_output_stays_in_range(engine):
    ratings, users, _ = refit_axes._synthetic(engine.catalog, 60, 12, 0.35, seed=1)
    fitted = refit_axes.refit(ratings, users, engine.catalog)
    assert set(fitted) == set(engine.catalog.ids)
    for movie_id, axes in fitted.items():
        engine.space.validate(axes, where=movie_id)


def test_users_without_quiz_answers_are_dropped(engine):
    """Their p_u is unknown, so including them would silently re-introduce the
    identifiability problem this design exists to avoid."""
    ratings, users, _ = refit_axes._synthetic(engine.catalog, 60, 12, 0.35, seed=1)
    ghost = ("jurassic-park-1993", "no-such-user", 5.0)
    assert refit_axes.refit(ratings + [ghost], users, engine.catalog) == \
        refit_axes.refit(ratings, users, engine.catalog)


def test_no_usable_ratings_is_an_error(engine):
    with pytest.raises(ValueError):
        refit_axes.refit([("jurassic-park-1993", "ghost", 5.0)], {}, engine.catalog)


def test_self_test_passes():
    assert refit_axes.self_test(seed=3) == 0
