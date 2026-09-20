import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dinoclub.quiz import DinoQuiz  # noqa: E402


@pytest.fixture(scope="session")
def quiz():
    return DinoQuiz.load()
