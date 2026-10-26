"""Een kalenderpagina die één keer niet binnenkomt, legt de dag niet stil.

Op 26 oktober 2026 om 00:23: "Kalender ophalen mislukt: kalenderpagina ...
kwam niet binnen". `_fetch_calendar` geeft dan een lege lijst terug (geen
uitzondering), en die werd opgeslagen mét de datum van vandaag. Gevolg: de
kalender van gisteren weg, en tot de volgende dag geen nieuwe poging.
"""
import asyncio
from datetime import date, datetime

import pytest

VANDAAG = date(2026, 10, 26)
KOERS = {"name": "Paris-Tours", "start": date(2026, 10, 11),
         "end": date(2026, 10, 11), "women": False, "level": "m",
         "url": "https://www.cyclingstage.com/paris-tours-2026/"}
FOUT = "kalenderpagina https://www.cyclingstage.com/uci/cycling-calendar-2026/ kwam niet binnen"


def _co(wt, monkeypatch, antwoorden):
    monkeypatch.setattr(wt.dt_util, "now",
                        lambda: datetime(2026, 10, 26, 0, 23))
    c = wt.CyclingCoordinator(None)
    c.verzoeken = 0

    async def job(fn, *args):
        assert fn is wt._fetch_calendar
        c.verzoeken += 1
        a = antwoorden.pop(0)
        if isinstance(a, Exception):
            raise a
        return a

    c._job = job
    return c


def _draai(c):
    return asyncio.run(c._async_update_data())


def test_mislukte_verversing_houdt_de_oude_kalender(wt, monkeypatch):
    c = _co(wt, monkeypatch, [([], {}, [FOUT])])
    c._calendar, c._calendar_fetched = [KOERS], date(2026, 10, 25)
    uit = _draai(c)
    assert uit["state"] == "Seizoen afgelopen"
    assert c._calendar == [KOERS]
    # de datum schuift niet op: volgende ronde opnieuw proberen
    assert c._calendar_fetched == date(2026, 10, 25)


@pytest.mark.parametrize("fout", [([], {}, [FOUT]), RuntimeError("time-out")])
def test_eerste_ronde_mislukt_en_de_volgende_probeert_opnieuw(wt, monkeypatch, fout):
    c = _co(wt, monkeypatch, [fout, ([KOERS], {}, [])])
    with pytest.raises(wt.UpdateFailed):
        _draai(c)
    assert c._calendar_fetched is None
    assert _draai(c)["state"] == "Seizoen afgelopen"
    assert c.verzoeken == 2
    assert c._calendar_fetched == VANDAAG
