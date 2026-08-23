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
    # De kaart is een extraatje; de sensor is bruikbaar zonder. `_registreer_kaart`
    # vangt zijn eigen fouten af, maar niet allemaal — `add_extra_js_url` en het
    # lezen van het kaartbestand staan erbuiten. Ging daar iets mis, dan viel de
    # hele integratie om en bleef er een herstelde entiteit over zonder
    # attributen. Dat mag een dashboardkaart nooit veroorzaken.
    try:
        await _registreer_kaart(hass)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Kaart registreren mislukt, de sensor draait door: %s", err)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ruim op bij verwijderen of herladen.

    Het statische pad en de scriptverwijzing blijven staan: Home Assistant
    kan die pas bij een herstart weer kwijt.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Haal de kaart uit de resourcelijst als de integratie eruit gaat.

    Zolang de registratie stilzwijgend faalde viel er niets op te ruimen —
    `add_extra_js_url` staat alleen in het geheugen en is na een herstart
    weg. Nu er werkelijk een regel in `.storage/lovelace_resources`
    terechtkomt, blijft die zonder dit staan en haalt de frontend bij elke
    paginalading een adres op dat niet meer bestaat.

    Het statische pad zelf blijft wel staan; dat kan Home Assistant pas bij
    een herstart kwijt. Faalt het opruimen, dan is dat geen reden om het
    verwijderen te laten mislukken.
    """
    resources = _resourcecollectie(hass)
    verwijder = getattr(resources, "async_delete_item", None)
    if callable(verwijder):
        try:
            await resources.async_get_info()
            for item in list(resources.async_items() or []):
                if str(item.get("url", "")).split("?")[0] == KAART_URL:
                    await verwijder(item["id"])
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Kaart uit de resourcelijst halen lukte niet: %s", err)

    # opnieuw toevoegen zonder herstart moet de kaart weer aanmelden
    hass.data.pop(_KAART_GEREGISTREERD, None)


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
        hass.data[_KAART_GEREGISTREERD] = True
        # op info-niveau: zonder deze regel in het log is de kaart niet
        # aangemeld, en dat is precies wat je wilt weten als hij niet verschijnt
        _LOGGER.info("Lovelace-kaart aangemeld als Lovelace-resource op %s", url)
        return

    # Terugval voor YAML-modus, waar de resourcelijst niet te wijzigen is.
    # Het script komt dan op elke pagina en Lovelace wacht er niet op,
    # waardoor een kaart soms als "Configuratiefout" verschijnt tot je
    # ververst. Vandaar een waarschuwing in plaats van een mededeling: dit
    # is de weg waarop dat gebeurt, en dan wil je in het log kunnen zien
    # dat het deze is.
    add_extra_js_url(hass, url)
    hass.data[_KAART_GEREGISTREERD] = True
    _LOGGER.warning(
        "Lovelace-kaart aangemeld via extra_js_url op %s. Lovelace wacht "
        "daar niet op, dus de kaart kan bij het openen van een dashboard "
        "kort als 'Configuratiefout' verschijnen. Draait Lovelace in "
        "YAML-modus, zet dan zelf %s in de resourcelijst.",
        url,
        url,
    )


def _resourcecollectie(hass: HomeAssistant):
    """De resourcecollectie van Lovelace, of None als die niet bruikbaar is.

    `hass.data["lovelace"]` heeft drie vormen gehad, en dat is precies waar
    het eerder op misging:

    | Home Assistant   | vorm                      | modusveld       |
    |------------------|---------------------------|-----------------|
    | t/m 2024.12      | dict                      | `mode`          |
    | 2025.2 – 2026.1  | dataclass `LovelaceData`  | `mode`          |
    | vanaf 2026.2     | dataclass `LovelaceData`  | `resource_mode` |

    (Nagekeken in de broncode van die versies; in 2026.2 is `mode`
    hernoemd omdat de modus van de resources losstaat van die van de
    dashboards.)

    Op de modus aftasten met één vaste attribuutnaam ging daarom altijd mis:
    de vraag `getattr(lovelace, "resource_mode", None) != "storage"` was op
    elke versie waar waarop deze integratie ooit gedraaid heeft, waarna de
    kaart stil terugviel op `add_extra_js_url` — juist de weg die de
    foutkaart oplevert.

    Vandaar dat de vraag nu aan de collectie zelf wordt gesteld in plaats
    van aan een veldnaam: alleen `ResourceStorageCollection` kan items
    aanmaken en bijwerken. `ResourceYAMLCollection` kent enkel
    `async_get_info` en `async_items` — daar beheert de gebruiker de lijst
    zelf en valt er niets te schrijven. Dat onderscheid staat vast zolang
    die twee klassen bestaan en overleeft dus een hernoemd veld.
    """
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return None

    if isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    else:
        resources = getattr(lovelace, "resources", None)
    if resources is None:
        return None

    nodig = ("async_get_info", "async_items", "async_create_item", "async_update_item")
    if not all(callable(getattr(resources, m, None)) for m in nodig):
        _LOGGER.debug(
            "Lovelace beheert zijn resources zelf (%s); de kaart gaat via "
            "extra_js_url", type(resources).__name__
        )
        return None
    return resources


async def _als_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Zet de kaart in de resourcelijst van Lovelace.

    Dat is beter dan `add_extra_js_url`: Lovelace laadt zijn resources en
    wacht daarop vóór het tekenen van de kaarten. Bij extra_js_url gebeurt
    dat niet, en dan kan een kaart getekend worden voordat het element
    bestaat — de foutkaart die na verversen weg is.

    Lukt alleen in storage-modus; in YAML-modus beheert de gebruiker de
    lijst zelf en is die hier niet te wijzigen.
    """
    resources = _resourcecollectie(hass)
    if resources is None:
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
