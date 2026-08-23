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
VERSION = "0.15.1"

# De meegeleverde Lovelace-kaart, door de integratie zelf geregistreerd.
KAART_BESTAND = "cycling-next-race-card.js"
KAART_URL = f"/{DOMAIN}/{KAART_BESTAND}"

# Optiesleutels (opgeslagen in ConfigEntry.options)
CONF_RESULT_N = "result_n"
CONF_GC_N = "gc_n"
# Hoeveel renners er in de startlijst staan zolang een koers nog geen
# uitslag heeft.
CONF_START_N = "start_n"
CONF_UPCOMING_N = "upcoming_n"
CONF_UPCOMING_DAYS = "upcoming_days"
CONF_SCAN_MINUTES = "scan_minutes"
CONF_LIVE_SCAN_MINUTES = "live_scan_minutes"
# Welke niveaus de integratie volgt, en welke daarvan alleen in de pop-up
# mogen staan. Zie NIVEAUS hieronder.
CONF_LEVELS = "levels"
CONF_LEVELS_POPUP = "levels_popup"
CONF_MAX_OTHER = "max_other"

# De niveaus (bij procyclingstats: het `circuit=`-nummer in races.php).
#
# `zeker` zegt of het nummer geverifieerd is tegen de echte site. Voor de
# WorldTour is dat gebeurd; ProSeries is overgenomen uit wat het nummer
# hoort te zijn en kon van hieruit niet worden nagekeken — de sandbox komt
# niet bij procyclingstats. Klopt een nummer niet, dan levert dat niveau
# stil een lege kalender op; `_fetch_calendar` logt daarom een
# waarschuwing en de sensor zet het attribuut `levels_diag` met het aantal
# koersen per niveau, zodat je het in de interface ziet staan.
#
# `vrouwen` bepaalt de vlag op elke koers uit dat niveau; die komt niet uit
# de kalenderpagina zelf.
NIVEAUS: dict[str, dict] = {
    "1": {"naam": "WorldTour mannen", "vrouwen": False, "zeker": True},
    "24": {"naam": "WorldTour vrouwen", "vrouwen": True, "zeker": True},
    "26": {"naam": "ProSeries mannen", "vrouwen": False, "zeker": False},
    "27": {"naam": "ProSeries vrouwen", "vrouwen": True, "zeker": False},
}

# Wat het optiescherm als keuzelijst laat zien: nummer -> naam.
NIVEAU_KEUZE: dict[str, str] = {k: v["naam"] for k, v in NIVEAUS.items()}

# Standaardwaarden; gelijk aan wat de integratie vóór de config flow gebruikte
DEFAULT_RESULT_N = 10
DEFAULT_GC_N = 10
DEFAULT_START_N = 10
DEFAULT_UPCOMING_N = 10
DEFAULT_UPCOMING_DAYS = 7
DEFAULT_SCAN_MINUTES = 30
DEFAULT_LIVE_SCAN_MINUTES = 5
# Alleen de WorldTour, en niets dat alleen in de pop-up staat: precies de
# kalender zoals de integratie hem altijd al liet zien.
DEFAULT_LEVELS = ["1", "24"]
DEFAULT_LEVELS_POPUP: list[str] = []
DEFAULT_MAX_OTHER = 2

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
# 0 = geen knoppen in de pop-up, alleen de getoonde koers. Hoger dan 4 heeft
# weinig zin: elke koers erbij kost verzoeken bij procyclingstats en ruimte
# in de attributen.
MIN_OTHER = 0
MAX_OTHER_LIMIT = 4

# Niet alleen getallen: `levels` en `levels_popup` zijn lijstjes met
# niveaus. De coordinator leest die met `_opt_niveaus()` in plaats van
# `_opt()`.
OPTION_DEFAULTS: dict[str, object] = {
    CONF_RESULT_N: DEFAULT_RESULT_N,
    CONF_GC_N: DEFAULT_GC_N,
    CONF_START_N: DEFAULT_START_N,
    CONF_UPCOMING_N: DEFAULT_UPCOMING_N,
    CONF_UPCOMING_DAYS: DEFAULT_UPCOMING_DAYS,
    CONF_SCAN_MINUTES: DEFAULT_SCAN_MINUTES,
    CONF_LIVE_SCAN_MINUTES: DEFAULT_LIVE_SCAN_MINUTES,
    CONF_LEVELS: DEFAULT_LEVELS,
    CONF_LEVELS_POPUP: DEFAULT_LEVELS_POPUP,
    CONF_MAX_OTHER: DEFAULT_MAX_OTHER,
}
