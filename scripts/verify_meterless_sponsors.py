"""Hybrid sponsor acceptance; injected adapters prove contracts, not a real runtime."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import io
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_zetaris_policy import validate_settings, build_settings


def _default_source(settings, scope):
    from app.sources.zetaris_policy import ZetarisPolicySource
    return ZetarisPolicySource(settings)


def _default_generator(env):
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings, MeterlessError, discover
    from app.providers.meterless_transport import request_json
    settings = MeterlessSettings.from_env(env)
    readiness = discover(settings, transport=request_json, timeout_s=10.0)
    if readiness.state != "online":
        raise MeterlessError(readiness.state)
    generator = MeterlessGenerator(settings)
    generator.runtime_readiness = asdict(readiness)
    return generator


def _run_one(label, scenario, selection, env, make_source, make_generator, output):
    from app.agents.base import AgentContext
    from app.config import RunConfig
    from app.evidence import EvidenceLedger
    from app.generator import generator_diagnostics
    from app.loop import Orchestrator
    from app.sources import get_source
    from app.sources.base import Scope
    from app.state import RunState
    from app.trace import Tracer
    cfg = RunConfig(sample_mode=True, logs_dir=output / "private" / label)
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=cfg.resolution_minutes)
    sources = {name: get_source(name, cfg, scenario_dir=scenario) for name in ("inventory", "iac", "telemetry")}
    sources["policy"] = make_source(build_settings(env, selection), scope)
    generator = make_generator(env)
    state = RunState(cfg.run_id, cfg.logs_dir)
    trace = Tracer(cfg.run_id, cfg.logs_dir, stream=io.StringIO())
    try:
        ctx = AgentContext(config=cfg, sources=sources, generator=generator, state=state,
                           trace=trace, ledger=EvidenceLedger(), scope=scope, scenario_dir=scenario)
        report = Orchestrator(ctx, scenario_dir=scenario).run()
        report.summary["execution_mode"] = "hybrid"
        events = [json.loads(line) for line in trace.path.read_text().splitlines()]
        policy = next(item for item in report.sources if item.name == "policy")
        provider = generator_diagnostics(generator)
        recorder = getattr(generator, "recorder", None)
        outcomes = [asdict(row) for row in recorder.outcomes()] if recorder is not None else []
        facts = {"run_id": cfg.run_id, "status": report.status, "provider": provider,
                 "outcomes": outcomes, "readiness": getattr(generator, "runtime_readiness", {"state":"unverified","model_ids":[]}), "source_outcomes": [s.model_dump(mode="json") for s in report.sources],
                 "world": report.summary["integrations"].get("meterless_world_model", {}),
                 "finding_rules": {f.finding_id: sorted(ctx.state.facts["candidates"][f.finding_id].matched_rule_ids)
                                   for f in report.findings}}
        facts["policy_ok"] = (policy.backend == "live" and not policy.degraded and policy.provenance is not None
                              and policy.provenance.content_sha256 == selection["expected_sha256"]
                              and policy.provenance.snapshot_id == selection["snapshot_id"]
                              and policy.provenance.provider == "zetaris" and policy.provenance.complete)
        (output / (label+"-report.json")).write_text(report.model_dump_json(by_alias=True, indent=2)+"\n")
        shutil.copyfile(trace.path, output / (label+"-trace.jsonl"))
        (output / (label+"-outcomes.json")).write_text(json.dumps(facts,indent=2,sort_keys=True)+"\n")
        return report, facts, events
    finally:
        trace.close()
        state.close()


def _world_ok(facts, events):
    contexts = [event for event in events if event["action"] == "world_context"]
    return (facts["world"].get("status") == "used" and bool(contexts)
        and {"Scout", "Skeptic"} <= {event["agent_name"] for event in contexts}
        and all(json.loads(event["output_summary"])["complete"] for event in contexts))


def _provider_ok(facts, events):
    rows = facts["outcomes"]
    observed = [json.loads(event["output_summary"]) for event in events if event["action"] == "provider_result"]
    return (bool(rows) and rows == observed
        and {"finding_claim", "verdict_reason", "run_summary"} <= {row["schema_name"] for row in rows}
        and all(row["attempted"] and not row["fallback"] and row["category"] is None
            and row["configured_provider"] == "meterless" and row["actual_backend"] == "meterless"
            and row["model"] == "meterless/local" for row in rows)
        and facts["provider"]["attempts"] == len(rows) == facts["provider"]["successes"]
        and facts["provider"]["fallbacks"] == 0)


def _semantic(finding, facts):
    # Text is intentionally excluded: different model wording is not a changed financial result.
    data = finding.model_dump(by_alias=True)
    return {**{key:data[key] for key in ("resource_id", "resource_class", "class", "impact", "status")},
            "rules": facts["finding_rules"][finding.finding_id],
            "verdicts": [{"round":h.round,"verdict":h.verdict} for h in finding.history]}


def run_acceptance(*, scenario: Path, base_settings: dict, variant_settings: dict,
                   output_dir: Path, env: dict, make_source=None, make_generator=None) -> dict:
    selections = [validate_settings(value) for value in (base_settings, variant_settings)]
    production = make_source is None and make_generator is None
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / "private").mkdir(mode=0o700)
    results = [_run_one(label, Path(scenario), selection, env, make_source or _default_source,
                       make_generator or _default_generator, output)
               for label, selection in zip(("base", "variant"), selections)]
    before = {json.dumps(_semantic(f,results[0][1]),sort_keys=True) for f in results[0][0].findings}
    after = {json.dumps(_semantic(f,results[1][1]),sort_keys=True) for f in results[1][0].findings}
    removed = [json.loads(value) for value in sorted(before-after)]
    added = [json.loads(value) for value in sorted(after-before)]
    guards = {"policy":all(facts["policy_ok"] for _,facts,_ in results),
              "world":all(_world_ok(facts, events) for _,facts,events in results),
              "provider":all(_provider_ok(facts, events) for _,facts,events in results),
              "run_success":all(report.status == "success" for report,_,_ in results),
              "causal":len(removed) == 1 and not added and removed[0]["resource_class"] == "block_volume"
                  and removed[0]["class"] == "cost_waste" and removed[0]["status"] == "accepted"
                  and removed[0]["rules"] == ["R-1"]}
    passed = all(guards.values())
    result = {"hybrid":True, "execution":"production_adapters" if production else "injected_contract_test",
              "acceptance_checks_passed":passed, "sponsor_acceptance":passed and production,
              "nightshift_verified":passed and production, "live_tenancy_audit":False,
              "guards":guards, "base":results[0][1], "variant":results[1][1],
              "causal":{"removed":removed,"added":added}}
    (output / "acceptance.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result


def export_proof(output: Path, target: Path, *, runtime_env: dict) -> None:
    """Fail closed on known credentials before creating any masked publication copy."""
    import hashlib
    from scripts.mask_ocids import mask_text
    from app.providers.meterless_settings import MeterlessError
    output, target = Path(output), Path(target)
    secrets = tuple(runtime_env.get(key) for key in ("METERLESS_TOKEN", "ZETARIS_API_KEY"))
    if any(not isinstance(value, str) or not value.strip() for value in secrets):
        raise MeterlessError("configuration")

    def contains_secret(value):
        if isinstance(value, str):
            return any(secret in value for secret in secrets)
        if isinstance(value, dict):
            return any(contains_secret(key) or contains_secret(item) for key, item in value.items())
        if isinstance(value, list):
            return any(contains_secret(item) for item in value)
        return False

    names = ["acceptance.json", *[side+suffix for side in ("base", "variant")
             for suffix in ("-report.json", "-trace.jsonl", "-outcomes.json")]]
    originals = {name: (output / name).read_bytes() for name in names}
    for name, original in originals.items():
        text = original.decode("utf-8")
        decoded = ([json.loads(line) for line in text.splitlines() if line.strip()]
                   if name.endswith(".jsonl") else json.loads(text))
        if contains_secret(text) or contains_secret(decoded):
            raise MeterlessError("schema")
    target.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, original in originals.items():
        rendered = mask_text(original.decode("utf-8"))[0]
        if name.endswith("-report.json"):
            report = json.loads(rendered)
            report["trace_path"] = str(target / name.replace("-report.json", "-trace.jsonl"))
            report["report_markdown_path"] = None
            rendered = json.dumps(report, indent=2, ensure_ascii=False)+chr(10)
        path = target / name
        path.write_text(rendered, encoding="utf-8")
        records[name] = {"raw_sha256": hashlib.sha256(original).hexdigest(),
                         "export_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (target / "export.json").write_text(json.dumps({"kind":"masked publication copies", "files":records},
                                                   indent=2, sort_keys=True)+chr(10))


def main(argv=None) -> int:
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--base-settings", type=Path)
    parser.add_argument("--variant-settings", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--stdin-env", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.stdin_env:
            from scripts.run_meterless_remote import read_runtime_payload
            runtime = read_runtime_payload(sys.stdin.buffer)
            env, base, variant = runtime["env"], runtime["base_settings"], runtime["variant_settings"]
        else:
            if args.base_settings is None or args.variant_settings is None:
                raise ValueError("both snapshot settings files are required")
            env, base, variant = dict(os.environ), json.loads(args.base_settings.read_text()), json.loads(args.variant_settings.read_text())
        result = run_acceptance(scenario=args.scenario, base_settings=base,
            variant_settings=variant, output_dir=args.output_dir, env=env)
    except Exception as exc:
        print(json.dumps({"sponsor_acceptance":False,"error_class":type(exc).__name__}))
        return 2
    print(json.dumps({key:result[key] for key in ("sponsor_acceptance","acceptance_checks_passed","execution")}))
    return 0 if result["sponsor_acceptance"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
