from ..country import CountryAPI


def test_country_process_one():
    a = CountryAPI()
    result = a.process('The meeting happend in Ontario.')
    assert result == u'CAN'


def test_country_process_two():
    a = CountryAPI()
    result = a.process('Rebels from Damascus attacked Aleppo')
    assert result == u'SYR'
