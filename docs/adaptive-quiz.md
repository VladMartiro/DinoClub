# The adaptive survey (movie recommender)

> This describes the **recommender's** question policy, not the personality
> test. The personality test asks all ten questions in a fixed order on
> purpose, so that two people who picked the same answers were asked the same
> things. See the [README](../README.md).

## The problem

A ten-question quiz where everybody answers all ten questions in the same
order is wasteful. After three answers, most of the remaining questions are
nearly redundant, and one of them is worth far more than the rest.

## The approach

Treat each question as an experiment and greedily pick the one with the
highest expected information gain about the persona posterior:

```
EIG(q) = H(P) - E_{o ~ P(o)}[ H(P | o) ]
```

Computing that needs `P(o)` — how likely the user is to pick each option —
which we do not know directly. So we marginalize over who we currently think
they are:

```
P(o) = sum_k  P(persona = k) * P(o | persona = k)
```

`P(o | persona = k)` is a softmax over how closely each option's implied
position matches persona `k`'s anchor, compared only on the axes that option
actually speaks to. An option about camp should not be penalized for saying
nothing about kaiju.

This is one-step lookahead, not the optimal sequential policy. The optimal
policy requires searching the tree of all future question/answer sequences and
is intractable for a real-time web quiz. Greedy EIG is the standard
approximation and captures most of the benefit.

## Does it work

From `dino-recommend-eval --users 240` (240 simulated users, 8 personas, chance
accuracy 0.125):

| Questions | adaptive acc@1 | static acc@1 | adaptive ndcg@5 | static ndcg@5 |
|---|---|---|---|---|
| 2 | 0.267 | 0.254 | 0.393 | 0.352 |
| 4 | 0.283 | 0.275 | 0.427 | 0.399 |
| 6 | **0.333** | 0.250 | **0.458** | 0.429 |
| 8 | 0.317 | 0.267 | 0.464 | 0.436 |

Adaptive selection wins consistently on `ndcg@5` (+0.02 to +0.04) and pulls
ahead on persona accuracy from about five questions on. The gap is real but
modest, and it is *smallest* at one question — which makes sense, since with
a uniform prior there is no user-specific information to exploit yet.

## What these numbers do not show

The users are simulated (`dinoclub/recommend/eval/simulate.py`), so this measures
robustness to users who sit off their archetype, not agreement with real
humans. Two specific weaknesses show up clearly:

- **acc@1 plateaus around 0.32.** The `the-maximalist` and `the-thrill-seeker`
  anchors sit 0.144 apart, which is close enough that noisy answers routinely
  swap them. Either the archetypes need pulling apart or the question bank
  needs an item that splits them.
- **Mean confidence *falls* as the quiz gets longer** (0.31 at three
  questions, 0.28 at eight). More evidence is making the posterior flatter,
  which means the softmax temperature is miscalibrated against the amount of
  evidence — a fixed `DEFAULT_TEMPERATURE` cannot be right for both a
  two-answer and an eight-answer profile.

Both are tracked in the README roadmap. They are written down rather than
tuned away because the fix should come from real response data.
