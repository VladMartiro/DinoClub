# Dino Club

A "what type of dinosaur are you?" quiz that is actually a small vector-matching
engine, plus a movie recommender for the club's film nights.

```console
$ pip install -e . && dino-quiz
```

The quiz scores your little dinosaur traits on 4 dimenstions vector-matches you to the closest dino archetype Every number below is reproducible with
`dino-quiz-audit`.

---

## algo

### space

The axes are set between -5 and 5. Every answer option and every dinosaur is a
point in the same box.

| Axis | −5 | +5 |
|---|---|---|
| `diet` | Gatherer | Hunter |
| `social` | Team player | Lone dino |
| `strategy` | Tough and durable | Fast and agile |
| `temperament` | Strong brute forcer | Smart and cunning |

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

An answer option moves you along the axes:

```json
{
  "id": "brainstorm",
  "text": "I pull in a few people and we find a clever way around it.",
  "effects": { "diet": -1, "social": -5, "strategy": 3, "temperament": 4 }
}
```

### point accumulating

Sum the effects of every pciked option:

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

### calibration

The raw totals are unbounded. A social coordinate ranges over roughly
[-47, +34] while every dinosaur sits in [−5, +5]. Because of this we can't compare the axes so we have to expand the distance:

```
‖u − v‖²  =  ‖u‖²  −  2(u · v)  +  ‖v‖²
```

`‖u‖²` is identical for every candidate, so the winner is whichever dinosaur
maximises `2(u · v) − ‖v‖²`. That `‖v‖²` is a fixed penalty on dinosaurs far
from the origin

- ‖u‖ > ‖v‖ -> `‖v‖²` is negligible so only direction is taken.
- ‖u‖ < ‖v‖ -> `‖v‖²` dominates and everyone collapses onto the dinosaurs
  nearest the origin.

So rescale each axis so the *spread of user coordinates matches the spread of
dinosaur coordinates* on that axis:

```
scale[a] = sd(dinosaur coordinates on a) / sd(user totals on a)
```

The user standard deviation is computed, a raw total is a
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

### measuring

Ordinary Euclidean distance unweighted:

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

for example nearest wins: **Dilophosaurus**.

The distance also gives a presentable match percentage. The furthest two points
in the box are `√(4 × 10²) = 20` apart, so:

```
match% = 100 × (1 − d / 20)     →  100 × (1 − 3.316/20)  =  83.4%
```

### ranking

A softmax over negative distance gives a distribution of matches in descending order

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

---

## Does it work

idk lol I made up most of it regarding personalities.

### Calibration is not optional

| Over all 1,048,576 answer sets | raw totals | calibrated |
|---|---:|---:|
| user lands outside the dinosaurs' [−5,+5] box | **94.1%** | 0.0% |
| match percentage comes out **negative** | **7.8%** | 0.0% |
| mean match percentage | 42.0 | 79.6 |
| typical ‖u‖ (dinosaurs sit at ‖v‖ ≈ 7.45) | 16.39 | 6.06 |

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

## A note on data

This repository contains no club member data and never will. What is public
here, what stays in the private site repo, and why anonymising a 40-person
response set does not actually anonymise it, are in
[`docs/public-private-split.md`](docs/public-private-split.md).

MIT licensed.
