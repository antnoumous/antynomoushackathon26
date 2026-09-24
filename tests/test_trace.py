# tests/test_trace.py
import io, json
from pathlib import Path
from app.trace import Tracer, REQUIRED_FIELDS

def test_every_line_carries_the_required_fields(tmp_path):
    stream = io.StringIO()
    tracer = Tracer(run_id="run-abc", logs_dir=tmp_path, stream=stream)
    tracer.emit(agent_name="Scout", action="propose_finding", input_summary="batch-01 168h",
                output_summary="candidate R-3", target_agent="Skeptic", confidence=0.6,
                round=1, evidence_refs=["E-001"])
    record = json.loads(stream.getvalue().strip())
    assert set(REQUIRED_FIELDS) <= set(record)
    assert record["round"] == 1
    assert record["evidence_refs"] == ["E-001"]
    assert record["status"] == "success"

def test_the_file_matches_stdout_line_for_line(tmp_path):
    stream = io.StringIO()
    tracer = Tracer(run_id="run-abc", logs_dir=tmp_path, stream=stream)
    for i in range(3):
        tracer.emit(agent_name="Scout", action="act", input_summary=str(i),
                    output_summary=str(i), status="capped")
    tracer.close()
    assert tracer.path == tmp_path / "trace-run-abc.jsonl"
    assert tracer.path.read_text().strip().splitlines() == stream.getvalue().strip().splitlines()
    assert all(json.loads(line)["status"] == "capped" for line in tracer.path.read_text().splitlines())
