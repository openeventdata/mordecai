# mordecai
Custom-built full text geocoding

Endpoints
---------

1. `/country`
In: text
Out: list of country codes for countries mentioned in text (used as input to later searches).

2. `/places`
In: text, list of country codes
Out: list of dictionaries of placenames and lat/lon in text

3. `/locate`
In: text, list of country codes
Out: Pick "best" location for the text.

4. `/osc`
In: text
Out: placenames and lat/lon, customized for OSC stories
