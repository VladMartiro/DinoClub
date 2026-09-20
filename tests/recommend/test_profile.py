import pytest

from dinoclub.recommend.profile import PRIOR_MEAN, Evidence, Profile


def test_empty_profile_sits_at_the_prior(engine):
    profile = Profile.empty(engine.space)
    assert all(v == PRIOR_MEAN for v in profile.vector.values())
    assert all(c == 0.0 for c in profile.confidence.values())


def test_evidence_moves_the_estimate_and_raises_confidence(engine):
    profile = Profile.empty(engine.space)
    before = profile.vector["camp"]
    profile.observe(Evidence("camp", 1.0, weight=2.0))
    assert profile.vector["camp"] > before
    assert 0.0 < profile.confidence["camp"] < 1.0


def test_confidence_approaches_but_never_reaches_one(engine):
    profile = Profile.empty(engine.space)
    for _ in range(50):
        profile.observe(Evidence("dread", 0.9))
    assert profile.confidence["dread"] > 0.95
    assert profile.confidence["dread"] < 1.0


def test_repeated_evidence_converges_to_that_value(engine):
    profile = Profile.empty(engine.space)
    for _ in range(100):
        profile.observe(Evidence("kaiju", 0.8))
    assert profile.vector["kaiju"] == pytest.approx(0.8, abs=0.01)


def test_copy_is_independent(engine):
    """The adaptive quiz simulates hypothetical answers on copies; if copies
    shared state, asking a question would corrupt the real profile."""
    profile = Profile.empty(engine.space)
    clone = profile.copy()
    clone.observe(Evidence("grit", 1.0, weight=5.0))
    assert profile.vector["grit"] == PRIOR_MEAN
    assert clone.vector["grit"] > PRIOR_MEAN


def test_unknown_axis_is_rejected(engine):
    with pytest.raises(ValueError):
        Profile.empty(engine.space).observe(Evidence("velocity", 0.5))


def test_salient_axes_ignore_unanswered_ones(engine):
    profile = Profile.empty(engine.space)
    profile.observe(Evidence("science", 0.95, weight=3.0))
    salient = dict(profile.salient(3))
    assert "science" in salient
