"""Tel hoeveel verzoeken een ophaalronde bij de bronnen kost.

    python3 tools/meet_verzoeken.py          # samenvatting per ronde
    python3 tools/meet_verzoeken.py -v       # plus elk adres

**Waarom dit script bestaat.** De robots.txt-afweging in CLAUDE.md leunt op
"niet vaker ophalen dan nodig", maar hoeveel dat in de praktijk is stond
nergens. Een schatting die niemand narekent gaat schuiven — dezelfde les als
bij `meet_attributen.py`.

**Wat het doet.** Het draait de échte coordinator (`_async_update_data`) met
Home Assistant gestubd, en vervangt alleen het netwerk: `urlopen` levert de
opgeslagen pagina's uit `tests/fixtures/` en een 404 voor al het andere. Het
scenario is zaterdag 5 september 2026, de dag van Vuelta-etappe 14: vier
rondes met het echte ritme — twee tijdens de etappe (om de vijf minuten
zou het LIVE-ritme zijn), één na de finish en één de volgende ochtend.

**Wat het níét is.** Geen parsertest: elke etappepagina krijgt de pagina van
etappe 4, elke gereden uitslag die van etappe 2, en de GPX is een
nagemaakt spoor — er ligt geen echt GPX-bestand in de fixtures, en voor het
tellen van verzoeken maakt de vorm van het profiel niets uit. Wat níét als
fixture bestaat (de Tour of Britain-koerspagina, GP Québec, het
tijdschema) geeft een 404; dat is voor sommige adressen de werkelijkheid en
voor andere niet, en dat staat er per soort bij.
"""
import asyncio
import io
import pathlib
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime

WORTEL = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = WORTEL / "tests" / "fixtures"
sys.path.insert(0, str(WORTEL / "tests"))
sys.path.insert(0, str(WORTEL / "custom_components"))

import importlib  # noqa: E402

if "homeassistant" not in sys.modules:
    import conftest  # noqa: E402  (de stubs voor Home Assistant)

    conftest._installeer_stubs()

wt = importlib.import_module("cycling_next_race.sensor")

CS = "https://www.cyclingstage.com"


def _fx(naam):
    return (FIXTURES / naam).read_bytes()


def _gpx():
    """Een nagemaakt spoor van 104 km met één klim; alleen om te tellen."""
    punten = []
    for i in range(400):
        lat = 42.5 + i * 0.0023
        hoogte = 1000 + (1400 * (i - 150) / 100 if 150 <= i < 250 else
                         (1400 if i >= 250 else 0))
        punten.append(f'<trkpt lat="{lat:.5f}" lon="1.52000"><ele>{hoogte:.0f}</ele></trkpt>')
    return ("<gpx><trk><trkseg>" + "".join(punten) + "</trkseg></trk></gpx>").encode()


# Welke etappe-uitslag er al staat. Etappe 14 finisht rond 17:30; om 18:30
# staat hij er.
def _gereden_tot(nu):
    return 14 if nu.hour >= 18 or nu.date().day > 5 else 13


def bron(url, nu):
    """(soort, inhoud) voor een adres; inhoud None betekent een 404."""
    u = url.split("#", 1)[0]
    if u == f"{CS}/uci/cycling-calendar-2026/":
        return "kalender", _fx("cyclingstage_kalender_2026.html")
    if u in (f"{CS}/vuelta-2026-route/", f"{CS}/vuelta-2026-route/spain-route-2026/"):
        return "routepagina", _fx("cyclingstage_vuelta_2026_route.html")
    m = re.match(rf"{CS}/vuelta-2026-route/stage-(\d+)-spain-2026/$", u)
    if m:
        return "etappepagina", _fx("cyclingstage_vuelta_2026_stage4.html")
    m = re.match(rf"{CS}/vuelta-2026-results/stage-(\d+)-spain-results-2026/$", u)
    if m:
        klaar = int(m.group(1)) <= _gereden_tot(nu)
        return "uitslag", _fx("cyclingstage_vuelta_2026_stage2_results.html") if klaar else None
    if u == f"{CS}/vuelta-2026-results/":
        return "uitslagoverzicht", _fx("cyclingstage_vuelta_2026_results_index_2026-09-12.html")
    if u == f"{CS}/vuelta-2026/spain-riders-2026/":
        return "startlijst", _fx("cyclingstage_vuelta_2026_riders.html")
    if u == f"{CS}/vuelta-2026-gpx/":
        return "gpx-overzicht", _fx("cyclingstage_vuelta_2026_gpx_index.html")
    if u.endswith(".gpx"):
        ok = u.endswith("/images/vuelta-spain/2026/stage-4-route.gpx")
        return "gpx", _gpx() if ok else None
    if u.endswith("-times.htm"):
        return "tijdschema", None
    if "wielerflits.nl" in u:
        return "tv-gids", _fx("wielerflits_tv_2026-09-07.html")
    if "-results" in u or "/results-" in u:
        return "uitslag", None
    return "overig", None


class _Antwoord(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def meet(rondes, uitgebreid=False, zet=setattr, stil=False):
    """Draai de rondes en geef `[(tijdstip, soort, adres, gelukt), ...]`.

    `zet` doet het vervangen van het netwerk en de klok; een test geeft hier
    `monkeypatch.setattr` mee, zodat alles na afloop weer terugstaat.
    """
    log = []
    klok = {"nu": rondes[0]}

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        soort, inhoud = bron(url, klok["nu"])
        log.append((klok["nu"], soort, url.split("#", 1)[0], inhoud is not None))
        if inhoud is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return _Antwoord(inhoud)

    async def geen_pauze(*a, **kw):
        return None

    zet(urllib.request, "urlopen", urlopen)
    zet(wt.dt_util, "now", lambda: klok["nu"])
    zet(wt.asyncio, "sleep", geen_pauze)
    # de caches op moduleniveau leeg beginnen; in een testrun kan een eerdere
    # test ze gevuld hebben, en dan telt dit script verzoeken die niet gaan
    for naam in ("_ETAPPE_HTML", "_UITSLAGINDEX", "_EENDAAGS_KANDIDATEN",
                 "_EENDAAGS_GOED", "_IMG_MAP"):
        zet(wt, naam, {})
    c = wt.CyclingCoordinator(None)

    async def job(fn, *args):
        return fn(*args)

    c._job = job

    vorige = set()
    for nu in rondes:
        klok["nu"] = nu
        begin = len(log)
        data = asyncio.run(c._async_update_data())
        ronde = log[begin:]
        a = data.get("attributes", {})
        per_soort = Counter(s for _, s, _, _ in ronde)
        mis = sum(1 for *_, ok in ronde if not ok)
        herhaald = [u for _, _, u, _ in ronde if u in vorige]
        vorige = {u for _, _, u, _ in ronde}
        if stil:
            continue
        print(f"\n── {nu:%a %d %b %H:%M} · tegel: {a.get('eyebrow', '')} "
              f"· {a.get('show_state', '')}")
        print(f"   {len(ronde)} verzoeken, waarvan {mis} een 404; "
              f"{len(herhaald)} ook al in de vorige ronde")
        for soort, n in per_soort.most_common():
            print(f"   {soort:<18}{n:>4}")
        if uitgebreid:
            for _, soort, url, ok in ronde:
                print(f"      {'   ' if ok else '404'} {soort:<16} {url}")
    return log


if __name__ == "__main__":
    meet([datetime(2026, 9, 5, 16, 0), datetime(2026, 9, 5, 16, 5),
          datetime(2026, 9, 5, 18, 30), datetime(2026, 9, 6, 9, 0)],
         uitgebreid="-v" in sys.argv)
