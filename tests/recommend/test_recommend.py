import pytest

from dinoclub.recommend.profile import Profile
from dinoclub.recommend.recommend import recommend, score_all


def _persona_profile(engine, persona_id):
    return Profile.from_vector(engine.space, engine.personas[persona_id].anchor)


def test_scores_are_sorted_and_bounded(engine):
    scored = score_all(_persona_profile(engine, "the-thrill-seeker"), engine.catalog)
    assert len(scored) == len(engine.catalog)
    assert all(0.0 < s <= 1.0 for _, s in scored)
    assert scored == sorted(scored, key=lambda ms: (-ms[1], ms[0].id))


def test_exclusions_are_honored(engine):
    blocked = ["jurassic-park-1993", "godzilla-1954"]
    ids = [m.id for m, _ in score_all(_persona_profile(engine, "the-maximalist"),
                                      engine.catalog, exclude=blocked)]
    assert not set(blocked) & set(ids)


def test_recommendations_are_unique_and_the_right_length(engine):
    recs = recommend(_persona_profile(engine, "the-soft-touch"), engine.catalog, k=5)
    ids = [r.movie.id for r in recs]
    assert len(ids) == 5
    assert len(set(ids)) == 5


def test_different_personas_get_different_lists(engine):
    a = {r.movie.id for r in recommend(_persona_profile(engine, "the-fact-checker"), engine.catalog)}
    b = {r.movie.id for r in recommend(_persona_profile(engine, "the-gremlin"), engine.catalog)}
    assert len(a & b) <= 1


def test_diversity_knob_changes_the_list(engine):
    profile = _persona_profile(engine, "the-maximalist")
    greedy = [r.movie.id for r in recommend(profile, engine.catalog, k=5, diversity=1.0)]
    mixed = [r.movie.id for r in recommend(profile, engine.catalog, k=5, diversity=0.4)]
    assert greedy != mixed


def test_pure_relevance_matches_raw_ranking(engine):
    """diversity=1.0 must reduce exactly to top-k by score, or MMR is wrong."""
    profile = _persona_profile(engine, "the-purist")
    greedy = [r.movie.id for r in recommend(profile, engine.catalog, k=5, diversity=1.0)]
    raw = [m.id for m, _ in score_all(profile, engine.catalog)][:5]
    assert greedy == raw


def test_diversity_out_of_range_is_rejected(engine):
    with pytest.raises(ValueError):
        recommend(_persona_profile(engine, "the-kaiju-head"), engine.catalog, diversity=1.5)


def test_persona_exemplars_rank_highly_for_that_persona(engine):
    """The sanity check that ties personas to the catalog: if a persona's own
    exemplars are not near the top of its own ranking, the anchor is wrong."""
    for persona in engine.personas:
        ranked = [m.id for m, _ in score_all(_persona_profile(engine, persona.id), engine.catalog)]
        positions = [ranked.index(e) for e in persona.exemplars]
        assert min(positions) < 5, "{}: exemplars rank at {}".format(persona.id, positions)


def test_result_serializes(engine):
    from dinoclub.recommend.survey import QuizSession

    session = QuizSession(engine.bank, engine.personas, max_questions=4, confidence_target=1.01)
    while not session.done:
        question = session.next_question()
        session.answer(question.id, question.options[0].id)
    payload = session.result().to_dict()
    assert payload["persona"]["id"] in engine.personas.ids
    assert 0.0 <= payload["confidence"] <= 1.0
    assert len(payload["recommendations"]) == 5
    assert sum(payload["posterior"].values()) == pytest.approx(1.0, abs=1e-3)
