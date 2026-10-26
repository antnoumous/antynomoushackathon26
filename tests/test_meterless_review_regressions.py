"""Reproductions from the independent whole-branch review; no real credentials."""
import json
from pathlib import Path
import pytest


@pytest.mark.parametrize("bad",["meterless/catalog-secret-sentinel","meterless/"+"x"*260,
                                "meterless/bad\nroute","meterless/\ud800"])
def test_discovery_rejects_secret_echo_or_unsafe_unbounded_ids(bad):
    from app.providers.meterless_settings import MeterlessSettings,discover
    settings=MeterlessSettings(token="catalog-secret-sentinel")
    result=discover(settings,transport=lambda *a,**k:{"data":[{"id":"meterless/local"},{"id":bad}]},timeout_s=1)
    assert result.state == "offline"
    assert result.model_ids == ()
    assert "catalog-secret-sentinel" not in repr(result)


@pytest.mark.parametrize("encoded",[False,True])
def test_publication_rejects_catalog_credentials_before_any_copy(tmp_path,encoded):
    from tests.test_meterless_acceptance import run,ENV
    from scripts.verify_meterless_sponsors import export_proof
    from app.providers.meterless_settings import MeterlessError
    run(tmp_path)
    raw=tmp_path / "proof";target=tmp_path / "public"
    path=raw / "base-outcomes.json"
    data=json.loads(path.read_text())
    token=ENV["METERLESS_TOKEN"]
    data["readiness"]={"state":"online","model_ids":["meterless/local","meterless/"+token]}
    rendered=json.dumps(data)
    if encoded:
        rendered=rendered.replace(token,"".join(chr(92)+"u"+format(ord(c),"04x") for c in token))
    path.write_text(rendered)
    original=path.read_bytes()
    with pytest.raises(MeterlessError) as caught:
        export_proof(raw,target,runtime_env=ENV)
    assert caught.value.category == "schema" and token not in str(caught.value)
    assert not target.exists() and path.read_bytes() == original
