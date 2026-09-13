"""De tegel rolt door naar de volgende koers — helemaal, niet half.

Op 13 september 2026 eindigde de Vuelta. De tegel rolde door naar de Tour of
Britain, een koers die op 7 september al was afgelopen, en liet daar de
uitslag en het algemeen klassement van de Vuelta onder zien — met Enric Mas
bovenaan een "Algemeen klassement" van de Tour of Britain.

Twee fouten in één beeld, allebei hier afgedekt.
"""
import asyncio
from datetime import date, datetime

import pytest

VANDAAG = date(2026, 9, 13)


def _koers(naam, slug, start, eind):
    return {"name": naam, "start": start, "end": eind, "women": False,
            "level": "m", "url": f"https://www.cyclingstage.com/{slug}-2026/",
            "route_url": f"https://www.cyclingstage.com/{slug}-2026/"}


def _etappe(koers, idx, dag, aantal=1):
    slug = koers["url"].rstrip("/").split("/")[-1].replace("-2026", "")
    return {"date": dag, "idx": idx, "one_day": aantal == 1,
            "stage_url": f"{koers['url']}stage-{idx}-2026/",
            "race_url": koers["url"], "race_name": koers["name"],
            "race_slug": slug, "women": False, "level": "m",
            "distance_km": 180.0, "stage_type": "flat",
            "departure": "A", "arrival": "B", "name": "A - B",
            "profile_icon": ""}


VUELTA = _koers("La Vuelta ciclista a España", "vuelta", date(2026, 8, 22), VANDAAG)
BRITAIN = _koers("Tour of Britain", "tour-of-britain",
                 date(2026, 9, 2), date(2026, 9, 7))
MONTREAL = _koers("Grand Prix de Montréal", "gp-montreal", VANDAAG, VANDAAG)
LOMBARDIJE = _koers("Il Lombardia", "il-lombardia",
                    date(2026, 10, 10), date(2026, 10, 10))

# de uitslag die in het echte geval onder de verkeerde koers belandde
VUELTA_UITSLAG = {
    "ok": True, "finished": True,
    "results": [{"rank": 1, "rider": "Tobias Halland Johannessen",
                 "country": "nor", "time": "2:54:08"}],
    "gc": [{"rank": 1, "rider": "Enric Mas", "country": "spa", "time": "—"}],
    "points_top": [], "kom_top": [], "youth_top": [],
    "points_leader": "", "kom_leader": "", "youth_leader": "",
    "distance": 180.0, "vertical": None, "profile_score": None,
    "stage_type": "flat", "start_time": "", "climbs_raw": [],
    "departure": "A", "arrival": "B", "result_url": "x",
    "startlist_quality": None,
}


def _leeg(stage):
    d = dict(VUELTA_UITSLAG)
    d.update(finished=False, results=[], gc=[])
    return d


@pytest.fixture
def co(wt, monkeypatch):
    """Een coordinator waarin alleen de koerskeuze echt draait."""
    monkeypatch.setattr(wt.dt_util, "now",
                        lambda: datetime(2026, 9, 13, 22, 31))
    c = wt.CyclingCoordinator(None)
    c._calendar = [VUELTA, BRITAIN, MONTREAL, LOMBARDIJE]
    c._calendar_fetched = VANDAAG
    c._levels_diag, c._kalenderfouten = {}, []

    etappes = {
        # etappe 21 valt op vandaag; de Vuelta is daarmee uitgereden
        VUELTA["url"]: [_etappe(VUELTA, n, VANDAAG - _dag(21 - n), 21)
                        for n in range(1, 22)],
        BRITAIN["url"]: [_etappe(BRITAIN, n, date(2026, 9, 1) + _dag(n), 6)
                         for n in range(1, 7)],
        MONTREAL["url"]: [_etappe(MONTREAL, None, VANDAAG)],
        LOMBARDIJE["url"]: [_etappe(LOMBARDIJE, None, date(2026, 10, 10))],
    }

    async def stages_for(ev, today):
        return etappes[ev["url"]]

    async def job(fn, *args):
        if fn is wt._fetch_stage:
            stage = args[0]
            # alles tot en met vandaag is gereden en heeft een uitslag
            return (dict(VUELTA_UITSLAG) if stage["date"] <= VANDAAG
                    else _leeg(stage))
        raise AssertionError(f"onverwachte job: {fn}")

    c._stages_for = stages_for
    c._job = job
    c._races_block = _nep_async({})
    c._build_upcoming = _nep_async([])
    c._build_past = _nep_async([])
    c._gpx_for = _nep_async(([], []))
    c._names_for = _nep_async(([], {}))
    c._meta_voor = _nep_async({})
    c._sprints_voor = _nep_async([])
    c._startlijst_blok = _nep_async({})
    c._zenders_voor = _nep_async([])
    return c


def _dag(n):
    from datetime import timedelta
    return timedelta(days=n)


def _nep_async(waarde):
    async def f(*a, **kw):
        return waarde
    return f


def _attributen(co):
    return asyncio.run(co._async_update_data())["attributes"]


def test_de_tegel_slaat_een_afgelopen_koers_over(co):
    """De Tour of Britain was op 7 september klaar en hoort niet meer op de tegel.

    De kalender staat op begindatum, dus een afgelopen koers kan verderop in
    de lijst staan dan een die nog moet komen. De doorrol liep die lijst af
    zonder naar de einddatum te kijken en pakte `nstages[0]` — etappe 1 van
    2 september.
    """
    a = _attributen(co)
    assert a["race_name"] != BRITAIN["name"]
    assert a["race_name"] == LOMBARDIJE["name"]
    assert a["eyebrow"].startswith("Il Lombardia") or "Lombardia" in a["eyebrow"]


def test_de_uitslag_hoort_bij_de_koers_die_er_staat(co):
    """Dit was de melding: Mas in het klassement van de Tour of Britain.

    `last_result`, `gc_top` en `last_stage_label` kwamen van de vórige koers,
    want bij het doorrollen werden alleen `shown` en `shown_event` bijgewerkt.
    """
    a = _attributen(co)
    assert a["last_result"] == []
    assert a["gc_top"] == []
    assert a["last_stage_label"] == ""
    # en zeker niemand uit de Vuelta
    assert "Mas" not in str(a["gc_top"])


def test_de_koersgegevens_rollen_mee(co):
    """Naam, datums en aftelling hoorden ook bij de oude koers.

    Op de tegel stond "22 aug – 13 sep · Etappekoers" met "Bezig — dag 23/23"
    terwijl het profiel van een andere koers was.
    """
    a = _attributen(co)
    assert "okt" in a["date"], a["date"]
    assert a["is_live"] is False
    assert "Bezig" not in a["countdown"]
    assert a["type"] in ("Eendaagse koers", "Monument")


def test_zonder_doorrol_verandert_er_niets(co, wt):
    """Rijdt de Vuelta nog, dan blijft alles gewoon van de Vuelta.

    De doorrol mag niet gaan lopen zolang de eigen koers nog iets te tonen
    heeft — dat zou de tegel midden in een grote ronde laten verspringen.
    """
    async def nog_bezig(fn, *args):
        if fn is wt._fetch_stage:
            stage = args[0]
            if stage["date"] == VANDAAG:
                return _leeg(stage)          # de slotrit rijdt nog
            return (dict(VUELTA_UITSLAG) if stage["date"] < VANDAAG
                    else _leeg(stage))
        raise AssertionError(fn)

    co._job = nog_bezig
    a = _attributen(co)
    assert a["race_name"] == VUELTA["name"]
    assert a["is_live"] is True
    # en de uitslag die erbij staat is die van de Vuelta, van etappe 20
    assert a["last_stage_label"].startswith("Etappe 20")
    assert a["gc_top"][0]["rider"] == "Enric Mas"
