"""Cycling Next Race - profwielrennen op je Home Assistant-dashboard.

Instellen gaat via de gebruikersinterface (Instellingen → Apparaten &
Services → Integratie toevoegen). De oude YAML-configuratie blijft werken:
`sensor.py` zet die om in een config entry.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN  # noqa: F401  (blijft importeerbaar als voorheen)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet de integratie op na toevoegen of na een herstart."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ruim op bij verwijderen of herladen."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad zodra de opties zijn gewijzigd, zodat ze meteen gelden."""
    await hass.config_entries.async_reload(entry.entry_id)
