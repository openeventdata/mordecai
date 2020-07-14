import plac
import pandas as pd
from mordecai import Geoparser
from tqdm import tqdm


def main(in_file: ("input CSV file"), 
        out_file: ("filename to write ouput to"), 
        city_col: ("column in CSV with city col") = "city",
         adm1_col: ("column in CSV with state/governorate/ADM1") = "adm1", 
         country_col: ("column in CSV with country name") = "country"):
    """Geocode a csv with a city, ADM1, and country columns."""
    print("Loading Mordecai...")
    geo = Geoparser() 
    df = pd.read_csv(in_file)
    geocoded = []
    print("Geocoding...")
    for i in tqdm(df.iterrows()):
        row = i[1]
        if pd.isnull(row[adm1_col]):
            # Elasticsearch doesn't like NaN, change to None
            adm1 = None
        else:
            adm1 = row[adm1_col] 
        res = geo.lookup_city(city = row[city_col], 
                              adm1 = adm1, 
                              country = row[country_col])
        try:
            gc = {"admin1_code" : res['geo']['admin1_code'],
                  "admin2_code": res['geo']['admin2_code'],
                  "asciiname": res['geo']['asciiname'],
                  "name": res['geo']['name'],
                  "geonameid": res['geo']['geonameid'],
                  "feature_class": res['geo']['feature_class'],
                  "feature_code": res['geo']['feature_code'],
                  "country_code3": res['geo']['country_code3'],
                  "lat": float(res['geo']['coordinates'].split(",")[0]),
                  "lon": float(res['geo']['coordinates'].split(",")[1])}
        except TypeError:
            gc = {"admin1_code" : "",
                  "admin2_code": "",
                  "asciiname": "",
                  "name": "",
                  "geonameid": "",
                  "feature_class": "",
                  "feature_code": "", 
                  "country_code3": "",
                  "lat": "",
                  "lon": ""}
        gc['search_city'] = row[city_col]
        gc['search_adm1'] = row[adm1_col]
        gc['search_country'] = row[country_col]
        gc["info"] = res['info']
        gc["reason"] = res['reason']
        geocoded.append(gc)
    geo_df = pd.DataFrame(geocoded)
    geo_df.to_csv(out_file)
    print("Wrote file out to ", out_file)

    
if __name__ == '__main__':
    plac.call(main)