# Fuel Route API (Django)

Given a start and finish inside the USA, returns the driving route, the cheapest fuel stops
along it (500-mile range, 10 MPG) and the total fuel cost.

## Setup

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
# 1) put your fuel CSV in data/fuel-prices.csv
# 2) download the free "US Cities Database (basic)" from simplemaps.com -> data/uscities.csv
python manage.py load_stations data/fuel-prices.csv --cities data/uscities.csv
# optional: add --nominatim to geocode cities missing from uscities.csv
python manage.py runserver
```

## Endpoint
`GET /api/route/?start=Dallas, TX&finish=Denver, CO`
`POST /api/route/  {"start": "...", "finish": "..."}`  (addresses or `"lat,lon"`)

Options: `format=html` (interactive Leaflet map), `geojson=1` (adds GeoJSON line to the JSON).

## How it works
- **External calls:** 1 OSRM routing call + up to 2 Nominatim geocodes (0 if you pass `lat,lon`). All cached.
- **Stations:** CSV is deduplicated and geocoded once at load time (city level), kept in memory as numpy arrays.
- **Matching:** a KD-tree over route points finds stations within `MAX_DETOUR_MILES` (default 15) and their mile marker.
- **Optimizer:** greedy cost-minimising fuel plan (buy just enough to reach a cheaper stop, else fill up).
  Tank starts empty; origin fill is priced at the nearest station in the dataset.
- **Tests:** `python manage.py test`

## Config (env vars)
`VEHICLE_RANGE_MILES`, `VEHICLE_MPG`, `MAX_DETOUR_MILES`, `OSRM_URL`, `NOMINATIM_URL`.
