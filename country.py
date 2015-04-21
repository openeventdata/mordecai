# coding=utf-8
# Mordecai is our RESTful MITIE-geonames-elasticsearch service, built for use in a text-to-Mongo pipeline
# It gets passed text and returns lat/lons and placenames.
#
# osc.py is a full-pipeline version optimized for our OSC stories
#
# Example: curl -XPOST -H "Content-Type: application/json"  --data '{"text":"On 12 August, the Independent Shafaq News Agency cited medical and security sources saying that fierce clashes broke out today in Tikrit, between the popular mobilization forces and elements of the terrorist DAISH. The sources added that the clashes resulted in the killing of 10 members of the popular mobilization and dozens from DAISH."}' 'http://192.168.50.236:8999/services/mordecai/osc' 

from __future__ import unicode_literals
import requests
import json
import requests
import re
import tangelo
import sys, os

import pandas as pd
from pyelasticsearch import ElasticSearch
es = ElasticSearch(urls='http://localhost:9200', timeout=60, max_retries=2)

parent = os.path.dirname(os.path.realpath(__file__))
sys.path.append('/home/admin1/MITIE/mitielib')

from mitie import *
# Plan: load up several of these custom MITIE models and allow a parameter passed
#       in the POST to pick which NER model to use.
ner = named_entity_extractor('/home/admin1/MITIE/MITIE-models/english/ner_model.dat')


def talk_to_mitie(text):
# Function that accepts text to MITIE and gets entities and HTML in response
    text = text.encode("utf-8")
    tokens = tokenize(text)
    tokens.append(' x ')
    entities = ner.extract_entities(tokens) # eventually, handle different NER models.
    out = []
    for e in entities:
        range = e[0]
        tag = e[1]
        score = e[2]
        entity_text = str(" ").join(tokens[i] for i in range)
        out.append({u'tag' : unicode(tag), u'text' : entity_text, u'score':score})
    for e in reversed(entities):
        range = e[0]
        tag = e[1]
        newt = tokens[range[0]]
        if len(range) > 1:
            for i in range:
                if i != range[0]:
                    newt += str(' ') + tokens[i]
        newt = str('<span class="mitie-') + tag  + str('">') + newt + str('</span>')
        tokens = tokens[:range[0]] + [newt] + tokens[(range[-1] + 1):]
    del tokens[-1]
    html = str(' ').join(tokens)
    htmlu = unicode(html.decode("utf-8"))
    return {"entities" : out, "html" : htmlu}

placenames = {"Afghanistan":"AFG", "Åland Islands":"ALA", "Albania":"ALB", "Algeria":"DZA",
"American Samoa":"ASM", "Andorra":"AND", "Angola":"AGO", "Anguilla":"AIA",
"Antarctica":"ATA", "Antigua and Barbuda":"ATG", "Argentina":"ARG",
"Armenia":"ARM", "Aruba":"ABW", "Ascension Island":"NA", "Australia":"AUS",
"Austria":"AUT", "Azerbaijan":"AZE", "Bahamas":"BHS", "Bahrain":"BHR",
"Bangladesh":"BGD", "Barbados":"BRB", "Belarus":"BLR", "Belgium":"BEL",
"Belize":"BLZ", "Benin":"BEN", "Bermuda":"BMU", "Bhutan":"BTN",
"Bolivia":"BOL", "Bonaire, Sint Eustatius, and Saba":"BES", "Bosnia and Herzegovina":"BIH", 
"Botswana":"BWA", "Bouvet Island":"BVT", "Brazil":"BRA",
"Britain":"GBR", "Great Britain":"GBR", "British Indian Ocean Territory":"IOT",
"British Virgin Islands":"VGB", "Brunei":"BRN", "Bulgaria":"BGR", "Burkina Faso":"BFA", 
"Burundi":"BDI", "Cambodia":"KHM", "Cameroon":"CMR",
"Canada":"CAN", "Canary Islands":"NA", "Cape Verde":"CPV", "Cayman Islands":"CYM", 
"Central African Republic":"CAF", "Ceuta and Melilla":"NA",
"Chad":"TCD", "Chile":"CHL", "China":"CHN", "Christmas Island":"CXR",
"Clipperton Island":"NA", "Cocos [Keeling] Islands":"CCK", "Colombia":"COL",
"Comoros":"COM", "Congo - Brazzaville":"COG", "Congo - Kinshasa":"COD",
"Congo":"COG", "Democratic Republic of Congo":"COD", "Cook Islands":"COK",
"Costa Rica":"CRI", "Côte d’Ivoire":"CIV", "Croatia":"HRV", "Cuba":"CUB",
"Curaçao":"CUW", "Cyprus":"CYP", "Czech Republic":"CZE", "Denmark":"DNK",
"Diego Garcia":"NA", "Djibouti":"DJI", "Dominica":"DMA", "Dominican Republic":"DOM", 
"Ecuador":"ECU", "Egypt":"EGY", "El Salvador":"SLV",
"Equatorial Guinea":"GNQ", "Eritrea":"ERI", "Estonia":"EST", "Ethiopia":"ETH",
"European Union":"NA", "Falkland Islands":"FLK", "Faroe Islands":"FRO",
"Fiji":"FJI", "Finland":"FIN", "France":"FRA", "French Guiana":"GUF", 
"French Polynesia":"PYF", "French Southern Territories":"ATF", "Gabon":"GAB",
"Gambia":"GMB", "Gaza":"PSE", "Georgia":"GEO", "Germany":"DEU", "Ghana":"GHA",
"Gibraltar":"GIB", "Greece":"GRC", "Greenland":"GRL", "Grenada":"GRD",
"Guadeloupe":"GLP", "Guam":"GUM", "Guatemala":"GTM", "Guernsey":"GGY",
"Guinea":"GIN", "Guinea-Bissau":"GNB", "Guyana":"GUY", "Haiti":"HTI", 
"Heard Island and McDonald Islands":"HMD", "Honduras":"HND", 
"Hong Kong SAR China":"HKG", "Hong Kong":"HKG", "Hungary":"HUN", "Iceland":"ISL", 
"India":"IND", "Indonesia":"IDN", "Iran":"IRN", "Iraq":"IRQ", "Ireland":"IRL", 
"Isle of Man":"IMN", "Israel":"ISR", "Italy":"ITA", "Jamaica":"JAM", "Japan":"JPN",
"Jersey":"JEY", "Jordan":"JOR", "Kazakhstan":"KAZ", "Kenya":"KEN",
"Kiribati":"KIR", "Kuwait":"KWT", "Kyrgyzstan":"KGZ", "Laos":"LAO",
"Latvia":"LVA", "Lebanon":"LBN", "Lesotho":"LSO", "Liberia":"LBR",
"Libya":"LBY", "Liechtenstein":"LIE", "Lithuania":"LTU", "Luxembourg":"LUX",
"Macau SAR China":"MAC", "Macedonia":"MKD", "Madagascar":"MDG", "Malawi":"MWI",
"Malaysia":"MYS", "Maldives":"MDV", "Mali":"MLI", "Malta":"MLT", "Marshall Islands":"MHL", 
"Martinique":"MTQ", "Mauritania":"MRT", "Mauritius":"MUS",
"Mayotte":"MYT", "Mexico":"MEX", "Micronesia":"FSM", "Moldova":"MDA",
"Monaco":"MCO", "Mongolia":"MNG", "Montenegro":"MNE", "Montserrat":"MSR",
"Morocco":"MAR", "Mozambique":"MOZ", "Myanmar":"MMR", "Burma":"MMR", "Namibia":"NAM",
"Nauru":"NRU", "Nepal":"NPL", "Netherlands":"NLD", "Netherlands Antilles":"ANT", 
"New Caledonia":"NCL", "New Zealand":"NZL", "Nicaragua":"NIC",
"Niger":"NER", "Nigeria":"NGA", "Niue":"NIU", "Norfolk Island":"NFK", "North Korea":"PRK", 
"Northern Ireland":"IRL", "Northern Mariana Islands":"MNP",
"Norway":"NOR", "Oman":"OMN", "Outlying Oceania":"NA", "Pakistan":"PAK",
"Palau":"PLW", "Palestinian Territories":"PSE", "Panama":"PAN", "Papua New Guinea":"PNG", 
"Paraguay":"PRY", "Peru":"PER", "Philippines":"PHL", "Pitcairn Islands":"PCN", 
"Poland":"POL", "Portugal":"PRT", "Puerto Rico":"PRI",
"Qatar":"QAT", "Réunion":"REU", "Romania":"ROU", "Russia":"RUS",
"Rwanda":"RWA", "Saint Barthélemy":"BLM", "Saint Helena":"SHN", 
"Saint Kitts and Nevis":"KNA", "Saint Lucia":"LCA", "Saint Martin":"NA", 
"Saint Pierre and Miquelon":"SPM", "Saint Vincent and the Grenadines":"VCT", 
"Samoa":"WSM", "San Marino":"SMR", "São Tomé and Príncipe":"STP", "Saudi Arabia":"SAU",
"Senegal":"SEN", "Serbia":"SRB", "Serbia and Montenegro":"NA",
"Seychelles":"SYC", "Sierra Leone":"SLE", "Singapore":"SGP", "Sint Maarten":"SXM", 
"Slovakia":"SVK", "Slovenia":"SVN", "Solomon Islands":"SLB",
"Somalia":"SOM", "South Africa":"ZAF", "South Georgia and the South Sandwich Islands":"SGS", 
"South Korea":"KOR", "South Sudan":"SSD", "Spain":"ESP", "Sri Lanka":"LKA", "Sudan":"SDN", 
"Suriname":"SUR", "Svalbard and Jan Mayen":"SJM",
"Swaziland":"SWZ", "Sweden":"SWE", "Switzerland":"CHE", "Syria":"SYR",
"Taiwan":"TWN", "Tajikistan":"TJK", "Tanzania":"TZA", "Thailand":"THA",
"Timor-Leste":"TLS", "Togo":"TGO", "Tokelau":"TKL", "Tonga":"TON", "Trinidad and Tobago":"TTO", 
"Tristan da Cunha":"NA", "Tunisia":"TUN", "Turkey":"TUR",
"Turkmenistan":"TKM", "Turks and Caicos Islands":"TCA", "Tuvalu":"TUV", "U.S. Minor Outlying Islands":"UMI", 
"U.S. Virgin Islands":"VIR", "Uganda":"UGA",
"Ukraine":"UKR", "United Arab Emirates":"ARE", "United Kingdom":"GBR",
"UK":"GBR", "United States":"USA", "USA":"USA", "United States of America":"USA", 
"Uruguay":"URY", "Uzbekistan":"UZB", "Vanuatu":"VUT", "Vatican City":"VAT", "Venezuela":"VEN", 
"Vietnam":"VNM", "Wallis and Futuna":"WLF",
"Western Sahara":"ESH", "Yemen":"YEM", "Zambia":"ZMB", "Zimbabwe":"ZWE"}



@tangelo.restful
def post(*arg, **kwargs):
    params = json.loads(tangelo.request_body().read())
    text  = params['text']
    # future: add place for title here?
    print text 
    bothn = []

    for n in placenames.keys():
        t = re.search(n, text)
        if t:
            print "Match!!!!"
            bothn.append(placenames[n])
       
 
    print bothn
    if bothn == []:
        print "Using text_to_country"
       # print text_to_country(r['sentence'])
    out = talk_to_mitie(text)
    print "MITIE output:",
    for i in out['entities']:
        if i['tag'] == "LOCATION" or i['tag'] == "location":
            print i['text']

    return json.dumps(bothn)
