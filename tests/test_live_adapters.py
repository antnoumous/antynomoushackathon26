# tests/test_live_adapters.py
"""The live OCI adapters, tested without a tenancy.

Every test here runs offline and credential-free: the SDK config file is pointed at a path that
does not exist, and the mapping logic is exercised against stub objects shaped like the SDK's.
The one thing these tests cannot prove is that a real tenancy answers — that is Task 15 Step 5,
gated on the lab tenancy existing (docs/lab-tenancy.md).

The plan's Task 15 Step 1 also asked for a mask_ocids test here; `tests/test_mask_ocids.py`
already tests the tool and scans every tracked file, so it is not duplicated.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import RunConfig
from app.sources import get_source
from app.sources.base import Scope, SourceError

SCEN = Path("data/scenarios/example_1")


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch, tmp_path):
    """No test may reach a real tenancy, even on a machine that has one configured."""
    monkeypatch.setenv("OCI_CONFIG_FILE", str(tmp_path / "does-not-exist"))
    monkeypatch.setenv("OCI_PROFILE", "DEFAULT")
    monkeypatch.delenv("OCI_COMPARTMENT_ID", raising=False)


def live_cfg(**scope):
    return RunConfig.from_env_and_request({"sample_mode": False, "scope": scope})


def scope_for(cfg, lookback_hours=168, resolution_minutes=5):
    return Scope(compartment_ids=cfg.compartment_ids, resource_types=cfg.resource_types,
                 lookback_hours=lookback_hours, resolution_minutes=resolution_minutes)


# --- construction and loud failure ----------------------------------------------------------

def test_live_sources_construct_without_credentials_and_fail_loudly_when_used(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..••••lab")
    cfg = live_cfg()
    for name in ("inventory", "telemetry", "iac", "policy"):
        source = get_source(name, cfg, scenario_dir=SCEN)
        assert source.name == name
    with pytest.raises(SourceError, match="credentials"):
        get_source("telemetry", cfg, scenario_dir=SCEN).fetch(scope_for(cfg))
    with pytest.raises(SourceError, match="credentials"):
        get_source("inventory", cfg, scenario_dir=SCEN).fetch(scope_for(cfg))


def test_a_live_run_with_no_compartment_anywhere_says_what_is_missing(monkeypatch):
    """No scope, no config, no env: the error names the variable instead of guessing."""
    cfg = live_cfg()
    with pytest.raises(SourceError, match="OCI_COMPARTMENT_ID"):
        get_source("inventory", cfg, scenario_dir=SCEN).fetch(scope_for(cfg))


def test_live_policy_and_iac_come_from_the_scenario_dir():
    """The IaC repo and the policy catalog are files, not OCI services: same adapter, both modes,
    and a live run pointed at the lab scenario reads the lab's declarations."""
    cfg = live_cfg()
    rules = get_source("policy", cfg, scenario_dir=SCEN).fetch(scope_for(cfg)).records
    assert {r["rule_id"] for r in rules} == {"R-1", "R-2", "R-3", "R-4", "R-5"}
    declarations = get_source("iac", cfg, scenario_dir=SCEN).fetch(scope_for(cfg)).records
    assert {d["address"] for d in declarations} == {
        "oci_core_instance.web_01", "oci_core_instance.batch_01", "oci_core_instance.reports_01"}


# --- inventory mapping -----------------------------------------------------------------------

def test_instance_record_maps_the_sdk_shape():
    from app.sources.oci_inventory import instance_record
    instance = SimpleNamespace(
        id="ocid1.instance.oc1..••••aaa1", display_name="lab-web-01",
        compartment_id="ocid1.compartment.oc1..••••lab", lifecycle_state="RUNNING",
        time_created=datetime(2026, 9, 20, tzinfo=timezone.utc), shape="VM.Standard.A1.Flex",
        shape_config=SimpleNamespace(ocpus=1.0, memory_in_gbs=6.0),
        freeform_tags={"owner": "ant", "schedule": "month-end"})
    record = instance_record(instance)
    assert record["resource_class"] == "compute_instance"
    assert record["ocpus"] == 1.0 and record["memory_gb"] == 6.0
    assert record["tags"] == {"owner": "ant", "schedule": "month-end"}
    assert record["time_created"] == "2026-09-20T00:00:00+00:00"
    from app.models import Resource
    assert Resource(**record).display_name == "lab-web-01"     # hydrates without coercion errors


def test_volume_attached_flag_comes_from_the_attachments_not_the_volume():
    from app.sources.oci_inventory import volume_record
    volume = SimpleNamespace(
        id="ocid1.volume.oc1..••••vol1", display_name="vol-orphan-50g",
        compartment_id="ocid1.compartment.oc1..••••lab", lifecycle_state="AVAILABLE",
        time_created=datetime(2026, 9, 20, tzinfo=timezone.utc), size_in_gbs=50,
        freeform_tags={})
    orphan = volume_record(volume, attached_ids=set())
    assert orphan["attached"] is False and orphan["size_gb"] == 50
    in_use = volume_record(volume, attached_ids={"ocid1.volume.oc1..••••vol1"})
    assert in_use["attached"] is True
    from app.models import Resource
    assert Resource(**orphan).resource_class == "block_volume"


def test_reserved_ip_is_attached_only_when_assigned():
    from app.sources.oci_inventory import public_ip_record
    ip = SimpleNamespace(
        id="ocid1.publicip.oc1..••••ip01", display_name="ip-orphan",
        compartment_id="ocid1.compartment.oc1..••••lab", lifecycle_state="AVAILABLE",
        time_created=datetime(2026, 9, 20, tzinfo=timezone.utc),
        assigned_entity_id=None, freeform_tags={})
    record = public_ip_record(ip)
    assert record["attached"] is False
    ip.assigned_entity_id = "ocid1.privateip.oc1..••••pip1"
    assert public_ip_record(ip)["attached"] is True


# --- telemetry mapping -------------------------------------------------------------------------

def _metric_data(resource_id, points):
    return SimpleNamespace(
        namespace="oci_computeagent", name="CpuUtilization",
        dimensions={"resourceId": resource_id},
        aggregated_datapoints=[SimpleNamespace(timestamp=ts, value=v) for ts, v in points])


def test_telemetry_coverage_uses_the_same_rule_as_the_fixture():
    from app.sources.oci_telemetry import series_records
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    hourly = [(now - timedelta(hours=h), 1.0) for h in range(168, 0, -1)]
    full = series_records([_metric_data("ocid1.instance.oc1..••••aaa1", hourly)],
                          lookback_hours=168, resolution_minutes=60, now=now)
    assert full[0]["sufficient"] is True and full[0]["coverage_hours"] >= 166

    short = hourly[-41:]                                   # a resource that only exists 41 h
    young = series_records([_metric_data("ocid1.instance.oc1..••••ddd4", short)],
                           lookback_hours=168, resolution_minutes=60, now=now)
    assert young[0]["sufficient"] is False
    assert "40h of 168h" in young[0]["insufficient_reason"]

    from app.models import MetricSeries
    assert MetricSeries(**full[0]).points[-1].value == 1.0


def test_a_resource_the_service_never_answers_for_has_no_record():
    """No stream means no record — the Scout's NO_TELEMETRY_STATS path, not a fabricated zero."""
    from app.sources.oci_telemetry import series_records
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert series_records([], lookback_hours=168, resolution_minutes=60, now=now) == []


def test_recheck_windows_widen_the_resolution_past_the_retention_edge():
    """5-minute-resolution data is kept 30 days; a 744 h re-check at 5 m would ask for data that
    no longer exists. Beyond 720 h the adapter requests hourly — the same resolution the fixture
    series use — so the widened window is one the service can actually answer."""
    from app.sources.oci_telemetry import resolution_for
    assert resolution_for(168, 5) == 5
    assert resolution_for(720, 5) == 5
    assert resolution_for(744, 5) == 60
