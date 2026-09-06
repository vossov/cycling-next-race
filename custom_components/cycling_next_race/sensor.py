"""Sensor: eerstvolgende of lopende WorldTour-koers, van cyclingstage.com.

YAML-configuratie:

    sensor:
      - platform: cycling_next_race

Uitgebreide versie:
- Spoiler-vrije attributen voor tegel + pop-up (parcours, cols, profielscore ...).
- Spoiler-attributen ALLEEN bedoeld voor de pop-up (uitslag laatste etappe + klassement).
- Etappe-selectie met rollover: zodra de etappe van vandaag klaar is (uitslag binnen)
  toont de tegel de eerstvolgende etappe. Een rustdag telt niet als etappe.

De kalender wordt 1x per dag opgehaald; live wordt elk half uur ververst.

Tot 0.24 kwam alles van procyclingstats. Die bron zit sinds 23 augustus 2026
achter een Cloudflare-uitdaging die geen enkele HTTP-client passeert; in 0.25
is het laatste dat er nog naartoe ging eruit. Wat cyclingstage niet heeft —
de startlijst, de UCI-ploegcode, de dagwinst, de colcategorie — blijft leeg.
Zie CLAUDE.md.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from . import bronnen
from .const import (
    CONF_GC_N,
    CONF_LEVELS,
    CONF_LEVELS_POPUP,
    CONF_LIVE_SCAN_MINUTES,
    CONF_MAX_OTHER,
    CONF_RESULT_N,
    CONF_SCAN_MINUTES,
    CONF_UPCOMING_DAYS,
    CONF_UPCOMING_N,
    CONF_PAST_N,
    DEFAULT_GC_N,
    DEFAULT_LIVE_SCAN_MINUTES,
    DEFAULT_MAX_OTHER,
    DEFAULT_RESULT_N,
    DEFAULT_SCAN_MINUTES,
    DEFAULT_UPCOMING_DAYS,
    DEFAULT_UPCOMING_N,
    DOMAIN,
    NAME,
    NIVEAUS,
    OUDE_NIVEAUS,
    OPTION_DEFAULTS,
    PAST_RESULT_N,
)

_LOGGER = logging.getLogger(__name__)

# Standaardwaarden. Ze zijn in te stellen via het optiescherm; deze constanten
# blijven de terugval wanneer een optie ontbreekt.
SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_MINUTES)
LIVE_SCAN_INTERVAL = timedelta(minutes=DEFAULT_LIVE_SCAN_MINUTES)

RESULT_N = DEFAULT_RESULT_N  # aantal renners in de uitslag (pop-up)
GC_N = DEFAULT_GC_N          # aantal renners in het klassement (pop-up)
UPCOMING_N = DEFAULT_UPCOMING_N  # veiligheidscap op aantal komende etappes
UPCOMING_DAYS = DEFAULT_UPCOMING_DAYS  # venster voor "Komende dagen"

# Hoeveel koersen er naast de getoonde in de pop-up aanklikbaar zijn. Elke
# koers erbij kost twee extra paginaverzoeken bij cyclingstage en ruimte
# in de attributen; in de praktijk lopen er mannen en vrouwen tegelijk.
# In te stellen via `max_other`; dit is de standaard.
MAX_ANDERE_KOERSEN = DEFAULT_MAX_OTHER

# Hoeveel koersen er hoogstens tegelijk worden bekeken om te bepalen welke op
# de tegel komt en welke er in de pop-up naast passen. Alles daarboven kost
# alleen maar verzoeken: er staan er toch maar 1 + `max_other` in beeld.
MAX_ACTIEVE_KOERSEN = 6

# Hoeveel subpagina's van een koerspagina er hoogstens worden geprobeerd als
# de kalender geen routeadres geeft. Een koerspagina linkt naar een handvol
# eigen pagina's (route, favorieten, gpx, uitslagen); meer dan drie proberen
# is verzoeken doen om het doen.
MAX_ROUTE_KANDIDATEN = 3

# Kleur van de leiderstrui, voor de knoppen bovenin de pop-up.
#
# Dit is een vaste lijst, geen bron: geen enkele bron geeft de kleur van een
# trui nergens terug. Er staan daarom alleen koersen in waarvan de truikleur
# buiten kijf staat. Een koers die er niet in staat krijgt geen kleur en
# houdt de gewone accentkleur van de kaart — liever geen kleur dan een
# verzonnen kleur. Eendaagse koersen hebben geen klassement en horen hier
# dus niet thuis. Sleutel: de cyclingstage-slug van de koers.
LEIDERSTRUI = {
    "tour-de-france": "#F3C700",          # geel
    "tour-de-france-femmes": "#F3C700",   # geel
    "giro": "#E6007E",                    # roze
    "giro-women": "#E6007E",              # roze
    "vuelta": "#D0021B",                  # rood
    "vuelta-femenina": "#D0021B",         # rood
    "paris-nice": "#F3C700",              # geel
    "tirreno-adriatico": "#0E5FA8",       # blauw
    "criterium-du-dauphine": "#F3C700",   # geel
    "tour-de-suisse": "#F3C700",          # geel
    "tour-de-romandie": "#F3C700",        # geel
    "tour-down-under": "#C8862B",         # oker
    "uae-tour": "#D0021B",                # rood
}

# De ranglijst waarop de startlijst wordt gesorteerd, per geslacht.
#
MONUMENTS = {
    "milano-sanremo",
    "ronde-van-vlaanderen",
    "paris-roubaix",
    "liege-bastogne-liege",
    "il-lombardia",
}

PROFILE_MAP = {
    "p1": ("Vlak", 1),
    "p2": ("Heuvelachtig, vlakke finish", 2),
    "p3": ("Heuvelachtig, finish bergop", 2),
    "p4": ("Bergen, vlakke finish", 3),
    "p5": ("Bergen, finish bergop", 3),
}

MONTHS_NL = ["", "jan", "feb", "mrt", "apr", "mei", "jun",
             "jul", "aug", "sep", "okt", "nov", "dec"]
DAYS_NL = ["ma", "di", "wo", "do", "vr", "za", "zo"]


def _type_tag(stage_type):
    """TT (individuele tijdrit) / TTT (ploegentijdrit) uit het PCS-type; anders ''."""
    s = (stage_type or "").upper()
    if "TTT" in s or ("TEAM" in s and "TIME TRIAL" in s):
        return "TTT"
    if "ITT" in s or "TIME TRIAL" in s or s == "TT":
        return "TT"
    return ""


def _finish_est(start_time, distance, sc, vm, stage_type):
    """Grove schatting finishtijd 'HH:MM' (start + afstand/gem. snelheid). Niet bij tijdritten."""
    if _type_tag(stage_type):          # tijdrit: verspreide starts, geen zinnige finish
        return ""
    m = re.match(r"(\d{1,2}):(\d{2})", (start_time or "").strip())
    dist = _num(distance)
    if not m or not dist:
        return ""
    sc = _num(sc) or 0
    vm = _num(vm) or 0
    speed = 36.0 if (sc >= 150 or vm >= 3000) else 42.0 if sc >= 50 else 44.0
    total = (int(m.group(1)) * 60 + int(m.group(2)) + round(dist / speed * 60)) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"

def _watchability(sc, dist, climbs, stage_type, vm=None):
    """Grove kijkscore 1-10 (heuristiek, GEEN officiele score).

    Gebaseerd op het finishtype, de cols en de hoogtemeters. Geeft None terug
    als geen van die dingen bekend is; dan is elke score een slag in de lucht.
    """
    sc = _num(sc) or 0
    vm = _num(vm) or 0
    dist = _num(dist) or 999
    climbs = climbs or []
    tt = _type_tag(stage_type)
    if not climbs and not sc and not vm and not tt:
        return None                     # niets bekend -> geen score
    k2f = [_num(c.get("km_to_finish")) for c in climbs
           if _num(c.get("km_to_finish")) is not None]
    last = min(k2f) if k2f else 999
    rank = {"HC": 4, "1": 3, "2": 2, "3": 1, "4": 0}
    top_cat = max((rank.get(str(c.get("category") or "").upper(), 0) for c in climbs),
                  default=0)
    zwaar = sc >= 180 or vm >= 3000      # hoogtemeters als sc ontbreekt
    heuvel = sc >= 60 or vm >= 1500
    # finalecircuit: dezelfde klim meermaals in de slotfase (bv. Montmartre 3x)
    fin = [c for c in climbs if (_num(c.get("km_to_finish")) or 999) <= 60]
    sleutels = [(c.get("name") or "").strip().lower()
                or f"{c.get('length_km')}@{c.get('steepness_pct')}" for c in fin]
    ronden = max((sleutels.count(k) for k in set(sleutels)), default=1)
    if last <= 2:
        w = 7 + (1 if top_cat >= 3 else 0) + (1 if (sc >= 250 or vm >= 3500) else 0)
    elif last <= 15:
        w = 6 + (1 if (sc >= 200 or vm >= 3000) else 0)
    elif last <= 30:
        w = 5 + (1 if top_cat >= 3 else 0)
    elif tt == "TT":
        w = 5
    elif tt == "TTT":
        w = 4
    elif zwaar:
        w = 5 + (1 if len(climbs) >= 5 else 0)
    elif heuvel and dist <= 170:
        w = 5
    elif heuvel:
        w = 4
    else:
        w = 3
    if ronden >= 2:                     # circuitfinale: gegarandeerd strijd
        w = max(w, 6) + (2 if ronden >= 3 else 1)
    return max(1, min(10, int(round(w))))


def _fmt_nl(d: date) -> str:
    return f"{d.day} {MONTHS_NL[d.month]}"


def _race_slug(url_of_slug: str) -> str:
    """De cyclingstage-slug van een koers.

    Neemt zowel een kale slug ("vuelta") als een cyclingstage-adres aan, zodat
    aanroepers die alleen een adres bij de hand hebben niets hoeven te weten.
    """
    from . import cyclingstage as cs

    tekst = url_of_slug or ""
    if "/" not in tekst:
        return tekst
    m = re.search(r"/(\d{4})[-/]", tekst) or re.search(r"-(\d{4})\b", tekst)
    return cs.slug_van(tekst, int(m.group(1)) if m else 0)


def _leiderstrui(race_url: str) -> str:
    """Kleur van de leiderstrui van een koers, of '' als die niet vaststaat."""
    return LEIDERSTRUI.get(_race_slug(race_url or ""), "")


def _lees_niveaus(waarde) -> list[str]:
    """Opgeslagen niveaus -> lijst met bekende nummers, zonder dubbelen.

    Home Assistant slaat een keuzelijst als lijst op, maar een oude of met
    de hand bewerkte opslag kan er tekst van maken; onbekende nummers gaan
    eruit, want die leveren toch niets op.
    """
    if not isinstance(waarde, (list, tuple, set)):
        waarde = re.split(r"[,;\s]+", str(waarde or ""))
    uit = []
    for deel in waarde:
        niveau = str(deel).strip()
        # opslag van vóór 0.19 bevat de circuitnummers van procyclingstats;
        # zonder deze vertaling valt een bestaande installatie stil terug op
        # de standaard en lijkt zijn keuze zomaar verdwenen
        niveau = OUDE_NIVEAUS.get(niveau, niveau)
        if niveau in NIVEAUS and niveau not in uit:
            uit.append(niveau)
    return uit


def _noemt_dames(naam):
    """Bevat de koersnaam zelf al een aanduiding dat het de vrouwenkoers is?"""
    return bool(re.search(
        r"\b(we|femmes|f[e\u00e9]minin\w*|femenina|feminas?|women|women's|donne|"
        r"ladies|dames)\b", (naam or "").lower()))


def _short_race(name: str, n: int = 20) -> str:
    name = (name or "").strip()
    return name if len(name) <= n else name[: n - 1] + "…"


def _num(x):
    """PCS-waarde (soms tekst als '172', '19,9', '-') -> float of None."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip().replace(",", ".").split()[0])
    except (ValueError, IndexError):
        return None


def _int(x):
    v = _num(x)
    return int(round(v)) if v is not None else None


def _parse_start_hhmm(start_time: str | None):
    """'17:00 (17:00 CET)' -> (17, 0). None als onbekend."""
    if not start_time:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})", start_time)
    return (int(m.group(1)), int(m.group(2))) if m else None


# ──────────────────────────────────────────────────────────────
# Blocking scrape-functies — draaien via async_add_executor_job
# ──────────────────────────────────────────────────────────────

# De laatste kalenderfout, om herhaling te dempen. Een blokkade bij de bron
# kan weken duren; vier waarschuwingen per ronde, elke 30 minuten, maken het
# logboek dan onbruikbaar voor al het andere. De eerste keer is nieuws, de
# tweeënnegentigste niet.
_LAATSTE_KALENDERFOUT = ""


def _haal_html(url: str, wat: str = "pagina") -> str:
    """Een pagina van cyclingstage ophalen; "" als het niet lukt.

    Alle cyclingstage-verzoeken lopen hierlangs, zodat er één plek is waar
    de user-agent en de tijdslimiet staan. Blokkkeerd worden we hier niet:
    deze bron doet gewoon open (bewezen — de GPX-profielen kwamen al binnen
    toen procyclingstats er allang uit lag).
    """
    import urllib.request
    if not url:
        return ""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("%s ophalen mislukt (%s): %s", wat.capitalize(), url, err)
        return ""


def _fetch_calendar(year: int, niveaus: list[str]) -> tuple[list[dict], dict, list]:
    """Kalender van cyclingstage, gefilterd op de gekozen niveaus.

    Eén pagina voor het hele jaar, met per koers het adres erbij. Dat adres
    is de reden dat de slug-tabellen weg konden: hij komt nu uit de bron in
    plaats van uit een lijst die iemand had ingevuld.

    Geeft `(koersen, telling, fouten)` terug; de telling is het aantal
    koersen per niveau en gaat als `levels_diag` naar de attributen.

    Wat cyclingstage dekt is een redactionele keuze — "the races we are
    passionate about" staat er boven de tabel. Voor de mannen is dat
    vrijwel de hele WorldTour, bij de vrouwen ontbreken de rondes van een
    week. Wat er niet in staat heeft ook geen profiel en geen tijdschema.
    """
    from . import cyclingstage as cs

    global _LAATSTE_KALENDERFOUT

    url = cs.KALENDER_URL.format(y=year)
    html = _haal_html(url, "kalender")
    if not html:
        melding = f"kalenderpagina {url} kwam niet binnen"
        nieuw = melding != _LAATSTE_KALENDERFOUT
        (_LOGGER.warning if nieuw else _LOGGER.debug)("Kalender: %s", melding)
        _LAATSTE_KALENDERFOUT = melding
        return [], {}, [melding]

    alles = cs.parse_kalender(html, year)
    gekozen = [n for n in (niveaus or []) if n in NIVEAUS]
    wil_vrouwen = {NIVEAUS[n]["vrouwen"] for n in gekozen}

    koersen, telling = [], {}
    for n in gekozen:
        telling[NIVEAUS[n]["naam"]] = 0
    for k in alles:
        if k["women"] not in wil_vrouwen:
            continue
        slug = cs.slug_van(k["route_url"] or k["url"], year)
        if not slug:
            _LOGGER.debug("Koers zonder bruikbaar adres overgeslagen: %s", k["name"])
            continue
        niveau = "v" if k["women"] else "m"
        koersen.append({
            "name": k["name"],
            # de routepagina is waar de etappelijst vandaan komt; de slug
            # bedient de GPX, het tijdschema en de overzichtspagina
            "url": k["route_url"] or k["url"],
            "slug": slug,
            "start": k["start"],
            "end": k["end"],
            "women": k["women"],
            "level": niveau,
            "bron": bronnen.STANDAARD,
        })
        if NIVEAUS[niveau]["naam"] in telling:
            telling[NIVEAUS[niveau]["naam"]] += 1

    # Koersen die cyclingstage niet noemt en die met de hand zijn toegevoegd
    # (zie EXTRA_KOERSEN in bronnen.py). Ze tellen mee in de diagnose, zodat
    # `levels_diag` blijft kloppen met wat er werkelijk in beeld komt.
    for k in bronnen.extra_koersen(year, gekozen):
        koersen.append(k)
        naam = NIVEAUS.get(str(k.get("level", "")), {}).get("naam")
        if naam in telling:
            telling[naam] += 1

    koersen.sort(key=lambda x: (x["start"], x["women"]))
    if koersen:
        _LAATSTE_KALENDERFOUT = ""
    else:
        _LOGGER.warning("Kalender %s: geen koersen voor de gekozen niveaus (%s)",
                        year, ", ".join(gekozen) or "geen")
    _LOGGER.debug("Kalender %s: %s koersen (%s)", year, len(koersen),
                  ", ".join(f"{n}: {a}" for n, a in telling.items()))
    return koersen, telling, []


def _cs_event_stages(event: dict) -> list[dict]:
    """Etappes van een koers met datum. Eendaagse koers = 1 'etappe'.

    De routepagina van cyclingstage geeft nummer, datum, start en finish,
    afstand, terreintype én het adres van elke etappe. Dat scheelt niet
    alleen raden: afstand en terrein zijn er meteen, dus daar hoeft later
    geen apart verzoek meer voor.

    Welke pagina de etappelijst draagt verschilt per koers — bij de Vuelta
    is dat `/vuelta-2026-route/`, bij de Tour Down Under
    `/tour-down-under-2026/`. Beide kandidaten worden geprobeerd en de
    eerste die een tabel oplevert wint; dat is nakijken in plaats van raden.
    """
    from . import cyclingstage as cs

    race_url = event["url"]
    jaar = event["start"].year
    slug = event.get("slug") or cs.slug_van(race_url, jaar)

    if event["start"] == event["end"]:
        # eendaagse koers: de routepagina is meteen de etappepagina
        return [{
            "date": event["start"], "stage_url": race_url,
            "profile_icon": "", "name": event["name"], "idx": None,
            "one_day": True, "race_url": race_url, "race_name": event["name"],
            "race_slug": slug, "women": bool(event.get("women")),
            "level": str(event.get("level", "")),
            "distance_km": None, "stage_type": "",
            "departure": "", "arrival": "",
        }]

    laatste_html = ""
    for kandidaat in _etappelijst_urls(race_url):
        laatste_html = _haal_html(kandidaat, "routepagina")
        rijen = cs.parse_etappes(laatste_html, jaar)
        if rijen:
            break
    else:
        # De kalender laat de routekolom voor een aantal koersen leeg (Tour
        # of Britain, het WK, Lombardije, Parijs-Tours) en wijst dan naar de
        # koerspagina. De etappetabel staat een niveau dieper, op een adres
        # dat niet af te leiden is (`route-gb-2026` tegenover
        # `route-tdu-2026`) maar waar die koerspagina zelf naar linkt.
        rijen = []
        for kandidaat in cs.route_kandidaten(laatste_html,
                                             race_url)[:MAX_ROUTE_KANDIDATEN]:
            rijen = cs.parse_etappes(_haal_html(kandidaat, "routepagina"), jaar)
            if rijen:
                _LOGGER.debug("Etappelijst van %s gevonden op %s",
                              race_url, kandidaat)
                break
        if not rijen:
            _LOGGER.debug("Geen etappelijst gevonden voor %s", race_url)
            return []

    return [{
        "date": r["date"],
        "stage_url": r["url"] or race_url,
        "profile_icon": "",
        "name": r["name"],
        "idx": r["idx"],
        "one_day": False,
        "race_url": race_url,
        "race_name": event["name"],
        "race_slug": slug,
        "women": bool(event.get("women")),
        "level": str(event.get("level", "")),
        # uit de etappelijst, dus zonder extra verzoek
        "distance_km": r["distance_km"],
        "stage_type": r["stage_type"],
        "departure": r["departure"],
        "arrival": r["arrival"],
    } for r in rijen]


def _etappelijst_urls(race_url: str) -> list[str]:
    """Waar de etappetabel van een koers kan staan.

    De kalender wijst naar de routepagina (`/vuelta-2026-route/spain-route-2026/`),
    maar de etappetabel staat een niveau hoger (`/vuelta-2026-route/`) —
    nagekeken op de opgeslagen Vuelta-pagina. Vandaar de bovenliggende
    pagina eerst, met de routepagina zelf als terugval voor koersen waar het
    andersom ligt. Wie een tabel oplevert heeft gelijk; dat is nakijken en
    geen aanname.
    """
    if not race_url:
        return []
    kaal = race_url.rstrip("/")
    ouder = kaal.rsplit("/", 1)[0]
    uit = []
    if ouder.count("/") > 2:            # niet tot voorbij het domein
        uit.append(ouder + "/")
    uit.append(kaal + "/")
    return uit


# Hier stond tot 0.25 alles wat via procyclingstats liep: het Stage-object,
# de startlijst en de individuele ranglijst die hem ordende, de officiële
# ploegcodes, de dagwinst (uit de kolom "Prev") en het naamherstel dat de
# verschuivende namenkolom van PCS rechttrok.
#
# Die bron is sinds 23 augustus 2026 onbereikbaar — een Cloudflare-uitdaging
# die geen enkele HTTP-client passeert, zie CLAUDE.md. Elk van die functies
# ving zijn eigen fouten af, dus er kwam niets in het log; het waren alleen
# verzoeken die elke ronde op een 403 stuklopen. Cyclingstage heeft geen
# vervanger voor deze gegevens: geen startlijst, geen ploegcode (alleen een
# landcode) en geen vorige stand per rij.
#
# De attribuutsleutels blijven bestaan en blijven leeg, zodat een kaart van
# vóór deze versie er niet over struikelt. Wie het terug wil zoekt in de
# geschiedenis: `git log -S "_fetch_startlist" -- custom_components`.

# De etappe-uitslagadressen per koers, gelezen van de resultatenpagina van
# die koers. Module-breed en niet op de coordinator: `_cs_fetch_stage` volgt
# het contract van een bron (`bronnen.py`) en krijgt alleen de etappe mee.
# Per dag geleegd, want een overzicht dat vandaag nog leeg was kan er morgen
# staan. `{}` in de cache betekent "vandaag al geprobeerd, niets gevonden" —
# zonder dat zou elke etappe van zo'n koers elke ronde de pagina opnieuw
# ophalen.
_UITSLAGINDEX: dict[str, dict] = {}
_UITSLAGINDEX_DAG = None


def _uitslagindex(slug: str, jaar: int) -> dict:
    """`{etappenummer: adres}` van een koers, hoogstens één verzoek per dag."""
    global _UITSLAGINDEX_DAG

    from . import cyclingstage as cs

    vandaag = date.today()
    if _UITSLAGINDEX_DAG != vandaag:
        _UITSLAGINDEX.clear()
        _UITSLAGINDEX_DAG = vandaag
    sleutel = f"{slug}-{jaar}"
    if sleutel not in _UITSLAGINDEX:
        url = cs.uitslag_index_url(slug, jaar)
        _UITSLAGINDEX[sleutel] = cs.parse_uitslag_index(
            _haal_html(url, "uitslagoverzicht"), slug, jaar) if url else {}
    return _UITSLAGINDEX[sleutel]


def _uitslagpagina(stage: dict) -> tuple:
    """`(adres, html)` van de uitslag van een etappe; `("", "")` als er niets is.

    Twee wegen, in deze volgorde:

    1. **Afleiden uit het etappeadres** (`uitslag_url`). Nagekeken op de
       Vuelta en verder gratis: geen extra verzoek om het adres te vinden.
    2. **Opzoeken op de resultatenpagina van de koers.** Die afleiding is
       alleen op de grote rondes nagekeken; daar heet de koersmap
       `{slug}-{jaar}-route`, bij de andere koersen heet hij anders. Levert
       de afleiding niets op, dan wordt het echte adres opgezocht — één
       verzoek per koers per dag, gedeeld door al zijn etappes.

    Voor een **eendaagse** koers bestaat weg 1 niet: er is geen etappenummer
    en dus geen `stage-N`-adres. Zijn uitslag staat op de resultatenpagina
    van de koers zelf, en die wordt hier direct gelezen.
    """
    from . import cyclingstage as cs

    slug = stage.get("race_slug") or ""
    jaar = stage["date"].year if stage.get("date") else 0

    if stage.get("one_day"):
        url = cs.uitslag_index_url(slug, jaar)
        return (url, _haal_html(url, "uitslag")) if url else ("", "")

    url = cs.uitslag_url(stage.get("stage_url") or "")
    if url:
        html = _haal_html(url, "uitslag")
        if html:
            return url, html

    idx = stage.get("idx")
    if not idx or not slug or not jaar:
        return "", ""
    url = _uitslagindex(slug, jaar).get(int(idx), "")
    if not url:
        return "", ""
    _LOGGER.debug("Uitslagadres van etappe %s (%s) via het overzicht: %s",
                  idx, slug, url)
    return url, _haal_html(url, "uitslag")


def _cs_fetch_stage(stage: dict, result_n: int = DEFAULT_RESULT_N,
                 gc_n: int = DEFAULT_GC_N) -> dict:
    """Uitslag en klassementen van één etappe, van cyclingstage.

    Cyclingstage zet de uitslag als kop met een alinea eronder, niet in een
    tabel; `parse_uitslag` leest dat. Wat er niet staat blijft leeg:

    - **geen ploeg.** Er is alleen een landcode, en een land is geen ploeg.
      Die gaat als `country` mee; `team` en `team_code` blijven weg en de
      kaart laat de haakjes dan weg.
    - **geen punten-, berg- en jongerenklassement.** Op 23 augustus 2026
      hebben de eigen klassementspagina's alleen de puntenverdeling, met de
      mededeling dat de standen "in a table during La Vuelta" komen. De
      herkenning staat klaar in `parse_uitslag`, dus zodra ze verschijnen
      lopen ze mee.
    - **geen dagwinst.** Die werd berekend uit de "Prev"-kolom bij
      procyclingstats; cyclingstage geeft geen vorige stand per rij.
    """
    from . import cyclingstage as cs

    data = _lege_uitslag(stage)
    url, html = _uitslagpagina(stage)
    if not html:
        return data
    uit = cs.parse_uitslag(html)
    data["ok"] = True
    data["results"] = uit["results"][:result_n]
    data["gc"] = uit["gc"][:gc_n]
    data["points_top"] = uit["points"][:gc_n]
    data["kom_top"] = uit["kom"][:gc_n]
    data["youth_top"] = uit["youth"][:gc_n]
    for sleutel, top in (("points_leader", "points_top"),
                         ("kom_leader", "kom_top"),
                         ("youth_leader", "youth_top")):
        if data[top]:
            data[sleutel] = data[top][0].get("rider", "")
    # gereden is: er staat een uitslag. Een pagina die er wel is maar nog
    # geen uitslag heeft, telt niet als afgelopen etappe.
    data["finished"] = bool(data["results"])
    _LOGGER.debug("Uitslag %s: %s rijen, gc %s", url,
                  len(data["results"]), len(data["gc"]))
    return data


# ── Bronnen ───────────────────────────────────────────────────────────
#
# Cyclingstage bedient alles wat in zijn kalender staat. Een koers die
# elders vandaan komt draagt `bron`, en dan gaat de vraag naar dat platform.
# Zie `bronnen.py` voor wat een bron moet kunnen en hoe je er een toevoegt.
bronnen.registreer(bronnen.Bron(
    naam="cyclingstage",
    etappes=_cs_event_stages,
    uitslag=_cs_fetch_stage,
))


def _event_stages(event: dict) -> list[dict]:
    """De etappelijst van een koers, bij de bron die hem bedient."""
    bron = bronnen.bron_van(event)
    if bron is None:
        return []
    try:
        etappes = bron.etappes(event)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Etappelijst mislukt bij %s voor %s: %s",
                      bron.naam, event.get("name"), err)
        return []
    # elke etappe onthoudt waar hij vandaan komt, zodat `_fetch_stage` later
    # niet hoeft te raden welke bron de uitslag heeft
    for e in etappes:
        e.setdefault("bron", bron.naam)
    return etappes


def _fetch_stage(stage: dict, result_n: int = DEFAULT_RESULT_N,
                 gc_n: int = DEFAULT_GC_N) -> dict:
    """Uitslag en klassementen van één etappe, bij de bron van die etappe."""
    bron = bronnen.bron_van(stage)
    if bron is None:
        return _lege_uitslag(stage)
    try:
        return bron.uitslag(stage, result_n, gc_n)
    except Exception as err:  # noqa: BLE001
        # Een organisatorsite die eruit ligt mag de rest niet meenemen; de
        # aanroepers rekenen op een dict en niet op een uitzondering.
        _LOGGER.debug("Uitslag mislukt bij %s voor %s: %s",
                      bron.naam, stage.get("stage_url"), err)
        return _lege_uitslag(stage)


def _lege_uitslag(stage: dict) -> dict:
    """Wat een bron teruggeeft als er niets te halen viel."""
    return {
        "ok": False, "finished": False,
        "departure": stage.get("departure") or "",
        "arrival": stage.get("arrival") or "",
        "distance": stage.get("distance_km"), "vertical": None,
        "profile_icon": "", "profile_score": None,
        "stage_type": stage.get("stage_type") or "",
        "start_time": "", "climbs_raw": [],
        "results": [], "gc": [], "points_leader": "", "kom_leader": "",
        "youth_leader": "", "points_top": [], "kom_top": [], "youth_top": [],
        "startlist_quality": None,
    }


def _show_state_for(sd: date, today: date) -> str:
    if sd == today:
        return "Vandaag"
    if sd == today + timedelta(days=1):
        return "Morgen"
    return f"{DAYS_NL[sd.weekday()]} {_fmt_nl(sd)}"


def _fetch_stage_meta(stage: dict) -> dict:
    """Wat er over een etappe bekend is, uit de etappelijst plus zijn pagina.

    Afstand, terreintype, vertrek en aankomst staan al in de etappelijst en
    kosten dus niets. Alleen de starttijd, de verwachte finishtijd en de
    hoogtemeters staan op de etappepagina zelf.

    `profile_score` bestaat bij cyclingstage niet en blijft leeg; de
    watchscore leunt dan op afstand, hoogtemeters, terreintype en de cols
    uit de GPX. Niets schatten waar de bron zwijgt.
    """
    from . import cyclingstage as cs

    d = {
        "ok": False,
        "departure": stage.get("departure") or "",
        "arrival": stage.get("arrival") or "",
        "distance": stage.get("distance_km"),
        "vertical": None,
        "profile_score": None,
        "stage_type": stage.get("stage_type") or "",
        "start_time": "",
    }
    html = _haal_html(stage.get("stage_url"), "etappepagina")
    if not html:
        return d
    d["ok"] = True
    meta = cs.parse_etappe_meta(html)
    d["start_time"] = meta.get("start_time", "")
    d["finish_time"] = meta.get("finish_time", "")
    if meta.get("vertical_m") is not None:
        d["vertical"] = meta["vertical_m"]
    return d


WIELERFLITS_TV_URL = "https://www.wielerflits.nl/nieuws/wielrennen-op-tv/"


def _slug_norm(s):
    s = (s or "").lower()
    for a, b in (("\u00e0", "a"), ("\u00e1", "a"), ("\u00e2", "a"), ("\u00e4", "a"),
                 ("\u00e9", "e"), ("\u00e8", "e"), ("\u00ea", "e"), ("\u00eb", "e"),
                 ("\u00ed", "i"), ("\u00ef", "i"), ("\u00f3", "o"), ("\u00f6", "o"),
                 ("\u00fa", "u"), ("\u00fc", "u"), ("\u00e7", "c"), ("\u00f1", "n")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s)


def _logo_url(u):
    """Directe plaatje-URL uit de beeldbewerker-link (.../_next/image?url=...)."""
    u = (u or "").replace("&amp;", "&").strip()
    m = re.search(r"[?&]url=([^&]+)", u)
    if m:
        from urllib.parse import unquote
        inner = unquote(m.group(1))
        if inner.startswith("http"):
            return inner
    return u


def _parse_channels(html, pcs_slug, year, idx, race_name):
    """NL-tv-zenders (naam, tijd, logo) voor een koers/etappe uit de tv-gids-HTML."""
    html = re.sub(r'<img[^>]*NL\.svg[^>]*>', ' ##NL## ', html, flags=re.I)
    html = re.sub(r'<img[^>]*BE\.svg[^>]*>', ' ##BE## ', html, flags=re.I)
    html = re.sub(r'<img[^>]*src="([^"]*_next/image[^"]*)"[^>]*>',
                  lambda m: f' ##LOGO|{m.group(1)}## ', html, flags=re.I)
    html = re.sub(r'<a[^>]*wielerkalender/([^/"\']+)/etappes/(\d+)/[^>]*>([^<]+)</a>',
                  lambda m: f' ##RACE|{m.group(1)}|{m.group(2)}|{m.group(3).strip()}## ',
                  html, flags=re.I)
    text = re.sub(r'[ \t\r\n\u00a0]+', ' ', re.sub(r'<[^>]+>', ' ', html))
    want_stage = str(idx) if idx else "1"
    rn = _slug_norm(race_name)
    for part in re.split(r'##RACE\|', text)[1:]:
        head, _, body = part.partition('##')
        f = head.split('|')
        if len(f) < 3 or f[1] != want_stage:
            continue
        wf_slug, wf_name = f[0], _slug_norm(f[2])
        if not (wf_slug.startswith(pcs_slug + "-") or wf_name == rn
                or (rn and (rn in wf_name or wf_name in rn))):
            continue
        seen, out = set(), []
        for m in re.finditer(
                r'(\d{1,2}:\d{2})\s*(?:##LOGO\|([^#]*)##)?\s*'
                r'([A-Za-z][^#]*?)\s*((?:##(?:NL|BE)##\s*)+)', body):
            tm, logo, name = m.group(1), (m.group(2) or "").strip(), m.group(3).strip()
            if "##NL##" in m.group(4) and name.lower() not in seen:
                seen.add(name.lower())
                out.append({"name": name, "time": tm, "logo": _logo_url(logo)})
        return out
    return []


def _fetch_tv_html():
    """De tv-gids van wielerflits, of '' als het niet lukt.

    Los van het uitlezen, want op de pagina staan álle koersen van de dag:
    één verzoek volstaat voor de koers op de tegel én die in de pop-up.
    """
    import urllib.request
    try:
        req = urllib.request.Request(
            WIELERFLITS_TV_URL,
            headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("TV-gids ophalen mislukt: %s", err)
        return ""


def _channels_from(html, race_url, idx, race_name):
    """NL-tv-zenders van één etappe uit de al opgehaalde tv-gids."""
    m = re.match(r"race/([^/]+)/(\d{4})", race_url or "")
    if not html or not m:
        return []
    ch = _parse_channels(html, m.group(1), m.group(2), idx, race_name or "")
    _LOGGER.debug("TV-zenders %s e%s: %s", m.group(1), idx, ch)
    return ch


_CLIMB_KW = (r"(?:Grand |Petit |Haut[e]? |Mont )?(?:Col|Côte|Cote|Mur|Ballon|"
             r"Cormet|Montée|Montee|Alpe|Puy|Port|Puerto|Colle|Passo|Cima|"
             r"Monte|Alto|Collada|Hourquette|Croix|Cabane)\b")
_CLIMB_NAME = _CLIMB_KW + (r"(?:(?:[ ]d['’]| du | de la | de l['’]| des | de "
                           r"| di | della | del )[A-ZÀ-Ü][\w'’à-ÿ\-]+"
                           r"(?:[ -][A-ZÀ-Ü][\w'’à-ÿ\-]+){0,2})?")
_BARE_CLIMB = {"col", "côte", "cote", "mur", "ballon", "cormet", "montée", "montee",
               "alpe", "puy", "port", "puerto", "colle", "passo", "cima", "monte",
               "alto", "collada", "hourquette", "croix", "cabane"}


def _fetch_stage_names(url, distance=None):
    """Uit de cyclingstage-etappetekst: cols (naam/lengte/%/km-tot-finish) + start/finish.

    Geeft terug: (climbs, route) met route = {"departure":.., "arrival":..} of {}.
    """
    if not url:
        return [], {}
    import urllib.request
    from html import unescape
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = resp.read().decode("utf-8", "replace")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Etappetekst ophalen mislukt %s: %s", url, err)
        return [], {}
    # Start/finish uit <title> "... stage N: Vertrek - Aankomst" (spaties rond koppelteken
    # vereist, zodat plaatsnamen als Orcières-Merlette heel blijven)
    route = {}
    tt = re.search(r"<title>(.*?)</title>", doc, re.S | re.I)
    if tt:
        tm = re.search(r"stage\s+\d+:\s*(.+?)\s+[-–]\s+(.+?)\s*$",
                       unescape(tt.group(1)).strip())
        if tm:
            route = {"departure": tm.group(1).strip(), "arrival": tm.group(2).strip()}
    # HTML opschonen: script/style weg, tags strippen, entities decoderen, witruimte pletten
    doc = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", doc, flags=re.S | re.I)
    text = unescape(re.sub(r"<[^>]+>", " ", doc)).replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"[ \t\r\n\u00a0]+", " ", text)
    fin = re.search(r"expected to finish around\s+(\d{1,2}:\d{2})", text, re.I)
    if fin:
        route["finish_time"] = fin.group(1)
    raw = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)[\s\-–]*kilometre", text):
        pm = re.search(r"(\d+(?:\.\d+)?)\s*%", text[m.end():m.end() + 55])
        if not pm:                       # geen % vlakbij -> geen klim
            continue
        if "." in text[m.end():m.end() + pm.start()]:   # punt tussen km en % = positiezin
            continue
        head = text[max(0, m.start() - 130):m.start()]
        names = list(re.finditer(_CLIMB_NAME, head))
        if not names:
            continue
        nm = names[-1]
        name = nm.group(0).strip(" ,.")
        if name.lower() in _BARE_CLIMB:  # los kernwoord ("Col") = parser-ruis -> overslaan
            continue
        raw.append({"name": name,
                    "length_km": float(m.group(1)),
                    "steepness_pct": float(pm.group(1)),
                    "_km_end": m.end(),
                    "_name_start": max(0, m.start() - 130) + nm.start()})
    # km-tot-finish: eerst "still X kilometres ...", anders "X kilometres into the stage",
    # telkens begrensd tot vóór de volgende colnaam
    for idx, c in enumerate(raw):
        bound = raw[idx + 1]["_name_start"] if idx + 1 < len(raw) else len(text)
        seg = text[c["_km_end"]:bound]
        fm = re.search(r"still\s+(\d+(?:\.\d+)?)\s*kilometres", seg)
        fin = re.search(r"(\d+(?:\.\d+)?)\s*kilometres?\s+(?:from|to)\s+the\s+finish", seg)
        if fm:
            c["km_to_finish"] = float(fm.group(1))
        elif fin:
            c["km_to_finish"] = float(fin.group(1))
        elif distance:
            im = re.search(r"(\d+(?:\.\d+)?)\s*kilometres?\s+into the (?:stage|race)", seg)
            c["km_to_finish"] = (distance - float(im.group(1))) if im else None
        else:
            c["km_to_finish"] = None
    seen, res = set(), []
    for c in raw:
        k = c["name"].lower()
        if k not in seen:
            seen.add(k)
            res.append({kk: c[kk] for kk in
                        ("name", "length_km", "steepness_pct", "km_to_finish")})
    _LOGGER.debug("Etappetekst %s: %d colnamen, route=%s", url, len(res), bool(route))
    return res, route


def _name_summit(climbs, arrival):
    """Slotklim (aankomst bergop) de aankomstplaats geven als hij nog geen naam heeft."""
    if not climbs or not arrival:
        return
    last = min(climbs, key=lambda c: c["km_to_finish"]
               if c.get("km_to_finish") is not None else 1e9)
    k = last.get("km_to_finish")
    if k is not None and k <= 3 and not last.get("name"):
        last["name"] = arrival


# _fetch_live is weg. Het bouwde `procyclingstats.com/{stage_url}/live` en
# las daar "KM to go" uit. Sinds 0.19 is `stage_url` een cyclingstage-adres,
# dus dat werd letterlijk
# `procyclingstats.com/https://www.cyclingstage.com/...//live` — een verzoek
# dat nergens op sloeg en elke vijf minuten opnieuw ging tijdens een etappe.
# En zelfs met het juiste adres komt er niets terug: procyclingstats zit
# achter een Cloudflare-uitdagingspagina (zie "Bronnen" in CLAUDE.md).
#
# Cyclingstage heeft geen vervanger: het woord "live" komt op de etappepagina
# nul keer voor. De positie schatten uit starttijd en afstand zou precies het
# verzinnen zijn dat dit project niet doet, dus `live_km_to_go` blijft leeg en
# de kaart tekent de stip niet. Komt er ooit een bron met een échte km-to-go,
# dan is dit de plek.


def _match_names(detected, parsed, tol_len=2.5, tol_pct=2.2):
    """Namen op gedetecteerde cols: eerst positie (km-tot-finish), dan (lengte, steilheid)."""
    used_d, done_p = set(), set()
    # pass 1: waar de tekst km-tot-finish geeft -> harde positie-match (±8 km)
    for i, p in enumerate(parsed):
        pk = p.get("km_to_finish")
        if pk is None:
            continue
        best, bestd = None, None
        for j, d in enumerate(detected):
            if j in used_d:
                continue
            dk = d.get("km_to_finish")
            if dk is None or abs(dk - pk) > 8:
                continue
            dist = (abs((d.get("length_km") or 0) - (p.get("length_km") or 0))
                    + 1.5 * abs((d.get("steepness_pct") or 0) - (p.get("steepness_pct") or 0)))
            if bestd is None or dist < bestd:
                bestd, best = dist, j
        if best is not None and p.get("name"):
            detected[best]["name"] = p["name"]
            used_d.add(best)
            done_p.add(i)
    # pass 2: rest -> globale best-eerst op (lengte, steilheid) binnen drempels
    pairs = []
    for i, p in enumerate(parsed):
        if i in done_p:
            continue
        for j, d in enumerate(detected):
            if j in used_d:
                continue
            dl = abs((d.get("length_km") or 0) - (p.get("length_km") or 0))
            dp = abs((d.get("steepness_pct") or 0) - (p.get("steepness_pct") or 0))
            if dl <= tol_len and dp <= tol_pct:
                pairs.append((dl + 1.5 * dp, i, j))
    pairs.sort(key=lambda x: x[0])
    used_p = set()
    for _d, i, j in pairs:
        if i in used_p or j in used_d:
            continue
        if parsed[i].get("name"):
            detected[j]["name"] = parsed[i]["name"]
            used_p.add(i)
            used_d.add(j)




# ──────────────────────────────────────────────────────────────
# GPX-hoogteprofiel (bron: cyclingstage.com, gratis per etappe)
# ──────────────────────────────────────────────────────────────

# PCS-slug -> cyclingstage CDN-slug (grote rondes; rest valt terug op klim-schema)
# Handmatige routebestanden. Vind je ergens zelf een GPX (velowire, la-flamme-rouge,
# een koerssite), zet het adres hier neer - deze gaan vóór op de automatische adressen.
# Sleutel: "<pcs-slug>/<jaar>" voor eendaagse koersen,
#          "<pcs-slug>/<jaar>/<etappenummer>" voor een etappe.
# Voorbeeld:
#   "san-sebastian/2026": "https://voorbeeld.nl/klasikoa-2026.gpx",
GPX_OVERRIDE = {
}


# De drie grote rondes. Ze duren drie weken en zijn in die periode de koers
# waar het om gaat; een tegel die tijdens de Vuelta de Renewi Tour laat zien
# klopt niet, ook al heeft die toevallig wél een hoogteprofiel. Een vaste
# lijst van drie koersen en geen weging of score - er valt niets aan te
# schatten. De rondes van een week bij de vrouwen (Tour de France Femmes,
# Giro Women, Vuelta Femenina) staan er bewust niet in: dat zijn geen grote
# rondes, en wie ze toch voor wil laten gaan verandert de volgorde en niet
# deze lijst.
GROTE_RONDES = {"tour-de-france", "giro", "vuelta"}


def _is_grote_ronde(slug_of_url: str) -> bool:
    return _race_slug(slug_of_url) in GROTE_RONDES

def _gpx_urls(stage: dict) -> list[str]:
    """Kandidaat-GPX-adressen voor een etappe.

    De slug komt uit de kalender en niet meer uit een handmatige tabel; dat
    was de helft van het Vuelta-probleem. De bestandsnaam blijft een
    aanname, en daarvoor is `_fetch_gpx_index` de terugval.
    """
    from . import cyclingstage as cs

    slug = stage.get("race_slug") or ""
    jaar = stage["date"].year if stage.get("date") else None
    if not slug or not jaar:
        return []
    eigen = GPX_OVERRIDE.get(f"{slug}/{jaar}/{stage.get('idx')}") if stage.get("idx") else None
    eigen = eigen or GPX_OVERRIDE.get(f"{slug}/{jaar}")
    vast = cs.gpx_urls(slug, jaar, None if stage.get("one_day") else stage.get("idx"))
    return ([eigen] if eigen else []) + vast


# Overzichtspagina met de GPX-bestanden van één koers, bv.
# ".../vuelta-2026-gpx/". De naam volgt de cyclingstage-slug hierboven;
# nagekeken voor de Tour, de Giro en de Vuelta.
CYCLINGSTAGE_GPX_INDEX = "https://www.cyclingstage.com/{cs}-{y}-gpx/"

_GPX_HREF = re.compile(r'href=["\']([^"\']+\.gpx)["\']', re.I)
_GPX_NUMMER = re.compile(r"(?:stage|etappe|rit)[-_]?0*(\d{1,2})(?:\D|$)", re.I)


def _gpx_index_urls(stage: dict) -> list[str]:
    """De GPX-overzichtspagina van de koers waar deze etappe bij hoort."""
    from . import cyclingstage as cs

    slug = stage.get("race_slug") or ""
    jaar = stage["date"].year if stage.get("date") else None
    url = cs.gpx_index_url(slug, jaar) if slug and jaar else ""
    return [url] if url else []


def _parse_gpx_index(html: str, basis: str, year: str) -> dict:
    """{etappenummer: gpx-adres} uit een cyclingstage GPX-pagina.

    Het nummer komt uit de **bestandsnaam** en niet uit de linktekst: die is
    opgemaakt en verschilt per koers, het bestandspad niet. Een eendaagse
    koers levert nummer 0 op.

    De pagina bevat ook links naar eerdere jaargangen, dus alleen adressen
    met dit jaar erin tellen mee - anders krijgt etappe 3 het profiel van
    vorig jaar. Staat het jaar nergens in een adres, dan is er niets te
    filteren en gaan ze allemaal mee.
    """
    from html import unescape
    from urllib.parse import urljoin

    gevonden = [urljoin(basis, unescape(h)) for h in _GPX_HREF.findall(html or "")]
    van_dit_jaar = [u for u in gevonden if f"/{year}/" in u or f"-{year}" in u]
    uit: dict[int, str] = {}
    for url in (van_dit_jaar or gevonden):
        m = _GPX_NUMMER.search(url.rsplit("/", 1)[-1])
        uit.setdefault(int(m.group(1)) if m else 0, url)
    return uit


def _fetch_gpx_index(stage: dict) -> dict:
    """{etappenummer: gpx-adres} zoals cyclingstage ze zelf op een rij zet.

    Terugval voor als geen van de vaste adressen uit `_gpx_urls` iets
    oplevert. Die adressen zijn een aanname over de bestandsnaam; deze
    pagina noemt het echte adres, dus hier wordt niets geraden.
    """
    import urllib.request
    for index_url in _gpx_index_urls(stage):
        try:
            req = urllib.request.Request(
                index_url,
                headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("GPX-overzicht ophalen mislukt (%s): %s", index_url, err)
            continue
        jaar = stage["date"].year if stage.get("date") else ""
        index = _parse_gpx_index(html, index_url, str(jaar))
        if index:
            _LOGGER.debug("GPX-overzicht %s: %s etappes", index_url, len(index))
            return index
        _LOGGER.debug("GPX-overzicht %s: geen .gpx-links gevonden", index_url)
    return {}


def _times_urls(stage: dict) -> list[str]:
    """Tijdschema-pagina's van cyclingstage; daar staat de tussensprint in."""
    from . import cyclingstage as cs

    if stage.get("one_day") or not stage.get("idx") or not stage.get("date"):
        return []
    return cs.times_url(stage.get("race_slug") or "", stage["date"].year,
                        stage.get("idx"))


def _parse_times(html):
    """Tussensprints (km tot finish) uit het tijdschema halen."""
    out = []
    for row in re.split(r"<tr", html or "", flags=re.I)[1:]:
        text = re.sub(r"[\s\u00a0]+", " ", re.sub(r"<[^>]+>", " ", row)).strip()
        if "sprint" not in text.lower():
            continue
        nums = re.findall(r"\d+(?:\.\d+)?", re.sub(r"\d{1,2}:\d{2}", " ", text))
        if len(nums) < 2:
            continue
        km_to_go = _num(nums[1])
        if km_to_go is not None and km_to_go >= 0:
            out.append(round(km_to_go, 1))
    return sorted(set(out), reverse=True)


def _fetch_times(stage: dict):
    """Tussensprint(s) van de etappe; lege lijst als er geen tijdschema is."""
    import urllib.request
    for url in _times_urls(stage):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Tijdschema ophalen mislukt (%s): %s", url, err)
            continue
        sp = _parse_times(html)
        if sp:
            _LOGGER.debug("Tussensprint(s) etappe %s: %s km te gaan", stage.get("idx"), sp)
            return sp
    return []


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _cat_from_score(length_km: float, grad: float) -> str:
    """Schat categorie uit zwaarte (benadering; officiele PCS-cat wint later)."""
    score = (grad / 2.0) ** 2 * length_km
    if score >= 110:
        return "HC"
    if score >= 50:
        return "1"
    if score >= 20:
        return "2"
    if score >= 8:
        return "3"
    return "4"


def _detect_climbs(series: list, min_grad: float = 3.0, min_gain: float = 140.0,
                   win_km: float = 0.7, gap_km: float = 1.6, max_out: int = 8,
                   steep_gain: float = 50.0, steep_grad: float = 4.0,
                   steep_len: float = 0.5) -> list:
    """Detecteer klimmen uit een (volledige) hoogtereeks [(km, ele), ...].

    Naast de gewone drempel (min_gain) wordt een kort maar steil klimmetje ook
    meegenomen: minstens steep_gain hoogtemeters bij steep_grad procent over
    steep_len kilometer. Zo blijft bijvoorbeeld de Butte Montmartre (1,1 km à
    5,9%, circa 65 hoogtemeters) niet onopgemerkt.
    """
    pts = [p for p in series if p and len(p) >= 2]
    n = len(pts)
    if n < 4:
        return []
    total = pts[-1][0] or 1
    climbing = [False] * n
    for i in range(n - 1):
        j = i + 1
        while j < n and pts[j][0] - pts[i][0] < win_km:
            j += 1
        j = min(j, n - 1)
        dk = pts[j][0] - pts[i][0]
        if dk > 0 and (pts[j][1] - pts[i][1]) / (dk * 10.0) >= min_grad:
            climbing[i] = True
    climbs = []
    i = 0
    while i < n:
        if not climbing[i]:
            i += 1
            continue
        start = i
        last = i
        j = i + 1
        while j < n:
            if climbing[j]:
                last = j
                j += 1
            else:
                gj = j
                while gj < n and not climbing[gj] and pts[gj][0] - pts[last][0] < gap_km:
                    gj += 1
                if gj < n and climbing[gj]:
                    j = gj
                else:
                    break
        # de stijgingsvlag dooft ~win_km vóór de top; zoek dus door tot voorbij
        # dat venster, anders mist een korte klim zijn eigen toppunt
        eind = last
        while eind + 1 < n and pts[eind + 1][0] - pts[last][0] <= win_km + 0.3:
            eind += 1
        pk = start
        for k in range(start, min(eind + 1, n)):
            if pts[k][1] >= pts[pk][1]:
                pk = k
        gain = pts[pk][1] - pts[start][1]
        length = pts[pk][0] - pts[start][0]
        grad = gain / (length * 10.0) if length > 0 else 0.0
        kort_en_steil = (gain >= steep_gain and grad >= steep_grad
                         and length >= steep_len)
        if length > 0 and (gain >= min_gain or kort_en_steil):
            climbs.append({
                "name": "",
                "category": _cat_from_score(length, grad),
                "km_to_finish": round(total - pts[pk][0], 1),
                "top_m": round(pts[pk][1]),
                "length_km": round(length, 1),
                "steepness_pct": round(grad, 1),
            })
        i = last + 1
    if len(climbs) > max_out:
        climbs = sorted(climbs, key=lambda c: c["steepness_pct"] * c["length_km"],
                        reverse=True)[:max_out]
    climbs.sort(key=lambda c: -(c["km_to_finish"] or 0))
    return climbs


def _lttb(series, n_out):
    """Reduceer een hoogtereeks tot n_out punten met behoud van de vorm.

    Largest-Triangle-Three-Buckets: per interval wordt het punt gekozen dat
    samen met de buren de grootste driehoek vormt. Toppen en dalen blijven
    daardoor staan, terwijl simpel elk zoveelste punt pakken ze juist wegsnijdt.
    """
    n = len(series)
    if n_out >= n or n_out < 3:
        return list(series)
    out = [series[0]]
    stap = (n - 2) / (n_out - 2)
    a = 0
    for i in range(n_out - 2):
        # gemiddelde van het volgende interval als derde punt van de driehoek
        vs, ve = int((i + 1) * stap) + 1, int((i + 2) * stap) + 1
        ve = min(ve, n)
        if ve <= vs:
            vs, ve = min(vs, n - 1), min(vs + 1, n)
        vx = sum(p[0] for p in series[vs:ve]) / max(ve - vs, 1)
        vy = sum(p[1] for p in series[vs:ve]) / max(ve - vs, 1)
        bs, be = int(i * stap) + 1, min(int((i + 1) * stap) + 1, n)
        ax, ay = series[a]
        beste, beste_opp = bs, -1.0
        for j in range(bs, be):
            opp = abs((ax - vx) * (series[j][1] - ay) - (ax - series[j][0]) * (vy - ay))
            if opp > beste_opp:
                beste_opp, beste = opp, j
        out.append(series[beste])
        a = beste
    out.append(series[-1])
    return out


def _fetch_gpx(gpx_url, n_out: int = 150):
    """Download GPX -> (gedownsamplede [[km,hoogte]], gedetecteerde klimmen).

    gpx_url mag een adres zijn of een lijst kandidaten; de eerste die een
    bruikbaar bestand oplevert wint.
    """
    if not gpx_url:
        return [], []
    if isinstance(gpx_url, (list, tuple)):
        for kandidaat in gpx_url:
            elev, climbs = _fetch_gpx(kandidaat, n_out)
            if elev:
                return elev, climbs
        return [], []
    import urllib.request
    try:
        req = urllib.request.Request(
            gpx_url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("GPX ophalen mislukt %s: %s", gpx_url, err)
        return [], []
    text = raw.decode("utf-8", "replace")
    pts = re.findall(r'<trkpt[^>]*lat="([-\d.]+)"[^>]*lon="([-\d.]+)"[^>]*>(.*?)</trkpt>',
                     text, re.S)
    if not pts:
        alt = re.findall(r'<trkpt[^>]*lon="([-\d.]+)"[^>]*lat="([-\d.]+)"[^>]*>(.*?)</trkpt>',
                         text, re.S)
        pts = [(la, lo, b) for (lo, la, b) in alt]
    series = []
    cum = 0.0
    plat = plon = None
    for la, lo, body in pts:
        try:
            lat = float(la)
            lon = float(lo)
        except ValueError:
            continue
        em = re.search(r"<ele>([-\d.]+)</ele>", body)
        ele = float(em.group(1)) if em else None
        if plat is not None:
            cum += _haversine(plat, plon, lat, lon)
        plat, plon = lat, lon
        if ele is not None:
            series.append((cum, ele))
    if len(series) < 2:
        return [], []
    total = series[-1][0]
    if total <= 0:
        return [], []
    climbs = _detect_climbs(series)
    out = [[round(km, 1), round(ele)] for km, ele in _lttb(series, n_out)]
    _LOGGER.debug("GPX %s: %d trackpunten -> %d punten, %d cols",
                  gpx_url, len(series), len(out), len(climbs))
    return out, climbs


class CyclingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, options: dict | None = None) -> None:
        # opties komen uit het optiescherm; ontbreekt er een, dan de standaard
        self._options = {**OPTION_DEFAULTS, **(options or {})}
        super().__init__(hass, _LOGGER, name=DOMAIN,
                         update_interval=self._scan_interval)
        self._calendar: list[dict] | None = None
        self._calendar_fetched: date | None = None
        # aantal koersen per niveau uit de laatste kalender; gaat als
        # `levels_diag` naar de attributen
        self._levels_diag: dict = {}
        # meldingen van niveaus die niet opgehaald konden worden; bepalen
        # wat er in `UpdateFailed` komt als de kalender leeg blijft
        self._kalenderfouten: list = []
        self._stages_cache: dict[str, tuple[date, list[dict]]] = {}
        self._upcoming_cache: dict[str, dict] = {}
        self._elev_cache: dict[tuple[str, int], tuple] = {}
        self._gpx_beschikbaar: dict[str, bool] = {}
        # {koers/jaar: {etappenummer: gpx-adres}} van de overzichtspagina van
        # cyclingstage. Wordt alleen gevuld als de vaste adressen niets geven,
        # en dan hoogstens één keer per koers per dag.
        self._gpxindex_cache: dict[str, dict] = {}
        # welk gpx-adres het uiteindelijk werd, per etappe; gaat als
        # `gpx_used` naar de attributen zodat een ontbrekend profiel te
        # herleiden is zonder in het debuglogboek te duiken
        self._gpx_gebruikt: dict[str, str] = {}
        # de tv-gids van vandaag als HTML; daar staan álle koersen op, dus
        # één verzoek per dag bedient de tegel en de pop-up samen
        self._tv_cache = None
        # tussensprints en klassementsstanden per etappe. Allebei een dict en
        # niet één plek, want de koersen in de pop-up vragen ze ook op.
        self._sprints_cache: dict[str, list] = {}
        # uitslag per etappe van de andere koersen, op stage_url; per dag geleegd
        self._other_cache: dict[str, dict] = {}
        self._names_cache: dict[str, list] = {}
        self._prose_cache: dict[str, list] = {}
        # uitslag van een gereden etappe om in terug te bladeren, op
        # stage_url. Deze wordt bewust *niet* bij een nieuwe dag geleegd: een
        # etappe die gereden is verandert niet meer, en juist gisteren is de
        # etappe waar het meest in wordt teruggekeken. Het scheelt elke
        # ochtend een verzoek per etappe.
        self._past_cache: dict[str, dict] = {}
        self._names_diag: list = []

    def _opt(self, sleutel: str) -> int:
        """Waarde uit het optiescherm, met de standaard als terugval."""
        waarde = self._options.get(sleutel, OPTION_DEFAULTS[sleutel])
        try:
            return int(waarde)
        except (TypeError, ValueError):
            return OPTION_DEFAULTS[sleutel]

    def _opt_niveaus(self, sleutel: str) -> list[str]:
        """Een keuzelijst met niveaus uit het optiescherm."""
        return _lees_niveaus(self._options.get(sleutel, OPTION_DEFAULTS[sleutel]))

    @property
    def _niveaus_tegel(self) -> list[str]:
        """Niveaus die op de tegel mogen komen (en dus ook in de pop-up)."""
        return self._opt_niveaus(CONF_LEVELS) or list(OPTION_DEFAULTS[CONF_LEVELS])

    @property
    def _niveaus_alles(self) -> list[str]:
        """Alle niveaus die worden opgehaald: die van de tegel plus de pop-up."""
        alles = list(self._niveaus_tegel)
        for niveau in self._opt_niveaus(CONF_LEVELS_POPUP):
            if niveau not in alles:
                alles.append(niveau)
        return alles

    def _mag_op_tegel(self, ev: dict) -> bool:
        """Mag deze koers de tegel op, of hoort hij alleen in de pop-up?"""
        niveau = str(ev.get("level", ""))
        # een koers zonder niveau (kalender van een oudere versie) sluiten
        # we niet uit; dat zou de tegel leeg laten
        return not niveau or niveau in self._niveaus_tegel

    @property
    def _scan_interval(self) -> timedelta:
        return timedelta(minutes=self._opt(CONF_SCAN_MINUTES))

    @property
    def _live_scan_interval(self) -> timedelta:
        return timedelta(minutes=self._opt(CONF_LIVE_SCAN_MINUTES))

    async def _job(self, fn, *args):
        return await self.hass.async_add_executor_job(fn, *args)

    async def _stages_for(self, event: dict, today: date) -> list[dict]:
        key = event["url"]
        cached = self._stages_cache.get(key)
        if cached and cached[0] == today:
            return cached[1]
        stages = await self._job(_event_stages, event)
        if stages:
            self._stages_cache[key] = (today, stages)
        return stages

    async def _tv_gids(self, today: date) -> str:
        """De tv-gids van vandaag, één keer opgehaald voor alle koersen."""
        if self._tv_cache and self._tv_cache[0] == today:
            return self._tv_cache[1]
        html = await self._job(_fetch_tv_html)
        if html:
            self._tv_cache = (today, html)
        return html

    async def _zenders_voor(self, stage: dict, today: date) -> list[dict]:
        """NL-tv-zenders van een etappe; leeg als hij te ver weg is.

        Deze drie helpers slikken hun eigen fouten. Ze worden ook gebruikt
        voor de koersen in de pop-up, en daar zou een mislukte scrape
        anders het hele koersblok kosten.
        """
        if stage is None or (stage["date"] - today).days > 6:
            return []          # de tv-gids toont ~6 dagen vooruit
        try:
            html = await self._tv_gids(today)
            return await self._job(_channels_from, html, stage["race_url"],
                                   stage.get("idx"), stage.get("race_name"))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("TV-zenders mislukt voor %s: %s",
                          stage.get("stage_url"), err)
            return []

    async def _sprints_voor(self, stage: dict) -> list:
        """Tussensprint(en) uit het cyclingstage-tijdschema, per etappe bewaard."""
        url = stage["stage_url"]
        if url in self._sprints_cache:
            return self._sprints_cache[url]
        try:
            sprints = await self._job(_fetch_times, stage["race_url"],
                                      stage.get("idx"), stage.get("one_day"))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Tijdschema mislukt voor %s: %s", url, err)
            return []
        self._sprints_cache[url] = sprints
        return sprints

    async def _stage_uitslag(self, s):
        """Uitslag + standen van \u00e9\u00e9n etappe van een andere koers.

        Alleen een afgeronde etappe komt in de cache: een etappe die nog
        bezig is moet elke ronde opnieuw opgehaald worden.
        """
        url = s["stage_url"]
        if url in self._other_cache:
            return self._other_cache[url]
        d = await self._job(_fetch_stage, s,
                            self._opt(CONF_RESULT_N), self._opt(CONF_GC_N))
        if not d.get("finished"):
            return d
        self._other_cache[url] = d
        return d

    async def _race_entry(self, ev, stages, today):
        """E\u00e9n koersblok voor de pop-up: welke etappe eraan komt, plus de
        laatste uitslag en de standen.

        Het hoogteprofiel zit er bewust niet in. Dat staat al in `upcoming`,
        waar elke etappe met `race_key` vertelt bij welke koers hij hoort;
        de kaart zoekt het daar op. Twee keer meesturen zou de attributen
        onnodig groter maken.
        """
        naam = ev["name"]
        dames = bool(ev.get("women")) and not _noemt_dames(naam)
        entry = {
            "key": _race_slug(ev["url"]),
            "label": _short_race(naam, 24) + (" \u00b7 Dames" if dames else ""),
            "race_name": naam,
            "women": bool(ev.get("women")),
            # het niveau (mannen of vrouwen; zie NIVEAUS). De kaart
            # laat zich per dashboardkaart op niveaus instellen en heeft
            # hiermee genoeg om zelf te kiezen wat hij toont.
            "level": str(ev.get("level", "")),
            # kleur van de leiderstrui voor de knop in de pop-up; leeg als
            # die niet vaststaat, dan houdt de knop de accentkleur
            "jersey": _leiderstrui(ev["url"]),
            "eyebrow": "",
            "show_state": "",
            # dagen tot de eerstvolgende etappe van déze koers. Staat er
            # alleen op zodat een kaart die deze koers naar de tegel haalt
            # zijn eigen `visible_days` kan toepassen; None betekent dat er
            # geen etappe meer komt.
            "days_until": None,
            "last_stage_label": "",
            "last_result": [],
            "gc_top": [],
            "points_top": [],
            "kom_top": [],
            "youth_top": [],
            "channels": [],
            "channels_detail": [],
            # wie er aan de start staan; alleen gevuld zolang deze koers nog
            # geen uitslag heeft (zie onderaan)
            "startlist_top": [],
            "startlist_riders": 0,
            "startlist_teams": 0,
        }

        vandaag = next((s for s in stages if s["date"] == today), None)
        klaar = [s for s in stages if s["date"] < today]
        toon = vandaag or next((s for s in stages if s["date"] > today), None)

        # dezelfde rollover als op de tegel: is de etappe van vandaag klaar,
        # dan is dat de laatste uitslag en toont het blok de volgende
        laatst, data = None, None
        if vandaag is not None:
            d = await self._stage_uitslag(vandaag)
            if d.get("finished"):
                laatst, data = vandaag, d
                toon = next((s for s in stages if s["date"] > today), None)
        if data is None and klaar:
            d = await self._stage_uitslag(klaar[-1])
            if d.get("finished"):
                laatst, data = klaar[-1], d

        if toon is not None:
            entry["show_state"] = _show_state_for(toon["date"], today)
            entry["days_until"] = max(0, (toon["date"] - today).days)
            entry["eyebrow"] = (_short_race(toon["race_name"], 26) if toon.get("one_day")
                                else f"Etappe {toon['idx']} \u00b7 {_short_race(toon['race_name'])}")
            if dames:
                entry["eyebrow"] += " \u00b7 Dames"
            # waar de etappe te zien is; uit dezelfde tv-gids als de tegel
            zenders = await self._zenders_voor(toon, today)
            entry["channels_detail"] = zenders
            entry["channels"] = [f"{c['name']} {c['time']}".strip()
                                 for c in zenders if c.get("name")]
        if data is not None:
            entry["last_stage_label"] = (
                _short_race(laatst["race_name"], 34) if laatst.get("one_day")
                else f"Etappe {laatst['idx']} \u00b7 {_short_race(laatst['race_name'], 34)}")
            entry["last_result"] = (data.get("results") or [])[:self._opt(CONF_RESULT_N)]
            entry["gc_top"] = (data.get("gc") or [])[:self._opt(CONF_GC_N)]
            entry["points_top"] = data.get("points_top") or []
            entry["kom_top"] = data.get("kom_top") or []
            entry["youth_top"] = data.get("youth_top") or []
        # Hier stond de dagwinst (uit de kolom "Prev" bij procyclingstats) en
        # de startlijst voor een koers die nog geen uitslag heeft. Allebei
        # zonder bron sinds de overstap naar cyclingstage; zie het blok
        # daarover bovenin dit bestand.
        return entry

    async def _races_block(self, primair, andere, today):
        """De koersen die de pop-up naast elkaar zet.

        De eerste is de koers die ook op de tegel staat; die staat in de
        kaart standaard open en heeft geen eigen blok nodig, want al zijn
        gegevens staan al in de gewone attributen \u2014 vandaar `primary`.

        `other_label`/`other_result`/`other_gc` blijven er voor kaarten van
        v\u00f3\u00f3r deze opzet; ze herhalen de eerste andere koers met een uitslag.
        """
        races = [dict(primair, primary=True)]
        legacy = {"other_label": "", "other_result": [], "other_gc": []}
        # de koers en zijn etappes staan achteraan; de sleutels ervoor zijn
        # alleen om te sorteren en er komt er af en toe een bij
        for kandidaat in andere[:self._opt(CONF_MAX_OTHER)]:
            ev, st = kandidaat[-2], kandidaat[-1]
            try:
                blok = await self._race_entry(ev, st, today)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Koersblok mislukt voor %s: %s", ev.get("url"), err)
                continue
            races.append(blok)
            if not legacy["other_label"] and blok["last_result"]:
                legacy = {"other_label": blok["last_stage_label"],
                          "other_result": blok["last_result"],
                          "other_gc": blok["gc_top"][:5]}
        return dict(legacy, races=races)

    def _keuzesleutel(self, ev, nxt, i):
        """Waarop de tegel zijn koers kiest; lager sorteert vooraan.

        De volgorde: eerstvolgende etappe, dan de grote ronde, dan een koers
        waarvan we een hoogteprofiel hebben, dan de mannen, en als tiebreak
        de plek in de kalender.

        Het profiel stond hiervoor bóven de grote ronde, en dat gaf de Renewi
        Tour voorrang op de Vuelta zodra de Vuelta-GPX niet binnenkwam. Een
        bestand dat niet laadt hoort niet te bepalen welke koers de
        belangrijkste is; andersom mag een ontbrekend profiel nog steeds de
        doorslag geven tussen twee koersen die verder gelijk staan.
        """
        return (nxt["date"],
                0 if _is_grote_ronde(ev.get("url", "")) else 1,
                self._gpx_rang(nxt),
                1 if ev.get("women") else 0,
                i)

    def _gpx_rang(self, s):
        """0 = hoogteprofiel beschikbaar, 1 = (waarschijnlijk) niet."""
        bekend = self._gpx_beschikbaar.get(s["stage_url"])
        if bekend is not None:
            return 0 if bekend else 1
        return 0 if _gpx_urls(s) else 1

    async def _gpx_index(self, stage):
        """De GPX-adressen die cyclingstage zelf op een rij zet, per koers."""
        slug = stage.get("race_slug") or ""
        jaar = stage["date"].year if stage.get("date") else None
        if not slug or not jaar:
            return {}
        sleutel = f"{slug}/{jaar}"
        if sleutel not in self._gpxindex_cache:
            self._gpxindex_cache[sleutel] = await self._job(
                _fetch_gpx_index, stage)
        return self._gpxindex_cache[sleutel]

    async def _gpx_van(self, s, n_out):
        """Hoogteprofiel + cols van één etappe, zonder cache.

        Eerst de vaste adressen uit `_gpx_urls`. Die zijn een aanname over de
        bestandsnaam, en zodra cyclingstage er voor één koers van afwijkt
        blijft het profiel leeg zonder dat iets kapot lijkt. Levert geen
        enkel adres iets op, dan wordt het adres opgezocht op de
        GPX-overzichtspagina van die koers - de bron, dus geen gokwerk.
        """
        kandidaten = _gpx_urls(s)
        # één voor één en niet de hele lijst aan `_fetch_gpx`, want dan is
        # achteraf te zeggen wélk adres het werd (`gpx_used`)
        for kandidaat in kandidaten:
            elev, climbs = await self._job(_fetch_gpx, kandidaat, n_out)
            if elev:
                self._gpx_gebruikt[s["stage_url"]] = kandidaat
                return elev, climbs
        alt = (await self._gpx_index(s)).get(s.get("idx") or 0)
        if not alt or alt in kandidaten:
            return [], []
        elev, climbs = await self._job(_fetch_gpx, alt, n_out)
        if elev:
            _LOGGER.debug("GPX via de overzichtspagina: %s", alt)
            self._gpx_gebruikt[s["stage_url"]] = alt
        return elev, climbs

    # 60 punten voor de kleine profieltjes in "Komende dagen"; de getoonde
    # etappe vraagt er expliciet 200. Meer punten kosten alleen ruimte in de
    # attributen: bij 150 werd de state ruim 37 kB, boven de grens van de
    # recorder (MAX_STATE_ATTRS_BYTES = 16384).
    async def _gpx_for(self, s, n_out=60):
        # de cache staat op (etappe, aantal punten): dezelfde etappe wordt
        # eerst als komende dag opgehaald met 60 punten en later, als hij de
        # getoonde etappe is, met 200. Zonder het aantal in de sleutel kreeg
        # het grote profiel de kleine versie uit de cache.
        stage_url = s["stage_url"]
        sleutel = (stage_url, n_out)
        if sleutel in self._elev_cache:
            return self._elev_cache[sleutel]
        elev, climbs = await self._gpx_van(s, n_out)
        if elev:
            self._elev_cache[sleutel] = (elev, climbs)
        self._gpx_beschikbaar[stage_url] = bool(elev)
        return elev, climbs

    async def _names_for(self, stage_url, art_url, distance=None):
        if stage_url in self._names_cache:
            return self._names_cache[stage_url]
        result = await self._job(_fetch_stage_names, art_url, distance)
        if result[0] or result[1]:
            self._names_cache[stage_url] = result
        return result

    async def _upcoming_entry(self, s: dict, today: date,
                              met_sprints: bool = False) -> dict:
        url = s["stage_url"]
        cached = self._upcoming_cache.get(url)
        if cached is not None:
            e = dict(cached)
        else:
            await asyncio.sleep(0.4)  # niet overspoelen
            meta = await self._job(_fetch_stage_meta, s)
            elev, gpx_climbs = await self._gpx_van(s, 45)
            dist = meta.get("distance")
            if dist is None and elev:
                dist = elev[-1][0]
            cs_route = {}
            if gpx_climbs:  # namen uit de cyclingstage-etappetekst
                art = s["stage_url"]   # de etappepagina ís de tekst
                cs_names, cs_route = await self._job(_fetch_stage_names, art, dist)
                _match_names(gpx_climbs, cs_names)
                _name_summit(gpx_climbs, meta.get("arrival") or cs_route.get("arrival"))
                self._prose_cache[url] = [
                    (f"{c.get('name') or '?'} {c.get('length_km')}@{c.get('steepness_pct')}"
                     + (f" k2f={c['km_to_finish']}" if c.get('km_to_finish') is not None else ""))
                    for c in cs_names]
            # Hier stond tot 0.25 een terugval bij procyclingstats: colnamen
            # als de etappetekst ze niet noemt, en korte klimmen die de
            # GPX-detectie mist (Montmartre, 1,1 km). Die bron is
            # onbereikbaar, dus die cols blijven nu weg. Niets invullen wat
            # er niet staat.
            # De koersen in de pop-up tekenen hun profiel uit deze lijst, dus
            # de starttijd en de verwachte finish horen erbij — anders staat
            # er bij hen alleen een dag op de badge en bij de tegelkoers ook
            # de tijden. De echte finishtijd van cyclingstage gaat voor op de
            # schatting.
            start_time = meta.get("start_time") or ""
            e = {
                "start_time": start_time,
                "finish_est": cs_route.get("finish_time") or _finish_est(
                    start_time, dist, meta.get("profile_score"),
                    meta.get("vertical"), meta.get("stage_type")),
                "departure": meta.get("departure") or cs_route.get("departure") or "",
                "arrival": meta.get("arrival") or cs_route.get("arrival") or "",
                "distance_km": dist,
                "vertical_m": meta.get("vertical"),
                "profile_score": meta.get("profile_score"),
                "stage_type": meta.get("stage_type"),
                "watchability": _watchability(meta.get("profile_score"), dist,
                                              gpx_climbs, meta.get("stage_type"),
                                              meta.get("vertical")),
                "climbs": gpx_climbs,
                "elevation": elev,
            }
            if elev:
                self._upcoming_cache[url] = dict(e)
        sd = s["date"]
        e["date"] = sd.isoformat()
        e["show_state"] = _show_state_for(sd, today)
        # waar dit etappeprofiel bij hoort; de kaart zoekt er per koersblok
        # in de pop-up de eigen etappes mee op
        e["race_key"] = _race_slug(s["race_url"])
        # het niveau van de koers waar deze etappe bij hoort. De kaart laat
        # zich per dashboardkaart op niveaus instellen en heeft dat ook hier
        # nodig: staat een niveau uit, dan hoort zijn etappe ook niet onder
        # "Komende dagen" te blijven staan.
        e["level"] = str(s.get("level", ""))
        if s.get("one_day"):
            e["eyebrow"] = _short_race(s["race_name"], 26)
        else:
            e["eyebrow"] = f"Etappe {s['idx']} \u00b7 {_short_race(s['race_name'])}"
        if s.get("women") and not _noemt_dames(s["race_name"]):
            e["eyebrow"] += " \u00b7 Dames"
        _tag = _type_tag(e.get("stage_type"))
        if _tag:
            e["eyebrow"] += f" \u00b7 {_tag}"
        # de tussensprint alleen bij de etappe die als profiel getekend
        # wordt; in de profieltjes van "Komende dagen" is hij toch niet te
        # zien en zou hij alleen ruimte kosten
        if met_sprints:
            sprints = await self._sprints_voor(s)
            if sprints:
                e["sprints"] = sprints
        return e

    async def _build_past(self, finished: list[dict], overslaan: str,
                          today: date) -> list[dict]:
        """De laatst gereden etappes om in terug te bladeren.

        Alleen van de koers op de tegel. Het zou per koersblok kunnen — elke
        rij draagt `race_key`, dus de kaart kan het uit elkaar houden — maar
        dat vermenigvuldigt zowel de verzoeken als de bytes, en de attributen
        zitten al boven de grens van de recorder. Wie het breder wil, begint
        daar.

        De etappe die al als `last_result` in de attributen staat wordt
        overgeslagen; die zou anders dubbel staan.

        Elke uitslag komt uit `_past_cache` zodra hij een keer is opgehaald.
        Alleen een uitslag die er ook echt is komt in die cache: een pagina
        die nog leeg was moet morgen opnieuw geprobeerd worden.
        """
        aantal = self._opt(CONF_PAST_N)
        if aantal <= 0:
            return []
        out = []
        # van achteren naar voren: de meest recente etappe eerst
        for s in reversed(finished):
            if len(out) >= aantal:
                break
            url = s["stage_url"]
            if url == overslaan:
                continue
            rij = self._past_cache.get(url)
            if rij is None:
                try:
                    d = await self._job(_fetch_stage, s, PAST_RESULT_N, 0)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Uitslag terugblik mislukt voor %s: %s", url, err)
                    continue
                if not d.get("results"):
                    continue
                rij = {
                    "date": s["date"].isoformat(),
                    "race_key": _race_slug(s["race_url"]),
                    "level": str(s.get("level", "")),
                    "departure": d.get("departure") or "",
                    "arrival": d.get("arrival") or "",
                    "distance_km": d.get("distance"),
                    "results": d["results"],
                }
                if s.get("one_day"):
                    rij["eyebrow"] = _short_race(s["race_name"], 26)
                else:
                    rij["eyebrow"] = (f"Etappe {s['idx']} \u00b7 "
                                      f"{_short_race(s['race_name'])}")
                if s.get("women") and not _noemt_dames(s["race_name"]):
                    rij["eyebrow"] += " \u00b7 Dames"
                self._past_cache[url] = rij
            out.append(rij)
        return out

    async def _build_upcoming(self, cur_idx: int, shown: dict,
                              future: list[dict], today: date,
                              getoond: set | None = None) -> list[dict]:
        shown_url = shown.get("stage_url")
        cutoff = today + timedelta(days=self._opt(CONF_UPCOMING_DAYS))
        pool = [s for s in future
                if s["stage_url"] != shown_url and today <= s["date"] <= cutoff]
        # alle koersen die in het venster vallen, ook koersen die al eerder
        # begonnen dan de koers op de tegel (mannen en vrouwen door elkaar)
        koersen = list(self._calendar or [])
        for i, ev in enumerate(koersen):
            if i == cur_idx or ev["end"] < today or ev["start"] > cutoff:
                continue
            # een koers van een niveau dat alleen in de pop-up staat en die
            # daar geen knop heeft gekregen, hoeft ook geen etappes in
            # `upcoming`: die zijn nergens te zien en verdringen wel de
            # koersen die je wél ziet
            if (getoond is not None and not self._mag_op_tegel(ev)
                    and _race_slug(ev["url"]) not in getoond):
                continue
            pool.extend([s for s in await self._stages_for(ev, today)
                         if s["stage_url"] != shown_url
                         and today <= s["date"] <= cutoff])
        if not pool:   # niets binnen het venster -> pak de eerstvolgende koers(en)
            later = []
            for ev in koersen:
                if ev["end"] < today:
                    continue
                later.extend([s for s in await self._stages_for(ev, today)
                              if s["stage_url"] != shown_url and s["date"] > today])
                if later:
                    break
            pool = later
        # sorteren: op datum, en op een gedeelde dag eerst de mannen
        gezien, uniek = set(), []
        for s in sorted(pool, key=lambda s: (s["date"], 1 if s.get("women") else 0)):
            if s["stage_url"] in gezien:
                continue
            gezien.add(s["stage_url"])
            uniek.append(s)
        pool = uniek
        out = []
        diag = []
        # De kaart tekent voor elke koers in de pop-up de eerste etappe uit
        # deze lijst als profiel. Daar hoort de tussensprint bij, net als op
        # de tegel — maar alleen daar, want elke sprint kost een verzoek bij
        # cyclingstage. De koers van de tegel heeft zijn eigen sprints al.
        tegel_key = _race_slug(shown.get("race_url", ""))
        eerste_van = set()
        for s in pool[:self._opt(CONF_UPCOMING_N)]:
            try:
                key = _race_slug(s["race_url"])
                met_sprints = (getoond is not None and key in getoond
                               and key != tegel_key and key not in eerste_van)
                eerste_van.add(key)
                e = await self._upcoming_entry(s, today, met_sprints)
                if e:
                    out.append(e)
                    if len(diag) < 3:
                        det = [
                            (f"{round(_num(c.get('km_to_finish')) or 0)}km "
                             f"{c.get('length_km')}@{c.get('steepness_pct')}"
                             + (" ✓ " + c["name"] if c.get("name") else " —"))
                            for c in (e.get("climbs") or [])]
                        diag.append({"etappe": e.get("eyebrow", ""),
                                     "tekst_cols": self._prose_cache.get(s["stage_url"], []),
                                     "gevonden_cols": det})
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Upcoming mislukt voor %s: %s", s.get("stage_url"), err)
        self._names_diag = diag
        return out

    async def _async_update_data(self) -> dict:
        today = dt_util.now().date()
        # Kalender: cache 24h, altijd verversen bij jaarwissel
        if (self._calendar is None or self._calendar_fetched is None
                or (today - self._calendar_fetched) >= timedelta(days=1)):
            try:
                self._calendar, self._levels_diag, self._kalenderfouten = \
                    await self._job(_fetch_calendar, today.year,
                                    self._niveaus_alles)
                self._calendar_fetched = today
                self._stages_cache.clear()
                self._upcoming_cache.clear()
                self._elev_cache.clear()
                self._gpx_beschikbaar.clear()
                self._gpxindex_cache.clear()
                self._gpx_gebruikt.clear()
                self._tv_cache = None
                self._sprints_cache.clear()
                self._other_cache.clear()
                self._names_cache.clear()
                self._prose_cache.clear()
            except Exception as err:  # noqa: BLE001
                if self._calendar is None:
                    raise UpdateFailed(f"Kalender ophalen mislukt: {err}") from err
                _LOGGER.warning("Kalender verversen mislukt, oude cache: %s", err)

        if not self._calendar:
            # kwam er van geen enkel niveau een pagina binnen, dan is dat de
            # melding — niet de gok dat de opmaak van PCS veranderd is
            if self._kalenderfouten:
                raise UpdateFailed("Kalender ophalen mislukt: "
                                   + "; ".join(dict.fromkeys(self._kalenderfouten)))
            raise UpdateFailed("Geen wedstrijden gevonden — PCS-structuur gewijzigd?")

        # de tegel gaat bij voorkeur naar een koers van een niveau dat daar
        # mag staan; blijft er anders niets over, dan liever een koers uit
        # de pop-up dan een lege tegel
        cur_idx = next((i for i, r in enumerate(self._calendar)
                        if r["end"] >= today and self._mag_op_tegel(r)), None)
        if cur_idx is None:
            cur_idx = next((i for i, r in enumerate(self._calendar)
                            if r["end"] >= today), None)
        if cur_idx is None:
            return {"state": "Seizoen afgelopen", "attributes": {"show_state": "Klaar"}}

        # Mannen en vrouwen kunnen tegelijk koersen; kies er EEN voor het dashboard.
        # Volgorde: eerstvolgende etappe, dan koersen met hoogteprofiel, dan mannen.
        venster = today + timedelta(days=self._opt(CONF_UPCOMING_DAYS))
        actief = [(i, r) for i, r in enumerate(self._calendar)
                  if r["end"] >= today and r["start"] <= venster]
        # koersen die op de tegel mogen eerst: staat er een niveau aan dat
        # alleen in de pop-up hoort, dan mag een druk weekend daarvan de
        # WorldTour niet uit de lijst duwen
        actief.sort(key=lambda p: (0 if self._mag_op_tegel(p[1]) else 1,
                                   p[1]["start"], bool(p[1].get("women"))))
        actief = actief[:MAX_ACTIEVE_KOERSEN]
        if not actief:
            actief = [(cur_idx, self._calendar[cur_idx])]
        kandidaten = []
        for i, ev in actief:
            st = await self._stages_for(ev, today)
            nxt = next((s for s in st if s["date"] >= today), None)
            if nxt is None:
                continue
            kandidaten.append(self._keuzesleutel(ev, nxt, i) + (ev, st))
        if kandidaten:
            kandidaten.sort(key=lambda k: k[:5])
            op_tegel = [k for k in kandidaten if self._mag_op_tegel(k[5])]
            gekozen = (op_tegel or kandidaten)[0]
            cur_idx, cur, stages = gekozen[4], gekozen[5], gekozen[6]
            # in de pop-up ook eerst de niveaus van het dashboard, daarna de
            # niveaus die er alleen in de pop-up bij staan
            andere_koersen = sorted(
                (k for k in kandidaten if k is not gekozen),
                key=lambda k: (0 if self._mag_op_tegel(k[5]) else 1,) + tuple(k[:5]))
            if len(kandidaten) > 1:
                _LOGGER.debug("Koerskeuze: %s (uit %s kandidaten)",
                              cur["name"], len(kandidaten))
        else:
            cur = self._calendar[cur_idx]
            stages = await self._stages_for(cur, today)
            andere_koersen = []

        finished = [s for s in stages if s["date"] < today]
        today_st = next((s for s in stages if s["date"] == today), None)
        future = [s for s in stages if s["date"] > today]

        shown = None
        shown_event = cur
        shown_data = None
        last_fin = finished[-1] if finished else None
        last_fin_data = None
        today_finished = False

        if today_st:
            td = await self._job(_fetch_stage, today_st,
                                 self._opt(CONF_RESULT_N), self._opt(CONF_GC_N))
            if td.get("finished"):
                today_finished = True
                last_fin, last_fin_data = today_st, td
                shown = future[0] if future else None
            else:
                shown, shown_data = today_st, td  # live/vandaag
        else:
            shown = future[0] if future else None  # rustdag / pre-race

        # Voorbij de laatste etappe van deze koers -> volgende koers die op
        # de tegel mag staan
        if shown is None:
            for volgende in self._calendar[cur_idx + 1:]:
                if not self._mag_op_tegel(volgende):
                    continue
                nstages = await self._stages_for(volgende, today)
                if nstages:
                    shown, shown_event = nstages[0], volgende
                    break

        if shown is None:
            return {"state": "Seizoen afgelopen", "attributes": {"show_state": "Klaar"}}

        if shown_data is None:
            shown_data = await self._job(_fetch_stage, shown,
                                         self._opt(CONF_RESULT_N), self._opt(CONF_GC_N))
        if last_fin is not None and last_fin_data is None:
            last_fin_data = await self._job(_fetch_stage, last_fin,
                                            self._opt(CONF_RESULT_N), self._opt(CONF_GC_N))

        # Hier stond het naamherstel (de namenkolom van procyclingstats kon
        # verschuiven), het ophalen van de officiële ploegcodes en de
        # dagwinst uit de kolom "Prev". Cyclingstage leest namen per regel,
        # dus dat eerste probleem bestaat niet meer; voor de andere twee is
        # er geen bron. Zie het blok over procyclingstats bovenin.

        # Echt hoogteprofiel + gedetecteerde cols (GPX) voor de getoonde etappe.
        # Tot 0.25 haalde procyclingstats hier de colnamen en de officiële
        # categorie bij; die bron is onbereikbaar. De namen komen nu alleen
        # uit de etappetekst van cyclingstage en de categorie blijft leeg —
        # cyclingstage publiceert geen bergklassement.
        gpx_url = _gpx_urls(shown)
        elevation, gpx_climbs = await self._gpx_for(shown, 200)
        cs_route = {}
        elev_bron = "gpx" if elevation else ""
        if gpx_climbs:
            art = shown["stage_url"]
            cs_names, cs_route = await self._names_for(
                shown["stage_url"], art, shown_data.get("distance"))
            _match_names(gpx_climbs, cs_names)
            _name_summit(gpx_climbs, shown_data.get("arrival") or cs_route.get("arrival"))
            climbs = gpx_climbs
        else:
            climbs = []
        if shown_data.get("distance") is None and elevation:
            shown_data["distance"] = elevation[-1][0]

        # tussensprint(en) uit het cyclingstage-tijdschema
        sprints = await self._sprints_voor(shown)

        # de aanklikbare koersen in de pop-up: eerst de getoonde koers, dan
        # de andere die tegelijk lopen, elk met hun eigen uitslag en standen
        _dames = bool(shown.get("women")) and not _noemt_dames(shown["race_name"])
        ander = await self._races_block(
            {"key": _race_slug(shown["race_url"]),
             "label": _short_race(shown["race_name"], 24) + (" · Dames" if _dames else ""),
             "race_name": shown["race_name"],
             "women": bool(shown.get("women")),
             "level": str(shown.get("level", "")),
             "jersey": _leiderstrui(shown["race_url"])},
            andere_koersen, today)

        # ── Status-pill + eyebrow ─────────────────────────────
        sd = shown["date"]
        if sd == today and not today_finished:
            hhmm = _parse_start_hhmm(shown_data.get("start_time"))
            now = dt_util.now()
            started = hhmm is not None and (now.hour, now.minute) >= hhmm
            show_state = "LIVE" if started else "Vandaag"
        elif sd == today + timedelta(days=1):
            show_state = "Morgen"
        else:
            show_state = f"{DAYS_NL[sd.weekday()]} {_fmt_nl(sd)}"


        if shown.get("one_day"):
            stage_label = shown["race_name"]
            eyebrow = _short_race(shown["race_name"], 26)
        else:
            stage_label = f"Etappe {shown['idx']}"
            eyebrow = f"{stage_label} · {_short_race(shown['race_name'])}"
        if shown.get("women") and not _noemt_dames(shown["race_name"]):
            eyebrow += " · Dames"
        _tag = _type_tag(shown_data.get("stage_type"))
        if _tag:
            eyebrow += f" · {_tag}"

        # ── etappe-data samenstellen (voor de attributen) ─────
        svg_stage = {
            "race_name": shown["race_name"],
            "departure": shown_data.get("departure") or "",
            "arrival": shown_data.get("arrival") or "",
            "distance_km": shown_data.get("distance"),
            "vertical_m": shown_data.get("vertical"),
            "profile_score": shown_data.get("profile_score"),
            "climbs": climbs,
        }
        # ── Spoiler-blok (alleen pop-up) ──────────────────────
        last_result = last_fin_data.get("results", []) if last_fin_data else []
        gc_top = last_fin_data.get("gc", []) if last_fin_data else []
        # De startlijst vulde het gat van een koers die nog geen uitslag
        # heeft. Hij kwam van procyclingstats en cyclingstage heeft er geen;
        # de sleutels blijven leeg staan zodat een oudere kaart niet
        # struikelt, en de meegeleverde kaart laat het onderdeel weg.
        startlijst = {"startlist_top": [], "startlist_riders": 0,
                      "startlist_teams": 0}
        if last_fin is None:
            last_stage_label = ""
        elif last_fin.get("one_day"):
            last_stage_label = last_fin["race_name"]
        else:
            last_stage_label = f"Etappe {last_fin['idx']} · {_short_race(last_fin['race_name'])}"

        # ── Backward-compat attributen (bestaande kaart) ──────
        cur_live = cur["start"] <= today <= cur["end"]
        one_day = cur["start"] == cur["end"]
        is_monument = _race_slug(cur["url"]) in MONUMENTS
        if cur_live and not one_day:
            countdown = (f"🟢 Bezig — dag {(today - cur['start']).days + 1}/"
                         f"{(cur['end'] - cur['start']).days + 1}")
        elif cur_live:
            countdown = "🟢 Vandaag"
        else:
            d = (cur["start"] - today).days
            countdown = "Start morgen" if d == 1 else f"Over {d} dagen"
        terrain = ""
        old_stage_info = ""
        old_stars = 3 if is_monument else 2
        if today_st and (shown_data or last_fin_data):
            src = last_fin_data if today_finished else shown_data
            if src:
                icon = src.get("profile_icon") or ""
                terrain, old_stars = PROFILE_MAP.get(icon, (terrain, old_stars))
                dep, arr = src.get("departure"), src.get("arrival")
                if dep and arr:
                    old_stage_info = f"{dep} → {arr}"
        date_display = _fmt_nl(cur["start"]) if one_day else \
            f"{_fmt_nl(cur['start'])} – {_fmt_nl(cur['end'])}"

        # Komende etappes (mini-profielen in de pop-up)
        upcoming = await self._build_upcoming(
            cur_idx, shown, future, today,
            {r.get("key") for r in ander.get("races", [])})

        # Terugbladeren door de uitslagen van deze koers. `last_fin` staat al
        # als `last_result` in de attributen, dus die slaan we hier over.
        past = await self._build_past(
            finished, (last_fin or {}).get("stage_url", ""), today)

        # Links. De live-positie zelf heeft geen bron meer; zie de opmerking
        # bij het verdwenen `_fetch_live`.
        from urllib.parse import quote
        _yr = re.search(r"/(20\d\d)(?:/|$)", shown.get("stage_url", ""))
        _yr = _yr.group(1) if _yr else ""
        _sm = re.search(r"Etappe (\d+)", last_stage_label or "")
        _q = (f"{cur['name']} {_yr} stage {_sm.group(1)} extended highlights"
              if _sm else f"{cur['name']} {_yr} highlights")
        highlights_url = "https://www.youtube.com/results?search_query=" + quote(_q)
        # Het live-adres bij procyclingstats kwam uit een PCS-etappeadres, en
        # dat hebben we niet meer. Er een raden op grond van de
        # cyclingstage-slug is precies wat ons het Vuelta-profiel kostte, dus
        # het blijft leeg en de kaart laat de link weg.
        live_url = ""
        # tijdens een live etappe vaker verversen zodat het live-stipje meebeweegt
        self.update_interval = (self._live_scan_interval if show_state == "LIVE"
                                else self._scan_interval)
        # voor de conditionele dashboardkaart
        today_or_tomorrow = show_state in ("LIVE", "Vandaag", "Morgen")
        days_until = max(0, (shown["date"] - today).days)
        # echte finishtijd van cyclingstage; anders de schatting
        finish_est = cs_route.get("finish_time") or _finish_est(
            shown_data.get("start_time"), svg_stage["distance_km"],
            svg_stage["profile_score"], svg_stage["vertical_m"],
            shown_data.get("stage_type"))
        channels = await self._zenders_voor(shown, today)

        return {
            "state": shown["race_name"],
            "attributes": {
                # ── spoiler-vrij (tegel + pop-up) ──
                "show_state": show_state,
                "eyebrow": eyebrow,
                "stage_label": stage_label,
                "departure": svg_stage["departure"],
                "arrival": svg_stage["arrival"],
                "distance_km": svg_stage["distance_km"],
                "vertical_m": svg_stage["vertical_m"],
                "profile_score": svg_stage["profile_score"],
                "stage_type": shown_data.get("stage_type") or "",
                "startlist_quality": shown_data.get("startlist_quality"),
                "watchability": _watchability(shown_data.get("profile_score"),
                    shown_data.get("distance"), climbs, shown_data.get("stage_type"),
                    shown_data.get("vertical")),
                "start_time": shown_data.get("start_time") or "",
                "climbs": climbs,
                "elevation": elevation,
                "upcoming": upcoming,
                "names_diag": self._names_diag,
                # aantal koersen per gekozen niveau; 0 verraadt een
                # circuitnummer dat niet klopt
                "levels_diag": self._levels_diag,
                # ── spoiler (alleen tonen in de pop-up!) ──
                "last_result": last_result,
                # eerder gereden etappes om in terug te bladeren
                "past": past,
                "gc_top": gc_top,
                "points_leader": last_fin_data.get("points_leader") if last_fin_data else "",
                "kom_leader": last_fin_data.get("kom_leader") if last_fin_data else "",
                "points_top": last_fin_data.get("points_top", []) if last_fin_data else [],
                "kom_top": last_fin_data.get("kom_top", []) if last_fin_data else [],
                "youth_leader": last_fin_data.get("youth_leader") if last_fin_data else "",
                "youth_top": last_fin_data.get("youth_top", []) if last_fin_data else [],
                "last_stage_label": last_stage_label,
                # ── startlijst (zolang er geen uitslag is) ──
                **startlijst,
                # ── backward-compat ──
                "race_name": cur["name"],
                "type": ("Monument" if is_monument else "Eendaagse koers"
                         if one_day else "Etappekoers"),
                "date": date_display,
                "countdown": countdown,
                "stage_today": old_stage_info,
                "terrain": terrain,
                "stars": "⭐" * old_stars,
                "is_live": cur_live,
                "today_or_tomorrow": today_or_tomorrow,
                "days_until": days_until,
                "women": bool(shown.get("women")),
                "gpx_diag": [u.split("/images/")[-1] for u in (gpx_url or [])],
                # welk adres het werd; leeg betekent dat geen enkel adres een
                # bruikbaar bestand gaf, ook het adres van de
                # overzichtspagina niet
                "gpx_used": self._gpx_gebruikt.get(
                    shown["stage_url"], "").split("/images/")[-1],
                "times_diag": [u.split("/images/")[-1] for u in
                               _times_urls(shown)],
                "elevation_source": elev_bron,
                "sprints": sprints,
                **ander,
                "finish_est": finish_est,
                "channels": [f"{c['name']} {c['time']}".strip()
                             for c in channels if c.get("name")],
                "channels_detail": channels,
                # ── live positie (spoilervrij) + links ──
                # De sleutels blijven staan zodat een oudere kaart niet
                # struikelt; ze zijn leeg omdat er geen bron voor is.
                "live_km_to_go": None,
                "live_avg_speed": None,
                "live_status": "",
                "live_url": live_url,
                "highlights_url": highlights_url,
            },
        }


# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """De gewone weg: opgezet vanuit een config entry.

    Bewust géén `async_config_entry_first_refresh()`. Die gooit
    `ConfigEntryNotReady` zodra de eerste ophaalactie faalt, en dan wordt de
    entiteit niet toegevoegd. Home Assistant zet er vervolgens een herstelde
    entiteit neer — status `unavailable`, `restored: true`, geen enkel
    attribuut — en daar valt niets aan af te lezen: niet dát het opzetten
    mislukte, en niet waaróm. De kaart tekende er een lege tegel mee.

    Eén mislukte ronde bij cyclingstage hoort deze integratie ook niet te
    blokkeren: er hangt geen apparaat aan, de kalender komt uit een website
    die er weleens even uit ligt, en een half uur later is het meestal weer
    goed. De entiteit komt er daarom altijd; lukt de eerste ronde niet, dan
    staat hij onbeschikbaar tot de volgende en zegt het log waarom.

    De prijs is dat Home Assistant de entry als geladen beschouwt en dus zelf
    niet opnieuw probeert. Dat doet de coordinator al op zijn eigen ritme.
    """
    coordinator = CyclingCoordinator(hass, dict(entry.options))
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        _LOGGER.warning(
            "Eerste ophaalronde mislukt; de sensor blijft onbeschikbaar tot "
            "de volgende ronde. Reden: %s", coordinator.last_exception)
    async_add_entities([CyclingNextRaceSensor(coordinator)])


async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """Oude YAML-configuratie: eenmalig omzetten naar een config entry.

    Wie `sensor: - platform: cycling_next_race` in configuration.yaml heeft
    staan houdt zijn sensor; de import-flow maakt er een entry van en de
    YAML-regel mag daarna weg.
    """
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={},
        )
    )


class CyclingNextRaceSensor(CoordinatorEntity, SensorEntity):
    # Engelse naam, gelijk aan het domein, zodat de entiteit
    # sensor.cycling_next_race heet. De unique_id blijft ongewijzigd: wie de
    # integratie al had houdt zijn registratie en kan de entiteit-id zelf
    # aanpassen zonder dat er een tweede entiteit bijkomt.
    _attr_name = NAME
    _attr_unique_id = DOMAIN
    _attr_icon = "mdi:bike-fast"

    @property
    def native_value(self):
        # `data` is None zolang er nog geen geslaagde ronde is geweest; de
        # entiteit bestaat dan wel al, want het opzetten wacht daar niet op
        return (self.coordinator.data or {}).get("state")

    @property
    def extra_state_attributes(self):
        return (self.coordinator.data or {}).get("attributes", {})
