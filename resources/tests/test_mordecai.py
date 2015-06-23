from ..country import CountryAPI
from ..places import PlacesAPI


def test_places_api_one():
    a = PlacesAPI()
    locs = {u'entities': [{u'context': ['meeting', 'happened', 'in', '.'],
                           u'score': 1.3923831181343844, u'tag': u'LOCATION',
                           u'text': 'Ontario'}]}

    result = a.process(locs, 'CAN')
    gold = [{u'countrycode': u'CAN', u'lat': 43.65004, u'lon': -79.90554,
             u'placename': u'SunnyView Dental', u'searchterm': 'Ontario'}]
    assert result == gold

def test_country_process_one():
    a = CountryAPI()
    result = a.process('The meeting happened in Ontario.')
    assert result == u'CAN'


def test_country_process_two():
    a = CountryAPI()
    result = a.process('Rebels from Damascus attacked Aleppo')
    assert result == u'SYR'
