from elasticsearch_dsl import Q
import numpy as np
from ..utilities import structure_results

import spacy
nlp = spacy.load('en_core_web_lg', disable=['parser', 'tagger'])

def test_issue_40_2_thread(geo_thread):
    doc_list = ["Government forces attacked the cities in Aleppo Governorate, while rebel leaders met in Geneva.",
                "EULEX is based in Prishtina, Kosovo.",
                "Clientelism may depend on brokers."]
    locs = geo_thread.batch_geoparse(doc_list)
    assert len(locs) == 3
    assert locs[0][0]['geo']['geonameid'] == '170063'
    assert locs[0][1]['country_predicted'] == 'CHE'
    assert locs[1][0]['geo']['feature_code'] == 'PPLC'
    assert locs[1][1]['geo']['country_code3'] == 'XKX'
    assert locs[2] == []

def test_fm_methods_exist(geo):
    assert hasattr(geo, "_feature_most_alternative")
    assert hasattr(geo, "_feature_first_back")
    assert hasattr(geo, "_feature_word_embedding")
    assert hasattr(geo, "clean_entity")

def test_fm_methods_exist_thread(geo_thread):
    assert hasattr(geo_thread, "_feature_most_alternative")
    assert hasattr(geo_thread, "_feature_first_back")
    assert hasattr(geo_thread, "_feature_word_embedding")
    assert hasattr(geo_thread, "clean_entity")

def test_cts(geo):
    assert "Kosovo" in geo._cts.keys()
    assert "Kosovo" not in geo._cts.values()
    assert "AFG" in geo._cts.values()

def test_cts_thread(geo_thread):
    assert "Kosovo" in geo_thread._cts.keys()
    assert "Kosovo" not in geo_thread._cts.values()
    assert "AFG" in geo_thread._cts.values()

def test_country_mentions(geo):
    doc = nlp("Puerto Cabello is a port city in Venezuela")
    f = geo._feature_country_mentions(doc)
    assert f == ('VEN', 1, '', 0)

def test_country_mentions_thread(geo_thread):
    doc = nlp("Puerto Cabello is a port city in Venezuela")
    f = geo_thread._feature_country_mentions(doc)
    assert f == ('VEN', 1, '', 0)

def test_vector_picking(geo):
    entity = nlp("Mosul")
    vp = geo._feature_word_embedding(entity)
    assert vp['country_1'] == "IRQ"

def test_vector_picking_thread(geo_thread):
    entity = nlp("Mosul")
    vp = geo_thread._feature_word_embedding(entity)
    assert vp['country_1'] == "IRQ"

def test_cts2(geo):
    out = geo._inv_cts['DEU']
    assert out == "Germany"

def test_cts2_thread(geo_thread):
    out = geo_thread._inv_cts['DEU']
    assert out == "Germany"

def test_lookup_city(geo):
    out = geo.lookup_city("Norman", country="USA", adm1="Oklahoma")
    assert out['geo']['geonameid'] == '4543762'
    assert out['reason'] == 'Single match for city in Elasticsearch with name, ADM1, country.'

def test_lookup_city2(geo):
    out = geo.lookup_city("Rukn al-Din", "SYR")
    assert out['geo']['geonameid'] == '7642446'
    assert out['reason'] ==  'CAUTION: Single edit distance match.'

def test_city_lookup3(geo):
    # two easy cases
    res = geo.lookup_city("Norman", adm1 = "OK", country = "USA")
    assert res['geo']['geonameid'] == '4543762'
    res = geo.lookup_city("College Park", adm1 = "MD", country = "USA") 
    assert res['geo']['geonameid'] == '4351977'
    res = geo.lookup_city("College Park", adm1 = "OK", country = "USA") 
    assert res['geo'] is None
    # for some reason, Cambridge neighborhoods are PPL, not PPLX.
    res =  geo.lookup_city("East Cambridge", adm1 = "MA", country = "USA")
    assert res['geo']['geonameid'] == '5152577'
    assert res['geo']['feature_code'] == 'PPL'
    # Non-US check
    res =  geo.lookup_city("Aleppo", adm1 = "Aleppo", country = "SYR")
    assert res['geo']['feature_code'] == 'PPLA'
    assert res['geo']['geonameid'] == '170063'
    res = geo.lookup_city("Munich", country = "DEU")
    assert res['geo']['geonameid'] == '2867714'
    # Another US check
    res =  geo.lookup_city("Aleppo", country = "USA")
    assert res['geo']['geonameid'] == '4556251'
    # test neighborhood
    res = geo.lookup_city("Bustan al-Qasr", adm1 = "Aleppo", country = "SYR")
    assert res['geo']['feature_code'] == 'PPLX'
    assert res['geo']['geonameid'] == '7753543'
    # check nonsense
    res = geo.lookup_city("qwertyqwerty", adm1 = "Aleppo", country = "SYR")
    assert res['geo'] is None

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

def test_most_population_thread(geo_thread):
    res_a = geo_thread.query_geonames("Berlin")
    res_b = geo_thread.query_geonames("Oklahoma City")
    res_c = geo_thread.query_geonames("Tripoli")
    a = geo_thread._feature_most_population(res_a)
    b = geo_thread._feature_most_population(res_b)
    c = geo_thread._feature_most_population(res_c)
    assert a == "DEU"
    assert b == "USA"
    assert c == "LBY"

def test_is_country(geo):
    a = geo.is_country("Senegal")
    assert a

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

def test_make_country_features_thread(geo_thread):
    doc = nlp("EULEX is based in Prishtina, Kosovo.")
    f = geo_thread.make_country_features(doc)
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

def test_infer_country1_thread(geo_thread):
    doc = "There's fighting in Aleppo and Homs."
    loc = geo_thread.infer_country(doc)
    assert loc[0]['country_predicted'] == "SYR"
    assert loc[1]['country_predicted'] == "SYR"


def test_infer_country2(geo):
    doc = "There's fighting in Berlin and Hamburg."
    loc = geo.infer_country(doc)
    assert loc[0]['country_predicted'] == "DEU"
    assert loc[1]['country_predicted'] == "DEU"

def test_infer_country2_thread(geo_thread):
    doc = "There's fighting in Berlin and Hamburg."
    loc = geo_thread.infer_country(doc)
    assert loc[0]['country_predicted'] == "DEU"
    assert loc[1]['country_predicted'] == "DEU"

def test_two_countries(geo):
    doc = "There's fighting in Aleppo and talking in Geneva."
    loc = geo.geoparse(doc)
    assert loc[0]['country_predicted'] == "SYR"
    assert loc[1]['country_predicted'] == "CHE"

def test_two_countries_thread(geo_thread):
    doc = "There's fighting in Aleppo and talking in Geneva."
    loc = geo_thread.geoparse(doc)
    assert loc[0]['country_predicted'] == "SYR"
    assert loc[1]['country_predicted'] == "CHE"

def test_US_city(geo):
    doc = "There's fighting in Norman, Oklahoma."
    locs = geo.geoparse(doc)
    assert locs[0]['geo']['geonameid'] == '4543762'
    assert locs[1]['geo']['geonameid'] == '4544379'

def test_US_city_thread(geo_thread):
    doc = "There's fighting in Norman, Oklahoma."
    locs = geo_thread.geoparse(doc)
    assert locs[0]['geo']['geonameid'] == '4543762'
    assert locs[1]['geo']['geonameid'] == '4544379'

def test_admin1(geo):
    doc = "There's fighting in Norman, Oklahoma."
    locs = geo.geoparse(doc)
    assert locs[0]['geo']['admin1'] == 'Oklahoma'

def test_admin1_thread(geo_thread):
    doc = "There's fighting in Norman, Oklahoma."
    locs = geo_thread.geoparse(doc)
    assert locs[0]['geo']['admin1'] == 'Oklahoma'

def test_weird_loc(geo):
    doc = "There's fighting in Ajnsdgjb city."
    loc = geo.geoparse(doc)
    assert loc[0]['country_conf'] < 0.3

def test_weird_loc_thread(geo_thread):
    doc = "There's fighting in GOUOsabgoajwh city."
    loc = geo_thread.geoparse(doc)
    assert loc[0]['country_conf'] < 0.3

def test_no_loc(geo):
    doc = "The dog ran through the park."
    loc = geo.geoparse(doc)
    assert len(loc) == 0

def test_no_loc_thread(geo_thread):
    doc = "The dog ran through the park."
    loc = geo_thread.geoparse(doc)
    assert len(loc) == 0

def test_query(geo):
    results = geo.query_geonames("Berlin")
    assert results['hits']['hits'][15]['country_code3']

def test_query_thread(geo_thread):
    results = geo_thread.query_geonames("Berlin")
    assert results['hits']['hits'][15]['country_code3']

def test_missing_feature_code(geo):
    doc = "Congress and in the legislatures of Alabama, California, Florida, and Michigan."
    locs = geo.geoparse(doc)
    assert locs

def test_missing_feature_code_thread(geo_thread):
    doc = "Congress and in the legislatures of Alabama, California, Florida, and Michigan."
    locs = geo_thread.geoparse(doc)
    assert locs

def test_aleppo_geneva(geo):
    locs = geo.geoparse("Government forces attacked the cities in Aleppo Governorate, while rebel leaders met in Geneva.")
    assert locs[0]['geo']['country_code3'] == 'SYR'
    assert locs[1]['geo']['country_code3'] == 'CHE'

def test_aleppo_geneva_thread(geo_thread):
    locs = geo_thread.geoparse("Government forces attacked the cities in Aleppo Governorate, while rebel leaders met in Geneva.")
    assert locs[0]['geo']['country_code3'] == 'SYR'
    assert locs[1]['geo']['country_code3'] == 'CHE'

def test_issue_40(geo):
    doc = "In early 1938, the Prime Minister cut grants-in-aid to the provinces, effectively killing the relief project scheme. Premier Thomas Dufferin Pattullo closed the projects in April, claiming that British Columbia could not shoulder the burden alone. Unemployed men again flocked to Vancouver to protest government insensitivity and intransigence to their plight. The RCPU organized demonstrations and tin-canning (organized begging) in the city. Under the guidance of twenty-six-year-old Steve Brodie, the leader of the Youth Division who had cut his activist teeth during the 1935 relief camp strike, protesters occupied Hotel Georgia, the Vancouver Art Gallery (then located at 1145 West Georgia Street), and the main post office (now the Sinclair Centre)."
    locs = geo.geoparse(doc)
    assert len(locs) > 2


def test_issue_45(geo):
    text = """Santa Cruz is a first class municipality in
the province of Davao del Sur, Philippines. It has a population of 81,093
people as of 2010. The Municipality of Santa Cruz is part of Metropolitan
Davao. Santa Cruz is politically subdivided into 18 barangays. Of the 18
barangays, 7 are uplands, 9 are upland-lowland and coastal and 2 are
lowland-coastal. Pista sa Kinaiyahan A yearly activity conducted every last
week of April as a tribute to the Mother Nature through tree-growing, cleanup
activities and Boulder Face challenge. Araw ng Santa Cruz It is celebrated
every October 5 in commemoration of the legal creation of the municipality in
1884. Highlights include parades, field demonstrations, trade fairs, carnivals
and traditional festivities. Sinabbadan Festival A festival of ethnic ritual
and dances celebrated every September. Santa Cruz is accessible by land
transportation vehicles plying the Davao-Digos City, Davao-Kidapawan City,
Davao-Cotabato City, Davao-Koronadal City and Davao-Tacurong City routes
passing through the town's single, 27 kilometres (17 mi) stretch of national
highway that traverses its 11 barangays. From Davao City, the administrative
center of Region XI, it is 38 kilometres (24 mi) away within a 45-minute ride,
while it is 16 kilometres (9.9 mi) or about 15-minute ride from provincial
capital city of Digos."""
    locs = geo.geoparse(text)
    assert len(locs) > 0

def test_issue_45_thread(geo_thread):
    text = """Santa Cruz is a first class municipality in
the province of Davao del Sur, Philippines. It has a population of 81,093
people as of 2010. The Municipality of Santa Cruz is part of Metropolitan
Davao. Santa Cruz is politically subdivided into 18 barangays. Of the 18
barangays, 7 are uplands, 9 are upland-lowland and coastal and 2 are
lowland-coastal. Pista sa Kinaiyahan A yearly activity conducted every last
week of April as a tribute to the Mother Nature through tree-growing, cleanup
activities and Boulder Face challenge. Araw ng Santa Cruz It is celebrated
every October 5 in commemoration of the legal creation of the municipality in
1884. Highlights include parades, field demonstrations, trade fairs, carnivals
and traditional festivities. Sinabbadan Festival A festival of ethnic ritual
and dances celebrated every September. Santa Cruz is accessible by land
transportation vehicles plying the Davao-Digos City, Davao-Kidapawan City,
Davao-Cotabato City, Davao-Koronadal City and Davao-Tacurong City routes
passing through the town's single, 27 kilometres (17 mi) stretch of national
highway that traverses its 11 barangays. From Davao City, the administrative
center of Region XI, it is 38 kilometres (24 mi) away within a 45-minute ride,
while it is 16 kilometres (9.9 mi) or about 15-minute ride from provincial
capital city of Digos."""
    locs = geo_thread.geoparse(text)
    assert len(locs) > 0

def test_ohio(geo):
    # This was a problem in issue 41
    r = Q("match", geonameid='5165418')
    result = geo.conn.query(r).execute()
    output = structure_results(result)
    assert output['hits']['hits'][0]['asciiname'] == "Ohio"

def test_readme_example(geo):
    output = geo.geoparse("I traveled from Oxford to Ottawa.")
    correct = [{'country_conf': np.float32(0.957188),
          'country_predicted': 'GBR',
          'geo': {'admin1': 'England',
           'country_code3': 'GBR',
           'feature_class': 'P',
           'feature_code': 'PPLA2',
           'geonameid': '2640729',
           'lat': '51.75222',
           'lon': '-1.25596',
           'place_name': 'Oxford'},
          'spans': [{'end': 22, 'start': 16}],
          'word': 'Oxford'},
         {'country_conf': np.float32(0.8799221),
          'country_predicted': 'CAN',
          'geo': {'admin1': 'Ontario',
           'country_code3': 'CAN',
           'feature_class': 'P',
           'feature_code': 'PPLC',
           'geonameid': '6094817',
           'lat': '45.41117',
           'lon': '-75.69812',
           'place_name': 'Ottawa'},
          'spans': [{'end': 32, 'start': 26}],
          'word': 'Ottawa'}]
    assert output == correct

def test_readme_example_thread(geo_thread):
    output = geo_thread.geoparse("I traveled from Oxford to Ottawa.")
    correct = [{'country_conf': np.float32(0.957188),
          'country_predicted': 'GBR',
          'geo': {'admin1': 'England',
           'country_code3': 'GBR',
           'feature_class': 'P',
           'feature_code': 'PPLA2',
           'geonameid': '2640729',
           'lat': '51.75222',
           'lon': '-1.25596',
           'place_name': 'Oxford'},
          'spans': [{'end': 22, 'start': 16}],
          'word': 'Oxford'},
         {'country_conf': np.float32(0.8799221),
          'country_predicted': 'CAN',
          'geo': {'admin1': 'Ontario',
           'country_code3': 'CAN',
           'feature_class': 'P',
           'feature_code': 'PPLC',
           'geonameid': '6094817',
           'lat': '45.41117',
           'lon': '-75.69812',
           'place_name': 'Ottawa'},
          'spans': [{'end': 32, 'start': 26}],
          'word': 'Ottawa'}]
    assert output == correct

def test_issue_53(geo):
    # the spans issue
    output = geo.geoparse("I traveled from Oxford to Ottawa.")
    assert output[0]['spans'][0]['start'] == 16
    assert output[0]['spans'][0]['end'] == 22
    assert output[1]['spans'][0]['start'] == 26
    assert output[1]['spans'][0]['end'] == 32

def test_issue_68_verbose(geo):
    res = geo.geoparse("The ship entered Greenville from Tarboro", verbose=True)
    assert res

def test_issue_77(geo):
    res = geo.geoparse("We traveled to the USA")
    assert res[0]['geo']['feature_code'] == "PCLI"
    res = geo.geoparse("We traveled to the United States.")
    assert res[0]['geo']['feature_code'] == "PCLI"
    res = geo.geoparse("We traveled to Germany.")
    assert res[0]['geo']['feature_code'] == "PCLI"
    res = geo.geoparse("We traveled to France.")
    assert res[0]['geo']['feature_code'] == "PCLI"

def test_issue_82(geo):
    ents = geo.nlp(""" Wuppertal (remote-option) """).ents
    res = geo.geoparse( """ Wuppertal (remote-option) """ )
    assert len(ents) == len(res)
    ents = geo.nlp(""" Wuppertal remote-option """).ents
    res = geo.geoparse( """ Wuppertal remote-option """ )
    assert len(ents) == len(res)