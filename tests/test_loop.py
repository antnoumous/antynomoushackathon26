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


def build(tmp_path, scenario=SCEN, **request):
    cfg = RunConfig.from_env_and_request({"sample_mode": True, **request})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=scenario)
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
    """A monotonic clock driven by a script, so wall-clock behaviour is testable.

    Call 1 is the orchestrator's start; each resource the Scout is about to examine costs one call,
    and each round boundary costs one. The last value repeats.
    """

    def __init__(self, schedule: list[float]):
        self.schedule = schedule
        self.calls = 0

    def monotonic(self) -> float:
        value = self.schedule[min(self.calls, len(self.schedule) - 1)]
        self.calls += 1
        return value


def test_the_soft_wall_clock_is_logged_as_a_cap_but_does_not_stop_the_run(tmp_path, monkeypatch):
    monkeypatch.setattr("app.loop.time", Clock([0.0, 310]))
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()

    assert "wall_clock_soft_s" in report.caps_hit
    assert report.status == "capped"          # a slow run never reads as a clean one
    assert report.findings                    # but the investigation finished anyway
    capped = [json.loads(line) for line in ctx.trace.path.read_text().splitlines()
              if json.loads(line)["status"] == "capped"]
    assert capped and capped[0]["action"] == "cap_hit"
    assert "wall clock" in capped[0]["input_summary"]


def test_the_hard_wall_clock_stops_the_run_rather_than_letting_it_hang(tmp_path, monkeypatch):
    # A full round runs, then the budget is gone: the loop must stop instead of starting another.
    monkeypatch.setattr("app.loop.time", Clock([0.0] * 8 + [600]))
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()

    assert report.caps_hit == ["wall_clock_hard_s"]     # hard wins; the soft check never runs
    assert report.status == "capped"
    assert report.findings                              # what round 1 found is still reported
    assert "request_recheck" in actions(ctx)            # the recheck was requested...

    # ...and never honoured, so the un-concluded claim must not be presented as a finding.
    assert [f for f in report.findings if f.resource_id.endswith("bbb2")] == []
    unresolved = [u for u in report.undetermined if u.resource_id.endswith("bbb2")]
    assert unresolved
    assert any("the re-check the Skeptic asked for did not run" in u.reason for u in unresolved)
    assert "not_concluded" in actions(ctx)


def test_the_budget_is_checked_before_each_resource_not_only_between_rounds(tmp_path, monkeypatch):
    # The budget expires mid-round, after two resources: the rest are named, never silently dropped.
    monkeypatch.setattr("app.loop.time", Clock([0.0, 0.0, 0.0, 700]))
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()

    unexamined = [u for u in report.undetermined if "wall-clock budget was exhausted" in u.reason]
    assert unexamined, "resources skipped for time must be named in the report"
    assert report.summary["resources_examined"] < report.summary["resources_in_scope"]
    assert "wall_clock_hard_s" in report.caps_hit
    assert report.status == "capped"


def test_no_telemetry_means_no_cpu_finding_rather_than_a_zero(tmp_path):
    """The worst failure this project can have: publishing a CPU number nobody measured."""
    cfg, ctx = build(tmp_path)

    class Broken:
        name = "telemetry"

        def fetch(self, scope):
            raise RuntimeError("monitoring API unavailable")

    ctx.sources["telemetry"] = Broken()
    report = Orchestrator(ctx).run()

    assert not [f for f in report.findings if "averages" in f.claim]
    reasons = [u.reason for u in report.undetermined]
    assert any("no telemetry was retrieved" in reason for reason in reasons)
    # A verdict that rests on the resource's shape needs no telemetry: it still stands.
    assert [f for f in report.findings if f.finding_class == "unattributed"]
    assert [f for f in report.findings if f.resource_class == "block_volume"]
    assert report.status == "partial"


def test_a_corrupt_fixture_degrades_the_source_instead_of_crashing_the_run(tmp_path):
    """Truncated JSON is the realistic corruption: a half-written file, not a missing one."""
    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    (corrupt / "inventory.json").write_text('{"scenario_id": "corrupt", "resources": [')
    for name in ("telemetry.json", "iac.json", "policy.json"):
        (corrupt / name).write_text((SCEN / name).read_text())

    cfg, ctx = build(tmp_path, scenario=corrupt)
    report = Orchestrator(ctx, scenario_dir=corrupt).run()

    assert report.status == "partial"
    assert [s for s in report.sources if s.name == "inventory" and s.degraded]
    assert report.findings == []


def test_more_resources_than_the_cap_are_reported_not_hidden(tmp_path):
    wide = tmp_path / "wide"
    wide.mkdir()
    resources, series = [], []
    for index in range(30):
        resource_id = f"ocid1.instance.oc1..v{index:04d}"
        resources.append({
            "resource_id": resource_id, "resource_class": "compute_instance",
            "display_name": f"wide-{index:02d}",
            "compartment_id": "ocid1.compartment.oc1..lab", "lifecycle_state": "RUNNING",
            "time_created": "2026-08-01T00:00:00Z", "shape": "VM.Standard.E4.Flex",
            "ocpus": 2, "memory_gb": 8, "tags": {}})
        series.append({"resource_id": resource_id, "metric": "CpuUtilization",
                       "start": "2026-08-24T00:00:00Z", "baseline": 0.4, "jitter": 0.1,
                       "bursts": []})
    (wide / "inventory.json").write_text(json.dumps({"scenario_id": "wide",
                                                     "resources": resources}))
    (wide / "telemetry.json").write_text(json.dumps({"scenario_id": "wide",
                                                     "now": "2026-09-23T04:00:00Z",
                                                     "series": series}))
    (wide / "iac.json").write_text(json.dumps({"scenario_id": "wide", "declarations": []}))
    (wide / "policy.json").write_text((SCEN / "policy.json").read_text())

    cfg, ctx = build(tmp_path, scenario=wide)
    report = Orchestrator(ctx, scenario_dir=wide).run()

    assert "max_resources" in report.caps_hit
    assert report.status == "capped"
    assert report.summary["resources_in_scope"] == 30
    assert report.summary["resources_examined"] == 25     # not 30: the report cannot overstate
    assert "cap_hit" in actions(ctx)
    # The narrative is the line a human reads first, so it must not quote the tenancy size either.
    assert "Audited 25 resources" in report.summary["narrative"]
    assert "30" not in report.summary["narrative"]


def test_a_broken_fixture_degrades_the_source_instead_of_crashing_the_run(tmp_path):
    cfg, ctx = build(tmp_path, scenario=tmp_path / "does-not-exist")
    report = Orchestrator(ctx, scenario_dir=tmp_path / "does-not-exist").run()

    assert report.status == "partial"
    assert report.findings == []
    assert all(source.degraded for source in report.sources)
    assert any(u.resource_id == "scope" for u in report.undetermined)


def test_a_re_check_that_changes_nothing_is_a_duplicate_not_a_revision(tmp_path):
    """Found by held-out seed 6, which no committed scenario covers.

    An idle, bursty, *undeclared* instance gets re-investigated for its cost verdict, and the Scout
    — working per resource, not per class — re-derives its `unattributed` finding too, identically.
    Superseding that untouched finding marked it `rejected` and the repeat `revised`: a change of
    mind the agent never had, which is exactly the kind of claim this report is supposed to make
    visible rather than invent.
    """
    scenario = tmp_path / "duplicate"
    scenario.mkdir()
    resource = {"resource_id": "ocid1.instance.oc1..\u2022\u2022\u2022\u2022dup1",
                "resource_class": "compute_instance", "display_name": "worker-01",
                "compartment_id": "ocid1.compartment.oc1..\u2022\u2022\u2022\u2022labtest",
                "lifecycle_state": "RUNNING",
                "time_created": "2026-08-01T00:00:00Z", "shape": "VM.Standard.E4.Flex",
                "ocpus": 2, "memory_gb": 8, "tags": {"schedule": "month-end"}}
    # now = 2026-10-05. The burst sits 20 days back, so it is outside the 7-day window the run asks
    # for and inside the 31-day window the Skeptic widens to: R-3 fires first, R-4 after the
    # re-check. That is the only arrangement in which `revised` is the true answer.
    series = {"resource_id": resource["resource_id"], "metric": "CpuUtilization",
              "start": "2026-08-21T00:00:00Z", "baseline": 0.6, "jitter": 0.4,
              "bursts": [{"start": "2026-09-15T02:00:00Z", "hours": 3, "value": 58.0}]}
    (scenario / "inventory.json").write_text(json.dumps(
        {"scenario_id": "duplicate", "resources": [resource]}))
    (scenario / "telemetry.json").write_text(json.dumps(
        {"scenario_id": "duplicate", "now": "2026-10-05T00:00:00Z", "series": [series]}))
    (scenario / "iac.json").write_text(json.dumps({"scenario_id": "duplicate", "declarations": []}))
    (scenario / "policy.json").write_text((SCEN / "policy.json").read_text())

    cfg, ctx = build(tmp_path, scenario=scenario)
    report = Orchestrator(ctx, scenario_dir=scenario).run()

    by_class = {finding.finding_class: finding for finding in report.findings}
    assert by_class["cost_waste"].status == "revised"          # R-3, then R-4: a real revision
    assert by_class["unattributed"].status == "accepted"       # untouched: not a revision
    assert len([f for f in report.findings if f.finding_class == "unattributed"]) == 1
    assert "drop_duplicate_finding" in actions(ctx)
    assert all(f.status != "revised" for f in report.findings
               if f.finding_class == "unattributed")
