"""De weg naar de etappelijst en naar de uitslag, als het vaste adres faalt.

Twee dingen die in september 2026 zichtbaar misgingen:

- **De Tour of Britain toonde alleen de etappe van vandaag.** De kalender
  laat de routekolom voor zes koersen leeg en wijst dan naar de koerspagina.
  Daar staat de etappetabel niet vooraan, dus werd een andere tabel gelezen.
- **Alleen de drie grote rondes hadden een uitslag.** `uitslag_url` eiste
  een `-route`-map in het etappeadres, en die heeft alleen de Giro, de Tour
  en de Vuelta.

De HTML die hier als "routepagina" achter een link hangt is de echte
Vuelta-routepagina uit `tests/fixtures/`. Getest wordt de weg ernaartoe,
niet het lezen van andermans opmaak — dat staat in `test_cyclingstage.py`.
"""
from datetime import date
from pathlib import Path

import pytest

ROUTE = Path(__file__).parent / "fixtures" / "cyclingstage_vuelta_2026_route.html"

KOERS = "https://www.cyclingstage.com/tour-of-britain-2026/"
ROUTEPAGINA = KOERS + "route-gb-2026/"

# Wat de koerspagina van zo'n koers oplevert: links naar de eigen
# subpagina's, en een tabel die de etappetabel níét is.
KOERSPAGINA_HTML = (
    '<table><tr><th>Winners</th></tr>'
    '<tr><td>2025</td><td>Lloyds Tour of Britain</td></tr></table>'
    f'<a href="/tour-of-britain-2026/favourites-gb-2026/">Favourites</a>'
    f'<a href="/tour-of-britain-2026/route-gb-2026/">Route</a>'
    f'<a href="/tour-of-britain-2025/route-gb-2025/">2025</a>'
)


@pytest.fixture
def koers():
    return {"url": KOERS, "name": "Tour of Britain",
            "start": date(2026, 9, 2), "end": date(2026, 9, 6),
            "women": False, "level": "m"}


def _pagina(wt, monkeypatch, paginas):
    """`_haal_html` uit een tabel bedienen en de opgevraagde adressen tellen."""
    opgevraagd = []

    def _haal(url, wat="pagina"):
        opgevraagd.append(url)
        return paginas.get(url, "")

    monkeypatch.setattr(wt, "_haal_html", _haal)
    return opgevraagd


# ── etappelijst ─────────────────────────────────────────────────────


def test_etappelijst_via_de_link_op_de_koerspagina(wt, monkeypatch, koers):
    opgevraagd = _pagina(wt, monkeypatch, {
        KOERS: KOERSPAGINA_HTML,
        ROUTEPAGINA: ROUTE.read_text(),
    })
    etappes = wt._cs_event_stages(koers)
    assert len(etappes) == 21
    assert etappes[0]["race_name"] == "Tour of Britain"
    assert etappes[0]["race_slug"] == "tour-of-britain"
    # de koerspagina eerst, daarna pas de link die daarop stond
    assert opgevraagd[0] == KOERS
    assert ROUTEPAGINA in opgevraagd


def test_niet_meer_dan_drie_kandidaten(wt, monkeypatch, koers):
    """Een koerspagina vol links mag geen verzoekenregen worden."""
    links = "".join(
        f'<a href="/tour-of-britain-2026/pagina-{i}-2026/">x</a>' for i in range(9))
    opgevraagd = _pagina(wt, monkeypatch, {KOERS: links})
    assert wt._cs_event_stages(koers) == []
    # de koerspagina zelf plus hoogstens MAX_ROUTE_KANDIDATEN
    assert len(opgevraagd) == 1 + wt.MAX_ROUTE_KANDIDATEN


def test_koers_zonder_bruikbare_pagina_geeft_leeg(wt, monkeypatch, koers):
    """Niets vinden mag geen uitzondering worden; de koers valt gewoon weg."""
    _pagina(wt, monkeypatch, {})
    assert wt._cs_event_stages(koers) == []


# ── uitslag ─────────────────────────────────────────────────────────


def _etappe(idx=1, **kw):
    d = {"date": date(2026, 9, 2), "idx": idx, "one_day": False,
         "race_slug": "tour-of-britain",
         "stage_url": f"{KOERS}stage-{idx}-gb-2026/"}
    d.update(kw)
    return d


def test_uitslag_via_het_afgeleide_adres(wt, monkeypatch):
    afgeleid = ("https://www.cyclingstage.com/tour-of-britain-2026-results/"
                "stage-1-gb-results-2026/")
    opgevraagd = _pagina(wt, monkeypatch, {afgeleid: "<h2>Stage 1 Results</h2>"})
    url, html = wt._uitslagpagina(_etappe())
    assert url == afgeleid and html
    # het overzicht is niet nodig zolang de afleiding klopt
    assert len(opgevraagd) == 1


def test_uitslag_via_het_overzicht_als_de_afleiding_niets_geeft(wt, monkeypatch):
    """Het afgeleide adres is een aanname; het overzicht is de bron."""
    index = "https://www.cyclingstage.com/tour-of-britain-2026-results/"
    echt = index + "stage-1-britain-results-2026/"
    opgevraagd = _pagina(wt, monkeypatch, {
        index: f'<a href="/tour-of-britain-2026-results/stage-1-britain-results-2026/">Stage 1</a>',
        echt: "<h2>Stage 1 Results</h2>",
    })
    wt._UITSLAGINDEX.clear()
    url, html = wt._uitslagpagina(_etappe())
    assert url == echt and html
    assert index in opgevraagd


def test_het_overzicht_wordt_hoogstens_een_keer_per_dag_gehaald(wt, monkeypatch):
    index = "https://www.cyclingstage.com/tour-of-britain-2026-results/"
    opgevraagd = _pagina(wt, monkeypatch, {})
    wt._UITSLAGINDEX.clear()
    for idx in (1, 2, 3):
        wt._uitslagpagina(_etappe(idx))
    assert opgevraagd.count(index) == 1


def test_eendaagse_koers_leest_zijn_resultatenpagina(wt, monkeypatch):
    """Geen etappenummer, dus geen `stage-N`-adres; de koerspagina heeft het."""
    index = "https://www.cyclingstage.com/paris-roubaix-2026-results/"
    opgevraagd = _pagina(wt, monkeypatch, {index: "<h2>Results</h2>"})
    url, html = wt._uitslagpagina({
        "date": date(2026, 4, 12), "idx": None, "one_day": True,
        "race_slug": "paris-roubaix",
        "stage_url": "https://www.cyclingstage.com/paris-roubaix-2026/route-pr-2026/",
    })
    assert url == index and html
    assert opgevraagd == [index]
