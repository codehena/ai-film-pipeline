import copy

import pytest

from pipeline.common import config
from pipeline.common.storyboard import load_json, load_schema


@pytest.fixture(scope="session")
def schema():
    return load_schema()


@pytest.fixture
def board():
    """A fresh copy of the real storyboard.json that a test may modify."""
    return copy.deepcopy(load_json(config.STORYBOARD))
