"""De coordinator leest zijn instellingen uit de config entry.

Wat hier getest wordt is de vertaling van opties naar gedrag; of het
optiescherm zelf verschijnt is alleen in een draaiende Home Assistant te
zien.
"""
from datetime import date
from datetime import timedelta


def _coordinator(wt, opties=None):
    return wt.CyclingCoordinator(None, opties)


def test_zonder_opties_gelden_de_standaarden(wt, const):
    c = _coordinator(wt)
    assert c._opt(const.CONF_RESULT_N) == const.DEFAULT_RESULT_N
    assert c._scan_interval == timedelta(minutes=const.DEFAULT_SCAN_MINUTES)
    assert c._live_scan_interval == timedelta(minutes=const.DEFAULT_LIVE_SCAN_MINUTES)


def test_opties_overschrijven_de_standaarden(wt, const):
    c = _coordinator(wt, {const.CONF_RESULT_N: 25, const.CONF_SCAN_MINUTES: 90})
    assert c._opt(const.CONF_RESULT_N) == 25
    assert c._scan_interval == timedelta(minutes=90)
    # niet ingestelde opties blijven op hun standaard
    assert c._opt(const.CONF_GC_N) == const.DEFAULT_GC_N


def test_gedeeltelijke_opties_vullen_zichzelf_aan(wt, const):
    c = _coordinator(wt, {const.CONF_GC_N: 5})
    assert set(c._options) == set(const.OPTION_DEFAULTS)


def test_onbruikbare_waarde_valt_terug(wt, const):
    """Liever de standaard dan een crash in de update-lus."""
    for rommel in ("", None, "twintig", []):
        c = _coordinator(wt, {const.CONF_RESULT_N: rommel})
        assert c._opt(const.CONF_RESULT_N) == const.DEFAULT_RESULT_N


def test_tekstgetal_wordt_geaccepteerd(wt, const):
    """HA slaat opties soms als tekst op."""
    c = _coordinator(wt, {const.CONF_UPCOMING_DAYS: "14"})
    assert c._opt(const.CONF_UPCOMING_DAYS) == 14


# ── hoogteprofielen uit de cache ────────────────────────────────────

def test_cache_verwart_grote_en_kleine_profielen_niet(wt):
    """Dezelfde etappe wordt met 60 en met 200 punten opgevraagd.

    De komende dagen krijgen kleine profieltjes, de getoonde etappe een
    groot. Staat de cache alleen op de etappe-URL, dan krijgt het grote
    profiel de kleine versie terug zodra die er eerder was.
    """
    import asyncio

    c = wt.CyclingCoordinator(None)
    gevraagd = []

    async def nep_job(fn, *args):
        # args van _fetch_gpx: (gpx_url, n_out)
        gevraagd.append(args[1])
        return [[i * 1.0, 100 + i] for i in range(args[1])], []

    c._job = nep_job
    etappe = {"stage_url": "https://www.cyclingstage.com/tour-de-france-2026-route/"
                           "stage-3-tdf-2026/",
              "race_url": "https://www.cyclingstage.com/tour-de-france-2026-route/",
              "race_slug": "tour-de-france", "idx": 3, "date": date(2026, 7, 3)}

    klein = asyncio.run(c._gpx_for(etappe, 60))
    groot = asyncio.run(c._gpx_for(etappe, 200))
    nogmaals = asyncio.run(c._gpx_for(etappe, 60))

    assert len(klein[0]) == 60
    assert len(groot[0]) == 200, "het grote profiel kreeg de kleine versie uit de cache"
    assert len(nogmaals[0]) == 60
    assert gevraagd == [60, 200], f"er is onnodig opnieuw opgehaald: {gevraagd}"


def test_beschikbaarheid_blijft_bekend_voor_de_koerskeuze(wt):
    """_gpx_rang leunt op wat er over een etappe bekend is."""
    import asyncio

    c = wt.CyclingCoordinator(None)

    async def zonder_profiel(fn, *args):
        # de terugval vraagt ook de overzichtspagina op; die geeft een dict
        return {} if fn is wt._fetch_gpx_index else ([], [])

    c._job = zonder_profiel
    geen = {"stage_url": "https://www.cyclingstage.com/tour-de-france-2026-route/stage-1-x-2026/",
           "race_url": "https://www.cyclingstage.com/tour-de-france-2026-route/",
           "race_slug": "tour-de-france", "idx": 1, "date": date(2026, 7, 1)}
    asyncio.run(c._gpx_for(geen, 60))
    assert c._gpx_rang(geen) == 1

    async def met_profiel(fn, *args):
        return [[0.0, 10], [1.0, 20]], []

    c._job = met_profiel
    wel = {"stage_url": "https://www.cyclingstage.com/giro-d-italia-2026-route/stage-1-x-2026/",
           "race_url": "https://www.cyclingstage.com/giro-d-italia-2026-route/",
           "race_slug": "giro-d-italia", "idx": 1, "date": date(2026, 7, 1)}
    asyncio.run(c._gpx_for(wel, 60))
    assert c._gpx_rang(wel) == 0


def test_gpx_valt_terug_op_de_overzichtspagina(wt):
    """Geven de vaste adressen niets, dan telt wat cyclingstage zelf noemt.

    De vaste adressen zijn een aanname over de bestandsnaam; wijkt een koers
    daarvan af, dan bleef het profiel leeg zonder dat iets kapotging.
    """
    import asyncio

    c = wt.CyclingCoordinator(None)
    echt = "https://cdn.cyclingstage.com/images/vuelta/2026/etappe-3-parcours.gpx"
    opgehaald = []

    async def nep_job(fn, *args):
        if fn is wt._fetch_gpx_index:
            return {3: echt}
        opgehaald.append(args[0])
        # alleen het adres van de overzichtspagina levert iets op
        return ([[0.0, 10], [1.0, 20]], []) if args[0] == echt else ([], [])

    c._job = nep_job
    etappe = {"stage_url": "https://www.cyclingstage.com/vuelta-2026-route/stage-3-x-2026/",
           "race_url": "https://www.cyclingstage.com/vuelta-2026-route/",
           "race_slug": "vuelta", "idx": 3, "date": date(2026, 7, 3)}
    elev, _ = asyncio.run(c._gpx_for(etappe, 60))

    assert elev, "de terugval leverde geen profiel op"
    assert opgehaald[-1] == echt
    # en de diagnose laat zien wélk adres het werd
    assert c._gpx_gebruikt[etappe["stage_url"]] == echt


def test_gpx_overzichtspagina_hoogstens_een_keer_per_koers(wt):
    """De terugval kost een verzoek; niet per etappe opnieuw."""
    import asyncio

    c = wt.CyclingCoordinator(None)
    index_verzoeken = []

    async def nep_job(fn, *args):
        if fn is wt._fetch_gpx_index:
            index_verzoeken.append(args[0].get("race_slug"))
            return {}
        return [], []

    c._job = nep_job
    for n in (3, 4):
        asyncio.run(c._gpx_for(
                {"stage_url": f"https://www.cyclingstage.com/vuelta-2026-route/"
                              f"stage-{n}-spain-2026/",
                 "race_url": "https://www.cyclingstage.com/vuelta-2026-route/",
                 "race_slug": "vuelta", "idx": n,
                 "date": date(2026, 8, 20 + n)}, 60))
    assert index_verzoeken == ["vuelta"], index_verzoeken



# ── opzetten ────────────────────────────────────────────────────────

def test_entiteit_komt_er_ook_als_de_eerste_ronde_faalt(wt, monkeypatch):
    """Anders staat er een herstelde entiteit zonder attributen.

    Met `async_config_entry_first_refresh()` wordt de entiteit bij een
    mislukte eerste ophaalronde helemaal niet toegevoegd. Home Assistant zet
    er dan zelf een neer met status `unavailable` en `restored: true`, en
    daar is niet aan te zien dát het opzetten mislukte, laat staan waarom.
    """
    import asyncio
    import types

    class NepCoordinator:
        def __init__(self, hass, opties=None):
            self.data = None
            self.last_update_success = False
            self.last_exception = RuntimeError("procyclingstats onbereikbaar")
            self.geprobeerd = False

        async def async_refresh(self):
            self.geprobeerd = True

    monkeypatch.setattr(wt, "CyclingCoordinator", NepCoordinator)
    toegevoegd = []
    entry = types.SimpleNamespace(options={})
    asyncio.run(wt.async_setup_entry(None, entry, toegevoegd.extend))

    assert len(toegevoegd) == 1, "de sensor werd niet toegevoegd"
    assert toegevoegd[0].coordinator.geprobeerd
    # en de entiteit valt niet over data die er nog niet is
    assert toegevoegd[0].native_value is None
    assert toegevoegd[0].extra_state_attributes == {}
