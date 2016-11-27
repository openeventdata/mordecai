# coding=utf-8
# Mordecai is our RESTful MITIE-geonames-elasticsearch service, built for use in
# a text-to-Mongo pipeline It gets passed text and returns lat/lons and
# placenames.
#
# osc.py is a full-pipeline version optimized for our OSC stories


from __future__ import unicode_literals
import os
import re
import glob
import json
import utilities
from country import CountryAPI
from ConfigParser import ConfigParser
from flask import jsonify, make_response
from flask_httpauth import HTTPBasicAuth
from flask_restful import Resource, reqparse
from flask_restful.representations.json import output_json

# for debugging
#import requests
#from elasticsearch_dsl import Search
#from elasticsearch import Elasticsearch
#from elasticsearch_dsl.query import MultiMatch

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

country_names = ["Afghanistan", "Åland Islands", "Albania", "Algeria",
                 "American Samoa", "Andorra", "Angola", "Anguilla",
                 "Antarctica", "Antigua and Barbuda", "Argentina", "Armenia",
                 "Aruba", "Ascension Island", "Australia", "Austria",
                 "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados",
                 "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan",
                 "Bolivia", "Bonaire,  Sint Eustatius,  and Saba",
                 "Bosnia and Herzegovina", "Botswana", "Bouvet Island",
                 "Brazil", "Britain", "Great Britain",
                 "British Indian Ocean Territory", "British Virgin Islands",
                 "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia",
                 "Cameroon", "Canada", "Canary Islands", "Cape Verde",
                 "Cayman Islands", "Central African Republic",
                 "Ceuta and Melilla", "Chad", "Chile", "China",
                 "Christmas Island", "Clipperton Island",
                 "Cocos [Keeling] Islands", "Colombia", "Comoros",
                 "Congo - Brazzaville", "Congo - Kinshasa", "Congo",
                 "Democratic Republic of Congo",  "Cook Islands", "Costa Rica",
                 "Côte d’Ivoire", "Croatia", "Cuba", "Curaçao", "Cyprus",
                 "Czech Republic", "Denmark", "Diego Garcia", "Djibouti",
                 "Dominica", "Dominican Republic", "Ecuador", "Egypt",
                 "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia",
                 "Ethiopia", "European Union", "Falkland Islands",
                 "Faroe Islands", "Fiji", "Finland", "France", "French Guiana",
                 "French Polynesia", "French Southern Territories", "Gabon",
                 "Gambia", "Gaza", "Georgia", "Germany", "Ghana", "Gibraltar",
                 "Greece", "Greenland", "Grenada", "Guadeloupe", "Guam",
                 "Guatemala", "Guernsey", "Guinea", "Guinea-Bissau", "Guyana",
                 "Haiti", "Heard Island and McDonald Islands", "Honduras",
                 "Hong Kong SAR China", "Hungary", "Iceland", "India",
                 "Indonesia", "Iran", "Iraq", "Ireland", "Isle of Man",
                 "Israel", "Italy", "Jamaica", "Japan", "Jersey", "Jordan"
                 "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan",
                 "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya",
                 "Liechtenstein", "Lithuania", "Luxembourg", "Macau SAR China",
                 "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives",
                 "Mali", "Malta", "Marshall Islands", "Martinique",
                 "Mauritania", "Mauritius", "Mayotte", "Mexico", "Micronesia",
                 "Moldova", "Monaco", "Mongolia", "Montenegro", "Montserrat",
                 "Morocco", "Mozambique", "Myanmar [Burma]", "Namibia", "Nauru",
                 "Nepal", "Netherlands", "Netherlands Antilles",
                 "New Caledonia", "New Zealand", "Nicaragua", "Niger",
                 "Nigeria", "Niue", "Norfolk Island", "North Korea",
                 "Northern Ireland",  "Northern Mariana Islands", "Norway",
                 "Oman", "Outlying Oceania", "Pakistan", "Palau",
                 "Palestinian Territories", "Panama", "Papua New Guinea",
                 "Paraguay", "Peru", "Philippines", "Pitcairn Islands",
                 "Poland", "Portugal", "Puerto Rico", "Qatar", "Réunion",
                 "Romania", "Russia", "Rwanda", "Saint Barthélemy",
                 "Saint Helena", "Saint Kitts and Nevis", "Saint Lucia",
                 "Saint Martin", "Saint Pierre and Miquelon",
                 "Saint Vincent and the Grenadines", "Samoa", "San Marino",
                 "São Tomé and Príncipe", "Saudi Arabia", "Senegal", "Serbia",
                 "Serbia and Montenegro", "Seychelles", "Sierra Leone",
                 "Singapore", "Sint Maarten", "Slovakia", "Slovenia",
                 "Solomon Islands", "Somalia", "South Africa",
                 "South Georgia and the South Sandwich Islands", "South Korea",
                 "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname",
                 "Svalbard and Jan Mayen", "Swaziland", "Sweden", "Switzerland",
                 "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand",
                 "Timor-Leste", "Togo", "Tokelau", "Tonga",
                 "Trinidad and Tobago", "Tristan da Cunha", "Tunisia", "Turkey",
                 "Turkmenistan", "Turks and Caicos Islands", "Tuvalu",
                 "U.S. Minor Outlying Islands", "U.S. Virgin Islands", "Uganda",
                 "Ukraine", "United Arab Emirates", "United Kingdom", "UK",
                 "United States", "USA",  "United States of America", "Uruguay",
                 "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela",
                 "Vietnam", "Wallis and Futuna", "Western Sahara", "Yemen",
                 "Zambia", "Zimbabwe",  "Europe",  "America",  "Africa", "Asia",
                 "North America",  "South America", "United Nations", "UN"]

P_list = ("city", "town", "village", "settlement", "capital", "cities",
          "villages", "towns", "neighborhood", "neighborhoods")
A_list = ("governorate", "province", "muhafazat")
# also need to get these from the term itself, not just the context


def check_names(results, term):
    """ Check for an exact string match between search term and the results terms. """
    for r in results:
        if r['name'].lower() == term.lower():
            return r


def extract_feature_class(results, term, context):
    """Guess at geographic feature class based on neighbor words.

    Geonames objects include information on the geographic feature types.
    This function looks at the neighboring words around the location and checks
    if they're in the defined lists above to tell the query whether to look for a
    place ("P") or administrative area ("A").

    This is currently not used because it was causing crappy results.
    """
    context = set([x.lower() for x in context])

    if context.intersection(P_list):
        return ['P']
    if context.intersection(A_list):
        return ['A']
    else:
        return ['A', 'P', 'S']

class PlacesAPI(Resource):
    def __init__(self, **kwargs):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('text', type=unicode, location='json')
        self.reqparse.add_argument('country', type=unicode, location='json')
        self.ner_model = kwargs['ner_model']
        self.es_conn = kwargs['es_conn']
        __location__ = os.path.realpath(os.path.join(os.getcwd(),
                               os.path.dirname(__file__)))
        admin1_file = glob.glob(os.path.join(__location__, 'data/admin1CodesASCII.json'))
        self.admin1_dict = utilities.read_in_admin1(admin1_file[0])
        self.place_cache = {}
        super(PlacesAPI, self).__init__()

    def get(self):
        """
        Let users send an HTTP GET request to this endpoint to make sure it's up and
        give some guidance on how it works.
        """

        return """This service expects a POST in the form '{"text":"On 12 August, the BBC
reported that..."}'

It will return the places mentioned in the text along with their latitudes
and longitudes in the form: {"lat":34.567, "lon":12.345,
"seachterm":"Baghdad", "placename":"Baghdad", "countrycode":"IRQ"}
"""

    def post(self):
        """
        A POST wrapper around the main process function defined below.

        It gets `text` and `country` out of the POST request. If country
        isn't in the request, call /country to get it. It listifies the country_filter
        because the elasticsearch request needs it in that format.
        """
        args = self.reqparse.parse_args()
        text = args['text']
        country_filter = args['country']
        print country_filter
        if not country_filter:
            try:
                country_filter = CountryAPI().process(text)
            except ValueError:
                return json.dumps(locations)
        if not isinstance(country_filter, list):
            # this is an ugly hack. The process expects a list, but
            # CountryAPI returns a string.
            print "Listifying country_filter"
            country_filter = [country_filter]
        located = self.process(text, country_filter)
        return located

    def process(self, text, country_filter):
        """
        The main processing function that extracts place names from text, does the
        country-limited search, and returns the findings.

        Parameters
        ----------
        self: the Flask API

        text: A unicode string

        country_filter: A list containing an ISO 3 character country code

        Returns
        -------

        locations: a list of locations. Each location is a dictionary with keys
        lat, lon, searchterm, placename, countrycode, admin1.

        admin1 is the name of the state/region/governorate/province that the location is in.
        """

        locs = utilities.mitie_context(text, self.ner_model)
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
                    try:
                        t = self.place_cache[cache_term]
                    except KeyError:
                        t = utilities.query_geonames(self.es_conn,
                                                     searchterm,
                                                     country_filter)
                        self.place_cache[cache_term] = t
                    loc = self.pick_best_result(t, i['text'], i['context'])
                    # loc is a nice format for debugging and looks like
                    # [35.13179, 36.75783, 'searchterm', u'matchname',
                    # u'feature_class', u'country_code3', u'admin1']:
                    if loc:
                        formatted_loc = {"lat": loc[0], "lon": loc[1],
                                         "searchterm": loc[2],
                                         "placename": loc[3],
                                         "countrycode": loc[5],
                                         "admin1" : loc[6]}
                        print('Formatted loc: {}'.format(formatted_loc))
                        locations.append(formatted_loc)
                except Exception as e:
                    print e
        return locations

    def pick_best_result(self, results, term, context):
        """
        From the geonames/elasticsearch results, pick the single best match.

        Parameters
        ---------
        self:

        results: the results returned by the query to elasticsearch

        term: the MITIE-extracted named entity search term. (Used for checking exact matches)

        context: the list of neighboring words to help figure out the type of place

        Returns
        ---------
        loc: list
             lat, lon, term, placename, place type (A, P, etc. see geonames docs),
             countrycode (ISO 3 character), administrative region name.
        """
        results = results['hits']['hits']
        context = set([x.lower() for x in context])
        place = check_names(results, term)
        if not place:
            print "No exact match"
            try:
                place = results[0]
            except IndexError:
                print "IndexError on results[0]"
                return []
        coords = place['coordinates'].split(",")
        admin1_name = utilities.get_admin1(place['country_code2'], place['admin1_code'], self.admin1_dict)
        loc = [float(coords[0]), float(coords[1]), term,
               place['name'], place['feature_class'],
               place['country_code3'], admin1_name]
        return loc
