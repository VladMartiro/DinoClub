# Data directory

| File | Committed | What it is |
|---|---|---|
| `ratings.example.csv` | yes | Schema demo: `movie_id,user_id,rating` with rating in 1–5 |
| `ratings.csv` | **no** | Real club ratings. Gitignored. See `docs/public-private-split.md` |

The catalog, questions and personas live in `src/dinoclub/recommend/data/` because they
are package data, shipped with the library. This directory is for datasets
that are an *input* to fitting, not part of the package.

To try the refitting path without real data:

    python scripts/refit_axes.py --self-test
