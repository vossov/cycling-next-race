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


# ── etappelijst ─────────────────────────────────────────────────────

# Op de routepagina van een rittenkoers staat één tabel: nummer, datum,
# "start - finish", afstand en terreintype, met per etappe het adres.
_TYPES = {
    "flat": "flat", "hills": "hilly", "hils": "hilly",  # "hils" staat zo op de site
    "mountains": "mountain", "mountain": "mountain",
    "itt": "itt", "ttt": "ttt", "prologue": "prologue",
}
# "22-8" = dag-maand; het jaar komt van de koers.
_DAGMAAND = re.compile(r"(\d{1,2})\s*-\s*(\d{1,2})$")


def parse_etappes(html: str, jaar: int) -> list[dict]:
    """De etappes van een rittenkoers uit zijn routepagina.

    Per etappe: nummer, datum, "start - finish", afstand, terreintype en het
    eigen adres. Dat adres is opnieuw de winst — de etappepagina hoeft niet
    uit een sjabloon geraden te worden.

    Rustdagen staan als eigen rij met een lege nummerkolom en `rest day`
    over drie kolommen. Ze worden overgeslagen: een rustdag is geen etappe,
    en de nummering in de eerste kolom loopt gewoon door, dus er valt niets
    mis te tellen.
    """
    uit: list[dict] = []
    tabel = _TABEL.search(html or "")
    if not tabel:
        _LOGGER.debug("Routepagina zonder tabel")
        return uit
    for rij in _RIJ.findall(tabel.group(0)):
        if "<th" in rij.lower():
            continue
        cellen = _CEL.findall(rij)
        nummer = _kaal(cellen[0]) if cellen else ""
        if len(cellen) < 5 or not nummer.isdigit():
            continue  # rustdag of een rij die we niet herkennen
        m = _DAGMAAND.match(_kaal(cellen[1]))
        if not m:
            continue
        try:
            dag = date(jaar, int(m.group(2)), int(m.group(1)))
        except ValueError:
            _LOGGER.debug("Etappedatum onbruikbaar: %s", _kaal(cellen[1]))
            continue
        naam = _kaal(cellen[2])
        uit.append({
            "idx": int(nummer),
            "date": dag,
            "name": naam,
            "departure": _plaats(naam, 0),
            "arrival": _plaats(naam, 1),
            "distance_km": _getal(_kaal(cellen[3])),
            "stage_type": _TYPES.get(_kaal(cellen[4]).lower(), ""),
            "url": _adres(cellen[2]),
        })
    _LOGGER.debug("Routepagina: %s etappes", len(uit))
    return uit


def _plaats(naam: str, kant: int) -> str:
    """Vertrek of aankomst uit "Start - Finish".

    Spaties rond het koppelteken zijn vereist, zodat plaatsnamen als
    Orcières-Merlette en Vall d'Alba heel blijven.
    """
    delen = re.split(r"\s+[-–]\s+", naam or "", maxsplit=1)
    return delen[kant].strip() if len(delen) > kant else ""


def _getal(tekst: str):
    try:
        return float(tekst.replace(",", "."))
    except (TypeError, ValueError):
        return None


# ── de etappetekst ──────────────────────────────────────────────────

# De colnamen uit deze tekst worden al door `_fetch_stage_names` in
# sensor.py gehaald; die code is beproefd en blijft. Hier staat alleen wat
# daar níét uit kwam en wat we tot nu toe bij procyclingstats haalden.
_START_TIJD = re.compile(r"starts?\s+at\s+(\d{1,2}[:.]\d{2})", re.I)
_FINISH_TIJD = re.compile(r"expected\s+to\s+finish\s+around\s+(\d{1,2}[:.]\d{2})", re.I)
# "2,953 metres of elevation gain" — de komma is een duizendtalscheiding.
_HOOGTE = re.compile(
    r"([\d.,]+)\s*(?:metres|meters|m)\s+of\s+(?:elevation|climbing|vertical)", re.I)


def parse_etappe_meta(html: str) -> dict:
    """Starttijd, verwachte finishtijd en hoogtemeters uit de etappetekst.

    Cyclingstage schrijft dit in gewone zinnen: "Stage 4 of the Vuelta
    starts at 14:40 and the race is expected to finish around 17:30 - both
    local times (CEST)", en "a route featuring 2,953 metres of elevation
    gain".

    De verwachte finishtijd is beter dan wat we hadden: bij procyclingstats
    werd die geschat uit afstand en profiel (`_finish_est`), hier staat hij
    er gewoon. De starttijd kwam van procyclingstats en staat hier ook.

    Wat niet gevonden wordt blijft weg uit het resultaat; niets schatten.
    """
    tekst = _plat(html)
    uit: dict = {}
    m = _START_TIJD.search(tekst)
    if m:
        uit["start_time"] = m.group(1).replace(".", ":")
    m = _FINISH_TIJD.search(tekst)
    if m:
        uit["finish_time"] = m.group(1).replace(".", ":")
    m = _HOOGTE.search(tekst)
    if m:
        try:
            uit["vertical_m"] = int(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return uit


def _plat(html: str) -> str:
    """Platte tekst van een hele pagina, script en style eruit."""
    from html import unescape

    doc = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html or "",
                 flags=re.S | re.I)
    tekst = unescape(re.sub(r"<[^>]+>", " ", doc))
    return re.sub(r"[ \t\r\n\u00a0]+", " ", tekst)
