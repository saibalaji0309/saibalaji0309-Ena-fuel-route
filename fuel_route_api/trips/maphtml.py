import json


def render_map(result: dict) -> str:
    payload = json.dumps({
        "line": [[la, lo] for lo, la in result["_geometry"]],
        "start": result["start"], "finish": result["finish"],
        "stops": result["fuel_stops"], "summary": result["summary"],
        "route": {k: v for k, v in result["route"].items() if k != "polyline"},
    }).replace("</", "<\\/")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Fuel route map</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>html,body,#map{{height:100%;margin:0}}#info{{position:absolute;z-index:999;top:10px;right:10px;
background:#fff;padding:10px 14px;border-radius:8px;font:14px sans-serif;box-shadow:0 1px 6px #0004}}</style>
</head><body><div id="map"></div><div id="info"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const d = {payload};
const map = L.map('map');
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom: 18, attribution: '&copy; OpenStreetMap'}}).addTo(map);
const line = L.polyline(d.line, {{color: '#2563eb', weight: 5}}).addTo(map);
map.fitBounds(line.getBounds());
L.marker([d.start.latitude, d.start.longitude]).addTo(map).bindPopup('Start: ' + d.start.query);
L.marker([d.finish.latitude, d.finish.longitude]).addTo(map).bindPopup('Finish: ' + d.finish.query);
d.stops.forEach(s => L.circleMarker([s.latitude, s.longitude], {{radius: 8, color: '#dc2626', fillOpacity: .9}}).addTo(map)
  .bindPopup(`<b>#${{s.order}} ${{s.name}}</b><br>${{s.city}}, ${{s.state}}<br>Mile ${{s.mile_marker}}<br>$${{s.price_per_gallon}}/gal &middot; ${{s.gallons_purchased}} gal &middot; $${{s.cost}}`));
document.getElementById('info').innerHTML =
  `<b>${{d.route.distance_miles}} mi</b> &middot; ${{d.summary.fuel_stops_count}} fuel stops<br>Total fuel: <b>$${{d.summary.total_fuel_cost_usd}}</b>`;
</script></body></html>"""
