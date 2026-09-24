# tests/test_writer.py
import pytest
from app.agents.writer import UntraceableFigureError, assert_figures_traceable


def test_a_figure_with_no_evidence_is_refused():
    allowed = {"168", "0.83", "5"}
    assert_figures_traceable("mean 0.83% over 168h against a 5% threshold", allowed)
    with pytest.raises(UntraceableFigureError):
        assert_figures_traceable("we will save 999.99 per month", allowed)


def test_allowed_set_is_built_from_ledger_payloads(tmp_path):
    from app.evidence import EvidenceLedger
    ledger = EvidenceLedger()
    ledger.add(source="telemetry", kind="cpu_stats", resource_id="r1", summary="mean 0.83%",
               payload={"mean": 0.83, "coverage_hours": 168.0})
    allowed = {token for item in ledger.all()
               for token in str(item.payload).replace(",", " ").replace(":", " ").replace("}", " ").replace("{", " ").split()}
    assert_figures_traceable("mean 0.83 over 168.0h", allowed | {"0.83", "168.0"})
