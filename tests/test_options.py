"""De coordinator leest zijn instellingen uit de config entry.

Wat hier getest wordt is de vertaling van opties naar gedrag; of het
optiescherm zelf verschijnt is alleen in een draaiende Home Assistant te
zien.
"""
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

    klein = asyncio.run(c._gpx_for("race/x/2026/stage-3", "https://x.gpx", 60))
    groot = asyncio.run(c._gpx_for("race/x/2026/stage-3", "https://x.gpx", 200))
    nogmaals = asyncio.run(c._gpx_for("race/x/2026/stage-3", "https://x.gpx", 60))

    assert len(klein[0]) == 60
    assert len(groot[0]) == 200, "het grote profiel kreeg de kleine versie uit de cache"
    assert len(nogmaals[0]) == 60
    assert gevraagd == [60, 200], f"er is onnodig opnieuw opgehaald: {gevraagd}"


def test_beschikbaarheid_blijft_bekend_voor_de_koerskeuze(wt):
    """_gpx_rang leunt op wat er over een etappe bekend is."""
    import asyncio

    c = wt.CyclingCoordinator(None)

    async def zonder_profiel(fn, *args):
        return [], []

    c._job = zonder_profiel
    asyncio.run(c._gpx_for("race/geen/2026/stage-1", "https://x.gpx", 60))
    assert c._gpx_rang({"stage_url": "race/geen/2026/stage-1",
                        "race_url": "race/geen/2026"}) == 1

    async def met_profiel(fn, *args):
        return [[0.0, 10], [1.0, 20]], []

    c._job = met_profiel
    asyncio.run(c._gpx_for("race/wel/2026/stage-1", "https://x.gpx", 60))
    assert c._gpx_rang({"stage_url": "race/wel/2026/stage-1",
                        "race_url": "race/wel/2026"}) == 0
