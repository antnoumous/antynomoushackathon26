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
