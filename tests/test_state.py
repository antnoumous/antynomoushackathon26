# tests/test_state.py
import json
from app.state import RunState

def test_state_file_is_separate_from_the_trace_file(tmp_path):
    state = RunState(run_id="run-abc", logs_dir=tmp_path)
    assert state.path == tmp_path / "state-run-abc.jsonl"
    assert state.path.name != f"trace-run-abc.jsonl"

def test_appends_are_ordered_and_round_trip(tmp_path):
    state = RunState(run_id="run-abc", logs_dir=tmp_path)
    state.append("hydrate", {"resources": 6})
    state.append("assignment", {"round": 1, "resource_ids": ["r1"]})
    kinds = [r["kind"] for r in state.records()]
    assert kinds == ["hydrate", "assignment"]
    assert json.loads(state.path.read_text().splitlines()[1])["round"] == 1
