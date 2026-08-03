"""Cycling Next Race - profwielrennen op je Home Assistant-dashboard.

Instellen gaat via de gebruikersinterface (Instellingen → Apparaten &
Services → Integratie toevoegen). De Lovelace-kaart wordt hier geregistreerd,
zodat je zelf niets aan resources hoeft toe te voegen.
"""
from __future__ import annotations

import hashlib
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
    stempel = await hass.async_add_executor_job(_bestandsstempel, pad)
    if stempel is None:
        _LOGGER.warning("Kaartbestand niet gevonden op %s", pad)
        return

    url = f"{KAART_URL}?v={stempel}"
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(KAART_URL, str(pad), False)]
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Kaart serveren mislukt: %s", err)
        return

    if await _als_lovelace_resource(hass, url):
        weg = "Lovelace-resource"
    else:
        # Terugval voor YAML-modus, waar de resourcelijst niet te wijzigen is.
        # Het script komt dan op elke pagina en Lovelace wacht er niet op,
        # waardoor een kaart soms als "Configuratiefout" verschijnt tot je
        # ververst.
        add_extra_js_url(hass, url)
        weg = "extra_js_url"

    hass.data[_KAART_GEREGISTREERD] = True
    # op info-niveau: zonder deze regel in het log is de kaart niet aangemeld,
    # en dat is precies wat je wilt weten als hij niet verschijnt
    _LOGGER.info("Lovelace-kaart aangemeld via %s op %s", weg, url)


async def _als_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Zet de kaart in de resourcelijst van Lovelace.

    Dat is beter dan `add_extra_js_url`: Lovelace laadt zijn resources en
    wacht daarop vóór het tekenen van de kaarten. Bij extra_js_url gebeurt
    dat niet, en dan kan een kaart getekend worden voordat het element
    bestaat — de foutkaart die na verversen weg is.

    Lukt alleen in storage-modus; in YAML-modus beheert de gebruiker de
    lijst zelf en is die hier niet te wijzigen.
    """
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None or getattr(lovelace, "resource_mode", None) != "storage":
        return False

    try:
        # zorgt dat de opgeslagen lijst is ingelezen
        await resources.async_get_info()

        for item in resources.async_items() or []:
            if str(item.get("url", "")).split("?")[0] != KAART_URL:
                continue
            if item.get("url") != url:
                # zelfde kaart, nieuwe inhoud: alleen de versie bijwerken
                await resources.async_update_item(item["id"], {"url": url})
            return True

        await resources.async_create_item({"res_type": "module", "url": url})
        return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Kaart als Lovelace-resource registreren lukte niet: %s", err)
        return False


def _bestandsstempel(pad: Path) -> str | None:
    """Versie plus een korte hash van de kaart, voor achter de URL.

    De hash maakt het onmogelijk dat een browser een oude kaart blijft
    tonen: wijzigt het bestand, dan wijzigt de URL. Zonder die hash zou dat
    afhangen van het ophogen van VERSION, en dat wordt vergeten.

    Draait in een executor; leest het bestand van schijf.
    """
    if not pad.is_file():
        return None
    korte_hash = hashlib.sha256(pad.read_bytes()).hexdigest()[:10]
    return f"{VERSION}-{korte_hash}"
