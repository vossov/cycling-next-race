"""Welke niveaus er te zien zijn, en in welke kleur de knoppen staan.

De integratie haalt de kalender per niveau op (bij procyclingstats het
`circuit=`-nummer). `levels` mag op de tegel én in de pop-up, `levels_popup`
alleen in de pop-up. Alles hier draait zonder netwerk.
"""
import asyncio
from datetime import date

import pytest

VANDAAG = date(2026, 8, 5)

WT_M, WT_V, PRO_M = "1", "24", "26"


def _ev(slug, naam, start, eind=None, niveau=WT_M, vrouwen=False):
    """Een kalenderregel zoals `_fetch_calendar` hem oplevert."""
    return {"name": naam, "url": f"race/{slug}/2026", "start": start,
            "end": eind or start, "women": vrouwen, "level": niveau}


POLEN = _ev("tour-de-pologne", "Tour de Pologne", date(2026, 8, 4),
            date(2026, 8, 10))
DENEMARKEN = _ev("danmark-rundt", "Danmark Rundt", date(2026, 8, 4),
                 date(2026, 8, 8), niveau=PRO_M)


@pytest.fixture
def coordinator(wt, monkeypatch):
    """Een coordinator die niets ophaalt: `_job` roept de functie direct aan."""
    monkeypatch.setattr(wt, "_fetch_tv_html", lambda *a: "")
    monkeypatch.setattr(wt, "_fetch_rank_maps", lambda *a: {})

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
    co = coordinator({const.CONF_LEVELS_POPUP: [PRO_M]})

    assert co._niveaus_tegel == [WT_M, WT_V]
    assert co._niveaus_alles == [WT_M, WT_V, PRO_M]


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
    co = coordinator({const.CONF_LEVELS_POPUP: [PRO_M]})

    assert co._mag_op_tegel(POLEN) is True
    assert co._mag_op_tegel(DENEMARKEN) is False


def test_niveau_op_het_dashboard_mag_de_tegel_pakken(wt, const, coordinator):
    co = coordinator({const.CONF_LEVELS: [WT_M, WT_V, PRO_M]})
    assert co._mag_op_tegel(DENEMARKEN) is True


def test_koers_zonder_niveau_wordt_niet_uitgesloten(wt, coordinator):
    """Een kalender uit een oudere versie kent het veld nog niet."""
    co = coordinator()
    assert co._mag_op_tegel({"url": "race/x/2026"}) is True


# ── de kalender per niveau ──────────────────────────────────────────

# Deze neppagina bootst de boomstructuur na die selectolax teruggeeft, niet
# de HTML zelf. Wat hier getest wordt is dus wat er per niveau gebeurt —
# welke circuits worden opgehaald, welk niveau en geslacht op elke koers
# komt te staan en wat er gebeurt als een niveau niets oplevert. Of de
# selectors (`table.basic`, `tbody tr`) op de echte pagina kloppen zegt dit
# niet; die code is ongewijzigd en alleen tegen de echte site te toetsen.

class _NepLink:
    def __init__(self, href, tekst):
        self.attributes = {"href": href}
        self._tekst = tekst

    def text(self):
        return self._tekst


class _NepCel:
    def __init__(self, tekst):
        self._tekst = tekst

    def text(self):
        return self._tekst


class _NepRij:
    def __init__(self, rij):
        # de parser wil minstens drie cellen en leest alleen de eerste
        self._cellen = [_NepCel(rij["date"]), _NepCel(""), _NepCel("")]
        self._link = _NepLink(rij["url"], rij["name"])

    def css(self, selector):
        return self._cellen if selector == "td" else []

    def css_first(self, selector):
        return self._link if selector == "a" else None


class _NepTabel:
    def __init__(self, rijen):
        self._rijen = [_NepRij(r) for r in rijen]

    def css(self, selector):
        return self._rijen if selector == "tbody tr" else []


class _NepHtml:
    def __init__(self, rijen):
        self._tabel = _NepTabel(rijen)

    def css_first(self, selector):
        return self._tabel if selector == "table.basic" else None


class _NepPagina:
    """Vervangt `Scraper`; `RacesCalendar` leest hier zijn tabel uit."""

    #  circuitnummer -> de rijen die op die kalenderpagina staan
    PAGINAS = {
        "1": [{"date": "04.08 - 10.08", "url": "race/tour-de-pologne/2026/gc",
               "name": "Tour de Pologne"}],
        "24": [{"date": "05.08", "url": "race/rvv-vrouwen/2026/result",
                "name": "Ronde van Vlaanderen"}],
        "26": [{"date": "04.08 - 08.08", "url": "race/danmark-rundt/2026",
                "name": "Danmark Rundt"}],
        "27": [],           # bootst een circuitnummer na dat niets oplevert
    }

    def __init__(self, url):
        import re
        m = re.search(r"circuit=(\d+)", url)
        self.html = _NepHtml(self.PAGINAS.get(m.group(1) if m else "", []))


@pytest.fixture
def nep_kalender(wt, monkeypatch):
    """`_fetch_calendar` laten praten met de neppagina in plaats van PCS."""
    import sys
    import types

    scraper = types.ModuleType("procyclingstats.scraper")
    scraper.Scraper = _NepPagina
    pakket = types.ModuleType("procyclingstats")
    pakket.scraper = scraper
    monkeypatch.setitem(sys.modules, "procyclingstats", pakket)
    monkeypatch.setitem(sys.modules, "procyclingstats.scraper", scraper)


def test_kalender_haalt_alleen_de_gekozen_niveaus(wt, nep_kalender):
    koersen, telling, _ = wt._fetch_calendar(2026, ["1", "24"])

    assert {k["name"] for k in koersen} == {"Tour de Pologne",
                                            "Ronde van Vlaanderen"}
    assert telling == {"WorldTour mannen": 1, "WorldTour vrouwen": 1}


def test_elke_koers_draagt_zijn_niveau_en_geslacht(wt, nep_kalender):
    koersen, _, _ = wt._fetch_calendar(2026, ["24", "26"])
    per_naam = {k["name"]: k for k in koersen}

    assert per_naam["Ronde van Vlaanderen"]["level"] == "24"
    assert per_naam["Ronde van Vlaanderen"]["women"] is True
    assert per_naam["Danmark Rundt"]["level"] == "26"
    assert per_naam["Danmark Rundt"]["women"] is False


def test_kalenderlink_wordt_teruggebracht_tot_de_koers(wt, nep_kalender):
    """De link eindigt vaak op /gc of /result; dat breekt de etappelijst."""
    koersen, _, _ = wt._fetch_calendar(2026, ["1"])
    assert koersen[0]["url"] == "race/tour-de-pologne/2026"


def test_niveau_zonder_koersen_staat_in_de_telling(wt, nep_kalender, caplog):
    """Een verkeerd circuitnummer moet zichtbaar zijn, niet stil blijven."""
    koersen, telling, _ = wt._fetch_calendar(2026, ["1", "27"])

    assert telling["ProSeries vrouwen"] == 0
    assert len(koersen) == 1
    assert "levert geen koersen op" in caplog.text
    assert "niet geverifieerd" in caplog.text, (
        "bij een niet-geverifieerd nummer hoort dat er expliciet bij te staan")


def test_onbekend_niveau_wordt_overgeslagen(wt, nep_kalender):
    koersen, telling, _ = wt._fetch_calendar(2026, ["1", "999"])

    assert len(koersen) == 1
    assert "999" not in telling


def test_datums_komen_uit_de_kalenderregel(wt, nep_kalender):
    koersen, _, _ = wt._fetch_calendar(2026, ["1", "24"])
    per_naam = {k["name"]: k for k in koersen}

    assert per_naam["Tour de Pologne"]["start"] == date(2026, 8, 4)
    assert per_naam["Tour de Pologne"]["end"] == date(2026, 8, 10)
    # eendaagse koers: begin en eind vallen samen
    assert (per_naam["Ronde van Vlaanderen"]["start"]
            == per_naam["Ronde van Vlaanderen"]["end"] == date(2026, 8, 5))


# ── hoeveel koersen er naast de getoonde passen ─────────────────────

def test_aantal_koersen_in_de_popup_is_instelbaar(wt, const, coordinator,
                                                  monkeypatch):
    monkeypatch.setattr(wt, "_fetch_stage", lambda *a: {
        "ok": True, "finished": False, "results": [], "gc": [],
        "points_top": [], "kom_top": [], "youth_top": []})
    monkeypatch.setattr(wt, "_fetch_startlist", lambda *a: [])

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
    monkeypatch.setattr(wt, "_fetch_startlist", lambda *a: [])
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
    vuelta = _ev("vuelta-a-espana", "La Vuelta ciclista a España", VANDAAG)
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
    ronde = _ev("vuelta-a-espana", "Vuelta", VANDAAG)
    morgen = dict(_nxt(ronde), date=date(2026, 8, 6))
    ander = _ev("renewi-tour", "Renewi Tour", VANDAAG)
    assert co._keuzesleutel(ander, _nxt(ander), 9) < co._keuzesleutel(ronde, morgen, 0)


def test_grote_rondes_zijn_er_drie(wt):
    assert wt._is_grote_ronde("race/vuelta-a-espana/2026")
    assert wt._is_grote_ronde("race/giro-d-italia/2026")
    assert wt._is_grote_ronde("race/tour-de-france/2026")
    # de rondes van een week bij de vrouwen horen er bewust niet bij
    assert not wt._is_grote_ronde("race/vuelta-espana-femenina/2026")
    assert not wt._is_grote_ronde("race/renewi-tour/2026")
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
        {"key": "vuelta-a-espana", "label": "Vuelta", "race_name": "Vuelta",
         "women": False}, [kandidaat], VANDAAG))
    assert [r.get("label") for r in uit["races"]] == ["Vuelta", "Renewi Tour"]
    assert gezien and gezien[0][0] is ev and gezien[0][1][0]["idx"] == 3


# ── de bron ligt eruit ──────────────────────────────────────────────

def test_fout_van_de_bron_reist_mee(wt, monkeypatch):
    """Een onbereikbare bron is iets anders dan een leeg circuitnummer.

    Op 23 augustus 2026 zette procyclingstats Cloudflare-bescherming aan.
    De kalender bleef leeg en de sensor meldde "PCS-structuur gewijzigd?" —
    dat wees de verkeerde kant op, terwijl de echte reden ("Cloudflare
    protection detected") wel in het log stond.
    """
    import sys
    import types

    class _Weigert:
        def __init__(self, url):
            raise ConnectionError(
                "Cloudflare protection detected. Install 'cloudscraper'")

    scraper = types.ModuleType("procyclingstats.scraper")
    scraper.Scraper = _Weigert
    pakket = types.ModuleType("procyclingstats")
    pakket.scraper = scraper
    monkeypatch.setitem(sys.modules, "procyclingstats", pakket)
    monkeypatch.setitem(sys.modules, "procyclingstats.scraper", scraper)

    koersen, telling, fouten = wt._fetch_calendar(2026, ["1", "24"])
    assert koersen == []
    assert telling == {"WorldTour mannen": 0, "WorldTour vrouwen": 0}
    assert any("Cloudflare" in f for f in fouten)
    # en erachteraan of de bypass er wel of niet is; de melding van
    # procyclingstats zegt daar niets over
    assert any("cloudscraper" in f for f in fouten)


def test_bypass_diag_zegt_of_het_pakket_er_is(wt, monkeypatch):
    """Twee heel verschillende situaties, één melding van procyclingstats."""
    import builtins

    echt = builtins.__import__

    def _zonder(naam, *a, **kw):
        if naam == "cloudscraper":
            raise ImportError("No module named 'cloudscraper'")
        return echt(naam, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _zonder)
    uit = wt._bypass_diag()
    assert "NIET geladen" in uit and "herstart" in uit.lower()

    import sys
    import types
    monkeypatch.setattr(builtins, "__import__", echt)
    nep = types.ModuleType("cloudscraper")
    nep.__version__ = "1.2.71"
    monkeypatch.setitem(sys.modules, "cloudscraper", nep)
    uit = wt._bypass_diag()
    assert "1.2.71" in uit and "wél geladen" in uit


def _zet_vandaag(wt, monkeypatch):
    """`dt_util.now()` is in de stubs None; hier een echte klok."""
    from datetime import datetime
    monkeypatch.setattr(wt.dt_util, "now",
                        lambda: datetime(VANDAAG.year, VANDAAG.month,
                                         VANDAAG.day, 12, 0))


def test_lege_kalender_noemt_de_reden(wt, coordinator, monkeypatch):
    """`UpdateFailed` krijgt de melding van de bron, niet de gok."""
    import asyncio

    _zet_vandaag(wt, monkeypatch)
    co = coordinator()

    async def _job(fn, *args):
        if fn is wt._fetch_calendar:
            return [], {}, ["Cloudflare protection detected"]
        return fn(*args)

    co._job = _job
    with pytest.raises(wt.UpdateFailed) as fout:
        asyncio.run(co._async_update_data())
    assert "Cloudflare" in str(fout.value)
    assert "structuur gewijzigd" not in str(fout.value)


def test_lege_kalender_zonder_fout_blijft_de_oude_melding(wt, coordinator,
                                                         monkeypatch):
    """Kwam alles binnen maar stond er niets in, dan is de opmaak verdacht."""
    import asyncio

    _zet_vandaag(wt, monkeypatch)
    co = coordinator()

    async def _job(fn, *args):
        if fn is wt._fetch_calendar:
            return [], {}, []
        return fn(*args)

    co._job = _job
    with pytest.raises(wt.UpdateFailed) as fout:
        asyncio.run(co._async_update_data())
    assert "structuur gewijzigd" in str(fout.value)


# ── curl_cffi aansluiten op procyclingstats ─────────────────────────

def _nep_pcs(monkeypatch):
    """Een `procyclingstats.scraper.Scraper` zoals het pakket hem heeft."""
    import sys
    import types

    class Scraper:
        _session = "de eigen sessie"

        @classmethod
        def _get_session(cls):
            return cls._session

    scraper = types.ModuleType("procyclingstats.scraper")
    scraper.Scraper = Scraper
    pakket = types.ModuleType("procyclingstats")
    pakket.scraper = scraper
    monkeypatch.setitem(sys.modules, "procyclingstats", pakket)
    monkeypatch.setitem(sys.modules, "procyclingstats.scraper", scraper)
    return Scraper


def _nep_curl(monkeypatch, sessie="curl-sessie"):
    import sys
    import types

    gemaakt = {}

    class Session:
        def __init__(self, impersonate=None):
            gemaakt["impersonate"] = impersonate

        def __repr__(self):
            return sessie

    requests_mod = types.ModuleType("curl_cffi.requests")
    requests_mod.Session = Session
    pakket = types.ModuleType("curl_cffi")
    pakket.requests = requests_mod
    monkeypatch.setitem(sys.modules, "curl_cffi", pakket)
    monkeypatch.setitem(sys.modules, "curl_cffi.requests", requests_mod)
    return gemaakt


@pytest.fixture(autouse=True)
def _sessie_vergeten(wt):
    """De patch staat modulewijd; elke test begint schoon."""
    wt._PCS_SESSIE = ""
    yield
    wt._PCS_SESSIE = ""


def test_curl_cffi_wordt_de_sessie_van_procyclingstats(wt, monkeypatch):
    Scraper = _nep_pcs(monkeypatch)
    gemaakt = _nep_curl(monkeypatch)

    uit = wt._zet_pcs_sessie()

    assert "curl_cffi actief" in uit
    assert gemaakt["impersonate"] == wt.PCS_IMPERSONATE
    # en het pakket praat er nu echt doorheen
    assert repr(Scraper._get_session()) == "curl-sessie"


def test_tweede_aanroep_patcht_niet_opnieuw(wt, monkeypatch):
    _nep_pcs(monkeypatch)
    gemaakt = _nep_curl(monkeypatch)

    eerst = wt._zet_pcs_sessie()
    gemaakt.clear()
    daarna = wt._zet_pcs_sessie()

    assert eerst == daarna
    assert gemaakt == {}, "er is een tweede sessie gemaakt"


def test_zonder_curl_cffi_blijft_de_eigen_sessie_staan(wt, monkeypatch):
    """Ontbreekt het pakket, dan mag er niets kapotgaan."""
    import builtins

    Scraper = _nep_pcs(monkeypatch)
    echt = builtins.__import__

    def _zonder(naam, *a, **kw):
        if naam.startswith("curl_cffi"):
            raise ImportError("No module named 'curl_cffi'")
        return echt(naam, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _zonder)
    uit = wt._zet_pcs_sessie()

    assert "niet beschikbaar" in uit
    assert Scraper._get_session() == "de eigen sessie"


def test_pakket_zonder_get_session_wordt_met_rust_gelaten(wt, monkeypatch):
    """procyclingstats mag zijn interne opzet wijzigen zonder ons te breken."""
    import sys
    import types

    class Scraper:
        pass

    scraper = types.ModuleType("procyclingstats.scraper")
    scraper.Scraper = Scraper
    pakket = types.ModuleType("procyclingstats")
    pakket.scraper = scraper
    monkeypatch.setitem(sys.modules, "procyclingstats", pakket)
    monkeypatch.setitem(sys.modules, "procyclingstats.scraper", scraper)
    _nep_curl(monkeypatch)

    uit = wt._zet_pcs_sessie()

    assert "geen _get_session meer" in uit
    assert not hasattr(Scraper, "_get_session")


def test_diagnose_noemt_beide_bypasses(wt, monkeypatch):
    import sys
    import types

    nep = types.ModuleType("cloudscraper")
    nep.__version__ = "1.2.71"
    monkeypatch.setitem(sys.modules, "cloudscraper", nep)
    wt._PCS_SESSIE = "curl_cffi actief (impersonate=chrome)"

    uit = wt._bypass_diag()
    assert "1.2.71" in uit and "curl_cffi actief" in uit
