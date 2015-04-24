mordecai
=========

Custom-built full text geocoding.

The purpose of mordecai is to accept text and return structured geographic information in return. It does this in several ways:

- It uses [MITIE](https://github.com/mit-nlp/MITIE) to extract placenames from
  the text. In the default configuration, it uses the out-of-the-box MITIE
  models, but these can be changed out for custom models when needed.

- It uses [word2vec](https://code.google.com/p/word2vec/)'s models, with
  [gensim](https://radimrehurek.com/gensim/)'s awesome Python wrapper, to infer
  the country focus of an article given the word vectors of the article's placenames. 

- It uses a country-filtered search of the [geonames](http://www.geonames.org/)
  gazetteer in [Elasticsearch](https://www.elastic.co/products/elasticsearch)
  (with some custom logic) to find the lat/lon for each place mentioned in the
  text.

It runs as a RESTful service in the Python
[Tangelo](https://github.com/Kitware/tangelo) web server.


Endpoints
---------

1. `/country`
In: text
Out: list of country codes for countries mentioned in text (used as input to later searches).

2. `/places`
In: text, list of country codes
Out: list of dictionaries of placenames and lat/lon in text

3. Not built yet: `/locate`
In: text, list of country codes
Out: Pick "best" location for the text. Alternatively, where did a thing take place? [Who knows what that means]

4. `/osc`
In: text
Out: placenames and lat/lon, customized for OSC stories

Example usage
-------------

`curl -XPOST -H "Content-Type: application/json"  --data '{"text":"(Reuters) - The Iraqi government claimed victory over Islamic State insurgents in Tikrit on Wednesday after a month-long battle for the city supported by Shiite militiamen and U.S.-led air strikes, saying that only small pockets of resistance remained. State television showed Prime Minister Haidar al-Abadi, accompanied by leaders of the army and police, the provincial governor and Shiite paramilitary leaders, parading through Tikrit and raising an Iraqi flag. The militants captured the city, about 140 km (90 miles) north of Baghdad, last June as they swept through most of Iraqs Sunni Muslim territories, swatting aside a demoralized and disorganized army that has now required an uneasy combination of Iranian and American support to get back on its feet."}' 'http://192.168.50.236:8999/services/mordecai/places'`

Returns:
`[{"lat": 34.61581, "placename": "Tikrit", "seachterm": "Tikrit", "lon": 43.67861, "countrycode": "IRQ"}, {"lat": 34.61581, "placename": "Tikrit", "seachterm": "Tikrit", "lon": 43.67861, "countrycode": "IRQ"}, {"lat": 33.32475, "placename": "Baghdad", "seachterm": "Baghdad", "lon": 44.42129, "countrycode": "IRQ"}]`
