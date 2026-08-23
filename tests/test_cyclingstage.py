"""De kalenderparser van cyclingstage, op echte HTML.

`tests/fixtures/cyclingstage_kalender_2026.html` is de pagina
https://www.cyclingstage.com/uci/cycling-calendar-2026/ zoals hij op
23 augustus 2026 was, opgeslagen in een browser. Geen verzonnen HTML: die
heeft in dit project al twee keer een echte bug gemaskeerd.
"""
from datetime import date
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "cyclingstage_kalender_2026.html"


@pytest.fixture(scope="module")
def kalender(cs):
    return cs.parse_kalender(FIXTURE.read_text(), 2026)


def _zoek(kalender, naam):
    for k in kalender:
        if k["name"] == naam:
            return k
    raise AssertionError(f"{naam} staat niet in de kalender")


def test_alle_koersen_komen_eruit(kalender):
    # tien maandtabellen, 49 koersen; verandert dit getal, dan is de pagina
    # veranderd en hoort de fixture ververst te worden
    assert len(kalender) == 49


def test_datums_lopen_niet_achteruit(kalender):
    krom = [k["name"] for k in kalender if k["end"] < k["start"]]
    assert krom == []


def test_koers_van_een_dag(kalender):
    lbl = _zoek(kalender, "Liège - Bastogne - Liège")
    assert lbl["start"] == date(2026, 4, 26)
    assert lbl["end"] == lbl["start"]


def test_koers_binnen_een_maand(kalender):
    renewi = _zoek(kalender, "Renewi Tour")
    assert (renewi["start"], renewi["end"]) == (date(2026, 8, 19), date(2026, 8, 23))


def test_koers_over_een_maandgrens(kalender):
    """De Vuelta staat als "8/22-13" in de tabel van september.

    Zonder het maandvoorvoegsel zou hij van 22 september tot 13 september
    lopen — een koers die achteruit rijdt.
    """
    vuelta = _zoek(kalender, "Vuelta a España")
    assert (vuelta["start"], vuelta["end"]) == (date(2026, 8, 22), date(2026, 9, 13))

    giro_w = _zoek(kalender, "Giro d'Italia Women")
    assert (giro_w["start"], giro_w["end"]) == (date(2026, 5, 30), date(2026, 6, 7))


def test_vrouwenkoersen_worden_herkend(kalender):
    for naam in ("Strade Bianche Donne", "Vuelta Femenina", "Giro d'Italia Women",
                 "Tour de France Femmes", "Paris - Roubaix Femmes",
                 "Amstel Gold Race (w)", "Tour of Flanders (w)"):
        assert _zoek(kalender, naam)["women"], naam

    for naam in ("Vuelta a España", "Paris - Roubaix", "Renewi Tour",
                 "Amstel Gold Race (m)", "Tour of Flanders (m)"):
        assert not _zoek(kalender, naam)["women"], naam


def test_geslacht_ook_uit_het_adres(cs):
    """Twee onafhankelijke signalen; één ervan volstaat."""
    html = ('<table><tr><td class="right">5</td>'
            '<td><a href="/ronde-van-drenthe-2026-women/">Ronde van Drenthe</a></td>'
            '<td>NL</td><td><a href="/ronde-van-drenthe-2026-women/route-rvd/">'
            'Route</a></td></tr></table>')
    koers, = cs.parse_kalender(html, 2026)
    assert koers["women"], "de naam zegt niets, het adres wel"


def test_route_adres_staat_erbij(kalender):
    vuelta = _zoek(kalender, "Vuelta a España")
    assert vuelta["route_url"] == (
        "https://www.cyclingstage.com/vuelta-2026-route/spain-route-2026/")
    # relatieve adressen worden volledig gemaakt
    assert all(not k["route_url"] or k["route_url"].startswith("https://")
               for k in kalender)


def test_koersen_zonder_route_blijven_staan(kalender):
    """Later in het seizoen is de route nog niet gepubliceerd."""
    zonder = [k["name"] for k in kalender if not k["route_url"]]
    assert "Tour of Lombardy" in zonder
    assert len(zonder) == 6


def test_kapotte_link_op_de_pagina_wordt_genegeerd(kalender):
    """Cyclingstage heeft bij de Tour de France Femmes een link die geen
    adres is (`http://Tour de France Femmes 2026`). Die telt niet mee, maar
    de koers zelf blijft staan omdat zijn routeadres wél klopt."""
    tdff = _zoek(kalender, "Tour de France Femmes")
    assert tdff["url"] == ""
    assert tdff["route_url"].endswith("/route-tdf-2026-women/")
    assert tdff["women"]


def test_onzin_levert_een_lege_lijst(cs):
    assert cs.parse_kalender("", 2026) == []
    assert cs.parse_kalender("<html><body>niets</body></html>", 2026) == []


def test_onmogelijke_datum_laat_de_rest_heel(cs):
    html = ('<h2>February</h2><table>'
            '<tr><td class="right">31</td><td><a href="/x/">Koers X</a></td>'
            '<td>NL</td><td><a href="/x/route/">Route</a></td></tr>'
            '<tr><td class="right">3</td><td><a href="/y/">Koers Y</a></td>'
            '<td>NL</td><td><a href="/y/route/">Route</a></td></tr></table>')
    koersen = cs.parse_kalender(html, 2026)
    assert [k["name"] for k in koersen] == ["Koers Y"]
