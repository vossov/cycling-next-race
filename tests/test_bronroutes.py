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
import asyncio
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
    opgevraagd = _pagina(wt, monkeypatch, {afgeleid: UITSLAG})
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
        echt: UITSLAG,
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
    opgevraagd = _pagina(wt, monkeypatch, {index: UITSLAG})
    url, html = wt._uitslagpagina({
        "date": date(2026, 4, 12), "idx": None, "one_day": True,
        "race_slug": "paris-roubaix",
        "stage_url": "https://www.cyclingstage.com/paris-roubaix-2026/route-pr-2026/",
    })
    assert url == index and html
    assert opgevraagd == [index]


# ── startlijst ──────────────────────────────────────────────────────
#
# Twee verzoeken: eerst de koerspagina om het adres te vínden, dan de
# startlijst zelf. Het adres is niet af te leiden — `spain-riders-2026` bij
# de Vuelta tegenover `riders-gb-2026` bij de Tour of Britain.

RIDERS = Path(__file__).parent / "fixtures" / "cyclingstage_vuelta_2026_riders.html"

# Zoals cyclingstage een uitslag zet: een kop met een alinea eronder, regels
# gescheiden door <br>. Een kop zónder die regels is géén uitslag — dat is
# precies het geval waarin het afgeleide adres niet mag winnen.
UITSLAG = ("<h2>Stage 1 Results</h2><p>1. Jasper Philipsen (bel) 4:12:03<br>"
           "2. Tim Merlier (bel) s.t.<br>3. Olav Kooij (ned) s.t.</p>")

VUELTA = "https://www.cyclingstage.com/vuelta-2026-route/spain-route-2026/"
VUELTA_RIDERS = "https://www.cyclingstage.com/vuelta-2026/spain-riders-2026/"


@pytest.fixture
def vuelta():
    return {"url": VUELTA, "name": "Vuelta a España",
            "start": date(2026, 8, 22), "end": date(2026, 9, 13),
            "women": False, "level": "m"}


def test_startlijst_via_de_link_op_de_koerspagina(wt, monkeypatch, vuelta):
    opgevraagd = _pagina(wt, monkeypatch, {
        VUELTA: ROUTE.read_text(),
        VUELTA_RIDERS: RIDERS.read_text(),
    })
    rijen = wt._cs_fetch_startlijst(vuelta)
    assert len(rijen) == 184
    assert len({r["team"] for r in rijen}) == 23
    # eerst de koerspagina, dan de startlijst die daarop stond
    assert opgevraagd == [VUELTA, VUELTA_RIDERS]


def test_startlijst_zonder_bruikbare_pagina_geeft_leeg(wt, monkeypatch, vuelta):
    """Een koers waarvan de startlijst nog niet gepubliceerd is."""
    _pagina(wt, monkeypatch, {VUELTA: ROUTE.read_text()})   # riders-pagina leeg
    assert wt._cs_fetch_startlijst(vuelta) == []
    _pagina(wt, monkeypatch, {})
    assert wt._cs_fetch_startlijst(vuelta) == []
    assert wt._cs_fetch_startlijst({"url": ""}) == []


def test_startlijstblok_telt_alles_maar_toont_per_ploeg(wt, monkeypatch, vuelta):
    co = wt.CyclingCoordinator(hass=None)

    async def _job(fn, *a):
        return fn(*a)

    co._job = _job
    _pagina(wt, monkeypatch, {VUELTA: ROUTE.read_text(),
                              VUELTA_RIDERS: RIDERS.read_text()})
    blok = asyncio.run(co._startlijst_blok(vuelta))
    # de tellingen slaan op de hele lijst, niet op wat er getoond wordt
    assert blok["startlist_riders"] == 184
    assert blok["startlist_teams"] == 23
    assert blok["startlist_out"] == 34
    # standaard één renner per ploeg
    assert len(blok["startlist_top"]) == 23
    assert blok["startlist_top"][0]["bib"] == 1
    # geen `rank`: dit is geen rangorde
    assert all("rank" not in r for r in blok["startlist_top"])


def test_startlijst_wordt_maar_een_keer_per_koers_opgehaald(wt, monkeypatch, vuelta):
    """Twee verzoeken per koers is genoeg; ook een lege uitkomst blijft staan."""
    co = wt.CyclingCoordinator(hass=None)

    async def _job(fn, *a):
        return fn(*a)

    co._job = _job
    opgevraagd = _pagina(wt, monkeypatch, {VUELTA: ROUTE.read_text(),
                                           VUELTA_RIDERS: RIDERS.read_text()})
    for _ in range(3):
        asyncio.run(co._startlijst_blok(vuelta))
    assert opgevraagd == [VUELTA, VUELTA_RIDERS]

    # een koers zonder startlijst wordt evenmin elke ronde opnieuw geprobeerd
    leeg = dict(vuelta, url="https://www.cyclingstage.com/nog-niets-2026/")
    opgevraagd2 = _pagina(wt, monkeypatch, {})
    for _ in range(3):
        blok = asyncio.run(co._startlijst_blok(leeg))
    assert blok["startlist_riders"] == 0 and blok["startlist_top"] == []
    assert len(opgevraagd2) == 1


def test_startlijstblok_slikt_zijn_eigen_fouten(wt, monkeypatch, vuelta):
    """Een koers in de pop-up mag niet omvallen op een stukke startlijst."""
    co = wt.CyclingCoordinator(hass=None)

    async def _job(fn, *a):
        raise RuntimeError("bron ligt eruit")

    co._job = _job
    blok = asyncio.run(co._startlijst_blok(vuelta))
    assert blok == {"startlist_top": [], "startlist_riders": 0,
                    "startlist_teams": 0, "startlist_out": 0}


def test_een_pagina_die_laadt_maar_leeg_is_wint_niet(wt, monkeypatch):
    """Toetsen op "staat er een uitslag in", niet op "kwam er iets binnen".

    Het afgeleide adres is een aanname. Antwoordt cyclingstage daarop met
    een pagina die wél laadt maar geen uitslag bevat, dan zou die gok
    permanent winnen en werd het overzicht nooit geraadpleegd — precies de
    stille "geen uitslag" waar deze terugval voor gemaakt is.
    """
    afgeleid = ("https://www.cyclingstage.com/tour-of-britain-2026-results/"
                "stage-1-gb-results-2026/")
    index = "https://www.cyclingstage.com/tour-of-britain-2026-results/"
    echt = index + "stage-1-britain-results-2026/"
    opgevraagd = _pagina(wt, monkeypatch, {
        # laadt prima, maar er staat geen uitslag op
        afgeleid: "<html><body><h2>Stage 1</h2><p>Nog geen uitslag.</p></body></html>",
        index: '<a href="/tour-of-britain-2026-results/stage-1-britain-results-2026/">Stage 1</a>',
        echt: UITSLAG,
    })
    wt._UITSLAGINDEX.clear()
    url, html = wt._uitslagpagina(_etappe())
    assert url == echt
    assert index in opgevraagd


def test_het_overzicht_dat_hetzelfde_adres_geeft_kost_geen_tweede_verzoek(wt, monkeypatch):
    """Wijst het overzicht naar het adres dat we al geprobeerd hebben, dan
    houdt het op — anders wordt dezelfde lege pagina twee keer gehaald."""
    afgeleid = ("https://www.cyclingstage.com/tour-of-britain-2026-results/"
                "stage-1-gb-results-2026/")
    index = "https://www.cyclingstage.com/tour-of-britain-2026-results/"
    opgevraagd = _pagina(wt, monkeypatch, {
        afgeleid: "<h2>Stage 1</h2><p>Nog geen uitslag.</p>",
        index: '<a href="/tour-of-britain-2026-results/stage-1-gb-results-2026/">Stage 1</a>',
    })
    wt._UITSLAGINDEX.clear()
    assert wt._uitslagpagina(_etappe()) == ("", "")
    assert opgevraagd.count(afgeleid) == 1


def test_de_koerspagina_blijft_bewaard_als_een_latere_kandidaat_faalt(wt, monkeypatch, koers):
    """De routelink staat op de koerspagina; die mag niet weggegooid worden.

    `_etappelijst_urls` probeert meerdere adressen. Werd alleen de HTML van
    de láátste bewaard, dan kreeg de link-terugval een lege string zodra die
    laatste niet binnenkwam — en werd de routepagina nooit gevonden.
    """
    diep = "https://www.cyclingstage.com/tour-of-britain-2026/route-gb-2026/"
    # de koerspagina komt binnen (met de link erop), een volgende kandidaat niet
    opgevraagd = _pagina(wt, monkeypatch, {
        KOERS: KOERSPAGINA_HTML,
        diep: ROUTE.read_text(),
    })
    etappes = wt._cs_event_stages(koers)
    assert len(etappes) == 21
    assert diep in opgevraagd


def test_de_pagina_die_we_al_hebben_kost_geen_kandidaatplek(cs):
    """`route_kandidaten` mag het adres dat hij meekreeg niet teruggeven.

    Die pagina heeft geen etappetabel opgeleverd, anders was de terugval niet
    nodig geweest. Hem opnieuw ophalen kost een van de drie plekken.
    """
    html = ('<a href="/tour-of-britain-2026/route-gb-2026/">Route</a>'
            '<a href="/tour-of-britain-2026/riders-gb-2026/">Riders</a>')
    kandidaten = cs.route_kandidaten(
        html, "https://www.cyclingstage.com/tour-of-britain-2026/route-gb-2026/")
    assert "https://www.cyclingstage.com/tour-of-britain-2026/route-gb-2026/" \
        not in kandidaten
    assert kandidaten == [
        "https://www.cyclingstage.com/tour-of-britain-2026/riders-gb-2026/"]


def test_tour_of_britain_krijgt_zijn_vijf_etappes(wt, monkeypatch):
    """De klacht waarmee dit begon: één etappe waar er vijf horen te zijn.

    De kalender geeft voor deze koers geen routeadres, dus de koerspagina
    komt binnen. Die linkt naar `route-gb-2026`, en dáár staan de etappes —
    niet in een tabel maar als lopende tekst.
    """
    route = (Path(__file__).parent / "fixtures"
             / "cyclingstage_tour_of_britain_2026_route.html").read_text()
    # de koerspagina linkt naar de routepagina; die staat in de fixture zelf
    opgevraagd = _pagina(wt, monkeypatch, {KOERS: route})
    etappes = wt._cs_event_stages(
        {"url": KOERS, "name": "Tour of Britain", "start": date(2026, 9, 2),
         "end": date(2026, 9, 6), "women": False, "level": "m"})
    assert [e["idx"] for e in etappes] == [1, 2, 3, 4, 5]
    assert [e["date"] for e in etappes] == [
        date(2026, 9, d) for d in (2, 3, 4, 5, 6)]
    assert etappes[0]["distance_km"] == 182.5
    assert etappes[3]["vertical_m"] == 2699


def test_datums_alleen_als_ze_sluitend_zijn(wt):
    """Minder etappes dan dagen betekent rustdagen, en dan is het raden.

    Een etappe op de verkeerde dag zetten is erger dan de koers laten
    wegvallen: de hele tegelkeuze rekent op die datum.
    """
    rijen = [{"idx": i, "date": None} for i in range(1, 6)]
    goed = wt._datums_verdelen([dict(r) for r in rijen],
                               date(2026, 9, 2), date(2026, 9, 6))
    assert [r["date"] for r in goed] == [date(2026, 9, d) for d in (2, 3, 4, 5, 6)]
    # 5 etappes over 7 dagen: er zitten rustdagen tussen, maar welke?
    assert wt._datums_verdelen([dict(r) for r in rijen],
                               date(2026, 9, 2), date(2026, 9, 8)) == []
    assert wt._datums_verdelen([], date(2026, 9, 2), date(2026, 9, 6)) == []
    assert wt._datums_verdelen([dict(r) for r in rijen], None, None) == []
