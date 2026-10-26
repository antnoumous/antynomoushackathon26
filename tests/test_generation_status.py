def test_recorder_counts_actual_attempts_fallbacks_and_per_schema():
    from app.generation_status import GenerationOutcome,GenerationRecorder
    rec=GenerationRecorder("meterless")
    assert rec.summary()["status"] == "not_used"
    rec.record(GenerationOutcome("finding_claim","meterless","meterless","meterless/local",True,False,None,0.1))
    rec.record(GenerationOutcome("run_summary","meterless","rules",None,False,True,"configuration",0.0))
    result=rec.summary()
    assert (result["attempts"],result["successes"],result["fallbacks"],result["status"]) == (1,1,1,"partial")
    assert result["schemas"]["finding_claim"] == {"attempts":1,"successes":1,"fallbacks":0}
    assert result["models"] == ["meterless/local"]
    assert len(rec.outcomes()) == 2
    assert GenerationRecorder("meterless").outcomes() == ()


def test_recorder_refuses_nonfinite_or_contradictory_outcomes_without_echoing_values():
    from dataclasses import replace
    import pytest
    from app.generation_status import GenerationOutcome,GenerationRecorder
    row=GenerationOutcome("verdict_reason","meterless","meterless","meterless/local",True,False,None,0.1)
    for change in [{"latency_s":float("nan")},{"latency_s":float("inf")},{"latency_s":-1},
                   {"actual_backend":"private-token"},{"category":"private-token"},
                   {"attempted":False},{"fallback":True},{"configured_provider":"rules"}]:
        rec=GenerationRecorder("meterless")
        with pytest.raises(ValueError) as caught:rec.record(replace(row,**change))
        assert "private-token" not in str(caught.value)
        assert rec.outcomes() == ()


def test_configuration_fallback_with_zero_attempts_remains_not_used():
    from app.generation_status import GenerationOutcome,GenerationRecorder
    rec=GenerationRecorder("meterless")
    rec.record(GenerationOutcome("run_summary","meterless","rules",None,False,True,"configuration",0.0))
    assert rec.summary()["status"] == "not_used"
    assert rec.summary()["fallbacks"] == 1


def _fixture_meterless(ctx,*,fail_summary=False):
    import json
    from app.generator import RulesGenerator
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings,MeterlessError
    rules=RulesGenerator()
    def transport(method,url,*,headers,payload,timeout_s):
        system=payload["messages"][0]["content"]
        name="run_summary" if '"summary"' in system else "finding_claim" if '"claim"' in system else "verdict_reason"
        if name == "run_summary" and fail_summary:raise MeterlessError("timeout")
        user=payload["messages"][1]["content"]
        context=json.loads(user[user.index("{"):])
        return {"choices":[{"message":{"content":json.dumps(rules.complete(prompt="",schema={"name":name},context=context))}}]}
    ctx.generator=MeterlessGenerator(MeterlessSettings(token="unit-final-call"),transport=transport)
    return ctx.generator


def test_summary_fallback_is_in_final_report_not_missed_by_early_snapshot(tmp_path):
    import json
    from tests.test_loop import build
    from app.loop import Orchestrator
    _,ctx=build(tmp_path)
    _fixture_meterless(ctx,fail_summary=True)
    try:
        report=Orchestrator(ctx).run()
        assert report.status == "partial"
        diag=report.summary["integrations"]["meterless_nightshift"]
        assert diag["fallbacks"] == 1 and diag["schemas"]["run_summary"]["fallbacks"] == 1
        assert ctx.state.records()[-1]["status"] == "partial"
        assert json.loads(ctx.trace.path.read_text().splitlines()[-1])["action"] == "synthesise"
    finally:ctx.trace.close();ctx.state.close()


def test_attempt_observer_precedes_io_and_final_trace_has_all_outcomes(tmp_path):
    import json
    from tests.test_loop import build
    from app.loop import Orchestrator
    _,ctx=build(tmp_path)
    gen=_fixture_meterless(ctx,fail_summary=True)
    transport=gen.transport;at_io=[]
    def watched(*args,**kwargs):
        at_io.append(json.loads(ctx.trace.path.read_text().splitlines()[-1])["action"])
        return transport(*args,**kwargs)
    gen.transport=watched
    try:
        report=Orchestrator(ctx).run()
        assert at_io and set(at_io) == {"provider_attempt"}
        events=[json.loads(line) for line in ctx.trace.path.read_text().splitlines()]
        outcomes=[event for event in events if event["action"] == "provider_result"]
        assert len(outcomes) == len(gen.recorder.outcomes())
        assert len([event for event in events if event["action"] == "provider_fallback"]) == 1
        assert events[-1]["action"] == "synthesise"
        assert "unit-final-call" not in ctx.trace.path.read_text()
        assert all(json.loads(event["output_summary"])["schema_name"] in {
            "finding_claim","verdict_reason","run_summary"} for event in outcomes)
        assert {source.backend for source in report.sources} == {"fixture"}
    finally:ctx.trace.close();ctx.state.close()


def test_capped_run_retains_last_call_fallback_and_both_integrations(tmp_path):
    from tests.test_loop import build
    from app.loop import Orchestrator
    _,ctx=build(tmp_path,caps={"max_rounds":1})
    _fixture_meterless(ctx,fail_summary=True)
    try:
        report=Orchestrator(ctx).run()
        assert report.status == "capped" and "max_rounds" in report.caps_hit
        assert report.summary["integrations"]["meterless_nightshift"]["fallbacks"] == 1
        assert report.summary["integrations"]["meterless_world_model"]["status"] == "used"
        assert ctx.state.records()[-1]["status"] == "capped"
    finally:ctx.trace.close();ctx.state.close()


def test_successful_provider_cannot_hide_empty_policy(tmp_path):
    from tests.test_loop import build
    from app.loop import Orchestrator
    from app.sources.base import SourceResult
    _,ctx=build(tmp_path)
    class Empty:
        def fetch(self,scope):return SourceResult(records=[],backend="fixture",degraded=False)
    ctx.sources["policy"]=Empty()
    _fixture_meterless(ctx)
    try:
        report=Orchestrator(ctx).run()
        assert report.status == "partial" and report.findings == []
        assert report.summary["integrations"]["meterless_nightshift"]["successes"] == 1
        assert ctx.state.records()[-1]["status"] == "partial"
    finally:ctx.trace.close();ctx.state.close()


def test_compatible_render_failure_is_not_counted_as_an_http_attempt(monkeypatch):
    import pytest
    from app.generator import ModelGenerator
    class Unrenderable:
        def __str__(self):raise RuntimeError("private-render-detail")
    monkeypatch.setattr("app.generator.requests.post",lambda *a,**k:pytest.fail("render failed before HTTP"))
    gen=ModelGenerator("https://example.invalid/v1","unit-only","m")
    gen.complete(prompt="",schema={"name":"verdict_reason"},context={
        "reason_key":"frequency_mismatch","unrenderable":Unrenderable()})
    assert gen.diagnostics()["attempts"] == 0
    assert gen.diagnostics()["fallbacks"] == 1
    assert "private-render-detail" not in str(gen.diagnostics())
