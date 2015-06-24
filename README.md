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

It runs as a Flask-RESTful service.

Installation
------------

Standing up the service is as simple as installing
[docker](https://www.docker.com/) and
[docker-compose](https://docs.docker.com/compose/). Once these components are
installed, the service is started by running `docker-compose up`. To run
the service in the background use `docker-compose up -d`. This will pull
the Elasticsearch docker image with the Geonames gazetter already stored
as an index. It will also build the `mordecai` docker image and link this
to the Elasticsearch image. 

**Please note that many of the required components for mordecai, such as the
word2vec and MITIE models, are rather large so downloading and loading takes
awhile.**

Requirements
------------

The software currently assumes that an Elasticsearch instance is running with
the Geonames gazetteer as the index. 

Endpoints
---------

1. `/country`

    In: text

    Out: An ISO country code that best matches the country focus of the text (used as input to later searches). In the future, this will be a list of country codes.

2. `/places`

    In: text, list of country codes

    Out: list of dictionaries of placenames and lat/lon in text. The keys are "lat", "lon", "placename", "searchterm", and "countrycode". 


4. `/osc`

    In: text

    Out: placenames and lat/lon, customized for OSC stories

Example usage
-------------

```
curl -XPOST -H "Content-Type: application/json"  --data '{"text":"(Reuters) -
The Iraqi government claimed victory over Islamic State insurgents in Tikrit on
Wednesday after a month-long battle for the city supported by Shiite militiamen
and U.S.-led air strikes, saying that only small pockets of resistance
remained. State television showed Prime Minister Haidar al-Abadi, accompanied
by leaders of the army and police, the provincial governor and Shiite
paramilitary leaders, parading through Tikrit and raising an Iraqi flag. The
militants captured the city, about 140 km (90 miles) north of Baghdad, last
June as they swept through most of Iraqs Sunni Muslim territories, swatting
aside a demoralized and disorganized army that has now required an uneasy
combination of Iranian and American support to get back on its feet."}'
'http://localhost:5000/places'
```

Or if you know this text is about Iraq:

```
curl -XPOST -H "Content-Type: application/json"  --data '{"text":"(Reuters) -
The Iraqi government claimed victory over Islamic State insurgents in Tikrit on
Wednesday after a month-long battle for the city supported by Shiite militiamen
and U.S.-led air strikes, saying that only small pockets of resistance
remained. State television showed Prime Minister Haidar al-Abadi, accompanied
by leaders of the army and police, the provincial governor and Shiite
paramilitary leaders, parading through Tikrit and raising an Iraqi flag. The
militants captured the city, about 140 km (90 miles) north of Baghdad, last
June as they swept through most of Iraqs Sunni Muslim territories, swatting
aside a demoralized and disorganized army that has now required an uneasy
combination of Iranian and American support to get back on its feet.",
"country": "IRQ"}'
'http://localhost:5000/places'
```

Returns:
`[{"lat": 34.61581, "placename": "Tikrit", "seachterm": "Tikrit", "lon": 43.67861, "countrycode": "IRQ"}, {"lat": 34.61581, "placename": "Tikrit", "seachterm": "Tikrit", "lon": 43.67861, "countrycode": "IRQ"}, {"lat": 33.32475, "placename": "Baghdad", "seachterm": "Baghdad", "lon": 44.42129, "countrycode": "IRQ"}]`

###Python

```
import json
import requests

headers = {'Content-Type': 'application/json'}
data = {'text': """(Reuters) - The Iraqi government claimed victory over Islamic State insurgents in Tikrit on Wednesday after a month-long battle for the city supported by Shiite militiamen and U.S.-led air strikes, saying that only small pockets of resistance remained. State television showed Prime Minister Haidar al-Abadi, accompanied by leaders of the army and police, the provincial governor and Shiite paramilitary leaders, parading through Tikrit and raising an Iraqi flag. The militants captured the city, about 140 km (90 miles) north of Baghdad, last June as they swept through most of Iraqs Sunni Muslim territories, swatting aside a demoralized and disorganized army that has now required an uneasy combination of Iranian and American support to get back on its feet."""}
data = json.dumps(data)
out = requests.post('http://localhost:5000/places', data=data, headers=headers)
```

Customization
------------

Mordecai is meant to be easy to customize. There are a few ways to do this.

1. Change the MITIE named entity recognition model. This is a matter of changing one line in the configuration file, assuming that the custom trained MITIE model returns entities tagged as "LOCATION".

2. Custom place-picking logic. See the `/osc` for an example. Prior knowledge about the place text is about and the vocabulary used in the text to describe place times can be hard coded into a special endpoint for a particular corpus.

3. If a corpus is known to be about a specific country, that country can be passed to `places` to limit the search to places in that country.

Tests
-----

`mordecai` currently includes a few basic unit tests. To run the tests:

```
cd resources
py.test
```
