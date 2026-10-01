"""
Load the fuel-price CSV into the DB, geocoding each station's city once (offline).

Usage:
    python manage.py load_stations data/fuel-prices.csv --cities data/uscities.csv
    python manage.py load_stations data/fuel-prices.csv --cities data/uscities.csv --nominatim

`uscities.csv` = free "US Cities Database (basic)" from simplemaps.com
(columns used: city, state_id, lat, lng). --nominatim geocodes cities missing
from that file (1 req/sec, results cached in data/geocode_cache.json).
"""
import csv
import json
import re
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from stations.models import FuelStation


def norm(city: str) -> str:
    city = city.lower().replace(".", "").replace("'", "")
    city = re.sub(r"^ft\b", "fort", city)
    city = re.sub(r"^mt\b", "mount", city)
    city = re.sub(r"^st\b", "saint", city)
    return re.sub(r"\s+", " ", city).strip()


class CityGeocoder:
    def __init__(self, cities_csv=None, use_nominatim=False):
        self.table = {}
        self.use_nominatim = use_nominatim
        self.cache_path = Path(settings.BASE_DIR) / "data" / "geocode_cache.json"
        self.cache = json.loads(self.cache_path.read_text()) if self.cache_path.exists() else {}
        if cities_csv:
            with open(cities_csv, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    key = (norm(r["city"]), r["state_id"].upper())
                    self.table.setdefault(key, (float(r["lat"]), float(r["lng"])))

    def lookup(self, city, state):
        key = (norm(city), state.upper())
        if key in self.table:
            return self.table[key]
        ck = f"{key[0]}|{key[1]}"
        if ck in self.cache:
            return tuple(self.cache[ck]) if self.cache[ck] else None
        if not self.use_nominatim:
            return None
        time.sleep(1.1)  # Nominatim usage policy
        try:
            r = requests.get(
                f"{settings.NOMINATIM_URL}/search",
                params={"city": city, "state": state, "country": "US", "format": "jsonv2", "limit": 1},
                headers={"User-Agent": settings.HTTP_USER_AGENT},
                timeout=15,
            )
            data = r.json()
        except (requests.RequestException, ValueError):
            return None
        self.cache[ck] = [float(data[0]["lat"]), float(data[0]["lon"])] if data else None
        self.cache_path.write_text(json.dumps(self.cache))
        return tuple(self.cache[ck]) if self.cache[ck] else None


class Command(BaseCommand):
    help = "Load fuel stations from CSV (deduplicated, geocoded by city)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--cities", help="Path to simplemaps uscities.csv")
        parser.add_argument("--nominatim", action="store_true", help="Fallback geocoding via Nominatim")

    def handle(self, *args, csv_path, cities, nominatim, **opts):
        if not cities and not nominatim:
            raise CommandError("Provide --cities <uscities.csv> and/or --nominatim")

        # 1) read + dedupe (same id/address/city/state -> keep cheapest price)
        unique = {}
        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            for raw in csv.DictReader(fh):
                r = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
                try:
                    price = float(r["Retail Price"])
                    key = (int(r["OPIS Truckstop ID"]), r["Address"], r["City"], r["State"].upper())
                except (KeyError, ValueError):
                    continue
                if key not in unique or price < unique[key]["price"]:
                    unique[key] = {"name": r["Truckstop Name"], "price": price}

        # 2) geocode per unique city (thousands of rows share few cities)
        geo = CityGeocoder(cities, nominatim)
        city_cache, objs, skipped = {}, [], 0
        for (opis_id, address, city, state), v in unique.items():
            ck = (city, state)
            if ck not in city_cache:
                city_cache[ck] = geo.lookup(city, state)
            coords = city_cache[ck]
            if not coords:
                skipped += 1
                continue
            objs.append(
                FuelStation(opis_id=opis_id, name=v["name"], address=address, city=city,
                            state=state, price=v["price"], latitude=coords[0], longitude=coords[1])
            )

        FuelStation.objects.all().delete()
        FuelStation.objects.bulk_create(objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(objs)} stations ({skipped} skipped: city not geocoded)."
        ))
