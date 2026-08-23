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


def _standaard(schema, sleutel):
    return next(m for m in schema.schema if str(m) == sleutel).default()


def test_gekozen_niveaus_staan_voorgevinkt(flow_mod, const):
    schema = _optieschema(flow_mod, {const.CONF_LEVELS_POPUP: ["v"]})
    assert _standaard(schema, const.CONF_LEVELS) == const.DEFAULT_LEVELS
    assert _standaard(schema, const.CONF_LEVELS_POPUP) == ["v"]


def test_onbekend_opgeslagen_niveau_blokkeert_het_scherm_niet(flow_mod, const):
    """Een keuzelijst met een waarde buiten de opties weigert Home Assistant.

    Verdwijnt er ooit een niveau uit NIVEAUS, dan zou het optiescherm van
    wie dat niveau had aangevinkt niet meer opengaan.
    """
    schema = _optieschema(flow_mod, {const.CONF_LEVELS: ["m", "999"]})
    assert _standaard(schema, const.CONF_LEVELS) == ["m"]


def test_circuitnummers_van_voor_0_19_worden_vertaald(flow_mod, const):
    """Een bestaande installatie heeft `1`/`24`/`26`/`27` opgeslagen staan.

    `sensor.py` vertaalt die met `OUDE_NIVEAUS`; deed het optiescherm dat
    niet, dan ging het leeg open en wiste het bij de eerstvolgende keer
    opslaan een keuze die de sensor wél nog gebruikte.
    """
    schema = _optieschema(flow_mod, {const.CONF_LEVELS: ["1", "26"],
                                     const.CONF_LEVELS_POPUP: ["24", "27"]})
    # 1 en 26 zijn allebei mannen: één vinkje, geen dubbele
    assert _standaard(schema, const.CONF_LEVELS) == ["m"]
    assert _standaard(schema, const.CONF_LEVELS_POPUP) == ["v"]


def test_flow_is_single_instance(flow_mod, const):
    """Twee keer toevoegen moet afketsen op dezelfde unieke id."""
    assert flow_mod.DOMAIN == const.DOMAIN
    bron = (flow_mod.CyclingNextRaceConfigFlow.async_step_user.__doc__ or "")
    assert bron is not None
    for stap in ("async_step_user", "async_step_import"):
        code = getattr(flow_mod.CyclingNextRaceConfigFlow, stap).__code__
        assert "_abort_if_unique_id_configured" in code.co_names, (
            f"{stap} controleert niet op een bestaande entry")
