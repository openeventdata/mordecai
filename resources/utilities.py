from __future__ import unicode_literals
import os
import sys
import glob
import json
import requests
import pandas as pd
from mitie import *
from ConfigParser import ConfigParser
from pyelasticsearch import ElasticSearch

# read in config file
__location__ = os.path.realpath(os.path.join(os.getcwd(),
                                             os.path.dirname(__file__)))
config_file = glob.glob(os.path.join(__location__, '../config.ini'))
parser = ConfigParser()
parser.read(config_file)
mitie_directory = parser.get('Locations', 'mitie_directory')
mitie_ner_model = parser.get('Locations', 'mitie_ner_model')

sys.path.append(mitie_directory)
ner_model = named_entity_extractor(mitie_ner_model)

es = ElasticSearch(urls='http://localhost:9200', timeout=60, max_retries=2)


def talk_to_mitie(text):
    # Function that accepts text to MITIE and gets entities and HTML in response
    text = text.encode("utf-8")
    tokens = tokenize(text)
    tokens.append(' x ')
    # eventually, handle different NER models.
    entities = ner_model.extract_entities(tokens)
    out = []
    for e in entities:
        range = e[0]
        tag = e[1]
        score = e[2]
        entity_text = str(" ").join(tokens[i] for i in range)
        out.append({u'tag': unicode(tag), u'text': entity_text,
                    u'score': score})
    for e in reversed(entities):
        range = e[0]
        tag = e[1]
        newt = tokens[range[0]]
        if len(range) > 1:
            for i in range:
                if i != range[0]:
                    newt += str(' ') + tokens[i]
        newt = str('<span class="mitie-') + tag + str('">') + newt + str('</span>')
        tokens = tokens[:range[0]] + [newt] + tokens[(range[-1] + 1):]
    del tokens[-1]
    html = str(' ').join(tokens)
    htmlu = unicode(html.decode("utf-8"))
    return {"entities": out, "html": htmlu}


def mitie_context(text):
    # Function that accepts text to MITIE and returns entities
    # (and +/- 3 words of context)
    text = text.encode("utf-8")
    tokens = tokenize(text)
    # eventually, handle different NER models.
    entities = ner_model.extract_entities(tokens)
    out = []
    for e in entities:
        range = e[0]
        tag = e[1]
        score = e[2]
        entity_text = str(" ").join(tokens[i] for i in range)
        beg_token = min(range)
        end_token = max(range)

        context = []
        for i in [3, 2, 1]:
            try:
                context.append(tokens[beg_token - i])
            except:
                pass
            try:
                context.append(tokens[end_token + i])
            except:
                pass

        out.append({u'tag': unicode(tag), u'text': entity_text, u'score': score,
                    u'context': context})
    return {"entities": out}


def query_geonames_simple(placename):
    payload = {
    "query": {
        "filtered": {
            "query": {
                "query_string": {
                    "query": placename
                }
            }
        }
    }
    }


def query_geonames(placename, country_filter):
    payload = {
    "query": {
        "filtered": {
            "query": {
                "query_string": {
                    "query": placename,
                    "fields": ["asciiname^5", "alternativenames"]
                }
            },
                "filter": {
                     "terms" : {
                        "country_code3": country_filter
                        }
                    }
                }
            }
        }

    out = requests.post("http://localhost:9200/geonames/_search?pretty",
                        data=json.dumps(payload))
    return out.json()
    # e.g.: query_geonames("Aleppo", ["IRQ", "SYR"])


def query_geonames_featureclass(placename, country_filter, feature_class):
    payload = {
    "query": {
        "filtered": {
            "query": {
                "query_string": {
                    "query": placename,
                    "fields": ["asciiname^5", "alternativenames"]
                }
            },
                "filter": {
                    "and" : [
                        {
                         "terms" : {
                        "country_code3": country_filter
                            }
                        },{
                         "terms" : {
                        "feature_class": feature_class
                        }
                    }
            ]
            }
        }
    }
}
    out = requests.post("http://localhost:9200/geonames/_search?pretty",
                        data=json.dumps(payload))
    return out.json()
    # e.g.: query_geonames("Aleppo", ["IRQ", "SYR"], ["P"])


def text_to_country(text):
    locations = []
    # text = text.decode("utf-8")
    # text = text.encode("utf-8")
    out = talk_to_mitie(text)
    for i in out['entities']:
        if i['tag'] == "LOCATION" or i['tag'] == "location":
            print i['text'],
            # try:
            t = query_geonames(i['text'])
            print(len(t['hits']['hits'])),
            for i in t['hits']['hits']:
                cc = i['_source']['country_code3']
                # score = i['_score']
                altnames = i['_source']['alternativenames'].split(',')
                score = len(altnames)
                locations.append((cc, score))
            # except:
            print "Unexpected error:", sys.exc_info()[0]
            print ", ",

    if locations != []:
        locations = pd.DataFrame(locations)
        locations.columns = ['country', 'score']
        total = locations.groupby(['country']).sum()
        total = total.sort(['score'], ascending=[0]).head(1)
        total = total.reset_index()['country'].tolist()[0]
        return total
    else:
        return []
