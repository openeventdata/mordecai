# coding=utf-8
# Mordecai is our RESTful MITIE-geonames-elasticsearch service, built for use in a text-to-Mongo pipeline
# It gets passed text and returns lat/lons and placenames.
#
# osc.py is a full-pipeline version optimized for our OSC stories
#
# Example: curl -XPOST -H "Content-Type: application/json"  --data '{"text":"On 12 August, the Independent Shafaq News Agency cited medical and security sources saying that fierce clashes broke out today in Tikrit, between the popular mobilization forces and elements of the terrorist DAISH. The sources added that the clashes resulted in the killing of 10 members of the popular mobilization and dozens from DAISH."}' 'http://192.168.50.236:8999/services/mordecai/osc'

from __future__ import unicode_literals
import re
import os
import sys
import json
import tangelo
import requests
import utilities

parent = os.path.dirname(os.path.realpath(__file__))
sys.path.append('/home/admin1/MITIE/mitielib')

from mitie import *
# Plan: load up several of these custom MITIE models and allow a parameter passed
#       in the POST to pick which NER model to use.
ner_osc = named_entity_extractor('/home/admin1/MITIE/custom_location_ner2.dat')


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

def query_geonames(placename, country_filter):
    payload = {
    "query": {
        "filtered": {
            "query": {
                "query_string": {
                    "query": placename
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

    out = requests.post("http://localhost:9200/geonames/_search?pretty", data=json.dumps(payload))
    return out.json()
    # e.g.: query_geonames("Aleppo", ["IRQ", "SYR"])


def pick_best_result(results, term):
# Given a search term and the elasticsearch/geonames result from that search, return the best lat, lon, searchterm, place name
    loc = []
    try:
        results = results['hits']['hits']
    except:
        return []
    if len(results) < 1:
    # end if there are no results
        return []
    # This is a big chunk of conditional logic to favor different results depending on what terms are in the
    #  original term. This is all obviously Syria and Iraq specific.

# Governorate/Province Search
    elif re.search("Governorate|Province|Wilayah", term):
        # look for top-level ADM1 code
        for r in results:
            if r['_source']['feature_code'] == 'ADM1':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term,
                       r['_source']['asciiname'], r['_source']['feature_class'],
                       r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an area
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'A':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term,
                           r['_source']['asciiname'],
                           r['_source']['feature_class'],
                           r['_source']['country_code3']]
                    if loc:
                        return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term,
                           r['_source']['asciiname'],
                           r['_source']['feature_class'],
                           r['_source']['country_code3']]
                    if loc:
                        return loc
        # last resort, just take the first result.
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term,
                   results[0]['_source']['asciiname'],
                   results[0]['_source']['feature_class'],
                   results[0]['_source']['country_code3']]
            return loc
# District search
    elif re.search("District", term):
         # take places that are areas
        ## define the default up here at the top?
        for r in results:
            if r['_source']['feature_class'] == 'A':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term,
                       r['_source']['asciiname'], r['_source']['feature_class'],
                       r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term,
                           r['_source']['asciiname'],
                           r['_source']['feature_class'],
                           r['_source']['country_code3']]
                    if loc:
                        return loc
        # last resort, just take the first place result.
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term,
                   results[0]['_source']['asciiname'],
                   results[0]['_source']['feature_class'],
                   results[0]['_source']['country_code3']]
            return loc
# Subdistrict search
    elif re.search("Subdistrict", term):
         # take places that are areas
        ## define the default up here at the top?
        for r in results:
            if r['_source']['feature_class'] == 'P':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term,
                       r['_source']['asciiname'], r['_source']['feature_class'],
                       r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term,
                           r['_source']['asciiname'],
                           r['_source']['feature_class'],
                           r['_source']['country_code3']]
                    if loc:
                        return loc
        # last resort, just take the first result.
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term,
                   results[0]['_source']['asciiname'],
                   results[0]['_source']['feature_class'],
                   results[0]['_source']['country_code3']]
            return loc
# Airport search
    elif re.search("Airport", term):
        for r in results:
            if r['_source']['feature_class'] == 'S':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term,
                       r['_source']['asciiname'], r['_source']['feature_class'],
                       r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term,
                           r['_source']['asciiname'],
                           r['_source']['feature_class'],
                           r['_source']['country_code3']]
                    if loc:
                        return loc
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term,
                   results[0]['_source']['asciiname'],
                   results[0]['_source']['feature_class'],
                   results[0]['_source']['country_code3']]
            return loc

# final condition: if it doesn't have any special terms, just take the first result.
# Not sure whether this should pick a city instead. Example: "Aleppo" should go to Aleppo the city.
# But switching makes Damascus resolve to the wrong place, since the city of Damascus doesn't make it into the top 10 for some reason.
# But definitely don't take bodies of water
    else:
        for r in results:
            if r['_source']['feature_code'] == 'PPLA':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term,
                       r['_source']['asciiname'], r['_source']['feature_class'],
                       r['_source']['country_code3']]
                if loc:
                    return loc
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term,
                   results[0]['_source']['asciiname'],
                   results[0]['_source']['feature_class'],
                   results[0]['_source']['country_code3']]
            return loc


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


class OscAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('text', type=unicode, location='json')
        super(OscAPI, self).__init__()

    def post(self):
        args = self.reqparse.parse_args()
        text = args['text']
        country_filter = ["SYR", "IRQ"]

        out = utilities.talk_to_mitie(text)
        for i in out['entities']:
            print i['text'],
            if i['text'] in country_names:
                print " (Country/blacklist. Skipping...)"
            else:
                # put this in query_geonames?
                searchterm = re.sub(r"Governorate|District|Subdistrict|Airport",
                                    "", i['text']).strip()
                searchterm = re.sub("Dar 'a", "Dar'a", searchterm)
                t = query_geonames(searchterm, country_filter)
                loc = pick_best_result(t, i['text'])
                # loc is a nice format for debugging and looks like [35.13179, 36.75783, 'searchterm', u'matchname', u'feature_class', u'country_code3']:
                formatted_loc = {"lat": loc[0], "lon": loc[1],
                                 "seachterm": loc[2], "placename": loc[3],
                                 "countrycode": loc[5]}
                return formatted_loc
