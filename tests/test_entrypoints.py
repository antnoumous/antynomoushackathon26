# tests/test_entrypoints.py
import json, subprocess, sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.api import app
from app.pipeline import run_pipeline
from app.state import RunState
from app.trace import Tracer

SCEN = Path("data/scenarios/example_1")
REQUEST = {"objective": "audit", "sample_mode": True}


def test_post_run_returns_the_documented_shape():
    client = TestClient(app)
    response = client.post("/run", json={**REQUEST, "scenario": str(SCEN)})
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"run_id", "status", "mode", "sources", "summary", "findings",
                         "undetermined", "trace_path"}
    assert body["mode"] == "sample"
    assert any(f["class"] == "cost_waste" for f in body["findings"])


def test_cli_and_http_return_the_same_findings(tmp_path):
    out = tmp_path / "result.json"
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps({**REQUEST, "scenario": str(SCEN)}))
    subprocess.run([sys.executable, "run.py", "--input", str(request_file),
                    "--scenario", str(SCEN), "--out", str(out)], check=True)
    cli = json.loads(out.read_text())
    http = TestClient(app).post("/run", json={**REQUEST, "scenario": str(SCEN)}).json()
    assert len(cli["findings"]) == len(http["findings"])


def test_unknown_scenario_is_a_400_not_a_crash():
    body = TestClient(app).post("/run", json={**REQUEST, "scenario": "data/scenarios/nope"}).json()
    assert "error" in body


def test_run_pipeline_closes_the_log_handles_it_opens(monkeypatch, tmp_path):
    """One open trace and one open state file per run, for the life of the process, is a leak."""
    monkeypatch.setenv("LOGS_DIR", str(tmp_path))
    closed: set[str] = set()
    for cls in (RunState, Tracer):
        original = cls.close
        monkeypatch.setattr(cls, "close",
                            lambda self, _o=original, _n=cls.__name__: (
                                closed.add(_n), _o(self))[1])
    run_pipeline({**REQUEST}, scenario_dir=SCEN)
    assert closed == {"RunState", "Tracer"}


def test_a_live_run_that_only_got_fixtures_says_so(monkeypatch, tmp_path, capsys):
    """A live run with no reachable tenancy must not quietly pretend it audited one."""
    monkeypatch.setenv("LOGS_DIR", str(tmp_path))
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    # Hermetic on any machine: even one that has real ~/.oci/config, the adapters must fail here.
    monkeypatch.setenv("OCI_CONFIG_FILE", str(tmp_path / "no-such-config"))
    report, _ = run_pipeline({"sample_mode": False}, scenario_dir=SCEN)

    assert report.mode == "live"
    assert "fixture" in report.summary["backends"]     # what actually answered the run
    assert report.summary["sources_degraded"] >= 1
    assert report.status in {"partial", "capped"}
    assert "no live backend answered" in capsys.readouterr().err
