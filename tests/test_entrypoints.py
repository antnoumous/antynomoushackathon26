# tests/test_entrypoints.py
import json, subprocess, sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.api import app

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
