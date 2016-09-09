# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import glob
import json
import mitie
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


def setup_mitie(mitie_directory):
    """ Given the location for MITIE and the model, create a named_entity_extractor object."""
    sys.path.append(mitie_directory)
    ner_model = mitie.named_entity_extractor(mitie_ner_model)
    return ner_model

def setup_es():
    """ 
    Read the config file for where to find the geonames elasticsearch index.

    If geonames/ES is running on a different server, the Server section in the config
    file should be uncommented and filled in. If it's running locally and being linked
    through Docker (e.g. `sudo docker run -d -p 5000:5000 --link elastic:elastic mordecai`),
    comment out the Server section so it knows to look for a linked container called `elastic` 
    running on port 9200.

    Returns
    -------
    es_conn: an elasticsearch_dsl Search connection object.
    """

    try:
        if 'Server' in parser.sections():
            print "Using config file for geonames/ES info"
            # Using config file for ES host and port
            es_ip = parser.get('Server', 'geonames_host')
            es_port = parser.get('Server', 'geonames_port')
        else:
            print "Using default Docker info for ES/geonames"
            # If no Server config, assume linked container
            es_ip = "elastic"
            es_port = '9200'
        es_url = 'http://{}:{}/'.format(es_ip, es_port)
        CLIENT = Elasticsearch(es_url)
        S = Search(CLIENT, index="geonames")
        return S
    except Exception as e:
        print 'Problem parsing config file. {}'.format(e)

def talk_to_mitie(text, ner_model):
    """
    Send text to MITIE NER, format the results, and return them.

    Note: this code also creates an HTML version of the output with 
    named entities highlighted. That output is not used in Mordecai.

    Returns
    -------
    named_entities: dictionary
                    "entities" contains a list of dictionaries. Each of these 
                    dicts has keys "tag", "text", and "score".
    """
    text = text.encode("utf-8")
    tokens = mitie.tokenize(text)
    tokens.append(' x ')
    # eventually, handle different NER models here.
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
    named_entities = {"entities": out, "html": htmlu}
    return named_entities


def mitie_context(text, ner_model):
    """
    Send text to MITIE NER, format the results, and return them with the 3 words
    on either side of every extracted entity.

    The context words can be used to filter results (e.g., if it says "the province of Aleppo", look
    for an admin area rather than a city.
    This version does not produce any HTML marked up text.
   
    Parameters
    ----------
    text: string
          The text to have its entities extracted
    ner_model: MITIE named entity extractor
               The NER model produced by `setup_mitie`
   
    Returns
    -------
    named_entities: dictionary
                    "entities" contains a list of dictionaries. Each of these 
                    dicts has keys "tag", "text", and "score".
    """
    text = text.encode("utf-8")
    tokens = mitie.tokenize(text)
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

def read_in_admin1(filepath):
    """
    Small helper function to read in a admin1 code <--> admin1 name document.

    Parameters
    ----------
    filepath: string
              path to the admin1 mapping JSON. This file is usually
              mordecai/resources/data/admin1CodesASCII.json 

    Returns
    -------
    admin1_dict: dictionary
                 keys are country + admin1codes, values are names
                 Example: "US.OK" : "Oklahoma"
                 Example: "SE.21": "Uppsala"
    """
    with open(filepath) as admin1file:
        admin1_dict = json.loads(admin1file.read())
    return admin1_dict

def get_admin1(country_code2, admin1_code, admin1_dict):
    """
    Convert a geonames admin1 code to the associated place name.

    Parameters
    ---------
    country_code2: string
                   The two character country code
    admin1_code: string
                 The admin1 code to be converted. (Admin1 is the highest 
                 subnational political unit, state/region/provice/etc.
    admin1_dict: dictionary
                 The dictionary containing the country code + admin1 code
                 as keys and the admin1 names as values.

    Returns
    ------
    admin1_name: string
                 The admin1 name. If none is found, return "NA".
    """
    lookup_key = ".".join([country_code2, admin1_code])
    try:
        admin1_name = admin1_dict[lookup_key]
        return admin1_name
    except KeyError:
        m = "No admin code found for country {} and code {}".format(country_code2, admin1_code)
        print m
        return "NA"


def query_geonames(conn, placename, country_filter):
    """
    Wrap search parameters into an elasticsearch query to the geonames index 
    and return results.

    Parameters
    ---------
    conn: an elasticsearch Search conn, like the one returned by `setup_es()`
    placename: string
               the placename text extracted by MITIE
    country_filter: list
                    a list of ISO 3 character country codes

    Returns
    -------
    out: The raw results of the elasticsearch query
    """


    country_filter = country_filter[0]
    q = MultiMatch(query=placename, fields=['asciiname^5', 'alternativenames'])
    res = conn.query('match', country_code3=country_filter).query(q).execute()
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
    """
    Wrap search parameters into an elasticsearch query to the geonames index 
    and return results.

    The difference between this featureclass modification and the simplier search
    is that this one limits the search to particular geographic feature types (e.g.,
    P = inhabited place, A = administrative area, etc.). This filtering was producing
    worse results than the simple queries, so it is not currently used in Mordecai.

    Parameters
    ---------
    conn: an elasticsearch Search conn, like the one returned by `setup_es()`
    placename: string
               the placename text extracted by MITIE
    country_filter: list
                    a list of ISO 3 character country codes
    feature_class: a Geonames feature class. Probably A or P, but see the Geonames
                   docs for more options.

    Returns
    -------
    out: The raw results of the elasticsearch query
    """

    q = MultiMatch(query=placename, fields=['asciiname^5', 'alternativenames'])
    res = conn.filter('term', country_code3=country_filter).filter('term', 
            feature_class=feature_class).query(q).execute()
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
