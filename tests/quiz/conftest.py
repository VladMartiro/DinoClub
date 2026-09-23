import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dinoclub.quiz import DinoQuiz  # noqa: E402

# Every test in this directory runs once per dataset. The data files are the
# part a human edits, so both the documented one and the shipped one need the
# same guardrails.
DATASETS = ("full", "mini")


@pytest.fixture(scope="session", params=DATASETS, ids=DATASETS)
def quiz(request):
    return DinoQuiz.load(dataset=request.param)
