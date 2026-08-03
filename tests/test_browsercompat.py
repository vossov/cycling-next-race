"""De kaart moet draaien op oude WebViews.

Wandpanelen (Sonoff, Nspanel en dergelijke) draaien vaak een Android
WebView die jaren achterloopt. Home Assistant laadt onze kaart met
`add_extra_js_url`, en dat betekent: het script staat op **elke** pagina,
ook op de loginpagina en op dashboards waar de kaart niet op staat. Een
enkele parse-fout legt daarmee de hele frontend van dat apparaat plat, en
de gebruiker kan er niet omheen zonder de integratie uit te zetten.

Deze test bewaakt de ondergrens. Draait op de tekst van het bestand, dus
zonder browser of npm.
"""
import re
from pathlib import Path

import pytest

WORTEL = Path(__file__).parent.parent
KAART = WORTEL / "custom_components" / "cycling_next_race" / "www" / "cycling-next-race-card.js"

# Alles wat de kaart gebruikt moet in deze browser werken. Chrome 61 is de
# WebView van Android 8, wat op dit soort panelen nog volop draait.
MAX_CHROME = 61


def _kaart():
    return KAART.read_text(encoding="utf-8")


def _css_blokken(tekst):
    """De inhoud van de template literals met stijlen, zonder commentaar.

    Commentaar telt niet mee: daar staat juist uitgelegd waarom iets
    vermeden wordt, en die uitleg mag de controle niet laten afgaan.
    """
    uit = []
    for naam in ("STIJL", "EDITOR_STIJL"):
        # vanaf ná het backtick, anders telt de declaratie mee als selector
        start = tekst.index(f"const {naam} = `") + len(f"const {naam} = `")
        uit.append(tekst[start:tekst.index("`;", start)])
    return re.sub(r"/\*.*?\*/", "", "\n".join(uit), flags=re.S)


# (patroon, sinds welke Chrome, waarom het breekt)
SYNTAX = [
    (r"\?\.(?=[A-Za-z_$\[(])", 80, "optional chaining — SyntaxError, de hele module draait niet"),
    (r"\?\?", 80, "nullish coalescing — SyntaxError, de hele module draait niet"),
    (r"\|\|=|&&=|\?\?=", 85, "logische toewijzing — SyntaxError"),
    (r"^\s*#[A-Za-z_]\w*\s*[=;(]", 74, "private klassevelden — SyntaxError"),
    (r"\bstatic\s*\{", 94, "static initialisatieblok — SyntaxError"),
]

API = [
    ("replaceChildren", 86, "TypeError bij gebruik"),
    ("structuredClone", 98, "bestaat niet"),
    ("Object.fromEntries", 73, "bestaat niet"),
    ("replaceAll", 85, "bestaat niet"),
    ("globalThis", 71, "bestaat niet"),
    ("flatMap", 69, "bestaat niet"),
    ("requestIdleCallback", 47, "bestaat niet"),
]

CSS = [
    ("gap:", 84, "flexbox-gap wordt genegeerd; alles plakt aan elkaar"),
    ("inset:", 87, "wordt genegeerd"),
    ("aspect-ratio", 88, "wordt genegeerd"),
    (":is(", 88, "de hele regel wordt overgeslagen"),
    (":where(", 88, "de hele regel wordt overgeslagen"),
    ("backdrop-filter", 76, "wordt genegeerd"),
    ("clamp(", 79, "de eigenschap valt weg"),
    ("content-visibility", 85, "wordt genegeerd"),
]


@pytest.mark.parametrize("patroon,sinds,gevolg", SYNTAX,
                         ids=[p[2].split(" —")[0] for p in SYNTAX])
def test_geen_te_nieuwe_syntax(patroon, sinds, gevolg):
    if sinds <= MAX_CHROME:
        pytest.skip(f"werkt al vanaf Chrome {sinds}")
    treffers = re.findall(patroon, _kaart(), re.M)
    assert not treffers, (
        f"{len(treffers)}x aangetroffen; vereist Chrome {sinds}, "
        f"wij mikken op {MAX_CHROME}. {gevolg}"
    )


@pytest.mark.parametrize("naam,sinds,gevolg", API, ids=[a[0] for a in API])
def test_geen_te_nieuwe_api(naam, sinds, gevolg):
    if sinds <= MAX_CHROME:
        pytest.skip(f"werkt al vanaf Chrome {sinds}")
    assert naam not in _kaart(), (
        f"{naam} vereist Chrome {sinds}, wij mikken op {MAX_CHROME}. {gevolg}"
    )


@pytest.mark.parametrize("eigenschap,sinds,gevolg", CSS, ids=[c[0] for c in CSS])
def test_geen_te_nieuwe_css(eigenschap, sinds, gevolg):
    if sinds <= MAX_CHROME:
        pytest.skip(f"werkt al vanaf Chrome {sinds}")
    css = _css_blokken(_kaart())
    assert eigenschap not in css, (
        f"{eigenschap} vereist Chrome {sinds}, wij mikken op {MAX_CHROME}. {gevolg}"
    )


def _regels(css):
    """(selector, inhoud) per CSS-regel."""
    return [(s.strip(), b) for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


# flex-containers waar de kinderen elkaar niet hoeven te ontlopen
GEEN_RUIMTE_NODIG = {
    ".kop",  # de sluitknop staat op margin-left:auto en duwt zichzelf weg
}


def test_flexbox_zonder_gap_heeft_marges():
    """Wie `gap` weglaat moet de ruimte teruggeven, anders plakt alles.

    `gap` in flexbox werkt pas vanaf Chrome 84 en wordt daaronder stilzwijgend
    genegeerd — de opmaak valt dan in elkaar zonder dat er iets faalt.
    """
    css = _css_blokken(_kaart())
    flex = {s for s, b in _regels(css) if re.search(r"display:\s*flex", b)}
    met_marge = {
        s.split(">")[0].strip()
        for s, _ in _regels(css)
        if re.search(r">\s*\*\s*\+\s*\*\s*$", s)
    }
    zonder = sorted(flex - met_marge - GEEN_RUIMTE_NODIG)
    assert not zonder, (
        f"flex-containers zonder ruimte tussen de kinderen: {zonder}. "
        "Gebruik `> * + * { margin-... }` in plaats van gap."
    )
