# tests/test_loop.py
import io, json, socket
from pathlib import Path
import pytest
from app.agents.base import AgentContext
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.loop import Orchestrator
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer

SCEN = Path("data/scenarios/example_1")


def build(tmp_path, **request):
    cfg = RunConfig.from_env_and_request({"sample_mode": True, **request})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac", "policy")}
    ctx = AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                       state=RunState(cfg.run_id, tmp_path),
                       trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                       ledger=EvidenceLedger(), scope=scope)
    return cfg, ctx


def actions(ctx):
    return [json.loads(line)["action"] for line in ctx.trace.path.read_text().splitlines()]


def agents(ctx):
    return {json.loads(line)["agent_name"] for line in ctx.trace.path.read_text().splitlines()}


def test_canonical_run_rejects_the_idle_claim_and_revises_it(tmp_path):
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()

    batch = [f for f in report.findings if f.resource_id.endswith("bbb2")]
    assert [f.status for f in batch] == ["rejected", "revised"]
    rejected, revised = batch
    assert revised.claim != rejected.claim      # the conclusion actually changed
    assert "peaks at" in revised.claim          # and cites the burst that forced the change
    assert report.status == "success"
    assert report.mode == "sample"
    assert report.caps_hit == []


def test_report_finds_both_orphans_and_the_unattributed_instance(tmp_path):
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()
    classes = {(f.resource_id[-4:], f.finding_class) for f in report.findings
               if f.status in {"accepted", "revised"}}
    assert ("eee5", "cost_waste") in classes        # detached block volume
    assert ("fff6", "cost_waste") in classes        # unattached reserved IP
    assert ("ddd4", "unattributed") in classes      # absent from every Terraform file
    assert report.summary["waste_found_usd_per_month"] > 0
    assert report.summary["findings_rejected"] == 1
    assert report.summary["unattributed_ratio"] > 0


def test_insufficient_telemetry_lands_in_undetermined(tmp_path):
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()
    reasons = {u.resource_id[-4:]: u.reason for u in report.undetermined}
    assert "ddd4" in reasons
    assert "41h of 168h" in reasons["ddd4"]


def test_the_trace_shows_at_least_two_agents_handing_off_and_a_recheck(tmp_path):
    cfg, ctx = build(tmp_path)
    Orchestrator(ctx).run()
    assert {"Planner", "Scout", "Skeptic", "Writer"} <= agents(ctx)
    assert "request_recheck" in actions(ctx)
    assert "validate_finding" in actions(ctx)
    handoffs = [json.loads(l)["target_agent"] for l in ctx.trace.path.read_text().splitlines()]
    assert "Scout" in handoffs and "Skeptic" in handoffs and "Writer" in handoffs


def test_sample_mode_makes_no_network_calls(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("sample mode attempted a network call")
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(socket, "create_connection", explode)
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()
    assert report.status == "success"


def test_max_rounds_is_enforced_and_logged_as_capped(tmp_path):
    cfg, ctx = build(tmp_path, caps={"max_rounds": 1})
    report = Orchestrator(ctx).run()
    assert "max_rounds" in report.caps_hit
    assert report.status == "capped"


def test_an_unavailable_source_degrades_and_is_named_in_the_report(tmp_path):
    cfg, ctx = build(tmp_path)

    class Broken:
        name = "policy"

        def fetch(self, scope):
            raise RuntimeError("simulated outage")

    ctx.sources["policy"] = Broken()
    report = Orchestrator(ctx, scenario_dir=SCEN).run()
    policy = next(s for s in report.sources if s.name == "policy")
    assert policy.degraded is True
    assert "outage" in (policy.reason or "")


def test_no_policy_rules_yields_partial_and_an_explanation(tmp_path):
    cfg, ctx = build(tmp_path)

    class EmptyPolicy:
        name = "policy"

        def fetch(self, scope):
            from app.sources.base import SourceResult
            return SourceResult(source="policy", backend="fixture", records=[])

    ctx.sources["policy"] = EmptyPolicy()
    report = Orchestrator(ctx).run()
    assert report.status == "partial"
    assert report.findings == []
    assert any(u.resource_id == "scope" for u in report.undetermined)


class Clock:
    """A monotonic clock that reads 0 at construction and a fixed elapsed time after that."""

    def __init__(self, elapsed: float):
        self.elapsed = elapsed
        self.calls = 0

    def monotonic(self) -> float:
        self.calls += 1
        return 0.0 if self.calls == 1 else self.elapsed


def test_the_soft_wall_clock_is_logged_as_a_cap_but_does_not_stop_the_run(tmp_path, monkeypatch):
    monkeypatch.setattr("app.loop.time", Clock(elapsed=310))
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()

    assert "wall_clock_soft_s" in report.caps_hit
    assert report.status == "capped"          # a slow run never reads as a clean one
    assert report.findings                    # but the investigation finished anyway
    capped = [json.loads(l) for l in ctx.trace.path.read_text().splitlines()
              if json.loads(l)["status"] == "capped"]
    assert capped and capped[0]["action"] == "cap_hit"
    assert "wall clock" in capped[0]["input_summary"]


def test_the_hard_wall_clock_stops_the_run_rather_than_letting_it_hang(tmp_path, monkeypatch):
    monkeypatch.setattr("app.loop.time", Clock(elapsed=600))
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()

    assert report.caps_hit == ["wall_clock_hard_s"]     # hard wins; the soft check never runs
    assert report.status == "capped"
    assert report.findings                              # what round 1 found is still reported
    assert "request_recheck" in actions(ctx)            # the recheck was requested...

    # ...and never honoured, so the un-concluded claim must not be presented as a finding.
    assert [f for f in report.findings if f.resource_id.endswith("bbb2")] == []
    unresolved = [u for u in report.undetermined if u.resource_id.endswith("bbb2")]
    assert unresolved and "the re-check the Skeptic asked for did not run" in unresolved[0].reason
    assert "not_concluded" in actions(ctx)
