from pathlib import Path
import pytest


def test_engine_acceptance_runs_real_pipeline_store_dedup_and_windows(tmp_path):
    from scripts.verify_world_model import run_world_acceptance
    output=tmp_path / "proof"
    result=run_world_acceptance(output)
    assert result["engine_acceptance"]
    assert {"Scout","Skeptic"} <= set(result["consumers"])
    assert result["dedup"]["before"] == result["dedup"]["after"]
    assert result["telemetry_windows"] == [168,744]
    assert (output / "acceptance.json").is_file()
    with pytest.raises(FileExistsError):
        run_world_acceptance(output)


def test_policy_ablation_changes_stored_selection_and_only_r1_finding(tmp_path):
    from scripts.verify_world_model import run_world_acceptance
    result=run_world_acceptance(tmp_path / "causal")
    assert result["causal"]["policy_observations_changed"]
    assert result["causal"]["only_r1_finding_removed"]
    assert result["causal"]["removed"][0]["resource_class"] == "block_volume"


def test_failed_real_context_guard_refuses_acceptance_and_cli_success(tmp_path,monkeypatch):
    from dataclasses import replace
    from app.world_model.context import ContextBuilderService
    from scripts.verify_world_model import run_world_acceptance,main
    real=ContextBuilderService.build
    def incomplete(self,**kwargs):return replace(real(self,**kwargs),complete=False)
    monkeypatch.setattr(ContextBuilderService,"build",incomplete)
    result=run_world_acceptance(tmp_path / "bad")
    assert not result["engine_acceptance"]
    assert main(["--output-dir",str(tmp_path / "cli-bad")]) != 0


@pytest.mark.parametrize("name",["example_1","example_2","example_3"])
def test_full_world_path_is_offline_under_hostile_provider_env(name,tmp_path,monkeypatch):
    import socket
    from app.pipeline import run_pipeline
    def blocked(*args,**kwargs):raise AssertionError("offline audit attempted networking")
    monkeypatch.setattr(socket,"socket",blocked)
    monkeypatch.setattr(socket,"create_connection",blocked)
    for key,value in {"LLM_PROVIDER":"meterless","METERLESS_BASE_URL":"not a valid URL",
                      "METERLESS_TOKEN":"rt-local","LOGS_DIR":str(tmp_path)}.items():monkeypatch.setenv(key,value)
    report,_=run_pipeline({"sample_mode":True},scenario_dir=Path("data/scenarios") / name)
    assert report.status == "success"
    assert report.summary["integrations"]["meterless_world_model"]["status"] == "used"


def test_generation_script_propagates_real_evaluator_failure(tmp_path):
    import os,shutil,subprocess,sys
    root=Path(__file__).resolve().parents[1]
    sandbox=tmp_path / "repo";sandbox.mkdir()
    for directory in ("app","data","input_examples","evals","scripts"):
        shutil.copytree(root / directory,sandbox / directory,ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(root / "run.py",sandbox / "run.py")
    shim=tmp_path / "python-shim"
    shim.write_text("#!"+sys.executable+"\nimport os,sys\n"
        "if sys.argv[1:3] == ['-m','evals.run_eval']: raise SystemExit(42)\n"
        "if 'scripts/make_scenario.py' in sys.argv: raise SystemExit(43)\n"
        "os.execv(sys.executable,[sys.executable,*sys.argv[1:]])\n")
    shim.chmod(0o700)
    env=dict(os.environ,PY=str(shim),SAMPLE_MODE="true",TMPDIR=str(tmp_path),LOGS_DIR=str(sandbox / "logs"))
    done=subprocess.run(["bash","scripts/run_examples.sh"],cwd=sandbox,env=env,capture_output=True,text=True,timeout=30)
    assert done.returncode == 42,done.stdout[-1000:] + done.stderr[-1000:]


def test_exported_proof_has_real_checksums_and_resolvable_trace(tmp_path):
    import hashlib,json
    from scripts.verify_world_model import main
    raw=tmp_path / "raw";export=tmp_path / "export"
    assert main(["--output-dir",str(raw),"--export-dir",str(export)]) == 0
    record=json.loads((export / "export.json").read_text())
    for name,hashes in record["files"].items():
        assert hashes["raw_sha256"] == hashlib.sha256((raw / name).read_bytes()).hexdigest()
        assert hashes["export_sha256"] == hashlib.sha256((export / name).read_bytes()).hexdigest()
    report=json.loads((export / "base-report.json").read_text())
    events=[json.loads(line) for line in Path(report["trace_path"]).read_text().splitlines()]
    assert events and {event["run_id"] for event in events} == {report["run_id"]}
    assert events[-1]["action"] == "synthesise"
