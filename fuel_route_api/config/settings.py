import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = ["stations", "trips"]
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

# Swap for Redis/Memcached in production so the cache is shared across workers.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
LANGUAGE_CODE = "en-us"

# ---- Fuel planner settings ----
VEHICLE_RANGE_MILES = float(os.getenv("VEHICLE_RANGE_MILES", 500))
VEHICLE_MPG = float(os.getenv("VEHICLE_MPG", 10))
MAX_DETOUR_MILES = float(os.getenv("MAX_DETOUR_MILES", 15))  # station-to-route distance

# ---- Free external APIs (no key needed) ----
OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
HTTP_USER_AGENT = os.getenv("HTTP_USER_AGENT", "fuel-route-api/1.0 (assessment project)")
EXTERNAL_TIMEOUT_SECONDS = 15
EXTERNAL_CACHE_SECONDS = 60 * 60 * 24
