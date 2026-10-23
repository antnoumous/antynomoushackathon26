# scripts/verify_zetaris_policy.py
"""M1 acceptance harness: dual-run a fixture scenario against the PRODUCTION
ZetarisPolicySource under two published snapshots (base and variant) and publish the
computed difference. Hybrid by construction: inventory/telemetry/IaC come from the
scenario fixtures, the policy is fetched over the sponsor transport — no application
branch ever swaps policy data based on known input. Runtime bearer/base/org are read
from the environment (or repo .env) only; the settings files carry just object,
snapshot and digest selections and are rejected if they try to smuggle secrets.

Nothing here runs on import; the CLI calls run_acceptance under a __main__ guard.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

ALLOWED_KEYS = {"snapshot_id", "policy_object", "manifest_object", "expected_sha256"}
_SECRET_MARKERS = ("key", "token", "password", "secret", "url", "org", "user", "auth")


def validate_settings(raw) -> dict:
    """Only non-secret selection fields may come from settings files."""
    if not isinstance(raw, dict):
        raise ValueError("malformed settings: expected a JSON object")
    for k in raw:
        lk = str(k).lower()
        if k not in ALLOWED_KEYS:
            if any(m in lk for m in _SECRET_MARKERS):
                raise ValueError("secret-in-settings: runtime bearer/base/org are environment-only")
            raise ValueError("malformed settings: unexpected key")
    missing = ALLOWED_KEYS - set(raw)
    if missing:
        raise ValueError("malformed settings: missing " + ", ".join(sorted(missing)))
    return {k: raw[k] for k in ALLOWED_KEYS}


def _load_env() -> dict:
    env = dict(os.environ)
    dot = _ROOT / ".env"
    if dot.exists():
        for line in dot.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def build_settings(env: dict, sel: dict):
    """Bearer/base/org strictly from env; selection fields from validated settings."""
    from app.sources.zetaris_http import ZetarisError, ZetarisSettings
    try:
        from pydantic import SecretStr
        return ZetarisSettings(
            base_url=env["ZETARIS_REST_URL"],
            api_key=SecretStr(env["ZETARIS_API_KEY"]),
            org_id=env["ZETARIS_ORG_ID"],
            policy_object=sel["policy_object"],
            manifest_object=sel["manifest_object"],
            snapshot_id=sel["snapshot_id"],
            expected_sha256=sel["expected_sha256"],
        )
    except ZetarisError:
        raise
    except Exception:
        raise ZetarisError("configuration", retryable=False) from None


def _default_make_source(settings, scope):
    from app.sources.zetaris_policy import ZetarisPolicySource
    return ZetarisPolicySource(settings)  # production transport, environment-only secrets


def _run_one(label, scenario, request, sel, env, make_source, logs_dir, out_side):
    from app.agents.base import AgentContext
    from app.config import RunConfig
    from app.evidence import EvidenceLedger
    from app.generator import RulesGenerator
    from app.loop import Orchestrator
    from app.report import render_markdown
    from app.sources import get_source
    from app.sources.base import Scope
    from app.state import RunState
    from app.trace import Tracer

    cfg = RunConfig.from_env_and_request({**request, "sample_mode": True})
    upd = {"logs_dir": Path(logs_dir)}
    cfg = cfg.model_copy(update=upd) if hasattr(cfg, "model_copy") else cfg.copy(update=upd)
    scope = Scope(compartment_ids=cfg.compartment_ids, resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=cfg.resolution_minutes)
    sources = {name: get_source(name, cfg, scenario_dir=scenario)
               for name in ("inventory", "telemetry", "iac")}
    sources["policy"] = make_source(build_settings(env, sel), scope)
    stream = io.StringIO()
    state = RunState(cfg.run_id, cfg.logs_dir)
    trace = Tracer(cfg.run_id, cfg.logs_dir, stream=stream)
    try:
        ctx = AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                           state=state, trace=trace, ledger=EvidenceLedger(),
                           scope=scope, scenario_dir=scenario)
        ctx.extras["stdout_stream"] = stream
        report = Orchestrator(ctx, scenario_dir=scenario).run()
    finally:
        trace.close()
        state.close()

    policy = next(s for s in report.sources if s.name == "policy")
    rule_ids = sorted({e.payload.get("rule_id") for e in ctx.ledger._items
                       if e.kind == "rule_hit" and e.payload.get("rule_id")})
    finding_keys = sorted([f.resource_id[-4:], f.finding_class, f.status]
                          for f in report.findings if f.status in {"accepted", "revised"})
    summary = {
        "run_id": cfg.run_id,
        "report_status": report.status,
        "snapshot_id": sel["snapshot_id"],
        "expected_sha256": sel["expected_sha256"],
        "policy_backend": policy.backend,
        "policy_degraded": bool(policy.degraded),
        "provenance_sha256": (policy.provenance.content_sha256
                              if policy.provenance is not None else None),
        "rules_selected": (policy.provenance.row_count if policy.provenance is not None else None),
        "rule_ids": rule_ids,
        "finding_keys": finding_keys,
        "source_outcomes": [{"name": s.name, "backend": s.backend, "degraded": bool(s.degraded)}
                            for s in report.sources],
    }
    out_side.mkdir(parents=True, exist_ok=True)
    (out_side / f"report-{cfg.run_id}.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8")
    (out_side / f"report-{cfg.run_id}.md").write_text(
        render_markdown(report), encoding="utf-8")
    (out_side / f"stdout-{cfg.run_id}.txt").write_text(stream.getvalue(), encoding="utf-8")
    shutil.copyfile(trace.path, out_side / trace.path.name)
    return report, summary


def run_acceptance(*, scenario: Path, base_settings: dict, variant_settings: dict,
                   output_dir: Path, env: dict | None = None,
                   make_source=_default_make_source, logs_dir: Path | None = None) -> dict:
    scenario = Path(scenario)
    base_settings = validate_settings(base_settings)
    variant_settings = validate_settings(variant_settings)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(str(output_dir))
    input_path = _ROOT / "input_examples" / f"{scenario.name}.json"
    if not input_path.exists():
        raise ValueError(f"malformed scenario: no input example {input_path.name}")
    request = json.loads(input_path.read_text())
    env = _load_env() if env is None else env
    logs_dir = Path(logs_dir) if logs_dir is not None else output_dir / "logs"
    output_dir.mkdir(parents=True)

    base_report, base = _run_one("base", scenario, request, base_settings, env,
                                 make_source, logs_dir, output_dir / "base")
    var_report, var = _run_one("variant", scenario, request, variant_settings, env,
                               make_source, logs_dir, output_dir / "variant")

    def _keyset(s):
        return {tuple(k) for k in s["finding_keys"]}
    only_in_base = sorted(_keyset(base) - _keyset(var))
    only_in_variant = sorted(_keyset(var) - _keyset(base))
    rules_removed = sorted(set(base["rule_ids"]) - set(var["rule_ids"]))
    sponsor_acceptance = all(
        s["policy_backend"] == "live" and not s["policy_degraded"]
        and s["provenance_sha256"] == s["expected_sha256"]
        for s in (base, var))
    result = {
        "hybrid": True,
        "scenario": scenario.name,
        "input": str(input_path),
        "base": base,
        "variant": var,
        "changed_finding_keys": {"only_in_base": [list(k) for k in only_in_base],
                                 "only_in_variant": [list(k) for k in only_in_variant]},
        "expected_effect": {
            "rules_removed": rules_removed,
            "effect_observed": bool(rules_removed) and bool(only_in_base)
                                and not only_in_variant,
        },
        "sponsor_acceptance": sponsor_acceptance,
    }
    (output_dir / "acceptance.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--base-settings", type=Path, required=True)
    parser.add_argument("--variant-settings", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    def _read(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    try:
        result = run_acceptance(
            scenario=args.scenario,
            base_settings=_read(args.base_settings),
            variant_settings=_read(args.variant_settings),
            output_dir=args.output_dir)
    except (ValueError, FileExistsError) as e:
        print(f"rejected: {e}")          # message text only; values are never echoed
        return 2
    except Exception as e:               # ZetarisError etc.: class + reason code, no payloads
        from app.sources.zetaris_http import ZetarisError
        if isinstance(e, ZetarisError):
            print(f"rejected: policy configuration ({e.reason})")
        else:
            print(f"error: {type(e).__name__}")
        return 2
    print(json.dumps({"sponsor_acceptance": result["sponsor_acceptance"],
                      "changed_finding_keys": result["changed_finding_keys"],
                      "expected_effect": result["expected_effect"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
