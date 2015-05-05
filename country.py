# coding=utf-8
# Mordecai is our RESTful MITIE-geonames-elasticsearch service, built for use in a text-to-Mongo pipeline
# It gets passed text and returns lat/lons and placenames.
#
# osc.py is a full-pipeline version optimized for our OSC stories
#
# Example: curl -XPOST -H "Content-Type: application/json"  --data '{"text":"On 12 August, the Independent Shafaq News Agency cited medical and security sources saying that fierce clashes broke out today in Tikrit, between the popular mobilization forces and elements of the terrorist DAISH. The sources added that the clashes resulted in the killing of 10 members of the popular mobilization and dozens from DAISH."}' 'http://192.168.50.236:8999/services/mordecai/osc' 

from __future__ import unicode_literals
import json
import requests
import re
import tangelo
import sys, os
import utilities
import glob
from gensim import corpora, models, similarities, utils
from gensim.models import Word2Vec
from unidecode import unidecode

import pandas as pd
from pyelasticsearch import ElasticSearch
es = ElasticSearch(urls='http://localhost:9200', timeout=60, max_retries=2)

# read in config file
from ConfigParser import ConfigParser
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
config_file = glob.glob(os.path.join(__location__, 'config.ini'))
parser = ConfigParser()
parser.read(config_file)
mitie_directory = parser.get('Locations', 'mitie_directory')
word2vec_model = parser.get('Locations', 'word2vec_model')

#parent = os.path.dirname(os.path.realpath(__file__))
sys.path.append(mitie_directory)     #'/home/admin1/MITIE/mitielib')
from mitie import *

# Plan: load up several of these custom MITIE models and allow a parameter passed
#       in the POST to pick which NER model to use.

#ner = named_entity_extractor('/home/admin1/MITIE/MITIE-models/english/ner_model.dat')

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

prebuilt = Word2Vec.load_word2vec_format(word2vec_model, binary=True)    #"/home/admin1/new_dashboard/services/mordecai/GoogleNews-vectors-negative300.bin.gz", binary=True)
vocab_set = set(prebuilt.vocab.keys())


@tangelo.restful
def get():
    return """
    This service expects a POST in the form '{"text":"On 12 August, the BBC reported that..."}'
    It will return a list of ISO 3 character country codes for the country or countries it thinks the 
    text is about.

    It uses gensim!!!
    """

@tangelo.restful
def post(*arg, **kwargs):
    params = json.loads(tangelo.request_body().read())
    text  = params['text']
    out = utilities.talk_to_mitie(text)
    places = []
    for i in out['entities']:
        if i['tag'] == "LOCATION" or i['tag'] == "location":
            places.append(i['text'])
    
    loc_list = [re.sub(" ", "_", element) for element in places]
    locs = [x for x in loc_list if x in vocab_set]
    output_list = []

    for i in stopword_country_names.keys():
        country = unidecode(i)
        country = country.split()
        score = prebuilt.n_similarity(locs, country) #utils.tokenize(text)
        out = [i, score]
        output_list.append(out)
    df = pd.DataFrame(output_list)
    country_name = df.sort([1], ascending=False).head(1)
    country_name = country_name.reset_index()[0].tolist()[0]
    try:
        return stopword_country_names[country_name]
    except:
        return []
    #return json.dumps(bothn)
    

# future: add place for title here?
#    bothn = []
#
#    for n in placenames.keys():
#        t = re.search(n, text)
#        if t:
#            print "Match!!!!"
#            bothn.append(placenames[n])
#       
# 
#    if bothn == []:
#        print "Using text_to_country"
#    #    print utilities.text_to_country(text)
#    out = utilities.talk_to_mitie(text)
#    print "MITIE output:",
#    for i in out['entities']:
#        if i['tag'] == "LOCATION" or i['tag'] == "location":
#            print i['text']
#
