"""Task 4 integration: the production remote policy source through the real
Orchestrator/Scout/Skeptic/Writer path, with an in-memory transport. No network, no
Zetaris instance, no credentials beyond the literal test token."""
import copy
import io
import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.agents.base import AgentContext
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.loop import Orchestrator
from app.sources import get_source
from app.sources.base import Scope
from app.sources.policy_snapshot import policy_digest, scope_digest, validate_rules
from app.sources.zetaris_http import ZetarisError, ZetarisSettings
from app.sources.zetaris_policy import MANIFEST_COLUMNS, RULE_COLUMNS, ZetarisPolicySource
from app.state import RunState
from app.trace import Tracer

SCEN = Path("data/scenarios/example_1")
SNAP = "integration_base_v1"
CANARY = "sk-CANARY-DO-NOT-LEAK-9e7d"
POLICY_OBJECT = "DRIFTWATCH_REF.policy_rules_base_v1"
MANIFEST_OBJECT = "DRIFTWATCH_REF.policy_manifest_base_v1"


def base_rules():
    return json.loads((SCEN / "policy.json").read_text())["rules"]


def settings_for(digest):
    return ZetarisSettings(
        base_url="http://127.0.0.1:8888/api/v1.0",
        api_key=SecretStr("test-only-token"),
        org_id="6",
        policy_object=POLICY_OBJECT,
        manifest_object=MANIFEST_OBJECT,
        snapshot_id=SNAP,
        expected_sha256=digest,
    )


def make_transport(rules, scope, *, starts=None, fail=None, snapshot=None):
    snap = snapshot or SNAP
    normalized = validate_rules(copy.deepcopy(rules))
    digest = policy_digest(normalized)
    manifest = {
        "snapshot_id": snap,
        "schema_version": "1",
        "expected_count": str(len(normalized)),
        "content_sha256": digest,
        "requested_scope_hash": scope_digest(scope),
        "observed_at_utc": "2026-10-22T08:00:00+00:00",
    }
    rows = [
        {
            "snapshot_id": snap,
            "rule_id": r["rule_id"],
            "class": r["class"],
            "when_json": json.dumps(r["when"], sort_keys=True, separators=(",", ":")),
            "note": r["note"],
        }
        for r in normalized
    ]

    def transport(config, queries, deadline):
        if starts is not None:
            starts.append(1)
        if fail == "auth":
            raise ZetarisError("authentication", retryable=False)
        if fail == "transport":
            raise ZetarisError("transport", retryable=True)
        manifest_resp = {
            "headers": list(MANIFEST_COLUMNS),
            "data": [[manifest[c] for c in MANIFEST_COLUMNS]],
            "total": 1,
            "timeUsed": 1,
        }
        rules_resp = {
            "headers": list(RULE_COLUMNS),
            "data": [[row[c] for c in RULE_COLUMNS] for row in rows],
            "total": len(rows),
            "timeUsed": 1,
        }
        if fail == "canary":
            rules_resp["error"] = {"detail": CANARY}
        return [manifest_resp, rules_resp]

    return transport, digest


def build_remote(tmp_path, transport, digest, *, scenario_fallback=True, **request):
    cfg = RunConfig.from_env_and_request({"sample_mode": True, **request})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac")}
    sources["policy"] = ZetarisPolicySource(settings_for(digest), transport=transport)
    stream = io.StringIO()
    ctx = AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                       state=RunState(cfg.run_id, tmp_path),
                       trace=Tracer(cfg.run_id, tmp_path, stream=stream),
                       ledger=EvidenceLedger(), scope=scope)
    ctx.extras["stdout_stream"] = stream
    orch = Orchestrator(ctx, scenario_dir=SCEN if scenario_fallback else None)
    return cfg, ctx, scope, orch


def rule_hits(ctx):
    return [e for e in ctx.ledger._items if e.kind == "rule_hit"]


def test_baseline_remote_run_matches_fixture_findings_and_carries_lineage(tmp_path):
    # scope must exist before the transport is built (the manifest pins its digest)
    draft_cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=draft_cfg.resource_types,
                  lookback_hours=draft_cfg.lookback_hours, resolution_minutes=60)
    transport, digest = make_transport(base_rules(), scope)
    cfg, ctx, scope2, orch = build_remote(tmp_path, transport, digest)
    assert scope2_digest_ok(scope, scope2)

    report = orch.run()
    assert report.status == "success"
    policy_status = next(s for s in report.sources if s.name == "policy")
    assert policy_status.backend == "live" and not policy_status.degraded
    assert policy_status.provenance is not None
    assert policy_status.provenance.row_count == 5
    assert policy_status.provenance.content_sha256 == digest

    accepted = {(f.resource_id[-4:], f.finding_class) for f in report.findings
                if f.status in {"accepted", "revised"}}
    assert ("eee5", "cost_waste") in accepted           # the R-1 detached volume

    hits = rule_hits(ctx)
    r1 = [h for h in hits if h.payload["rule_id"] == "R-1"]
    assert r1, "R-1 must have fired against the fixture inventory"
    for hit in r1:
        assert hit.payload["snapshot_id"] == SNAP
        assert hit.payload["content_sha256"] == digest
        assert hit.payload["provider"] == "zetaris"
        assert hit.payload["object_name"] == POLICY_OBJECT
        assert hit.payload["ref"] == f"policy:{digest}:R-1"

    trace_text = ctx.trace.path.read_text()
    assert "source_snapshot" in trace_text
    snap = [json.loads(line) for line in trace_text.splitlines()
            if json.loads(line)["action"] == "source_snapshot"][0]
    assert digest in snap["output_summary"] and SNAP in snap["output_summary"]
    assert "test-only-token" not in trace_text


def scope2_digest_ok(a, b):
    from app.sources.policy_snapshot import scope_digest
    return scope_digest(a) == scope_digest(b)


def test_variant_without_r1_removes_exactly_that_finding(tmp_path):
    draft_cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=draft_cfg.resource_types,
                  lookback_hours=draft_cfg.lookback_hours, resolution_minutes=60)

    variant_rules = [r for r in base_rules() if r["rule_id"] != "R-1"]
    transport_v, digest_v = make_transport(variant_rules, scope)
    _, ctx_v, _, orch_v = build_remote(tmp_path / "v", transport_v, digest_v)
    variant_report = orch_v.run()

    _, ctx_b, _, orch_b = build_remote(tmp_path / "b", *make_transport(base_rules(), scope))
    base_report = orch_b.run()

    base_set = {(f.resource_id[-4:], f.finding_class, f.status)
                for f in base_report.findings if f.status in {"accepted", "revised"}}
    variant_set = {(f.resource_id[-4:], f.finding_class, f.status)
                   for f in variant_report.findings if f.status in {"accepted", "revised"}}
    assert ("eee5", "cost_waste", "accepted") in base_set
    assert all(res != "eee5" or cls != "cost_waste" for res, cls, _ in variant_set)
    assert base_set - {("eee5", "cost_waste", "accepted")} == variant_set


def test_auth_failure_is_not_retried_and_fallback_keeps_fixture_identity(tmp_path):
    starts: list[int] = []
    draft_cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=draft_cfg.resource_types,
                  lookback_hours=draft_cfg.lookback_hours, resolution_minutes=60)
    transport, digest = make_transport(base_rules(), scope, starts=starts, fail="auth")
    _, ctx, _, orch = build_remote(tmp_path, transport, digest)
    report = orch.run()
    assert len(starts) == 1                                  # retryable=False honoured
    status = next(s for s in report.sources if s.name == "policy")
    assert status.degraded is True and status.backend == "fixture"
    assert status.provenance is None                         # fixture never inherits Zetaris metadata
    for hit in rule_hits(ctx):
        assert set(hit.payload) == {"rule_id", "_world"}
        assert hit.payload["_world"]["observation_ids"]


def test_no_fallback_policy_failure_yields_no_fabricated_finding(tmp_path):
    draft_cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=draft_cfg.resource_types,
                  lookback_hours=draft_cfg.lookback_hours, resolution_minutes=60)
    starts: list[int] = []
    transport, digest = make_transport(base_rules(), scope, starts=starts, fail="transport")
    _, ctx, _, orch = build_remote(tmp_path, transport, digest, scenario_fallback=False)
    report = orch.run()
    assert report.findings == []
    assert report.status == "partial"
    assert len(starts) == 2                                  # retryable transport retried once
    status = next(s for s in report.sources if s.name == "policy")
    assert status.backend == "none" and status.degraded is True


def test_canary_in_server_body_never_reaches_report_trace_or_stdout(tmp_path):
    draft_cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=draft_cfg.resource_types,
                  lookback_hours=draft_cfg.lookback_hours, resolution_minutes=60)
    transport, digest = make_transport(base_rules(), scope, fail="canary")
    _, ctx, _, orch = build_remote(tmp_path, transport, digest)
    report = orch.run()
    # The poisoned response degrades the source; the fixture fallback legitimately carries
    # findings. What must be true everywhere is that the raw server body never surfaces.
    status = next(s for s in report.sources if s.name == "policy")
    assert status.degraded is True and status.backend == "fixture"
    assert CANARY not in ctx.trace.path.read_text()
    assert CANARY not in report.model_dump_json()
    assert CANARY not in ctx.extras["stdout_stream"].getvalue()


def test_degraded_success_remote_result_reports_partial(tmp_path):
    draft_cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=draft_cfg.resource_types,
                  lookback_hours=draft_cfg.lookback_hours, resolution_minutes=60)
    transport, digest = make_transport(base_rules(), scope)
    _, ctx, _, orch = build_remote(tmp_path, transport, digest)
    inner = ctx.sources["policy"]

    class DegradedLive:
        name = "policy"

        def fetch(self, s):
            result = inner.fetch(s)
            return result.model_copy(update={"degraded": True, "reason": "stale replica read"})

    ctx.sources["policy"] = DegradedLive()  # type: ignore[assignment]
    report = orch.run()
    status = next(s for s in report.sources if s.name == "policy")
    assert status.degraded is True and status.reason == "stale replica read"
    assert status.backend == "live"
    assert report.status == "partial"


def test_complete_empty_remote_policy_is_identified_not_a_failure(tmp_path):
    draft_cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=draft_cfg.resource_types,
                  lookback_hours=draft_cfg.lookback_hours, resolution_minutes=60)
    transport, digest = make_transport([], scope)
    _, ctx, _, orch = build_remote(tmp_path, transport, digest)
    report = orch.run()
    assert report.findings == []
    status = next(s for s in report.sources if s.name == "policy")
    assert status.degraded is False and status.backend == "live"
    assert status.provenance is not None and status.provenance.complete is True
    assert report.status == "partial"
    assert "complete empty" in ctx.trace.path.read_text()


# ---------- Task 6: acceptance harness script ----------
import dataclasses
import sys as _sys

_ROOT = Path(__file__).resolve().parents[1]
_sys.path.insert(0, str(_ROOT / "scripts"))


def _input_scope():
    req = json.loads((_ROOT / "input_examples/example_1.json").read_text())
    cfg = RunConfig.from_env_and_request(req)
    scope = Scope(compartment_ids=cfg.compartment_ids, resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=cfg.resolution_minutes)
    return req, cfg, scope


def _selection(snapshot, rules=None):
    _, _, scope = _input_scope()
    transport, digest = make_transport(rules if rules is not None else base_rules(),
                                       scope, snapshot=snapshot)
    sel = {"snapshot_id": snapshot, "policy_object": POLICY_OBJECT,
           "manifest_object": MANIFEST_OBJECT, "expected_sha256": digest}
    return sel, transport


_ENV = {"ZETARIS_API_KEY": "test-on...nly",
        "ZETARIS_REST_URL": "http://127.0.0.1:9/api/v1.0",
        "ZETARIS_ORG_ID": "6"}


def _fake_make_source(transports):
    def make_source(settings, scope):
        return ZetarisPolicySource(settings, transport=transports[settings.snapshot_id])
    return make_source


def test_run_acceptance_reports_computed_difference(tmp_path):
    from verify_zetaris_policy import run_acceptance
    base_sel, base_tr = _selection("example1_base_v1")
    variant_rules = [r for r in base_rules() if r["rule_id"] != "R-1"]
    var_sel, var_tr = _selection("example1_no_volume_v1", variant_rules)
    out = tmp_path / "acceptance"
    result = run_acceptance(
        scenario=SCEN, base_settings=base_sel, variant_settings=var_sel,
        output_dir=out, env=dict(_ENV),
        make_source=_fake_make_source({base_sel["snapshot_id"]: base_tr,
                                       var_sel["snapshot_id"]: var_tr}),
        logs_dir=tmp_path / "logs")
    assert result["hybrid"] is True
    assert result["sponsor_acceptance"] is True
    assert result["base"]["rules_selected"] == 5 and result["base"]["policy_backend"] == "live"
    assert result["variant"]["rules_selected"] == 4
    assert result["expected_effect"]["rules_removed"] == ["R-1"]
    removed = {tuple(x) for x in result["changed_finding_keys"]["only_in_base"]}
    assert ("eee5", "cost_waste", "accepted") in removed
    assert result["changed_finding_keys"]["only_in_variant"] == []
    written = json.loads((out / "acceptance.json").read_text())
    assert written == json.loads(json.dumps(result))   # published file is the computed result
    for side in ("base", "variant"):
        assert list((out / side).glob("report-*.json"))
        assert list((out / side).glob("trace-*.jsonl"))
    blob = json.dumps(result) + "".join(
        f.read_text() for f in (out / "base").glob("trace-*.jsonl"))
    assert "test-on...nly" not in blob


def test_run_acceptance_fallback_only_fails_sponsor_acceptance(tmp_path):
    from verify_zetaris_policy import run_acceptance
    base_sel, _ = _selection("example1_base_v1")
    var_sel, _ = _selection("example1_no_volume_v1")
    def failing(config, queries, deadline):
        raise ZetarisError("authentication", retryable=False)
    result = run_acceptance(
        scenario=SCEN, base_settings=base_sel, variant_settings=var_sel,
        output_dir=tmp_path / "acc", env=dict(_ENV),
        make_source=_fake_make_source({base_sel["snapshot_id"]: failing,
                                       var_sel["snapshot_id"]: failing}),
        logs_dir=tmp_path / "logs")
    assert result["sponsor_acceptance"] is False          # fallback never counts, report or not
    assert result["base"]["policy_backend"] == "fixture"
    assert (tmp_path / "acc" / "acceptance.json").exists()


def test_run_acceptance_rejects_existing_output_dir(tmp_path):
    from verify_zetaris_policy import run_acceptance
    base_sel, _ = _selection("example1_base_v1")
    var_sel, _ = _selection("example1_no_volume_v1")
    (tmp_path / "out").mkdir()
    with pytest.raises(FileExistsError):
        run_acceptance(scenario=SCEN, base_settings=base_sel, variant_settings=var_sel,
                       output_dir=tmp_path / "out", env=dict(_ENV),
                       make_source=_fake_make_source({}), logs_dir=tmp_path / "logs")


def test_settings_validation_rejects_secrets_and_malformed():
    from verify_zetaris_policy import validate_settings
    base_sel, _ = _selection("example1_base_v1")
    for bad, why in [({**base_sel, "api_key": "***"}, "secret"),
                     ({**base_sel, "ZETARIS_API_KEY": "x"}, "secret"),
                     ({**base_sel, "base_url": "http://evil/"}, "secret"),
                     ({k: v for k, v in base_sel.items() if k != "manifest_object"}, "settings")]:
        with pytest.raises(ValueError) as e:
            validate_settings(bad)
        assert why in str(e.value).lower()
        assert "evil" not in str(e.value)                  # never echoes offending values


def test_default_settings_construction_fails_without_env_secrets():
    from verify_zetaris_policy import build_settings
    sel, _ = _selection("example1_base_v1")
    with pytest.raises(ZetarisError):
        build_settings({}, sel)                            # bearer/base/org are environment-only


def test_main_reports_errors_as_exit_2(tmp_path, capsys):
    from verify_zetaris_policy import main
    base_sel, _ = _selection("example1_base_v1")
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps({**base_sel, "api_key": "***"}))
    good_file = tmp_path / "good.json"
    good_file.write_text(json.dumps(base_sel))
    rc = main(["--scenario", "data/scenarios/example_1",
               "--base-settings", str(bad_file), "--variant-settings", str(good_file),
               "--output-dir", str(tmp_path / "nope")])
    assert rc == 2
    assert "secret" in capsys.readouterr().out.lower()
    assert "leaked" not in capsys.readouterr().out        # no value echoed
