"""Start- en finishtijd komen uit één bron, op één klok.

Tot 0.31.4 las `_fetch_stage_names` de verwachte finishtijd een tweede keer
uit de etappetekst: alleen "expected to finish around", en zonder de tijd om
te rekenen naar de tijdzone van Home Assistant. De tegel gaf die lezing
voorrang op de meta, en "Komende dagen" gebruikte hem alleen als er cols
waren — anders een schatting. Zo kreeg de WK-wegrit van de mannen in de
pop-up "15:00-22:36" terwijl de pagina 21:40 (onze tijd) zegt.

Alles hieronder draait op de echte pagina's in tests/fixtures/.
"""
import asyncio
import pathlib
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest


def _fixture(naam):
    return (pathlib.Path(__file__).parent / "fixtures" / naam).read_text(
        errors="replace")


@pytest.fixture
def wk_live():
    return _fixture("cyclingstage_wk_2026_montreal.html")


@pytest.fixture
def wk_wegrit():
    return _fixture("cyclingstage_wk_2026_route_wegrit.html")


@pytest.fixture
def wk_itt():
    return _fixture("cyclingstage_wk_2026_route_itt.html")


def _wk_onderdelen(wt, monkeypatch, pagina):
    """De vijf onderdelen, van de echte kalenderregel en de echte WK-pagina."""
    monkeypatch.setattr(
        wt, "_haal_html",
        lambda url, wat="": pagina if "world-championships" in url else "")
    from cycling_next_race import cyclingstage as cs_mod
    koers = next(k for k in cs_mod.parse_kalender(
        _fixture("cyclingstage_kalender_2026.html"), 2026)
        if "World Champ" in k["name"])
    koers["level"] = "m"
    return {s["onderdeel"]: s for s in wt._event_stages(koers)}


async def _geen(*a, **kw):
    return {}


# ── "Komende dagen" ─────────────────────────────────────────────────

def test_komende_dagen_neemt_de_finishtijd_van_de_pagina(
        wt, monkeypatch, wk_live, wk_wegrit):
    """21:40 zoals de pagina zegt, niet de schatting 22:36.

    "expected to finish at 15:40 — both are local times (EDT)". De meta las
    dat al goed; `_upcoming_entry` gebruikte het alleen niet.
    """
    st = _wk_onderdelen(wt, monkeypatch, wk_live)["Wegrit mannen"]
    monkeypatch.setattr(wt, "_etappe_html",
                        lambda url: wk_wegrit if "road-race" in url else "")
    monkeypatch.setattr(wt.dt_util, "now", lambda: datetime(2026, 9, 26, 10, 0))
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        if fn is wt._fetch_gpx:
            return [], []            # geen GPX in de fixtures
        return fn(*args)

    c._job = job
    c._gpx_index = _geen
    e = asyncio.run(c._upcoming_entry(st, date(2026, 9, 26)))
    assert e["start_time"] == "15:00"
    assert e["finish_est"] == "21:40"


def test_komende_dagen_rekent_de_finish_om_net_als_de_start(wt, monkeypatch):
    """Wie Home Assistant op Londen heeft staan, krijgt beide tijden in BST.

    De Vuelta-pagina zegt "starts at 14:40 ... finish around 17:30 - both
    local times (CEST)". Met cols erbij kwam de finish uit de etappetekst,
    en die rekende niet om: 13:40 tot 17:30, een uur te lang LIVE.
    """
    monkeypatch.setattr(wt.dt_util, "DEFAULT_TIME_ZONE", ZoneInfo("Europe/London"))
    pagina = _fixture("cyclingstage_vuelta_2026_stage4.html")
    monkeypatch.setattr(wt, "_etappe_html", lambda url: pagina)
    monkeypatch.setattr(wt.dt_util, "now", lambda: datetime(2026, 8, 25, 10, 0))
    etappe = {"date": date(2026, 8, 25), "idx": 4, "one_day": False,
              "stage_url": "https://www.cyclingstage.com/vuelta-2026-route/"
                           "stage-4-spain-2026/",
              "race_url": "https://www.cyclingstage.com/vuelta-2026-route/",
              "race_name": "La Vuelta", "race_slug": "vuelta", "women": False,
              "level": "m", "distance_km": 104.8, "stage_type": "mountain",
              "departure": "Andorra la Vella", "arrival": "Andorra la Vella",
              "eigen_pagina": True}
    c = wt.CyclingCoordinator(None)
    # met cols, want alleen dan werd de etappetekst gelezen
    profiel = [[0.0, 1000], [50.0, 2400], [104.8, 1900]]
    col = {"name": "", "category": "1", "km_to_finish": 54.8, "top_m": 2400,
           "length_km": 20.0, "steepness_pct": 7.0}

    async def job(fn, *args):
        if fn is wt._fetch_gpx:
            return profiel, [dict(col)]
        return fn(*args)

    c._job = job
    c._gpx_index = _geen
    e = asyncio.run(c._upcoming_entry(etappe, date(2026, 8, 24)))
    assert e["start_time"] == "13:40"
    assert e["finish_est"] == "16:30"


# ── de tegel ────────────────────────────────────────────────────────

VUELTA_4 = {"date": date(2026, 8, 25), "idx": 4, "one_day": False,
            "stage_url": "https://www.cyclingstage.com/vuelta-2026-route/"
                         "stage-4-spain-2026/",
            "race_url": "https://www.cyclingstage.com/vuelta-2026-route/",
            "race_name": "La Vuelta", "race_slug": "vuelta", "women": False,
            "level": "m", "distance_km": 104.8, "stage_type": "mountain",
            "departure": "Andorra la Vella", "arrival": "Andorra la Vella",
            "eigen_pagina": True}


def _tegel(wt, monkeypatch, etappe, pagina, nu, profiel, cols=()):
    """Het hele pad van `_async_update_data` voor één etappe van vandaag.

    Alleen het netwerk en de onderdelen die hier niets toe doen zijn
    vervangen; de meta en de etappetekst worden echt gelezen, van `pagina`.
    """
    koers = {"name": etappe["race_name"], "url": etappe["race_url"],
             "slug": etappe["race_slug"], "start": etappe["date"],
             "end": etappe["date"], "women": False, "level": "m",
             "bron": "cyclingstage"}
    monkeypatch.setattr(wt, "_etappe_html", lambda url: pagina)
    monkeypatch.setattr(wt.dt_util, "now", lambda: nu)
    c = wt.CyclingCoordinator(None)
    c._calendar = [koers]
    c._calendar_fetched = nu.date()
    c._levels_diag, c._kalenderfouten = {}, []
    leeg = {"ok": True, "finished": False, "results": [], "gc": [],
            "points_top": [], "kom_top": [], "youth_top": [],
            "points_leader": "", "kom_leader": "", "youth_leader": "",
            "distance": etappe["distance_km"], "vertical": None,
            "profile_score": None, "stage_type": "", "start_time": "",
            "climbs_raw": [], "departure": etappe["departure"],
            "arrival": etappe["arrival"], "result_url": "",
            "startlist_quality": None}

    async def stages_for(ev, today):
        return [etappe]

    async def job(fn, *args):
        if fn is wt._fetch_stage:
            return dict(leeg)
        return fn(*args)

    async def nep(waarde):
        return waarde

    c._stages_for = stages_for
    c._job = job
    c._gpx_for = lambda s, n=60: nep((profiel, [dict(x) for x in cols]))
    c._sprints_voor = lambda s: nep([])
    c._zenders_voor = lambda s, t: nep([])
    c._startlijst_blok = lambda ev: nep({})
    c._build_upcoming = lambda *a, **kw: nep([])
    c._build_past = lambda *a, **kw: nep([])
    c._races_block = lambda *a, **kw: nep({"races": []})
    return asyncio.run(c._async_update_data())["attributes"]


def test_de_tegel_neemt_de_finishtijd_van_de_meta(wt, monkeypatch, wk_live, wk_wegrit):
    """De wegrit van vandaag: 15:00 tot 21:40 hier, en om 16:00 LIVE."""
    wegrit = _wk_onderdelen(wt, monkeypatch, wk_live)["Wegrit mannen"]
    a = _tegel(wt, monkeypatch, wegrit, wk_wegrit,
               datetime(2026, 9, 27, 16, 0), [[0.0, 20], [273.4, 60]])
    assert a["start_time"] == "15:00"
    assert a["finish_est"] == "21:40"
    assert a["show_state"] == "LIVE"


def test_de_tegel_rekent_de_finish_om_net_als_de_start(wt, monkeypatch):
    """Home Assistant op Londen: de Vuelta rijdt daar van 13:40 tot 16:30.

    Hier ging de etappetekst vóór op de meta, en die rekende niet om. Om
    17:10 Londense tijd stond de etappe dan nog op LIVE, en de geschatte
    stip rekende met een uur te veel.
    """
    monkeypatch.setattr(wt.dt_util, "DEFAULT_TIME_ZONE", ZoneInfo("Europe/London"))
    col = {"name": "", "category": "1", "km_to_finish": 54.8, "top_m": 2400,
           "length_km": 20.0, "steepness_pct": 7.0}
    a = _tegel(wt, monkeypatch, VUELTA_4,
               _fixture("cyclingstage_vuelta_2026_stage4.html"),
               datetime(2026, 8, 25, 14, 0),
               [[0.0, 1000], [50.0, 2400], [104.8, 1900]], [col])
    assert a["start_time"] == "13:40"
    assert a["finish_est"] == "16:30"


# ── twee starttijden op één pagina ──────────────────────────────────

def test_de_tijdritpagina_noemt_twee_starttijden(cs, wk_itt):
    """"The women start at 9:19 and the men at 12:45 local time (TDE)"."""
    meta = cs.parse_etappe_meta(wk_itt)
    assert meta["start_per_geslacht"] == {"v": "9:19", "m": "12:45"}
    # de eerste tijd in de tekst blijft de algemene starttijd
    assert meta["start_time"] == "9:19"


def test_een_gewone_etappe_heeft_er_maar_een(cs):
    meta = cs.parse_etappe_meta(_fixture("cyclingstage_vuelta_2026_stage4.html"))
    assert "start_per_geslacht" not in meta
    assert meta["start_time"] == "14:40"


def test_de_tijdrit_van_de_mannen_start_om_zijn_eigen_tijd(
        wt, monkeypatch, wk_live, wk_itt):
    """12:45 EDT is 18:45 hier — niet 15:19, de start van de vrouwen.

    Beide tijdritten delen één routepagina. Met alleen de eerste tijd uit de
    tekst stond de tijdrit van de mannen op 20 september al vanaf 15:19 op
    LIVE, bijna twee uur voordat de eerste man van de schans rolde.
    """
    onderdelen = _wk_onderdelen(wt, monkeypatch, wk_live)
    monkeypatch.setattr(wt, "_etappe_html",
                        lambda url: wk_itt if "route-itt" in url else "")
    assert wt._fetch_stage_meta(onderdelen["Tijdrit mannen"])["start_time"] == "18:45"
    assert wt._fetch_stage_meta(onderdelen["Tijdrit vrouwen"])["start_time"] == "15:19"
