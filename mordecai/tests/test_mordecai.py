import os
import sys
import glob
import json
from ..utilities import read_in_admin1
from ..geoparse import Geoparse

import spacy
nlp = spacy.load('en_core_web_lg')

def test_fm_values_exist(geo):
    assert hasattr(geo, "cts")
    assert hasattr(geo, "both_codes")
    assert hasattr(geo, "ct_nlp")
    assert hasattr(geo, "inv_cts")

def test_fm_methods_exist(geo):
    assert hasattr(geo, "most_alternative")
    assert hasattr(geo, "most_common_geo")
    assert hasattr(geo, "most_alternative")
    assert hasattr(geo, "vector_picking")
    assert hasattr(geo, "clean_entity")

#def test_read_in_admin1():
#    __location__ = os.path.realpath(os.path.join(os.getcwd(),
#                                    os.path.dirname(__file__)))
#    admin1_file = glob.glob(os.path.join(__location__, 'data/admin1CodesASCII.json'))
#    print(admin1_file)
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

def test_vector_picking(geo):
    entity = nlp("Mosul")
    vp = geo.vector_picking(entity)
    assert vp['country_1'] == "IRQ"

def test_cts(geo):
    out = geo.inv_cts['DEU']
    assert out == "Germany"

def test_syria(geo):
    doc = "There's fighting in Aleppo and Homs."
    loc = geo.doc_to_guess(doc)
    assert loc[0]['country_predicted'] == "SYR"
    assert loc[1]['country_predicted'] == "SYR"

def test_germany(geo):
    doc = "There's fighting in Berlin and Hamburg."
    loc = geo.doc_to_guess(doc)
    assert loc[0]['country_predicted'] == "DEU"
    assert loc[1]['country_predicted'] == "DEU"

def test_two_countries(geo):
    doc = "There's fighting in Aleppo and talking in Geneva."
    loc = geo.geoparse(doc)
    assert loc[0]['country_predicted'] == "SYR"
    assert loc[1]['country_predicted'] == "CHE"

def test_US_city(geo):
    doc = "There's fighting in Norman, Oklahoma."
    locs = geo.geoparse(doc)
    assert locs[0]['geo']['geonameid'] == '4543762'
    assert locs[1]['geo']['geonameid'] == '4544379'

def test_admin1(geo):
    doc = "There's fighting in Norman, Oklahoma."
    locs = geo.geoparse(doc)
    assert locs[0]['geo']['admin1'] == 'Oklahoma'

def test_weird_loc(geo):
    doc = "There's fighting in Ajnsdgjb."
    loc = geo.geoparse(doc)
    assert loc[0]['country_predicted'] == ""

def test_no_loc(geo):
    doc = "The dog ran through the park."
    loc = geo.geoparse(doc)
    assert len(loc) == 0

def test_query(geo):
    results = geo.query_geonames("Berlin")
    assert results['hits']['hits'][15]['country_code3']


