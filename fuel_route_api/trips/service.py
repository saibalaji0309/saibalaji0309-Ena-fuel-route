import numpy as np
from django.conf import settings
from scipy.spatial import cKDTree

from stations.repository import get_station_index
from .clients import ExternalServiceError, geocode, get_route
from .geo import haversine_miles, to_xyz
from .optimizer import Candidate, plan_fuel_stops


def find_candidates(index, coords, cum_miles, max_detour):
    """Stations within `max_detour` miles of the route, with their mile marker."""
    lat_pad = max_detour / 69.0 + 0.05
    lon_pad = lat_pad / max(np.cos(np.radians(coords[:, 0].mean())), 0.2)
    mask = (
        (index.lats >= coords[:, 0].min() - lat_pad) & (index.lats <= coords[:, 0].max() + lat_pad)
        & (index.lons >= coords[:, 1].min() - lon_pad) & (index.lons <= coords[:, 1].max() + lon_pad)
    )
    ids = np.nonzero(mask)[0]
    if ids.size == 0:
        return []
    tree = cKDTree(to_xyz(coords[:, 0], coords[:, 1]))
    dist, nearest = tree.query(to_xyz(index.lats[ids], index.lons[ids]), distance_upper_bound=max_detour)
    ok = np.isfinite(dist)
    return [
        Candidate(int(s), float(cum_miles[n]), float(index.prices[s]), float(d))
        for s, n, d in zip(ids[ok], nearest[ok], dist[ok])
    ]


def plan_trip(start_query: str, finish_query: str) -> dict:
    start, finish = geocode(start_query), geocode(finish_query)
    route = get_route(start, finish)               # the only routing call

    index = get_station_index()
    if len(index) == 0:
        raise ExternalServiceError("No fuel stations loaded. Run `manage.py load_stations` first.")

    coords = np.array(route.coords)
    seg = haversine_miles(coords[:-1, 0], coords[:-1, 1], coords[1:, 0], coords[1:, 1])
    cum = np.concatenate(([0.0], np.cumsum(seg)))
    if cum[-1] > 0:
        cum *= route.distance_miles / cum[-1]      # align with OSRM's road distance

    candidates = find_candidates(index, coords, cum, settings.MAX_DETOUR_MILES)
    purchases = plan_fuel_stops(
        candidates,
        route.distance_miles,
        index.nearest_price(*start),
        settings.VEHICLE_RANGE_MILES,
        settings.VEHICLE_MPG,
    )

    stops, initial_fill = [], None
    for p in purchases:
        if p.candidate is None:
            initial_fill = {
                "gallons": round(p.gallons, 2),
                "price_per_gallon": round(p.price, 3),
                "cost": round(p.cost, 2),
                "note": "Fuel bought at the origin, priced at the nearest station in the dataset.",
            }
            continue
        st = index.records[p.candidate.station_idx]
        stops.append({
            "order": len(stops) + 1,
            "name": st["name"], "address": st["address"], "city": st["city"], "state": st["state"],
            "latitude": st["latitude"], "longitude": st["longitude"],
            "mile_marker": round(p.candidate.mile, 1),
            "detour_miles": round(p.candidate.detour, 1),
            "price_per_gallon": round(p.price, 3),
            "gallons_purchased": round(p.gallons, 2),
            "cost": round(p.cost, 2),
        })

    return {
        "start": {"query": start_query, "latitude": start[0], "longitude": start[1]},
        "finish": {"query": finish_query, "latitude": finish[0], "longitude": finish[1]},
        "route": {
            "distance_miles": round(route.distance_miles, 1),
            "duration_hours": round(route.duration_hours, 2),
            "polyline": route.polyline,   # encoded polyline, precision 5
        },
        "initial_fill": initial_fill,
        "fuel_stops": stops,
        "summary": {
            "total_fuel_cost_usd": round(sum(p.cost for p in purchases), 2),
            "total_gallons": round(sum(p.gallons for p in purchases), 2),
            "fuel_stops_count": len(stops),
            "vehicle_range_miles": settings.VEHICLE_RANGE_MILES,
            "mpg": settings.VEHICLE_MPG,
        },
        "_geometry": [[lo, la] for la, lo in route.coords],  # stripped unless GeoJSON/map requested
    }
