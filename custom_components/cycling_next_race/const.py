"""Gedeelde constanten voor Cycling Next Race.

Staat apart zodat `config_flow.py`, `__init__.py` en `sensor.py` dezelfde
sleutels en standaardwaarden gebruiken zonder elkaar te importeren.
"""
from __future__ import annotations

DOMAIN = "cycling_next_race"
NAME = "Cycling Next Race"

# Gelijk aan "version" in manifest.json; hangt achter de kaart-URL zodat de
# browser na een update de nieuwe versie ophaalt. tests/test_repo.py bewaakt
# dat de twee niet uiteenlopen.
VERSION = "0.3.0"

# De meegeleverde Lovelace-kaart, door de integratie zelf geregistreerd.
KAART_BESTAND = "cycling-next-race-card.js"
KAART_URL = f"/{DOMAIN}/{KAART_BESTAND}"

# Optiesleutels (opgeslagen in ConfigEntry.options)
CONF_RESULT_N = "result_n"
CONF_GC_N = "gc_n"
CONF_UPCOMING_N = "upcoming_n"
CONF_UPCOMING_DAYS = "upcoming_days"
CONF_SCAN_MINUTES = "scan_minutes"
CONF_LIVE_SCAN_MINUTES = "live_scan_minutes"

# Standaardwaarden; gelijk aan wat de integratie vóór de config flow gebruikte
DEFAULT_RESULT_N = 10
DEFAULT_GC_N = 10
DEFAULT_UPCOMING_N = 10
DEFAULT_UPCOMING_DAYS = 7
DEFAULT_SCAN_MINUTES = 30
DEFAULT_LIVE_SCAN_MINUTES = 5

# Grenzen voor het optiescherm. Ruim genoeg om iets zinnigs in te stellen,
# strak genoeg om procyclingstats niet te overvragen.
MIN_SCAN_MINUTES = 5
MAX_SCAN_MINUTES = 240
MIN_LIVE_SCAN_MINUTES = 2
MAX_LIVE_SCAN_MINUTES = 60
MIN_RIDERS = 3
MAX_RIDERS = 30
MIN_UPCOMING_DAYS = 1
MAX_UPCOMING_DAYS = 21

OPTION_DEFAULTS: dict[str, int] = {
    CONF_RESULT_N: DEFAULT_RESULT_N,
    CONF_GC_N: DEFAULT_GC_N,
    CONF_UPCOMING_N: DEFAULT_UPCOMING_N,
    CONF_UPCOMING_DAYS: DEFAULT_UPCOMING_DAYS,
    CONF_SCAN_MINUTES: DEFAULT_SCAN_MINUTES,
    CONF_LIVE_SCAN_MINUTES: DEFAULT_LIVE_SCAN_MINUTES,
}
