# tests/test_planner.py
from datetime import datetime, timezone
from pathlib import Path
from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.models import Resource
from app.state import RunState
from app.trace import Tracer
import io, pytest

SCEN = Path("data/scenarios/example_1")


def ctx(tmp_path, sample=True):
    cfg = RunConfig.from_env_and_request({"sample_mode": sample})
    return AgentContext(config=cfg, sources={}, generator=RulesGenerator(),
                        state=RunState(cfg.run_id, tmp_path),
                        trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                        ledger=EvidenceLedger())


def res(i):
    return Resource(resource_id=f"r{i}", resource_class="compute_instance", display_name=f"n{i}",
                    compartment_id="c1", lifecycle_state="RUNNING",
                    time_created=datetime(2026, 8, 1, tzinfo=timezone.utc))


def test_planner_respects_max_resources(tmp_path):
    c = ctx(tmp_path)
    c.config.max_resources = 3
    assignment = Planner(c).assign(round=1, resources=[res(i) for i in range(10)], recheck_requests=[])
    assert len(assignment.resource_ids) == 3
    assert assignment.assignment_id == "A-1"


def test_recheck_requests_narrow_the_assignment_and_change_the_window(tmp_path):
    c = ctx(tmp_path)
    request = {"resource_id": "r7", "lookback_hours": 744, "reason": "window excludes the burst"}
    assignment = Planner(c).assign(round=2, resources=[res(i) for i in range(10)],
                                   recheck_requests=[request])
    assert assignment.resource_ids == ["r7"]
    assert assignment.lookback_hours == 744
    assert assignment.focus == "recheck"


def test_planner_emits_one_trace_line_per_assignment(tmp_path):
    c = ctx(tmp_path)
    Planner(c).assign(round=1, resources=[res(0)], recheck_requests=[])
    Planner(c).assign(round=2, resources=[res(0)], recheck_requests=[])
    lines = c.trace.path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert '"agent_name": "Planner"' in lines[0]
