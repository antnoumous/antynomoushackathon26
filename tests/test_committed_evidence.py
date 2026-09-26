# tests/test_committed_evidence.py
"""The committed evidence has to belong to the run it is filed under.

`output_examples/*.json`, `logs/samples/trace-*.jsonl` and the rendered reports are what a judge
reads instead of watching the agent work, so they are the easiest place in this repository to be
quietly wrong. They were, once: the regeneration script picked each run's artifacts by file mtime,
two runs landed in the same second, and `trace-example_2.jsonl` was committed carrying example_1's
run. These tests are the guard that replaced that guess.
"""
import json
from pathlib import Path

import pytest

EXAMPLES = ("example_1", "example_2", "example_3")


def _report_and_trace(name: str) -> tuple[dict, list[dict]]:
    report = json.loads(Path(f"output_examples/{name}.json").read_text())
    lines = [json.loads(line) for line in
             Path(f"logs/samples/trace-{name}.jsonl").read_text().splitlines() if line.strip()]
    return report, lines


@pytest.mark.parametrize("name", EXAMPLES)
def test_a_committed_trace_carries_its_own_reports_run_id(name):
    report, lines = _report_and_trace(name)

    assert lines, "a committed trace cannot be empty"
    assert {line["run_id"] for line in lines} == {report["run_id"]}
    assert Path(report["trace_path"]).name == f"trace-{report['run_id']}.jsonl"


@pytest.mark.parametrize("name", EXAMPLES)
def test_the_last_trace_line_is_the_narrative_in_its_report(name):
    """The surest sign a trace belongs to another scenario: the numbers do not match."""
    report, lines = _report_and_trace(name)
    final = lines[-1]

    assert final["action"] == "synthesise"
    assert final["output_summary"] == report["summary"]["narrative"]


@pytest.mark.parametrize("name", EXAMPLES)
def test_the_committed_markdown_matches_the_committed_json(name):
    report = json.loads(Path(f"output_examples/{name}.json").read_text())
    markdown = Path(f"output_examples/{name}_report.md").read_text()

    assert report["summary"]["narrative"] in markdown
    for finding in report["findings"]:
        assert finding["claim"] in markdown
        assert finding["finding_id"] in markdown


@pytest.mark.parametrize("name", EXAMPLES)
def test_a_committed_state_file_is_the_record_of_that_run(name):
    report, _ = _report_and_trace(name)
    events = [json.loads(line) for line in
              Path(f"logs/samples/state-{name}.jsonl").read_text().splitlines() if line.strip()]

    assert events, "the state file is the append-only record of the run"
    assert {event["run_id"] for event in events} == {report["run_id"]}
    assert any(event["kind"] == "assignment" for event in events)
    assert events[-1]["kind"] == "report"
    # A clean tenancy has no candidates and therefore no rulings; any other run must record one.
    if report["findings"]:
        assert any(event["kind"] == "ruling" for event in events)
    # The state's own view of the tenancy must agree with the report's, which is exactly the
    # comparison that failed while the previous run's trace sat in the repository.
    hydrate = [event for event in events if event["kind"] == "hydrate"][0]
    assert hydrate["resources"] == report["summary"]["resources_in_scope"]
