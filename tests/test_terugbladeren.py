"""Terugbladeren door de uitslagen van eerder gereden etappes (`past`).

De coordinator draait hier zonder netwerk: `_job` roept de functie direct
aan en `_fetch_stage` is vervangen door een teller, zodat ook te zien is
wanneer er een verzoek *niet* gedaan wordt.
"""
import asyncio
from datetime import date

import pytest

VANDAAG = date(2026, 8, 23)


def _stages(n, race_url="https://www.cyclingstage.com/vuelta-2026-route/",
            naam="La Vuelta", women=False):
    """Etappes 1..n, elke dag een, eindigend gisteren."""
    return [{
        "date": date(2026, 8, 22 - (n - i)), "stage_url": f"{race_url}stage-{i}",
        "idx": i, "one_day": False, "race_url": race_url, "race_name": naam,
        "women": women, "level": "v" if women else "m",
        "departure": f"Start {i}", "arrival": f"Finish {i}",
        "distance_km": 180.0,
    } for i in range(1, n + 1)]


@pytest.fixture
def co(wt, monkeypatch):
    c = wt.CyclingCoordinator(hass=None)

    async def _job(fn, *args):
        return fn(*args)

    c._job = _job
    c.opgehaald = []

    def _stage(stage, result_n=10, gc_n=10):
        c.opgehaald.append((stage["stage_url"], result_n, gc_n))
        return {
            "ok": True, "finished": True,
            "departure": stage.get("departure") or "",
            "arrival": stage.get("arrival") or "",
            "distance": stage.get("distance_km"),
            "results": [{"rank": r, "rider": f"Renner {r}", "time": "4:11:02"}
                        for r in range(1, result_n + 1)],
            "gc": [], "points_top": [], "kom_top": [], "youth_top": [],
        }

    monkeypatch.setattr(wt, "_fetch_stage", _stage)
    return c


def _draai(c, stages, overslaan=""):
    return asyncio.run(c._build_past(stages, overslaan, VANDAAG))


def test_de_nieuwste_etappe_staat_vooraan(co):
    uit = _draai(co, _stages(5))
    assert [r["eyebrow"].split(" ")[1] for r in uit] == ["5", "4", "3"]


def test_niet_meer_dan_de_instelling(co):
    assert len(_draai(co, _stages(9))) == 3


def test_nul_zet_het_uit(wt, co, monkeypatch):
    monkeypatch.setattr(co, "_opt", lambda s: 0)
    assert _draai(co, _stages(5)) == []
    assert co.opgehaald == []


def test_de_etappe_die_al_als_last_result_staat_wordt_overgeslagen(co):
    stages = _stages(5)
    uit = _draai(co, stages, stages[-1]["stage_url"])
    assert [r["eyebrow"].split(" ")[1] for r in uit] == ["4", "3", "2"]


def test_kortere_uitslag_dan_de_pop_up(wt, co):
    _draai(co, _stages(4))
    assert all(n == wt.PAST_RESULT_N for _u, n, _g in co.opgehaald)
    # geen klassement: dat staat al bovenaan en zou alleen ruimte kosten
    assert all(g == 0 for _u, _n, g in co.opgehaald)


def test_tweede_ronde_haalt_niets_opnieuw_op(co):
    stages = _stages(4)
    _draai(co, stages)
    aantal = len(co.opgehaald)
    _draai(co, stages)
    assert len(co.opgehaald) == aantal


def test_de_dagwissel_leegt_de_cache_niet(co):
    """Een gereden uitslag verandert niet meer; juist gisteren wordt bekeken."""
    stages = _stages(4)
    _draai(co, stages)
    assert co._past_cache
    assert "_past_cache" not in _daglegers(co)


def _daglegers(c):
    """De caches die `_async_update_data` bij een nieuwe dag leegt."""
    import inspect
    bron = inspect.getsource(type(c)._async_update_data)
    kop = bron.split("self._calendar_fetched = today", 1)[1].split("except", 1)[0]
    return kop


def test_lege_uitslag_komt_niet_in_de_cache(wt, co, monkeypatch):
    monkeypatch.setattr(wt, "_fetch_stage",
                        lambda s, r=10, g=10: {"ok": True, "results": []})
    assert _draai(co, _stages(4)) == []
    assert co._past_cache == {}


def test_een_fout_laat_de_rest_staan(wt, co, monkeypatch):
    echt = wt._fetch_stage

    def _stuk(stage, result_n=10, gc_n=10):
        if stage["idx"] == 4:
            raise RuntimeError("cyclingstage doet niet open")
        return echt(stage, result_n, gc_n)

    monkeypatch.setattr(wt, "_fetch_stage", _stuk)
    uit = _draai(co, _stages(5))
    assert [r["eyebrow"].split(" ")[1] for r in uit] == ["5", "3", "2"]


def test_rijen_dragen_de_koers_en_het_niveau(co):
    rij = _draai(co, _stages(3, women=True))[0]
    assert rij["race_key"] == "vuelta"
    assert rij["level"] == "v"
    assert rij["date"] == "2026-08-22"
    assert rij["departure"] and rij["arrival"]


def test_eendaagse_koers_heet_naar_de_koers(co):
    stages = _stages(1)
    stages[0]["one_day"] = True
    assert _draai(co, stages)[0]["eyebrow"] == "La Vuelta"


def test_dames_erbij_als_de_naam_het_niet_zegt(co):
    uit = _draai(co, _stages(2, naam="Ronde van Zwitserland", women=True))
    assert uit[0]["eyebrow"].endswith("· Dames")


def test_past_staat_in_de_attributen(wt):
    """`past` hoort bij de spoilers, niet bij het spoiler-vrije deel."""
    import inspect
    bron = inspect.getsource(wt.CyclingCoordinator._async_update_data)
    spoiler = bron.split("spoiler (alleen tonen", 1)[1]
    assert '"past": past' in spoiler


def test_geen_pcs_adres_meer_uit_een_etappe_url(wt):
    """`stage_url` is sinds 0.19 een cyclingstage-adres.

    Er een procyclingstats-adres uit bouwen levert
    `procyclingstats.com/https://www.cyclingstage.com/...` op — precies wat
    de live-stip stukmaakte. Deze test bewaakt dat het niet terugkomt.
    """
    import inspect
    import io
    import tokenize

    bron = inspect.getsource(wt)
    # commentaar eruit: de uitleg bij het verdwenen `_fetch_live` noemt het
    # foute adres met zoveel woorden, en dat is juist de bedoeling
    code = []
    for tok in tokenize.generate_tokens(io.StringIO(bron).readline):
        # alléén commentaar; de strings moeten blijven staan, want daar zou
        # het foute adres juist in zitten
        if tok.type != tokenize.COMMENT:
            code.append(tok.string)
    plat = "".join(code)
    assert "procyclingstats.com/{stage" not in plat
    assert "procyclingstats.com/{shown" not in plat


def test_live_attributen_beloven_niets(wt):
    """Zonder bron horen de live-velden leeg te blijven, niet geschat."""
    import inspect
    bron = inspect.getsource(wt.CyclingCoordinator._async_update_data)
    assert '"live_km_to_go": None' in bron
    assert '"live_url": live_url' in bron
    assert 'live_url = ""' in bron
