# What is public, what stays private

This repo is deliberately split along a line that is both a privacy boundary
and a good engineering boundary: **`dinoclub` is a library, the club website is
an application.** The library knows nothing about the club.

## The rule

> Nothing that identifies a club member, and nothing that only the club needs,
> ever enters this repository.

## Public (this repo — `dinoclub`)

| What | Why it is safe |
|---|---|
| The algorithms: trait matching, EIG question selection, MMR ranking | No data in them |
| `data/catalog.json` | Public facts about published films |
| `data/questions.json`, `data/personas.json` | Written by us, about dinosaurs |
| The eval harness and **synthetic** users | Generated, not collected |
| Benchmark results, docs, notebooks | Aggregate numbers only |

This is the half that demonstrates skill, and it is the larger half. Nothing
about keeping the club's data private weakens the portfolio case — a reviewer
wants to see the modelling, the evaluation and the judgement, none of which
require a single real user.

## Private (a separate repo — e.g. `dinoclub-site`)

| What | Why it stays out |
|---|---|
| Real quiz responses, `data/ratings.csv` | Personal data about identifiable students |
| Member roster, emails, attendance | Same |
| Private Discord/group links, meeting locations | Club safety, not ML |
| API keys, deploy config, analytics IDs | Credentials |
| Anything a member assumed was internal | The assumption is the reason |

The private repo depends on the public one:

```
# dinoclub-site/requirements.txt
dinoclub @ git+https://github.com/<you>/DinoClub@v0.2.0
```

So the website imports the engine, loads its own private catalog overlay and
real ratings, and publishes nothing back.

## Why real ratings cannot be published, even anonymized

A club has tens of members, not thousands. With a catalog this small, a
"anonymous" rating vector is close to a fingerprint: knowing two or three
films someone mentioned liking is often enough to pick their row out of the
file. Dropping the names does not fix this. If you ever do want to publish
data, publish *aggregates* (per-movie means, axis distributions) with a
minimum bucket size, after asking members — and say in the README that you
asked.

## Practical guardrails

1. **Two repos from the start.** Splitting later means rewriting history to
   purge whatever leaked, which is far worse than the ten minutes it costs now.
2. **`.gitignore` blocks the private paths by name**, so the private files
   have a natural home (`data/ratings.csv`) that git refuses to stage even if
   you develop both in one working tree.
3. **`data/ratings.example.csv` is committed; `data/ratings.csv` is not.** The
   schema is public, the contents are not. That is enough for anyone to run
   your code on their own data.
4. **No member-supplied free text, ever.** The quiz collects option ids, not
   sentences. Structured answers cannot accidentally contain someone's name.
5. **Check before the first push:** `git log -p | grep -iE 'ratings\.csv|@umd\.edu'`
   should return nothing.

## The site itself

Publish the personality test; keep the club pages behind the split. The test
is the interesting artifact and works fine for a stranger. The meeting times
and group links are for members and can live on a separate, unlisted page or
behind whatever login the club already uses.
