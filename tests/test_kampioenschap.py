"""Een kampioenschap heeft onderdelen, geen genummerde etappes.

Het WK stond wél in de kalender van cyclingstage maar verdween stil: zijn
programmatabel heeft een dátum in de eerste kolom waar een rittenkoers een
etappenummer heeft, dus `parse_etappes` gaf nul rijen en een koers zonder
etappes valt weg. Alles hieronder draait op de échte pagina.
"""
import asyncio
import pathlib
from datetime import date

import pytest

VANDAAG = date(2026, 9, 20)      # de dag van beide tijdritten


def _fixture(naam):
    return (pathlib.Path(__file__).parent / "fixtures" / naam).read_text(
        errors="replace")


@pytest.fixture
def wk():
    return _fixture("cyclingstage_wk_2026_canada.html")


@pytest.fixture
def wk_live():
    """De pagina zoals hij op 20 september 2026 was, op een nieuw adres.

    `/world-championships-2026-canada/` geeft inmiddels een 404; de koers
    staat nu op `/world-championships-2026-montreal/`. De kalender wijst er
    zelf naar, dus daar hoeft niets voor geraden te worden.
    """
    return _fixture("cyclingstage_wk_2026_montreal.html")


# ── de programmatabel ───────────────────────────────────────────────

def test_programma_van_het_echte_wk(cs, wk):
    """Datum, route, onderdeel, afstand en hoogtemeters, per onderdeel."""
    rijen = cs.parse_programma(wk, 2026)
    assert len(rijen) == 5
    namen = [r["onderdeel"] for r in rijen]
    assert namen == ["Tijdrit vrouwen", "Tijdrit mannen",
                     "Gemengde estafette", "Wegrit vrouwen", "Wegrit mannen"]
    eerste = rijen[0]
    assert eerste["date"] == VANDAAG
    assert eerste["name"] == "Montreal"
    assert eerste["distance_km"] == 39.9
    assert eerste["stage_type"] == "itt"
    assert eerste["women"] is True


def test_het_geslacht_staat_er_letterlijk(cs, wk):
    """`ITT (v)` en `ITT (m)` — aflezen, niet raden.

    De gemengde estafette draagt geen aanduiding en krijgt daarom None: dan
    houdt het onderdeel het geslacht van de koers zelf.
    """
    per_naam = {r["onderdeel"]: r for r in cs.parse_programma(wk, 2026)}
    assert per_naam["Tijdrit vrouwen"]["women"] is True
    assert per_naam["Tijdrit mannen"]["women"] is False
    assert per_naam["Gemengde estafette"]["women"] is None


def test_de_komma_in_de_hoogtemeters_is_een_duizendtalscheiding(cs, wk):
    """`2,502` is 2502 meter en niet 2,502 meter."""
    per_naam = {r["onderdeel"]: r for r in cs.parse_programma(wk, 2026)}
    assert per_naam["Wegrit vrouwen"]["vertical_m"] == 2502
    assert per_naam["Wegrit mannen"]["vertical_m"] == 3720
    assert per_naam["Tijdrit mannen"]["vertical_m"] == 195


def test_een_gewone_routepagina_is_geen_programma(cs):
    """Anders zou een etappetabel er ook doorheen glippen.

    Het onderscheid zit in de eerste kolom: een datum bij een kampioenschap,
    een etappenummer bij een rittenkoers.
    """
    assert cs.parse_programma(
        _fixture("cyclingstage_vuelta_2026_route.html"), 2026) == []
    assert cs.parse_programma(
        _fixture("cyclingstage_tour_of_britain_2026_route.html"), 2026) == []
    assert cs.parse_programma("", 2026) == []


# ── de keten: kalender -> onderdelen ────────────────────────────────

def _wk_etappes(wt, monkeypatch, wk):
    monkeypatch.setattr(wt, "_haal_html",
                        lambda url, wat="": wk if "world-championships" in url else "")
    from cycling_next_race import cyclingstage as cs_mod
    koers = next(k for k in cs_mod.parse_kalender(
        _fixture("cyclingstage_kalender_2026.html"), 2026)
        if "World Champ" in k["name"])
    koers["level"] = "m"
    return wt._event_stages(koers)


def test_het_wk_levert_zijn_vijf_onderdelen(wt, monkeypatch, wk):
    """Van de echte kalenderregel tot de vijf onderdelen, in één verzoek."""
    st = _wk_etappes(wt, monkeypatch, wk)
    assert len(st) == 5
    assert [s["date"] for s in st] == [
        VANDAAG, VANDAAG, date(2026, 9, 23), date(2026, 9, 26), date(2026, 9, 27)]
    assert st[4]["distance_km"] == 273.2
    assert st[4]["vertical_m"] == 3720


def test_elk_onderdeel_heeft_een_eigen_sleutel(wt, monkeypatch, wk):
    """Anders vallen vijf onderdelen samen tot één.

    `stage_url` is de sleutel van de ontdubbeling in `_build_upcoming` en van
    vier caches. De onderdelen hebben geen eigen pagina, dus het onderdeel
    komt als fragment achter het koersadres — dat knipt `urllib` er vóór het
    verzoek weer af.
    """
    st = _wk_etappes(wt, monkeypatch, wk)
    adressen = [s["stage_url"] for s in st]
    assert len(set(adressen)) == 5
    assert adressen[0].endswith("#tijdrit-vrouwen")
    # en het blijft dezelfde pagina
    import urllib.request
    assert urllib.request.Request(adressen[0]).selector == \
        "/world-championships-2026-canada/"


def test_het_niveau_volgt_het_onderdeel(wt, monkeypatch, wk):
    """De kalender kent het WK één geslacht toe; de tabel weet beter."""
    st = {s["onderdeel"]: s for s in _wk_etappes(wt, monkeypatch, wk)}
    assert st["Tijdrit vrouwen"]["level"] == "v"
    assert st["Tijdrit vrouwen"]["women"] is True
    assert st["Wegrit mannen"]["level"] == "m"
    # zonder aanduiding houdt het onderdeel het niveau van de koers
    assert st["Gemengde estafette"]["level"] == "m"


def test_het_label_zegt_het_onderdeel_en_niet_etappe_none(wt, monkeypatch, wk):
    """`idx` is leeg bij een onderdeel; zonder dit las de tegel "Etappe None"."""
    st = _wk_etappes(wt, monkeypatch, wk)
    assert wt._etappe_label(st[0]) == "Tijdrit vrouwen"
    assert all("None" not in wt._etappe_label(s) for s in st)
    # een gewone etappe blijft gewoon genummerd
    assert wt._etappe_label({"idx": 7, "race_name": "La Vuelta"}) == "Etappe 7"


# ── twee onderdelen op één dag ──────────────────────────────────────

def test_het_tweede_onderdeel_van_de_dag_raakt_niet_zoek(wt, monkeypatch, wk):
    """Beide tijdritten zijn op 20 september.

    Is die van de vrouwen gereden, dan hoort die van de mannen op de tegel —
    niet de wegrit van zes dagen later. "Wat er nog komt" was alleen een
    látere dag, dus het tweede onderdeel was nergens te zien.
    """
    st = _wk_etappes(wt, monkeypatch, wk)
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        # de tijdrit van de vrouwen is gereden, de rest nog niet
        klaar = args[0]["onderdeel"] == "Tijdrit vrouwen"
        return {"ok": True, "finished": klaar, "results": [], "gc": [],
                "points_top": [], "kom_top": [], "youth_top": [],
                "points_leader": "", "kom_leader": "", "youth_leader": "",
                "distance": None, "vertical": None, "profile_score": None,
                "stage_type": "", "start_time": "", "climbs_raw": [],
                "departure": "", "arrival": "", "result_url": "",
                "startlist_quality": None}

    c._job = job
    keuze = asyncio.run(c._kies_etappe(st, VANDAAG))
    assert keuze["shown"]["onderdeel"] == "Tijdrit mannen"
    assert keuze["today_finished"] is True
    # en de latere onderdelen staan er nog achter
    assert [s["onderdeel"] for s in keuze["future"]][:2] == [
        "Tijdrit mannen", "Gemengde estafette"]


def test_een_rittenkoers_merkt_er_niets_van(wt):
    """Eén etappe per dag: "wat er nog komt" blijft precies zoals het was."""
    stages = [{"date": date(2026, 9, 19), "idx": 1, "onderdeel": None},
              {"date": VANDAAG, "idx": 2, "onderdeel": None},
              {"date": date(2026, 9, 21), "idx": 3, "onderdeel": None}]
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        return {"finished": False, "results": [], "gc": []}

    c._job = job
    keuze = asyncio.run(c._kies_etappe(stages, VANDAAG))
    assert keuze["shown"]["idx"] == 2
    assert [s["idx"] for s in keuze["future"]] == [3]
    assert [s["idx"] for s in keuze["finished"]] == [1]


# ── de koerspagina gaat over een ánder onderdeel (0.31.1) ───────────

def test_de_kolommen_worden_op_inhoud_gelezen(cs, wk, wk_live):
    """Twee échte pagina's, twee kolomvolgordes.

    Op de tegel van 20 september stond "Montreal · World Championships" waar
    "Tijdrit mannen" hoorde te staan. De eigenaar leverde diezelfde ochtend
    de live pagina, en daar staat het:

        7 september:  datum | route | type  | km | el.gain
        20 september: datum | type  | route | km | el.gain | riders

    Kolom 2 en 3 zijn omgedraaid en er is een kolom bij gekomen. Vandaar dat
    er op geen enkele volgorde meer wordt gerekend: het onderdeel is de cel
    die een onderdeel nóemt, de getalcellen zijn de afstand en de
    hoogtemeters, en de route is wat er aan tekst overblijft.
    """
    for html in (wk, wk_live):
        rijen = cs.parse_programma(html, 2026)
        assert [r["onderdeel"] for r in rijen] == [
            "Tijdrit vrouwen", "Tijdrit mannen", "Gemengde estafette",
            "Wegrit vrouwen", "Wegrit mannen"]
        assert [r["name"] for r in rijen[:2]] == ["Montreal", "Montreal"]
        assert rijen[4]["name"] == "Brossard - Montreal"
        assert [r["women"] for r in rijen] == [True, False, None, True, False]


def test_de_live_pagina_schrijft_road_race_en_w(cs, wk_live):
    """`road race (w)` in plaats van `wegrace (v)` — allebei herkend."""
    rijen = cs.parse_programma(wk_live, 2026)
    assert rijen[0]["stage_type"] == "itt"
    assert rijen[3]["onderdeel"] == "Wegrit vrouwen"
    # en de getallen van die dag, met de duizendtalscheiding
    assert rijen[4]["distance_km"] == 273.4
    assert rijen[4]["vertical_m"] == 3808


def test_de_live_pagina_geeft_een_adres_per_onderdeel(cs, wk_live):
    """Nieuw op 20 september: de routekolom linkt per onderdeel.

    De gemengde estafette heeft er nog geen ("to follow"), en de twee
    tijdritten delen er één — ze rijden dezelfde route.
    """
    per_naam = {r["onderdeel"]: r["url"] for r in cs.parse_programma(wk_live, 2026)}
    assert per_naam["Tijdrit vrouwen"].endswith("/route-itt-wc-2026/")
    assert per_naam["Tijdrit mannen"] == per_naam["Tijdrit vrouwen"]
    assert per_naam["Wegrit vrouwen"].endswith("/route-road-race-wc-2026-women/")
    assert per_naam["Gemengde estafette"] == ""


def test_de_tijdritten_delen_een_pagina_maar_geen_sleutel(wt, monkeypatch, wk_live):
    """Eén routepagina voor twee onderdelen; het fragment houdt ze uit elkaar."""
    st = _wk_etappes(wt, monkeypatch, wk_live)
    assert len({s["stage_url"] for s in st}) == 5
    assert st[0]["stage_url"].endswith("/route-itt-wc-2026/#tijdrit-vrouwen")
    assert st[1]["stage_url"].endswith("/route-itt-wc-2026/#tijdrit-mannen")
    import urllib.request
    assert urllib.request.Request(st[0]["stage_url"]).selector == \
        "/world-championships-2026-montreal/route-itt-wc-2026/"


def test_de_tabel_wint_van_de_lopende_tekst(wt, monkeypatch, wk_live):
    """Op de koerspagina staat "3,800 metres of elevation gain".

    Die zin gaat over de wegrit van de mannen en stond op 20 september bij
    álle vijf de onderdelen — ook bij de tijdrit van 39 km, die daarmee
    "Bergrit" heette. De tabel zegt 220.
    """
    st = _wk_etappes(wt, monkeypatch, wk_live)
    monkeypatch.setattr(wt, "_etappe_html",
                        lambda url: "<p>3,800 metres of elevation gain</p>")
    assert wt._fetch_stage_meta(st[1])["vertical"] == 220
    assert wt._fetch_stage_meta(st[4])["vertical"] == 3808


def test_een_onderdeel_weet_dat_het_geen_eigen_pagina_heeft(wt, monkeypatch, wk):
    st = _wk_etappes(wt, monkeypatch, wk)
    assert all(s["eigen_pagina"] is False for s in st)


def test_de_hoogtemeters_komen_van_de_programmatabel(wt, monkeypatch, wk):
    """Niet van de koerspagina: die gaat over een ánder onderdeel.

    Op 20 september 2026 las de tegel bij de tijdrit van 39 km "3800 hm" en
    daarmee "Bergrit" — de hoogtemeters van de wegrit, want alle vijf
    onderdelen delen één pagina. De tabel zegt 195.
    """
    st = _wk_etappes(wt, monkeypatch, wk)

    def nooit(*a, **kw):                       # er hoort niets opgehaald te worden
        raise AssertionError("de koerspagina hoort hier niet gelezen te worden")

    monkeypatch.setattr(wt, "_etappe_html", nooit)
    meta = wt._fetch_stage_meta(st[1])         # Tijdrit mannen
    assert meta["vertical"] == 195
    assert meta["distance"] == 39.9
    assert meta["start_time"] == ""            # de tabel noemt er geen
    assert meta["ok"] is True                  # compleet, niets bij te leren
    assert wt._fetch_stage_meta(st[4])["vertical"] == 3720


def test_zonder_eigen_pagina_geen_profiel(wt, monkeypatch, wk):
    """Het GPX-adres op de koerspagina hoort bij een ander onderdeel."""
    st = _wk_etappes(wt, monkeypatch, wk)
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        raise AssertionError("er hoort geen GPX opgehaald te worden")

    c._job = job
    assert asyncio.run(c._gpx_van(st[0], 45)) == ([], [])


def test_de_eyebrow_herhaalt_de_tijdrit_niet(wt, monkeypatch, wk):
    """"Tijdrit mannen" zegt het al; daar hoeft geen "· TT" meer achter."""
    st = _wk_etappes(wt, monkeypatch, wk)
    assert wt._eyebrow_tag(st[1], "itt") == ""
    # een gewone etappe houdt zijn tag
    assert wt._eyebrow_tag({"idx": 18}, "itt") == "TT"
