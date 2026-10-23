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


def test_sample_mode_forces_file_even_with_zetaris_selection_and_bad_sponsor_env(monkeypatch):
    """Selection and sponsor env are read AFTER sample resolution; malformed sponsor
    variables must never pull a sample run onto a network path."""
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("DRIFTWATCH_POLICY_SOURCE", "zetaris")
    monkeypatch.setenv("ZETARIS_REST_URL", "https://not:valid:8888/@@@")
    monkeypatch.setenv("ZETARIS_API_KEY", "")
    monkeypatch.setenv("ZETARIS_ORG_ID", "not-a-number")
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    assert cfg.policy_source == "file"
    from app.sources.policy_fixture import PolicyFixtureSource

    src = get_source("policy", cfg, scenario_dir=SCEN)
    assert isinstance(src, PolicyFixtureSource)
    assert src.fetch(scope(cfg)).backend == "fixture"


def test_zetaris_named_objects_never_imported_by_default(monkeypatch):
    """With selection unset or file, live mode uses the file-backed policy and the
    sponsor modules are not required; iac still needs its scenario directory."""
    monkeypatch.delenv("DRIFTWATCH_POLICY_SOURCE", raising=False)
    monkeypatch.setenv("SAMPLE_MODE", "false")
    cfg = RunConfig.from_env_and_request({})
    assert cfg.policy_source == "file"
    assert cfg.sample_mode is False
    from app.sources.policy_fixture import PolicyFixtureSource

    src = get_source("policy", cfg, scenario_dir=SCEN)
    assert isinstance(src, PolicyFixtureSource)
    with pytest.raises(Exception):
        get_source("iac", cfg)  # unchanged behaviour: needs a scenario directory


def test_zetaris_optin_constructs_without_network(monkeypatch):
    import socket

    from app.sources.zetaris_policy import ZetarisPolicySource

    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("DRIFTWATCH_POLICY_SOURCE", "zetaris")
    monkeypatch.setenv("ZETARIS_REST_URL", "http://127.0.0.1:8888/api/v1.0")
    monkeypatch.setenv("ZETARIS_API_KEY", "test-only-token")
    monkeypatch.setenv("ZETARIS_ORG_ID", "6")
    monkeypatch.setenv("ZETARIS_POLICY_OBJECT", "DW.DW_POLICY_RULES")
    monkeypatch.setenv("ZETARIS_MANIFEST_OBJECT", "DW.DW_POLICY_MANIFEST")
    monkeypatch.setenv("ZETARIS_POLICY_SNAPSHOT", "example1_base_v1")
    monkeypatch.setenv("ZETARIS_POLICY_SHA256", "0" * 64)

    def no_sockets(*args, **kwargs):
        raise AssertionError("construction must not open sockets")

    monkeypatch.setattr(socket.socket, "__init__", no_sockets, raising=False)
    cfg = RunConfig.from_env_and_request({})
    src = get_source("policy", cfg)
    assert isinstance(src, ZetarisPolicySource)


def test_invalid_selection_fails_explicitly_not_silent_file(monkeypatch):
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("DRIFTWATCH_POLICY_SOURCE", "kafka")
    with pytest.raises(ValueError):
        RunConfig.from_env_and_request({})
