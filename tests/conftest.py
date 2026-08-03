"""Laadt sensor.py zonder dat Home Assistant geïnstalleerd hoeft te zijn.

De HA-imports worden vervangen door lege stubs; alle pure functies
(parsers, berekeningen) zijn daarna gewoon te testen.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _stub(naam, **attrs):
    mod = types.ModuleType(naam)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[naam] = mod
    return mod


def _installeer_stubs():
    def _klasse(naam):
        # elke stub een eigen klasse; sensor.py erft van er twee tegelijk
        return type(naam, (), {"__init__": lambda self, *a, **kw: None})

    _stub("homeassistant")
    _stub("homeassistant.components")
    _stub("homeassistant.components.sensor", SensorEntity=_klasse("SensorEntity"))
    _stub("homeassistant.core", HomeAssistant=_klasse("HomeAssistant"))
    _stub("homeassistant.helpers")
    _stub("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    _stub("homeassistant.helpers.update_coordinator",
          DataUpdateCoordinator=_klasse("DataUpdateCoordinator"),
          CoordinatorEntity=_klasse("CoordinatorEntity"),
          UpdateFailed=type("UpdateFailed", (Exception,), {}))
    _stub("homeassistant.util")
    _stub("homeassistant.util.dt", now=lambda: None)


@pytest.fixture(scope="session")
def wt():
    """De geladen sensor-module."""
    _installeer_stubs()
    pad = (Path(__file__).parent.parent / "custom_components"
           / "cycling_next_race" / "sensor.py")
    spec = importlib.util.spec_from_file_location("wt_sensor", pad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
