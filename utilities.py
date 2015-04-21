from __future__ import unicode_literals
import sys, os
import pandas as pd
from pyelasticsearch import ElasticSearch
es = ElasticSearch(urls='http://localhost:9200', timeout=60, max_retries=2)
import json
import requests

parent = os.path.dirname(os.path.realpath(__file__))
sys.path.append('/home/admin1/MITIE/mitielib')

from mitie import *

ner_model = named_entity_extractor('/home/admin1/MITIE/MITIE-models/english/ner_model.dat')


def talk_to_mitie(text):
    # Function that accepts text to MITIE and gets entities and HTML in response
    text = text.encode("utf-8")
    tokens = tokenize(text)
    tokens.append(' x ')
    entities = ner_model.extract_entities(tokens) # eventually, handle different NER models.
    out = []
    for e in entities:
        range = e[0]
        tag = e[1]
        score = e[2]
        entity_text = str(" ").join(tokens[i] for i in range)
        out.append({u'tag' : unicode(tag), u'text' : entity_text, u'score':score})
    for e in reversed(entities):
        range = e[0]
        tag = e[1]
        newt = tokens[range[0]]
        if len(range) > 1:
            for i in range:
                if i != range[0]:
                    newt += str(' ') + tokens[i]
        newt = str('<span class="mitie-') + tag  + str('">') + newt + str('</span>')
        tokens = tokens[:range[0]] + [newt] + tokens[(range[-1] + 1):]
    del tokens[-1]
    html = str(' ').join(tokens)
    htmlu = unicode(html.decode("utf-8"))
    return {"entities" : out, "html" : htmlu}

def query_geonames(placename):
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


def text_to_country(text):
    locations = []
    #text = text.decode("utf-8")
    #text = text.encode("utf-8")
    out = talk_to_mitie(text)
    for i in out['entities']:
        if i['tag'] == "LOCATION" or i['tag'] == "location":
            print i['text'],
            #try:
            t = query_geonames(i['text'])
            print(len(t['hits']['hits'])),
            for i in t['hits']['hits']:
                cc = i['_source']['country_code3']
                #score = i['_score']
                altnames = i['_source']['alternativenames'].split(',')
                score = len(altnames)
                locations.append((cc, score))
            #except:
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
