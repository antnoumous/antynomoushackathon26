import json
from pathlib import Path
import pytest
from app.generator import RulesGenerator
from app.providers.meterless import MeterlessGenerator
from app.providers.meterless_settings import MeterlessSettings,MeterlessError
from app.sources.zetaris_policy import ZetarisPolicySource
from app.sources.policy_snapshot import policy_digest,validate_rules
from tests.test_zetaris_integration import make_transport

SCEN=Path("data/scenarios/example_1")
ENV={"ZETARIS_REST_URL":"http://127.0.0.1:8888/api/v1.0","ZETARIS_API_KEY":"unit-policy-token",
     "ZETARIS_ORG_ID":"6","METERLESS_TOKEN":"unit-model-token"}


def selections():
    rules=json.loads((SCEN / "policy.json").read_text())["rules"]
    def setting(name,items):
        return {"snapshot_id":name,"policy_object":"S.rules","manifest_object":"S.manifest",
                "expected_sha256":policy_digest(validate_rules(items))}
    return rules,setting("base",rules),setting("variant",[r for r in rules if r["rule_id"] != "R-1"])


def sources(settings,scope):
    rules,_,_=selections()
    if settings.snapshot_id == "variant":rules=[r for r in rules if r["rule_id"] != "R-1"]
    transport,_=make_transport(rules,scope,snapshot=settings.snapshot_id)
    return ZetarisPolicySource(settings,transport=transport)


def generators(env):
    def transport(method,url,*,headers,payload,timeout_s):
        system=payload["messages"][0]["content"]
        name="run_summary" if '"summary"' in system else "finding_claim" if '"claim"' in system else "verdict_reason"
        user=payload["messages"][1]["content"]
        context=json.loads(user[user.index("{"):])
        out=RulesGenerator().complete(prompt="",schema={"name":name},context=context)
        return {"choices":[{"message":{"content":json.dumps(out)}}]}
    return MeterlessGenerator(MeterlessSettings.from_env(env),transport=transport)


def run(tmp_path,**kwargs):
    from scripts.verify_meterless_sponsors import run_acceptance
    _,base,variant=selections()
    arguments=dict(scenario=SCEN,base_settings=base,variant_settings=variant,
        output_dir=tmp_path / "proof",env=ENV,make_source=sources,make_generator=generators)
    arguments.update(kwargs)
    return run_acceptance(**arguments)


def test_combined_contract_executes_real_loops_and_all_schema_paths(tmp_path):
    result=run(tmp_path)
    assert result["acceptance_checks_passed"]
    assert not result["nightshift_verified"] and result["execution"] == "injected_contract_test"
    assert result["causal"]["removed"][0]["resource_class"] == "block_volume"
    assert result["base"]["provider"]["schemas"].keys() == {"finding_claim","verdict_reason","run_summary"}
    for side in ("base","variant"):
        report=json.loads((tmp_path / "proof" / (side+"-report.json")).read_text())
        events=[json.loads(line) for line in Path(report["trace_path"]).read_text().splitlines()]
        assert events and {e["run_id"] for e in events} == {report["run_id"]}
        assert events[-1]["action"] == "synthesise"
        assert result[side]["outcomes"]


def test_health_or_self_reported_success_without_actual_calls_fails(tmp_path):
    class ClaimedHealthy(RulesGenerator):
        def diagnostics(self):return {"configured_provider":"meterless","status":"success",
            "attempts":999,"successes":999,"fallbacks":0,"models":["meterless/local"],"schemas":{}}
    result=run(tmp_path,make_generator=lambda env:ClaimedHealthy())
    assert not result["acceptance_checks_passed"]
    assert not result["sponsor_acceptance"]


def test_stale_snapshot_with_matching_digest_fails(tmp_path):
    def stale(settings,scope):
        inner=sources(settings,scope)
        class Stale:
            def fetch(self,scope):
                result=inner.fetch(scope)
                return result.model_copy(update={"provenance":result.provenance.model_copy(update={"snapshot_id":"stale"})})
        return Stale()
    assert not run(tmp_path,make_source=stale)["acceptance_checks_passed"]


def test_missing_context_trace_is_not_replaced_by_manifest_claim(tmp_path,monkeypatch):
    from app.trace import Tracer
    real=Tracer.emit
    def filtered(self,**kwargs):
        if kwargs["action"] == "world_context":return None
        return real(self,**kwargs)
    monkeypatch.setattr(Tracer,"emit",filtered)
    assert not run(tmp_path)["acceptance_checks_passed"]


def test_wrong_removed_rule_cannot_satisfy_causal_acceptance(tmp_path):
    rules,_,variant=selections()
    wrong=[r for r in rules if r["rule_id"] != "R-2"]
    variant=dict(variant,expected_sha256=policy_digest(validate_rules(wrong)))
    def wrong_source(settings,scope):
        items=wrong if settings.snapshot_id == "variant" else rules
        transport,_=make_transport(items,scope,snapshot=settings.snapshot_id)
        return ZetarisPolicySource(settings,transport=transport)
    result=run(tmp_path,variant_settings=variant,make_source=wrong_source)
    assert not result["acceptance_checks_passed"]


def test_production_generator_requires_authenticated_local_discovery(monkeypatch):
    import app.providers.meterless_settings as settings
    from scripts.verify_meterless_sponsors import _default_generator
    monkeypatch.setattr(settings,"discover",lambda *a,**k:settings.MeterlessReadiness("unsupported_mode",("meterless/auto",)))
    with pytest.raises(MeterlessError) as caught:_default_generator(ENV)
    assert caught.value.category == "unsupported_mode"


@pytest.mark.parametrize("mode",["zero_calls","summary_fallback","no_effect","figure_failure","old_outcomes"])
def test_false_positive_paths_fail_checks_and_cli(tmp_path,monkeypatch,mode):
    import scripts.verify_meterless_sponsors as module
    real=module.run_acceptance
    _,base,variant=selections()
    def factory(env):
        if mode == "zero_calls":return RulesGenerator()
        gen=generators(env);original=gen.transport
        def transport(method,url,**kwargs):
            system=kwargs["payload"]["messages"][0]["content"]
            if '"summary"' in system:
                if mode == "summary_fallback":raise MeterlessError("timeout")
                if mode == "figure_failure":return {"choices":[{"message":{"content":'{"summary":"999999 USD","confidence":1.0}'}}]}
            return original(method,url,**kwargs)
        gen.transport=transport
        if mode == "old_outcomes":
            gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
        return gen
    def actual(**kwargs):
        kwargs.update(env=ENV,make_source=sources,make_generator=factory)
        if mode == "no_effect":kwargs["variant_settings"]=base
        return real(**kwargs)
    monkeypatch.setattr(module,"run_acceptance",actual)
    for label,value in [("base",base),("variant",variant)]:
        (tmp_path / (label+".json")).write_text(json.dumps(value))
    output=tmp_path / "cli-proof"
    code=module.main(["--scenario",str(SCEN),"--base-settings",str(tmp_path / "base.json"),
        "--variant-settings",str(tmp_path / "variant.json"),"--output-dir",str(output)])
    assert code != 0
    if (output / "acceptance.json").exists():
        result=json.loads((output / "acceptance.json").read_text())
        assert not result["acceptance_checks_passed"] and not result["sponsor_acceptance"]


def test_export_masks_copies_and_rebinds_report_linked_traces(tmp_path):
    import hashlib
    from scripts.verify_meterless_sponsors import export_proof
    run(tmp_path)
    raw=tmp_path / "proof";public=tmp_path / "public"
    export_proof(raw,public)
    manifest=json.loads((public / "export.json").read_text())
    assert len(manifest["files"]) == 7
    for name,hashes in manifest["files"].items():
        assert hashes["raw_sha256"] == hashlib.sha256((raw / name).read_bytes()).hexdigest()
        assert hashes["export_sha256"] == hashlib.sha256((public / name).read_bytes()).hexdigest()
        assert "unit-model-token" not in (public / name).read_text()
        assert "unit-policy-token" not in (public / name).read_text()
    report=json.loads((public / "base-report.json").read_text())
    assert Path(report["trace_path"]) == public / "base-trace.jsonl"
    events=[json.loads(line) for line in Path(report["trace_path"]).read_text().splitlines()]
    assert {e["run_id"] for e in events} == {report["run_id"]}
    with pytest.raises(FileExistsError):export_proof(raw,public)
