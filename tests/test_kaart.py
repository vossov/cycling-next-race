"""De meegeleverde Lovelace-kaart.

Het tekenwerk van de profielen staat op twee plekken: in de
button-card-templates en in de kaart. Deze tests bewaken dat die twee niet
uiteenlopen, plus de zaken die de kaart onbruikbaar maken als ze ontbreken.
"""
import itertools
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


def test_kaart_noemt_dezelfde_versie(const):
    """De kaart draagt zijn eigen nummer, want hij weet niets van const.py.

    Dat nummer staat in de console en onder in het bewerkscherm, en is de
    enige manier om te zien welke kaart je browser werkelijk draait — Home
    Assistant meldt bij de integratie de versie van de Python-kant, ook als
    de frontend nog een oude kaart uit de cache haalt. Loopt het hier uiteen,
    dan wijst die aanwijzing de verkeerde kant op.
    """
    gevonden = re.search(r"const VERSIE = '([^']+)'", _kaart())
    assert gevonden, "de kaart noemt nergens een versie"
    assert gevonden.group(1) == const.VERSION, (
        f"de kaart zegt {gevonden.group(1)}, const.py zegt {const.VERSION}"
    )


def test_kaart_kent_dezelfde_niveaus_als_const(const):
    """De niveaus staan twee keer: in const.py en in de kaart.

    De kaart is statisch en kan die tabel niet opvragen, dus staat hij er
    nog een keer in. Lopen ze uiteen, dan biedt de editor een niveau aan
    dat de sensor niet levert (of andersom: een niveau dat je nergens meer
    kunt uitzetten).
    """
    tekst = _kaart()
    blok = tekst[tekst.index("const NIVEAUS = ["):tekst.index("const NIVEAU_SLEUTELS")]
    # sleutels zijn sinds 0.19 letters ("m"/"v") in plaats van de
    # circuitnummers van procyclingstats
    gevonden = dict(re.findall(r"value:\s*'([\w-]+)',\s*label:\s*'([^']+)'", blok))
    verwacht = {k: v["naam"] for k, v in const.NIVEAUS.items()}
    assert gevonden == verwacht, (
        f"kaart en const.py lopen uiteen: {set(gevonden.items()) ^ set(verwacht.items())}")


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
    # alleen de optietabel zelf: tot de eerste regel die geen tabelrij meer
    # is. Verderop staan tabellen met de waarden van een optie, en die
    # zouden anders als optienaam meetellen
    regels = readme[readme.index("| Optie |"):].splitlines()
    tabel = "\n".join(itertools.takewhile(lambda r: r.startswith("|"), regels))
    beschreven = set(re.findall(r"\|\s*`(\w+)`\s*\|", tabel))

    assert opties == beschreven, (
        f"kaart en README lopen uiteen: {opties ^ beschreven}")


def test_readme_noemt_dezelfde_secties():
    """Een onderdeel dat de kaart kent maar de README niet noemt.

    `sections` is de enige optie waarvan de waarden ook uitgeschreven staan,
    en een onderdeel dat nergens gedocumenteerd is vindt niemand.
    """
    kaart = _kaart()
    blok = kaart[kaart.index("const SECTIES = ["):kaart.index("const SECTIE_SLEUTELS")]
    secties = set(re.findall(r"key:\s*'(\w+)'", blok))

    readme = (WORTEL / "README.md").read_text(encoding="utf-8")
    stuk = readme[readme.index("### Onderdelen van het detailvenster"):]
    stuk = stuk[:stuk.index("###", 5)]
    genoemd = set(re.findall(r"`(\w+)`", stuk)) - {"sections", "details"}

    assert secties == genoemd, f"kaart en README lopen uiteen: {secties ^ genoemd}"


def test_stempel_verandert_mee_met_het_bestand(wt, const):
    """De cache-buster mag niet afhangen van het ophogen van VERSION.

    Blijft hij gelijk terwijl de kaart wijzigt, dan houdt een browser de
    oude versie vast — precies wat er eerder misging.
    """
    import importlib

    init = importlib.import_module("cycling_next_race")
    pad = COMPONENT / "www" / KAART.name

    eerste = init._bestandsstempel(pad)
    assert eerste and eerste.startswith(const.VERSION)

    origineel = pad.read_bytes()
    try:
        pad.write_bytes(origineel + b"\n// proef\n")
        gewijzigd = init._bestandsstempel(pad)
    finally:
        pad.write_bytes(origineel)

    assert gewijzigd != eerste, "stempel beweegt niet mee met de inhoud"
    assert init._bestandsstempel(pad) == eerste, "stempel is niet stabiel"
    assert init._bestandsstempel(COMPONENT / "www" / "bestaat-niet.js") is None


# ── hoe de kaart bij de frontend komt ───────────────────────────────

class _NepResources:
    """Bootst ResourceStorageCollection na: die kan items schrijven."""

    def __init__(self, items=None):
        self.items = list(items or [])
        self.aangemaakt = []
        self.bijgewerkt = []

    async def async_get_info(self):
        return {"resources": len(self.items)}

    def async_items(self):
        return self.items

    async def async_create_item(self, data):
        self.aangemaakt.append(data)
        self.items.append({"id": "nieuw", **data})
        return self.items[-1]

    async def async_update_item(self, item_id, updates):
        self.bijgewerkt.append((item_id, updates))
        for i in self.items:
            if i["id"] == item_id:
                i.update(updates)

    async def async_delete_item(self, item_id):
        self.items = [i for i in self.items if i["id"] != item_id]


class _NepYamlResources:
    """Bootst ResourceYAMLCollection na.

    Die kent alleen deze twee methoden — schrijven kan er niet, want in
    YAML-modus beheert de gebruiker de lijst zelf. Precies daaraan is de
    modus te herkennen, ongeacht hoe het modusveld in die versie heet.
    """

    loaded = True

    def __init__(self, items=None):
        self.items = list(items or [])

    async def async_get_info(self):
        return {"resources": len(self.items)}

    def async_items(self):
        return self.items


class _NepLovelace:
    """De vorm van `hass.data["lovelace"]` vanaf Home Assistant 2025.2.

    Het veld met de modus heet daar `mode` en heet vanaf 2026.6
    `resource_mode`; welke van de twee erop staat is instelbaar, want de
    registratie mag van geen van beide afhangen.
    """

    def __init__(self, resources, modus="storage", modusveld="mode"):
        self.resources = resources
        if modusveld:
            setattr(self, modusveld, modus)


class _NepHass:
    def __init__(self, lovelace=None):
        self.data = {"lovelace": lovelace} if lovelace is not None else {}


def _init():
    import importlib

    return importlib.import_module("cycling_next_race")


def test_resource_wordt_aangemaakt_als_hij_ontbreekt(wt):
    import asyncio

    init = _init()
    res = _NepResources()
    hass = _NepHass(_NepLovelace(res))
    gelukt = asyncio.run(init._als_lovelace_resource(hass, "/cycling_next_race/x.js?v=1"))

    assert gelukt is True
    assert res.aangemaakt == [{"res_type": "module",
                               "url": "/cycling_next_race/x.js?v=1"}]


def test_bestaande_resource_wordt_bijgewerkt_niet_verdubbeld(wt):
    """Na een update wijzigt de versie achter de URL; één regel volstaat."""
    import asyncio

    init = _init()
    res = _NepResources([{"id": "a1", "res_type": "module",
                          "url": f"{init.KAART_URL}?v=oud"}])
    hass = _NepHass(_NepLovelace(res))
    gelukt = asyncio.run(init._als_lovelace_resource(hass, f"{init.KAART_URL}?v=nieuw"))

    assert gelukt is True
    assert res.aangemaakt == [], "er is een tweede regel bijgekomen"
    assert res.bijgewerkt == [("a1", {"url": f"{init.KAART_URL}?v=nieuw"})]


def test_ongewijzigde_resource_blijft_met_rust(wt):
    import asyncio

    init = _init()
    url = f"{init.KAART_URL}?v=gelijk"
    res = _NepResources([{"id": "a1", "res_type": "module", "url": url}])
    gelukt = asyncio.run(init._als_lovelace_resource(_NepHass(_NepLovelace(res)), url))

    assert gelukt is True
    assert res.aangemaakt == [] and res.bijgewerkt == []


def test_yaml_modus_valt_terug(wt):
    """Daar beheert de gebruiker de lijst zelf; niets aan wijzigen."""
    import asyncio

    init = _init()
    hass = _NepHass(_NepLovelace(_NepYamlResources(), modus="yaml"))
    assert asyncio.run(init._als_lovelace_resource(hass, "/x.js")) is False


def test_zonder_lovelace_valt_terug(wt):
    import asyncio

    init = _init()
    assert asyncio.run(init._als_lovelace_resource(_NepHass(), "/x.js")) is False


# De vorm van hass.data["lovelace"] is drie keer veranderd. Elke keer dat de
# registratie daarop struikelde viel de kaart terug op add_extra_js_url, en
# juist die weg levert de foutkaart op waar het dashboard mee opent. Vandaar
# een test per vorm.

def test_lovelace_als_dict_wordt_herkend(wt):
    """Home Assistant t/m 2024.12: `hass.data["lovelace"]` is een dict.

    `getattr(dict, "resources")` levert daar niets op; wie het zo leest
    registreert nooit een resource.
    """
    import asyncio

    init = _init()
    res = _NepResources()
    hass = _NepHass({"mode": "storage", "resources": res})
    gelukt = asyncio.run(init._als_lovelace_resource(hass, f"{init.KAART_URL}?v=1"))

    assert gelukt is True
    assert res.aangemaakt == [{"res_type": "module", "url": f"{init.KAART_URL}?v=1"}]


def test_lovelace_met_alleen_mode_wordt_herkend(wt):
    """Home Assistant 2025.2 t/m 2026.1: dataclass met `mode`, geen
    `resource_mode`."""
    import asyncio

    init = _init()
    res = _NepResources()
    hass = _NepHass(_NepLovelace(res, modusveld="mode"))

    assert asyncio.run(init._als_lovelace_resource(hass, "/x.js")) is True
    assert res.aangemaakt


def test_lovelace_met_resource_mode_wordt_herkend(wt):
    """Home Assistant vanaf 2026.6: het veld heet `resource_mode`."""
    import asyncio

    init = _init()
    res = _NepResources()
    hass = _NepHass(_NepLovelace(res, modusveld="resource_mode"))

    assert asyncio.run(init._als_lovelace_resource(hass, "/x.js")) is True
    assert res.aangemaakt


def test_verwijderen_haalt_de_resource_weg(wt):
    """Anders blijft de frontend een adres ophalen dat niet meer bestaat."""
    import asyncio

    init = _init()
    res = _NepResources([
        {"id": "a1", "res_type": "module", "url": f"{init.KAART_URL}?v=1"},
        {"id": "a2", "res_type": "module", "url": "/local/iets-anders.js"},
    ])
    hass = _NepHass(_NepLovelace(res))
    hass.data[f"{init.DOMAIN}_kaart_geregistreerd"] = True

    asyncio.run(init.async_remove_entry(hass, None))

    assert [i["id"] for i in res.items] == ["a2"], "de kaart staat er nog, of te veel weg"
    assert f"{init.DOMAIN}_kaart_geregistreerd" not in hass.data, (
        "opnieuw toevoegen zonder herstart meldt de kaart dan niet meer aan"
    )


def test_verwijderen_zonder_resourcelijst_gaat_goed(wt):
    """In YAML-modus valt er niets op te ruimen; dat mag niet stukgaan."""
    import asyncio

    init = _init()
    hass = _NepHass(_NepLovelace(_NepYamlResources(), modus="yaml"))
    asyncio.run(init.async_remove_entry(hass, None))
    asyncio.run(init.async_remove_entry(_NepHass(), None))


def test_lovelace_zonder_modusveld_wordt_herkend(wt):
    """Een volgende hernoeming mag de registratie niet weer stilleggen.

    De modus komt daarom van de collectie zelf — kan die schrijven, dan is
    het de opslagvariant — en niet van een veldnaam die per versie wisselt.
    """
    import asyncio

    init = _init()
    res = _NepResources()
    hass = _NepHass(_NepLovelace(res, modusveld=None))

    assert asyncio.run(init._als_lovelace_resource(hass, "/x.js")) is True
    assert res.aangemaakt


def test_kaart_registreert_zich_niet_dubbel():
    """Via twee wegen geladen mag geen DOMException geven."""
    tekst = _kaart()
    for element in ("cycling-next-race-card", "cycling-next-race-card-editor"):
        assert f"customElements.get('{element}')" in tekst, (
            f"{element} wordt zonder controle gedefinieerd; twee keer laden "
            "gooit dan een DOMException en breekt alles"
        )
