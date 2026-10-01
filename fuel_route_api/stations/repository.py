"""In-memory, numpy-backed view of all stations (loaded once per process)."""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .models import FuelStation
from trips.geo import haversine_miles


@dataclass(frozen=True)
class StationIndex:
    records: tuple      # tuple of dicts (name, address, city, state, ...)
    lats: np.ndarray
    lons: np.ndarray
    prices: np.ndarray

    def __len__(self):
        return len(self.records)

    def nearest_price(self, lat, lon):
        """Price at the station closest to a point (used to price the first fill-up)."""
        d = haversine_miles(self.lats, self.lons, lat, lon)
        return float(self.prices[int(np.argmin(d))])


@lru_cache(maxsize=1)
def get_station_index() -> StationIndex:
    rows = list(
        FuelStation.objects.values(
            "name", "address", "city", "state", "price", "latitude", "longitude"
        )
    )
    return StationIndex(
        records=tuple(rows),
        lats=np.array([r["latitude"] for r in rows], dtype=float),
        lons=np.array([r["longitude"] for r in rows], dtype=float),
        prices=np.array([r["price"] for r in rows], dtype=float),
    )
