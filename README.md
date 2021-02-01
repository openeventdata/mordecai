![](paper/mordecai_geoparsing.png)

Full text geoparsing as a Python library. Extract the place names from a
piece of English-language text, resolve them to the correct place, and return
their coordinates and structured geographic information.

**Mordecai is ready for an upgrade!** Please take the user survey [here](https://z0l4ihmu0ud.typeform.com/to/b8FmCfMt) 
to help shape what v3 will look like.

Example usage
-------------

```
>>> from mordecai import Geoparser
>>> geo = Geoparser()
>>> geo.geoparse("I traveled from Oxford to Ottawa.")

[{'country_conf': 0.96474487,
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
 {'country_conf': 0.83302397,
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
```

Mordecai requires a running Elasticsearch service with Geonames in it. See
"Installation" below for instructions.


Installation and Requirements
--------------------

1. Mordecai is on PyPI and can be installed for Python 3 with pip:

```
pip install mordecai
```

**Note**: It's *strongly* recommended that you run Mordecai in a virtual
environment. The libraries that Mordecai depends on are not always the most
recent versions and using a virtual environment prevents libraries from being
downgraded or running into other issues:

```
python -m venv mordecai-env
source mordecai-env/bin/activate
pip install mordecai
```

2. You should then download the required spaCy NLP model:

```
python -m spacy download en_core_web_lg
```

3. In order to work, Mordecai needs access to a Geonames gazetteer running in
Elasticsearch. The easiest way to set it up is by running the following
commands (you must have [Docker](https://docs.docker.com/engine/installation/)
installed first).

```
docker pull elasticsearch:5.5.2
wget https://andrewhalterman.com/files/geonames_index.tar.gz --output-file=wget_log.txt
tar -xzf geonames_index.tar.gz
docker run -d -p 127.0.0.1:9200:9200 -v $(pwd)/geonames_index/:/usr/share/elasticsearch/data elasticsearch:5.5.2
```

See the [es-geonames](https://github.com/openeventdata/es-geonames) for the code used
to produce this index.

To update the index, simply shut down the old container, re-download the index
from s3, and restart the container with the new index.

Citing
------

If you use this software in academic work, please cite as 

```
@article{halterman2017mordecai,
  title={Mordecai: Full Text Geoparsing and Event Geocoding},
  author={Halterman, Andrew},
  journal={The Journal of Open Source Software},
  volume={2},
  number={9},
  year={2017},
  doi={10.21105/joss.00091}
}
```

How does it work?
-----------------

Mordecai takes in unstructured text and returns structured geographic information extracted
from it. 

- It uses [spaCy](https://github.com/explosion/spaCy/)'s named entity recognition to
  extract placenames from the text.

- It uses the [geonames](http://www.geonames.org/)
  gazetteer in an [Elasticsearch](https://www.elastic.co/products/elasticsearch) index 
  (with some custom logic) to find the potential coordinates of
  extracted place names.

- It uses neural networks implemented in [Keras](https://keras.io/) and trained on new annotated
  English-language data labeled with [Prodigy](https://prodi.gy/) to infer the correct country and correct gazetteer entries for each
  placename. 

The training data for the two models includes copyrighted text so cannot be
shared freely. Applying Mordecai to non-English language text would require labeling data
in the target language and retraining.

API and Configuration
---------------------

When instantiating the `Geoparser()` module, the following options can be changed:

- `es_hosts` : List of hosts where the Geonames Elasticsearch service is
    running. Defaults to `['localhost']`, which is where it runs if you're using
    the default Docker setup described above.
- `es_port` : What port the Geonames Elasticsearch service is running on.
    Defaults to `9200`, which is where the Docker setup has it
- `es_ssl` : Whether Elasticsearch requires an SSL connection.
    Defaults to `False`.
- `es_auth` : Optional HTTP auth parameters to use with ES.
    If provided, it should be a two-tuple of `(user, password)`.
- `country_confidence` : Set the country model confidence below which no
    geolocation will be returned. If it's really low, the model's probably
    wrong and will return weird results. Defaults to `0.6`. 
- `verbose` : Return all the features used in the country picking model?
    Defaults to `False`. 
- `threads`: whether to use threads to make parallel queries to the
    Elasticsearch database. Defaults to `True`, which gives a ~6x speedup.

`geoparse` is the primary endpoint and the only one that most users will need.
Other, mostly internal, methods may be useful in some cases:

- `lookup_city` takes a city name, country, and (optionally) ADM1/state/governorate and 
    does a rule-based lookup for the city.
- `infer_country` take a document and attempts to infer the most probable
    country for each.
- `query_geonames` and `query_geonames_country` can be used for performing a
    search over Geonames in Elasticsearch
- methods with the `_feature` prefix are internal methods for
    calculating country picking features from text.

`batch_geoparse` takes in a list of documents and uses spaCy's `nlp.pipe`
method to process them more efficiently in the NLP step. 

Advanced users on large machines can increase the `lru_cache` parameter from 250
to 1000. This will use more memory but will increase parsing speed.

Tests
-----

Mordecai includes unit tests. To run the tests, `cd` into the
`mordecai` directory and run:

```
pytest
```

The tests require access to a running Elastic/Geonames service to
complete. The tests are currently failing on TravisCI with an unexplained
segfault but run fine locally. Mordecai has only been tested with Python 3.


Acknowledgements
----------------

An earlier verion of this software was donated to the Open Event Data Alliance
by Caerus Associates.  See [Releases](https://github.com/openeventdata/mordecai/releases) 
or the [legacy-docker](https://github.com/openeventdata/mordecai/tree/legacy-docker) branch for the
2015-2016 and the 2016-2017 production versions of Mordecai.

This work was funded in part by DARPA's XDATA program, the U.S. Army Research
Laboratory and the U.S. Army Research Office through the Minerva Initiative
under grant number W911NF-13-0332, and the National Science Foundation under
award number SBE-SMA-1539302. Any opinions, findings, and conclusions or
recommendations expressed in this material are those of the authors and do not
necessarily reflect the views of DARPA, ARO, Minerva, NSF, or the U.S.
government.


Contributing
------------

Contributions via pull requests are welcome. Please make sure that changes
pass the unit tests. Any bugs and problems can be reported
on the repo's [issues page](https://github.com/openeventdata/mordecai/issues).

