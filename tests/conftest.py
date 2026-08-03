"""Laadt sensor.py zonder dat Home Assistant geïnstalleerd hoeft te zijn.

De HA-imports worden vervangen door lege stubs; alle pure functies
(parsers, berekeningen) zijn daarna gewoon te testen.

Het component wordt als package geladen — `sensor.py` doet `from .const
import ...` en dat werkt niet met een los bestand.
"""
import importlib
import sys
import types
from pathlib import Path

import pytest

COMPONENTS = Path(__file__).parent.parent / "custom_components"


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
    # ConfigFlow neemt `domain=` mee in de klassedefinitie, vandaar het
    # eigen __init_subclass__; een kale type() weigert dat.
    def _init_subclass(cls, **kwargs):
        return None

    config_flow_stub = type("ConfigFlow", (), {
        "__init__": lambda self, *a, **kw: None,
        "__init_subclass__": classmethod(_init_subclass),
    })

    _stub("homeassistant.config_entries",
          ConfigEntry=_klasse("ConfigEntry"),
          ConfigFlow=config_flow_stub,
          ConfigFlowResult=dict,
          OptionsFlow=_klasse("OptionsFlow"),
          SOURCE_IMPORT="import")
    _stub("homeassistant.const", Platform=types.SimpleNamespace(SENSOR="sensor"))
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
    if str(COMPONENTS) not in sys.path:
        sys.path.insert(0, str(COMPONENTS))
    return importlib.import_module("cycling_next_race.sensor")


@pytest.fixture(scope="session")
def const():
    """De constantenmodule."""
    _installeer_stubs()
    if str(COMPONENTS) not in sys.path:
        sys.path.insert(0, str(COMPONENTS))
    return importlib.import_module("cycling_next_race.const")


@pytest.fixture(scope="session")
def flow_mod():
    """De config-flow-module; vereist voluptuous."""
    pytest.importorskip("voluptuous")
    _installeer_stubs()
    if str(COMPONENTS) not in sys.path:
        sys.path.insert(0, str(COMPONENTS))
    return importlib.import_module("cycling_next_race.config_flow")
