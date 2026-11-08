"""Na het seizoen: de kalender van volgend jaar, als aankondiging (0.32).

Op 8 november 2026 stond er "Seizoen afgelopen" en verborg de kaart zich,
terwijl cyclingstage de kalender van 2027 al had: 44 koersen, met naam en
datum maar nog zonder routes. Tot 0.32 werd een koers zonder adres
weggegooid, en bovendien werd alleen de kalender van dit jaar opgehaald.

De fixture is de echte pagina van die dag
(`cyclingstage_kalender_2027_2026-11-08.html`).
"""
import asyncio
from datetime import date, datetime
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
K2026 = (FIXTURES / "cyclingstage_kalender_2026.html").read_text(encoding="utf-8")
K2027 = (FIXTURES / "cyclingstage_kalender_2027_2026-11-08.html").read_text(
    encoding="utf-8")


def _pagina_s(wt, monkeypatch):
    """`_haal_html` op de twee kalenderpagina's; al het andere is een 404."""
    gevraagd = []

    def haal(url, wat="pagina"):
        gevraagd.append(url)
        if url.endswith("cycling-calendar-2026/"):
            return K2026
        if url.endswith("cycling-calendar-2027/"):
            return K2027
        return ""

    monkeypatch.setattr(wt, "_haal_html", haal)
    return gevraagd


def _co(wt, monkeypatch, nu):
    monkeypatch.setattr(wt.dt_util, "now", lambda: nu)
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        return fn(*args)

    c._job = job
    return c


def test_koersen_zonder_route_blijven_in_de_kalender(wt, monkeypatch):
    _pagina_s(wt, monkeypatch)
    koersen, telling, fouten = wt._fetch_calendar(2027, ["m", "v"])
    assert not fouten
    assert len(koersen) == 44
    eerste = koersen[0]
    assert eerste["name"] == "Tour Down Under"
    assert eerste["start"] == date(2027, 1, 19)
    # nog geen route: een leeg adres, geen geraden adres. Alleen de drie
    # grote rondes hebben in november 2026 al een routepagina.
    met_adres = [k["name"] for k in koersen if k["url"]]
    assert met_adres == ["Giro d'Italia", "Tour de France", "Vuelta a España"]
    assert eerste["url"] == ""


def test_in_november_staat_de_eerste_koers_van_volgend_jaar_op_de_tegel(
        wt, monkeypatch):
    gevraagd = _pagina_s(wt, monkeypatch)
    c = _co(wt, monkeypatch, datetime(2026, 11, 8, 12, 0))
    uit = asyncio.run(c._async_update_data())

    assert uit["state"] == "Tour Down Under"
    a = uit["attributes"]
    assert a["stages_known"] is False
    assert a["show_state"] != "Klaar"
    assert a["countdown"] == "Over 72 dagen"
    assert a["days_until"] == 72
    assert a["date"] == "19 jan – 24 jan"
    assert a["type"] == "Etappekoers"
    assert a["races"][0]["primary"] is True
    # alleen de twee kalenderpagina's: een koers zonder adres kost niets, en
    # de routepagina's van de Giro en de Tour van 2027 (die er al zijn)
    # worden niet afgezocht zolang de Tour Down Under eerder is
    assert len(gevraagd) == 2, gevraagd


def test_tijdens_het_seizoen_geen_kalender_van_volgend_jaar(wt, monkeypatch):
    gevraagd = _pagina_s(wt, monkeypatch)
    c = _co(wt, monkeypatch, datetime(2026, 10, 1, 12, 0))
    asyncio.run(c._async_update_data())
    assert not any("2027" in u for u in gevraagd)


def test_zonder_kalender_van_volgend_jaar_blijft_het_seizoen_afgelopen(
        wt, monkeypatch):
    gevraagd = _pagina_s(wt, monkeypatch)

    def haal(url, wat="pagina"):
        gevraagd.append(url)
        return K2026 if url.endswith("cycling-calendar-2026/") else ""

    monkeypatch.setattr(wt, "_haal_html", haal)
    c = _co(wt, monkeypatch, datetime(2026, 11, 8, 12, 0))
    uit = asyncio.run(c._async_update_data())
    assert uit["state"] == "Seizoen afgelopen"
    # de kalender van dit jaar blijft staan; morgen weer een poging
    assert c._calendar and c._calendar_fetched == date(2026, 11, 8)


def test_aftel_tekst(wt):
    k = {"start": date(2027, 1, 19), "end": date(2027, 1, 24)}
    assert wt._aftel_tekst(k, date(2027, 1, 18)) == "Start morgen"
    assert wt._aftel_tekst(k, date(2027, 1, 20)) == "🟢 Bezig — dag 2/6"
    e = {"start": date(2027, 2, 27), "end": date(2027, 2, 27)}
    assert wt._aftel_tekst(e, date(2027, 2, 27)) == "🟢 Vandaag"
