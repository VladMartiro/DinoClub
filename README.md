# Dino Club

A "what type of dinosaur are you?" quiz that is actually a small vector-matching
engine, plus a movie recommender for the club's film nights.

```console
$ pip install -e . && dino-quiz
```

The quiz does not add points to dinosaurs. It scores you on four behavioral
axes, places the dinosaurs on those same axes, and returns whichever one you
are closest to in 4-dimensional space. Every number below is reproducible with
`dino-quiz-audit`.

---

## The algorithm

### Step 0 — the space

Four axes, each running −5 to +5. Every answer option and every dinosaur is a
point in the same box, which is the whole trick: it is what makes distance
between a *person* and a *dinosaur* a meaningful quantity.

| Axis | −5 | +5 |
|---|---|---|
| `diet` | Herbivore / Forager | Carnivore / Active Hunter |
| `social` | Herd / Pack Player | Solitary Apex |
| `strategy` | Heavy Armor / Defense | High Speed / Agility |
| `temperament` | Brute Force / Instinct | Calculating / Cunning |

Each dinosaur is a fixed ideal profile:

| Dinosaur | diet | social | strategy | temperament | ‖v‖ |
|---|---:|---:|---:|---:|---:|
| Tyrannosaurus rex | +5 | +4 | −2 | +1 | 6.78 |
| Velociraptor | +4 | −5 | +5 | +5 | 9.54 |
| Triceratops | −5 | −1 | −4 | −3 | 7.14 |
| Ankylosaurus | −5 | +5 | −5 | −4 | 9.54 |
| Parasaurolophus | −5 | −5 | +2 | +2 | 7.62 |
| Spinosaurus | +5 | +5 | +2 | −3 | 7.94 |
| Pteranodon | +2 | −3 | +5 | −1 | 6.24 |
| Therizinosaurus | −4 | +4 | −2 | +3 | 6.71 |
| Pachycephalosaurus | −4 | +2 | +1 | −5 | 6.78 |
| Dilophosaurus | +3 | +2 | +3 | +4 | 6.16 |

An answer option moves you along the axes; it never names a dinosaur:

```json
{
  "id": "brainstorm",
  "text": "I pull in a few people and we find a clever way around it.",
  "effects": { "diet": -1, "social": -5, "strategy": 3, "temperament": 4 }
}
```

### Step 1 — accumulate

Sum the effects of every option picked. Ten questions, one worked example:

```
question         option          diet  social strategy temperament
big-problem      brainstorm        -1      -5       +3          +4
group-project    angle             +0      +1       +2          +4
free-saturday    out               +2      -2       +5          +1
challenged       dismantle         +2      +1       +0          +5
big-decision     gut               +3      +2       +4          -5
environment      roaming           +2      +0       +5          +0
broken           fix               +3      +3       +2          -2
conflict         say               +4      +3       +0          -3
prepare          shortcut          +1      +0       +5          +4
misread          aggressive        +5      +3       +0          -2
------------------------------------------------------------------
RAW TOTAL                         +21      +6      +26          +6
```

These totals **cannot** be compared to the dinosaurs yet, and that is the part
most implementations of this idea get wrong.

### Step 2 — calibrate

The raw totals are unbounded. A `social` coordinate ranges over roughly
[−47, +34] while every dinosaur sits in [−5, +5]. Two things break at once.

**The axes stop being comparable.** Each axis has a different reachable range,
so one question's worth of disagreement on the widest axis outweighs the same
disagreement on the narrowest. The metric quietly decides one trait matters
more than another, and nobody chose that.

**The extreme dinosaurs get penalised.** Expand the distance:

```
‖u − v‖²  =  ‖u‖²  −  2(u · v)  +  ‖v‖²
```

`‖u‖²` is identical for every candidate, so the winner is whichever dinosaur
maximises `2(u · v) − ‖v‖²`. That `‖v‖²` is a fixed penalty on dinosaurs far
from the origin, and the ratio of ‖u‖ to ‖v‖ decides whether it matters:

- ‖u‖ ≫ ‖v‖ → `‖v‖²` is negligible, only *direction* survives, and how
  strongly you answered stops carrying information.
- ‖u‖ ≪ ‖v‖ → `‖v‖²` dominates and everyone collapses onto the dinosaurs
  nearest the origin.

So rescale each axis so the *spread of user coordinates matches the spread of
dinosaur coordinates* on that axis:

```
scale[a] = sd(dinosaur coordinates on a) / sd(user totals on a)
```

The user standard deviation is computed exactly, not sampled. A raw total is a
sum of independent per-question contributions, so its variance is the sum of
the per-question variances:

```
Var(total on a) = Σ_questions  Var_options( effect[q][o][a] )
```

For this bank:

| Axis | sd(user) | sd(dino) | scale | raw | calibrated |
|---|---:|---:|---:|---:|---:|
| `diet` | 7.198 | 4.294 | 0.5966 | +21 | +12.53 → **+5.00** |
| `social` | 10.118 | 3.789 | 0.3745 | +6 | **+2.25** |
| `strategy` | 8.667 | 3.384 | 0.3904 | +26 | +10.15 → **+5.00** |
| `temperament` | 8.895 | 3.390 | 0.3811 | +6 | **+2.29** |

(Two axes here exceed the box and are clamped to +5 — this answer set is an
extreme one. About half of all answer sets clamp on at least one axis; see
*The calibration trade-off* below.)

So **u = (+5.00, +2.25, +5.00, +2.29)**.

### Step 3 — measure

Ordinary Euclidean distance, unweighted:

```
d(u, v) = √( (u_diet − v_diet)² + (u_social − v_social)²
           + (u_strategy − v_strategy)² + (u_temperament − v_temperament)² )
```

```
Dilophosaurus      √((5.00−3)² + (2.25−2)² + (5.00−3)² + (2.29−4)²) = 3.316
Spinosaurus        √((5.00−5)² + (2.25−5)² + (5.00−2)² + (2.29+3)²) = 6.673
Pteranodon         √((5.00−2)² + (2.25+3)² + (5.00−5)² + (2.29+1)²) = 6.880
Tyrannosaurus rex  √((5.00−5)² + (2.25−4)² + (5.00+2)² + (2.29−1)²) = 7.330
Velociraptor       √((5.00−4)² + (2.25+5)² + (5.00−5)² + (2.29−5)²) = 7.803
```

Nearest wins: **Dilophosaurus**.

The distance also gives a presentable match percentage. The furthest two points
in the box are `√(4 × 10²) = 20` apart, so:

```
match% = 100 × (1 − d / 20)     →  100 × (1 − 3.316/20)  =  83.4%
```

### Step 4 — rank

A softmax over negative distance turns the whole ranking into a distribution,
which is what fills the results page and the "how close the others came" bars:

```
P(k) = exp(−d_k / τ) / Σ_j exp(−d_j / τ)          τ = 2.6
```

```
Dilophosaurus      exp(−3.316/2.6)  →  49.0%
Spinosaurus        exp(−6.673/2.6)  →  13.5%
Pteranodon         exp(−6.880/2.6)  →  12.4%
Tyrannosaurus rex  exp(−7.330/2.6)  →  10.5%
Velociraptor       exp(−7.803/2.6)  →   8.7%
```

τ is a presentation choice, not a modelling one — it changes the confidence
numbers shown, never the winner.

---

## Does it work

There is no ground truth for a personality quiz, so it cannot be scored for
accuracy. It can still be wrong in ways that are measurable. `dino-quiz-audit`
enumerates **all 1,048,576 possible answer sets** — so "this dinosaur is
unreachable" is a proof, not a sample that missed it.

### Calibration is not optional

| Over all 1,048,576 answer sets | raw totals | calibrated |
|---|---:|---:|
| user lands outside the dinosaurs' [−5,+5] box | **94.1%** | 0.0% |
| match percentage comes out **negative** | **7.8%** | 0.0% |
| mean match percentage | 42.0 | 79.6 |
| typical ‖u‖ (dinosaurs sit at ‖v‖ ≈ 7.45) | 16.39 | 6.06 |

The headline is the first row. The design calls for a radar chart with your
four coordinates laid over the dinosaur's ideal profile — and on raw totals,
94% of users cannot be drawn on that chart at all, because they are off it.
7.8% would be shown a negative match percentage.

### Magnitude stops washing out

| | answer sets whose result changes if you answer 2× as strongly |
|---|---:|
| raw totals | 9.7% |
| calibrated | **16.7%** |

Higher is better: it means *how hard you leaned* carries information instead of
dissolving into pure direction.

### Everyone is reachable

Exhaustively, with calibration: **0 of 10 dinosaurs are unreachable**, and the
win distribution has a normalised entropy of 0.937 (1.0 would be perfectly
uniform).

| Dinosaur | share | | Dinosaur | share |
|---|---:|---|---|---:|
| Parasaurolophus | 16.25% | | Spinosaurus | 11.75% |
| Triceratops | 14.82% | | Therizinosaurus | 8.88% |
| Dilophosaurus | 13.31% | | Pachycephalosaurus | 4.68% |
| Tyrannosaurus rex | 12.93% | | Ankylosaurus | 2.62% |
| Pteranodon | 12.81% | | Velociraptor | 1.95% |

### The honest cost

Calibration makes the corner dinosaurs rarer. Correlation between a dinosaur's
‖v‖ and its win share goes from **+0.35 raw to −0.65 calibrated** — that is the
`‖v‖²` penalty becoming visible once the user cloud stops dwarfing it.
Velociraptor and Ankylosaurus, the two most extreme profiles at ‖v‖ = 9.54,
drop to about 2% each.

For a personality quiz that is arguably a feature — a rare result should feel
rare — but it is a consequence of the geometry, not a decision anyone made, so
it is stated rather than tuned away. Pull an extreme dinosaur's coordinates
inward if you want it to come up more often.

### The calibration trade-off

Matching standard deviations cannot match *shapes*. The dinosaur coordinates
are bimodal, piled up at ±4 and ±5; user totals bell around zero. Any linear
map that gives a bell the same spread as a barbell pushes its tails past the
box edge. So there is no setting that both keeps everyone inside the box and
keeps the corner dinosaurs common:

```console
$ dino-quiz-audit --sweep

   spread   clamped    evenness     rarest   magnitude-sens
     0.55     4.7%       0.889     0.12%           18.8%
     0.65    13.9%       0.903     0.35%           18.7%
     0.75    23.2%       0.916     0.75%           18.2%
     0.85    36.5%       0.926     1.23%           17.4%
     1.00    50.5%       0.937     2.04%           16.7%   <- default
     1.15    62.9%       0.944     2.65%           15.9%
```

`spread` is exposed in `dinoclub.quiz.scoring`. The default is 1.0 — plain
moment matching, so the default path has no tuned constant hiding in it.

Fixing this properly would need a non-linear quantile map from the user
distribution onto the dinosaur distribution, which would buy a better win
distribution at the cost of distances no longer meaning what they say. The
simple geometry is worth more here than the last few points of evenness.

---

## One bug worth reading

The first version of step 2 rescaled each axis by its **theoretical span** —
the largest total a user could possibly reach. That looks obviously right and
is wrong: no real answer set maxes out every axis at once, so the user cloud
came out with a standard deviation of ~1.1 per axis against the dinosaurs'
~3.7, roughly 3× too small.

The audit caught it immediately. With ‖u‖ ≪ ‖v‖ the `‖v‖²` term dominated, and:

- Velociraptor and Ankylosaurus became **literally unreachable** — zero wins
  across the entire answer space
- win share correlated with ‖v‖ at **−0.67**
- evenness fell from 0.899 to **0.797**

Normalising by the span was worse than not normalising at all. The fix was to
calibrate against the distribution that actually occurs rather than the one
that theoretically could — which is what `axis_scales` does now.

The general lesson is the reason `analysis.py` exists at all: a quiz has no
accuracy metric, so the only way to catch this class of bug is to ask
structural questions about the whole output space.

---

## Using it

```python
from dinoclub.quiz import DinoQuiz

quiz = DinoQuiz.load()

# Stateless: the frontend collected the answers.
result = quiz.score([("big-problem", "brainstorm"), ("group-project", "angle")])
result.to_dict()      # winner, match %, leaderboard, radar rows, JSON-ready

# Or drive it question by question.
session = quiz.start()
while not session.done:
    question = session.next_question()
    session.answer(question.id, question.options[0].id)
session.result().radar()
```

`quiz.questions_payload()` hands the whole bank to a JS frontend, effects
included — they are readable in this repo anyway, and hiding them would imply
the quiz is a secret rather than a design worth showing.

```console
$ dino-quiz --show-math      # take it in the terminal, with the arithmetic
$ dino-quiz-audit            # the full exhaustive audit (~75s)
$ dino-quiz-audit --sweep    # the calibration trade-off curve
```

## Layout

```
src/dinoclub/quiz/          the personality test
  traits.py        the four axes and the geometry
  dinosaurs.py     the library of ideal profiles
  questions.py     the bank, plus span and balance checks
  scoring.py       accumulate -> calibrate -> measure -> rank
  session.py       one person taking the quiz
  analysis.py      the exhaustive audit
  demo.py          terminal version, with an ASCII radar chart
  data/            traits, dinosaurs, questions (all hand-authored JSON)

src/dinoclub/recommend/     the movie recommender (see below)
```

## Editing the data

The JSON files are meant to be edited. `tests/quiz/test_data.py` guards them:

- `test_dinosaurs_are_distinguishable` — two profiles that collapse cannot be
  told apart by any set of answers
- `test_standing_on_a_dinosaur_gives_that_dinosaur` — every dinosaur wins at
  its own coordinates, so none is shadowed by another
- `test_bank_is_not_leaning` — where does a coin-flip answerer land? It must be
  near the origin. A lean here is a bias no rescaling downstream can undo,
  because it moves the *centre* of the user cloud rather than its scale
- `test_each_question_discriminates` — a question whose options all say the
  same thing is just a click

Run `dino-quiz-audit` after any edit.

---

## The movie recommender

A second, separate system for picking what the club watches: 28 films placed
on ten *taste* axes, an adaptive question policy that picks each question by
expected information gain, and MMR re-ranking so the list is not five Jurassic
World sequels. It solves a different problem in a different space and is kept
deliberately separate.

```console
$ dino-recommend
$ dino-recommend-eval
```

It has its own write-ups: [`docs/axes.md`](docs/axes.md),
[`docs/adaptive-quiz.md`](docs/adaptive-quiz.md).

## Development

No runtime dependencies. `git clone` and `python -m dinoclub.quiz.demo` works
on a stock Python 3.9+.

```console
$ pip install -e ".[dev]" && pytest      # 93 tests
$ pip install -e ".[learn]"              # numpy, for scripts/refit_axes.py
```

## A note on data

This repository contains no club member data and never will. What is public
here, what stays in the private site repo, and why anonymising a 40-person
response set does not actually anonymise it, are in
[`docs/public-private-split.md`](docs/public-private-split.md).

MIT licensed.
