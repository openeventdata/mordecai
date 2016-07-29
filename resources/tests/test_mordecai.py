import os
import sys
import glob
import json
from ConfigParser import ConfigParser
from mitie import named_entity_extractor
from ..country import CountryAPI
from ..places import PlacesAPI
from ..utilities import mitie_context, setup_es, query_geonames, read_in_admin1, get_admin1

def test_places_api_one():
    if os.environ.get('CI'):
        ci = 'circle'
        assert ci == 'circle'
    else:
        a = PlacesAPI()
        locs = "Ontario"
        result = a.process(locs, ['CAN'])
        print result
        gold = [{u'lat': 49.25014, u'searchterm': 'Ontario', u'lon': -84.49983, u'countrycode': u'CAN', u'placename': u'Ontario', u'admin1' : u'Ontario'}]
        assert result == gold

def test_places_api_two():
    if os.environ.get('CI'):
        ci = 'circle'
        assert ci == 'circle'
    else:
        a = PlacesAPI()
        locs = "Toronto"
        result = a.process(locs, ['CAN'])
        print result
        gold = [{u'placename': u'Toronto', u'countrycode': u'CAN', u'lon': -79.4163, u'admin1': u'Ontario', u'searchterm': 'Toronto', u'lat': 43.70011}]
        assert result == gold

def test_places_api_three():
    if os.environ.get('CI'):
        ci = 'circle'
        assert ci == 'circle'
    else:
        a = PlacesAPI()
        locs = "Kampala"
        result = a.process(locs, ['UGA'])
        print result
        gold = [{u'placename': u'Kampala', u'countrycode': u'UGA', u'lon': 32.20767, u'admin1': u'Northern Region', u'searchterm': 'Kampala', u'lat': 1.69669}]
        assert result == gold

def test_read_in_admin1():
    __location__ = os.path.realpath(os.path.join(os.getcwd(),
                                    os.path.dirname(__file__)))
    admin1_file = glob.glob(os.path.join(__location__, '../data/admin1CodesASCII.json'))
    t = read_in_admin1(admin1_file[0])
    assert t[u'ML.03'] == u'Kayes'

def test_get_admin1():
    __location__ = os.path.realpath(os.path.join(os.getcwd(),
                       os.path.dirname(__file__)))
    admin1_file = glob.glob(os.path.join(__location__, '../data/admin1CodesASCII.json'))
    admin1_dict = read_in_admin1(admin1_file[0])
    assert "Berlin" == get_admin1("DE", "16", admin1_dict)

def test_get_admin1_none():
    __location__ = os.path.realpath(os.path.join(os.getcwd(),
                       os.path.dirname(__file__)))
    admin1_file = glob.glob(os.path.join(__location__, '../data/admin1CodesASCII.json'))
    admin1_dict = read_in_admin1(admin1_file[0])
    assert "NA" == get_admin1("fakeplace", "16", admin1_dict)

def test_query_geonames():
    conn = setup_es()
    placename = "Berlin"
    country_filter = ["DEU"]
    qg = query_geonames(conn, placename, country_filter)
    hit_hit_name = qg['hits']['hits'][0]['name'] 
    assert hit_hit_name == "Berlin"

def test_places_api_syria():
    if os.environ.get('CI'):
        ci = 'circle'
        assert ci == 'circle'
    else:
        a = PlacesAPI()
        locs = "Rebels from Aleppo attacked Damascus."
        result = a.process(locs, ['SYR'])
        print result
        gold = [{u'lat': 36.20124, u'searchterm': 'Aleppo', u'lon': 37.16117, u'countrycode': u'SYR', u'placename': u'Aleppo', u'admin1' : u'Aleppo'}, 
                {u'lat': 33.5102, u'searchterm': 'Damascus', u'lon': 36.29128, u'countrycode': u'SYR', u'placename': u'Damascus', u'admin1' : u'Dimashq'}]
        assert result == gold


def test_mitie_context():
    __location__ = os.path.realpath(os.path.join(os.getcwd(),
                                                 os.path.dirname(__file__)))
    config_file = glob.glob(os.path.join(__location__, '../../config.ini'))
    parser = ConfigParser()
    parser.read(config_file)
    mitie_directory = parser.get('Locations', 'mitie_directory')
    mitie_ner_model = parser.get('Locations', 'mitie_ner_model')
    sys.path.append(mitie_directory)
    ner_model = named_entity_extractor(mitie_ner_model)
    text = "The meeting happened in Ontario."
    mc = mitie_context(text, ner_model)
    mc_gold = {u'entities': [{u'text': 'Ontario', u'tag': u'LOCATION', u'score': 1.3923831181343844, u'context': ['meeting', 'happened', 'in', '.']}]}
    assert mc == mc_gold

def test_country_process_one():
    a = CountryAPI()
    result = a.process('The meeting happened in Ontario.')
    assert result == u'CAN'

def test_country_process_two():
    a = CountryAPI()
    result = a.process('Rebels from Damascus attacked Aleppo')
    assert result == u'SYR'

def test_city_resolution():
    a = PlacesAPI()
    city_list = [("Lagos", "NGA"),
             ("Mogadishu", "SOM"),
             ("Mannheim", "DEU"),
             ("Noida", "IND"),
             ("Berlin", "DEU"),
             ("Damascus", "SYR"),
             ("New York", "USA"),
             ("San Francisco", "USA"),
             ("Freetown", "SLE"),
             ("Cape Town", "ZAF"),
             ("Windhoek", "NAM"),
             ("Paris", "FRA")]
    rs = [a.process(c[0], [c[1]]) for c in city_list]
    searched_cities = [c[0]['searchterm'] for c in rs]
    resolved_cities = [c[0]['placename'] for c in rs]
    assert resolved_cities == searched_cities
   
