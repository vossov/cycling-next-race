"""Config flow voor Cycling Next Race.

De integratie heeft niets nodig om te starten — geen sleutel, geen adres —
dus het toevoegscherm bevestigt alleen. Wat je wél kunt bijstellen staat in
het optiescherm en komt terecht in `ConfigEntry.options`.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)

from .const import (
    CONF_GC_N,
    CONF_LIVE_SCAN_MINUTES,
    CONF_RESULT_N,
    CONF_SCAN_MINUTES,
    CONF_UPCOMING_DAYS,
    CONF_UPCOMING_N,
    DOMAIN,
    MAX_LIVE_SCAN_MINUTES,
    MAX_RIDERS,
    MAX_SCAN_MINUTES,
    MAX_UPCOMING_DAYS,
    MIN_LIVE_SCAN_MINUTES,
    MIN_RIDERS,
    MIN_SCAN_MINUTES,
    MIN_UPCOMING_DAYS,
    NAME,
    OPTION_DEFAULTS,
)


def _aantal(minimum: int, maximum: int):
    """Geheel getal binnen grenzen."""
    return vol.All(vol.Coerce(int), vol.Range(min=minimum, max=maximum))


class CyclingNextRaceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Toevoegen via Instellingen → Apparaten & Services."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Eén bevestiging; er valt niets in te vullen."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_import(
        self, import_data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Overname van de oude YAML-configuratie (`sensor: - platform: ...`)."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=NAME, data={})

    @staticmethod
    def async_get_options_flow(config_entry) -> CyclingNextRaceOptionsFlow:
        """Het optiescherm achter de knop Configureren."""
        return CyclingNextRaceOptionsFlow()


class CyclingNextRaceOptionsFlow(OptionsFlow):
    """Instellingen die anders als constante in sensor.py zouden staan."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        huidig = {**OPTION_DEFAULTS, **dict(self.config_entry.options)}

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_RESULT_N, default=huidig[CONF_RESULT_N]
                ): _aantal(MIN_RIDERS, MAX_RIDERS),
                vol.Optional(CONF_GC_N, default=huidig[CONF_GC_N]): _aantal(
                    MIN_RIDERS, MAX_RIDERS
                ),
                vol.Optional(
                    CONF_UPCOMING_N, default=huidig[CONF_UPCOMING_N]
                ): _aantal(1, 30),
                vol.Optional(
                    CONF_UPCOMING_DAYS, default=huidig[CONF_UPCOMING_DAYS]
                ): _aantal(MIN_UPCOMING_DAYS, MAX_UPCOMING_DAYS),
                vol.Optional(
                    CONF_SCAN_MINUTES, default=huidig[CONF_SCAN_MINUTES]
                ): _aantal(MIN_SCAN_MINUTES, MAX_SCAN_MINUTES),
                vol.Optional(
                    CONF_LIVE_SCAN_MINUTES, default=huidig[CONF_LIVE_SCAN_MINUTES]
                ): _aantal(MIN_LIVE_SCAN_MINUTES, MAX_LIVE_SCAN_MINUTES),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
