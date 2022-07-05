from collections.abc import Mapping
from pathlib import Path

import pytest


DATA_ROOT = Path(__file__).parent / 'data'


@pytest.fixture
def data_root():
    return DATA_ROOT


@pytest.fixture
def custom_mapping():
    return CustomMapping


class CustomMapping(Mapping):
    def __init__(self, inner):
        self.inner = inner

    def __getitem__(self, item):
        return self.inner[item]

    def __len__(self):
        return len(self.inner)

    def __iter__(self):
        return iter(self.inner)
