# tests/test_scout.py
import json
from pathlib import Path
import pytest
from datetime import datetime, timezone
from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.agents.scout import Scout
from app.config import RunConfig
from app.evidence import DanglingEvidenceError, EvidenceLedger
from app.generator import RulesGenerator
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer
import io

SCEN = Path("data/scenarios/example_1")


@pytest.fixture
def ctx(tmp_path):
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac", "policy")}
    return AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                        state=RunState(cfg.run_id, tmp_path),
                        trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                        ledger=EvidenceLedger(), scope=scope)


def hydrate_and_assign(ctx, round=1, lookback_hours=None):
    """The Scout must hydrate the shared state before it can investigate anything, and the
    Planner must be given the real resources — an empty assignment investigates nothing."""
    scout = Scout(ctx)
    scout.hydrate()
    assignment = Planner(ctx).assign(
        round=round, resources=list(ctx.state.facts["resources"].values()), recheck_requests=[])
    if lookback_hours is not None:
        assignment = assignment.model_copy(update={"lookback_hours": lookback_hours})
    return scout, assignment


def test_hydrate_loads_six_resources_three_declarations_and_five_rules(ctx):
    hydrate_and_assign(ctx)
    assert len(ctx.state.facts["resources"]) == 6
    assert len(ctx.state.facts["declarations"]) == 3
    assert len(ctx.state.facts["rules"]) == 5


def test_scout_proposes_the_idle_claim_for_batch01_on_the_narrow_window(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    batch = next(c for c in candidates if c.resource_id.endswith("bbb2"))
    assert batch.finding_class == "cost_waste"
    assert batch.matched_rule_ids == ["R-3"]
    assert "average" in batch.claim
    assert batch.confidence < 0.8           # lifecycle-only evidence, no purpose found
    ctx.ledger.resolve(batch.evidence_refs)  # every ref must resolve


def test_scout_never_sets_a_status(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    for candidate in scout.investigate(assignment):
        assert not hasattr(candidate, "status")


def test_every_candidate_ref_resolves_or_the_ledger_raises(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    assert candidates
    for candidate in candidates:
        assert candidate.evidence_refs
        assert ctx.ledger.resolve(candidate.evidence_refs)
    with pytest.raises(DanglingEvidenceError):
        ctx.ledger.resolve(["E-404"])


def test_insufficient_coverage_becomes_undetermined_not_a_candidate(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    scout.investigate(assignment)
    undetermined = {u.resource_id: u.reason for u in scout.undetermined()}
    sandbox = next(k for k in undetermined if k.endswith("ddd4"))
    assert "41h of 168h" in undetermined[sandbox]


def test_unattributed_finding_needs_no_telemetry_but_cost_finding_does(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    sandbox = [c for c in candidates if c.resource_id.endswith("ddd4")]
    assert [c.finding_class for c in sandbox] == ["unattributed"]


def test_scout_does_not_flag_a_genuinely_busy_instance(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    assert not [c for c in candidates if c.resource_id.endswith("aaa1")]  # web-01, steady 50%
    assert not [c for c in candidates if c.resource_id.endswith("ccc3")]  # reports-01, steady 10%
