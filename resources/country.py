# coding=utf-8
# Mordecai is our RESTful MITIE-geonames-elasticsearch service, built for use in a text-to-Mongo pipeline
# It gets passed text and returns lat/lons and placenames.
#
# osc.py is a full-pipeline version optimized for our OSC stories
#
# Example: curl -XPOST -H "Content-Type: application/json"  --data '{"text":"On 12 August, the BBC cited medical and security sources saying that fierce clashes broke out today in Tikrit, between the popular mobilization forces and elements of the terrorist DAISH. The sources added that the clashes resulted in the killing of 10 members of the popular mobilization and dozens from DAISH."}' 'http://192.168.50.236:8999/services/mordecai/osc'

from __future__ import unicode_literals
import re
import os
import sys
import glob
import numpy
import utilities
from mitie import *
from gensim import matutils
from unidecode import unidecode
from gensim.models import Word2Vec
from ConfigParser import ConfigParser
from flask.ext.httpauth import HTTPBasicAuth
from flask import jsonify, make_response
from flask.ext.restful import Resource, reqparse
from flask.ext.restful.representations.json import output_json

output_json.func_globals['settings'] = {'ensure_ascii': False,
                                        'encoding': 'utf8'}

auth = HTTPBasicAuth()


@auth.get_password
def get_password(username):
    if username == 'user':
        return 'text2features'
    return None


@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the
    # default auth dialog
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


# read in config file
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
config_file = glob.glob(os.path.join('../' + __location__, 'config.ini'))
parser = ConfigParser()
parser.read(config_file)
mitie_directory = parser.get('Locations', 'mitie_directory')
word2vec_model = parser.get('Locations', 'word2vec_model')

sys.path.append(mitie_directory)

with open('./countries.json', 'r') as f:
    stopword_country_names = json.load(f)


prebuilt = Word2Vec.load_word2vec_format(word2vec_model, binary=True)
vocab_set = set(prebuilt.vocab.keys())

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


class CountryAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('text', type=unicode, location='json')
        super(HermesAPI, self).__init__()

    def get():
        return """ This service expects a POST in the form '{"text":"On 12
    August, the BBC reported that..."}' It will return a list of ISO 3 character
    country codes for the country or countries it thinks the text is about. It
    determines the country focus by comparing the word2vec vectors for the
    places mentioned in the text with the vector representation of each country
    in the world, picking the closest."""

    def post(self):
        args = self.reqparse.parse_args()
        text = args['text']
        out = utilities.talk_to_mitie(text)
        places = []
        miscs = []
        for i in out['entities']:
            if i['tag'] == "LOCATION" or i['tag'] == "location":
                places.append(i['text'])
            if i['tag'] == "MISC" or i['tag'] == "misc":
                miscs.append(i['text'])

        loc_list = [re.sub(" ", "_", element) for element in places]
        locs = [x for x in loc_list if x in vocab_set]

        if locs:
            locs_word_vec = [prebuilt[word] for word in locs]
            locs_vec = numpy.array(locs_word_vec)
            weights = numpy.dot(index,
                                matutils.unitvec(locs_vec.mean(axis=0)).T).T
            ranks = weights.argsort()[::-1]
            try:
                return idx_country_mapping[ranks[0]]
            except:
                return []
        else:
            misc_list = [re.sub(" ", "_", element) for element in miscs]
            misc = [x for x in misc_list if x in vocab_set]

            misc_word_vec = [prebuilt[word] for word in misc]
            misc_vec = numpy.array(misc_word_vec)
            weights = numpy.dot(index,
                                matutils.unitvec(misc_vec.mean(axis=0)).T).T
            ranks = weights.argsort()[::-1]
            try:
                return idx_country_mapping[ranks[0]]
            except:
                return []
