from ..geoparse import Geoparser
import pytest

@pytest.fixture(scope='session', autouse=True)
def geo():
    return Geoparser()
