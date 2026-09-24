# tests/test_evidence.py
import pytest
from app.evidence import EvidenceLedger, DanglingEvidenceError


def test_ids_are_sequential_and_stable():
    ledger = EvidenceLedger()
    first = ledger.add(source="telemetry", kind="cpu_stats", resource_id="r1",
                       summary="mean 0.8%", payload={"mean": 0.8})
    second = ledger.add(source="policy", kind="rule_hit", resource_id="r1",
                        summary="rule R-3", payload={"rule_id": "R-3"})
    assert first.evidence_id == "E-001"
    assert second.evidence_id == "E-002"
    assert ledger.resolve(["E-001"])[0].payload == {"mean": 0.8}


def test_dangling_ref_is_an_error_not_a_silent_skip():
    ledger = EvidenceLedger()
    ledger.add(source="telemetry", kind="cpu_stats", resource_id="r1", summary="x", payload={})
    with pytest.raises(DanglingEvidenceError):
        ledger.resolve(["E-001", "E-999"])
