# tests/test_skeptic.py
import pytest
from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.agents.scout import Scout
from app.agents.skeptic import Skeptic
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer
import io
from pathlib import Path

SCEN = Path("data/scenarios/example_1")


@pytest.fixture
def ctx(tmp_path):
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac", "policy")}
    c = AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                     state=RunState(cfg.run_id, tmp_path),
                     trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                     ledger=EvidenceLedger(), scope=scope)
    scout = Scout(c)
    scout.hydrate()
    c.extras["scout"] = scout
    return c


def candidates(ctx, lookback=168):
    scout: Scout = ctx.extras["scout"]
    assignment = Planner(ctx).assign(
        round=1, resources=list(ctx.state.facts["resources"].values()), recheck_requests=[])
    assignment = assignment.model_copy(update={"lookback_hours": lookback})
    return scout.investigate(assignment)


def test_skeptic_demands_a_wider_window_when_a_schedule_signal_exists(ctx):
    batch = next(c for c in candidates(ctx) if c.resource_id.endswith("bbb2"))
    ruling = Skeptic(ctx).judge(batch, round=1)
    assert ruling.verdict == "recheck"
    assert ruling.request["lookback_hours"] == 744
    assert "month-end" in ruling.reason or "cadence" in ruling.reason


def test_skeptic_accepts_the_revised_claim_once_the_burst_is_in_the_window(ctx):
    batch = next(c for c in candidates(ctx, lookback=744) if c.resource_id.endswith("bbb2"))
    assert batch.matched_rule_ids == ["R-4"]
    ruling = Skeptic(ctx).judge(batch, round=2)
    assert ruling.verdict == "accept"
    # The reason must state the revised conclusion — a duty cycle — rather than repeat "idle".
    assert "duty-cycle" in ruling.reason


def test_skeptic_accepts_a_clean_orphan_without_fuss(ctx):
    orphans = [c for c in candidates(ctx) if c.matched_rule_ids[0] in {"R-1", "R-2"}]
    assert len(orphans) == 2
    assert all(Skeptic(ctx).judge(o, round=1).verdict == "accept" for o in orphans)


def test_skeptic_refuses_a_third_recheck_on_the_same_finding(ctx):
    batch = next(c for c in candidates(ctx) if c.resource_id.endswith("bbb2"))
    skeptic = Skeptic(ctx)
    ctx.state.facts["recheck_counts"][batch.candidate_id] = 2   # already re-checked twice
    ruling = skeptic.judge(batch, round=3)
    assert ruling.verdict == "reject"
    assert "re-investigated" in ruling.reason
