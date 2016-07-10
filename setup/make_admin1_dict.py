import pandas as pd
import json

t = pd.read_table('http://download.geonames.org/export/dump/admin1CodesASCII.txt', sep = "\t", header = None)
adm1_dict = dict(zip(t[0], t[1]))

with open('admin1CodesASCII.json', 'w') as outfile:
    json.dump(adm1_dict, outfile)
