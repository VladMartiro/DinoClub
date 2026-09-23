"""The committed parity fixture must match what this package produces now.

If this fails, either the mini dataset or scoring.py changed. Regenerate with
`python scripts/quiz_parity_fixture.py` and commit the result -- the
TypeScript side's engine.spec.ts then checks the port against it.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import quiz_parity_fixture as fixture_script  # noqa: E402
from dinoclub.quiz import DinoQuiz  # noqa: E402


def test_committed_fixture_matches_python():
    committed = json.loads(fixture_script.FIXTURE.read_text())
    fresh = fixture_script.build(DinoQuiz.load(dataset=fixture_script.DATASET))
    assert committed["cases"] == fresh["cases"], (
        "parity fixture is stale; run scripts/quiz_parity_fixture.py"
    )


def test_fixture_covers_the_edges():
    labels = {c["label"] for c in json.loads(fixture_script.FIXTURE.read_text())["cases"]}
    assert {"all-first", "all-last", "none", "one-answer", "half"} <= labels
