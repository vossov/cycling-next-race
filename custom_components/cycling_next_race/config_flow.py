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
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_GC_N,
    CONF_LEVELS,
    CONF_LEVELS_POPUP,
    CONF_LIVE_SCAN_MINUTES,
    CONF_MAX_OTHER,
    CONF_RESULT_N,
    CONF_SCAN_MINUTES,
    CONF_START_N,
    CONF_UPCOMING_DAYS,
    CONF_PAST_N,
    CONF_UPCOMING_N,
    DOMAIN,
    MAX_LIVE_SCAN_MINUTES,
    MAX_OTHER_LIMIT,
    MAX_PAST_N,
    MAX_RIDERS,
    MAX_SCAN_MINUTES,
    MAX_UPCOMING_DAYS,
    MIN_LIVE_SCAN_MINUTES,
    MIN_OTHER,
    MIN_RIDERS,
    MIN_SCAN_MINUTES,
    MIN_UPCOMING_DAYS,
    NAME,
    NIVEAU_KEUZE,
    OPTION_DEFAULTS,
    OUDE_NIVEAUS,
)


def _aantal(minimum: int, maximum: int):
    """Geheel getal binnen grenzen."""
    return vol.All(vol.Coerce(int), vol.Range(min=minimum, max=maximum))


def _lijst(waarde) -> list[str]:
    """Opgeslagen niveaus als lijst met bekende sleutels.

    Opslag van v\u00f3\u00f3r 0.19 bevat de circuitnummers van procyclingstats;
    `OUDE_NIVEAUS` vertaalt die, net als in `sensor.py`. Zonder dat zou het
    optiescherm van een bestaande installatie leeg opengaan en zou de
    eerstvolgende keer opslaan de keuze wissen.

    Wat daarna nog niet bestaat valt weg: een keuzelijst met een waarde die
    niet in de opties staat weigert Home Assistant, en dan is het scherm
    niet meer te openen.
    """
    if not isinstance(waarde, (list, tuple)):
        waarde = [waarde] if waarde else []
    uit: list[str] = []
    for v in waarde:
        n = OUDE_NIVEAUS.get(str(v), str(v))
        if n in NIVEAU_KEUZE and n not in uit:
            uit.append(n)
    return uit


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
                    CONF_START_N, default=huidig[CONF_START_N]
                ): _aantal(MIN_RIDERS, MAX_RIDERS),
                vol.Optional(
                    CONF_UPCOMING_N, default=huidig[CONF_UPCOMING_N]
                ): _aantal(1, 30),
                vol.Optional(
                    CONF_UPCOMING_DAYS, default=huidig[CONF_UPCOMING_DAYS]
                ): _aantal(MIN_UPCOMING_DAYS, MAX_UPCOMING_DAYS),
                # 0 zet het terugbladeren uit; elke etappe kost ruimte in de
                # attributen, en die zitten al tegen de grens van de recorder.
                # Het maximum is een hele grote ronde: wie de Vuelta van
                # etappe 1 af wil kunnen nalezen heeft er 21 nodig.
                vol.Optional(
                    CONF_PAST_N, default=huidig[CONF_PAST_N]
                ): _aantal(0, MAX_PAST_N),
                vol.Optional(
                    CONF_SCAN_MINUTES, default=huidig[CONF_SCAN_MINUTES]
                ): _aantal(MIN_SCAN_MINUTES, MAX_SCAN_MINUTES),
                vol.Optional(
                    CONF_LIVE_SCAN_MINUTES, default=huidig[CONF_LIVE_SCAN_MINUTES]
                ): _aantal(MIN_LIVE_SCAN_MINUTES, MAX_LIVE_SCAN_MINUTES),
                # Welke niveaus meedoen. Aanvinken wat op het dashboard mag
                # komen, en los daarvan wat je alleen in de pop-up wilt zien.
                vol.Optional(
                    CONF_LEVELS, default=_lijst(huidig[CONF_LEVELS])
                ): cv.multi_select(NIVEAU_KEUZE),
                vol.Optional(
                    CONF_LEVELS_POPUP, default=_lijst(huidig[CONF_LEVELS_POPUP])
                ): cv.multi_select(NIVEAU_KEUZE),
                vol.Optional(
                    CONF_MAX_OTHER, default=huidig[CONF_MAX_OTHER]
                ): _aantal(MIN_OTHER, MAX_OTHER_LIMIT),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
