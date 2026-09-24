# tests/test_writer.py
import io
from pathlib import Path

import pytest
from app.agents.base import AgentContext
from app.agents.writer import UntraceableFigureError, Writer, assert_figures_traceable
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.loop import Orchestrator
from app.models import Candidate, Ruling
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer

SCEN = Path("data/scenarios/example_1")


def _ctx(tmp_path, generator=None) -> AgentContext:
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac", "policy")}
    return AgentContext(config=cfg, sources=sources, generator=generator or RulesGenerator(),
                        state=RunState(cfg.run_id, tmp_path),
                        trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                        ledger=EvidenceLedger(), scope=scope)


class LyingNarrative(RulesGenerator):
    """The shape a bad model produces: a confident sentence with a money figure nobody measured."""

    def complete(self, *, prompt, schema, context):
        if schema.get("name") == "run_summary":
            return {"summary": "This tenancy wastes 41,998.37 USD per month across 999 servers.",
                    "confidence": 1.0}
        return super().complete(prompt=prompt, schema=schema, context=context)


class LyingReason(RulesGenerator):
    def complete(self, *, prompt, schema, context):
        if schema.get("name") == "verdict_reason":
            return {"reason": "withdrawn: 12,345.67 USD of unverified noise", "confidence": 0.8}
        return super().complete(prompt=prompt, schema=schema, context=context)


def test_a_figure_with_no_evidence_is_refused():
    allowed = {"168", "0.83", "5"}
    assert_figures_traceable("mean 0.83% over 168h against a 5% threshold", allowed)
    with pytest.raises(UntraceableFigureError):
        assert_figures_traceable("we will save 999.99 per month", allowed)


def test_a_money_figure_is_never_allowed_because_the_number_is_a_cap_value():
    """300 is the soft wall clock; that must not make "300 USD" publishable."""
    assert_figures_traceable("the soft budget is 300 seconds and the cap is 25 resources", set())
    with pytest.raises(UntraceableFigureError):
        assert_figures_traceable("this instance wastes 300 USD every month", set())
    with pytest.raises(UntraceableFigureError):
        assert_figures_traceable("about $300 is recoverable", set())


def test_allowed_set_is_built_from_ledger_payloads(tmp_path):
    from app.evidence import EvidenceLedger
    ledger = EvidenceLedger()
    ledger.add(source="telemetry", kind="cpu_stats", resource_id="r1", summary="mean 0.83%",
               payload={"mean": 0.83, "coverage_hours": 168.0})
    allowed = {token for item in ledger.all()
               for token in str(item.payload).replace(",", " ").replace(":", " ").replace("}", " ").replace("{", " ").split()}
    assert_figures_traceable("mean 0.83 over 168.0h", allowed | {"0.83", "168.0"})


def test_a_claim_cannot_vouch_for_its_own_numbers(tmp_path):
    """The numbers in `candidate.stats` are only allowed if the evidence carries them too."""
    ctx = _ctx(tmp_path)
    candidate = Candidate(
        candidate_id="C-900", resource_id="ocid1.instance.oc1..nope",
        resource_class="compute_instance", **{"class": "cost_waste"},
        claim="the instance averages 7.777% CPU", evidence_refs=[],
        impact={"kind": "usd_per_month", "value": 1.0}, confidence=0.5,
        falsifier="a declared purpose would withdraw this finding",
        stats={"mean": 7.777, "peak": 9.9, "coverage_ratio": 1.0, "sufficient": True})
    ruling = Ruling(candidate_id="C-900", verdict="accept", reason="ok", round=1)
    with pytest.raises(UntraceableFigureError):
        Writer(ctx).synthesise(candidates=[candidate], rulings={"C-900": ruling}, undetermined=[],
                               sources=[], status="success", caps_hit=[])


def test_a_model_narrative_with_an_unsupported_figure_never_reaches_the_report(tmp_path):
    ctx = _ctx(tmp_path, generator=LyingNarrative())
    with pytest.raises(UntraceableFigureError):
        Orchestrator(ctx, scenario_dir=SCEN).run()


def test_a_model_verdict_reason_with_an_unsupported_figure_never_reaches_the_report(tmp_path):
    ctx = _ctx(tmp_path, generator=LyingReason())
    with pytest.raises(UntraceableFigureError):
        Orchestrator(ctx, scenario_dir=SCEN).run()
