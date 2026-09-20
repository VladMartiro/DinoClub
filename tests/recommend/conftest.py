import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dinoclub.recommend import DinoRec  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    return DinoRec.load()
