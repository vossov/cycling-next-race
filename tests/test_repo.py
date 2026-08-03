"""Controles op de repo-bestanden die hassfest en HACS in CI valideren.

Deze draaien zonder netwerk en vangen fouten af die anders pas in GitHub
Actions zichtbaar worden.
"""
import json
from pathlib import Path

WORTEL = Path(__file__).parent.parent
COMPONENT = WORTEL / "custom_components" / "cycling_next_race"
MANIFEST = COMPONENT / "manifest.json"
HACS_JSON = WORTEL / "hacs.json"
STRINGS = COMPONENT / "strings.json"
VERTALINGEN = COMPONENT / "translations"


def _laad(pad):
    return json.loads(pad.read_text(encoding="utf-8"))


# ── manifest.json ───────────────────────────────────────────────────

def test_manifest_sleutels_zijn_gesorteerd():
    """Hassfest eist: domain, name, daarna alfabetisch."""
    sleutels = list(_laad(MANIFEST))
    assert sleutels[:2] == ["domain", "name"]
    rest = sleutels[2:]
    assert rest == sorted(rest), f"niet alfabetisch: {rest}"


def test_manifest_heeft_wat_hacs_vereist():
    """INTEGRATION_MANIFEST_JSON_SCHEMA van HACS."""
    m = _laad(MANIFEST)
    for sleutel in ("codeowners", "documentation", "domain", "issue_tracker",
                    "name", "version"):
        assert sleutel in m, f"manifest mist {sleutel}"
    assert isinstance(m["codeowners"], list)
    assert m["documentation"].startswith("https://")
    assert m["issue_tracker"].startswith("https://")
    assert m["version"]


# ── hacs.json ───────────────────────────────────────────────────────

# HACS_MANIFEST_JSON_SCHEMA weigert onbekende sleutels (PREVENT_EXTRA).
HACS_TOEGESTAAN = {
    "content_in_root", "country", "filename", "hacs", "hide_default_branch",
    "homeassistant", "name", "persistent_directory", "render_readme",
    "zip_release",
}


def test_hacs_json_is_geldig():
    h = _laad(HACS_JSON)
    assert "name" in h, "hacs.json mist de verplichte sleutel 'name'"
    onbekend = set(h) - HACS_TOEGESTAAN
    assert not onbekend, f"onbekende sleutels in hacs.json: {onbekend}"
    if h.get("zip_release"):
        assert h.get("filename"), "zip_release zonder filename"


# ── config flow ─────────────────────────────────────────────────────

def test_config_flow_is_aangemeld():
    """Zonder deze vlag toont HA geen toevoegscherm."""
    assert _laad(MANIFEST).get("config_flow") is True
    assert (COMPONENT / "config_flow.py").exists()


def _sleutelboom(obj, pad=""):
    """Alle sleutelpaden van een geneste dict, voor vergelijking."""
    if not isinstance(obj, dict):
        return {pad}
    uit = set()
    for k, v in obj.items():
        uit |= _sleutelboom(v, f"{pad}.{k}" if pad else k)
    return uit


def test_vertalingen_dekken_dezelfde_sleutels():
    """Een ontbrekende vertaling laat hassfest struikelen en het scherm leeg."""
    verwacht = _sleutelboom(_laad(STRINGS))
    bestanden = sorted(VERTALINGEN.glob("*.json"))
    assert bestanden, "geen vertalingen gevonden"
    assert (VERTALINGEN / "en.json").exists(), "en.json is verplicht"
    for pad in bestanden:
        assert _sleutelboom(_laad(pad)) == verwacht, f"{pad.name} wijkt af van strings.json"


def test_optiescherm_kent_elke_optie(const):
    """Elke optiesleutel heeft een standaardwaarde en een label."""
    labels = set(_laad(STRINGS)["options"]["step"]["init"]["data"])
    sleutels = {v for k, v in vars(const).items()
                if k.startswith("CONF_") and isinstance(v, str)}
    assert sleutels == labels, f"verschil tussen CONF_* en de labels: {sleutels ^ labels}"
    assert set(const.OPTION_DEFAULTS) == sleutels, "OPTION_DEFAULTS dekt niet elke optie"


def test_standaardwaarden_liggen_binnen_de_grenzen(const):
    grenzen = {
        const.CONF_RESULT_N: (const.MIN_RIDERS, const.MAX_RIDERS),
        const.CONF_GC_N: (const.MIN_RIDERS, const.MAX_RIDERS),
        const.CONF_UPCOMING_DAYS: (const.MIN_UPCOMING_DAYS, const.MAX_UPCOMING_DAYS),
        const.CONF_SCAN_MINUTES: (const.MIN_SCAN_MINUTES, const.MAX_SCAN_MINUTES),
        const.CONF_LIVE_SCAN_MINUTES: (const.MIN_LIVE_SCAN_MINUTES,
                                       const.MAX_LIVE_SCAN_MINUTES),
    }
    for sleutel, (laag, hoog) in grenzen.items():
        waarde = const.OPTION_DEFAULTS[sleutel]
        assert laag <= waarde <= hoog, f"{sleutel}={waarde} valt buiten [{laag}, {hoog}]"


def test_sensor_gebruikt_dezelfde_standaarden(wt, const):
    """De oude module-constanten en de nieuwe defaults mogen niet uiteenlopen."""
    assert wt.RESULT_N == const.DEFAULT_RESULT_N
    assert wt.GC_N == const.DEFAULT_GC_N
    assert wt.UPCOMING_N == const.DEFAULT_UPCOMING_N
    assert wt.UPCOMING_DAYS == const.DEFAULT_UPCOMING_DAYS
    assert wt.SCAN_INTERVAL.total_seconds() == const.DEFAULT_SCAN_MINUTES * 60
    assert wt.LIVE_SCAN_INTERVAL.total_seconds() == const.DEFAULT_LIVE_SCAN_MINUTES * 60
