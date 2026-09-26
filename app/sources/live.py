# app/sources/live.py
"""Live backends.

Inventory and telemetry are real OCI adapters (`oci_inventory`, `oci_telemetry`), built and
tested offline but **not yet verified against a live tenancy** — that needs the lab tenancy from
`docs/lab-tenancy.md` to exist first. The IaC repository and the policy catalog are files, not OCI
services, so the same file-backed adapters serve both modes; in a live run they read the scenario
directory the run was pointed at (for the lab tenancy that is `data/scenarios/lab_live`).

This module is imported lazily by the source registry, so sample mode never touches the SDK.
"""
from __future__ import annotations

from pathlib import Path

from app.config import RunConfig
from app.sources.base import SourceError
from app.sources.iac_fixture import IaCFixtureSource
from app.sources.oci_inventory import OCIInventorySource
from app.sources.oci_telemetry import OCITelemetrySource
from app.sources.policy_fixture import PolicyFixtureSource

FILE_BACKED = {"iac": IaCFixtureSource, "policy": PolicyFixtureSource}


def get_live_source(name: str, config: RunConfig, scenario_dir: Path | None = None):
    if name == "inventory":
        return OCIInventorySource(config)
    if name == "telemetry":
        return OCITelemetrySource(config)
    if name in FILE_BACKED:
        if scenario_dir is None:
            raise SourceError(
                "a live run still needs a scenario directory: the IaC declarations and the "
                "policy catalog are files (--scenario data/scenarios/lab_live)")
        return FILE_BACKED[name](scenario_dir)
    raise KeyError(name)
