# coding=utf-8
# Mordecai is our RESTful MITIE-geonames-elasticsearch service, built for use in a text-to-Mongo pipeline
# It gets passed text and returns lat/lons and placenames.
#
# osc.py is a full-pipeline version optimized for our OSC stories


from __future__ import unicode_literals
import requests
import json
import requests
from bson.objectid import ObjectId
import re
from pymongo import MongoClient
import tangelo
# import pandas as pd
from pyelasticsearch import ElasticSearch
import sys, os
import utilities

parent = os.path.dirname(os.path.realpath(__file__))
sys.path.append('/home/admin1/MITIE/mitielib')

from mitie import *
# Plan: load up several of these custom MITIE models and allow a parameter passed
#       in the POST to pick which NER model to use.

#ner = named_entity_extractor('/home/admin1/MITIE/MITIE-models/english/ner_model.dat')

es = ElasticSearch(urls='http://localhost:9200', timeout=60, max_retries=2)


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
                loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an area
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'A':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                    if loc:
                        return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                    if loc:
                        return loc
        # last resort, just take the first result.
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term, results[0]['_source']['asciiname'], results[0]['_source']['feature_class'], results[0]['_source']['country_code3']]
            return loc
# District search
    elif re.search("District", term):
         # take places that are areas
        ## define the default up here at the top?
        for r in results:
            if r['_source']['feature_class'] == 'A':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                    if loc:
                        return loc
        # last resort, just take the first place result.
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term, results[0]['_source']['asciiname'], results[0]['_source']['feature_class'], results[0]['_source']['country_code3']]
            return loc
# Subdistrict search    
    elif re.search("Subdistrict", term):
         # take places that are areas
        ## define the default up here at the top?
        for r in results:
            if r['_source']['feature_class'] == 'P':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                    if loc:
                        return loc
        # last resort, just take the first result.
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term, results[0]['_source']['asciiname'], results[0]['_source']['feature_class'], results[0]['_source']['country_code3']]
            return loc
# Airport search    
    elif re.search("Airport", term):
        for r in results:
            if r['_source']['feature_class'] == 'S':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                if loc:
                    return loc
        # Failing that, take an inhabited place
        if loc == []:
            for r in results:
                if r['_source']['feature_class'] == 'P':
                    coords = r['_source']['coordinates'].split(",")
                    loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                    if loc:
                        return loc
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term, results[0]['_source']['asciiname'], results[0]['_source']['feature_class'], results[0]['_source']['country_code3']]
            return loc

# final condition: if it doesn't have any special terms, just take the first result. 
# Not sure whether this should pick a city instead. Example: "Aleppo" should go to Aleppo the city. 
# But switching makes Damascus resolve to the wrong place, since the city of Damascus doesn't make it into the top 10 for some reason.
# But definitely don't take bodies of water
    else:
        for r in results:
            if r['_source']['feature_code'] == 'PPLA':
                coords = r['_source']['coordinates'].split(",")
                loc = [float(coords[0]), float(coords[1]), term, r['_source']['asciiname'], r['_source']['feature_class'], r['_source']['country_code3']]
                if loc:
                    return loc
        if loc == []:
            coords = results[0]['_source']['coordinates'].split(",")
            loc = [float(coords[0]), float(coords[1]), term, results[0]['_source']['asciiname'], results[0]['_source']['feature_class'], results[0]['_source']['country_code3']]
            return loc


place_cache = {}


@tangelo.restful
def get():
    return """
    This service expects a POST in the form '{"text":"On 12 August, the BBC reported that..."}'
    
    It will return the places mentioned in the text along with their latitudes and longitudes in the form: 
        {"lat":34.567, "lon":12.345, "seachterm":"Baghdad", "placename":"Baghdad", "countrycode":"IRQ"}
    """


@tangelo.restful
def post(*arg, **kwargs):
    params = json.loads(tangelo.request_body().read())
    text  = params['text']

    country = requests.post("http://192.168.50.236:8999/services/mordecai/country", data=json.dumps({"text":text}))
    country_filter = [country.text]
    
    locations = []

    out = utilities.talk_to_mitie(text)
    for i in out['entities']:
         if i['text'] in country_names:
             print " (Country/blacklist. Skipping...)"
         elif i['tag'] == "LOCATION" or i['tag'] == "Location":
            try:
                searchterm = re.sub(r"Governorate|District|Subdistrict|Airport", "", i['text']).strip() #put this in query_geonames?
                searchterm = re.sub("Dar 'a", "Dar'a", searchterm)
                try:
                    t = place_cache[searchterm]
                except:
                    t = utilities.query_geonames(searchterm, country_filter)
                    place_cache[searchterm] = t
                loc = pick_best_result(t, i['text'])
                # loc is a nice format for debugging and looks like [35.13179, 36.75783, 'searchterm', u'matchname', u'feature_class', u'country_code3']: 
                formatted_loc = {"lat":loc[0], "lon":loc[1], "seachterm":loc[2], "placename":loc[3], "countrycode":loc[5]}
                locations.append(formatted_loc)
            except:
                pass

    print "Place cache is ",
    print len(place_cache)
    return json.dumps(locations)

