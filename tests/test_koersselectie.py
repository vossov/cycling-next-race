"""Welke koersen er te zien zijn, en in welke kleur.

De kalender die de integratie ophaalt is de WorldTour (mannen en vrouwen).
Met de instellingen zet je daar koersen bij (`extra_races`) of laat je er
koersen af (`hidden_races`); een koers erbij komt standaard alleen in de
pop-up, niet op de tegel. Alles hier draait zonder netwerk.
"""
import asyncio
from datetime import date

import pytest

VANDAAG = date(2026, 8, 5)


def _ev(slug, naam, start, eind=None, **velden):
    """Een kalenderregel zoals `_fetch_calendar` hem oplevert."""
    return {"name": naam, "url": f"race/{slug}/2026", "start": start,
            "end": eind or start, "women": False, **velden}


TOUR = _ev("tour-de-france", "Tour de France", date(2026, 7, 4), date(2026, 7, 26))
POLEN = _ev("tour-de-pologne", "Tour de Pologne", date(2026, 8, 4), date(2026, 8, 10))
DENEMARKEN = _ev("danmark-rundt", "Danmark Rundt", date(2026, 8, 4),
                 date(2026, 8, 8), extra=True)


@pytest.fixture
def coordinator(wt):
    """Een coordinator die niets ophaalt: `_job` roept de functie direct aan."""
    def _maak(opties=None):
        co = wt.CyclingCoordinator(None, opties)

        async def _job(fn, *args):
            return fn(*args)

        co._job = _job
        co._calendar = [POLEN]
        co._calendar_fetched = VANDAAG
        return co

    return _maak


# ── de koersnaam uit wat de gebruiker intikt ────────────────────────

@pytest.mark.parametrize("ingevuld,verwacht", [
    ("danmark-rundt", "danmark-rundt"),
    ("  Danmark-Rundt  ", "danmark-rundt"),
    ("race/danmark-rundt/2026", "danmark-rundt"),
    ("https://www.procyclingstats.com/race/danmark-rundt/2026/stage-3",
     "danmark-rundt"),
    ("https://www.procyclingstats.com/race/danmark-rundt/2026/gc",
     "danmark-rundt"),
    ("", ""),
])
def test_koersnaam_uit_de_invoer(wt, ingevuld, verwacht):
    assert wt._koers_slug(ingevuld) == verwacht


def test_lijst_met_koersen_scheidt_op_komma_en_regel(wt):
    assert wt._lees_koersen("danmark-rundt, tour-of-britain\nrenewi-tour") == [
        "danmark-rundt", "tour-of-britain", "renewi-tour"]


def test_lijst_met_koersen_slaat_rommel_en_dubbelen_over(wt):
    assert wt._lees_koersen(" , ,danmark-rundt,,danmark-rundt , ") == [
        "danmark-rundt"]
    assert wt._lees_koersen(None) == []
    assert wt._lees_koersen(["race/danmark-rundt/2026"]) == ["danmark-rundt"]


# ── de instellingen lezen ───────────────────────────────────────────

def test_schakelaar_leest_ook_tekst(wt, const, coordinator):
    for waarde, verwacht in ((True, True), (False, False), ("true", True),
                             ("", False), (None, False), ("aan", True)):
        co = coordinator({const.CONF_EXTRA_ON_DASHBOARD: waarde})
        assert co._opt_bool(const.CONF_EXTRA_ON_DASHBOARD) is verwacht


def test_zonder_instelling_blijft_de_kalender_zoals_hij_was(wt, coordinator):
    co = coordinator()
    uit = asyncio.run(co._kalender_met_opties(VANDAAG))
    assert [e["url"] for e in uit] == [POLEN["url"]]


def test_koers_erbij_komt_in_de_kalender(wt, const, coordinator, monkeypatch):
    monkeypatch.setattr(wt, "_fetch_extra_race",
                        lambda slug, jaar: dict(DENEMARKEN))
    co = coordinator({const.CONF_EXTRA_RACES: "danmark-rundt"})

    uit = asyncio.run(co._kalender_met_opties(VANDAAG))

    assert {e["url"] for e in uit} == {POLEN["url"], DENEMARKEN["url"]}
    assert [e for e in uit if e.get("extra")], "de koers erbij is niet gemerkt"


def test_koers_die_niet_op_te_halen_is_blijft_gewoon_weg(
        wt, const, coordinator, monkeypatch):
    """Geen uitzondering naar boven, en de rest werkt door."""
    monkeypatch.setattr(wt, "_fetch_extra_race", lambda slug, jaar: None)
    co = coordinator({const.CONF_EXTRA_RACES: "bestaat-niet"})

    uit = asyncio.run(co._kalender_met_opties(VANDAAG))

    assert [e["url"] for e in uit] == [POLEN["url"]]


def test_koers_erbij_wordt_niet_elke_ronde_opnieuw_opgehaald(
        wt, const, coordinator, monkeypatch):
    opgehaald = []

    def _fetch(slug, jaar):
        opgehaald.append(slug)
        return dict(DENEMARKEN)

    monkeypatch.setattr(wt, "_fetch_extra_race", _fetch)
    co = coordinator({const.CONF_EXTRA_RACES: "danmark-rundt"})

    asyncio.run(co._kalender_met_opties(VANDAAG))
    asyncio.run(co._kalender_met_opties(VANDAAG))

    assert opgehaald == ["danmark-rundt"]

    # nieuwe kalenderdag -> wel opnieuw, de data kunnen verschoven zijn
    co._calendar_fetched = date(2026, 8, 6)
    asyncio.run(co._kalender_met_opties(date(2026, 8, 6)))
    assert len(opgehaald) == 2


def test_weggelaten_koers_verdwijnt(wt, const, coordinator):
    co = coordinator({const.CONF_HIDDEN_RACES:
                      "https://www.procyclingstats.com/race/tour-de-pologne/2026"})

    assert asyncio.run(co._kalender_met_opties(VANDAAG)) == []


def test_weglaten_gaat_voor_op_erbij_zetten(wt, const, coordinator, monkeypatch):
    """Wie een koers in beide velden zet, wil hem duidelijk niet zien."""
    monkeypatch.setattr(wt, "_fetch_extra_race",
                        lambda slug, jaar: dict(DENEMARKEN))
    co = coordinator({const.CONF_EXTRA_RACES: "danmark-rundt",
                      const.CONF_HIDDEN_RACES: "danmark-rundt"})

    uit = asyncio.run(co._kalender_met_opties(VANDAAG))

    assert [e["url"] for e in uit] == [POLEN["url"]]


# ── op de tegel of alleen in de pop-up ──────────────────────────────

def test_koers_erbij_hoort_standaard_niet_op_de_tegel(wt, const, coordinator):
    co = coordinator()
    assert co._mag_op_tegel(TOUR) is True
    assert co._mag_op_tegel(DENEMARKEN) is False


def test_koers_erbij_mag_wel_op_de_tegel_als_je_dat_aanzet(
        wt, const, coordinator):
    co = coordinator({const.CONF_EXTRA_ON_DASHBOARD: True})
    assert co._mag_op_tegel(DENEMARKEN) is True


# ── hoeveel koersen er naast de getoonde passen ─────────────────────

def test_aantal_koersen_in_de_popup_is_instelbaar(wt, const, coordinator,
                                                  monkeypatch):
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: {
        "ok": True, "finished": False, "results": [], "gc": [],
        "points_top": [], "kom_top": [], "youth_top": []})
    monkeypatch.setattr(wt, "_fetch_roster", lambda *a: {})

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
    assert wt._leiderstrui("race/tour-de-france/2026") == "#F3C700"
    assert wt._leiderstrui("race/giro-d-italia/2026") == "#E6007E"


def test_onbekende_koers_krijgt_geen_kleur(wt):
    """Liever geen kleur dan een verzonnen kleur."""
    assert wt._leiderstrui("race/danmark-rundt/2026") == ""
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
    monkeypatch.setattr(wt, "_fetch_roster", lambda *a: {})
    co = coordinator()
    stages = [{"date": VANDAAG, "stage_url": f"{TOUR['url']}/stage-1", "idx": 1,
               "one_day": False, "race_url": TOUR["url"],
               "race_name": TOUR["name"], "women": False}]

    blok = asyncio.run(co._race_entry(TOUR, stages, VANDAAG))

    assert blok["jersey"] == "#F3C700"


# ── datums van een koers erbij ──────────────────────────────────────

@pytest.mark.parametrize("waarde,verwacht", [
    ("2026-08-11", date(2026, 8, 11)),
    ("08-11", date(2026, 8, 11)),
    ("", None),
    (None, None),
    ("geen datum", None),
    ("2026-13-40", None),
])
def test_datum_van_procyclingstats(wt, waarde, verwacht):
    assert wt._pcs_datum(waarde, 2026) == verwacht
