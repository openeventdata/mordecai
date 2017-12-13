import os
import sys
import glob
import json
#from ..geoparse import Geoparser

import spacy
nlp = spacy.load('en_core_web_lg')

def test_fm_methods_exist(geo):
    assert hasattr(geo, "_feature_most_alternative")
    assert hasattr(geo, "_feature_first_back")
    assert hasattr(geo, "_feature_word_embedding")
    assert hasattr(geo, "clean_entity")

def test_cts(geo):
    assert "Kosovo" in geo._cts.keys()
    assert "Kosovo" not in geo._cts.values()
    assert "AFG" in geo._cts.values()

def test_country_mentions(geo):
    doc = nlp("Puerto Cabello is a port city in Venezuela")
    f = geo._feature_country_mentions(doc)
    assert f == ('VEN', 1, '', 0)

def test_vector_picking(geo):
    entity = nlp("Mosul")
    vp = geo._feature_word_embedding(entity)
    assert vp['country_1'] == "IRQ"

def test_cts(geo):
    out = geo._inv_cts['DEU']
    assert out == "Germany"

def test_most_population(geo):
    res_a = geo.query_geonames("Berlin")
    res_b = geo.query_geonames("Oklahoma City")
    res_c = geo.query_geonames("Tripoli")
    a = geo._feature_most_population(res_a)
    b = geo._feature_most_population(res_b)
    c = geo._feature_most_population(res_c)
    assert a == "DEU"
    assert b == "USA"
    assert c == "LBY"

def test_is_country(geo):
    a = geo.is_country("Senegal")
    assert a == True

def test_make_country_features(geo):
    doc = nlp("EULEX is based in Prishtina, Kosovo.")
    f = geo.make_country_features(doc)
    assert f[0]['features']['most_alt'] == "XKX"
    assert f[1]['features']['most_alt'] == "XKX"
    assert f[0]['features']['word_vec'] == "XKX"
    assert f[1]['features']['word_vec'] == "XKX"
    assert f[0]['features']['wv_confid'] > 10
    assert f[1]['features']['wv_confid'] > 10
    assert len(f[0]['spans']) == 1
    assert len(f[1]['spans']) == 1

def test_infer_country1(geo):
    doc = "There's fighting in Aleppo and Homs."
    loc = geo.infer_country(doc)
    assert loc[0]['country_predicted'] == "SYR"
    assert loc[1]['country_predicted'] == "SYR"

def test_infer_country2(geo):
    doc = "There's fighting in Berlin and Hamburg."
    loc = geo.infer_country(doc)
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
    doc = "There's fighting in Ajnsdgjb city."
    loc = geo.geoparse(doc)
    assert loc[0]['country_conf'] < 0.001

def test_no_loc(geo):
    doc = "The dog ran through the park."
    loc = geo.geoparse(doc)
    assert len(loc) == 0

def test_query(geo):
    results = geo.query_geonames("Berlin")
    assert results['hits']['hits'][15]['country_code3']

def test_missing_feature_code(geo):
    doc = "Congress and in the legislatures of Alabama, California, Florida, and Michigan."
    locs = geo.geoparse(doc)

def test_aleppo_geneva(geo):
    locs = geo.geoparse("Government forces attacked the cities in Aleppo Governorate, while rebel leaders met in Geneva.")
    assert locs[0]['geo']['country_code3'] == 'SYR'
    assert locs[1]['geo']['country_code3'] == 'CHE'

def test_issue_40(geo):
    doc = "In early 1938, the Prime Minister cut grants-in-aid to the provinces, effectively killing the relief project scheme. Premier Thomas Dufferin Pattullo closed the projects in April, claiming that British Columbia could not shoulder the burden alone. Unemployed men again flocked to Vancouver to protest government insensitivity and intransigence to their plight. The RCPU organized demonstrations and tin-canning (organized begging) in the city. Under the guidance of twenty-six-year-old Steve Brodie, the leader of the Youth Division who had cut his activist teeth during the 1935 relief camp strike, protesters occupied Hotel Georgia, the Vancouver Art Gallery (then located at 1145 West Georgia Street), and the main post office (now the Sinclair Centre)."
    locs = geo.geoparse(doc)
    assert len(locs) > 2

def test_issue_40(geo):
    doc_list = ["Government forces attacked the cities in Aleppo Governorate, while rebel leaders met in Geneva.",
                "EULEX is based in Prishtina, Kosovo.",
                "Clientelism may depend on brokers."]
    locs = geo.batch_geoparse(doc_list)
    assert len(locs) == 3
    assert locs[0][0]['geo']['geonameid'] == '170063'
    assert locs[0][1]['country_predicted'] == 'CHE'
    assert locs[1][0]['geo']['feature_code'] == 'PPLC'
    assert locs[1][1]['geo']['country_code3'] == 'XKX'
    assert locs[2] == []

