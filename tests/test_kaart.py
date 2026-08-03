"""De meegeleverde Lovelace-kaart.

Het tekenwerk van de profielen staat op twee plekken: in de
button-card-templates en in de kaart. Deze tests bewaken dat die twee niet
uiteenlopen, plus de zaken die de kaart onbruikbaar maken als ze ontbreken.
"""
import json
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORTEL = Path(__file__).parent.parent
COMPONENT = WORTEL / "custom_components" / "cycling_next_race"
KAART = COMPONENT / "www" / "cycling-next-race-card.js"
TEMPLATES = WORTEL / "lovelace" / "button_card_templates.yaml"

# templatenaam -> functienaam in de kaart
OVERGENOMEN = {
    "cycling_profile": "svgTegel",
    "cycling_detail": "svgDetail",
    "cycling_upcoming": "svgKomend",
}


def _configsleutels(tekst):
    """De sleutels uit het this._config-object van de kaart.

    Begrensd op het object zelf; wat erachter komt (zoals de omgang met
    verouderde opties) telt niet mee.
    """
    start = tekst.index("this._config = {")
    eind = tekst.index("};", start)
    blok = tekst[start:eind]
    return set(re.findall(r"^\s*(\w+):", blok, re.M))


def _kaart():
    return KAART.read_text(encoding="utf-8")


def _template_js(naam):
    tpl = yaml.safe_load(TEMPLATES.read_text(encoding="utf-8"))["button_card_templates"]
    code = tpl[naam]["custom_fields"]["profile"].strip()
    return re.sub(r"\]\]\]$", "", re.sub(r"^\[\[\[", "", code)).strip()


def test_kaartbestand_bestaat():
    assert KAART.is_file(), "zonder dit bestand registreert de integratie niets"


def test_kaart_definieert_het_element():
    tekst = _kaart()
    assert "customElements.define('cycling-next-race-card'" in tekst
    assert "window.customCards" in tekst, "kaart verschijnt anders niet in de kaartkiezer"


def _functiebody(tekst, naam):
    """De inhoud van function <naam>(entity) { ... }, via accolades geteld."""
    start = tekst.index(f"function {naam}(entity)")
    open_haak = tekst.index("{", start)
    diepte = 0
    for i in range(open_haak, len(tekst)):
        if tekst[i] == "{":
            diepte += 1
        elif tekst[i] == "}":
            diepte -= 1
            if diepte == 0:
                return tekst[open_haak + 1:i]
    raise AssertionError(f"accolades van {naam} lopen niet rond")


def _regels(code):
    return [r.strip() for r in code.splitlines() if r.strip()]


@pytest.mark.parametrize("template,functie", OVERGENOMEN.items())
def test_tekencode_is_gelijk_aan_de_template(template, functie):
    """Wijzigt de template, dan moet de kaart mee — en andersom.

    De vergelijking gaat per functie: dezelfde regel komt in meerdere
    functies voor, dus zoeken in het hele bestand mist een afwijking.
    """
    tekst = _kaart()
    assert f"function {functie}(entity)" in tekst, f"{functie} ontbreekt in de kaart"

    verwacht = _regels(_template_js(template))
    gevonden = _regels(_functiebody(tekst, functie))
    assert gevonden == verwacht, (
        f"{functie} loopt uit de pas met {template}: "
        f"{len(verwacht)} regels in de template, {len(gevonden)} in de kaart"
    )


def test_versie_komt_overeen_met_het_manifest(const):
    """De versie hangt achter de kaart-URL; loopt hij achter, dan blijft de
    browser de oude kaart tonen."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert const.VERSION == manifest["version"]


def test_manifest_vraagt_de_benodigde_onderdelen():
    """Zonder frontend en http kan de kaart niet geserveerd worden."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest.get("dependencies", [])) >= {"frontend", "http"}


def test_kaart_gebruikt_de_juiste_standaardentiteit(const):
    assert f"'sensor.{const.DOMAIN}'" in _kaart()


def test_editor_bestaat_en_wordt_aangeboden():
    """getConfigElement verwijst naar een element dat er ook echt is."""
    tekst = _kaart()
    verwezen = re.search(r"createElement\('([\w-]+-editor)'\)", tekst)
    assert verwezen, "de kaart biedt geen visuele editor aan"
    naam = verwezen.group(1)
    assert f"customElements.define('{naam}'" in tekst, (
        f"{naam} wordt opgevraagd maar nergens gedefinieerd; "
        "de bewerkknop levert dan geen editor op"
    )


def test_editor_kent_dezelfde_opties_als_de_kaart():
    """Een veld dat de editor niet aanbiedt is via de interface onbereikbaar."""
    tekst = _kaart()
    opties = _configsleutels(tekst)

    velden = tekst[tekst.index("const VELDEN = ["):tekst.index("const EDITOR_STIJL")]
    aangeboden = set(re.findall(r"name:\s*'(\w+)'", velden))

    assert opties == aangeboden, f"editor en kaart lopen uiteen: {opties ^ aangeboden}"


def test_readme_beschrijft_dezelfde_opties():
    """Een optie die alleen in de kaart of alleen in de README staat."""
    kaart = _kaart()
    # de sleutels uit setConfig, tussen de standaardwaarden
    opties = _configsleutels(kaart)

    readme = (WORTEL / "README.md").read_text(encoding="utf-8")
    tabel = readme[readme.index("| Optie |"):readme.index("### Voorbeelden")]
    beschreven = set(re.findall(r"\|\s*`(\w+)`\s*\|", tabel))

    assert opties == beschreven, (
        f"kaart en README lopen uiteen: {opties ^ beschreven}")
