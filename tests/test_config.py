# tests/test_config.py
import os
import pytest
from app.config import RunConfig


def test_defaults_are_the_spec_caps():
    cfg = RunConfig.from_env_and_request({})
    assert cfg.max_rounds == 3
    assert cfg.max_resources == 25
    assert cfg.max_rechecks_per_finding == 2
    assert cfg.wall_clock_soft_s == 300
    assert cfg.wall_clock_hard_s == 540
    assert cfg.lookback_hours == 168


def test_env_sample_mode_wins_over_request(monkeypatch):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    cfg = RunConfig.from_env_and_request({"sample_mode": False})
    assert cfg.sample_mode is True


def test_request_may_lower_a_cap_but_not_raise_it(monkeypatch):
    cfg = RunConfig.from_env_and_request({"caps": {"max_rounds": 1}})
    assert cfg.max_rounds == 1
    with pytest.raises(ValueError):
        RunConfig.from_env_and_request({"caps": {"max_rounds": 99}})


def test_run_id_is_generated_and_filesystem_safe():
    cfg = RunConfig.from_env_and_request({})
    assert cfg.run_id
    assert all(c.isalnum() or c in "-_" for c in cfg.run_id)
