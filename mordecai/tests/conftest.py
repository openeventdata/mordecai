from ..geoparse import Geoparse
import pytest

@pytest.fixture(scope='session', autouse=True)
def geo():
    return Geoparse()
