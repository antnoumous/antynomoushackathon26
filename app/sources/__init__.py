from __future__ import annotations
from pathlib import Path
from app.config import RunConfig
from app.sources.base import Source, SourceError, SourceResult, Scope
from app.sources.iac_fixture import IaCFixtureSource
from app.sources.inventory_fixture import InventoryFixtureSource
from app.sources.policy_fixture import PolicyFixtureSource
from app.sources.telemetry_fixture import TelemetryFixtureSource

FIXTURE_BACKENDS = {
    "inventory": InventoryFixtureSource,
    "telemetry": TelemetryFixtureSource,
    "iac": IaCFixtureSource,
    "policy": PolicyFixtureSource,
}


def get_source(name: str, config: RunConfig, scenario_dir: Path | None = None) -> Source:
    if config.sample_mode:
        backend = FIXTURE_BACKENDS.get(name)
        if backend is None:
            raise KeyError(name)
        if scenario_dir is None:
            raise SourceError("sample mode needs a scenario directory")
        return backend(scenario_dir)

    from app.sources import live  # imported lazily: sample mode never imports the OCI SDK

    return live.get_live_source(name, config, scenario_dir=scenario_dir)
