"""Cyclocross uit de sites van drie series (0.33).

Alles op de echte pagina's van 8 november 2026 (via Cowork opgehaald, zie
de README bij elke fixture). De kalenderpagina van de Superprestige, de
uitslagenpagina van de wereldbeker en de manches in Glasgow en Benidorm
kwamen er later op de dag bij.
"""
import asyncio
import importlib
from datetime import date, datetime
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _lees(naam):
    return (FIXTURES / naam).read_text(encoding="utf-8")


PAGINA_S = {
    "https://www.ucicyclocrossworldcup.com/en/calendar": "ucicxworldcup_kalender_cx_2026-11-08.html",
    "https://www.ucicyclocrossworldcup.com/en/calendar/2026-2027/ostrava": "ucicxworldcup_manche_cx_ostrava_2026-11-08.html",
    "https://www.superprestigecyclocross.be/nl/kalender": "superprestige_kalender_cx_2026-11-08.html",
    "https://www.superprestigecyclocross.be/nl/kalender/2026-2027/niel": "superprestige_manche_cx_niel_2026-11-08.html",
    "https://www.superprestigecyclocross.be/nl/uitslagen": "superprestige_uitslagen_cx_2026-11-08.html",
    "https://www.ucicyclocrossworldcup.com/en/results": "ucicxworldcup_uitslagen_cx_2026-11-08.html",
    "https://x2otrofee.be/": "x2otrofee_kalender_en_klassement_cx_2026-11-08.html",
    "https://www.cyclingstage.com/uci/cycling-calendar-2026/": "cyclingstage_kalender_2026.html",
    "https://www.cyclingstage.com/uci/cycling-calendar-2027/": "cyclingstage_kalender_2027_2026-11-08.html",
}


@pytest.fixture
def cx(wt):
    # pas na `wt`: die zet het pakket op het pad
    return importlib.import_module("cycling_next_race.cross")


@pytest.fixture
def web(wt, monkeypatch):
    """`_haal_html` op de fixtures; al het andere is een 404."""
    gevraagd = []

    def haal(url, wat="pagina"):
        gevraagd.append(url)
        naam = PAGINA_S.get(url)
        return _lees(naam) if naam else ""

    monkeypatch.setattr(wt, "_haal_html", haal)
    # de dagcache leunt op de klok van Home Assistant; een test die een
    # andere dag nodig heeft zet hem zelf
    _klok(wt, monkeypatch, datetime(2026, 11, 8, 12, 0))
    wt._CX_DAG.clear()
    wt._CX_DIAG.clear()
    yield gevraagd
    wt._CX_DAG.clear()


def _klok(wt, monkeypatch, nu):
    monkeypatch.setattr(wt.dt_util, "now", lambda: nu)


# ── parsers ──────────────────────────────────────────────────────────

def test_wereldbekerkalender(cx):
    manches = cx.parse_fc_kalender(_lees(PAGINA_S["https://www.ucicyclocrossworldcup.com/en/calendar"]))
    assert len(manches) == 12
    # de eerstvolgende staat er twee keer (bovenaan als "Next round"); één keer tellen
    assert [m["plaats"] for m in manches].count("Ostrava") == 1
    eerste = manches[0]
    assert eerste == {"plaats": "Ostrava", "datum": date(2026, 11, 27),
                      "url": "https://www.ucicyclocrossworldcup.com/en/calendar/2026-2027/ostrava",
                      "land": "Czech Republic"}
    glasgow = next(m for m in manches if m["plaats"] == "Glasgow")
    assert glasgow["land"] == "United Kingdom"


def test_manchepagina_superprestige(cx):
    info = cx.parse_fc_manche(_lees("superprestige_manche_cx_niel_2026-11-08.html"))
    assert info["datum"] == date(2026, 11, 11)
    assert info["land"] == "België"
    assert cx.elite_tijd(info["programma"], vrouwen=False) == "15:10"
    assert cx.elite_tijd(info["programma"], vrouwen=True) == "13:40"
    # de junioren zijn geen elite
    assert "Junioren Mannen" in info["programma"]
    assert info["zenders"]["NLD"] == "Eurosport 1"


def test_manchepagina_wereldbeker(cx):
    info = cx.parse_fc_manche(_lees("ucicxworldcup_manche_cx_ostrava_2026-11-08.html"))
    # Engelse namen en "Doors open" ertussen
    assert cx.elite_tijd(info["programma"], vrouwen=False) == "19:45"
    assert cx.elite_tijd(info["programma"], vrouwen=True) == "18:15"
    assert info["land"] == "Czech Republic"
    assert info["zenders"] == {}


def test_superprestigekalender(cx):
    # het adres in SP_KALENDER_URL was een aanname; dit is de echte pagina
    manches = cx.parse_fc_kalender(_lees(PAGINA_S[cx.SP_KALENDER_URL]))
    assert len(manches) == 8
    assert manches[0] == {"plaats": "Niel", "datum": date(2026, 11, 11),
                          "url": "https://www.superprestigecyclocross.be/nl/kalender/2026-2027/niel",
                          "land": "België"}
    # de gereden manches staan achteraan, niet op datum
    assert [m["plaats"] for m in manches][-2:] == ["Overijse", "Middelkerke"]


@pytest.mark.parametrize("naam, land, zone, vrouwen, mannen", [
    ("glasgow", "United Kingdom", "Europe/London", "12:40", "14:10"),
    ("benidorm", "Spain", "Europe/Madrid", "13:40", "15:10"),
])
def test_manches_buiten_belgie_en_tsjechie(cx, naam, land, zone, vrouwen, mannen):
    info = cx.parse_fc_manche(_lees(f"ucicxworldcup_manche_cx_{naam}_2026-11-08.html"))
    assert info["land"] == land
    assert cx.zone_van(info["land"]) == zone
    assert cx.elite_tijd(info["programma"], vrouwen=True) == vrouwen
    assert cx.elite_tijd(info["programma"], vrouwen=False) == mannen
    # vijf weken vooraf staan er nog geen zenders op
    assert info["zenders"] == {}


def test_glasgow_naar_onze_klok(wt):
    # De pagina zegt "GMT +1", maar Glasgow zit in december op GMT. Als
    # GMT gelezen komen de tijden uit op 13:40 en 15:10, de vaste tv-tijden
    # van de andere manches; zie de README bij de fixture.
    assert wt._iana_naar_lokaal("12:40", "Europe/London", date(2026, 12, 13)) == "13:40"
    assert wt._iana_naar_lokaal("14:10", "Europe/London", date(2026, 12, 13)) == "15:10"


def test_wereldbekeruitslagen_categorieen(cx):
    # zelfde platform als de Superprestige; de podia worden gelezen
    manches = cx.parse_sp_uitslagen(_lees("ucicxworldcup_uitslagen_cx_2026-11-08.html"))
    benidorm = next(m for m in manches if m["datum"] == date(2026, 1, 18))
    mannen = next(r for t, r in benidorm["categorieen"].items() if cx.is_elite(t, False))
    assert [r["rider"] for r in mannen] == [
        "Mathieu van der Poel", "Thibau Nys", "Felipe Orts"]
    assert mannen[1]["time"] == "+00:28"
    # zonder plaatsnaam vindt podium() hem dus al
    assert cx.podium(manches, date(2026, 1, 18), "", vrouwen=True)[0]["rider"] == "Lucinda Brand"


def test_wereldbekeruitslagen_plaats(cx):
    """De wereldbeker zet de plaats in een <p>, de Superprestige in een <h2>.

    Tot 0.33.1 knipte de parser op </h2>, en liep de plaats bij de
    wereldbeker door over de hele manche (dit stond hier als xfail).
    """
    manches = cx.parse_sp_uitslagen(_lees("ucicxworldcup_uitslagen_cx_2026-11-08.html"))
    assert manches[0]["plaats"] == "Tabor"
    assert cx.podium(manches, date(2026, 1, 18), "Benidorm", vrouwen=False)
    # en de Superprestige leest nog steeds goed
    sp = cx.parse_sp_uitslagen(_lees("superprestige_uitslagen_cx_2026-11-08.html"))
    assert sp[0]["plaats"] == "Overijse"


def test_plaatsnaam_met_en_zonder_accent(cx):
    """De kalender schrijft "Tábor", de uitslagenpagina "Tabor"."""
    manches = cx.parse_sp_uitslagen(_lees("ucicxworldcup_uitslagen_cx_2026-11-08.html"))
    mannen = cx.podium(manches, date(2025, 11, 23), "Tábor", vrouwen=False)
    assert [r["rider"] for r in mannen] == [
        "Thibau Nys", "Laurens Sweeck", "Joris Nieuwenhuis"]


def test_superprestige_podium(cx):
    manches = cx.parse_sp_uitslagen(_lees("superprestige_uitslagen_cx_2026-11-08.html"))
    mannen = cx.podium(manches, date(2026, 10, 25), "Overijse", vrouwen=False)
    assert [r["rider"] for r in mannen] == [
        "Michael Vanthourenhout", "Witse Meeussen", "Niels Vandeputte"]
    assert mannen[0]["time"] == "01:03:18"
    # het aanhalingsteken is een secondeteken, geen deel van de tijd
    assert mannen[1]["time"] == "+00:15"
    assert mannen[0]["country"] == "bel"
    vrouwen = cx.podium(manches, date(2026, 10, 25), "Overijse", vrouwen=True)
    assert vrouwen[0]["rider"] == "Lucinda Brand"
    # Overijse van vorig jaar is een andere manche
    assert cx.podium(manches, date(2025, 10, 26), "Overijse", False)[0]["rider"] != ""
    assert cx.podium(manches, date(2026, 11, 11), "Niel", False) == []


def test_x2o_kalender(cx):
    manches = cx.parse_x2o_kalender(_lees("x2otrofee_kalender_en_klassement_cx_2026-11-08.html"))
    assert len(manches) == 8
    assert manches[0] == {"naam": "Koppenbergcross", "plaats": "Oudenaarde",
                          "datum": date(2026, 11, 1), "url": "https://koppenbergcross.be/"}
    assert manches[-1]["datum"] == date(2027, 2, 14)


def test_tijd_ter_plaatse_naar_onze_klok(wt):
    # Glasgow ligt een uur achter op Amsterdam (de testzone)
    assert wt._iana_naar_lokaal("18:15", "Europe/London", date(2026, 12, 13)) == "19:15"
    assert wt._iana_naar_lokaal("19:45", "Europe/Prague", date(2026, 11, 27)) == "19:45"
    # onbekend land: niets omrekenen
    assert wt._iana_naar_lokaal("19:45", "", date(2026, 11, 27)) == "19:45"


# ── kalender, etappes, uitslag ───────────────────────────────────────

def test_kalender_geeft_een_koers_per_geslacht(wt, web):
    koersen = wt._cx_kalender(2026, ["m", "v", "cm", "cv"])
    ostrava = [k for k in koersen if k["name"] == "Wereldbeker Ostrava"]
    assert [k["level"] for k in ostrava] == ["cm", "cv"]
    # het adres is de sleutel van de etappecache: per geslacht anders
    assert len({k["url"] for k in koersen}) == len(koersen)
    assert all(k["bron"] == "cross" for k in koersen)
    # alleen dit jaar: Baal (1 januari 2027) hoort bij volgend jaar
    assert all(k["start"].year == 2026 for k in koersen)
    assert "X²O Koppenbergcross" in {k["name"] for k in koersen}
    assert wt._CX_DIAG["Superprestige"] == 8
    sp = {k["name"] for k in koersen if k.get("serie") == "sp"} or {
        k["name"] for k in koersen if "Niel" in k["name"]}
    assert any("Niel" in n for n in sp)
    assert wt._CX_DIAG["Wereldbeker"] == 12


def test_alleen_cross_vrouwen(wt, web):
    koersen, telling, fouten = wt._fetch_calendar(2026, ["cv"])
    assert koersen and not fouten
    assert {k["level"] for k in koersen} == {"cv"}
    # geen wegkoersen van de vrouwen erbij, en de wegkalender wordt niet eens opgehaald
    assert not any("cyclingstage" in u for u in web)


def test_geen_cross_gekozen_geen_crossverzoeken(wt, web):
    wt._fetch_calendar(2026, ["m", "v"])
    assert all("cyclingstage" in u for u in web)


def test_etappe_van_een_wereldbekermanche(wt, web):
    koers = next(k for k in wt._cx_kalender(2026, ["cv"])
                 if k["name"] == "Wereldbeker Ostrava")
    [etappe] = wt._cx_etappes(koers)
    assert etappe["start_time"] == "18:15"
    assert etappe["onderdeel"] == "Elite vrouwen"
    assert etappe["eigen_pagina"] is False
    assert etappe["distance_km"] is None
    assert wt._etappe_label(etappe) == "Elite vrouwen"


def test_etappe_van_een_superprestigemanche(wt, web):
    koers = {"name": "Superprestige Niel", "start": date(2026, 11, 11),
             "end": date(2026, 11, 11), "women": False, "level": "cm",
             "bron": "cross", "serie": "sp", "plaats": "Niel", "land": "België",
             "url": "https://www.superprestigecyclocross.be/nl/kalender/2026-2027/niel#mannen",
             "manche_url": "https://www.superprestigecyclocross.be/nl/kalender/2026-2027/niel"}
    [etappe] = wt._cx_etappes(koers)
    assert etappe["start_time"] == "15:10"
    assert etappe["zenders"] == [{"name": "Eurosport 1", "time": "", "logo": ""}]
    # mannen en vrouwen delen de manchepagina: één verzoek
    wt._cx_etappes({**koers, "women": True, "level": "cv",
                    "url": koers["url"].replace("#mannen", "#vrouwen")})
    assert web.count(koers["manche_url"]) == 1


def test_uitslag_superprestige(wt, web, monkeypatch):
    _klok(wt, monkeypatch, datetime(2026, 11, 8, 12, 0))
    etappe = {"date": date(2026, 10, 25), "serie": "sp", "plaats": "Overijse",
              "women": True, "start_time": "13:40", "bron": "cross"}
    uit = wt._cx_uitslag(etappe, 10, 10)
    assert uit["finished"] is True
    assert uit["results"][0]["rider"] == "Lucinda Brand"
    assert uit["gc"] == []


def test_uitslag_wereldbeker(wt, web, monkeypatch):
    _klok(wt, monkeypatch, datetime(2026, 11, 8, 12, 0))
    etappe = {"date": date(2026, 1, 18), "serie": "wb", "plaats": "Benidorm",
              "women": True, "start_time": "11:00", "bron": "cross"}
    uit = wt._cx_uitslag(etappe, 10, 10)
    assert uit["finished"] is True
    assert uit["results"][0]["rider"] == "Lucinda Brand"
    assert uit["result_url"] == "https://www.ucicyclocrossworldcup.com/en/results"


def test_uitslag_wereldbeker_die_er_nog_niet_is(wt, web, monkeypatch):
    # Ostrava, de avond zelf, vóór de start: niet gevonden en niet opnieuw
    # gezocht (dat gebeurt pas na de start)
    _klok(wt, monkeypatch, datetime(2026, 11, 27, 17, 0))
    uit = wt._cx_uitslag({"date": date(2026, 11, 27), "serie": "wb",
                          "plaats": "Ostrava", "women": False,
                          "start_time": "19:45", "bron": "cross"}, 10, 10)
    assert uit["results"] == [] and not uit["finished"]
    assert web.count("https://www.ucicyclocrossworldcup.com/en/results") == 1


def test_uitslag_x2o_blijft_leeg(wt, web):
    uit = wt._cx_uitslag({"date": date(2026, 11, 15), "serie": "x2o",
                          "women": False, "bron": "cross"}, 10, 10)
    assert uit["results"] == [] and not uit["finished"]
    assert not web   # er is geen pagina om te lezen, dus ook geen verzoek


# ── een hele ronde ───────────────────────────────────────────────────

def _ronde(wt, monkeypatch, nu):
    _klok(wt, monkeypatch, nu)
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        return fn(*args)

    c._job = job

    async def niet_slapen(*_):
        return None

    monkeypatch.setattr(wt.asyncio, "sleep", niet_slapen)
    return asyncio.run(c._async_update_data())


def test_de_dag_voor_ostrava_staat_de_cross_op_de_tegel(wt, web, monkeypatch):
    uit = _ronde(wt, monkeypatch, datetime(2026, 11, 26, 12, 0))
    a = uit["attributes"]
    assert uit["state"] == "Wereldbeker Ostrava"
    assert a["discipline"] == "cross"
    assert a["type"] == "Veldrit"
    assert a["show_state"] == "Morgen"
    assert a["start_time"] == "19:45"         # de mannen gaan voor
    assert a["elevation"] == []
    # de vrouwen van dezelfde manche als eigen knop in de pop-up
    knoppen = [(r["race_name"], r["level"]) for r in a["races"]]
    assert ("Wereldbeker Ostrava", "cv") in knoppen
    # geen enkel verzoek naar een cyclingstage-pagina die bij een cross niet bestaat
    assert [u for u in web if "cyclingstage" in u and "calendar" not in u] == []


@pytest.mark.parametrize("uur, minuut, badge", [
    (19, 30, "Vandaag"), (20, 30, "LIVE"), (21, 30, "Gereden")])
def test_live_venster_van_een_cross(wt, web, monkeypatch, uur, minuut, badge):
    uit = _ronde(wt, monkeypatch, datetime(2026, 11, 27, uur, minuut))
    a = uit["attributes"]
    assert uit["state"] == "Wereldbeker Ostrava"
    assert a["show_state"] == badge
