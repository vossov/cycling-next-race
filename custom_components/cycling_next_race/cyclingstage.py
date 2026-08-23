"""Cyclingstage.com als bron voor de kalender en de koersgegevens.

Waarom een eigen bestand: procyclingstats.com is sinds 23 augustus 2026
onbereikbaar (Cloudflare-uitdaging, zie CLAUDE.md) en die weg is uitgeput.
Cyclingstage leverde al de GPX-profielen, de tijdschema's en de
etappeteksten, en blijkt de rest ook te hebben. Tijdens de overgang staat
de nieuwe bron hier los van `sensor.py`, zodat de oude PCS-code ernaast
blijft werken en er stap voor stap overgezet kan worden.

**Alles hier is beproefd op echte HTML** uit `tests/fixtures/`, niet op
verzonnen voorbeelden. Dat is een harde projectregel: verzonnen HTML heeft
al twee keer een echte bug gemaskeerd.
"""
from __future__ import annotations

import logging
import re
from datetime import date

_LOGGER = logging.getLogger(__name__)

BASIS = "https://www.cyclingstage.com"

# De kalender van een heel jaar op één pagina, één tabel per maand.
KALENDER_URL = BASIS + "/uci/cycling-calendar-{y}/"

MAANDEN = {naam: nr for nr, naam in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}

# Vrouwenkoersen zijn te herkennen aan de naam én aan het adres; die twee
# zijn onafhankelijk van elkaar, dus samen is dit geen gok. Cyclingstage
# kent géén UCI-niveaus (de woorden "WorldTour" en "ProSeries" komen op de
# kalenderpagina niet voor), dus dit is de enige indeling die er is.
_VROUWEN = re.compile(r"\bdonne\b|\bfemmes\b|\bfemenina\b|\bwomen\b|\(w\)", re.I)

_TABEL = re.compile(r"(<table[^>]*>.*?</table>)", re.S | re.I)
_RIJ = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CEL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_HREF = re.compile(r'href="([^"]+)"', re.I)
# "1", "20-25" of "4/28-3": de tabel staat onder de maand waarin de koers
# eindigt, en een koers die in een eerdere maand begint krijgt die maand
# ervoor. Zonder dat voorvoegsel loopt de Vuelta (8/22-13 onder September)
# van 22 september tot 13 september.
_DATUM = re.compile(r"(?:(\d{1,2})/)?(\d{1,2})(?:\s*-\s*(\d{1,2}))?$")


def _kaal(html: str) -> str:
    """Platte tekst uit een stukje HTML."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def _adres(cel: str) -> str:
    """Het eerste adres uit een cel, als volledig adres.

    Cyclingstage schrijft de meeste links relatief (`/vuelta-2026-route/`)
    maar niet allemaal; en er staat minstens één kapotte link op de pagina
    (`http://Tour de France Femmes 2026`). Wat geen pad en geen adres op
    cyclingstage is, telt niet mee.
    """
    m = _HREF.search(cel or "")
    if not m:
        return ""
    u = m.group(1).strip()
    if u.startswith("/"):
        return BASIS + u
    if re.match(r"https?://(www\.)?cyclingstage\.com/", u):
        return re.sub(r"^http://", "https://", u)
    return ""


def parse_kalender(html: str, jaar: int) -> list[dict]:
    """De koersen van een jaar uit de kalenderpagina van cyclingstage.

    Geeft per koers: naam, begin- en einddatum, of het een vrouwenkoers is,
    het adres van de koerspagina en dat van de routepagina.

    Dat laatste is de winst ten opzichte van procyclingstats: het adres van
    elke koers staat er gewoon, dus het hoeft niet uit een sjabloon geraden
    te worden. Precies dat raden kostte eerder het profiel van de Vuelta en
    de colnamen van de Giro.

    De lijst is wat cyclingstage dekt, en dat is een redactionele keuze —
    "the races we are passionate about", staat er boven de tabel. Voor de
    mannen is dat vrijwel de hele WorldTour; bij de vrouwen ontbreken de
    rondes van een week. Wat er niet in staat heeft ook geen profiel en
    geen tijdschema, dus het zou toch leeg blijven.
    """
    uit: list[dict] = []
    maand = 1
    for stuk in _TABEL.split(html or ""):
        if stuk.lstrip().lower().startswith("<table"):
            uit.extend(_rijen(stuk, jaar, maand))
            continue
        # tussen de tabellen staat de maandnaam als kop
        tekst = _kaal(stuk)
        if tekst in MAANDEN:
            maand = MAANDEN[tekst]
    _LOGGER.debug("Kalender %s: %s koersen (%s vrouwen)", jaar, len(uit),
                  sum(1 for k in uit if k["women"]))
    return uit


def _rijen(tabel: str, jaar: int, maand: int) -> list[dict]:
    """De koersen uit één maandtabel."""
    uit = []
    for rij in _RIJ.findall(tabel):
        if "<th" in rij.lower():
            continue
        cellen = _CEL.findall(rij)
        if len(cellen) < 4:
            continue
        m = _DATUM.match(_kaal(cellen[0]))
        naam = _kaal(cellen[1])
        if not m or not naam:
            continue
        try:
            start = date(jaar, int(m.group(1) or maand), int(m.group(2)))
            eind = date(jaar, maand, int(m.group(3))) if m.group(3) else start
        except ValueError:  # onmogelijke datum op de pagina
            _LOGGER.debug("Kalenderdatum onbruikbaar: %s (%s)",
                          _kaal(cellen[0]), naam)
            continue
        route = _adres(cellen[3])
        uit.append({
            "name": naam,
            "start": start,
            "end": eind,
            "women": bool(_VROUWEN.search(naam) or _VROUWEN.search(route)),
            "url": _adres(cellen[1]),
            "route_url": route,
        })
    return uit
