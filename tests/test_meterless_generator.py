def test_meterless_call_uses_local_route_and_records_success():
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    seen=[]
    def transport(method,url,*,headers,payload,timeout_s):
        seen.append((method,url,headers,payload,timeout_s))
        return {"choices":[{"message":{"content":'{"reason":"duty cycle","confidence":0.8}'}}]}
    gen=MeterlessGenerator(MeterlessSettings(token="unit-only"),transport=transport)
    result=gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
    assert result == {"reason":"duty cycle","confidence":0.8}
    assert seen[0][0:2] == ("POST","http://127.0.0.1:8088/v1/chat/completions")
    assert seen[0][2] == {"Authorization":"Bearer unit-only","meterless-app":"driftwatch","meterless-scope":"user"}
    assert seen[0][3]["model"] == "meterless/local"
    assert '"reason"' in seen[0][3]["messages"][0]["content"]
    assert (gen.diagnostics()["attempts"],gen.diagnostics()["successes"],gen.diagnostics()["fallbacks"]) == (1,1,0)


import pytest


@pytest.mark.parametrize("content",['[]','null','{}','{"reason":"x"}',
    '{"reason":"x","confidence":true}','{"reason":"x","confidence":"0.8"}',
    '{"reason":"x","confidence":NaN}','{"reason":"x","confidence":-0.1}',
    '{"reason":"x","confidence":1.1}','{"reason":17,"confidence":0.8}'])
def test_invalid_schema_is_visible_rules_fallback(content):
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    gen=MeterlessGenerator(MeterlessSettings(token="unit-only"),transport=lambda *a,**k:{
        "choices":[{"message":{"content":content}}]})
    out=gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
    assert out["confidence"] == 0.8 and "duty-cycle problem" in out["reason"]
    assert (gen.diagnostics()["attempts"],gen.diagnostics()["successes"],gen.diagnostics()["fallbacks"]) == (1,0,1)
    row=gen.recorder.outcomes()[0]
    assert (row.actual_backend,row.category,row.attempted) == ("rules","schema",True)


@pytest.mark.parametrize("name,context,bad",[
    ("finding_claim",{"rule_id":"R-2","resource_name":"ip-x","stats":{}},'{"claim":17,"confidence":0.8}'),
    ("run_summary",{"resources":6,"sources":4,"accepted":3,"rejected":0,"undetermined":4},'{"summary":false,"confidence":0.8}')])
def test_each_text_schema_rejects_non_strings(name,context,bad):
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    gen=MeterlessGenerator(MeterlessSettings(token="unit-only"),transport=lambda *a,**k:{"choices":[{"message":{"content":bad}}]})
    out=gen.complete(prompt="",schema={"name":name},context=context)
    assert gen.diagnostics()["fallbacks"] == 1
    assert isinstance(out["claim" if name == "finding_claim" else "summary"],str)


def test_unknown_schema_is_programming_error_not_provider_fallback():
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    gen=MeterlessGenerator(MeterlessSettings(token="unit-only"),transport=lambda *a,**k:pytest.fail("unexpected request"))
    with pytest.raises(KeyError):gen.complete(prompt="",schema={"name":"unknown"},context={})
    assert gen.recorder.outcomes() == ()


@pytest.mark.parametrize("remaining,want",[(10,10),(100,60),(-1,None),(0,None)])
def test_exact_remaining_budget_and_no_requests_after_expiry(monkeypatch,remaining,want):
    from types import SimpleNamespace
    import app.providers.meterless as module
    from app.providers.meterless_settings import MeterlessSettings
    calls=[]
    def transport(*args,**kwargs):
        calls.append(kwargs["timeout_s"])
        return {"choices":[{"message":{"content":'{"reason":"duty cycle","confidence":0.8}'}}]}
    monkeypatch.setattr(module,"time",SimpleNamespace(monotonic=lambda:100.0))
    gen=module.MeterlessGenerator(MeterlessSettings(token="unit-only"),transport=transport)
    gen.set_deadline(100.0+remaining)
    gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
    assert calls == ([] if want is None else [want])
    assert gen.diagnostics()["attempts"] == (0 if want is None else 1)
    if want is None:
        assert gen.recorder.outcomes()[0].category == "timeout"
        assert gen.diagnostics()["status"] == "not_used"


def test_transport_failure_has_exactly_one_post_and_truthful_rules_outcome():
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings,MeterlessError
    calls=[]
    def transport(method,*args,**kwargs):calls.append(method);raise MeterlessError("offline")
    gen=MeterlessGenerator(MeterlessSettings(token="unit-only"),transport=transport)
    gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
    assert calls == ["POST"]
    assert gen.recorder.outcomes()[0].category == "offline"


def test_configuration_failure_is_visible_without_a_remote_attempt():
    from app.providers.meterless import MeterlessGenerator
    gen=MeterlessGenerator(None,configuration_error="configuration")
    out=gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
    assert "duty-cycle problem" in out["reason"]
    assert (gen.diagnostics()["attempts"],gen.diagnostics()["fallbacks"],gen.diagnostics()["status"]) == (0,1,"not_used")


def test_response_echoing_bearer_is_not_published_as_prose():
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    gen=MeterlessGenerator(MeterlessSettings(token="unit-response-secret"),transport=lambda *a,**k:{
        "choices":[{"message":{"content":'{"reason":"unit-response-secret","confidence":0.8}'}}]})
    out=gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
    assert "unit-response-secret" not in str(out)
    assert gen.recorder.outcomes()[0].category == "schema"
