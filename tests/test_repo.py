"""Controles op de repo-bestanden die hassfest en HACS in CI valideren.

Deze draaien zonder netwerk en vangen fouten af die anders pas in GitHub
Actions zichtbaar worden.
"""
import json
from pathlib import Path

WORTEL = Path(__file__).parent.parent
MANIFEST = WORTEL / "custom_components" / "worldtour_next_race" / "manifest.json"
HACS_JSON = WORTEL / "hacs.json"


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
