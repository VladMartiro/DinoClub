"""Guardrails on the hand-authored data files.

These are the tests most likely to actually fire, because the data is the part
a human edits most often and the part with no type checker.
"""


def test_catalog_vectors_are_complete_and_in_range(engine):
    for movie in engine.catalog:
        engine.space.validate(movie.axes, where=movie.id)


def test_movie_ids_are_unique_and_slug_like(engine):
    ids = engine.catalog.ids
    assert len(ids) == len(set(ids))
    for mid in ids:
        assert mid == mid.lower()
        assert " " not in mid


def test_persona_exemplars_resolve(engine):
    for persona in engine.personas:
        assert persona.exemplars
        for movie_id in persona.exemplars:
            assert movie_id in engine.catalog


def test_personas_are_distinguishable(engine):
    """If two anchors collapse, no amount of quiz can separate them."""
    a, b, distance = engine.personas.closest_pair()
    assert distance > 0.08, "personas {} and {} are too close ({:.3f})".format(a, b, distance)


def test_every_persona_is_reachable(engine):
    """Each persona must win for *someone*. A persona no user can ever be told
    they are is dead weight in the quiz and a bug in the anchors."""
    from dinoclub.recommend.profile import Profile

    winners = set()
    for persona in engine.personas:
        profile = Profile.from_vector(engine.space, persona.anchor)
        winners.add(engine.personas.best(profile)[0].id)
    assert winners == set(engine.personas.ids)


def test_every_question_option_carries_evidence(engine):
    for question in engine.bank:
        assert len(question.options) >= 2
        for option in question.options:
            assert option.evidence
            assert option.label.strip()


def test_every_axis_is_touched_by_some_question(engine):
    """An axis no question asks about can only ever sit at the prior, which
    makes it dead weight in matching."""
    touched = {
        key
        for question in engine.bank
        for option in question.options
        for key in option.evidence
    }
    assert set(engine.space.keys) == touched
