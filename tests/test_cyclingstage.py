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


# ── etappelijst ─────────────────────────────────────────────────────

ROUTE = Path(__file__).parent / "fixtures" / "cyclingstage_vuelta_2026_route.html"


@pytest.fixture(scope="module")
def etappes(cs):
    return cs.parse_etappes(ROUTE.read_text(), 2026)


def test_alle_etappes_en_geen_rustdagen(etappes):
    """De Vuelta 2026 heeft 21 etappes en twee rustdagen.

    Rustdagen staan als eigen rij in dezelfde tabel; die horen er niet in,
    want de rest van de integratie rekent elke regel als een etappe.
    """
    assert len(etappes) == 21
    assert [e["idx"] for e in etappes] == list(range(1, 22))


def test_datums_lopen_door_over_de_maandgrens(etappes):
    assert etappes[0]["date"] == date(2026, 8, 22)
    assert etappes[-1]["date"] == date(2026, 9, 13)
    # de rustdag van 31 augustus zit tussen etappe 9 en 10, maar telt niet mee
    assert etappes[8]["date"] == date(2026, 8, 30)
    assert etappes[9]["date"] == date(2026, 9, 1)
    # oplopend, zonder gaten in de nummering
    assert all(a["date"] < b["date"] for a, b in zip(etappes, etappes[1:]))


def test_start_en_finish_los(etappes):
    vier = etappes[3]
    assert vier["departure"] == "Andorra La Vella"
    assert vier["arrival"] == "Andorra La Vella"
    # een plaatsnaam met een koppelteken erin mag niet in tweeën vallen
    zeven = etappes[6]
    assert zeven["departure"] == "Vall d'Alba"
    assert zeven["arrival"] == "Valdelinares"


def test_afstand_en_terrein(etappes):
    assert etappes[0]["distance_km"] == 9.4
    assert etappes[0]["stage_type"] == "itt"
    assert etappes[3]["distance_km"] == 104.8
    assert etappes[3]["stage_type"] == "mountain"
    assert etappes[4]["stage_type"] == "flat"


def test_typefout_op_de_site_wordt_opgevangen(etappes):
    """Etappe 2 staat op cyclingstage als "hils" in plaats van "hills"."""
    assert etappes[1]["stage_type"] == "hilly"


def test_elke_etappe_draagt_zijn_eigen_adres(etappes):
    assert etappes[3]["url"] == (
        "https://www.cyclingstage.com/vuelta-2026-route/stage-4-spain-2026/")
    assert all(e["url"].startswith("https://www.cyclingstage.com/") for e in etappes)


def test_routepagina_zonder_tabel(cs):
    assert cs.parse_etappes("<html><body>nog geen route</body></html>", 2026) == []
    assert cs.parse_etappes("", 2026) == []


# ── de etappetekst ──────────────────────────────────────────────────

ETAPPE4 = Path(__file__).parent / "fixtures" / "cyclingstage_vuelta_2026_stage4.html"


def test_meta_uit_de_etappetekst(cs):
    """Deze drie kwamen tot nu toe van procyclingstats.

    De verwachte finishtijd is zelfs beter dan wat we hadden: die werd
    geschat uit afstand en profiel, en staat hier gewoon op de pagina.
    """
    meta = cs.parse_etappe_meta(ETAPPE4.read_text())
    assert meta == {"start_time": "14:40", "finish_time": "17:30",
                    "vertical_m": 2953}


def test_meta_verzint_niets(cs):
    """Wat er niet staat, komt er niet in."""
    assert cs.parse_etappe_meta("<p>Een etappe zonder tijden.</p>") == {}
    assert cs.parse_etappe_meta("") == {}


def test_hoogtemeters_zonder_duizendtalkomma(cs):
    meta = cs.parse_etappe_meta("<p>a route with 850 metres of climbing</p>")
    assert meta["vertical_m"] == 850


def test_de_bestaande_colparser_leest_deze_pagina(wt, monkeypatch):
    """`_fetch_stage_names` in sensor.py is gebouwd op deze teksten en
    blijft; hier wordt hij op echte HTML nagelopen in plaats van alleen op
    de pagina's die toevallig binnenkwamen."""
    import io
    import urllib.request

    ruw = ETAPPE4.read_bytes()

    class Nep(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: Nep(ruw))
    climbs, route = wt._fetch_stage_names("https://x/", 104.8)

    assert route["departure"] == "Andorra La Vella"
    assert route["arrival"] == "Andorra La Vella"
    assert route["finish_time"] == "17:30"
    namen = [c["name"] for c in climbs]
    assert namen == ["Port d'Envalira", "Collada de Beixalis",
                     "Col d'Ordino", "Alto de la Comella"]
    assert climbs[1]["length_km"] == 6.5 and climbs[1]["steepness_pct"] == 8.5
    # de tekst noemt alleen bij de Ordino hoeveel er nog te gaan is
    assert climbs[2]["km_to_finish"] == 26.1
