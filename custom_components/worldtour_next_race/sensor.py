"""Sensor: eerstvolgende of lopende UCI WorldTour wedstrijd via procyclingstats.com.

YAML-configuratie:

    sensor:
      - platform: worldtour_next_race

Uitgebreide versie:
- Spoiler-vrije attributen voor tegel + pop-up (parcours, cols, profielscore ...).
- Spoiler-attributen ALLEEN bedoeld voor de pop-up (uitslag laatste etappe + klassement).
- Etappe-selectie met rollover: zodra de etappe van vandaag klaar is (uitslag binnen)
  toont de tegel de eerstvolgende etappe. Een rustdag telt niet als etappe.
- Genereert twee transparante SVG-profielen (tegel + detail) naar
  /config/www/worldtour/ die de kaart als /local/worldtour/*.svg toont.

De kalender wordt 1x per dag opgehaald; live wordt elk half uur ververst.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=30)
LIVE_SCAN_INTERVAL = timedelta(minutes=5)  # sneller pollen tijdens een live etappe

RESULT_N = 10  # aantal renners in de uitslag (pop-up)
GC_N = 10      # aantal renners in het klassement (pop-up)
UPCOMING_N = 10  # veiligheidscap op aantal komende etappes (pop-up)
UPCOMING_DAYS = 7  # toon alleen komende etappes binnen zoveel dagen

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

def _fetch_calendar(year: int) -> list[dict]:
    """Haal de WorldTour-kalender op van procyclingstats.com."""
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

    races = []
    # circuit 1 = UCI WorldTour (mannen), circuit 24 = UCI Women's WorldTour
    for circuit, vrouwen in ((1, False), (24, True)):
        try:
            cal = RacesCalendar(
                f"races.php?year={year}&circuit={circuit}&class=&filter=Filter")
            rijen = cal.races()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Kalender circuit %s ophalen mislukt: %s", circuit, err)
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
                          "start": start, "end": end, "women": vrouwen})
    races.sort(key=lambda x: (x["start"], x["women"]))
    _LOGGER.debug("Kalender: %s koersen (%s bij de vrouwen)",
                  len(races), sum(1 for r in races if r["women"]))
    return races


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


def _fetch_roster(race_url):
    """Renner -> ploeg uit de startlijst.

    De startlijst is per ploegblok opgebouwd (de ploegnaam komt uit de kop van
    het blok), dus deze koppeling kan niet verschuiven zoals in de
    klassementstabellen.
    """
    from procyclingstats import RaceStartlist
    try:
        rows = RaceStartlist(f"{race_url}/startlist").startlist(
            "rider_name", "team_name")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Startlijst ophalen mislukt: %s", err)
        return {}
    out = {}
    for r in rows or []:
        nm, tm = _name_key(r.get("rider_name")), (r.get("team_name") or "").strip()
        if nm and tm:
            out[nm] = tm
    _LOGGER.debug("Startlijst: %s renners", len(out))
    return out


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


def _fetch_stage(stage_url: str, one_day: bool = False) -> dict:
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

    results = _safe(
        lambda: st.results("rank", "rider_name", "team_name", "time", "status"), []) or []
    _fix_names(results, _row_names(st, "stage"), "uitslag")
    clean = []
    for r in results:
        if r.get("rank") in (None, "") or r.get("status") not in (None, "DF", ""):
            continue
        clean.append({
            "rank": r.get("rank"),
            "rider": (r.get("rider_name") or "").strip(),
            "team": (r.get("team_name") or "").strip(),
            "time": r.get("time") or "",
        })
        if len(clean) >= RESULT_N:
            break
    data["results"] = clean
    data["finished"] = bool(clean)

    gc = _safe(lambda: st.gc(
        "rank", "rider_name", "team_name", "time", "prev_rank"), []) or []
    if not gc:
        gc = _safe(lambda: st.gc("rank", "rider_name", "team_name", "time"), []) or []
    _fix_names(gc, _row_names(st, "gc"), "klassement")
    data["gc"] = [{
        "rank": g.get("rank"),
        "rider": (g.get("rider_name") or "").strip(),
        "team": (g.get("team_name") or "").strip(),
        "time": g.get("time") or "",
        "move": _move(g.get("prev_rank"), g.get("rank")),
        "prev": _int(g.get("prev_rank")),
    } for g in gc[:GC_N]]
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
        "rank", "rider_name", "team_name", "time", "prev_rank"), []) or []
    if not youth:
        youth = _safe(lambda: st.youth("rank", "rider_name", "team_name", "time"), []) or []
    _fix_names(youth, _row_names(st, "youth"), "jongeren")
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


def _fetch_channels(race_url, idx, one_day, race_name):
    """NL-tv-zenders van de (aankomende) etappe uit de wielerflits-tv-gids."""
    m = re.match(r"race/([^/]+)/(\d{4})", race_url or "")
    if not m:
        return []
    import urllib.request
    try:
        req = urllib.request.Request(
            WIELERFLITS_TV_URL,
            headers={"User-Agent": "Mozilla/5.0 (HomeAssistant WorldTour)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", "replace")
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("TV-gids ophalen mislukt: %s", err)
        return []
    ch = _parse_channels(html, m.group(1), m.group(2), idx, race_name or "")
    _LOGGER.debug("TV-zenders %s e%s: %s", m.group(1), idx, ch)
    return ch


# Etappe-artikelen op cyclingstage (colnamen + verwachte finishtijd).
# De adressen volgen geen vast patroon, dus per koers een sjabloon.
CYCLINGSTAGE_ROUTE = {
    "tour-de-france":
        "https://www.cyclingstage.com/tour-de-france-{y}-route/stage-{n}-tdf-{y}/",
    "giro-d-italia":
        "https://www.cyclingstage.com/giro-{y}-route/stage-{n}-giro-{y}/",
    "vuelta-a-espana":
        "https://www.cyclingstage.com/vuelta-{y}-route/stage-{n}-vuelta-{y}/",
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
            url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant WorldTour)"})
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
            url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant WorldTour)"})
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
                url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant WorldTour)"})
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
            gpx_url, headers={"User-Agent": "Mozilla/5.0 (HomeAssistant WorldTour)"})
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


class WorldTourCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, _LOGGER, name="worldtour_next_race",
                         update_interval=SCAN_INTERVAL)
        self._calendar: list[dict] | None = None
        self._calendar_fetched: date | None = None
        self._stages_cache: dict[str, tuple[date, list[dict]]] = {}
        self._climbs_cache: dict[str, dict] = {}
        self._upcoming_cache: dict[str, dict] = {}
        self._elev_cache: dict[str, list] = {}
        self._channels_cache = None
        self._sprints_cache = None
        self._roster_cache: dict = {}
        self._other_cache = None
        self._prevrank_cache = None
        self._names_cache: dict[str, list] = {}
        self._prose_cache: dict[str, list] = {}
        self._names_diag: list = []

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

    async def _climbs_for(self, race_url: str) -> dict:
        if race_url in self._climbs_cache:
            return self._climbs_cache[race_url]
        climbs = await self._job(_fetch_race_climbs, race_url)
        self._climbs_cache[race_url] = climbs
        return climbs

    async def _other_block(self, andere, today):
        """Laatste uitslag + klassement van de andere gelijktijdige koers."""
        leeg = {"other_label": "", "other_result": [], "other_gc": []}
        for _d, _g, _w, _i, _ev, st in andere:
            klaar = [s for s in st if s["date"] < today]
            vandaag = next((s for s in st if s["date"] == today), None)
            for s in ([vandaag] if vandaag else []) + klaar[-1:]:
                key = (today.isoformat(), s["stage_url"])
                if self._other_cache and self._other_cache[0] == key:
                    d = self._other_cache[1]
                else:
                    d = await self._job(_fetch_stage, s["stage_url"], s.get("one_day"))
                    if d.get("finished"):
                        self._other_cache = (key, d)
                if not d.get("finished"):
                    continue
                rkey = s["race_url"]
                if rkey not in self._roster_cache and not s.get("one_day"):
                    r = await self._job(_fetch_roster, rkey)
                    if r:
                        self._roster_cache[rkey] = r
                roster = self._roster_cache.get(rkey) or {}
                if roster:
                    _repair_rows(d.get("results"), roster)
                    _repair_rows(d.get("gc"), roster)
                label = (_short_race(s["race_name"], 34) if s.get("one_day")
                         else f"Etappe {s['idx']} \u00b7 {_short_race(s['race_name'], 34)}")
                if s.get("women") and not _noemt_dames(s["race_name"]):
                    label += " \u00b7 Dames"
                return {"other_label": label,
                        "other_result": (d.get("results") or [])[:RESULT_N],
                        "other_gc": (d.get("gc") or [])[:5]}
        return leeg

    def _gpx_rang(self, s):
        """0 = hoogteprofiel beschikbaar, 1 = (waarschijnlijk) niet."""
        gecached = self._elev_cache.get(s["stage_url"])
        if gecached is not None:
            return 0 if gecached[0] else 1
        return 0 if _gpx_urls(s["race_url"], s.get("idx"), s.get("one_day")) else 1

    async def _gpx_for(self, stage_url, gpx_url, n_out=150):
        if stage_url in self._elev_cache:
            return self._elev_cache[stage_url]
        elev, climbs = await self._job(_fetch_gpx, gpx_url, n_out)
        if elev:
            self._elev_cache[stage_url] = (elev, climbs)
        return elev, climbs

    async def _names_for(self, stage_url, art_url, distance=None):
        if stage_url in self._names_cache:
            return self._names_cache[stage_url]
        result = await self._job(_fetch_stage_names, art_url, distance)
        if result[0] or result[1]:
            self._names_cache[stage_url] = result
        return result

    async def _upcoming_entry(self, s: dict, today: date) -> dict:
        url = s["stage_url"]
        cached = self._upcoming_cache.get(url)
        if cached is not None:
            e = dict(cached)
        else:
            await asyncio.sleep(0.4)  # niet overspoelen
            meta = await self._job(_fetch_stage_meta, url, s.get("one_day"))
            gpx = _gpx_urls(s["race_url"], s.get("idx"), s.get("one_day"))
            elev, gpx_climbs = await self._job(_fetch_gpx, gpx, 45)
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
            e = {
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
        if s.get("one_day"):
            e["eyebrow"] = _short_race(s["race_name"], 26)
        else:
            e["eyebrow"] = f"Etappe {s['idx']} \u00b7 {_short_race(s['race_name'])}"
        if s.get("women") and not _noemt_dames(s["race_name"]):
            e["eyebrow"] += " \u00b7 Dames"
        _tag = _type_tag(e.get("stage_type"))
        if _tag:
            e["eyebrow"] += f" \u00b7 {_tag}"
        return e

    async def _build_upcoming(self, cur_idx: int, shown: dict,
                              future: list[dict], today: date) -> list[dict]:
        shown_url = shown.get("stage_url")
        cutoff = today + timedelta(days=UPCOMING_DAYS)   # max N dagen vooruit
        pool = [s for s in future
                if s["stage_url"] != shown_url and today <= s["date"] <= cutoff]
        # alle koersen die in het venster vallen, ook koersen die al eerder
        # begonnen dan de koers op de tegel (mannen en vrouwen door elkaar)
        for i, ev in enumerate(self._calendar):
            if i == cur_idx or ev["end"] < today or ev["start"] > cutoff:
                continue
            pool.extend([s for s in await self._stages_for(ev, today)
                         if s["stage_url"] != shown_url
                         and today <= s["date"] <= cutoff])
        if not pool:   # niets binnen het venster -> pak de eerstvolgende koers(en)
            later = []
            for ev in self._calendar:
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
        for s in pool[:UPCOMING_N]:
            try:
                e = await self._upcoming_entry(s, today)
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
                self._calendar = await self._job(_fetch_calendar, today.year)
                self._calendar_fetched = today
                self._stages_cache.clear()
                self._upcoming_cache.clear()
                self._elev_cache.clear()
                self._channels_cache = None
                self._sprints_cache = None
                self._prevrank_cache = None
                self._names_cache.clear()
                self._prose_cache.clear()
            except Exception as err:  # noqa: BLE001
                if self._calendar is None:
                    raise UpdateFailed(f"Kalender ophalen mislukt: {err}") from err
                _LOGGER.warning("Kalender verversen mislukt, oude cache: %s", err)

        if not self._calendar:
            raise UpdateFailed("Geen WorldTour-wedstrijden gevonden — PCS-structuur gewijzigd?")

        cur_idx = next((i for i, r in enumerate(self._calendar) if r["end"] >= today), None)
        if cur_idx is None:
            return {"state": "Seizoen afgelopen", "attributes": {"show_state": "Klaar"}}

        # Mannen en vrouwen kunnen tegelijk koersen; kies er EEN voor het dashboard.
        # Volgorde: eerstvolgende etappe, dan koersen met hoogteprofiel, dan mannen.
        venster = today + timedelta(days=UPCOMING_DAYS)
        actief = [(i, r) for i, r in enumerate(self._calendar)
                  if r["end"] >= today and r["start"] <= venster][:4]
        if not actief:
            actief = [(cur_idx, self._calendar[cur_idx])]
        kandidaten = []
        for i, ev in actief:
            st = await self._stages_for(ev, today)
            nxt = next((s for s in st if s["date"] >= today), None)
            if nxt is None:
                continue
            kandidaten.append((nxt["date"], self._gpx_rang(nxt),
                               1 if ev.get("women") else 0, i, ev, st))
        if kandidaten:
            kandidaten.sort(key=lambda k: k[:4])
            cur_idx, cur, stages = kandidaten[0][3], kandidaten[0][4], kandidaten[0][5]
            andere_koersen = kandidaten[1:]
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
            td = await self._job(_fetch_stage, today_st["stage_url"], today_st.get("one_day"))
            if td.get("finished"):
                today_finished = True
                last_fin, last_fin_data = today_st, td
                shown = future[0] if future else None
            else:
                shown, shown_data = today_st, td  # live/vandaag
        else:
            shown = future[0] if future else None  # rustdag / pre-race

        # Voorbij de laatste etappe van deze koers -> volgende koers
        if shown is None and cur_idx + 1 < len(self._calendar):
            nxt = self._calendar[cur_idx + 1]
            nstages = await self._stages_for(nxt, today)
            if nstages:
                shown, shown_event = nstages[0], nxt

        if shown is None:
            return {"state": "Seizoen afgelopen", "attributes": {"show_state": "Klaar"}}

        if shown_data is None:
            shown_data = await self._job(_fetch_stage, shown["stage_url"], shown.get("one_day"))
        if last_fin is not None and last_fin_data is None:
            last_fin_data = await self._job(_fetch_stage, last_fin["stage_url"], last_fin.get("one_day"))

        # namen in de klassementen kunnen bij de verkeerde rij staan; herstellen
        # met de startlijst (renner -> ploeg) als betrouwbare referentie
        roster, names_fixed = {}, 0
        if last_fin is not None and not last_fin.get("one_day"):
            rkey = last_fin["race_url"]
            if rkey in self._roster_cache:
                roster = self._roster_cache[rkey]
            else:
                roster = await self._job(_fetch_roster, rkey)
                if roster:
                    self._roster_cache[rkey] = roster
        if roster and last_fin_data:
            for _k in ("results", "gc", "points_top", "kom_top", "youth_top"):
                names_fixed += _repair_rows(last_fin_data.get(_k), roster)
            if names_fixed:
                _LOGGER.debug("%s scheve naam/namen hersteld via de startlijst", names_fixed)

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
            pkey = prev_fin["stage_url"]
            if self._prevrank_cache and self._prevrank_cache[0] == pkey:
                pmaps = self._prevrank_cache[1]
            else:
                pmaps = await self._job(_fetch_rank_maps,
                                        pkey, prev_fin.get("one_day"))
                if pmaps:
                    self._prevrank_cache = (pkey, pmaps)
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
        elevation, gpx_climbs = await self._gpx_for(shown["stage_url"], gpx_url, 200)
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
        skey = shown["stage_url"]
        if self._sprints_cache and self._sprints_cache[0] == skey:
            sprints = self._sprints_cache[1]
        else:
            sprints = await self._job(_fetch_times, shown["race_url"],
                                      shown.get("idx"), shown.get("one_day"))
            self._sprints_cache = (skey, sprints)

        # dag-uitslag van de andere koers die tegelijk bezig is
        ander = await self._other_block(andere_koersen, today)

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
        upcoming = await self._build_upcoming(cur_idx, shown, future, today)

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
        self.update_interval = LIVE_SCAN_INTERVAL if show_state == "LIVE" else SCAN_INTERVAL
        # voor de conditionele dashboardkaart
        today_or_tomorrow = show_state in ("LIVE", "Vandaag", "Morgen")
        days_until = max(0, (shown["date"] - today).days)
        # echte finishtijd van cyclingstage; anders de schatting
        finish_est = cs_route.get("finish_time") or _finish_est(
            shown_data.get("start_time"), svg_stage["distance_km"],
            svg_stage["profile_score"], svg_stage["vertical_m"],
            shown_data.get("stage_type"))
        channels = []
        if days_until <= 6:            # de tv-gids toont ~6 dagen vooruit
            ckey = (today.isoformat(), shown["stage_url"])
            if self._channels_cache and self._channels_cache[0] == ckey:
                channels = self._channels_cache[1]
            else:
                channels = await self._job(
                    _fetch_channels, shown["race_url"], shown.get("idx"),
                    shown.get("one_day"), shown.get("race_name"))
                if channels:
                    self._channels_cache = (ckey, channels)

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
# Platform setup (YAML)
# ──────────────────────────────────────────────────────────────

async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    coordinator = WorldTourCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([WorldTourNextRaceSensor(coordinator)])


class WorldTourNextRaceSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Volgende WorldTour Wedstrijd"
    _attr_unique_id = "worldtour_next_race"
    _attr_icon = "mdi:bike-fast"

    @property
    def native_value(self):
        return self.coordinator.data.get("state")

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("attributes", {})
