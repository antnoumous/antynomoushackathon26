# tests/test_generator.py
import pytest
from app.config import RunConfig
from app.generator import GeneratorUnavailableError, ModelGenerator, RulesGenerator, get_generator

FAKE_KEY = "test-key-not-a-real-credential"


def test_sample_mode_selects_the_rule_engine_even_when_a_key_is_present(monkeypatch):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    assert isinstance(get_generator(RunConfig.from_env_and_request({})), RulesGenerator)


def test_live_mode_without_a_key_degrades_to_rules_instead_of_crashing(monkeypatch):
    monkeypatch.delenv("SAMPLE_MODE", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert isinstance(get_generator(RunConfig.from_env_and_request({"sample_mode": False})), RulesGenerator)


def test_live_mode_with_a_key_uses_the_model(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "some-model")
    assert isinstance(get_generator(RunConfig.from_env_and_request({})), ModelGenerator)


def test_rule_engine_shapes_match_their_schema():
    gen = RulesGenerator()
    claim = gen.complete(prompt="", schema={"name": "finding_claim"},
                         context={"rule_id": "R-3", "resource_name": "sandbox-tmp",
                                  "stats": {"mean": 0.3, "peak": 0.4}, "iac_match_rule": None})
    assert set(claim) == {"claim", "confidence"}
    assert claim["claim"]
    with pytest.raises(KeyError):
        gen.complete(prompt="", schema={"name": "not_a_schema"}, context={})


def test_confidence_reflects_how_the_iac_link_was_made():
    gen = RulesGenerator()
    common = {"rule_id": "R-3", "resource_name": "x", "stats": {"mean": 0.4, "peak": 0.5}}
    declared = gen.complete(prompt="", schema={"name": "finding_claim"},
                            context={**common, "iac_match_rule": "tag"})
    inferred = gen.complete(prompt="", schema={"name": "finding_claim"},
                            context={**common, "iac_match_rule": "normalised"})
    unmatched = gen.complete(prompt="", schema={"name": "finding_claim"},
                             context={**common, "iac_match_rule": None})
    assert declared["confidence"] > inferred["confidence"] == unmatched["confidence"]


def test_model_generator_refuses_to_construct_without_a_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(GeneratorUnavailableError):
        ModelGenerator.from_env()


class FakeTime:
    monotonic = staticmethod(lambda: 100.0)


def test_a_model_call_timeout_shrinks_to_fit_the_run_budget(monkeypatch):
    """A 60 s call under a 115 s deadline is 15 s, and never under a second."""
    monkeypatch.setattr("app.generator.time", FakeTime)
    generator = ModelGenerator("https://example.invalid/v1", FAKE_KEY, "some-model", timeout_s=60)
    assert generator.current_timeout() == 60.0          # no deadline yet: the configured timeout

    generator.set_deadline(115.0)
    assert generator.current_timeout() == 15.0

    generator.set_deadline(99.0)                        # the budget is already gone
    assert generator.current_timeout() == 1.0


class _Resp:
    def __init__(self, content, status=200):
        self._content, self.status_code = content, status
    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"http {self.status_code}")
    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _ok_post(content):
    def post(url, headers=None, json=None, timeout=None):
        return _Resp(content)
    return post


def test_model_generator_expands_named_schemas_and_posts_the_full_one(monkeypatch):
    """Call sites hand the generator {"name": ...}; the model must receive a real schema and the
    context, or it cannot answer the shape the loop consumes (found on the first model live run).
    The stub mirrors requests.post's signature: a payload mismatch that the error fallback would
    otherwise swallow must fail loudly here, not degrade silently."""
    seen = {}
    def post(url, headers=None, json=None, timeout=None):
        assert url.endswith("/chat/completions")
        seen.update(json)
        return _Resp('{"claim": "detached volume", "confidence": 0.6}')
    monkeypatch.setattr("app.generator.requests.post", post)
    gen = ModelGenerator("https://example.invalid/v1", FAKE_KEY, "m")
    out = gen.complete(prompt="say the finding", schema={"name": "finding_claim"},
                       context={"rule_id": "R-1", "resource_name": "vol-x"})
    assert out == {"claim": "detached volume", "confidence": 0.6}
    assert "claim" in seen["messages"][0]["content"]        # full schema, not just the name
    assert "vol-x" in seen["messages"][1]["content"]        # context rendered into the prompt


def test_model_generator_falls_back_to_rules_on_http_error(monkeypatch):
    def boom(url, headers=None, json=None, timeout=None):
        return _Resp(None, status=500)
    monkeypatch.setattr("app.generator.requests.post", boom)
    gen = ModelGenerator("https://example.invalid/v1", FAKE_KEY, "m")
    out = gen.complete(prompt="", schema={"name": "run_summary"},
                       context={"resources": 6, "sources": 4, "accepted": 3,
                                "rejected": 0, "undetermined": 4})
    assert "6 resources" in out["summary"]                  # RulesGenerator's text


def test_model_generator_falls_back_on_off_schema_answers(monkeypatch):
    """A model that returns valid JSON of the wrong shape is as unusable as an HTTP 500."""
    monkeypatch.setattr("app.generator.requests.post",
                        _ok_post('{"claim": "no confidence attached"}'))
    gen = ModelGenerator("https://example.invalid/v1", FAKE_KEY, "m")
    out = gen.complete(prompt="", schema={"name": "finding_claim"},
                       context={"rule_id": "R-2", "resource_name": "ip-x",
                                "stats": {}, "iac_match_rule": None})
    assert set(out) == {"claim", "confidence"}              # rule engine's shape, model's failure


@pytest.mark.parametrize("mode,want",[("rules","rules"),("meterless","meterless"),("openai-compatible","openai-compatible")])
def test_explicit_provider_selection_is_not_silently_replaced(monkeypatch,mode,want):
    from app.generator import generator_diagnostics
    monkeypatch.setenv("LLM_PROVIDER",mode)
    monkeypatch.setenv("METERLESS_TOKEN","unit-registry-only")
    monkeypatch.setenv("LLM_API_KEY",FAKE_KEY)
    gen=get_generator(RunConfig(sample_mode=False))
    assert generator_diagnostics(gen)["configured_provider"] == want


def test_missing_meterless_config_never_selects_another_provider(monkeypatch):
    from app.generator import generator_diagnostics
    from app.providers.meterless import MeterlessGenerator
    monkeypatch.setenv("LLM_PROVIDER","meterless")
    monkeypatch.delenv("METERLESS_TOKEN",raising=False)
    gen=get_generator(RunConfig(sample_mode=False))
    assert isinstance(gen,MeterlessGenerator)
    gen.complete(prompt="",schema={"name":"verdict_reason"},context={"reason_key":"frequency_mismatch"})
    assert generator_diagnostics(gen)["fallbacks"] == 1
    assert generator_diagnostics(gen)["attempts"] == 0


def test_sample_overrides_hostile_provider_and_unknown_live_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER","not-a-provider")
    monkeypatch.setenv("METERLESS_BASE_URL","file:///wrong")
    monkeypatch.setenv("METERLESS_TOKEN","rt-local")
    assert isinstance(get_generator(RunConfig(sample_mode=True)),RulesGenerator)
    with pytest.raises(ValueError):get_generator(RunConfig(sample_mode=False))


def test_model_fallback_accounting_and_unknown_double_are_not_success(monkeypatch):
    from app.generator import generator_diagnostics
    monkeypatch.setattr("app.generator.requests.post",_ok_post('{"claim":"missing confidence"}'))
    gen=ModelGenerator("https://example.invalid/v1",FAKE_KEY,"m")
    gen.complete(prompt="",schema={"name":"finding_claim"},context={"rule_id":"R-2","resource_name":"ip-x","stats":{}})
    diag=generator_diagnostics(gen)
    assert (diag["attempts"],diag["successes"],diag["fallbacks"],diag["status"]) == (1,0,1,"partial")
    assert generator_diagnostics(object())["status"] == "unverified"
