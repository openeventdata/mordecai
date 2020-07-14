from ..geoparse import Geoparser
import pytest

import spacy
nlp = spacy.load('en_core_web_lg', disable=['parser', 'tagger'])

@pytest.fixture(scope='session', autouse=True)
def geo():
    return Geoparser(nlp=nlp, threads=False)

@pytest.fixture(scope='session', autouse=True)
def geo_thread():
    return Geoparser(nlp=nlp, threads=True)
