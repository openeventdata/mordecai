# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import json
import numpy
import mitie
import pprint
import argparse
import unidecode
from gensim.models import Word2Vec
from elasticsearch_dsl import Search
from ConfigParser import ConfigParser
from elasticsearch import Elasticsearch
from elasticsearch_dsl.query import MultiMatch


def parse_args():
    parser = argparse.ArgumentParser(description='Mordecai Geolocation')
    parser._optionals.title = 'Options'
    parser.add_argument('-c', '--config-file',
                        help='Specify path to config file.',
                        type=str,
                        required=False,
                        default="")
    parser.add_argument('-p', '--port',
                        help='Specify port to listen on.',
                        type=int,
                        required=False,
                        default=5000)
    parser.add_argument('-eh', '--elasticsearch-host',
                        help='Specify elasticsearch host.',
                        type=str,
                        required=False,
                        default='elastic')
    parser.add_argument('-ep', '--elasticsearch-port',
                        help='Specify elasticsearch port.',
                        type=str,
                        required=False,
                        default='9200')
    parser.add_argument('-w', '--w2v-model',
                        help='Specify path to w2v model.',
                        type=str,
                        required=False,
                        default="/usr/src/data/GoogleNews-vectors-negative300.bin.gz")
    parser.add_argument('-md', '--mitie-dir',
                        help='Specify MITIE directory.',
                        type=str,
                        required=False,
                        default="/usr/src/MITIE/mitielib")
    parser.add_argument('-mn', '--mitie-ner',
                        help='Specify path to MITIE NER model.',
                        type=str,
                        required=False,
                        default="/usr/src/data/MITIE-models/english/ner_model.dat")
    return parser.parse_args()


def get_configs(args):
    '''
    Given the command line arguments, first check for a config file. If there
    is a config file use that, if ther eis no config file first check for
    environment variables, then fall back to command line arguments.

    If geonames/ES is running on a different server, the Server section in the config
    file should be uncommented and filled in. If it's running locally and being linked
    through Docker (e.g. `sudo docker run -d -p 5000:5000 --link elastic:elastic mordecai`),
    comment out the Server section so it knows to look for a linked container called `elastic`
    running on port 9200.
    '''
    config_dict = {}

    # if there's a config file provided just use that
    if args.config_file:
        config_parser = ConfigParser()
        config_parser.read(args.config_file)
        config_dict['word2vec_model'] = config_parser.get('Locations', 'word2vec_model')
        config_dict['mitie_directory'] = config_parser.get('Locations', 'mitie_directory')
        config_dict['mitie_ner_model'] = config_parser.get('Locations', 'mitie_ner_model')
        if 'Server' in config_parser.sections():
            config_dict['mordecai_port'] = config_parser.get('Server', 'mordecai_port')
            config_dict['es_host'] = config_parser.get('Server', 'geonames_host')
            config_dict['es_port'] = config_parser.get('Server', 'geonames_host')
        else:
            config_dict['mordecai_port'] = 5000
            config_dict['es_host'] = 'elastic'
            config_dict['es_port'] = '9200'
    else:
        # if no config file, first check for an environment variable,
        # then fallback to a command line argument
        if os.getenv('W2V_MODEL'):
            config_dict['word2vec_model'] = os.getenv('W2V_MODEL')
        else:
            config_dict['word2vec_model'] = args.w2v_model
        if os.getenv('MITIE_DIR'):
            config_dict['mitie_directory'] = os.getenv('MITIE_DIR')
        else:
            config_dict['mitie_directory'] = args.mitie_dir
        if os.getenv('MITIE_NER'):
            config_dict['mitie_ner_model'] = os.getenv('MITIE_NER')
        else:
            config_dict['mitie_ner_model'] = args.mitie_ner
        if os.getenv('MORDECAI_PORT'):
            config_dict['moredcai_port'] = os.getenv('MORDECAI_PORT')
        else:
            config_dict['moredecai_port'] = args.port
        if os.getenv('ES_HOST'):
            config_dict['es_host'] = os.getenv('ES_HOST')
        else:
            config_dict['es_host'] = args.elasticsearch_host
        if os.getenv('ES_PORT'):
            config_dict['es_port'] = os.getenv('ES_PORT')
        else:
            config_dict['es_port'] = args.elasticsearch_port
    print 'Starting Mordecai with the following configuration:\n'
    pprint.pprint(config_dict, width=1)
    return config_dict


def setup_mitie(mitie_directory, mitie_ner_model):
    """
    Given the location for MITIE and the model, create a named_entity_extractor
    object.
    """
    sys.path.append(mitie_directory)
    ner_model = mitie.named_entity_extractor(mitie_ner_model)
    return ner_model


def setup_w2v(word2vec_model, country_names_json):
    ''' Given the path to a word2vec model and a JSON file containing country
    names and codes, setup the indices and vocabulary for geocoding.'''
    prebuilt = Word2Vec.load_word2vec_format(word2vec_model, binary=True)
    vocab_set = set(prebuilt.vocab.keys())
    with open(country_names_json) as f:
        stopword_country_names = json.load(f)
    countries = stopword_country_names.keys()
    idx_country_mapping = {}
    index = numpy.empty(shape=(len(countries), 300), dtype='float64')
    for idx, country in enumerate(countries):
        country = unidecode(country)
        try:
            vector = prebuilt[country]
        except KeyError:
            pass
        index[idx] = vector
        try:
            idx_country_mapping[idx] = stopword_country_names[country]
        except KeyError:
            pass
    return {'prebuilt': prebuilt, 'vocab_set': vocab_set, 'index': index,
            'idx_country_mapping': idx_country_mapping}


def setup_es(es_ip, es_port):
    """
    Setup an Elasticsearch connection

    Parameters
    ----------
    es_ip: string
            IP address for elasticsearch instance
    es_port: string
            Port for elasticsearch instance

    Returns
    -------
    es_conn: an elasticsearch_dsl Search connection object.
    """

    es_url = 'http://{}:{}/'.format(es_ip, es_port)
    CLIENT = Elasticsearch(es_url)
    S = Search(CLIENT, index="geonames")
    return S


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
