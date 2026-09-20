# The taste space (movie recommender)

> This is the **recommender's** ten-axis movie-taste space, and it is separate
> from the personality test's four behavioral axes in `dinoclub.quiz`. Two
> systems, two spaces, on purpose. The personality test is documented in the
> [README](../README.md).

Everything in `dinoclub.recommend` — movies, survey answers, user profiles, taste
personas — lives in the same ten-dimensional space. Each dimension runs from
0.0 to 1.0 and has a name a human can argue about.

| Axis | 0.0 | 1.0 |
|---|---|---|
| `spectacle` | intimate and small-scale | enormous set-pieces |
| `dread` | safe and reassuring | tense, predatory horror |
| `camp` | played completely straight | knowingly ridiculous |
| `wonder` | grounded and matter-of-fact | awe at the prehistoric |
| `heart` | plot over people | characters you cry about |
| `science` | pure fantasy | paleo-accurate |
| `retro` | modern CGI | practical effects, older era |
| `kaiju` | dinosaurs at dinosaur scale | city-flattening titans |
| `kid` | strictly for grown-ups | the whole family |
| `grit` | bloodless | brutal survival |

## Why named axes instead of learned embeddings

A learned embedding would almost certainly rank better. It would also make the
result unexplainable, and an unexplainable personality test is not fun — half
the payoff is the site telling you *"because you want practical effects and
you want them to hurt."*

There is a second, less obvious reason. With 28 items and zero users, there is
nothing to learn *from*. Hand-authored axes are a prior that makes the system
work on day one. The point of the design is that this prior is replaceable,
not permanent:

```
hand-authored axes  ->  axes refit from real ratings  ->  learned item factors
   (today)                (scripts/refit_axes.py)          (with enough data)
```

Each step keeps the same interface (`Movie.axes` is a dict of floats), so the
quiz, the personas and the ranker never need to change.

## Authoring a new movie

Judge each axis independently and against the catalog, not against the
platonic ideal. `retro` is about texture and era, not quality. `kaiju` is
about scale only — *Godzilla (1954)* is 1.0 on `kaiju` and 0.10 on `kid`.

Then run the tests. `tests/test_data_integrity.py` will catch an incomplete
vector, a duplicate id, and — more usefully — a new movie that collapses two
personas into each other.

## Calibration caveat

These values are one person's opinion, entered in one sitting. They have not
been cross-rated by multiple annotators, so there is no inter-rater
reliability figure to report. Until `data/ratings.csv` exists, treat every
number in `catalog.json` as a defensible guess rather than a measurement.
