# tests/test_analysis.py
from datetime import datetime, timezone
from pathlib import Path
import json
import pytest
from app.analysis import (match_iac, monthly_cost, qualifying_rules, stats_from_series)
from app.config import RunConfig
from app.models import IaCDeclaration, MetricSeries, PolicyRule, Resource
from app.sources import get_source
from app.sources.base import Scope

SCEN = Path("data/scenarios/example_1")
PRICING = json.loads(Path("data/pricing.json").read_text())


def resource(**kw):
    base = dict(resource_id="r1", resource_class="compute_instance", display_name="batch-01",
                compartment_id="c1", lifecycle_state="RUNNING",
                time_created=datetime(2026, 8, 14, tzinfo=timezone.utc), tags={})
    return Resource(**{**base, **kw})


def series(index):
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    src = get_source("telemetry", cfg, scenario_dir=SCEN)
    return MetricSeries(**src.fetch(Scope(compartment_ids=[], resource_types=[],
                                          lookback_hours=168, resolution_minutes=60)).records[index])


def test_stats_expose_mean_peak_and_coverage():
    stats = stats_from_series(series(1))          # batch-01, 7-day window
    assert stats["mean"] < 5.0
    assert stats["peak"] < 20.0
    assert stats["coverage_ratio"] >= 0.99
    assert stats["sufficient"] is True


def test_monthly_cost_uses_shape_rates():
    assert monthly_cost(resource(shape="VM.Standard.E4.Flex", ocpus=4, memory_gb=16), PRICING) == 90.52
    assert monthly_cost(resource(resource_class="block_volume", size_gb=50), PRICING) == pytest.approx(
        50 * PRICING["block_volume_gb_month"], abs=0.01)
    assert monthly_cost(resource(resource_class="reserved_public_ip"), PRICING) == pytest.approx(7.30)
    with pytest.raises(KeyError):
        monthly_cost(resource(shape="VM.Does.Not.Exist", ocpus=1, memory_gb=1), PRICING)


def test_iac_match_prefers_the_declared_tag_then_name_then_normalised():
    tag_match = IaCDeclaration(address="oci_core_instance.batch_01", resource_type="oci_core_instance",
                               declared_name="batch-01", file_path="terraform/batch.tf",
                               last_commit="d4e5f6a", commit_message="month-end batch worker", author="me")
    r = resource(tags={"iac_address": "oci_core_instance.batch_01"})
    assert match_iac(r, [tag_match]) == ("tag", tag_match)
    assert match_iac(resource(display_name="batch-01"), [tag_match])[0] == "name"
    assert match_iac(resource(display_name="BATCH 01"), [tag_match])[0] == "normalised"
    assert match_iac(resource(display_name="sandbox-tmp"), [tag_match]) == (None, None)


def test_short_coverage_disqualifies_every_cost_rule():
    sandbox = series(3)
    stats = stats_from_series(sandbox)
    rules = [PolicyRule(**r) for r in json.loads((SCEN / "policy.json").read_text())["rules"]]
    assert stats["coverage_ratio"] < 0.8
    fired = qualifying_rules(resource(display_name="sandbox-tmp"), stats, None, True, rules)
    # R-5 is an unattributed rule and deliberately needs no metric window; every rule that
    # depends on statistics is disqualified.
    assert [r.rule_id for r in fired if r.finding_class == "cost_waste"] == []
    assert [r.rule_id for r in fired] == ["R-5"]


def test_window_width_changes_which_rule_fires():
    rules = [PolicyRule(**r) for r in json.loads((SCEN / "policy.json").read_text())["rules"]]
    narrow = qualifying_rules(resource(), stats_from_series(series(1)), None, False, rules)
    assert [r.rule_id for r in narrow] == ["R-3"]

    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    wide_records = get_source("telemetry", cfg, scenario_dir=SCEN).fetch(
        Scope(compartment_ids=[], resource_types=[], lookback_hours=744, resolution_minutes=60)).records
    wide = qualifying_rules(resource(), stats_from_series(MetricSeries(**wide_records[1])), None, False, rules)
    assert [r.rule_id for r in wide] == ["R-4"]


def test_unattributed_rule_needs_no_telemetry():
    rules = [PolicyRule(**r) for r in json.loads((SCEN / "policy.json").read_text())["rules"]]
    stats = stats_from_series(series(3))          # insufficient coverage
    fired = qualifying_rules(resource(display_name="sandbox-tmp"), stats, None, True, rules)
    assert [r.rule_id for r in fired] == ["R-5"]
