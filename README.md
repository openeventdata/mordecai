[![Circle CI](https://circleci.com/gh/caerusassociates/mordecai.svg?style=svg)](https://circleci.com/gh/caerusassociates/mordecai)

mordecai
=========

Custom-built full text geocoding. 

This software was donated to the Open Event Data Alliance by Caerus Associates.
See [Releases](https://github.com/openeventdata/mordecai/releases) for the
2015-2016 production version of Mordecai.

`Mordecai` accepts text and returns structured geographic information extracted
from it. It does this in several ways:

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

Mordecai is built as a series of [Docker](https://www.docker.com/) containers. You'll need to install Docker and and
[docker-compose](https://docs.docker.com/compose/) to be able to use it. If you're using Ubuntu,
[this gist](https://gist.github.com/wdullaer/f1af16bd7e970389bad3) is a good
place to start. 

`Mordecai`'s Geonames gazeteer can either be run locally alongside Mordecai or on a remote server.
. Elasticsearch/Geonames requires a large amount of memory, so running it
locally may be okay for small projects (if your machine has enough RAM), but is
not recommended for production. The config file's default settings assume it is
running locally. Uncomment and change those lines if your index is elsewhere on
the network. To download and start the Geonames Elasticsearch container
locally, run

```
sudo docker pull openeventdata/es-geonames
sudo docker run -d -p 9200:9200 --name=elastic openeventdata/es-geonames
```

This pulls a pre-built image and starts it running with an open port and defined name.

To start `Mordecai` itself, from inside this directory, run

```
sudo docker build -t mordecai .
sudo docker run -d -p 5000:5000 --link elastic:elastic mordecai
```

The `--link` flag connects `Mordecai` to the elastic image running locally.
Leave off if it's running on a different server.

Please note that many of the required components for `mordecai`, such as the
word2vec and MITIE models, are rather large so downloading and starting the
service takes a while.


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
curl -XPOST -H "Content-Type: application/json"  --data '{"text":"(Reuters) - The Iraqi government claimed victory over Islamic State insurgents in Tikrit on Wednesday after a month-long battle for the city supported by Shiite militiamen and U.S.-led air strikes, saying that only small pockets of resistance remained. State television showed Prime Minister Haidar al-Abadi, accompanied by leaders of the army and police, the provincial governor and Shiite paramilitary leaders, parading through Tikrit and raising an Iraqi flag. The militants captured the city, about 140 km (90 miles) north of Baghdad, last June as they swept through most of Iraqs Sunni Muslim territories, swatting aside a demoralized and disorganized army that has now required an uneasy combination of Iranian and American support to get back on its feet."}' 'http://localhost:5000/places'
```

Or if you know this text is about Iraq:

```
curl -XPOST -H "Content-Type: application/json"  --data '{"text":"(Reuters) - The Iraqi government claimed victory over Islamic State insurgents in Tikrit on Wednesday after a month-long battle for the city supported by Shiite militiamen and U.S.-led air strikes, saying that only small pockets of resistance remained. State television showed Prime Minister Haidar al-Abadi, accompanied by leaders of the army and police, the provincial governor and Shiite paramilitary leaders, parading through Tikrit and raising an Iraqi flag. The militants captured the city, about 140 km (90 miles) north of Baghdad, last June as they swept through most of Iraqs Sunni Muslim territories, swatting aside a demoralized and disorganized army that has now required an uneasy combination of Iranian and American support to get back on its feet.", "country": "IRQ"}' 'http://localhost:5000/places'
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

`mordecai` currently includes a few unit tests. To run the tests:

```
cd resources
py.test
```

The tests currently require access to a running Elastic/Geonames service to
complete. If this service is running locally in a Docker container, uncomment
the `Server` section in the config file so host = `localhost` and port =
`9200`.
