import copy
from pathlib import Path

import pytest

from pipeline.common import config
from pipeline.common.storyboard import load_json, load_schema

# Tests use a FIXED storyboard so that writing the real film (storyboard.json)
# never breaks a test whose code did not change. The real file is still
# checked by test_real_storyboard_is_valid.
FIXTURE = Path(__file__).parent / "fixtures" / "storyboard.json"


@pytest.fixture(scope="session")
def schema():
    return load_schema()


@pytest.fixture
def board():
    """A fresh copy of the test fixture storyboard that a test may modify."""
    return copy.deepcopy(load_json(FIXTURE))


@pytest.fixture
def real_board():
    """The real storyboard.json at the repository root."""
    return load_json(config.STORYBOARD)
