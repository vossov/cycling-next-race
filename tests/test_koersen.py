"""De koersblokken voor de pop-up (`races`).

Mannen en vrouwen koersen vaak op dezelfde dag. De tegel toont er één; de
andere zijn in de pop-up aan te klikken. Deze tests draaien de coordinator
met een gestubde `_fetch_stage`, dus zonder netwerk.
"""
import asyncio
from datetime import date

import pytest

VANDAAG = date(2026, 7, 18)


def _stages(race_url, naam, dagen, women=False):
    """Etappelijst zoals `_event_stages` hem oplevert."""
    return [{
        "date": d, "stage_url": f"{race_url}/stage-{i}", "profile_icon": "",
        "name": "", "idx": i, "one_day": False, "race_url": race_url,
        "race_name": naam, "women": women,
    } for i, d in enumerate(dagen, 1)]


def _uitslag(finished=True):
    return {
        "ok": True, "finished": finished,
        "results": [{"rank": 1, "rider": "Vollering Demi", "team": "FDJ",
                     "time": "3:02:11"}],
        "gc": [{"rank": 1, "rider": "Vollering Demi", "time": "9:14:02"}],
        "points_top": [{"rank": 1, "rider": "Wiebes Lorena", "points": 120}],
        "kom_top": [], "youth_top": [],
    }


@pytest.fixture
def coordinator(wt, monkeypatch):
    """Een coordinator die niets ophaalt: `_job` roept de functie direct aan."""
    co = wt.CyclingCoordinator(hass=None)

    async def _job(fn, *args):
        return fn(*args)

    co._job = _job
    monkeypatch.setattr(wt, "_fetch_roster", lambda *a: {})
    return co


def _draai(co, primair, andere, today=VANDAAG):
    return asyncio.run(co._races_block(primair, andere, today))


def _kandidaat(ev, stages):
    """Zoals `kandidaten` in `_async_update_data`: (datum, gpx, dames, i, ev, st)."""
    return (VANDAAG, 0, 1 if ev.get("women") else 0, 1, ev, stages)


PRIMAIR = {"key": "tour-de-france", "label": "Tour de France",
           "race_name": "Tour de France", "women": False}

FEMMES = {"name": "Tour de France Femmes", "url": "race/tour-de-france-femmes/2026",
          "start": date(2026, 7, 16), "end": date(2026, 7, 24), "women": True}


def test_alleen_de_getoonde_koers(coordinator):
    """Zonder andere koersen blijft er één blok over en is `other_*` leeg."""
    uit = _draai(coordinator, PRIMAIR, [])
    assert [r["key"] for r in uit["races"]] == ["tour-de-france"]
    assert uit["races"][0]["primary"] is True
    assert uit["other_label"] == "" and uit["other_result"] == []


def test_andere_koers_krijgt_eigen_uitslag_en_stand(wt, coordinator, monkeypatch):
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 16), date(2026, 7, 17), VANDAAG], women=True)
    # de etappe van vandaag is nog niet binnen; die van gisteren wel
    monkeypatch.setattr(wt, "_fetch_stage", lambda url, *a: _uitslag(
        finished=not url.endswith("stage-3")))

    uit = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    blok = uit["races"][1]

    assert blok["key"] == "tour-de-france-femmes"
    assert blok["label"] == "Tour de France Femmes"   # naam noemt de dames al
    assert blok["last_stage_label"] == "Etappe 2 · Tour de France Femmes"
    assert blok["last_result"][0]["rider"] == "Vollering Demi"
    assert blok["gc_top"] and blok["points_top"]
    # de etappe van vandaag is nog bezig, dus die staat bovenaan het blok
    assert blok["eyebrow"] == "Etappe 3 · Tour de France Femm…"
    assert blok["show_state"] == "Vandaag"


def test_uitslag_van_vandaag_schuift_door_naar_de_volgende_etappe(
        wt, coordinator, monkeypatch):
    """Dezelfde rollover als op de tegel: uitslag binnen = volgende etappe tonen."""
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 17), VANDAAG, date(2026, 7, 19)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])["races"][1]

    assert blok["last_stage_label"] == "Etappe 2 · Tour de France Femmes"
    assert blok["eyebrow"] == "Etappe 3 · Tour de France Femm…"
    assert blok["show_state"] == "Morgen"


def test_dames_erbij_als_de_naam_het_niet_zegt(wt, coordinator, monkeypatch):
    ev = dict(FEMMES, name="Ronde van Vlaanderen", url="race/rvv-vrouwen/2026")
    stages = _stages(ev["url"], ev["name"], [VANDAAG], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))

    blok = _draai(coordinator, PRIMAIR, [_kandidaat(ev, stages)])["races"][1]

    assert blok["label"] == "Ronde van Vlaanderen · Dames"
    assert blok["eyebrow"].endswith("· Dames")


def test_zonder_uitslag_blijft_het_blok_leeg_maar_bestaat_het(
        wt, coordinator, monkeypatch):
    """Een koers die nog moet beginnen krijgt geen verzonnen uitslag."""
    stages = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 20)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag(finished=False))

    uit = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    blok = uit["races"][1]

    assert blok["last_result"] == [] and blok["gc_top"] == []
    assert blok["eyebrow"] == "Etappe 1 · Tour de France Femm…"
    assert uit["other_label"] == ""


def test_oude_attributen_herhalen_de_eerste_koers_met_uitslag(
        wt, coordinator, monkeypatch):
    """`other_*` blijft bestaan voor kaarten van vóór `races`."""
    stages = _stages(FEMMES["url"], FEMMES["name"],
                     [date(2026, 7, 17)], women=True)
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())

    uit = _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])

    assert uit["other_label"] == uit["races"][1]["last_stage_label"]
    assert uit["other_result"] == uit["races"][1]["last_result"]


def test_niet_meer_koersen_dan_de_cap(wt, coordinator, monkeypatch):
    """Elke koers erbij kost verzoeken bij PCS en ruimte in de attributen."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: _uitslag())
    andere = []
    for n in range(wt.MAX_ANDERE_KOERSEN + 2):
        ev = dict(FEMMES, name=f"Koers {n}", url=f"race/koers-{n}/2026")
        andere.append(_kandidaat(ev, _stages(ev["url"], ev["name"], [VANDAAG])))

    uit = _draai(coordinator, PRIMAIR, andere)

    assert len(uit["races"]) == wt.MAX_ANDERE_KOERSEN + 1


def test_afgeronde_etappe_wordt_maar_een_keer_opgehaald(
        wt, coordinator, monkeypatch):
    """Anders zou elke ronde dezelfde uitslag opnieuw opgevraagd worden."""
    opgehaald = []

    def _fetch(url, *a):
        opgehaald.append(url)
        return _uitslag()

    monkeypatch.setattr(wt, "_fetch_stage", _fetch)
    stages = _stages(FEMMES["url"], FEMMES["name"], [date(2026, 7, 17)], women=True)

    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])

    assert len(opgehaald) == 1


def test_lopende_etappe_wordt_niet_bewaard(wt, coordinator, monkeypatch):
    """Een uitslag die nog binnenkomt moet elke ronde opnieuw opgehaald."""
    opgehaald = []

    def _fetch(url, *a):
        opgehaald.append(url)
        return _uitslag(finished=False)

    monkeypatch.setattr(wt, "_fetch_stage", _fetch)
    stages = _stages(FEMMES["url"], FEMMES["name"], [VANDAAG], women=True)

    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])
    _draai(coordinator, PRIMAIR, [_kandidaat(FEMMES, stages)])

    assert len(opgehaald) == 2


def test_koers_die_omvalt_haalt_de_rest_niet_onderuit(wt, coordinator, monkeypatch):
    """Degraderen: een mislukte koers verdwijnt, de andere blijven staan."""
    def _fetch(url, *a):
        if "stuk" in url:
            raise RuntimeError("PCS geeft onzin terug")
        return _uitslag()

    monkeypatch.setattr(wt, "_fetch_stage", _fetch)
    stuk = dict(FEMMES, name="Kapotte Koers", url="race/stuk/2026")
    andere = [
        _kandidaat(stuk, _stages(stuk["url"], stuk["name"], [date(2026, 7, 17)])),
        _kandidaat(FEMMES, _stages(FEMMES["url"], FEMMES["name"],
                                   [date(2026, 7, 17)], women=True)),
    ]

    uit = _draai(coordinator, PRIMAIR, andere)

    assert [r["key"] for r in uit["races"]] == [
        "tour-de-france", "tour-de-france-femmes"]
