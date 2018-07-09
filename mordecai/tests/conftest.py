from ..geoparse import Geoparser
import pytest

@pytest.fixture(scope='session', autouse=True)
def geo():
    return Geoparser(threads=False)

@pytest.fixture(scope='session', autouse=True)
def geo_thread():
    return Geoparser(threads=True)
