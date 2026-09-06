"""Welke niveaus er te zien zijn, en in welke kleur de knoppen staan.

De integratie haalt de kalender per niveau op (bij procyclingstats het
`circuit=`-nummer). `levels` mag op de tegel én in de pop-up, `levels_popup`
alleen in de pop-up. Alles hier draait zonder netwerk.
"""
import asyncio
from datetime import date
from pathlib import Path

import pytest

VANDAAG = date(2026, 8, 5)

WT_M, WT_V = "m", "v"


def _ev(slug, naam, start, eind=None, niveau=WT_M, vrouwen=False):
    """Een kalenderregel zoals `_fetch_calendar` hem oplevert."""
    return {"name": naam,
            "url": f"https://www.cyclingstage.com/{slug}-2026-route/",
            "slug": slug, "start": start,
            "end": eind or start, "women": vrouwen, "level": niveau}


POLEN = _ev("tour-de-pologne", "Tour de Pologne", date(2026, 8, 4),
            date(2026, 8, 10))
DENEMARKEN = _ev("danmark-rundt", "Danmark Rundt", date(2026, 8, 4),
                 date(2026, 8, 8), niveau=WT_V, vrouwen=True)


@pytest.fixture
def coordinator(wt, monkeypatch):
    """Een coordinator die niets ophaalt: `_job` roept de functie direct aan."""
    monkeypatch.setattr(wt, "_fetch_tv_html", lambda *a: "")

    def _maak(opties=None):
        co = wt.CyclingCoordinator(None, opties)

        async def _job(fn, *args):
            return fn(*args)

        co._job = _job
        return co

    return _maak


# ── de opgeslagen keuze lezen ───────────────────────────────────────

def test_zonder_keuze_geldt_de_worldtour(wt, const, coordinator):
    co = coordinator()
    assert co._niveaus_tegel == const.DEFAULT_LEVELS
    assert co._niveaus_alles == const.DEFAULT_LEVELS


def test_niveau_alleen_in_de_popup_wordt_wel_opgehaald(wt, const, coordinator):
    co = coordinator({const.CONF_LEVELS_POPUP: [WT_V]})

    assert co._niveaus_tegel == [WT_M, WT_V]
    assert co._niveaus_alles == [WT_M, WT_V]


def test_hetzelfde_niveau_twee_keer_telt_een_keer(wt, const, coordinator):
    co = coordinator({const.CONF_LEVELS: [WT_M], const.CONF_LEVELS_POPUP: [WT_M]})
    assert co._niveaus_alles == [WT_M]


def test_onbekend_niveau_valt_weg(wt, const, coordinator):
    """Een nummer dat we niet kennen levert toch niets op."""
    co = coordinator({const.CONF_LEVELS: [WT_M, "999"]})
    assert co._niveaus_tegel == [WT_M]


def test_alles_uitgevinkt_valt_terug_op_de_worldtour(wt, const, coordinator):
    """Liever de standaard dan een sensor die niets meer te melden heeft."""
    co = coordinator({const.CONF_LEVELS: []})
    assert co._niveaus_tegel == const.DEFAULT_LEVELS


def test_opgeslagen_tekst_wordt_ook_gelezen(wt, const, coordinator):
    """HA slaat een keuzelijst als lijst op; oudere opslag kan tekst zijn."""
    co = coordinator({const.CONF_LEVELS: "1, 24"})
    assert co._niveaus_tegel == [WT_M, WT_V]


# ── op de tegel of alleen in de pop-up ──────────────────────────────

def test_niveau_uit_de_popup_hoort_niet_op_de_tegel(wt, const, coordinator):
    co = coordinator({const.CONF_LEVELS: [WT_M], const.CONF_LEVELS_POPUP: [WT_V]})

    assert co._mag_op_tegel(POLEN) is True
    assert co._mag_op_tegel(DENEMARKEN) is False


def test_niveau_op_het_dashboard_mag_de_tegel_pakken(wt, const, coordinator):
    co = coordinator({const.CONF_LEVELS: [WT_M, WT_V, WT_V]})
    assert co._mag_op_tegel(DENEMARKEN) is True


def test_koers_zonder_niveau_wordt_niet_uitgesloten(wt, coordinator):
    """Een kalender uit een oudere versie kent het veld nog niet."""
    co = coordinator()
    assert co._mag_op_tegel({"url": "https://www.cyclingstage.com/x-2026-route/"}) is True


# ── de kalender per niveau ──────────────────────────────────────────
#
# Sinds 0.19 komt de kalender van cyclingstage. Deze tests draaien op de
# échte pagina uit tests/fixtures/, niet op een nagebouwde tabel — dat is
# waarom ze mogen vaststellen dat de Vuelta van 22 augustus tot 13 september
# loopt.

KALENDER_HTML = (Path(__file__).parent / "fixtures"
                 / "cyclingstage_kalender_2026.html").read_text()


@pytest.fixture
def nep_kalender(wt, monkeypatch):
    """`_fetch_calendar` de opgeslagen kalenderpagina laten lezen."""
    monkeypatch.setattr(wt, "_haal_html", lambda url, wat="": KALENDER_HTML)


def test_kalender_haalt_alleen_de_gekozen_niveaus(wt, nep_kalender):
    mannen, telling, _ = wt._fetch_calendar(2026, ["m"])
    assert all(not k["women"] for k in mannen)
    assert telling == {"Mannen": 38}

    vrouwen, telling, _ = wt._fetch_calendar(2026, ["v"])
    assert all(k["women"] for k in vrouwen)
    assert telling == {"Vrouwen": 11}

    beide, telling, _ = wt._fetch_calendar(2026, ["m", "v"])
    assert len(beide) == 49
    assert telling == {"Mannen": 38, "Vrouwen": 11}


def test_elke_koers_draagt_zijn_niveau_en_geslacht(wt, nep_kalender):
    koersen, _, _ = wt._fetch_calendar(2026, ["m", "v"])
    vuelta = next(k for k in koersen if k["name"] == "Vuelta a España")
    assert (vuelta["level"], vuelta["women"]) == ("m", False)
    femenina = next(k for k in koersen if k["name"] == "Vuelta Femenina")
    assert (femenina["level"], femenina["women"]) == ("v", True)


def test_elke_koers_draagt_zijn_slug(wt, nep_kalender):
    """De slug komt uit het adres in de kalender, niet uit een tabel."""
    koersen, _, _ = wt._fetch_calendar(2026, ["m", "v"])
    slugs = {k["name"]: k["slug"] for k in koersen}
    assert slugs["Vuelta a España"] == "vuelta"
    assert slugs["Giro d'Italia"] == "giro"
    assert slugs["Tour of Flanders (w)"] == "tour-of-flanders-women"
    assert all(s and "2026" not in s for s in slugs.values())


def test_datums_komen_uit_de_kalenderregel(wt, nep_kalender):
    koersen, _, _ = wt._fetch_calendar(2026, ["m"])
    vuelta = next(k for k in koersen if k["name"] == "Vuelta a España")
    assert (vuelta["start"], vuelta["end"]) == (date(2026, 8, 22), date(2026, 9, 13))
    lombardije = next(k for k in koersen if k["name"] == "Tour of Lombardy")
    assert lombardije["start"] == lombardije["end"] == date(2026, 10, 10)


def test_koersen_staan_op_datum(wt, nep_kalender):
    koersen, _, _ = wt._fetch_calendar(2026, ["m", "v"])
    assert [k["start"] for k in koersen] == sorted(k["start"] for k in koersen)


def test_onbekend_niveau_wordt_overgeslagen(wt, nep_kalender):
    koersen, telling, _ = wt._fetch_calendar(2026, ["m", "999"])
    assert telling == {"Mannen": 38}
    assert koersen


def test_kalenderpagina_die_niet_binnenkomt(wt, monkeypatch, caplog):
    import logging
    monkeypatch.setattr(wt, "_haal_html", lambda url, wat="": "")
    monkeypatch.setattr(wt, "_LAATSTE_KALENDERFOUT", "")
    with caplog.at_level(logging.WARNING, logger="cycling_next_race.sensor"):
        koersen, telling, fouten = wt._fetch_calendar(2026, ["m"])
    assert koersen == [] and telling == {}
    assert fouten and "kwam niet binnen" in fouten[0]
    assert [r for r in caplog.records if "Kalender" in r.message]


def test_zelfde_kalenderfout_logt_maar_een_keer(wt, monkeypatch, caplog):
    """Een bron die eruit ligt hoort het logboek niet vol te schrijven."""
    import logging
    monkeypatch.setattr(wt, "_haal_html", lambda url, wat="": "")
    monkeypatch.setattr(wt, "_LAATSTE_KALENDERFOUT", "")
    with caplog.at_level(logging.WARNING, logger="cycling_next_race.sensor"):
        wt._fetch_calendar(2026, ["m"])
        eerste = len(caplog.records)
        caplog.clear()
        wt._fetch_calendar(2026, ["m"])
        tweede = len(caplog.records)
    assert eerste == 1 and tweede == 0


# ── hoeveel koersen er naast de getoonde passen ─────────────────────

def test_aantal_koersen_in_de_popup_is_instelbaar(wt, const, coordinator,
                                                  monkeypatch):
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: {
        "ok": True, "finished": False, "results": [], "gc": [],
        "points_top": [], "kom_top": [], "youth_top": []})

    andere = []
    for n in range(4):
        ev = _ev(f"koers-{n}", f"Koers {n}", VANDAAG)
        andere.append((VANDAAG, 0, 0, n, ev, [{
            "date": VANDAAG, "stage_url": f"{ev['url']}/stage-1", "idx": 1,
            "one_day": False, "race_url": ev["url"], "race_name": ev["name"],
            "women": False}]))
    primair = {"key": "tour-de-france", "label": "Tour", "race_name": "Tour",
               "women": False}

    for gevraagd in (0, 1, 3):
        co = coordinator({const.CONF_MAX_OTHER: gevraagd})
        uit = asyncio.run(co._races_block(primair, andere, VANDAAG))
        assert len(uit["races"]) == gevraagd + 1


# ── kleur van de leiderstrui ────────────────────────────────────────

def test_bekende_koersen_krijgen_hun_truikleur(wt):
    assert wt._leiderstrui("tour-de-france") == "#F3C700"
    assert wt._leiderstrui("giro") == "#E6007E"


def test_onbekende_koers_krijgt_geen_kleur(wt):
    """Liever geen kleur dan een verzonnen kleur."""
    assert wt._leiderstrui("danmark-rundt") == ""
    assert wt._leiderstrui("") == ""


def test_truikleuren_zijn_geldige_hexkleuren(wt):
    import re
    for slug, kleur in wt.LEIDERSTRUI.items():
        assert re.match(r"^#[0-9A-F]{6}$", kleur), f"{slug}: {kleur}"


def test_koersblok_draagt_de_truikleur_mee(wt, coordinator, monkeypatch):
    """De kaart kleurt de knop ermee; zonder dit veld blijft hij grijs."""
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: {
        "ok": True, "finished": False, "results": [], "gc": [],
        "points_top": [], "kom_top": [], "youth_top": []})
    co = coordinator()
    tour = _ev("tour-de-france", "Tour de France", VANDAAG)
    stages = [{"date": VANDAAG, "stage_url": f"{tour['url']}/stage-1", "idx": 1,
               "one_day": False, "race_url": tour["url"],
               "race_name": tour["name"], "women": False}]

    blok = asyncio.run(co._race_entry(tour, stages, VANDAAG))

    assert blok["jersey"] == "#F3C700"


# ── welke koers de tegel krijgt ─────────────────────────────────────

def _nxt(ev):
    return {"date": VANDAAG, "stage_url": f"{ev['url']}/stage-3", "idx": 3,
            "one_day": False, "race_url": ev["url"], "race_name": ev["name"],
            "women": bool(ev.get("women")), "level": ev.get("level", WT_M),
            "profile_icon": "", "name": "Etappe 3"}


def test_grote_ronde_gaat_voor_op_een_koers_met_profiel(wt, coordinator):
    """De Renewi Tour kreeg voorrang op de Vuelta omdat die wél een
    hoogteprofiel had. Een bestand dat niet laadt hoort niet te bepalen welke
    koers de belangrijkste is."""
    co = coordinator()
    vuelta = _ev("vuelta", "La Vuelta ciclista a España", VANDAAG)
    renewi = _ev("renewi-tour", "Renewi Tour", VANDAAG)
    # de Vuelta heeft geen profiel, de Renewi Tour wel
    co._gpx_beschikbaar[_nxt(vuelta)["stage_url"]] = False
    co._gpx_beschikbaar[_nxt(renewi)["stage_url"]] = True

    sleutels = sorted([co._keuzesleutel(renewi, _nxt(renewi), 0),
                       co._keuzesleutel(vuelta, _nxt(vuelta), 1)])
    assert sleutels[0] == co._keuzesleutel(vuelta, _nxt(vuelta), 1)


def test_profiel_beslist_nog_steeds_tussen_gelijke_koersen(wt, coordinator):
    """Alleen de grote ronde is erbij gekomen; de rest van de volgorde blijft."""
    co = coordinator()
    met = _ev("renewi-tour", "Renewi Tour", VANDAAG)
    zonder = _ev("tour-of-britain", "Tour of Britain", VANDAAG)
    co._gpx_beschikbaar[_nxt(met)["stage_url"]] = True
    co._gpx_beschikbaar[_nxt(zonder)["stage_url"]] = False

    sleutels = sorted([co._keuzesleutel(zonder, _nxt(zonder), 0),
                       co._keuzesleutel(met, _nxt(met), 1)])
    assert sleutels[0] == co._keuzesleutel(met, _nxt(met), 1)


def test_een_eerdere_etappedatum_wint_van_alles(wt, coordinator):
    co = coordinator()
    ronde = _ev("vuelta", "Vuelta", VANDAAG)
    morgen = dict(_nxt(ronde), date=date(2026, 8, 6))
    ander = _ev("renewi-tour", "Renewi Tour", VANDAAG)
    assert co._keuzesleutel(ander, _nxt(ander), 9) < co._keuzesleutel(ronde, morgen, 0)


def test_grote_rondes_zijn_er_drie(wt):
    assert wt._is_grote_ronde("vuelta")
    assert wt._is_grote_ronde("giro")
    assert wt._is_grote_ronde("tour-de-france")
    # de rondes van een week bij de vrouwen horen er bewust niet bij
    assert not wt._is_grote_ronde("vuelta-femenina")
    assert not wt._is_grote_ronde("renewi-tour")
    assert not wt._is_grote_ronde("")


def test_koersblok_leest_de_koers_achteraan_de_sleutel(wt, coordinator):
    """`_races_block` pakt ev en stages van achteren, zodat een sleutel erbij
    de uitpakking niet stukmaakt.

    Dat ging bijna mis toen de grote ronde als sorteersleutel werd toegevoegd:
    de lus pakte de tuple met een vast aantal namen uit. `_races_block` vangt
    een fout per blok af, dus zoiets valt niet op als een fout maar als een
    koers die stilletjes uit de pop-up verdwijnt — vandaar dat `_race_entry`
    hier wordt vervangen en de aanroep zelf wordt nagekeken.
    """
    co = coordinator()
    ev = _ev("renewi-tour", "Renewi Tour", VANDAAG)
    gezien = []

    async def _entry(event, stages, today):
        gezien.append((event, stages))
        return {"label": event["name"], "last_result": [], "gc_top": [],
                "last_stage_label": ""}

    co._race_entry = _entry
    kandidaat = co._keuzesleutel(ev, _nxt(ev), 0) + (ev, [_nxt(ev)])
    uit = asyncio.run(co._races_block(
        {"key": "vuelta", "label": "Vuelta", "race_name": "Vuelta",
         "women": False}, [kandidaat], VANDAAG))
    assert [r.get("label") for r in uit["races"]] == ["Vuelta", "Renewi Tour"]
    assert gezien and gezien[0][0] is ev and gezien[0][1][0]["idx"] == 3


# ── niet blijven roepen bij een blokkade die blijft ─────────────────

@pytest.fixture(autouse=True)
def _kalenderfout_vergeten(wt):
    wt._LAATSTE_KALENDERFOUT = ""
    yield
    wt._LAATSTE_KALENDERFOUT = ""


