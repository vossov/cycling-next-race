"""De tv-gids van wielerflits, op de echte pagina.

`tests/fixtures/wielerflits_tv_2026-09-07.html` is
https://www.wielerflits.nl/nieuws/wielrennen-op-tv/ zoals hij op 7 september
2026 was, door de eigenaar opgeslagen in een browser — de proxy in de
ontwikkelomgeving laat wielerflits niet door.

**Tot deze fixture was dit de enige parser in het project die volledig op
verzonnen HTML draaide.** Wat daardoor niet was opgevallen staat hieronder,
elk met een eigen test: de koppeling was al maanden stuk, eendaagse koersen
konden nooit zenders krijgen, en koppelen op slug gaf verkeerde zenders.
"""
from pathlib import Path

import pytest

TV = Path(__file__).parent / "fixtures" / "wielerflits_tv_2026-09-07.html"


@pytest.fixture(scope="module")
def gids():
    return TV.read_text(encoding="utf-8", errors="replace")


def _kort(kanalen):
    return [(c["time"], c["name"]) for c in kanalen]


# ── rittenkoers ─────────────────────────────────────────────────────


def test_etappe_met_een_uitzending(wt, gids):
    assert _kort(wt._parse_channels(gids, "Vuelta a España", 16)) == [
        ("14:45", "HBO Max")]


def test_etappe_met_meerdere_uitzendingen(wt, gids):
    """Etappe 19 staat er drie keer op; Sporza online is alleen Belgisch."""
    assert _kort(wt._parse_channels(gids, "Vuelta a España", 19)) == [
        ("13:15", "HBO Max"), ("13:30", "VRT1")]
    assert "Sporza online" not in str(wt._parse_channels(gids, "Vuelta a España", 19))


def test_elke_etappe_op_de_pagina_wordt_gevonden(wt, gids):
    for etappe in range(16, 22):
        assert wt._parse_channels(gids, "Vuelta a España", etappe), etappe


def test_etappe_die_er_niet_op_staat(wt, gids):
    assert wt._parse_channels(gids, "Vuelta a España", 3) == []


# ── eendaagse koers ─────────────────────────────────────────────────


def test_eendaagse_koers_krijgt_zijn_zenders(wt, gids):
    """Dit werkte nooit.

    Een eendaagse koers staat als `/wielerkalender/{slug}/startlijst`, niet
    als `/wielerkalender/{slug}/etappes/{n}/`. De regex eiste die tweede
    vorm, en `want_stage` viel bovendien terug op "1". Elke eendaagse koers
    — de monumenten, de klassiekers, Québec, Montréal, Lombardije,
    Parijs-Tours — kwam dus zonder zenders binnen.
    """
    assert _kort(wt._parse_channels(gids, "Grand Prix de Québec", None)) == [
        ("16:45", "HBO Max")]
    assert _kort(wt._parse_channels(gids, "Grand Prix de Montréal", None)) == [
        ("16:00", "HBO Max")]


# ── de koers herkennen ──────────────────────────────────────────────


def test_twee_sites_schrijven_de_naam_anders(wt, gids):
    """Wij: "Grand Prix de Québec". Wielerflits: "Grand Prix Cycliste de Québec"."""
    assert wt._zelfde_koers("Grand Prix de Québec", False,
                            "Grand Prix Cycliste de Québec", False)


def test_de_giro_krijgt_niet_de_zenders_van_de_giro_della_toscana(wt, gids):
    """Koppelen op slug-prefix gaf verkeerde zenders, en dat is erger dan geen.

    `giro` is een prefix van `giro-della-toscana-memorial-alfredo-martini-2026`.
    Op de opgeslagen pagina staan die twee naast elkaar, dus dit is geen
    theoretisch geval.
    """
    assert not wt._zelfde_koers("Giro d'Italia", False, "Giro della Toscana", False)
    assert wt._parse_channels(gids, "Giro d'Italia", None) == []


def test_de_tour_krijgt_niet_de_zenders_van_de_tour_femmes(wt):
    """Op woordniveau is "Tour de France" een deelverzameling van "Tour de
    France Femmes"; het geslacht houdt ze uit elkaar."""
    assert not wt._zelfde_koers("Tour de France", False, "Tour de France Femmes", True)
    assert wt._zelfde_koers("Tour de France Femmes", True, "Tour de France Femmes", True)


def test_een_los_woord_matcht_niet_overal(wt):
    """Minstens twee woorden, anders past "Tour" in elke ronde."""
    assert not wt._zelfde_koers("Tour", False, "Tour de France", False)
    assert not wt._zelfde_koers("", False, "Tour de France", False)


def test_koers_die_niet_op_de_pagina_staat(wt, gids):
    assert wt._parse_channels(gids, "Ronde van Vlaanderen", None) == []


# ── de weg die de coordinator gebruikt ──────────────────────────────


def test_channels_from_koppelt_op_naam_niet_op_een_pcs_pad(wt, gids):
    """`_channels_from` matchte op `race/{slug}/{jaar}` — een
    procyclingstats-pad. Sinds 0.19 komt daar een cyclingstage-adres binnen,
    dus die match faalde altijd en élke koers kreeg een lege lijst. De
    tv-gids was stil dood; het viel niet op omdat leeg er hetzelfde uitziet
    als "vandaag niets op tv".
    """
    assert _kort(wt._channels_from(gids, "Vuelta a España", 19, False)) == [
        ("13:15", "HBO Max"), ("13:30", "VRT1")]
    assert wt._channels_from(gids, "", 19, False) == []
    assert wt._channels_from("", "Vuelta a España", 19, False) == []


def test_de_lees_meer_tags_onderaan_tellen_niet_mee(wt, gids):
    """Onderaan staat "Lees meer over: # Coppa Sabatini # Giro della Toscana …",
    met links naar `/wielerkalender/{slug}` zónder achtervoegsel. Zonder de
    eis van `/etappes/{n}/` of `/startlijst` zou de tekst daarna als zenders
    gelezen worden."""
    import re

    kaal = [m for m in re.findall(r'wielerkalender/([^/"\']+)"', gids)]
    assert kaal, "de tag-links zijn verdwenen — is de pagina veranderd?"
    # zo'n koers levert niets op, ook al staat zijn naam op de pagina
    assert wt._parse_channels(gids, "Giro d'Italia", None) == []
