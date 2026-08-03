"""Het optieschema van de config flow.

Home Assistant is hier gestubd, dus dit zegt niets over de vraag of het
scherm in de interface verschijnt — alleen dat het schema klopt en de
ingevoerde waarden doen wat ze moeten doen.
"""
import asyncio
import types

import pytest


def _optieschema(flow_mod, opties=None):
    flow = flow_mod.CyclingNextRaceOptionsFlow()
    flow.config_entry = types.SimpleNamespace(options=opties or {})
    gezien = {}
    flow.async_show_form = lambda **kw: gezien.update(kw) or kw
    asyncio.run(flow.async_step_init())
    return gezien["data_schema"]


def test_schema_bevat_elke_optie(flow_mod, const):
    schema = _optieschema(flow_mod)
    sleutels = {str(m) for m in schema.schema}
    assert sleutels == set(const.OPTION_DEFAULTS)


def test_ingevulde_waarden_komen_er_geheel_uit(flow_mod, const):
    schema = _optieschema(flow_mod)
    uit = schema({const.CONF_RESULT_N: "15", const.CONF_SCAN_MINUTES: 45})
    assert uit[const.CONF_RESULT_N] == 15      # tekst wordt een getal
    assert uit[const.CONF_SCAN_MINUTES] == 45
    # niet ingevulde velden krijgen hun huidige waarde als standaard
    assert uit[const.CONF_GC_N] == const.DEFAULT_GC_N


def test_waarden_buiten_de_grenzen_worden_geweigerd(flow_mod, const):
    import voluptuous as vol

    schema = _optieschema(flow_mod)
    for sleutel, waarde in [
        (const.CONF_SCAN_MINUTES, const.MAX_SCAN_MINUTES + 1),
        (const.CONF_SCAN_MINUTES, 0),
        (const.CONF_RESULT_N, const.MAX_RIDERS + 5),
        (const.CONF_UPCOMING_DAYS, 0),
    ]:
        with pytest.raises(vol.Invalid):
            schema({sleutel: waarde})


def test_opgeslagen_opties_zijn_de_voorinvulling(flow_mod, const):
    schema = _optieschema(flow_mod, {const.CONF_RESULT_N: 20})
    assert schema({})[const.CONF_RESULT_N] == 20


def test_flow_is_single_instance(flow_mod, const):
    """Twee keer toevoegen moet afketsen op dezelfde unieke id."""
    assert flow_mod.DOMAIN == const.DOMAIN
    bron = (flow_mod.CyclingNextRaceConfigFlow.async_step_user.__doc__ or "")
    assert bron is not None
    for stap in ("async_step_user", "async_step_import"):
        code = getattr(flow_mod.CyclingNextRaceConfigFlow, stap).__code__
        assert "_abort_if_unique_id_configured" in code.co_names, (
            f"{stap} controleert niet op een bestaande entry")
