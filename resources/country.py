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
import json
import numpy
import utilities
from mitie import *
from gensim import matutils
from unidecode import unidecode
from gensim.models import Word2Vec
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
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
config_file = glob.glob(os.path.join('../' + __location__, 'config.ini'))
parser = ConfigParser()
word2vec_model= parser.get('Locations', 'word2vec_model')

#countries_file = glob.glob(os.path.join(__location__, 'countries.json'))[0]
#with open(countries_file, 'r') as f:
#    stopword_country_names = json.loads(f.read())


stopword_country_names = {"Afghanistan":"AFG", "Åland Islands":"ALA", "Albania":"ALB", "Algeria":"DZA",
    "American Samoa":"ASM", "Andorra":"AND", "Angola":"AGO", "Anguilla":"AIA",
    "Antarctica":"ATA", "Antigua Barbuda":"ATG", "Argentina":"ARG",
    "Armenia":"ARM", "Aruba":"ABW", "Ascension_Island":"NA", "Australia":"AUS",
    "Austria":"AUT", "Azerbaijan":"AZE", "Bahamas":"BHS", "Bahrain":"BHR",
    "Bangladesh":"BGD", "Barbados":"BRB", "Belarus":"BLR", "Belgium":"BEL",
    "Belize":"BLZ", "Benin":"BEN", "Bermuda":"BMU", "Bhutan":"BTN",
    "Bolivia":"BOL", "Bosnia_Herzegovina":"BIH",
    "Botswana":"BWA", "Bouvet Island":"BVT", "Brazil":"BRA",
    "Britain":"GBR", "Great_Britain":"GBR",
    "British Virgin Islands":"VGB", "Brunei":"BRN", "Bulgaria":"BGR", "Burkina_Faso":"BFA",
    "Burundi":"BDI", "Cambodia":"KHM", "Cameroon":"CMR",
    "Canada":"CAN","Cape Verde":"CPV", "Cayman_Islands":"CYM",
    "Central African Republic":"CAF", "Chad":"TCD", "Chile":"CHL", "China":"CHN",
    "Cocos_Islands":"CCK", "Colombia":"COL",
    "Comoros":"COM", "Congo Brazzaville":"COG", "Congo Kinshasa":"COD",
    "Congo":"COG", "Cook_Islands":"COK",
    "Costa_Rica":"CRI", "Cote Ivoire":"CIV", "Ivory_Coast":"CIV","Croatia":"HRV", "Cuba":"CUB",
    "Curaçao":"CUW", "Cyprus":"CYP", "Czech_Republic":"CZE", "Denmark":"DNK",
    "Djibouti":"DJI", "Dominica":"DMA", "Dominican_Republic":"DOM",
    "Ecuador":"ECU", "Egypt":"EGY", "El_Salvador":"SLV",
    "Equatorial_Guinea":"GNQ", "Eritrea":"ERI", "Estonia":"EST", "Ethiopia":"ETH",
    "Falkland_Islands":"FLK", "Faroe_Islands":"FRO",
    "Fiji":"FJI", "Finland":"FIN", "France":"FRA", "French_Guiana":"GUF",
    "French_Polynesia":"PYF","Gabon":"GAB",
    "Gambia":"GMB", "Gaza":"PSE", "Georgia":"GEO", "Germany":"DEU", "Ghana":"GHA",
    "Gibraltar":"GIB", "Greece":"GRC", "Greenland":"GRL", "Grenada":"GRD",
    "Guadeloupe":"GLP", "Guam":"GUM", "Guatemala":"GTM", "Guernsey":"GGY",
    "Guinea":"GIN", "Guinea_Bissau":"GNB", "Guyana":"GUY", "Haiti":"HTI","Honduras":"HND",
    "Hong_Kong":"HKG",  "Hungary":"HUN", "Iceland":"ISL",
    "India":"IND", "Indonesia":"IDN", "Iran":"IRN", "Iraq":"IRQ", "Ireland":"IRL",
    "Israel":"ISR", "Italy":"ITA", "Jamaica":"JAM", "Japan":"JPN",
    "Jordan":"JOR", "Kazakhstan":"KAZ", "Kenya":"KEN",
    "Kiribati":"KIR", "Kuwait":"KWT", "Kyrgyzstan":"KGZ", "Laos":"LAO",
    "Latvia":"LVA", "Lebanon":"LBN", "Lesotho":"LSO", "Liberia":"LBR",
    "Libya":"LBY", "Liechtenstein":"LIE", "Lithuania":"LTU", "Luxembourg":"LUX",
    "Macau":"MAC", "Macedonia":"MKD", "Madagascar":"MDG", "Malawi":"MWI",
    "Malaysia":"MYS", "Maldives":"MDV", "Mali":"MLI", "Malta":"MLT", "Marshall_Islands":"MHL",
    "Martinique":"MTQ", "Mauritania":"MRT", "Mauritius":"MUS",
    "Mayotte":"MYT", "Mexico":"MEX", "Micronesia":"FSM", "Moldova":"MDA",
    "Monaco":"MCO", "Mongolia":"MNG", "Montenegro":"MNE", "Montserrat":"MSR",
    "Morocco":"MAR", "Mozambique":"MOZ", "Myanmar":"MMR", "Burma":"MMR", "Namibia":"NAM",
    "Nauru":"NRU", "Nepal":"NPL", "Netherlands":"NLD", "Netherlands Antilles":"ANT",
    "New Caledonia":"NCL", "New_Zealand":"NZL", "Nicaragua":"NIC",
    "Niger":"NER", "Nigeria":"NGA", "Niue":"NIU", "North_Korea":"PRK",
    "Northern Ireland":"IRL", "Northern Mariana Islands":"MNP",
    "Norway":"NOR", "Oman":"OMN", "Pakistan":"PAK",
    "Palau":"PLW", "Palestinian_Territories":"PSE", "Palestine":"PSE","Panama":"PAN", "Papua New Guinea":"PNG",
    "Paraguay":"PRY", "Peru":"PER", "Philippines":"PHL", "Pitcairn_Islands":"PCN",
    "Poland":"POL", "Portugal":"PRT", "Puerto_Rico":"PRI",
    "Qatar":"QAT", "Réunion":"REU", "Romania":"ROU", "Russia":"RUS",
    "Rwanda":"RWA", "Saint Barthélemy":"BLM", "Saint Helena":"SHN",
    "Saint Kitts Nevis":"KNA", "Saint Lucia":"LCA",
    "Saint Pierre Miquelon":"SPM", "Saint Vincent Grenadines":"VCT",
    "Samoa":"WSM", "San_Marino":"SMR", "São Tomé Príncipe":"STP", "Saudi_Arabia":"SAU",
    "Senegal":"SEN", "Serbia":"SRB",
    "Seychelles":"SYC", "Sierra_Leone":"SLE", "Singapore":"SGP", "Sint Maarten":"SXM",
    "Slovakia":"SVK", "Slovenia":"SVN", "Solomon_Islands":"SLB",
    "Somalia":"SOM", "South_Africa":"ZAF",
    "South_Korea":"KOR", "South Sudan":"SSD", "Spain":"ESP", "Sri_Lanka":"LKA", "Sudan":"SDN",
    "Suriname":"SUR", "Svalbard Jan Mayen":"SJM",
    "Swaziland":"SWZ", "Sweden":"SWE", "Switzerland":"CHE", "Syria":"SYR",
    "Taiwan":"TWN", "Tajikistan":"TJK", "Tanzania":"TZA", "Thailand":"THA",
    "Timor Leste":"TLS", "East_Timor":"TLS","Togo":"TGO", "Tokelau":"TKL", "Tonga":"TON", "Trinidad Tobago":"TTO",
    "Tunisia":"TUN", "Turkey":"TUR",
    "Turkmenistan":"TKM", "Turks Caicos Islands":"TCA", "Tuvalu":"TUV", "U.S. Minor Outlying Islands":"UMI",
    "Virgin_Islands":"VIR", "Uganda":"UGA",
    "Ukraine":"UKR", "United_Arab_Emirates":"ARE", "United_Kingdom":"GBR",
    "UK":"GBR", "United_States":"USA", "USA":"USA", "America":"USA",
    "Uruguay":"URY", "Uzbekistan":"UZB", "Vanuatu":"VUT", "Vatican":"VAT", "Venezuela":"VEN",
    "Vietnam":"VNM", "Wallis Futuna":"WLF",
    "Western_Sahara":"ESH", "Yemen":"YEM", "Zambia":"ZMB", "Zimbabwe":"ZWE"}

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
        super(CountryAPI, self).__init__()

    def get(self):
        return """ This service expects a POST in the form '{"text":"On 12
    August, the BBC reported that..."}' It will return a list of ISO 3 character
    country codes for the country or countries it thinks the text is about. It
    determines the country focus by comparing the word2vec vectors for the
    places mentioned in the text with the vector representation of each country
    in the world, picking the closest."""

    def post(self):
        args = self.reqparse.parse_args()
        text = args['text']
        output = self.process(text)
        return output

    def process(self, text):
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
