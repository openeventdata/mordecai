# Mordecai examples

## Geocoding cities

This script is an example usage of `geo.lookup_city()`, which takes a CSV
containing columns with city names, country 3 letter codes, and (optionally)
state/ADM1 names. If the columns are named (respectively) `city`, `adm1`, and
`country`, you can run it like this:

```
python geocode_cities.py geocode_cities.csv out.csv
```

Otherwise, you'll have to specify the column names as part of the call. The
geocoder returns lat/lon and Geonames information, as well as providing the
reason for why it selected a particular location and cautions when the results
were ambiguous. 