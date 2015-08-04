from __future__ import print_function
from __future__ import unicode_literals
import os
import sys
import glob
from mitie import *
from elasticsearch_dsl import Search
from ConfigParser import ConfigParser
from elasticsearch import Elasticsearch
from elasticsearch_dsl.query import MultiMatch

# read in config file
__location__ = os.path.realpath(os.path.join(os.getcwd(),
                                             os.path.dirname(__file__)))
config_file = glob.glob(os.path.join(__location__, '../config.ini'))
parser = ConfigParser()
parser.read(config_file)
mitie_directory = parser.get('Locations', 'mitie_directory')
mitie_ner_model = parser.get('Locations', 'mitie_ner_model')


def setup_mitie():
    sys.path.append(mitie_directory)
    ner_model = named_entity_extractor(mitie_ner_model)

    return ner_model


def setup_es():
    try:
        if 'Server' in parser.sections():
            es_ip = parser.get('Server', 'geonames')
        else:
            es_ip = os.environ['ELASTIC_PORT_9200_TCP_ADDR']

        es_url = 'http://{}:{}/'.format(es_ip, '9200')
        CLIENT = Elasticsearch(es_url)
        S = Search(CLIENT)

        return S
    except Exception as e:
        print('Problem parsing config file. {}'.format(e))


def talk_to_mitie(text, ner_model):
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
        newt = (str('<span class="mitie-') + tag + str('">') + newt +
                str('</span>'))
        tokens = tokens[:range[0]] + [newt] + tokens[(range[-1] + 1):]
    del tokens[-1]
    html = str(' ').join(tokens)
    htmlu = unicode(html.decode("utf-8"))
    return {"entities": out, "html": htmlu}


def mitie_context(text, ner_model):
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


def query_geonames(conn, placename, country_filter):
    country_lower = [x.lower() for x in country_filter]
    q = MultiMatch(query=placename, fields=['asciiname^5', 'alternativenames'])
    res = conn.filter('term', country_code3=country_lower).query(q).execute()
    out = {'hits': {'hits': []}}
    keys = [u'admin1_code', u'admin2_code', u'admin3_code', u'admin4_code',
            u'alternativenames', u'asciiname', u'cc2', u'coordinates',
            u'country_code2', u'country_code3', u'dem', u'elevation',
            u'feature_class', u'feature_code', u'geonameid',
            u'modification_date', u'name', u'population', u'timzeone']
    for i in res:
        i_out = {}
        for k in keys:
            i_out[k] = i[k]
        out['hits']['hits'].append(i_out)
    return out
    # e.g.: query_geonames("Aleppo", ["IRQ", "SYR"])


def query_geonames_featureclass(conn, placename, country_filter, feature_class):
    country_lower = [x.lower() for x in [country_filter]]
    feature_lower = [x.lower() for x in feature_class]
    q = MultiMatch(query=placename, fields=['asciiname^5', 'alternativenames'])
    res = conn.filter('term', country_code3=country_lower).filter('term', feature_class=feature_lower).query(q).execute()
    out = {'hits': {'hits': []}}
    keys = [u'admin1_code', u'admin2_code', u'admin3_code', u'admin4_code',
            u'alternativenames', u'asciiname', u'cc2', u'coordinates',
            u'country_code2', u'country_code3', u'dem', u'elevation',
            u'feature_class', u'feature_code', u'geonameid',
            u'modification_date', u'name', u'population', u'timzeone']
    for i in res:
        i_out = {}
        for k in keys:
            i_out[k] = i[k]
        out['hits']['hits'].append(i_out)
    return out
    # e.g.: query_geonames_featureclass("Aleppo", ["IRQ", "SYR"], ["P"])
