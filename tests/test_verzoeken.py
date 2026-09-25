"""Niet vaker ophalen dan nodig — nagemeten, niet aangenomen.

Draait `tools/meet_verzoeken.py`: de échte coordinator tegen de opgeslagen
pagina's, op de dag van Vuelta-etappe 14 (5 september 2026). Tot 0.31.4 kostte
een ronde tijdens de etappe acht verzoeken, waarvan er vijf niets konden
opleveren: de uitslag van gisteren (die verandert niet meer) en de GPX- en
etappepagina's van GP Québec, zes dagen later, die al een 404 hadden gegeven.
Om de vijf minuten, want tijdens een live etappe ververst de sensor vaker.

De Tour of Britain-koerspagina ligt niet in de fixtures en geeft hier dus
elke ronde een 404; in het echt bestaat hij en komt zijn etappelijst in de
cache. Die telt daarom niet mee in wat hieronder wordt nagekeken.
"""
import importlib.util
import pathlib
from datetime import datetime

import pytest

WORTEL = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def meet(wt):
    spec = importlib.util.spec_from_file_location(
        "meet_verzoeken", WORTEL / "tools" / "meet_verzoeken.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.meet


def _ronde(log, nu):
    return [url for tijd, _, url, _ in log if tijd == nu]


START = datetime(2026, 9, 5, 16, 0)
LIVE = datetime(2026, 9, 5, 16, 5)
NA_DE_FINISH = datetime(2026, 9, 5, 18, 30)
AVOND = datetime(2026, 9, 5, 19, 0)


def test_een_live_ronde_haalt_alleen_de_uitslag_van_vandaag(meet, monkeypatch):
    log = meet([START, LIVE], zet=monkeypatch.setattr, stil=True)
    live = [u for u in _ronde(log, LIVE) if "tour-of-britain" not in u]
    # daar hangt het doorrollen aan, dus die blijft elke ronde
    assert live == ["https://www.cyclingstage.com/vuelta-2026-results/"
                    "stage-14-spain-results-2026/"]


def test_de_uitslag_van_gisteren_komt_uit_de_cache(meet, monkeypatch):
    log = meet([START, LIVE], zet=monkeypatch.setattr, stil=True)
    gisteren = "stage-13-spain-results-2026"
    assert any(gisteren in u for u in _ronde(log, START))
    assert not any(gisteren in u for u in _ronde(log, LIVE))


def test_een_latere_etappe_zonder_profiel_kost_vandaag_niets_meer(meet, monkeypatch):
    """GP Québec, zes dagen later: één keer geprobeerd, daarna tot morgen niet."""
    log = meet([START, LIVE], zet=monkeypatch.setattr, stil=True)
    assert any("gp-quebec" in u for u in _ronde(log, START))
    assert not any("gp-quebec" in u for u in _ronde(log, LIVE))


def test_na_de_finish_geen_uitslag_van_morgen_en_geen_herhaling(meet, monkeypatch):
    """Na de finish rolt de tegel door naar morgen.

    Van morgen bestaat nog geen uitslag, dus daar gaat geen verzoek heen; en
    de uitslag van vandaag staat na één keer compleet in de cache.
    """
    log = meet([START, NA_DE_FINISH, AVOND], zet=monkeypatch.setattr, stil=True)
    avond = [u for u in _ronde(log, AVOND) if "tour-of-britain" not in u]
    assert not any("stage-15-spain-results" in u for u in avond)
    assert not any("stage-14-spain-results" in u for u in avond)
    assert avond == []


def test_een_lege_uitkomst_van_gisteren_geldt_niet_voor_vandaag(wt):
    """Mislukt de kalender om middernacht, dan worden de dagcaches niet
    geleegd. Een etappe die gisteren "morgen, geen GPX" was, is vandaag de
    etappe op de tegel — en die hoort gewoon opnieuw geprobeerd te worden."""
    import asyncio
    from datetime import date

    c = wt.CyclingCoordinator(None)
    etappe = {"stage_url": "https://www.cyclingstage.com/x-2026/stage-5-x-2026/",
              "date": date(2026, 9, 6)}
    gezocht = []

    async def zoek(s, n):
        gezocht.append(s["stage_url"])
        return [], []

    c._gpx_zoek = zoek
    c._vandaag = date(2026, 9, 5)          # gisteren: de etappe is morgen
    asyncio.run(c._gpx_van(etappe, 45))
    asyncio.run(c._gpx_van(etappe, 45))
    assert len(gezocht) == 1               # de tweede keer uit de cache
    c._vandaag = date(2026, 9, 6)          # vandaag, en de cache staat er nog
    asyncio.run(c._gpx_van(etappe, 45))
    assert len(gezocht) == 2

    # hetzelfde voor de etappepagina
    gelezen = []

    async def job(fn, *args):
        gelezen.append(fn)
        return {"ok": False}

    c._job = job
    c._vandaag = date(2026, 9, 5)
    asyncio.run(c._meta_voor(etappe))
    asyncio.run(c._meta_voor(etappe))
    assert len(gelezen) == 1
    c._vandaag = date(2026, 9, 6)
    asyncio.run(c._meta_voor(etappe))
    assert len(gelezen) == 2
