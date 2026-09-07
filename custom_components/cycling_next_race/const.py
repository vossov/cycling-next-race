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
VERSION = "0.27.0"

# De meegeleverde Lovelace-kaart, door de integratie zelf geregistreerd.
KAART_BESTAND = "cycling-next-race-card.js"
KAART_URL = f"/{DOMAIN}/{KAART_BESTAND}"

# Optiesleutels (opgeslagen in ConfigEntry.options)
CONF_RESULT_N = "result_n"
CONF_GC_N = "gc_n"
# Hoeveel renners er per ploeg in de startlijst staan zolang een koers nog
# geen uitslag heeft. Per ploeg en niet in totaal, want dat is de enige
# indeling die cyclingstage geeft: één blok per ploeg, op rugnummer.
CONF_START_N = "start_n"
CONF_UPCOMING_N = "upcoming_n"
CONF_PAST_N = "past_n"
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
# `vrouwen` zegt welke koersen dit niveau oplevert.
#
# Tot 0.18 waren dit de `circuit=`-nummers van procyclingstats, met
# WorldTour en ProSeries apart. Die bron is onbereikbaar; cyclingstage kent
# géén UCI-niveaus — "WorldTour" en "ProSeries" komen op de kalenderpagina
# niet één keer voor. Mannen en vrouwen zijn wél betrouwbaar te scheiden,
# uit de koersnaam én uit het adres, onafhankelijk van elkaar.
NIVEAUS: dict[str, dict] = {
    "m": {"naam": "Mannen", "vrouwen": False, "zeker": True},
    "v": {"naam": "Vrouwen", "vrouwen": True, "zeker": True},
}

# Wat er in de opslag kan staan van vóór 0.19: de oude circuitnummers.
# Zonder deze vertaling zou een bestaande installatie na de update op een
# lege keuze uitkomen en stilletjes terugvallen op de standaard.
OUDE_NIVEAUS: dict[str, str] = {"1": "m", "26": "m", "24": "v", "27": "v"}

# Wat het optiescherm als keuzelijst laat zien: nummer -> naam.
NIVEAU_KEUZE: dict[str, str] = {k: v["naam"] for k, v in NIVEAUS.items()}

# Standaardwaarden; gelijk aan wat de integratie vóór de config flow gebruikte
DEFAULT_RESULT_N = 10
DEFAULT_GC_N = 10
# Eén renner per ploeg. Dat is bewust zuinig: 23 ploegen x 1 is zo'n 1,7 kB
# in de attributen en die zitten al ruim boven de grens van de recorder.
# Hoger zetten mag, het kost ongeveer even veel per stap erbij.
DEFAULT_START_N = 1
DEFAULT_UPCOMING_N = 10
# Hoeveel gereden etappes je in de pop-up terug kunt bladeren. Elke etappe
# kost een verzoek (eenmalig — een gereden uitslag verandert niet meer) en
# ruim 400 bytes in de attributen, en die zitten al tegen de grens van de
# recorder aan. Vandaar bescheiden; 0 zet het uit en `MAX_PAST_N` is het
# maximum voor wie een hele grote ronde wil kunnen terugbladeren.
DEFAULT_PAST_N = 3
# Hoeveel renners per teruggebladerde etappe. Korter dan de gewone uitslag:
# wie derde werd in etappe 7 wil je nog weten, wie negende niet.
PAST_RESULT_N = 5
DEFAULT_UPCOMING_DAYS = 7
DEFAULT_SCAN_MINUTES = 30
DEFAULT_LIVE_SCAN_MINUTES = 5
# Alleen de WorldTour, en niets dat alleen in de pop-up staat: precies de
# kalender zoals de integratie hem altijd al liet zien.
DEFAULT_LEVELS = ["m", "v"]
DEFAULT_LEVELS_POPUP: list[str] = []
DEFAULT_MAX_OTHER = 2

# Grenzen voor het optiescherm. Ruim genoeg om iets zinnigs in te stellen,
# strak genoeg om procyclingstats niet te overvragen.
MIN_SCAN_MINUTES = 5
MAX_SCAN_MINUTES = 240
MIN_LIVE_SCAN_MINUTES = 2
MAX_LIVE_SCAN_MINUTES = 60
MIN_RIDERS = 3
# Renners per ploeg in de startlijst; een grote ronde heeft er acht.
MIN_START_N = 1
MAX_START_N = 8

# Opties waarvan de betekenis is veranderd en waarvan een opgeslagen waarde
# dus buiten het nieuwe bereik kan vallen. `start_n` telde tot 0.24 renners
# in totaal (3..30) en telt sinds 0.26 renners per ploeg (1..8): een entry
# van vóór die wijziging draagt bijvoorbeeld 10, en dan levert het
# optiescherm een standaardwaarde op die het eigen schema afkeurt — het
# formulier is dan niet meer in te dienen. Bovendien zou 10 per ploeg de
# hele startlijst van 184 renners in de attributen zetten.
OPTIE_GRENZEN: dict[str, tuple] = {
    CONF_START_N: (MIN_START_N, MAX_START_N),
}


def binnen_grenzen(sleutel: str, waarde):
    """Een opgeslagen optiewaarde naar het geldige bereik trekken.

    Alleen voor de sleutels in `OPTIE_GRENZEN`; de rest komt onveranderd
    terug. Onleesbare waarden vallen terug op de standaard, net als in
    `_opt()` op de coordinator.
    """
    grens = OPTIE_GRENZEN.get(sleutel)
    if grens is None:
        return waarde
    try:
        getal = int(waarde)
    except (TypeError, ValueError):
        return OPTION_DEFAULTS[sleutel]
    return max(grens[0], min(grens[1], getal))
MAX_RIDERS = 30
MIN_UPCOMING_DAYS = 1
MAX_UPCOMING_DAYS = 21
# 0 = geen knoppen in de pop-up, alleen de getoonde koers. Hoger dan 4 heeft
# weinig zin: elke koers erbij kost verzoeken bij procyclingstats en ruimte
# in de attributen.
MIN_OTHER = 0
MAX_OTHER_LIMIT = 4
# Hoe ver je hoogstens kunt terugbladeren. 21 = een hele grote ronde, want
# dat is wat je bij de Vuelta of de Tour wilt kunnen. Het is bewust geen
# standaard: elke etappe kost ruim 400 bytes in de attributen en die zitten
# in de praktijk al boven de 16 kB van de recorder (zie "Omvang van de
# attributen" in CLAUDE.md). Wie hem hoog zet ruilt de historie van de
# sensor in voor terugbladeren op het dashboard; de sensor zelf en de kaart
# blijven het gewoon doen.
MAX_PAST_N = 21

# Niet alleen getallen: `levels` en `levels_popup` zijn lijstjes met
# niveaus. De coordinator leest die met `_opt_niveaus()` in plaats van
# `_opt()`.
OPTION_DEFAULTS: dict[str, object] = {
    CONF_RESULT_N: DEFAULT_RESULT_N,
    CONF_GC_N: DEFAULT_GC_N,
    CONF_START_N: DEFAULT_START_N,
    CONF_UPCOMING_N: DEFAULT_UPCOMING_N,
    CONF_PAST_N: DEFAULT_PAST_N,
    CONF_UPCOMING_DAYS: DEFAULT_UPCOMING_DAYS,
    CONF_SCAN_MINUTES: DEFAULT_SCAN_MINUTES,
    CONF_LIVE_SCAN_MINUTES: DEFAULT_LIVE_SCAN_MINUTES,
    CONF_LEVELS: DEFAULT_LEVELS,
    CONF_LEVELS_POPUP: DEFAULT_LEVELS_POPUP,
    CONF_MAX_OTHER: DEFAULT_MAX_OTHER,
}
