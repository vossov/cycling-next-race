"""Cycling Next Race - profwielrennen op je Home Assistant-dashboard.

Instellen gaat via de gebruikersinterface (Instellingen → Apparaten &
Services → Integratie toevoegen). De Lovelace-kaart wordt hier geregistreerd,
zodat je zelf niets aan resources hoeft toe te voegen.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, KAART_BESTAND, KAART_URL, VERSION  # noqa: F401

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
_KAART_GEREGISTREERD = f"{DOMAIN}_kaart_geregistreerd"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet de integratie op na toevoegen of na een herstart."""
    await _registreer_kaart(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ruim op bij verwijderen of herladen.

    Het statische pad en de scriptverwijzing blijven staan: Home Assistant
    kan die pas bij een herstart weer kwijt.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad zodra de opties zijn gewijzigd, zodat ze meteen gelden."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _registreer_kaart(hass: HomeAssistant) -> None:
    """Serveer de kaart en laat de frontend hem laden.

    Faalt dit, dan draait de integratie gewoon door: de sensor is bruikbaar
    zonder de kaart, en de gebruiker kan hem desnoods zelf als resource
    toevoegen.
    """
    if hass.data.get(_KAART_GEREGISTREERD):
        return

    pad = Path(__file__).parent / "www" / KAART_BESTAND
    if not await hass.async_add_executor_job(pad.is_file):
        _LOGGER.warning("Kaartbestand niet gevonden op %s", pad)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(KAART_URL, str(pad), False)]
        )
        # de versie erachter dwingt de browser na een update te herladen
        add_extra_js_url(hass, f"{KAART_URL}?v={VERSION}")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Kaart registreren mislukt: %s", err)
        return

    hass.data[_KAART_GEREGISTREERD] = True
    # op info-niveau: zonder deze regel in het log is de kaart niet aangemeld,
    # en dat is precies wat je wilt weten als hij niet verschijnt
    _LOGGER.info("Lovelace-kaart aangemeld op %s?v=%s", KAART_URL, VERSION)
