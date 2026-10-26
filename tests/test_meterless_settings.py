import pytest


@pytest.mark.parametrize("value", ["127.0.0.1:8088", "http://127.0.0.1:8088/v1/",
    "http://127.0.0.1:8088/v1/models", "http://127.0.0.1:8088/v1/chat/completions",
    "http://127.0.0.1:8088/healthz"])
def test_url_is_normalized_once(value):
    from app.providers.meterless_settings import normalize_base_url
    assert normalize_base_url(value) == "http://127.0.0.1:8088/v1"


def test_ipv6_host_and_port_are_preserved():
    from app.providers.meterless_settings import normalize_base_url
    assert normalize_base_url("[::1]:8088/v1/models") == "http://[::1]:8088/v1"


@pytest.mark.parametrize("value", ["file:///etc/passwd", "http://user:secret@localhost:8088/v1",
    "http://localhost:8088/v1?token=secret", "http://localhost:8088/v1/v1",
    "http://localhost:8088/nope", "http://localhost:8088/#secret", "http://localhost:99999/v1",
    "http://local\nhost:8088/v1", "http://localhost:8088/v1?", "http://localhost:8088/v1#", ""])
def test_unsafe_url_is_rejected_without_echoing_input(value):
    from app.providers.meterless_settings import normalize_base_url, MeterlessError
    with pytest.raises(MeterlessError) as caught:
        normalize_base_url(value)
    assert caught.value.category == "configuration"
    assert "secret" not in str(caught.value)


def test_discovery_authenticates_and_keeps_unknown_meterless_modes():
    from app.providers.meterless_settings import MeterlessSettings, discover
    settings=MeterlessSettings(base_url="http://127.0.0.1:8088/v1",token="unit-test-only")
    seen=[]
    def transport(method,url,*,headers,payload,timeout_s):
        seen.append((method,url,headers,timeout_s))
        return {"data":[{"id":"meterless/local"},{"id":"meterless/new-mode"}]}
    result=discover(settings,transport=transport,timeout_s=2)
    assert result.state == "online"
    assert result.model_ids == ("meterless/local","meterless/new-mode")
    assert seen == [("GET","http://127.0.0.1:8088/v1/models",
        {"Authorization":"Bearer unit-test-only","meterless-app":"driftwatch"},2)]
    assert "unit-test-only" not in repr(settings)


@pytest.mark.parametrize("body,state",[({"status":"ok"},"offline"),({"data":[]},"offline"),
    ({"data":[{"id":"not-meterless"}]},"offline"),({"data":[{"id":17}]},"offline"),
    ({"data":[{"id":"meterless/auto"}]},"unsupported_mode"),
    ({"data":"bad"},"offline"),({"data":[{}]},"offline")])
def test_health_or_malformed_catalog_cannot_report_online(body,state):
    from app.providers.meterless_settings import MeterlessSettings, discover
    settings=MeterlessSettings(token="unit-only")
    result=discover(settings,transport=lambda *a,**k:body,timeout_s=1)
    assert result.state == state


@pytest.mark.parametrize("category,state",[("unauthorized","unauthorized"),("offline","offline"),
                                           ("timeout","offline"),("schema","offline")])
def test_discovery_preserves_unauthorized_but_does_not_expose_errors(category,state):
    from app.providers.meterless_settings import MeterlessSettings, MeterlessError,discover
    def transport(*a,**k):raise MeterlessError(category)
    assert discover(MeterlessSettings(token="unit-only"),transport=transport,timeout_s=1).state == state


def test_settings_from_env_normalize_and_hide_actual_token():
    from app.providers.meterless_settings import MeterlessSettings
    settings=MeterlessSettings.from_env({"METERLESS_TOKEN":"unit-env-sentinel",
                                       "METERLESS_BASE_URL":"127.0.0.1:8088/v1/models"})
    assert settings.base_url == "http://127.0.0.1:8088/v1"
    assert settings.token.get_secret_value() == "unit-env-sentinel"
    assert "unit-env-sentinel" not in repr(settings)
    assert "unit-env-sentinel" not in settings.model_dump_json()


@pytest.mark.parametrize("token",[None,""," ","rt-local","bad\ntoken"])
def test_placeholder_or_header_unsafe_tokens_never_reach_transport(token):
    from app.providers.meterless_settings import MeterlessSettings,MeterlessError
    env={} if token is None else {"METERLESS_TOKEN":token}
    with pytest.raises(MeterlessError) as caught:MeterlessSettings.from_env(env)
    assert caught.value.category == "configuration"


def test_local_only_settings_reject_cloud_modes_and_invalid_budget():
    from app.providers.meterless_settings import MeterlessSettings,MeterlessError
    from pydantic import ValidationError
    with pytest.raises(MeterlessError) as caught:
        MeterlessSettings.from_env({"METERLESS_TOKEN":"unit-only","METERLESS_MODEL":"meterless/auto"})
    assert caught.value.category == "unsupported_mode"
    for budget in [float("nan"),float("inf"),0,-1,61,True]:
        with pytest.raises((ValidationError,MeterlessError)):
            MeterlessSettings(token="unit-only",timeout_s=budget)
