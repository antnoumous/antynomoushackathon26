from pathlib import Path
import pytest

ENV={"LLM_PROVIDER":"meterless","METERLESS_TOKEN":"unit-secret",
     "METERLESS_BASE_URL":"http://127.0.0.1:18088/v1","METERLESS_MODEL":"meterless/local",
     "ZETARIS_API_KEY":"unit-zetaris","ZETARIS_ORG_ID":"unit-org",
     "ZETARIS_REST_URL":"http://127.0.0.1:9000/api/v1.0"}
BASE={"snapshot_id":"base","policy_object":"S.base","manifest_object":"S.manifest","expected_sha256":"a"*64}
VARIANT=dict(BASE,snapshot_id="variant",expected_sha256="b"*64)


def test_remote_runner_keeps_credentials_in_stdin_only(tmp_path,capsys):
    from scripts.run_meterless_remote import run_remote_acceptance
    calls=[]
    def process(argv,**kwargs):calls.append((argv,kwargs));return type("Result",(),{"returncode":0})()
    rc=run_remote_acceptance(ssh_config=tmp_path / "ssh-config",release_dir="driftwatch-meterless/test-release",
        runtime_env=ENV,base_settings=BASE,variant_settings=VARIANT,output_dir="logs/acceptance-unit",run_subprocess=process)
    assert rc == 0 and len(calls) == 1
    assert "unit-secret" not in repr(calls[0][0])
    assert "unit-secret" in calls[0][1]["input"]
    assert "zetaris-01" in calls[0][0] and "--stdin-env" in calls[0][0][-1]
    assert "unit-secret" not in capsys.readouterr().out


@pytest.mark.parametrize("change",[{"OCI_CONFIG_FILE":"private"},{"METERLESS_TOKEN":17},
    {"METERLESS_TOKEN":""},{"ZETARIS_API_KEY":""},{"LLM_PROVIDER":"openai-compatible"},
    {"METERLESS_BASE_URL":"http://remote.example:18088/v1"},{"METERLESS_MODEL":"meterless/auto"}])
def test_runtime_env_rejects_forbidden_or_malformed_values(change):
    from scripts.run_meterless_remote import validate_runtime_env
    with pytest.raises(ValueError):validate_runtime_env(ENV | change)


@pytest.mark.parametrize("release,output",[("../escape","logs/ok"),("driftwatch-meterless/a;id","logs/ok"),
    ("driftwatch-meterless/a","../escape"),("driftwatch-meterless/a","logs/x/../bad"),
    ("driftwatch-meterless/a","logs/x\nid")])
def test_paths_cannot_become_arbitrary_remote_commands(tmp_path,release,output):
    from scripts.run_meterless_remote import run_remote_acceptance
    with pytest.raises(ValueError):
        run_remote_acceptance(ssh_config=tmp_path / "ssh-config",release_dir=release,runtime_env=ENV,
            base_settings=BASE,variant_settings=VARIANT,output_dir=output,
            run_subprocess=lambda *a,**k:pytest.fail("bad input reached SSH"))


def test_stdin_payload_is_bounded_and_strict_before_parsing():
    import io,json
    from scripts.run_meterless_remote import read_runtime_payload
    payload={"env":ENV,"base_settings":BASE,"variant_settings":VARIANT}
    assert read_runtime_payload(io.BytesIO(json.dumps(payload).encode())) == payload
    for raw in [b"x"*65537,b"[]",b'{"unexpected":1}',b"not-json"]:
        with pytest.raises(ValueError):read_runtime_payload(io.BytesIO(raw))


def test_nonzero_ssh_result_is_not_changed_to_success(tmp_path):
    from scripts.run_meterless_remote import run_remote_acceptance
    seen=[]
    def process(argv,**kwargs):seen.append(argv);return type("Result",(),{"returncode":23})()
    assert run_remote_acceptance(ssh_config=tmp_path / "config",release_dir="driftwatch-meterless/a",runtime_env=ENV,
        base_settings=BASE,variant_settings=VARIANT,output_dir="logs/test",run_subprocess=process) == 23
    assert "MemoryMax=1073741824" in seen[0][-1]


def test_process_error_never_echoes_input_secrets(tmp_path):
    from scripts.run_meterless_remote import run_remote_acceptance
    def fail(*a,**k):raise RuntimeError("unit-secret")
    with pytest.raises(RuntimeError) as caught:
        run_remote_acceptance(ssh_config=tmp_path / "config",release_dir="driftwatch-meterless/a",runtime_env=ENV,
            base_settings=BASE,variant_settings=VARIANT,output_dir="logs/test",run_subprocess=fail)
    assert "unit-secret" not in str(caught.value)


def test_acceptance_cli_uses_validated_stdin_environment(tmp_path,monkeypatch):
    import io,json,sys
    import scripts.verify_meterless_sponsors as module
    from tests.test_meterless_acceptance import ENV as POLICY_ENV,sources,generators,selections,SCEN
    real=module.run_acceptance;_,base,variant=selections();environment=dict(ENV,ZETARIS_ORG_ID="6")
    stdin=io.TextIOWrapper(io.BytesIO(json.dumps({"env":environment,"base_settings":base,"variant_settings":variant}).encode()))
    monkeypatch.setattr(sys,"stdin",stdin)
    def actual(**kwargs):
        assert kwargs["env"]["METERLESS_TOKEN"] == "unit-secret"
        return real(**kwargs,make_source=sources,make_generator=generators)
    monkeypatch.setattr(module,"run_acceptance",actual)
    assert module.main(["--stdin-env","--scenario",str(SCEN),"--output-dir",str(tmp_path / "proof")]) == 1
    result=json.loads((tmp_path / "proof" / "acceptance.json").read_text())
    assert result["acceptance_checks_passed"] and not result["sponsor_acceptance"]
