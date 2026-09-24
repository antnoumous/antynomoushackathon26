# tests/test_sources.py
from pathlib import Path
import pytest
from app.config import RunConfig
from app.models import MetricSeries, Resource
from app.sources import get_source
from app.sources.base import Scope

SCEN = Path("data/scenarios/example_1")


def scope(cfg):
    return Scope(compartment_ids=cfg.compartment_ids, resource_types=cfg.resource_types,
                 lookback_hours=cfg.lookback_hours, resolution_minutes=cfg.resolution_minutes)


def fixture_cfg():
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    return cfg


def test_inventory_returns_six_typed_resources():
    src = get_source("inventory", fixture_cfg(), scenario_dir=SCEN)
    result = src.fetch(scope(fixture_cfg()))
    assert result.backend == "fixture"
    assert len(result.records) == 6
    assert all(Resource(**r) for r in result.records)


def test_telemetry_marks_short_coverage_insufficient():
    src = get_source("telemetry", fixture_cfg(), scenario_dir=SCEN)
    series = [MetricSeries(**s) for s in src.fetch(scope(fixture_cfg())).records]
    sandbox = next(s for s in series if s.resource_id.endswith("ddd4"))
    assert sandbox.sufficient is False
    assert "41h of 168h" in (sandbox.insufficient_reason or "")
    assert all(s.sufficient for s in series if not s.resource_id.endswith("ddd4"))


def test_telemetry_points_are_reproducible_and_window_sensitive():
    cfg = fixture_cfg()
    src = get_source("telemetry", cfg, scenario_dir=SCEN)
    first = src.fetch(scope(cfg)).records[1]     # batch-01
    second = src.fetch(scope(cfg)).records[1]
    assert first["points"] == second["points"]   # deterministic between calls and processes

    wide = Scope(compartment_ids=[], resource_types=[], lookback_hours=744, resolution_minutes=60)
    wide_points = src.fetch(wide).records[1]["points"]
    assert max(p["value"] for p in wide_points) >= 20.0    # burst is inside the 31-day window
    assert max(p["value"] for p in first["points"]) < 20.0  # and outside the 7-day window
    assert wide_points != first["points"]


def test_iac_excludes_the_unmanaged_instance():
    src = get_source("iac", fixture_cfg(), scenario_dir=SCEN)
    addresses = {r["address"] for r in src.fetch(scope(fixture_cfg())).records}
    assert "oci_core_instance.sandbox_tmp" not in addresses
    assert len(addresses) == 3


def test_policy_loads_all_five_rules():
    src = get_source("policy", fixture_cfg(), scenario_dir=SCEN)
    assert {r["rule_id"] for r in src.fetch(scope(fixture_cfg())).records} == {"R-1", "R-2", "R-3", "R-4", "R-5"}


def test_unknown_source_name_is_an_error():
    with pytest.raises(KeyError):
        get_source("nonexistent", fixture_cfg(), scenario_dir=SCEN)
