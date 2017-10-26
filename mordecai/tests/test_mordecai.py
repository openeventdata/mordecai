import os
import sys
import glob
import json
from ..feature_maker import FeatureMaker
from utilities import read_in_admin1, get_admin1

import spacy
nlp = spacy.load('en_core_web_lg')

# switch to pytest fixtures eventually to speed tests
#fm = FeatureMaker()

def test_fm_values_exist():
    fm = FeatureMaker()
    assert hasattr(fm, "cts")
    assert hasattr(fm, "both_codes")
    assert hasattr(fm, "ct_nlp")
    assert hasattr(fm, "inv_cts")

def test_fm_methods_exist():
    fm = FeatureMaker()
    assert hasattr(fm, "most_alternative")
    assert hasattr(fm, "most_common_geo")
    assert hasattr(fm, "most_alternative")
    assert hasattr(fm, "vector_picking")
    assert hasattr(fm, "clean_entity")

#def test_read_in_admin1():
#    __location__ = os.path.realpath(os.path.join(os.getcwd(),
#                                    os.path.dirname(__file__)))
#    admin1_file = glob.glob(os.path.join(__location__, 'data/admin1CodesASCII.json'))
#    t = read_in_admin1(admin1_file[0])
#    assert t[u'ML.03'] == u'Kayes'
#
#def test_get_admin1():
#    __location__ = os.path.realpath(os.path.join(os.getcwd(),
#                       os.path.dirname(__file__)))
#    admin1_file = glob.glob(os.path.join(__location__, 'data/admin1CodesASCII.json'))
#    admin1_dict = read_in_admin1(admin1_file[0])
#    assert "Berlin" == get_admin1("DE", "16", admin1_dict)
#
#def test_get_admin1_none():
#    __location__ = os.path.realpath(os.path.join(os.getcwd(),
#                       os.path.dirname(__file__)))
#    admin1_file = glob.glob(os.path.join(__location__, 'data/admin1CodesASCII.json'))
#    admin1_dict = read_in_admin1(admin1_file[0])
#    assert "NA" == get_admin1("fakeplace", "16", admin1_dict)

def test_vector_picking():
    # switch to pytest fixtures
    fm = FeatureMaker()
    vp = fm.vector_picking(nlp("Mosul"))
    assert vp['country_1'] == "IRQ"

def test_cts():
    fm = FeatureMaker()
    out = fm.inv_cts['DEU']
    assert out == "Germany"

def test_query_geonames():
    pass

def test_country_process_one():
    pass
    #a = CountryAPI()
    #result = a.process('The meeting happened in Ontario.')
    #assert result == u'CAN'

def test_country_process_two():
    pass
    #a = CountryAPI()
    #result = a.process('Rebels from Damascus attacked Aleppo')
    #assert result == u'SYR'

