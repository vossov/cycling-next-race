"""Het bronnenregister: welke koers wordt door welk platform bediend.

Hier mag met een verzonnen bron worden gewerkt: dit test óns eigen contract
tussen sensor.py en een bron, niet het lezen van andermans pagina's. Voor dat
laatste geldt onverkort dat er echte, opgeslagen HTML aan te pas moet komen.
"""
from datetime import date

import pytest

VANDAAG = date(2026, 9, 3)


@pytest.fixture
def bronnen(wt, bronnen_mod):
    """Het register schoon achterlaten; het is moduleniveau-toestand."""
    mod = bronnen_mod
    bewaard = dict(mod.BRONNEN)
    extra = list(mod.EXTRA_KOERSEN)
    yield mod
    mod.BRONNEN.clear()
    mod.BRONNEN.update(bewaard)
    mod.EXTRA_KOERSEN[:] = extra


def _etappe(bron=None):
    e = {"date": VANDAAG, "stage_url": "u", "idx": 1, "one_day": False,
         "race_url": "r", "race_name": "Ronde van Ergens", "women": False,
         "level": "m"}
    if bron:
        e["bron"] = bron
    return e


# ── de standaardbron ──────────────────────────────────────────────


def test_cyclingstage_is_aangemeld(bronnen):
    assert bronnen.STANDAARD == "cyclingstage"
    assert "cyclingstage" in bronnen.BRONNEN


def test_koers_zonder_bron_valt_terug_op_de_standaard(bronnen):
    """Een kalender uit een oudere versie draagt geen `bron`."""
    assert bronnen.bron_van({"name": "x"}).naam == "cyclingstage"


def test_onbekende_bron_geeft_niets(bronnen):
    assert bronnen.bron_van({"name": "x", "bron": "bestaat-niet"}) is None


# ── een tweede bron erbij ─────────────────────────────────────────


def test_eigen_bron_levert_de_etappes(wt, bronnen):
    gezien = []

    def _etappes(koers):
        gezien.append(koers["name"])
        return [_etappe()]

    bronnen.registreer(bronnen.Bron("organisator", _etappes, lambda *a: {}))
    uit = wt._event_stages({"name": "Ronde van Ergens", "bron": "organisator"})

    assert gezien == ["Ronde van Ergens"]
    assert len(uit) == 1
    # de etappe onthoudt zelf waar hij vandaan kwam
    assert uit[0]["bron"] == "organisator"


def test_de_etappe_mag_zijn_eigen_bron_houden(wt, bronnen):
    """Een bron die etappes uit een ander platform doorgeeft."""
    bronnen.registreer(bronnen.Bron(
        "organisator", lambda k: [_etappe(bron="ergens-anders")], lambda *a: {}))
    uit = wt._event_stages({"name": "x", "bron": "organisator"})
    assert uit[0]["bron"] == "ergens-anders"


def test_uitslag_gaat_naar_de_bron_van_de_etappe(wt, bronnen):
    bronnen.registreer(bronnen.Bron(
        "organisator", lambda k: [],
        lambda e, r, g: {"ok": True, "finished": True,
                         "results": [{"rank": 1, "rider": "Iemand"}] * r}))
    uit = wt._fetch_stage(_etappe(bron="organisator"), 3, 5)
    assert uit["ok"] and len(uit["results"]) == 3


# ── falen mag de rest niet meenemen ───────────────────────────────


def test_stukke_bron_geeft_een_lege_etappelijst(wt, bronnen):
    def _stuk(koers):
        raise RuntimeError("organisatorsite ligt eruit")

    bronnen.registreer(bronnen.Bron("organisator", _stuk, lambda *a: {}))
    assert wt._event_stages({"name": "x", "bron": "organisator"}) == []


def test_stukke_uitslag_geeft_een_lege_uitslag(wt, bronnen):
    def _stuk(e, r, g):
        raise RuntimeError("time-out")

    bronnen.registreer(bronnen.Bron("organisator", lambda k: [], _stuk))
    uit = wt._fetch_stage(_etappe(bron="organisator"))
    assert uit["ok"] is False and uit["finished"] is False and uit["results"] == []


def test_onbekende_bron_geeft_een_lege_uitslag_en_geen_fout(wt, bronnen):
    uit = wt._fetch_stage(_etappe(bron="bestaat-niet"))
    assert uit["results"] == []
    # de aanroepers lezen deze sleutels zonder te kijken of ze bestaan
    for sleutel in ("ok", "finished", "gc", "points_top", "kom_top",
                    "youth_top", "distance", "stage_type"):
        assert sleutel in uit


def test_lege_uitslag_kent_dezelfde_sleutels_als_een_echte(wt, bronnen):
    """Anders struikelt een aanroeper juist wanneer het misgaat."""
    leeg = wt._lege_uitslag(_etappe())
    echt = wt._cs_fetch_stage({"stage_url": ""})
    assert set(leeg) == set(echt)


# ── handmatige koersen ────────────────────────────────────────────


def _extra(**kw):
    basis = {"name": "Ronde van Ergens", "start": date(2026, 9, 2),
             "end": date(2026, 9, 6), "women": False, "level": "m",
             "bron": "organisator", "url": "https://organisator.nl/2026/"}
    basis.update(kw)
    return basis


def test_extra_koers_van_dit_jaar_komt_mee(bronnen):
    bronnen.EXTRA_KOERSEN[:] = [_extra()]
    uit = bronnen.extra_koersen(2026, ["m", "v"])
    assert [k["name"] for k in uit] == ["Ronde van Ergens"]


def test_extra_koers_van_een_ander_jaar_niet(bronnen):
    bronnen.EXTRA_KOERSEN[:] = [_extra()]
    assert bronnen.extra_koersen(2027, ["m"]) == []


def test_extra_koers_van_een_uitgezet_niveau_niet(bronnen):
    bronnen.EXTRA_KOERSEN[:] = [_extra()]
    assert bronnen.extra_koersen(2026, ["v"]) == []


def test_de_lijst_zelf_blijft_ongemoeid(bronnen):
    """De aanroeper mag erin schrijven zonder het register te vervuilen."""
    bronnen.EXTRA_KOERSEN[:] = [_extra()]
    uit = bronnen.extra_koersen(2026, ["m"])
    uit[0]["name"] = "Aangepast"
    assert bronnen.EXTRA_KOERSEN[0]["name"] == "Ronde van Ergens"


def test_standaard_is_leeg(bronnen):
    """Een koers zonder werkende bron zou stil verdwijnen; niet vast zetten."""
    assert bronnen.EXTRA_KOERSEN == [] or all(
        k.get("bron") in bronnen.BRONNEN for k in bronnen.EXTRA_KOERSEN)
