# coding=utf-8
# Mordecai is our RESTful MITIE-geonames-elasticsearch service, built for use in
# a text-to-Mongo pipeline It gets passed text and returns lat/lons and
# placenames.
#
# osc.py is a full-pipeline version optimized for our OSC stories


from __future__ import unicode_literals
import os
import re
import sys
import glob
import json
import utilities
from mitie import *
from country import CountryAPI
from ConfigParser import ConfigParser
from flask import jsonify, make_response
from flask.ext.httpauth import HTTPBasicAuth
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

# read in config file
__location__ = os.path.realpath(os.path.join(os.getcwd(),
                                             os.path.dirname(__file__)))
config_file = glob.glob(os.path.join(__location__, '../config.ini'))
parser = ConfigParser()
parser.read(config_file)
mitie_directory = parser.get('Locations', 'mitie_directory')

sys.path.append(mitie_directory)

# Setup connection for elasticsearch
es_conn = utilities.setup_es()
ner_model = utilities.setup_mitie()


country_names = ["Afghanistan","Åland Islands","Albania","Algeria","American Samoa",
                 "Andorra","Angola","Anguilla","Antarctica","Antigua and Barbuda",
                 "Argentina","Armenia","Aruba","Ascension Island","Australia","Austria",
                 "Azerbaijan","Bahamas","Bahrain","Bangladesh","Barbados","Belarus",
                 "Belgium","Belize","Benin","Bermuda","Bhutan","Bolivia",
                 "Bonaire, Sint Eustatius, and Saba","Bosnia and Herzegovina","Botswana",
                 "Bouvet Island","Brazil","Britain","Great Britain", "British Indian Ocean Territory",
                 "British Virgin Islands","Brunei","Bulgaria","Burkina Faso","Burundi","Cambodia",
                 "Cameroon","Canada","Canary Islands","Cape Verde","Cayman Islands","Central African Republic",
                 "Ceuta and Melilla","Chad","Chile","China","Christmas Island","Clipperton Island",
                 "Cocos [Keeling] Islands","Colombia","Comoros","Congo - Brazzaville","Congo - Kinshasa","Congo",
                 "Democratic Republic of Congo", "Cook Islands","Costa Rica","Côte d’Ivoire","Croatia","Cuba",
                 "Curaçao","Cyprus","Czech Republic","Denmark","Diego Garcia","Djibouti","Dominica",
                 "Dominican Republic","Ecuador","Egypt","El Salvador","Equatorial Guinea","Eritrea",
                 "Estonia","Ethiopia","European Union","Falkland Islands","Faroe Islands","Fiji","Finland",
                 "France","French Guiana","French Polynesia","French Southern Territories","Gabon","Gambia",
                 "Gaza","Georgia","Germany","Ghana","Gibraltar","Greece","Greenland","Grenada","Guadeloupe",
                 "Guam","Guatemala","Guernsey","Guinea","Guinea-Bissau","Guyana","Haiti",
                 "Heard Island and McDonald Islands","Honduras","Hong Kong SAR China","Hungary","Iceland",
                 "India","Indonesia","Iran","Iraq","Ireland","Isle of Man","Israel","Italy","Jamaica","Japan",
                 "Jersey","Jordan","Kazakhstan","Kenya","Kiribati","Kuwait","Kyrgyzstan","Laos","Latvia","Lebanon",
                 "Lesotho","Liberia","Libya","Liechtenstein","Lithuania","Luxembourg","Macau SAR China","Macedonia",
                 "Madagascar","Malawi","Malaysia","Maldives","Mali","Malta","Marshall Islands","Martinique","Mauritania",
                 "Mauritius","Mayotte","Mexico","Micronesia","Moldova","Monaco","Mongolia","Montenegro","Montserrat",
                 "Morocco","Mozambique","Myanmar [Burma]","Namibia","Nauru","Nepal","Netherlands","Netherlands Antilles",
                 "New Caledonia","New Zealand","Nicaragua","Niger","Nigeria","Niue","Norfolk Island","North Korea",
                 "Northern Ireland", "Northern Mariana Islands","Norway","Oman","Outlying Oceania","Pakistan","Palau",
                 "Palestinian Territories","Panama","Papua New Guinea","Paraguay","Peru","Philippines","Pitcairn Islands",
                 "Poland","Portugal","Puerto Rico","Qatar","Réunion","Romania","Russia","Rwanda","Saint Barthélemy",
                 "Saint Helena","Saint Kitts and Nevis","Saint Lucia","Saint Martin","Saint Pierre and Miquelon",
                 "Saint Vincent and the Grenadines","Samoa","San Marino","São Tomé and Príncipe","Saudi Arabia",
                 "Senegal","Serbia","Serbia and Montenegro","Seychelles","Sierra Leone","Singapore","Sint Maarten",
                 "Slovakia","Slovenia","Solomon Islands","Somalia","South Africa",
                 "South Georgia and the South Sandwich Islands","South Korea","South Sudan","Spain","Sri Lanka",
                 "Sudan","Suriname","Svalbard and Jan Mayen","Swaziland","Sweden","Switzerland","Syria","Taiwan",
                 "Tajikistan","Tanzania","Thailand","Timor-Leste","Togo","Tokelau","Tonga","Trinidad and Tobago",
                 "Tristan da Cunha","Tunisia","Turkey","Turkmenistan","Turks and Caicos Islands","Tuvalu",
                 "U.S. Minor Outlying Islands","U.S. Virgin Islands","Uganda","Ukraine","United Arab Emirates",
                 "United Kingdom","UK","United States","USA", "United States of America", "Uruguay","Uzbekistan",
                 "Vanuatu","Vatican City","Venezuela","Vietnam","Wallis and Futuna","Western Sahara","Yemen",
                 "Zambia","Zimbabwe", "Europe", "America", "Africa", "Asia", "North America", "South America",
                 "United Nations","UN"]

P_list = ("city", "town", "village", "settlement", "capital", "cities",
          "villages", "towns", "neighborhood", "neighborhoods")
A_list = ("governorate", "province", "muhafazat")
# also need to get these from the term itself, not just the context


def check_names(results, term):
    # Is there an exact match?
    for r in results:
        if r['name'].lower() == term.lower():
            return r


def extract_feature_class(results, term, context):
    context = set([x.lower() for x in context])

    if context.intersection(P_list):
        return ['P']
    if context.intersection(A_list):
        return ['A']
    else:
        return ['A', 'P', 'S']


def pick_best_result2(results, term, context):
    results = results['hits']['hits']
    context = set([x.lower() for x in context])
    place = check_names(results, term)
    if not place:
        print "No nothing"
        try:
            place = results[0]
        except IndexError:
            return []
    coords = place['coordinates'].split(",")
    loc = [float(coords[0]), float(coords[1]), term,
           place['asciiname'], place['feature_class'],
           place['country_code3']]
    return loc

place_cache = {}


class PlacesAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('text', type=unicode, location='json')
        self.reqparse.add_argument('country', type=unicode, location='json')
        super(PlacesAPI, self).__init__()

    def get(self):
        return """
    This service expects a POST in the form '{"text":"On 12 August, the BBC
    reported that..."}'

    It will return the places mentioned in the text along with their latitudes
    and longitudes in the form: {"lat":34.567, "lon":12.345,
    "seachterm":"Baghdad", "placename":"Baghdad", "countrycode":"IRQ"}
    """

    def post(self):
        args = self.reqparse.parse_args()
        text = args['text']
        country_filter = args['country']
        if not country_filter:
            try:
                country_filter = CountryAPI().process(text)
            except ValueError:
                return json.dumps(locations)

        out = utilities.mitie_context(text, ner_model)

        located = self.process(out, country_filter)

        return located

    def process(self, locs, country_filter):
        locations = []
        for i in locs['entities']:
            if i['text'] in country_names:
                print " (Country/blacklist. Skipping...)"
            elif i['tag'] == "LOCATION" or i['tag'] == "Location":
                try:
                    # put this in query_geonames?
                    searchterm = re.sub(r"Governorate|District|Subdistrict|Airport",
                                        "", i['text']).strip()
                    searchterm = re.sub("Dar 'a", "Dar'a", searchterm)
                    feature_class = extract_feature_class(searchterm, i['text'],
                                                          i['context'])
                    cache_term = '___'.join([searchterm,
                                             ''.join(feature_class)])
                    # print cache_term
                    try:
                        t = place_cache[cache_term]
                    except KeyError:
                        t = utilities.query_geonames_featureclass(es_conn,
                                                                  searchterm,
                                                                  country_filter,
                                                                  feature_class)
                        place_cache[cache_term] = t
                    # for n in t['hits']['hits']:
                    #     print n['_source'][u'name']
                    # print extract_feature_class(t, i['text'], i['context'])
                    loc = pick_best_result2(t, i['text'], i['context'])
                    # loc is a nice format for debugging and looks like
                    # [35.13179, 36.75783, 'searchterm', u'matchname',
                    # u'feature_class', u'country_code3']:
                    if loc:
                        formatted_loc = {"lat": loc[0], "lon": loc[1],
                                         "searchterm": loc[2],
                                         "placename": loc[3],
                                         "countrycode": loc[5]}
                        print('Formatted loc: {}'.format(formatted_loc))
                        locations.append(formatted_loc)
                except Exception as e:
                    print e
        return locations
