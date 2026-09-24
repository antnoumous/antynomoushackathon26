# tests/test_models.py
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.models import Finding, MetricSeries, Resource


def test_resource_rejects_unknown_class():
    with pytest.raises(ValidationError):
        Resource(resource_id="ocid1.instance.oc1..aaaa", resource_class="kubernetes_cluster",
                 display_name="x", compartment_id="c1", lifecycle_state="RUNNING",
                 time_created=datetime.now(timezone.utc), tags={})


def test_metric_series_reports_coverage():
    s = MetricSeries(resource_id="r1", metric="CpuUtilization", lookback_hours=168,
                     resolution_minutes=5, coverage_hours=168.0, sufficient=True,
                     points=[{"ts": datetime.now(timezone.utc), "value": 0.5}])
    assert s.coverage_hours == 168.0
    assert s.sufficient is True


def test_finding_serialises_class_alias():
    f = Finding(finding_id="F-001", resource_id="r1", resource_class="compute_instance",
                finding_class="cost_waste", claim="idle", evidence_refs=["E-001"],
                impact={"kind": "usd_per_month", "value": 8.94}, confidence=0.7,
                status="accepted", falsifier="a documented scheduled job", history=[])
    payload = f.model_dump(by_alias=True)
    assert payload["class"] == "cost_waste"
    assert "finding_class" not in payload


def test_finding_rejects_unknown_status():
    with pytest.raises(ValidationError):
        Finding(finding_id="F-001", resource_id="r1", resource_class="compute_instance",
                finding_class="cost_waste", claim="idle", evidence_refs=[], impact={},
                confidence=0.7, status="maybe", falsifier="", history=[])
