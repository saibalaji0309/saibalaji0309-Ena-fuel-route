"""Thin, cached clients for the free OSRM (routing) and Nominatim (geocoding) APIs."""
import hashlib
import re
from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.cache import cache

from .geo import decode_polyline

_session = requests.Session()
_LATLON = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


class InvalidInput(ValueError):
    pass


class LocationNotFound(ValueError):
    pass


class ExternalServiceError(RuntimeError):
    pass


@dataclass
class Route:
    distance_miles: float
    duration_hours: float
    polyline: str
    coords: list  # [(lat, lon), ...]


def _in_usa(lat, lon):
    return 17.0 <= lat <= 72.0 and -180.0 <= lon <= -65.0  # CONUS + AK + HI (rough box)


def _key(prefix, *parts):
    return prefix + hashlib.md5("|".join(parts).lower().encode()).hexdigest()


def geocode(query: str):
    """'lat,lon' is used as-is (0 API calls); free text goes to Nominatim (cached)."""
    m = _LATLON.match(query)
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        if not _in_usa(lat, lon):
            raise InvalidInput(f"Coordinates '{query}' are outside the USA.")
        return lat, lon

    key = _key("geo:", query.strip())
    hit = cache.get(key)
    if hit:
        return hit
    try:
        r = _session.get(
            f"{settings.NOMINATIM_URL}/search",
            params={"q": query, "format": "jsonv2", "countrycodes": "us", "limit": 1},
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            timeout=settings.EXTERNAL_TIMEOUT_SECONDS,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalServiceError(f"Geocoding service failed: {exc}") from exc
    if not data:
        raise LocationNotFound(f"Could not find a USA location for '{query}'.")
    result = (float(data[0]["lat"]), float(data[0]["lon"]))
    cache.set(key, result, settings.EXTERNAL_CACHE_SECONDS)
    return result


def get_route(start, finish) -> Route:
    """ONE OSRM call returns the full route geometry, distance and duration."""
    key = _key("route:", f"{start[0]:.4f},{start[1]:.4f}", f"{finish[0]:.4f},{finish[1]:.4f}")
    hit = cache.get(key)
    if hit:
        return hit
    url = (
        f"{settings.OSRM_URL}/route/v1/driving/"
        f"{start[1]},{start[0]};{finish[1]},{finish[0]}"
    )
    try:
        r = _session.get(
            url,
            params={"overview": "full", "geometries": "polyline", "steps": "false"},
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            timeout=settings.EXTERNAL_TIMEOUT_SECONDS,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalServiceError(f"Routing service failed: {exc}") from exc
    if data.get("code") != "Ok" or not data.get("routes"):
        raise LocationNotFound("No drivable route found between the given locations.")
    best = data["routes"][0]
    route = Route(
        distance_miles=best["distance"] / 1609.344,
        duration_hours=best["duration"] / 3600,
        polyline=best["geometry"],
        coords=decode_polyline(best["geometry"]),
    )
    cache.set(key, route, settings.EXTERNAL_CACHE_SECONDS)
    return route
