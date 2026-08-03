"""De meegeleverde kaarten moeten passen op wat de sensor levert.

Een kaart die een attribuut opvraagt dat niet bestaat blijft stilletjes
leeg; dat is in Home Assistant lastig te zien en hier goedkoop te vangen.
"""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORTEL = Path(__file__).parent.parent
LOVELACE = WORTEL / "lovelace"
SENSOR = (WORTEL / "custom_components" / "cycling_next_race" / "sensor.py").read_text()
KAARTBESTANDEN = sorted(LOVELACE.glob("*.yaml"))

ENTITEIT = "sensor.cycling_next_race"


def _tekst(pad):
    return pad.read_text(encoding="utf-8")


@pytest.mark.parametrize("pad", KAARTBESTANDEN, ids=lambda p: p.name)
def test_kaartbestand_is_geldige_yaml(pad):
    assert yaml.safe_load(_tekst(pad)) is not None


@pytest.mark.parametrize("pad", KAARTBESTANDEN, ids=lambda p: p.name)
def test_kaarten_wijzen_naar_de_juiste_entiteit(pad):
    tekst = _tekst(pad)
    for verwijzing in set(re.findall(r"sensor\.[a-z_]+", tekst)):
        assert verwijzing == ENTITEIT, f"{pad.name} verwijst naar {verwijzing}"


def test_opgevraagde_attributen_bestaan_in_de_sensor():
    """state_attr(...) en `attribute:` moeten de sensor kennen."""
    gevraagd = set()
    for pad in KAARTBESTANDEN:
        tekst = _tekst(pad)
        gevraagd |= set(re.findall(r"state_attr\([^,]+,\s*'(\w+)'\)", tekst))
        gevraagd |= set(re.findall(r"^\s*attribute:\s*(\w+)\s*$", tekst, re.M))
        # de button-card-templates lezen ze als a.<naam>
        gevraagd |= set(re.findall(r"\ba\.(\w+)", tekst))

    onbekend = {a for a in gevraagd if f'"{a}"' not in SENSOR}
    assert not onbekend, f"kaarten vragen attributen die de sensor niet zet: {sorted(onbekend)}"


def test_gebruikte_templates_bestaan():
    """`template: x` moet in button_card_templates.yaml staan."""
    beschikbaar = set(
        yaml.safe_load(_tekst(LOVELACE / "button_card_templates.yaml"))["button_card_templates"]
    )
    gebruikt = set()
    for pad in KAARTBESTANDEN:
        gebruikt |= set(re.findall(r"^\s*template:\s*([\w-]+)\s*$", _tekst(pad), re.M))
    ontbreekt = gebruikt - beschikbaar
    assert not ontbreekt, f"onbekende templates: {sorted(ontbreekt)}"


def test_tegel_en_popup_delen_dezelfde_hash():
    kaarten = yaml.safe_load(_tekst(LOVELACE / "dashboard.yaml"))
    tegel, popup = kaarten
    assert tegel["card"]["tap_action"]["navigation_path"] == popup["hash"], (
        "de tegel opent een andere pop-up dan er gedefinieerd is")
