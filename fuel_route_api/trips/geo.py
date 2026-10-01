import numpy as np

EARTH_RADIUS_MI = 3958.8


def haversine_miles(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * np.arcsin(np.sqrt(a))


def to_xyz(lats, lons):
    """3-D coordinates (miles) so a KD-tree gives ~true distances anywhere."""
    lat, lon = np.radians(lats), np.radians(lons)
    return EARTH_RADIUS_MI * np.column_stack(
        (np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat))
    )


def decode_polyline(encoded: str, precision: int = 5):
    """Decode a Google/OSRM encoded polyline -> list of (lat, lon)."""
    coords, index, lat, lng, factor = [], 0, 0, 0, 10 ** precision
    while index < len(encoded):
        for is_lng in (False, True):
            shift = result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lng:
                lng += delta
            else:
                lat += delta
        coords.append((lat / factor, lng / factor))
    return coords
