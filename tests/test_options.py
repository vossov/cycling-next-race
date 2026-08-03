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
