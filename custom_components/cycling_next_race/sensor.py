"""Sensor: eerstvolgende of lopende UCI WorldTour wedstrijd via procyclingstats.com.

YAML-configuratie:

    sensor:
      - platform: cycling_next_race

Uitgebreide versie:
- Spoiler-vrije attributen voor tegel + pop-up (parcours, cols, profielscore ...).
- Spoiler-attributen ALLEEN bedoeld voor de pop-up (uitslag laatste etappe + klassement).
- Etappe-selectie met rollover: zodra de etappe van vandaag klaar is (uitslag binnen)
  toont de tegel de eerstvolgende etappe. Een rustdag telt niet als etappe.

De kalender wordt 1x per dag opgehaald; live wordt elk half uur ververst.
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

from .const import (
    CONF_GC_N,
    CONF_LEVELS,
    CONF_LEVELS_POPUP,
    CONF_LIVE_SCAN_MINUTES,
    CONF_MAX_OTHER,
    CONF_RESULT_N,
    CONF_SCAN_MINUTES,
    CONF_START_N,
    CONF_UPCOMING_DAYS,
    CONF_UPCOMING_N,
    DEFAULT_GC_N,
    DEFAULT_LIVE_SCAN_MINUTES,
    DEFAULT_MAX_OTHER,
    DEFAULT_RESULT_N,
    DEFAULT_SCAN_MINUTES,
    DEFAULT_START_N,
    DEFAULT_UPCOMING_DAYS,
    DEFAULT_UPCOMING_N,
    DOMAIN,
    NAME,
    NIVEAUS,
    OPTION_DEFAULTS,
)

_LOGGER = logging.getLogger(__name__)

# Standaardwaarden. Ze zijn in te stellen via het optiescherm; deze constanten
# blijven de terugval wanneer een optie ontbreekt.
SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_MINUTES)
LIVE_SCAN_INTERVAL = timedelta(minutes=DEFAULT_LIVE_SCAN_MINUTES)

RESULT_N = DEFAULT_RESULT_N  # aantal renners in de uitslag (pop-up)
GC_N = DEFAULT_GC_N          # aantal renners in het klassement (pop-up)
START_N = DEFAULT_START_N    # aantal renners in de startlijst (pop-up)
UPCOMING_N = DEFAULT_UPCOMING_N  # veiligheidscap op aantal komende etappes
UPCOMING_DAYS = DEFAULT_UPCOMING_DAYS  # venster voor "Komende dagen"

# Hoeveel koersen er naast de getoonde in de pop-up aanklikbaar zijn. Elke
# koers erbij kost twee extra paginaverzoeken bij procyclingstats en ruimte
# in de attributen; in de praktijk lopen er mannen en vrouwen tegelijk.
# In te stellen via `max_other`; dit is de standaard.
MAX_ANDERE_KOERSEN = DEFAULT_MAX_OTHER

# Hoeveel koersen er hoogstens tegelijk worden bekeken om te bepalen welke op
# de tegel komt en welke er in de pop-up naast passen. Alles daarboven kost
# alleen maar verzoeken: er staan er toch maar 1 + `max_other` in beeld.
MAX_ACTIEVE_KOERSEN = 6

# Hoeveel ploegcodes er per ronde nieuw worden opgehaald. Een koers telt zo'n
# twintig ploegen en elke code is een eigen pagina; die allemaal ineens halen
# maakt de eerste update na een herstart onnodig lang. De rest volgt de
# volgende ronde en houdt tot die tijd de volledige ploegnaam.
MAX_PLOEGCODES_PER_RONDE = 12

# Kleur van de leiderstrui, voor de knoppen bovenin de pop-up.
#
# Dit is een vaste lijst, geen bron: procyclingstats geeft de kleur van een
# trui nergens terug. Er staan daarom alleen koersen in waarvan de truikleur
# buiten kijf staat. Een koers die er niet in staat krijgt geen kleur en
# houdt de gewone accentkleur van de kaart — liever geen kleur dan een
# verzonnen kleur. Eendaagse koersen hebben geen klassement en horen hier
# dus niet thuis. Sleutel: de procyclingstats-naam van de koers.
LEIDERSTRUI = {
    "tour-de-france": "#F3C700",          # geel
    "tour-de-france-femmes": "#F3C700",   # geel
    "giro-d-italia": "#E6007E",           # roze
    "giro-d-italia-women": "#E6007E",     # roze
    "vuelta-a-espana": "#D0021B",         # rood
    "vuelta-espana-femenina": "#D0021B",  # rood
    "paris-nice": "#F3C700",              # geel
    "tirreno-adriatico": "#0E5FA8",       # blauw
    "dauphine": "#F3C700",                # geel
    "tour-de-suisse": "#F3C700",          # geel
    "tour-de-romandie": "#F3C700",        # geel
    "tour-down-under": "#C8862B",         # oker
    "uae-tour": "#D0021B",                # rood
}

# De ranglijst waarop de startlijst wordt gesorteerd, per geslacht.
#
# Zolang een koers nog geen uitslag heeft valt er niets te tonen behalve wie
# er meedoen. De startlijst zelf staat op volgorde van ploeg en zegt niets
# over wie de kopmannen zijn; die volgorde komt daarom van de individuele
# ranglijst bij procyclingstats — een bron, geen inschatting. Wie daar niet
# op staat komt niet in het lijstje.
#
# Het mannenadres staat zo in de documentatie van het pakket. Het
# vrouwenadres is de analogie daarvan en kon van hieruit niet worden
# nagekeken (de sandbox komt niet bij procyclingstats), net als bij de
# ProSeries-circuitnummers. Klopt het niet, dan blijft de startlijst leeg;
# `_fetch_ranking` logt daar een waarschuwing bij en `startlist_diag` op de
# sensor laat zien hoeveel renners er gekoppeld konden worden.
RANGLIJST = {
    False: "rankings/me/individual",
    True: "rankings/we/individual",
}
RANGLIJST_ZEKER = {"rankings/me/individual"}

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


def _race_slug(url: str) -> str:
    m = re.match(r"race/([^/]+)", url)
    return m.group(1) if m else ""


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


def _safe(fn, default=None):
    """Roep een procyclingstats-parsemethode veilig aan."""
    try:
        v = fn()
        return default if v is None else v
    except Exception:  # noqa: BLE001  (parse mag falen)
        return default


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

# Welke browser curl_cffi nadoet. "chrome" volgt de nieuwste die de
# geïnstalleerde versie kent; een vast nummer zou verouderen zonder dat
# iemand het merkt, en juist een oude vingerafdruk valt op.
PCS_IMPERSONATE = "chrome"

# Basisadres van procyclingstats; het pakket werkt met relatieve paden en
# `_pcs_antwoord_diag` heeft een volledig adres nodig.
PCS_BASE = "https://www.procyclingstats.com/"


def _pcs_url(pad: str) -> str:
    """Relatief pad -> volledig adres, met het adres van het pakket zelf
    als dat er is (dan blijft het kloppen als procyclingstats verhuist)."""
    try:
        from procyclingstats.scraper import Scraper

        basis = getattr(Scraper, "BASE_URL", "") or PCS_BASE
    except Exception:  # noqa: BLE001
        basis = PCS_BASE
    return basis.rstrip("/") + "/" + (pad or "").lstrip("/")

# Of de sessie van procyclingstats al vervangen is. Modulewijd, want de
# patch zit op de klasse en hoeft maar één keer.
_PCS_SESSIE = ""


def _zet_pcs_sessie() -> str:
    """Laat procyclingstats via curl_cffi praten in plaats van requests.

    cloudscraper doet de héaders van een browser na, maar niet de
    TLS-handdruk. Cloudflare herkent die vingerafdruk en blokkeert alsnog —
    op 23 augustus 2026 stond in het log dat cloudscraper 1.2.71 geladen was
    en er tóch niet langs kwam. curl_cffi bootst de handdruk van Chrome zelf
    na en komt daar vaak wel doorheen.

    Dit is een monkeypatch op andermans pakket: `Scraper._get_session()` is
    interne code van procyclingstats en kan bij een update verdwijnen of van
    vorm veranderen. Daarom wordt hier alles afgevangen — lukt het niet, dan
    blijft de eigen sessie van het pakket gewoon staan en is er niets
    slechter geworden dan het al was.

    Eén gedeelde sessie, net als procyclingstats zelf doet: Cloudflare deelt
    cookies uit die je juist wilt bewaren.

    Geeft een korte melding terug voor in het log. Draait in de executor,
    want `import` en het opzetten van een sessie zijn blokkerend.
    """
    global _PCS_SESSIE
    if _PCS_SESSIE:
        return _PCS_SESSIE
    try:
        from curl_cffi import requests as curl_requests
    except Exception as err:  # noqa: BLE001
        _PCS_SESSIE = f"curl_cffi niet beschikbaar ({type(err).__name__}: {err})"
        return _PCS_SESSIE
    try:
        from procyclingstats.scraper import Scraper

        if not hasattr(Scraper, "_get_session"):
            # het pakket is van vorm veranderd; niets aanraken
            _PCS_SESSIE = ("procyclingstats kent geen _get_session meer, "
                           "curl_cffi niet aangesloten")
            return _PCS_SESSIE
        sessie = curl_requests.Session(impersonate=PCS_IMPERSONATE)
        Scraper._get_session = classmethod(lambda cls: sessie)
    except Exception as err:  # noqa: BLE001
        _PCS_SESSIE = f"curl_cffi aansluiten mislukt ({type(err).__name__}: {err})"
        return _PCS_SESSIE
    _PCS_SESSIE = f"curl_cffi actief (impersonate={PCS_IMPERSONATE})"
    _LOGGER.debug("procyclingstats praat nu via %s", _PCS_SESSIE)
    return _PCS_SESSIE


def _kop(headers, naam: str) -> str:
    """Eén header, ongeacht hoe de client hem schrijft."""
    try:
        waarde = headers.get(naam)
        if waarde:
            return str(waarde)
        for k, v in dict(headers).items():
            if str(k).lower() == naam.lower():
                return str(v)
    except Exception:  # noqa: BLE001
        pass
    return ""


def _pcs_antwoord_diag(url: str) -> str:
    """Wat procyclingstats werkelijk terugstuurt als het misgaat.

    Het pakket gooit dezelfde fout bij een JS-uitdaging ("Just a moment")
    en bij een kale 403, en dat zijn twee heel verschillende dingen: het
    eerste is een uitdaging die een client kan proberen te doorlopen, het
    tweede is een weigering (IP-reputatie, of beleid van de site) waar aan
    onze kant niets tegen helpt. Zolang dat verschil niet vaststaat is elke
    volgende bypass een gok.

    Eén verzoek, met dezelfde sessie die het pakket zelf gebruikt, zodat we
    meten wat procyclingstats ervaart en niet iets anders. Draait in de
    executor en wordt alleen aangeroepen als het al misgegaan is.
    """
    try:
        from procyclingstats.scraper import Scraper

        resp = Scraper._get_session().get(url, timeout=30)
    except Exception as err:  # noqa: BLE001
        return f"proefverzoek mislukt ({type(err).__name__}: {err})"

    tekst = getattr(resp, "text", "") or ""
    headers = getattr(resp, "headers", {}) or {}
    delen = [f"status {getattr(resp, 'status_code', '?')}",
             f"{len(tekst)} tekens"]

    # Cloudflare nummert zijn eigen weigeringen; 1020 = Access Denied
    # (firewallregel), 1015 = rate limit. Staat er een nummer, dan is het
    # een weigering en geen uitdaging.
    code = re.search(r"Error\s*(\d{4})", tekst)
    if code:
        delen.append(f"Cloudflare-fout {code.group(1)}")
    uitdaging = [m for m in ("Just a moment", "challenge-platform",
                             "cf-browser-verification", "Enable JavaScript")
                 if m.lower() in tekst.lower()]
    delen.append("uitdagingspagina (%s)" % ", ".join(uitdaging)
                 if uitdaging else "geen uitdagingstekst")
    for naam in ("cf-mitigated", "cf-ray", "server"):
        waarde = _kop(headers, naam)
        if waarde:
            delen.append(f"{naam}={waarde}")
    # de eerste regel tekst zegt vaak genoeg; opgeschoond en kort gehouden
    kaal = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", tekst)).strip()
    if kaal:
        delen.append(f"begin: {kaal[:160]!r}")
    return "; ".join(delen)


def _bypass_diag() -> str:
    """Welke bypasses er draaien op het moment dat Cloudflare toch blokkeert.

    Nodig omdat de melding van procyclingstats hierover niets zegt. Die
    luidt altijd "Cloudflare protection detected. Install 'cloudscraper'",
    ook als cloudscraper wél actief is: `_make_request` kijkt alleen of het
    antwoord een uitdagingspagina is of een 403, en plakt daar
    onvoorwaardelijk dat installatie-advies achter (nagekeken in de wheel,
    `scraper.py`). Uit het log alleen is dus niet te zien of de bypass
    ontbreekt of dat hij er niet langs komt — en dat is precies het verschil
    tussen "herstart Home Assistant" en "hier helpt dit pakket niet meer".

    Draait in de executor; `import` leest van schijf.
    """
    try:
        import cloudscraper
    except Exception as err:  # noqa: BLE001
        return (f"cloudscraper is NIET geladen ({type(err).__name__}: {err}) — "
                "herstart Home Assistant zodat de afhankelijkheid uit de "
                "manifest geïnstalleerd wordt")
    return (f"cloudscraper {getattr(cloudscraper, '__version__', '?')} is wél "
            f"geladen en {_PCS_SESSIE or 'curl_cffi is niet geprobeerd'}; "
            "procyclingstats komt er ondanks die bypass(es) niet langs")


def _fetch_calendar(year: int, niveaus: list[str]) -> tuple[list[dict], dict, list]:
    """Kalender van de gekozen niveaus ophalen van procyclingstats.com.

    Geeft `(koersen, telling, fouten)` terug. De telling is het aantal
    koersen per niveau en gaat als `levels_diag` naar de attributen, zodat
    een niveau dat niets oplevert in de interface te zien is.

    `fouten` zijn de meldingen van de niveaus die niet opgehaald konden
    worden. Die reizen mee omdat een lege kalender twee heel verschillende
    dingen kan betekenen: een circuitnummer dat niets oplevert, of een bron
    die niet bereikbaar was. Zonder dat onderscheid meldde de sensor
    "PCS-structuur gewijzigd?" terwijl procyclingstats simpelweg achter
    Cloudflare zat — dat wijst de verkeerde kant op.
    """
    from procyclingstats.scraper import Scraper

    class RacesCalendar(Scraper):
        def races(self) -> list[dict]:
            out = []
            table = self.html.css_first("table.basic")
            if table is None:
                return out
            for row in table.css("tbody tr"):
                cells = row.css("td")
                if len(cells) < 3:
                    continue
                link = row.css_first("a")
                if link is None:
                    continue
                href = link.attributes.get("href", "")
                if not href.startswith("race/"):
                    continue
                out.append({
                    "date": cells[0].text().strip(),
                    "url": href,
                    "name": link.text().strip(),
                })
            return out

    # vóór de eerste aanroep van het pakket; idempotent, dus dit is na de
    # eerste ronde een woordenboek-opzoeking
    _zet_pcs_sessie()

    races = []
    telling = {}
    fouten = []
    proef_pad = ""
    for niveau in niveaus or []:
        info = NIVEAUS.get(str(niveau))
        if info is None:
            _LOGGER.warning("Onbekend niveau %s, overgeslagen", niveau)
            continue
        gevonden = 0
        pad = f"races.php?year={year}&circuit={niveau}&class=&filter=Filter"
        try:
            cal = RacesCalendar(pad)
            rijen = cal.races()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Kalender van %s ophalen mislukt: %s", info["naam"], err)
            telling[info["naam"]] = 0
            fouten.append(str(err))
            proef_pad = proef_pad or pad
            continue
        for r in rijen:
            m = re.findall(r"(\d{2})\.(\d{2})", r["date"])
            if not m:
                continue
            # de kalenderlink eindigt vaak op /gc of /result -> terug naar race/<naam>/<jaar>
            u = re.match(r"(race/[^/]+/\d{4})", r["url"] or "")
            if not u:
                continue
            start = date(year, int(m[0][1]), int(m[0][0]))
            end = date(year, int(m[-1][1]), int(m[-1][0])) if len(m) > 1 else start
            races.append({"name": r["name"], "url": u.group(1),
                          "start": start, "end": end,
                          "women": info["vrouwen"], "level": str(niveau)})
            gevonden += 1
        telling[info["naam"]] = gevonden
        if not gevonden:
            # een verkeerd circuitnummer levert stil een lege lijst op; dat
            # hoort zichtbaar te zijn en niet als "geen koersen deze week"
            _LOGGER.warning(
                "Niveau %s (circuit %s) levert geen koersen op%s",
                info["naam"], niveau,
                "" if info["zeker"] else
                " — dit circuitnummer is niet geverifieerd, mogelijk klopt het niet")
    # dubbele koersen kunnen niet: een koers zit bij PCS in één circuit. Toch
    # ontdubbelen, want twee blokken van dezelfde koers is lelijker dan de
    # paar regels die het kost.
    gezien, uniek = set(), []
    for r in races:
        if r["url"] in gezien:
            continue
        gezien.add(r["url"])
        uniek.append(r)
    uniek.sort(key=lambda x: (x["start"], x["women"]))
    if any("cloudflare" in f.lower() for f in fouten):
        # zeggen wélke van de twee het is; de melding van procyclingstats
        # zelf maakt dat onderscheid niet
        diag = _bypass_diag()
        _LOGGER.warning("Cloudflare bij procyclingstats — %s", diag)
        fouten.append(diag)
        # en wat de bron werkelijk terugstuurt: een uitdaging of een
        # weigering. Eén extra verzoek, alleen als het toch al misging.
        antwoord = _pcs_antwoord_diag(_pcs_url(proef_pad))
        _LOGGER.warning("Antwoord van procyclingstats — %s", antwoord)
        fouten.append(antwoord)
    _LOGGER.debug("Kalender: %s koersen (%s)", len(uniek),
                  ", ".join(f"{n}: {a}" for n, a in telling.items()))
    return uniek, telling, fouten


def _event_stages(event: dict) -> list[dict]:
    """Etappes van een koers met datum. Eendaagse koers = 1 'etappe'."""
    race_url = event["url"]
    year = event["start"].year
    if event["start"] == event["end"]:
        return [{
            "date": event["start"], "stage_url": race_url,
            "profile_icon": "", "name": event["name"], "idx": None,
            "one_day": True, "race_url": race_url, "race_name": event["name"],
            "women": bool(event.get("women")),
            # het niveau reist mee tot in de attributen; de kaart filtert
            # er per dashboardkaart op
            "level": str(event.get("level", "")),
        }]

    from procyclingstats import Race
    out = []
    try:
        race = Race(f"{race_url}/overview")
        stages = race.stages()
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Etappelijst ophalen mislukt voor %s: %s", race_url, err)
        return out
    for i, st in enumerate(stages, 1):
        sd = st.get("date")
        if not sd:
            continue
        try:
            mm, dd = sd.split("-")
            d = date(year, int(mm), int(dd))
        except (ValueError, AttributeError):
            continue
        out.append({
            "date": d, "stage_url": st.get("stage_url"),
            "profile_icon": (st.get("profile_icon") or "").strip(),
            "name": st.get("stage_name", ""), "idx": i, "one_day": False,
            "race_url": race_url, "race_name": event["name"],
            "women": bool(event.get("women")),
            "level": str(event.get("level", "")),
        })
    return out


def _fetch_race_climbs(race_url: str) -> dict:
    """{climb_url: {length, steepness, top, km_before_finnish}} voor de hele koers."""
    from procyclingstats import RaceClimbs
    out = {}
    try:
        rc = RaceClimbs(f"{race_url}/route/climbs")
        rows = rc.climbs("climb_url", "length", "steepness", "top", "km_before_finnish")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("RaceClimbs mislukt voor %s: %s", race_url, err)
        return out
    for r in rows:
        u = r.get("climb_url")
        if u:
            out[u] = r
    return out


def _stage_obj(stage_url, one_day=False):
    """Stage-object; bij een EENDAAGSE koers staat de info op de /result-pagina."""
    from procyclingstats import Stage
    urls = [f"{stage_url}/result", stage_url] if one_day else [stage_url]
    for u in urls:
        try:
            return Stage(u)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Stage ophalen mislukt voor %s: %s", u, err)
    return None


def _secs(t):
    """'H:MM:SS' / 'MM:SS' -> seconden (None als het geen tijd is)."""
    s = str(t or "").strip().lstrip("+")
    if ":" not in s:
        return None
    try:
        p = [int(x) for x in s.split(":")]
    except ValueError:
        return None
    if len(p) == 3:
        return p[0] * 3600 + p[1] * 60 + p[2]
    if len(p) == 2:
        return p[0] * 60 + p[1]
    return None


def _move(prev, now):
    """Positieverandering t.o.v. de vorige dag (+ = gestegen, - = gedaald)."""
    p, n = _int(prev), _int(now)
    return None if p is None or n is None else p - n


def _row_names(st, table_key):
    """Rennernamen per tabelrij uit de al opgehaalde pagina.

    Het procyclingstats-pakket verzamelt alle rennerlinks van een tabel als
    een platte lijst en plakt die positioneel op de rijen, terwijl tijd en
    ploeg wel per rij worden gelezen. Bevat een rij een extra of ontbrekende
    rennerlink, dan schuiven alle namen daarna op. Daarom lezen we ze hier
    per rij. Dit kost geen extra verzoek: de HTML is al binnen.
    """
    try:
        tbl = st._table_html(table_key)   # noqa: SLF001
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Tabel-HTML (%s) niet leesbaar: %s", table_key, err)
        return []
    if tbl is None:
        return []
    body = tbl.css_first("tbody") or tbl
    names = []
    for row in body.css("tr"):
        found = []
        for a_el in row.css("a"):
            href = a_el.attributes.get("href") or ""
            if "rider" in href.split("/"):
                txt = " ".join(a_el.text().split())
                if txt:
                    found.append(txt)
        # een rennernaam is "ACHTERNAAM Voornaam"; kortere links (icoon, "view")
        # kunnen in dezelfde rij staan en mogen niet worden gekozen
        full = [t for t in found if len(t.split()) >= 2]
        names.append((full or found or [""])[0])
    return names


def _fix_names(rows, names, label=""):
    """Zet de per-rij gelezen namen terug op de rijen van het pakket."""
    if not rows or len(names) != len(rows):
        if rows and names:
            _LOGGER.debug("%s: %s namen voor %s rijen, niet gecorrigeerd",
                          label, len(names), len(rows))
        return
    fixed = 0
    for row, nm in zip(rows, names):
        if nm and nm != (row.get("rider_name") or "").strip():
            row["rider_name"] = nm
            fixed += 1
    if fixed:
        _LOGGER.debug("%s: %s scheve naam/namen gecorrigeerd", label, fixed)


def _delta_seconds(txt):
    """'+1:12' / '-0:20' / '0:00' -> seconden (+ = tijd verloren)."""
    t = (txt or "").strip().replace("\u2212", "-").replace("\u2013", "-")
    t = t.replace(" ", "")
    if not t or t in ("-", "--", "0", "..."):
        return None
    m = re.match(r"^([+-]?)(\d{1,2}):(\d{2})(?::(\d{2}))?$", t)
    if not m:
        return None
    sec = (int(m.group(2)) * 3600 + int(m.group(3)) * 60 + int(m.group(4))
           if m.group(4) else int(m.group(2)) * 60 + int(m.group(3)))
    return -sec if m.group(1) == "-" else sec


def _is_gain_header(h):
    k = (h or "").strip().lower()
    return (("won" in k and "lost" in k) or "\u03b4" in k
            or k in ("today", "+/-", "gained", "diff"))


def _delta_col(st, table_key):
    """PCS' eigen kolom met dagwinst/-verlies, per rij gelezen.

    Deze kolom wordt via de tabelkop per rij uitgelezen (zoals de ploegkolom)
    en is daarmee betrouwbaar; er hoeft geen tweede etappe te worden opgehaald
    en er hoeven geen renners op naam te worden gekoppeld.
    """
    try:
        from procyclingstats.table_parser import TableParser
        tbl = st._table_html(table_key)   # noqa: SLF001
        if tbl is None:
            return [], [], []
        tp = TableParser(tbl)
        heads = ([" ".join(h.text().split()) for h in tp.header.css("th")]
                 if tp.header is not None else [])
        for h in heads:
            if _is_gain_header(h):
                raw = tp.parse_extra_column(h, str)
                return [_delta_seconds(v) for v in raw], heads, raw[:4]
        return [], heads, []
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Dagwinst-kolom (%s) niet leesbaar: %s", table_key, err)
        return [], [], []


def _fetch_rank_maps(stage_url: str, one_day: bool = False) -> dict:
    """Klassementen van een etappe als {positie: waarde}.

    Positie, tijd en punten komen alle drie uit kolommen die per rij worden
    gelezen. Door op positie te koppelen hoeven er geen renners op naam te
    worden gematcht - precies de kolom die bij PCS kan verschuiven.
    """
    st = _stage_obj(stage_url, one_day)
    if st is None:
        return {}

    def _m(fn, key):
        rows = _safe(lambda: fn("rank", key), []) or []
        out = {}
        for r in rows:
            rk = _int(r.get("rank"))
            if rk is not None and r.get(key) not in (None, ""):
                out[rk] = r.get(key)
        return out

    return {"gc": _m(st.gc, "time"), "youth": _m(st.youth, "time"),
            "points": _m(st.points, "points"), "kom": _m(st.kom, "points")}


def _gain_time_by_rank(rows, prev_map):
    """Tijdwinst/-verlies van de laatste dag t.o.v. de leider (+ = verloren)."""
    if not rows or not prev_map:
        return 0
    ln, lp = _secs(rows[0].get("time")), _secs(prev_map.get(rows[0].get("prev")))
    if ln is None or lp is None:
        return 0
    n = 0
    for row in rows:
        if row.get("gain_s") is not None:
            continue
        now, pv = _secs(row.get("time")), _secs(prev_map.get(row.get("prev")))
        if now is None or pv is None:
            continue
        row["gain_s"] = (now - ln) - (pv - lp)
        n += 1
    return n


def _gain_pts_by_rank(rows, prev_map):
    """Punten gepakt op de laatste dag."""
    if not rows or not prev_map:
        return 0
    n = 0
    for row in rows:
        now, pv = _int(row.get("points")), _int(prev_map.get(row.get("prev")))
        if now is not None and pv is not None:
            row["gain"] = now - pv
            n += 1
    return n


def _fetch_startlist(race_url):
    """De startlijst van een koers: renner, ploeg en hun adressen.

    De startlijst is per ploegblok opgebouwd (de ploegnaam komt uit de kop van
    het blok), dus de koppeling renner→ploeg kan hier niet verschuiven zoals in
    de klassementstabellen.

    Levert de rijen zoals de pagina ze geeft; wie alleen renner→ploeg nodig
    heeft gebruikt `_roster_van`.
    """
    from procyclingstats import RaceStartlist
    try:
        rows = RaceStartlist(f"{race_url}/startlist").startlist(
            "rider_name", "rider_url", "team_name", "team_url")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Startlijst ophalen mislukt: %s", err)
        return []
    out = []
    for r in rows or []:
        naam = (r.get("rider_name") or "").strip()
        if not naam:
            continue
        out.append({
            "rider": naam,
            "rider_url": (r.get("rider_url") or "").strip(),
            "team": (r.get("team_name") or "").strip(),
            "team_url": (r.get("team_url") or "").strip(),
        })
    _LOGGER.debug("Startlijst %s: %s renners", race_url, len(out))
    return out


def _roster_van(rows):
    """Renner -> ploeg uit de startlijstrijen, met een naamsleutel."""
    out = {}
    for r in rows or []:
        nm, tm = _name_key(r.get("rider")), (r.get("team") or "").strip()
        if nm and tm:
            out[nm] = tm
    return out


def _fetch_ranking(url):
    """De PCS-ranglijst als {renneradres: (positie, punten)}.

    Het adres van een renner is een vaste sleutel; daarmee is de startlijst
    aan de ranglijst te koppelen zonder namen te vergelijken — precies de
    valkuil die elders in dit bestand al zoveel tijd heeft gekost.
    """
    from procyclingstats import Ranking
    try:
        rows = Ranking(url).individual_ranking(
            "rank", "rider_url", "points")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Ranglijst %s ophalen mislukt: %s", url, err)
        return {}
    out = {}
    for r in rows or []:
        adres = (r.get("rider_url") or "").strip()
        positie = _int(r.get("rank"))
        if adres and positie:
            # de punten staan bij PCS als heel getal; afronden houdt ze uit
            # de attributen als "2981.0"
            out[adres] = (positie, _int(r.get("points")))
    if not out:
        _LOGGER.warning(
            "Ranglijst %s levert geen renners op%s", url,
            "" if url in RANGLIJST_ZEKER else " (adres niet geverifieerd)")
    else:
        _LOGGER.debug("Ranglijst %s: %s renners", url, len(out))
    return out


def _start_top(rows, ranking, n):
    """De hoogst geklasseerde renners van een startlijst.

    De volgorde komt van de PCS-ranglijst en nergens anders vandaan: een
    renner die daar niet op staat krijgt geen plek naar schatting, hij valt
    weg. Staat er niemand van de startlijst op de ranglijst, dan is de lijst
    leeg en laat de kaart hem weg.
    """
    if not rows or not ranking:
        return []
    gevonden = []
    for r in rows:
        plek = ranking.get(r.get("rider_url"))
        if plek:
            gevonden.append((plek[0], plek[1], r))
    gevonden.sort(key=lambda g: g[0])
    return [{"rank": positie, "rider": r["rider"], "team": r["team"],
             "points": punten}
            for positie, punten, r in gevonden[:max(0, n)]]


def _fetch_team_abbr(team_url):
    """De officiële ploegcode van de ploegpagina bij procyclingstats.

    Komt van de bron: er wordt niets uit de naam afgeleid. Een verzonnen
    afkorting lijkt op een UCI-ploegcode zonder het te zijn, en dat is
    precies wat dit project niet doet. Geeft "" als de pagina geen
    bruikbare code noemt; dan blijft de volledige naam staan.
    """
    from procyclingstats import Team

    try:
        code = (_safe(Team(team_url).abbreviation, "") or "").strip().upper()
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Ploegcode ophalen mislukt voor %s: %s", team_url, err)
        return ""
    # een code is kort en bestaat uit letters/cijfers; alles daarbuiten is
    # iets anders (de volledige naam, een leeg veld, HTML-ruis)
    if not re.match(r"^[A-Z0-9]{2,4}$", code):
        if code:
            _LOGGER.debug("Ploegcode van %s onbruikbaar: %r", team_url, code)
        return ""
    return code


def _name_key(s):
    """Naamsleutel die niet afhangt van de volgorde van voor- en achternaam."""
    parts = [p for p in (_slug_norm(w) for w in re.split(r"[\s,]+", s or "")) if p]
    return "|".join(sorted(parts))


def _repair_rows(rows, roster, name_key="rider", team_key="team"):
    """Zet namen terug op de juiste rij aan de hand van de ploegkolom.

    Ploeg en tijd worden per rij gelezen en zijn betrouwbaar; de namen komen
    uit een tabelbrede lijst en kunnen verschoven staan. Hoort de ploeg van
    een rij niet bij de genoemde renner, dan zoeken we welke renner er volgens
    de startlijst wel bij die ploeg hoort.
    """
    if not rows or not roster:
        return 0
    verdacht = []
    for i, row in enumerate(rows):
        echt = roster.get(_name_key(row.get(name_key)))
        if echt and _slug_norm(echt) != _slug_norm(row.get(team_key)):
            verdacht.append(i)
    if not verdacht:
        return 0
    namen = [rows[i].get(name_key) for i in verdacht]
    gebruikt, hersteld = set(), 0
    for i in verdacht:
        wil = _slug_norm(rows[i].get(team_key))
        for nm in namen:
            if nm in gebruikt:
                continue
            if _slug_norm(roster.get(_name_key(nm), "")) == wil:
                if nm != rows[i].get(name_key):
                    _LOGGER.debug("Naam hersteld: %s -> %s (%s)",
                                  rows[i].get(name_key), nm, rows[i].get(team_key))
                    rows[i][name_key] = nm
                    hersteld += 1
                gebruikt.add(nm)
                break
    return hersteld


def _fetch_stage(stage_url: str, one_day: bool = False,
                 result_n: int = DEFAULT_RESULT_N,
                 gc_n: int = DEFAULT_GC_N) -> dict:
    """Alle relevante velden uit één Stage-pagina (meta + cols + uitslag + klassement)."""

    data = {
        "ok": False, "finished": False,
        "departure": "", "arrival": "", "distance": None, "vertical": None,
        "profile_icon": "", "profile_score": None, "stage_type": "",
        "start_time": "", "climbs_raw": [],
        "results": [], "gc": [], "points_leader": "", "kom_leader": "",
        "youth_leader": "", "points_top": [], "kom_top": [], "youth_top": [],
        "startlist_quality": None,
    }
    if not stage_url:
        return data
    st = _stage_obj(stage_url, one_day)
    if st is None:
        return data

    data["ok"] = True
    data["departure"] = _safe(st.departure, "") or ""
    data["arrival"] = _safe(st.arrival, "") or ""
    data["distance"] = _num(_safe(st.distance))
    data["vertical"] = _int(_safe(st.vertical_meters))
    data["profile_icon"] = (_safe(st.profile_icon, "") or "").strip()
    data["profile_score"] = _int(_safe(st.profile_score))
    data["stage_type"] = _safe(st.stage_type, "") or ""
    data["startlist_quality"] = _quality(st)
    data["start_time"] = _safe(st.start_time, "") or ""
    data["climbs_raw"] = _safe(
        lambda: st.climbs("climb_name", "climb_url", "category"), []) or []

    # adres van de ploegpagina per ploegnaam. Blijft binnen deze functie en
    # gaat níét mee in de rijen: de coordinator zoekt er de ploegcode mee op,
    # en in de attributen zou het alleen ruimte kosten.
    team_urls: dict[str, str] = {}

    def _onthoud_ploeg(r):
        naam = (r.get("team_name") or "").strip()
        adres = (r.get("team_url") or "").strip()
        if naam and adres and naam not in team_urls:
            team_urls[naam] = adres

    results = _safe(lambda: st.results(
        "rank", "rider_name", "team_name", "team_url", "time", "status"), []) or []
    if not results:   # oudere pagina zonder ploeglink
        results = _safe(
            lambda: st.results("rank", "rider_name", "team_name", "time", "status"), []) or []
    _fix_names(results, _row_names(st, "stage"), "uitslag")
    clean = []
    for r in results:
        if r.get("rank") in (None, "") or r.get("status") not in (None, "DF", ""):
            continue
        _onthoud_ploeg(r)
        clean.append({
            "rank": r.get("rank"),
            "rider": (r.get("rider_name") or "").strip(),
            "team": (r.get("team_name") or "").strip(),
            "time": r.get("time") or "",
        })
        if len(clean) >= result_n:
            break
    data["results"] = clean
    data["finished"] = bool(clean)

    gc = _safe(lambda: st.gc(
        "rank", "rider_name", "team_name", "team_url", "time", "prev_rank"), []) or []
    if not gc:
        gc = _safe(lambda: st.gc(
            "rank", "rider_name", "team_name", "time", "prev_rank"), []) or []
    if not gc:
        gc = _safe(lambda: st.gc("rank", "rider_name", "team_name", "time"), []) or []
    _fix_names(gc, _row_names(st, "gc"), "klassement")
    for _g in gc:
        _onthoud_ploeg(_g)
    data["gc"] = [{
        "rank": g.get("rank"),
        "rider": (g.get("rider_name") or "").strip(),
        "team": (g.get("team_name") or "").strip(),
        "time": g.get("time") or "",
        "move": _move(g.get("prev_rank"), g.get("rank")),
        "prev": _int(g.get("prev_rank")),
    } for g in gc[:gc_n]]
    _dg, _dh, _draw = _delta_col(st, "gc")
    data["gain_headers"] = _dh
    data["gain_raw"] = _draw
    for _row, _d in zip(data["gc"], _dg):
        if _d is not None:
            _row["gain_s"] = _d

    def _leader(fn):
        rows = _safe(lambda: fn("rank", "rider_name"), []) or []
        for r in rows:
            if r.get("rank") in (1, "1"):
                return (r.get("rider_name") or "").strip()
        return (rows[0].get("rider_name").strip() if rows else "")

    data["points_leader"] = _leader(st.points)
    data["kom_leader"] = _leader(st.kom)
    data["youth_leader"] = _leader(st.youth)

    def _standings(fn, table_key, n=5):
        rows = _safe(lambda: fn(
            "rank", "rider_name", "team_name", "team_url", "points", "prev_rank"), []) or []
        if not rows:
            rows = _safe(lambda: fn(
                "rank", "rider_name", "team_name", "points", "prev_rank"), []) or []
        if not rows:
            rows = _safe(lambda: fn("rank", "rider_name", "team_name", "points"), []) or []
        if not rows:
            rows = _safe(lambda: fn("rank", "rider_name", "team_name"), []) or []
        _fix_names(rows, _row_names(st, table_key), table_key)
        out = []
        for r in rows:
            rider = (r.get("rider_name") or "").strip()
            if not rider:
                continue
            _onthoud_ploeg(r)
            out.append({"rank": r.get("rank"), "rider": rider,
                        "team": (r.get("team_name") or "").strip(),
                        "points": r.get("points"),
                        "move": _move(r.get("prev_rank"), r.get("rank")),
                        "prev": _int(r.get("prev_rank"))})
            if len(out) >= n:
                break
        return out

    data["points_top"] = _standings(st.points, "points")
    data["kom_top"] = _standings(st.kom, "kom")

    youth = _safe(lambda: st.youth(
        "rank", "rider_name", "team_name", "team_url", "time", "prev_rank"), []) or []
    if not youth:
        youth = _safe(lambda: st.youth(
            "rank", "rider_name", "team_name", "time", "prev_rank"), []) or []
    if not youth:
        youth = _safe(lambda: st.youth("rank", "rider_name", "team_name", "time"), []) or []
    _fix_names(youth, _row_names(st, "youth"), "jongeren")
    for _y in youth:
        _onthoud_ploeg(_y)
    data["youth_top"] = [{
        "rank": g.get("rank"),
        "rider": (g.get("rider_name") or "").strip(),
        "team": (g.get("team_name") or "").strip(),
        "time": g.get("time") or "",
        "move": _move(g.get("prev_rank"), g.get("rank")),
        "prev": _int(g.get("prev_rank")),
    } for g in youth[:5]]
    for _row, _d in zip(data["youth_top"], _delta_col(st, "youth")[0]):
        if _d is not None:
            _row["gain_s"] = _d
    data["team_urls"] = team_urls
    return data


def _build_climbs(stage_data: dict, race_climbs: dict) -> list[dict]:
    """Join stage-cols (naam/categorie) met de koersbrede col-details (km/lengte/%/top)."""
    out = []
    for c in stage_data.get("climbs_raw", []):
        det = race_climbs.get(c.get("climb_url"), {})
        top = _int(det.get("top"))
        if top is None:
            continue  # zonder hoogte/positie kunnen we 'm niet plaatsen
        out.append({
            "name": (c.get("climb_name") or "").strip(),
            "category": str(c.get("category", "")).upper(),
            "km_to_finish": _num(det.get("km_before_finnish")),
            "top_m": top,
            "length_km": _num(det.get("length")),
            "steepness_pct": _num(det.get("steepness")),
        })
    return out


# ──────────────────────────────────────────────────────────────
# Coordinator
# ──────────────────────────────────────────────────────────────



def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _show_state_for(sd: date, today: date) -> str:
    if sd == today:
        return "Vandaag"
    if sd == today + timedelta(days=1):
        return "Morgen"
    return f"{DAYS_NL[sd.weekday()]} {_fmt_nl(sd)}"


def _quality(st):
    """Startlijstkwaliteit; PCS geeft (bij aanvang, na de huidige etappe)."""
    v = _safe(st.race_startlist_quality_score)
    if isinstance(v, (tuple, list)):
        v = v[-1] if v else None
    return _int(v)


def _fetch_stage_meta(stage_url: str, one_day: bool = False) -> dict:
    """Lichte meta-fetch (dep/arr/afstand/hm/score). Eendaagse: info op /result."""
    d = {"ok": False, "departure": "", "arrival": "",
         "distance": None, "vertical": None, "profile_score": None}
    if not stage_url:
        return d
    st = _stage_obj(stage_url, one_day)
    if st is None:
        return d
    d["ok"] = True
    d["departure"] = _safe(st.departure, "") or ""
    d["arrival"] = _safe(st.arrival, "") or ""
    d["distance"] = _num(_safe(st.distance))
    d["vertical"] = _int(_safe(st.vertical_meters))
    d["profile_score"] = _int(_safe(st.profile_score))
    d["stage_type"] = _safe(st.stage_type, "") or ""
    d["startlist_quality"] = _quality(st)
    # starttijd hoort bij de lichte fetch: de koersen in de pop-up tekenen
    # hun profiel uit `upcoming` en anders staat daar geen tijd op
    d["start_time"] = _safe(st.start_time, "") or ""
    return d


def _fetch_stage_climbs(stage_url: str, race_climbs: dict) -> list[dict]:
    """Cols van een etappe uit de ROUTE (voor de rit beschikbaar)."""
    from procyclingstats import RaceClimbs, Stage
    rows = []
    try:
        rc = RaceClimbs(f"{stage_url}/route/climbs")
        rows = rc.climbs("climb_name", "climb_url", "length",
                         "steepness", "top", "km_before_finnish")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Per-etappe climbs mislukt voor %s: %s", stage_url, err)
        rows = []

    if not rows:
        lst = None
        try:
            st = Stage(stage_url)
            lst = st._find_header_list("Climbs")  # noqa: SLF001
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Stage climbs-lijst mislukt voor %s: %s", stage_url, err)
        if lst is not None:
            for li in lst.css("li"):
                a = li.css_first("a")
                url = a.attributes.get("href") if a else None
                det = race_climbs.get(url) if url else None
                if det:
                    rows.append({"climb_name": a.text(strip=True),
                                 "climb_url": url, **det})

    out = []
    for r in rows:
        top = _int(r.get("top"))
        if not top or top <= 0:
            continue  # ongeldige/ontbrekende hoogte (bv. kapotte aankomst-bergop-data)
        out.append({
            "name": (r.get("climb_name") or "").strip(),
            "category": "",
            "km_to_finish": _num(r.get("km_before_finnish")),
            "top_m": top,
            "length_km": _num(r.get("length")),
            "steepness_pct": _num(r.get("steepness")),
        })
    out.sort(key=lambda c: (c["km_to_finish"] if c["km_to_finish"] is not None else -1),
             reverse=True)
    _LOGGER.debug("Cols voor %s: %d gevonden", stage_url, len(out))
    return out


def _merge_categories(climbs: list[dict], kom_raw: list[dict]) -> None:
    """Vul categorie (HC/1/2/3/4) uit de KOM-uitslag zodra beschikbaar."""
    kom = {}
    for c in kom_raw or []:
        nm = _norm(c.get("climb_name"))
        cat = str(c.get("category") or "").upper()
        if nm and cat:
            kom[nm] = cat
    for c in climbs:
        cat = kom.get(_norm(c.get("name")))
        if cat:
            c["category"] = cat


def _enrich_names(detected: list, named: list) -> None:
    """Zet PCS-naam + officiele categorie op de dichtstbijzijnde gedetecteerde klim."""
    for d in detected:
        dk = d.get("km_to_finish") or 0
        best, bestdiff = None, 6.0
        for p in named or []:
            pk = p.get("km_to_finish")
            if pk is None:
                continue
            diff = abs(pk - dk)
            if diff < bestdiff:
                bestdiff, best = diff, p
        if best:
            if best.get("name"):
                d["name"] = best["name"]
            if best.get("category"):
                d["category"] = best["category"]


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


# Etappe-artikelen op cyclingstage (colnamen + verwachte finishtijd).
# De adressen volgen geen vast patroon, dus per koers een sjabloon.
CYCLINGSTAGE_ROUTE = {
    "tour-de-france":
        "https://www.cyclingstage.com/tour-de-france-{y}-route/stage-{n}-tdf-{y}/",
    # Let op: het achtervoegsel is het land, niet de koers - "stage-5-italy-2026"
    # en "stage-3-spain-2026", niet "stage-5-giro-2026". Nagekeken op de
    # koerspagina's van cyclingstage (2025 en 2026); alleen de Tour gebruikt
    # zijn eigen afkorting.
    "giro-d-italia":
        "https://www.cyclingstage.com/giro-{y}-route/stage-{n}-italy-{y}/",
    "vuelta-a-espana":
        "https://www.cyclingstage.com/vuelta-{y}-route/stage-{n}-spain-{y}/",
    # vrouwen (adressen geverifieerd op cyclingstage)
    "tour-de-france-femmes":
        "https://www.cyclingstage.com/tour-de-france-femmes-{y}/stage-{n}-tdf-{y}-women/",
    "giro-d-italia-women":
        "https://www.cyclingstage.com/giro-women-{y}/stage-{n}-route-ita-{y}/",
}

_CLIMB_KW = (r"(?:Grand |Petit |Haut[e]? |Mont )?(?:Col|Côte|Cote|Mur|Ballon|"
             r"Cormet|Montée|Montee|Alpe|Puy|Port|Puerto|Colle|Passo|Cima|"
             r"Monte|Alto|Collada|Hourquette|Croix|Cabane)\b")
_CLIMB_NAME = _CLIMB_KW + (r"(?:(?:[ ]d['’]| du | de la | de l['’]| des | de "
                           r"| di | della | del )[A-ZÀ-Ü][\w'’à-ÿ\-]+"
                           r"(?:[ -][A-ZÀ-Ü][\w'’à-ÿ\-]+){0,2})?")
_BARE_CLIMB = {"col", "côte", "cote", "mur", "ballon", "cormet", "montée", "montee",
               "alpe", "puy", "port", "puerto", "colle", "passo", "cima", "monte",
               "alto", "collada", "hourquette", "croix", "cabane"}


def _stage_article_url(race_url, stage_idx, one_day):
    m = re.match(r"race/([^/]+)/(\d{4})", race_url or "")
    if not m or one_day or not stage_idx:
        return None
    sjabloon = CYCLINGSTAGE_ROUTE.get(m.group(1))
    if not sjabloon:
        return None
    return sjabloon.format(y=m.group(2), n=stage_idx)


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


def _fetch_live(stage_url):
    """KM-to-go + status van de PCS live-pagina (spoilervrij: alleen de kop van de koers).

    Let op: PCS werkt deze waarden mogelijk via JavaScript bij; dan bevat de kale HTML
    de pre-race stand. De aanroeper toont daarom alleen iets als km-to-go < afstand.
    """
    if not stage_url:
        return {}
    import urllib.request
    url = f"https://www.procyclingstats.com/{stage_url}/live"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = resp.read().decode("utf-8", "replace")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Live ophalen mislukt %s: %s", url, err)
        return {}
    text = re.sub(r"[ \t\r\n\u00a0]+", " ", re.sub(r"<[^>]+>", " ", doc))
    out = {}
    for key, pat in (("km_to_go", r"KM to go\s+([\d.]+)"),
                     ("km_done", r"km done\s+([\d.]+)"),
                     ("avg_speed", r"Avg\.\s+([\d.]+)")):
        m = re.search(pat, text)
        if m:
            out[key] = float(m.group(1))
    m = re.search(r"Status\s+([A-Za-z]+)", text)
    if m:
        out["status"] = m.group(1).lower()
    _LOGGER.debug("Live %s: %s", url, out)
    return out


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


CYCLINGSTAGE_SLUG = {
    "tour-de-france": "tour-de-france",
    "giro-d-italia": "giro",
    "vuelta-a-espana": "vuelta",
}

# De drie grote rondes. Ze duren drie weken en zijn in die periode de koers
# waar het om gaat; een tegel die tijdens de Vuelta de Renewi Tour laat zien
# klopt niet, ook al heeft die toevallig wél een hoogteprofiel. Een vaste
# lijst van drie koersen en geen weging of score - er valt niets aan te
# schatten. De rondes van een week bij de vrouwen (Tour de France Femmes,
# Giro Women, Vuelta Femenina) staan er bewust niet in: dat zijn geen grote
# rondes, en wie ze toch voor wil laten gaan verandert de volgorde en niet
# deze lijst.
GROTE_RONDES = {"tour-de-france", "giro-d-italia", "vuelta-a-espana"}


def _is_grote_ronde(race_url: str) -> bool:
    m = re.match(r"race/([^/]+)/", race_url or "")
    return bool(m) and m.group(1) in GROTE_RONDES

# Overige rittenkoersen op cyclingstage. Let op: deze gebruiken
# "stage-{N}-route.gpx" in plaats van "stage-{N}-parcours.gpx".
# (PCS-slug -> cyclingstage-CDN-slug)
CYCLINGSTAGE_STAGERACE = {
    "tour-down-under": "tour-down-under",
    "volta-a-la-comunitat-valenciana": "tour-of-valencia",
    "uae-tour": "uae-tour",
    "ruta-del-sol": "ruta-del-sol",
    "volta-ao-algarve": "volta-ao-algarve",
    "paris-nice": "paris-nice",
    "tirreno-adriatico": "tirreno-adriatico",
    "volta-a-catalunya": "volta-a-catalunya",
    "itzulia-basque-country": "tour-of-the-basque-country",
    "o-gran-camino": "o-gran-camino",
    "tour-of-the-alps": "tour-of-the-alps",
    "tour-de-romandie": "tour-de-romandie",
    "dauphine": "criterium-du-dauphine",
    "tour-de-suisse": "tour-de-suisse",
    "renewi-tour": "renewi-tour",
    "tour-of-britain": "tour-of-britain",
    # vrouwen (bevestigd: .../tour-de-france-femmes/2026/stage-1-route.gpx)
    "tour-de-france-femmes": "tour-de-france-femmes",
    "giro-d-italia-women": "giro-women",
    "vuelta-espana-femenina": "vuelta-femenina",
    "uae-tour-women": "uae-tour-women",
    "itzulia-women": "itzulia-women",
    "tour-de-suisse-women": "tour-de-suisse-women",
}

# Eendaagse koersen: cyclingstage-GPX = .../{slug}/{jaar}/route.gpx
# (PCS-slug -> cyclingstage CDN-slug; uitbreidbaar)
CYCLINGSTAGE_ONEDAY = {
    # PCS-slug -> kandidaat-namen op de cyclingstage-CDN (eerste die werkt wint).
    # De CDN-naam volgt doorgaans exact de paginanaam, bv. de pagina
    # "clasica-de-san-sebastian-2026" hoort bij ".../clasica-de-san-sebastian/2026/".
    "omloop-het-nieuwsblad": ("omloop-het-nieuwsblad",),
    "kuurne-brussels-kuurne": ("kuurne-brussels-kuurne",),
    "strade-bianche": ("strade-bianche",),
    "milano-sanremo": ("milan-san-remo",),
    "e3-harelbeke": ("e3-saxo-classic",),
    "gent-wevelgem": ("gent-wevelgem", "in-flanders-fields"),
    "dwars-door-vlaanderen": ("dwars-door-vlaanderen",),
    "ronde-van-vlaanderen": ("tour-of-flanders",),
    "paris-roubaix": ("paris-roubaix",),
    "brabantse-pijl": ("brabantse-pijl",),
    "amstel-gold-race": ("amstel-gold-race",),
    "la-fleche-wallonne": ("la-fleche-wallonne", "fleche-wallonne"),
    "liege-bastogne-liege": ("liege-bastogne-liege",),
    "san-sebastian": ("clasica-san-sebastian", "clasica-de-san-sebastian"),
    "bretagne-classic-ouest-france": ("bretagne-classic",),
    "gp-quebec": ("gp-quebec",),
    "gp-montreal": ("gp-montreal",),
    "il-lombardia": ("tour-of-lombardy", "il-lombardia"),
    "paris-tours": ("paris-tours",),
    # vrouwen: cyclingstage gebruikt eigen paginanamen, dus meerdere kandidaten
    "strade-bianche-donne": ("strade-bianche-donne",),
    "milano-sanremo-we": ("milano-san-remo-donne", "milan-san-remo-women"),
    "gent-wevelgem-women-elite": ("in-flanders-fields-women", "gent-wevelgem-women"),
    "ronde-van-vlaanderen-we": ("tour-of-flanders-women",),
    "paris-roubaix-we": ("paris-roubaix-femmes",),
    "amstel-gold-race-we": ("amstel-gold-race-women",),
    "la-fleche-wallonne-feminine": ("la-fleche-wallonne-femmes",),
    "liege-bastogne-liege-femmes": ("liege-bastogne-liege-femmes",),
    "omloop-het-nieuwsblad-we": ("omloop-het-nieuwsblad-women",),
}


def _gpx_urls(race_url: str, stage_idx, one_day: bool) -> list[str]:
    """Kandidaat-GPX-adressen op cyclingstage, op volgorde van waarschijnlijkheid.

    Grote rondes gebruiken "stage-{N}-parcours.gpx", de overige rittenkoersen
    "stage-{N}-route.gpx". Er zit ook een enkele afwijking in ("etappe-5-route"),
    dus we proberen meerdere varianten.
    """
    m = re.match(r"race/([^/]+)/(\d{4})", race_url or "")
    if not m:
        return []
    slug, year = m.group(1), m.group(2)
    eigen = GPX_OVERRIDE.get(f"{slug}/{year}/{stage_idx}") if stage_idx else None
    eigen = eigen or GPX_OVERRIDE.get(f"{slug}/{year}")
    voor = [eigen] if eigen else []
    basis = f"https://cdn.cyclingstage.com/images/{{}}/{year}"
    if one_day:
        namen = CYCLINGSTAGE_ONEDAY.get(slug) or ()
        if isinstance(namen, str):
            namen = (namen,)
        uit = []
        for cs in namen:
            uit.append(f"{basis.format(cs)}/route.gpx")
            uit.append(f"{basis.format(cs)}/parcours.gpx")
        return voor + uit
    if not stage_idx:
        return voor
    cs = CYCLINGSTAGE_SLUG.get(slug)
    if cs:
        return voor + [f"{basis.format(cs)}/stage-{stage_idx}-parcours.gpx",
                       f"{basis.format(cs)}/stage-{stage_idx}-route.gpx"]
    cs = CYCLINGSTAGE_STAGERACE.get(slug)
    if not cs:
        return voor
    return voor + [f"{basis.format(cs)}/stage-{stage_idx}-route.gpx",
            f"{basis.format(cs)}/stage-{stage_idx}-parcours.gpx",
            f"{basis.format(cs)}/etappe-{stage_idx}-route.gpx"]


# Overzichtspagina met de GPX-bestanden van één koers, bv.
# ".../vuelta-2026-gpx/". De naam volgt de cyclingstage-slug hierboven;
# nagekeken voor de Tour, de Giro en de Vuelta.
CYCLINGSTAGE_GPX_INDEX = "https://www.cyclingstage.com/{cs}-{y}-gpx/"

_GPX_HREF = re.compile(r'href=["\']([^"\']+\.gpx)["\']', re.I)
_GPX_NUMMER = re.compile(r"(?:stage|etappe|rit)[-_]?0*(\d{1,2})(?:\D|$)", re.I)


def _gpx_index_urls(race_url: str) -> list[str]:
    """Overzichtspagina's van cyclingstage met de GPX-links van deze koers."""
    m = re.match(r"race/([^/]+)/(\d{4})", race_url or "")
    if not m:
        return []
    slug, year = m.group(1), m.group(2)
    cs = CYCLINGSTAGE_SLUG.get(slug) or CYCLINGSTAGE_STAGERACE.get(slug)
    namen = (cs,) if cs else (CYCLINGSTAGE_ONEDAY.get(slug) or ())
    if isinstance(namen, str):
        namen = (namen,)
    return [CYCLINGSTAGE_GPX_INDEX.format(cs=n, y=year) for n in namen]


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


def _fetch_gpx_index(race_url: str) -> dict:
    """{etappenummer: gpx-adres} zoals cyclingstage ze zelf op een rij zet.

    Terugval voor als geen van de vaste adressen uit `_gpx_urls` iets
    oplevert. Die adressen zijn een aanname over de bestandsnaam; deze
    pagina noemt het echte adres, dus hier wordt niets geraden.
    """
    import urllib.request
    for index_url in _gpx_index_urls(race_url):
        try:
            req = urllib.request.Request(
                index_url,
                headers={"User-Agent": "Mozilla/5.0 (HomeAssistant CyclingNextRace)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("GPX-overzicht ophalen mislukt (%s): %s", index_url, err)
            continue
        year = re.search(r"(\d{4})", race_url or "")
        index = _parse_gpx_index(html, index_url, year.group(1) if year else "")
        if index:
            _LOGGER.debug("GPX-overzicht %s: %s etappes", index_url, len(index))
            return index
        _LOGGER.debug("GPX-overzicht %s: geen .gpx-links gevonden", index_url)
    return {}


def _times_urls(race_url, stage_idx, one_day):
    """Tijdschema-pagina's van cyclingstage (bevatten o.a. de tussensprint).

    Geldt voor alle rittenkoersen die cyclingstage dekt - grote rondes,
    de overige rittenkoersen en de vrouwenkoersen.
    """
    m = re.match(r"race/([^/]+)/(\d{4})", race_url or "")
    if not m or one_day or not stage_idx:
        return []
    slug, year = m.group(1), m.group(2)
    cs = CYCLINGSTAGE_SLUG.get(slug) or CYCLINGSTAGE_STAGERACE.get(slug)
    if not cs:
        return []
    basis = f"https://www.cyclingstage.com/images/{cs}/{year}"
    return [f"{basis}/stage-{stage_idx}-times.htm",
            f"{basis}/etappe-{stage_idx}-times.htm"]


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


def _fetch_times(race_url, stage_idx, one_day):
    """Tussensprint(s) van de etappe; lege lijst als er geen tijdschema is."""
    import urllib.request
    for url in _times_urls(race_url, stage_idx, one_day):
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
            _LOGGER.debug("Tussensprint(s) etappe %s: %s km te gaan", stage_idx, sp)
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
        self._climbs_cache: dict[str, dict] = {}
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
        # de startlijst per koers, zoals procyclingstats hem geeft. Dient twee
        # doelen: renner→ploeg om scheve namen te herstellen (`_roster_van`),
        # en de renners aan de start zolang er nog geen uitslag is.
        self._startlist_cache: dict[str, list] = {}
        # de individuele ranglijst per adres uit RANGLIJST; die verandert
        # hoogstens één keer per dag en bedient alle koersen samen
        self._ranking_cache: dict[str, dict] = {}
        # wat er van de laatste startlijst terechtkwam; gaat als
        # `startlist_diag` naar de attributen
        self._startlist_diag: dict = {}
        # uitslag per etappe van de andere koersen, op stage_url; per dag geleegd
        self._other_cache: dict[str, dict] = {}
        self._prevrank_cache: dict[str, dict] = {}
        self._names_cache: dict[str, list] = {}
        self._prose_cache: dict[str, list] = {}
        # ploegnaam -> officiële code. Blijft een seizoen lang gelijk, dus
        # alleen bij een nieuwe kalenderdag opnieuw; een mislukte poging
        # staat als "" in de cache en wordt dan morgen weer geprobeerd.
        self._abbr_cache: dict[str, str] = {}
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

    async def _ploegcodes(self, data: dict, sleutels=(
            "results", "gc", "points_top", "kom_top", "youth_top")) -> None:
        """Zet de officiële ploegcode op elke rij, waar PCS hem geeft.

        De code komt van de ploegpagina bij procyclingstats; er wordt niets
        uit de naam afgeleid. Per ronde worden er hoogstens
        `MAX_PLOEGCODES_PER_RONDE` nieuwe opgehaald — een koers telt zo'n
        twintig ploegen en elke code is een eigen pagina. Wat nog niet
        bekend is houdt de volledige ploegnaam en volgt de volgende ronde.

        `sleutels` zegt welke lijsten in `data` rijen bevatten; de startlijst
        gebruikt dezelfde weg met een eigen sleutel.
        """
        adressen = data.get("team_urls") or {}
        nieuw = 0
        for sleutel in sleutels:
            for row in data.get(sleutel) or []:
                naam = (row.get("team") or "").strip()
                if not naam:
                    continue
                code = self._abbr_cache.get(naam)
                if (code is None and naam in adressen
                        and nieuw < MAX_PLOEGCODES_PER_RONDE):
                    await asyncio.sleep(0.3)   # niet overspoelen
                    code = await self._job(_fetch_team_abbr, adressen[naam])
                    self._abbr_cache[naam] = code
                    nieuw += 1
                if code:
                    row["team_code"] = code
        if nieuw:
            _LOGGER.debug("%s ploegcodes opgehaald (%s bekend)",
                          nieuw, len(self._abbr_cache))

    async def _startlijst(self, race_url: str) -> list:
        """De startlijst van een koers, per koers bewaard.

        Slikt zijn eigen fouten: hij wordt ook voor de koersen in de pop-up
        opgevraagd, en daar zou een mislukte scrape anders het hele blok
        kosten.
        """
        if race_url in self._startlist_cache:
            return self._startlist_cache[race_url]
        try:
            rows = await self._job(_fetch_startlist, race_url)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Startlijst mislukt voor %s: %s", race_url, err)
            return []
        if rows:
            self._startlist_cache[race_url] = rows
        return rows

    async def _ranglijst(self, women: bool) -> dict:
        """De individuele PCS-ranglijst, één keer per dag per geslacht.

        Ook een mislukte poging blijft in de cache staan, net als bij de
        ploegcodes: klopt het adres niet, dan zou hij anders elke ronde
        opnieuw worden opgehaald en elke ronde dezelfde waarschuwing loggen.
        Morgen wordt het weer geprobeerd; de startlijst is intussen het enige
        dat mist.
        """
        url = RANGLIJST[bool(women)]
        if url in self._ranking_cache:
            return self._ranking_cache[url]
        try:
            ranking = await self._job(_fetch_ranking, url)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Ranglijst %s mislukt: %s", url, err)
            ranking = {}
        self._ranking_cache[url] = ranking
        return ranking

    async def _startlijst_blok(self, race_url: str, women: bool) -> dict:
        """Wie er aan de start staan, voor een koers zonder uitslag.

        `startlist_top` is de kop van de startlijst volgens de PCS-ranglijst;
        `startlist_riders` en `startlist_teams` zijn wat er geteld is. Levert
        de startlijst niets op, dan blijft alles leeg en laat de kaart het
        onderdeel weg.
        """
        leeg = {"startlist_top": [], "startlist_riders": 0, "startlist_teams": 0}
        rows = await self._startlijst(race_url)
        if not rows:
            return leeg
        ranking = await self._ranglijst(women)
        top = _start_top(rows, ranking, self._opt(CONF_START_N))
        if top:
            # dezelfde ploegcodes als in de uitslag; de adressen staan op de
            # startlijst zelf
            adressen = {r["team"]: r["team_url"] for r in rows
                        if r.get("team") and r.get("team_url")}
            await self._ploegcodes({"team_urls": adressen,
                                    "startlist_top": top}, ("startlist_top",))
        self._startlist_diag = {
            "koers": _race_slug(race_url),
            "ranglijst": RANGLIJST[bool(women)],
            "renners": len(rows),
            "gerangschikt": len(top),
        }
        return {
            "startlist_top": top,
            "startlist_riders": len(rows),
            "startlist_teams": len({r["team"] for r in rows if r.get("team")}),
        }

    async def _rank_maps(self, stage: dict) -> dict:
        """Klassementen van een etappe als {positie: waarde}, per etappe bewaard.

        Hiermee wordt de dagwinst berekend: koppelen op positie via de
        kolom "Prev", nooit op naam.
        """
        url = stage["stage_url"]
        if url in self._prevrank_cache:
            return self._prevrank_cache[url]
        try:
            maps = await self._job(_fetch_rank_maps, url, stage.get("one_day"))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Vorige stand mislukt voor %s: %s", url, err)
            return {}
        if maps:
            self._prevrank_cache[url] = maps
        return maps

    async def _climbs_for(self, race_url: str) -> dict:
        if race_url in self._climbs_cache:
            return self._climbs_cache[race_url]
        climbs = await self._job(_fetch_race_climbs, race_url)
        self._climbs_cache[race_url] = climbs
        return climbs

    async def _stage_uitslag(self, s):
        """Uitslag + standen van \u00e9\u00e9n etappe van een andere koers.

        Alleen een afgeronde etappe komt in de cache: een etappe die nog
        bezig is moet elke ronde opnieuw opgehaald worden.
        """
        url = s["stage_url"]
        if url in self._other_cache:
            d = self._other_cache[url]
            # de ploegcodes die vorige ronde nog niet aan de beurt waren
            await self._ploegcodes(d)
            return d
        d = await self._job(_fetch_stage, url, s.get("one_day"),
                            self._opt(CONF_RESULT_N), self._opt(CONF_GC_N))
        if not d.get("finished"):
            await self._ploegcodes(d)
            return d
        rkey = s["race_url"]
        roster = ({} if s.get("one_day")
                  else _roster_van(await self._startlijst(rkey)))
        if roster:
            for _k in ("results", "gc", "points_top", "kom_top", "youth_top"):
                _repair_rows(d.get(_k), roster)
        # ná het herstellen van de namen: `_repair_rows` vergelijkt de
        # ploegkolom met de startlijst en die noemt de volledige naam
        await self._ploegcodes(d)
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
            # het niveau (het circuitnummer van procyclingstats). De kaart
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
            # dagwinst en -verlies, net als bij de tegelkoers: de stand van
            # de vorige etappe op positie koppelen via de kolom "Prev"
            eerder = [s for s in stages if s["date"] < laatst["date"]]
            if eerder and not laatst.get("one_day"):
                pmaps = await self._rank_maps(eerder[-1])
                if pmaps:
                    _gain_time_by_rank(entry["gc_top"], pmaps.get("gc"))
                    _gain_time_by_rank(entry["youth_top"], pmaps.get("youth"))
                    _gain_pts_by_rank(entry["points_top"], pmaps.get("points"))
                    _gain_pts_by_rank(entry["kom_top"], pmaps.get("kom"))
        # nog geen uitslag: dan is wie er meedoet het enige dat er te melden
        # valt. Zodra er wel een uitslag is blijft de startlijst weg — die
        # kost ruimte in de attributen en de uitslag zegt meer.
        if not entry["last_result"] and toon is not None:
            entry.update(await self._startlijst_blok(ev["url"], ev.get("women")))
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
        return 0 if _gpx_urls(s["race_url"], s.get("idx"), s.get("one_day")) else 1

    async def _gpx_index(self, race_url):
        """De GPX-adressen die cyclingstage zelf op een rij zet, per koers."""
        m = re.match(r"race/([^/]+)/(\d{4})", race_url or "")
        if not m:
            return {}
        sleutel = f"{m.group(1)}/{m.group(2)}"
        if sleutel not in self._gpxindex_cache:
            self._gpxindex_cache[sleutel] = await self._job(
                _fetch_gpx_index, race_url)
        return self._gpxindex_cache[sleutel]

    async def _gpx_van(self, s, n_out):
        """Hoogteprofiel + cols van één etappe, zonder cache.

        Eerst de vaste adressen uit `_gpx_urls`. Die zijn een aanname over de
        bestandsnaam, en zodra cyclingstage er voor één koers van afwijkt
        blijft het profiel leeg zonder dat iets kapot lijkt. Levert geen
        enkel adres iets op, dan wordt het adres opgezocht op de
        GPX-overzichtspagina van die koers - de bron, dus geen gokwerk.
        """
        kandidaten = _gpx_urls(s["race_url"], s.get("idx"), s.get("one_day"))
        # één voor één en niet de hele lijst aan `_fetch_gpx`, want dan is
        # achteraf te zeggen wélk adres het werd (`gpx_used`)
        for kandidaat in kandidaten:
            elev, climbs = await self._job(_fetch_gpx, kandidaat, n_out)
            if elev:
                self._gpx_gebruikt[s["stage_url"]] = kandidaat
                return elev, climbs
        alt = (await self._gpx_index(s["race_url"])).get(s.get("idx") or 0)
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
            meta = await self._job(_fetch_stage_meta, url, s.get("one_day"))
            elev, gpx_climbs = await self._gpx_van(s, 45)
            dist = meta.get("distance")
            if dist is None and elev:
                dist = elev[-1][0]
            cs_route = {}
            if gpx_climbs:  # namen uit de cyclingstage-etappetekst
                art = _stage_article_url(s["race_url"], s.get("idx"), s.get("one_day"))
                cs_names, cs_route = await self._job(_fetch_stage_names, art, dist)
                _match_names(gpx_climbs, cs_names)
                _name_summit(gpx_climbs, meta.get("arrival") or cs_route.get("arrival"))
                self._prose_cache[url] = [
                    (f"{c.get('name') or '?'} {c.get('length_km')}@{c.get('steepness_pct')}"
                     + (f" k2f={c['km_to_finish']}" if c.get('km_to_finish') is not None else ""))
                    for c in cs_names]
            # geen colnamen uit de etappetekst (klassiekers, vrouwenkoersen,
            # kleinere rittenkoersen) -> namen bij PCS ophalen
            if gpx_climbs and not any((c.get("name") or "").strip() for c in gpx_climbs):
                pcs = await self._job(_fetch_stage_climbs, s["stage_url"], {})
                _enrich_names(gpx_climbs, pcs)
            if not gpx_climbs:
                # korte klimmen (bv. Montmartre, 1,1 km) ziet de GPX-detectie niet;
                # PCS kent ze wel, inclusief hoe vaak ze worden verreden
                gpx_climbs = await self._job(_fetch_stage_climbs, s["stage_url"], {})
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
        # diagnose van déze ronde; anders blijft die van een vorige koers
        # staan zodra er nergens meer een startlijst wordt opgevraagd
        self._startlist_diag = {}

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
                self._prevrank_cache.clear()
                # renners vallen af en de ranglijst schuift; allebei een dag
                # oud is precies zo vers als de rest
                self._startlist_cache.clear()
                self._ranking_cache.clear()
                self._names_cache.clear()
                self._prose_cache.clear()
                self._abbr_cache.clear()
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
            td = await self._job(_fetch_stage, today_st["stage_url"], today_st.get("one_day"),
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
            shown_data = await self._job(_fetch_stage, shown["stage_url"], shown.get("one_day"),
                                         self._opt(CONF_RESULT_N), self._opt(CONF_GC_N))
        if last_fin is not None and last_fin_data is None:
            last_fin_data = await self._job(_fetch_stage, last_fin["stage_url"], last_fin.get("one_day"),
                                            self._opt(CONF_RESULT_N), self._opt(CONF_GC_N))

        # namen in de klassementen kunnen bij de verkeerde rij staan; herstellen
        # met de startlijst (renner -> ploeg) als betrouwbare referentie
        roster, names_fixed = {}, 0
        if last_fin is not None and not last_fin.get("one_day"):
            roster = _roster_van(await self._startlijst(last_fin["race_url"]))
        if roster and last_fin_data:
            for _k in ("results", "gc", "points_top", "kom_top", "youth_top"):
                names_fixed += _repair_rows(last_fin_data.get(_k), roster)
            if names_fixed:
                _LOGGER.debug("%s scheve naam/namen hersteld via de startlijst", names_fixed)
        # ploegcodes ná het herstellen van de namen: `_repair_rows` vergelijkt
        # de ploegkolom met de startlijst, en die noemt de volledige naam
        if last_fin_data:
            await self._ploegcodes(last_fin_data)

        # dag-winst/-verlies: koppel de vorige stand op POSITIE (kolom "Prev"),
        # zodat er geen renners op naam gematcht hoeven te worden
        gains_set = 0
        prev_fin = None
        if last_fin is not None and not last_fin.get("one_day"):
            if today_finished:
                prev_fin = finished[-1] if finished else None
            elif len(finished) >= 2:
                prev_fin = finished[-2]
        if prev_fin is not None and last_fin_data:
            pmaps = await self._rank_maps(prev_fin)
            if pmaps:
                gains_set += _gain_time_by_rank(last_fin_data.get("gc"), pmaps.get("gc"))
                gains_set += _gain_time_by_rank(last_fin_data.get("youth_top"),
                                                pmaps.get("youth"))
                gains_set += _gain_pts_by_rank(last_fin_data.get("points_top"),
                                               pmaps.get("points"))
                gains_set += _gain_pts_by_rank(last_fin_data.get("kom_top"),
                                               pmaps.get("kom"))

        # PCS-cols alleen voor NAMEN + officiele categorie
        race_climbs = await self._climbs_for(shown_event["url"])
        pcs_climbs = await self._job(_fetch_stage_climbs, shown["stage_url"], race_climbs)
        _merge_categories(pcs_climbs, shown_data.get("climbs_raw", []))

        # Echt hoogteprofiel + gedetecteerde cols (GPX) voor de getoonde etappe
        gpx_url = _gpx_urls(shown["race_url"], shown.get("idx"), shown.get("one_day"))
        elevation, gpx_climbs = await self._gpx_for(shown, 200)
        cs_route = {}
        elev_bron = "gpx" if elevation else ""
        if gpx_climbs:
            _enrich_names(gpx_climbs, pcs_climbs)
            art = _stage_article_url(shown["race_url"], shown.get("idx"), shown.get("one_day"))
            cs_names, cs_route = await self._names_for(
                shown["stage_url"], art, shown_data.get("distance"))
            _match_names(gpx_climbs, cs_names)
            _name_summit(gpx_climbs, shown_data.get("arrival") or cs_route.get("arrival"))
            climbs = gpx_climbs
        else:
            climbs = pcs_climbs
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

        live = {}
        if show_state == "LIVE":
            live = await self._job(_fetch_live, shown["stage_url"])

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
        # Nog niets gereden in deze koers: dan is de startlijst wat er te
        # melden valt. Met een uitslag erbij blijft hij weg — die zegt meer en
        # de attributen zijn al krap.
        startlijst = {"startlist_top": [], "startlist_riders": 0,
                      "startlist_teams": 0}
        if not last_result:
            startlijst = await self._startlijst_blok(shown["race_url"],
                                                     shown.get("women"))
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

        # Live-positie (alleen als de kop echt onderweg is) + links
        from urllib.parse import quote
        live_dist = svg_stage["distance_km"]
        live_km = live.get("km_to_go")
        if _type_tag(shown_data.get("stage_type")):   # tijdrit: geen peloton-stip
            live_km = None
        live_racing = bool(live_km is not None and live_dist and 0 < live_km < live_dist)
        _yr = re.search(r"/(20\d\d)(?:/|$)", shown.get("stage_url", ""))
        _yr = _yr.group(1) if _yr else ""
        _sm = re.search(r"Etappe (\d+)", last_stage_label or "")
        _q = (f"{cur['name']} {_yr} stage {_sm.group(1)} extended highlights"
              if _sm else f"{cur['name']} {_yr} highlights")
        highlights_url = "https://www.youtube.com/results?search_query=" + quote(_q)
        live_url = f"https://www.procyclingstats.com/{shown['stage_url']}/live"
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
                "startlist_diag": self._startlist_diag,
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
                               _times_urls(shown["race_url"], shown.get("idx"),
                                           shown.get("one_day"))],
                "elevation_source": elev_bron,
                "sprints": sprints,
                **ander,
                "gain_headers": (last_fin_data or {}).get("gain_headers", []),
                "gain_raw": (last_fin_data or {}).get("gain_raw", []),
                "names_fixed": names_fixed,
                "gains_set": gains_set,
                "roster_size": len(roster),
                "finish_est": finish_est,
                "channels": [f"{c['name']} {c['time']}".strip()
                             for c in channels if c.get("name")],
                "channels_detail": channels,
                # ── live positie (spoilervrij) + links ──
                "live_km_to_go": live_km if live_racing else None,
                "live_avg_speed": live.get("avg_speed") if live_racing else None,
                "live_status": live.get("status") or "",
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

    Eén mislukte ronde bij procyclingstats hoort deze integratie ook niet te
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
