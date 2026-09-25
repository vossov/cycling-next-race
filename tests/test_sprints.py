"""Het tijdschema wordt ook echt opgevraagd.

`_sprints_voor` gaf tot 0.31.4 `(race_url, idx, one_day)` door aan
`_fetch_times`, dat sinds 0.19 één etappe verwacht. De TypeError werd stil
afgevangen, dus het tijdschema — en daarmee de tussensprint — is in al die
versies geen enkele keer opgevraagd. `times_diag` liet intussen de adressen
zien alsof ze geprobeerd waren. De proeftests stubden `_sprints_voor` weg, dus
ook daar viel het niet op.

Of `stage-{n}-times.htm` bij cyclingstage bestaat is een aparte vraag (voor
de Vuelta: nee, zie CLAUDE.md). Hier gaat het erom dat de code doet wat hij
zegt: de adressen proberen, en een lege uitkomst per dag onthouden.
"""
import asyncio
import io
import urllib.error
import urllib.request
from datetime import date

ETAPPE = {"date": date(2026, 9, 5), "idx": 14, "one_day": False,
          "stage_url": "https://www.cyclingstage.com/vuelta-2026-route/"
                       "stage-14-spain-2026/",
          "race_url": "https://www.cyclingstage.com/vuelta-2026-route/",
          "race_name": "La Vuelta", "race_slug": "vuelta", "women": False}


def _coordinator(wt):
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        return fn(*args)

    c._job = job
    return c


def test_het_tijdschema_wordt_opgevraagd(wt, monkeypatch):
    """Alle adressen uit `_times_urls`, in die volgorde, en geen TypeError."""
    monkeypatch.setattr(wt, "_IMG_MAP", {"vuelta/2026": "vuelta-spain"})
    gevraagd = []

    def urlopen(req, timeout=None):
        gevraagd.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    c = _coordinator(wt)
    assert asyncio.run(c._sprints_voor(ETAPPE)) == []
    assert gevraagd == wt._times_urls(ETAPPE)
    assert gevraagd[0].endswith("/images/vuelta-spain/2026/stage-14-times.htm")


def test_een_leeg_tijdschema_wordt_per_dag_onthouden(wt, monkeypatch):
    """Anders kost een etappe zonder tijdschema elke ronde vier verzoeken."""
    monkeypatch.setattr(wt, "_IMG_MAP", {})
    gevraagd = []

    def urlopen(req, timeout=None):
        gevraagd.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    c = _coordinator(wt)
    asyncio.run(c._sprints_voor(ETAPPE))
    eerste = len(gevraagd)
    asyncio.run(c._sprints_voor(ETAPPE))
    assert eerste > 0
    assert len(gevraagd) == eerste


def test_een_gevonden_tussensprint_komt_door(wt, monkeypatch):
    """Het pad van verzoek tot lijst, met de tabelvorm die `_parse_times` leest.

    Dit is geen parsertest — er bestaat geen echte `times.htm` om op te
    testen, en dat staat ook zo in CLAUDE.md. Het is alleen de keten: komt er
    iets binnen, dan staat het in de uitkomst.
    """
    monkeypatch.setattr(wt, "_IMG_MAP", {})
    tabel = (b"<table><tr><td>Sprint Chantada</td><td>96.4</td>"
             b"<td>88.0</td><td>15:24</td></tr></table>")

    class Antwoord(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=None: Antwoord(tabel))
    assert asyncio.run(_coordinator(wt)._sprints_voor(ETAPPE)) == [88.0]
