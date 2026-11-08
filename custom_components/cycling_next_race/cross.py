"""Parsers voor cyclocross: de officiële sites van drie series.

Sinds 0.33. Cyclingstage heeft geen cross, en de bron die alles heeft
(CyclingFlash) zit achter een Cloudflare-uitdaging die curl en dus ook Home
Assistant tegenhoudt — dat is het procyclingstats-scenario van augustus 2026
opnieuw. Wat wél open is, zijn de sites van de series zelf:

| serie | site | wat er staat |
|---|---|---|
| Superprestige | superprestigecyclocross.be | kalender (zie hieronder), programma met starttijd per categorie, zenders per land, podium per categorie |
| UCI-wereldbeker | ucicyclocrossworldcup.com | kalender, programma met starttijden |
| X²O Trofee | x2otrofee.be | kalender; geen tijden, uitslagen op de sites van de organisatoren |

De Superprestige en de wereldbeker draaien op hetzelfde platform (Flanders
Classics, gebouwd door Dynamate), met dezelfde opmaak; één parser bedient
ze allebei. Alles is beproefd op de echte pagina's van 8 november 2026 in
`tests/fixtures/`, op één uitzondering na: zie `SP_KALENDER_URL`.

Losse crossen buiten deze drie series staan er niet in. Dat is een bewuste
grens: geen bron, dan geen koers.
"""
from __future__ import annotations

import html as _html
import re
import unicodedata
from datetime import date

SP_BASIS = "https://www.superprestigecyclocross.be"
# Nagekeken op 8 november 2026 (`superprestige_kalender_cx_2026-11-08.html`):
# acht manches, dezelfde opmaak als de wereldbekerkalender.
SP_KALENDER_URL = SP_BASIS + "/nl/kalender"
SP_UITSLAGEN_URL = SP_BASIS + "/nl/uitslagen"
WB_BASIS = "https://www.ucicyclocrossworldcup.com"
WB_KALENDER_URL = WB_BASIS + "/en/calendar"
# Dezelfde opmaak als de uitslagen van de Superprestige, op één verschil na:
# de plaats staat in een <p> in plaats van een <h2>
# (`ucicxworldcup_uitslagen_cx_2026-11-08.html`).
WB_UITSLAGEN_URL = WB_BASIS + "/en/results"
X2O_KALENDER_URL = "https://x2otrofee.be/"

SERIES = {
    "sp": "Superprestige",
    "wb": "Wereldbeker",
    "x2o": "X²O Trofee",
}

# Het land van een manche staat er als `alt` bij de vlag, in de taal van de
# site. Tijden op een manchepagina noemen geen zone: het is de lokale tijd
# van die plek. Een land dat hier niet staat laat de tijd onomgerekend.
LAND_ZONE = {
    "belgium": "Europe/Brussels", "belgië": "Europe/Brussels",
    "netherlands": "Europe/Amsterdam", "nederland": "Europe/Amsterdam",
    "czech republic": "Europe/Prague", "tsjechië": "Europe/Prague",
    "france": "Europe/Paris", "frankrijk": "Europe/Paris",
    "spain": "Europe/Madrid", "spanje": "Europe/Madrid",
    "italy": "Europe/Rome", "italië": "Europe/Rome",
    "germany": "Europe/Berlin", "duitsland": "Europe/Berlin",
    "switzerland": "Europe/Zurich", "zwitserland": "Europe/Zurich",
    "luxembourg": "Europe/Luxembourg", "luxemburg": "Europe/Luxembourg",
    "united kingdom": "Europe/London", "great britain": "Europe/London",
    "verenigd koninkrijk": "Europe/London",
    "united states": "America/New_York",
}

_MAANDEN = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "augustus": 8, "september": 9, "oktober": 10,
    "november": 11, "december": 12,
}


def _kaal(tekst: str) -> str:
    """Tags eruit, entiteiten omgezet, witruimte samengevoegd."""
    t = re.sub(r"<[^>]+>", " ", tekst or "")
    t = _html.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def _datum_kort(tekst: str) -> date | None:
    """`27/11/26` → 27 november 2026."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2})\b", tekst or "")
    if not m:
        return None
    try:
        return date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _plaatssleutel(plaats: str) -> str:
    """"Tábor" en "Tabor" zijn dezelfde plaats.

    De kalender van de wereldbeker schrijft de plaatsnaam met accent, de
    uitslagenpagina zonder. Zonder deze vergelijking vond `podium` de
    uitslag van Tábor nooit.
    """
    t = unicodedata.normalize("NFKD", plaats or "")
    return "".join(c for c in t if not unicodedata.combining(c)).strip().lower()


def zone_van(land: str) -> str:
    return LAND_ZONE.get((land or "").strip().lower(), "")


# ── Flanders Classics: Superprestige en wereldbeker ──────────────────

_BLOK = re.compile(r'class="competition-block(?:\s[^"]*)?"', re.I)
_MANCHE_HREF = re.compile(
    r'href="([^"]*/(?:calendar|kalender)/\d{4}-\d{4}/[^"#?]+)"', re.I)


def parse_fc_kalender(html: str) -> list[dict]:
    """De manches van een kalenderpagina van het Flanders Classics-platform.

    Per manche een `competition-block` met de datum (`27/11/26`), de plaats,
    de vlag met het land als `alt` en een link "More info" naar de
    manchepagina. De eerstvolgende manche staat er nog een keer apart
    bovenaan ("Next round"); dubbele adressen vallen weg.
    """
    stukken = _BLOK.split(html or "")[1:]
    uit, gezien = [], set()
    for stuk in stukken:
        # alleen tot het volgende blok kijken, anders leent een blok zonder
        # link die van zijn buurman
        datum = _datum_kort(
            (re.search(r'competition-block-date">([^<]+)<', stuk) or [None, ""])[1])
        href = _MANCHE_HREF.search(stuk)
        if not datum or not href:
            continue
        url = href.group(1)
        if url in gezien:
            continue
        gezien.add(url)
        plaats = ""
        m = re.search(r'competition-block-location">(.*?)</div>', stuk, re.S)
        if m:
            # de plaats staat in een <h2> (bovenaan) of een <p> (de lijst)
            n = re.search(r"<(?:h2|p)[^>]*>(.*?)</(?:h2|p)>", m.group(1), re.S)
            plaats = _kaal(n.group(1)) if n else ""
        land = (re.search(r'class="flag"[^>]*\balt="([^"]*)"', stuk) or [None, ""])[1]
        uit.append({"plaats": plaats, "datum": datum, "url": url,
                    "land": _html.unescape(land)})
    return uit


_NL_DATUM = re.compile(
    r"<p>\s*\w+dag\s+(\d{1,2})\s+(" + "|".join(_MAANDEN) + r")\s+(\d{4})\s*</p>",
    re.I)


def parse_fc_manche(html: str) -> dict:
    """Programma, datum, land en zenders van één manchepagina.

    Het programma staat als `next-race-programma-title` met de tijd in de
    alinea erna: `Elite Mannen` / `15:10`. Het bevat ook dingen als "Doors
    open" en "Afterparty"; die blijven gewoon in de lijst — de aanroeper
    zoekt de categorie die hij nodig heeft (`elite_tijd`).

    De zenders staan onder "Broadcasters" als `<strong>NLD</strong> -
    Eurosport 1`, per land.
    """
    h = html or ""
    programma = {}
    for titel, tijd in re.findall(
            r'next-race-programma-title">([^<]+)</p>\s*<p>\s*(\d{1,2}:\d{2})\s*</p>',
            h):
        programma.setdefault(_kaal(titel), tijd)
    datum = None
    m = _NL_DATUM.search(h)
    if m:
        try:
            datum = date(int(m.group(3)), _MAANDEN[m.group(2).lower()],
                         int(m.group(1)))
        except ValueError:
            datum = None
    land = ""
    kop = re.search(r'calendar-detail--header">(.*?)</div>', h, re.S)
    if kop:
        land = (re.search(r'class="flag"[^>]*\balt="([^"]*)"', kop.group(1))
                or [None, ""])[1]
    zenders = {}
    for code, naam in re.findall(
            r"<li>\s*<strong>\s*([A-Z]{2,5})(?:&nbsp;|\s)*</strong>(?:&nbsp;|\s)*-\s*([^<]+)</li>",
            h):
        zenders.setdefault(code, _kaal(naam))
    return {"programma": programma, "datum": datum,
            "land": _html.unescape(land), "zenders": zenders}


_ELITE = {
    False: re.compile(r"\belite\b.*\b(mannen|men|heren)\b|\b(mannen|men|heren)\b.*\belite\b", re.I),
    True: re.compile(r"\belite\b.*\b(vrouwen|women|dames)\b|\b(vrouwen|women|dames)\b.*\belite\b", re.I),
}


def elite_tijd(programma: dict, vrouwen: bool) -> str:
    """De starttijd van de elitewedstrijd van dit geslacht, of ""."""
    for titel, tijd in (programma or {}).items():
        if _ELITE[bool(vrouwen)].search(titel):
            return tijd
    return ""


def is_elite(titel: str, vrouwen: bool) -> bool:
    return bool(_ELITE[bool(vrouwen)].search(titel or ""))


# ── Superprestige: uitslagen ─────────────────────────────────────────

_PODIUMREGEL = re.compile(r"^(\d{1,3})\.\s+(.+?)\s+\(([A-Z]{3})\)$")


def parse_sp_uitslagen(html: str) -> list[dict]:
    """Alle manches op de uitslagenpagina, met per categorie het podium.

    Leest de Superprestige én de wereldbeker: hetzelfde platform.

    De pagina toont meerdere seizoenen onder elkaar (Overijse staat er als
    `25/10/26`, `26/10/25` en `27/10/24`); de datum houdt ze uit elkaar.
    Per categorie een `<h3>Elite Mannen :</h3>` met een lijst van drie:
    `1. Michael Vanthourenhout (BEL)` en de tijd (`01:03:18`) of de
    achterstand (`+00:15"`, met een aanhalingsteken als secondeteken).

    Meer dan het podium staat er niet; de volledige uitslag is een PDF.
    """
    uit = []
    delen = re.split(r'class="accordion--uitslagen-location">', html or "")[1:]
    for deel in delen:
        # tot de eerste tag: de Superprestige sluit af met </h2>, de
        # wereldbeker met </p>. Op "</h2>" knippen liet de plaats bij de
        # wereldbeker doorlopen over de hele manche.
        plaats = _kaal(deel.split("<", 1)[0])
        datum = _datum_kort(
            (re.search(r'accordion--uitslagen-date">([^<]+)<', deel) or [None, ""])[1])
        if not datum:
            continue
        categorieen = {}
        for kop, romp in re.findall(r"<h3>([^<]+)</h3>\s*<ol>(.*?)</ol>", deel, re.S):
            rijen = []
            for regel, tijd in re.findall(
                    r"<p>([^<]+)</p>\s*<p class=\"rankings-top-3-time\">([^<]*)</p>",
                    romp):
                m = _PODIUMREGEL.match(_kaal(regel))
                if not m:
                    continue
                t = _kaal(tijd).replace('"', "").strip()
                rijen.append({"rank": int(m.group(1)), "rider": m.group(2).strip(),
                              "country": m.group(3).lower(),
                              "time": re.sub(r"^\+\s*", "+", t)})
            if [r["rank"] for r in rijen] == list(range(1, len(rijen) + 1)) and rijen:
                categorieen[_kaal(kop).rstrip(" :")] = rijen
        uit.append({"plaats": plaats, "datum": datum, "categorieen": categorieen})
    return uit


def podium(manches: list[dict], datum: date, plaats: str, vrouwen: bool) -> list[dict]:
    """Het elitepodium van één manche, of [] als die er (nog) niet staat."""
    for m in manches or []:
        if m["datum"] != datum:
            continue
        if plaats and m["plaats"] and _plaatssleutel(m["plaats"]) != _plaatssleutel(plaats):
            continue
        for titel, rijen in m["categorieen"].items():
            if is_elite(titel, vrouwen):
                return rijen
    return []


# ── X²O Trofee ───────────────────────────────────────────────────────

def parse_x2o_kalender(html: str) -> list[dict]:
    """De manches op de voorpagina van x2otrofee.be.

    `glz-event`-tegels met de datum (`zondag 01.11.2026`), de naam van de
    cross en de plaats, en een link naar de site van de organisator. Geen
    starttijden, geen land (het is een Belgische serie).
    """
    uit = []
    for stuk in re.split(r'class="glz-event\b', html or "")[1:]:
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", stuk)
        naam = re.search(r"<h5>(.*?)</h5>", stuk, re.S)
        if not m or not naam:
            continue
        try:
            datum = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        plaats = re.search(r'class="event-city">(.*?)</span>', stuk, re.S)
        href = re.search(r'<a href="([^"]+)"', stuk)
        uit.append({"naam": _kaal(naam.group(1)),
                    "plaats": _kaal(plaats.group(1)) if plaats else "",
                    "datum": datum,
                    "url": href.group(1) if href else ""})
    return uit
