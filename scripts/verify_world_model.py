"""Reproducible offline engine proof; does not claim a live Nightshift runtime."""
from __future__ import annotations

import contextlib
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from app.config import RunConfig
from app.pipeline import run_pipeline
from app.sources import get_source
from app.sources.base import Scope
from app.world_model.ingest import IngestPipelineService
from app.world_model.store import WorldStoreService


@contextlib.contextmanager
def _log_directory(path):
    old=os.environ.get("LOGS_DIR")
    os.environ["LOGS_DIR"]=str(path)
    try:
        yield
    finally:
        if old is None:os.environ.pop("LOGS_DIR",None)
        else:os.environ["LOGS_DIR"]=old


def _run(scenario, output, name):
    with _log_directory(output / "private" / name), (output / "private" / (name+".stdout.jsonl")).open("w") as stream:
        with contextlib.redirect_stdout(stream):
            report,_=run_pipeline({"sample_mode":True},scenario_dir=scenario)
    (output / (name+"-report.json")).write_text(report.model_dump_json(by_alias=True,indent=2)+"\n")
    shutil.copyfile(report.trace_path,output / (name+"-trace.jsonl"))
    return report


def run_world_acceptance(output_dir: Path) -> dict:
    output=Path(output_dir)
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    (output / "private").mkdir(mode=0o700)
    scenario=Path("data/scenarios/example_1")
    base=_run(scenario,output,"base")
    world=base.summary["integrations"]["meterless_world_model"]
    events=[json.loads(line) for line in Path(base.trace_path).read_text().splitlines()]
    contexts=[json.loads(event["output_summary"]) for event in events if event["action"] == "world_context"]
    selected=[c["selection"] for c in contexts if c["selection"]["telemetry_snapshot"]]
    windows=sorted({s["lookback_hours"] for s in selected})
    consumers=sorted({event["agent_name"] for event in events if event["action"] == "world_context"})
    store=WorldStoreService(Path(base.trace_path).parent / world["store"])
    try:
        scope_args=dict(run_id=base.run_id,namespace=world["namespace"])
        before=store.counts(**scope_args)
        ingest=IngestPipelineService(store,**scope_args)
        config=RunConfig(sample_mode=True)
        scope=Scope(compartment_ids=[],resource_types=config.resource_types,lookback_hours=168,resolution_minutes=5)
        for source in ("inventory","iac","policy"):
            ingest.ingest(source,get_source(source,config,scenario_dir=scenario).fetch(scope))
        after=store.counts(**scope_args)
        base_policy_ids=store.snapshot(**scope_args,snapshot_id=world["sources"]["policy"]["snapshots"][0]).observation_ids
        exact=all(any(o.external_key == selection["resource_id"]
              and o.lookback_hours == selection["lookback_hours"]
              and o.resolution_minutes == selection["resolution_minutes"]
              for o in store.read(**scope_args,snapshot_id=selection["telemetry_snapshot"]))
              for selection in selected)
    finally:
        store.close()
    variant_scenario=output / "private" / "variant-scenario"
    shutil.copytree(scenario,variant_scenario)
    policy_file=variant_scenario / "policy.json"
    policy=json.loads(policy_file.read_text())
    policy["rules"]=[r for r in policy["rules"] if r["rule_id"] != "R-1"]
    policy_file.write_text(json.dumps(policy,indent=2)+"\n")
    variant=_run(variant_scenario,output,"variant")
    variant_world=variant.summary["integrations"]["meterless_world_model"]
    variant_store=WorldStoreService(Path(variant.trace_path).parent / variant_world["store"])
    try:
        variant_policy_ids=variant_store.snapshot(run_id=variant.run_id,namespace=variant_world["namespace"],
            snapshot_id=variant_world["sources"]["policy"]["snapshots"][0]).observation_ids
    finally:
        variant_store.close()
    def semantic(finding):
        data=finding.model_dump(by_alias=True)
        return {k:data[k] for k in ("resource_id","resource_class","class","claim","impact","status","confidence","history")}
    before_findings={json.dumps(semantic(f),sort_keys=True) for f in base.findings}
    after_findings={json.dumps(semantic(f),sort_keys=True) for f in variant.findings}
    removed=[json.loads(value) for value in sorted(before_findings-after_findings)]
    added=[json.loads(value) for value in sorted(after_findings-before_findings)]
    causal={"policy_observations_changed":base_policy_ids != variant_policy_ids,
        "only_r1_finding_removed":len(removed) == 1 and removed[0]["resource_class"] == "block_volume"
            and removed[0]["status"] == "accepted" and not added,
        "removed":removed,"added":added}
    guards={"run_success":base.status == "success" and variant.status == "success","world_used":world["status"] == "used",
        "actual_consumers":{"Scout","Skeptic"} <= set(consumers),"dedup":before == after,
        "both_windows":windows == [168,744],"exact_windows":bool(selected) and exact,
        "causal_policy":causal["policy_observations_changed"] and causal["only_r1_finding_removed"]}
    result={"engine_acceptance":all(guards.values()),"guards":guards,"consumers":consumers,
        "manifest":world,"causal":causal,"dedup":{"before":before,"after":after},"telemetry_windows":windows,
        "selections":selected,"nightshift_verified":False,"live_tenancy_audit":False}
    (output / "acceptance.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result



def export_proof(output: Path, target: Path) -> None:
    from scripts.mask_ocids import mask_text
    target.mkdir(parents=True,exist_ok=False)
    records={}
    names=["acceptance.json","base-report.json","variant-report.json","base-trace.jsonl","variant-trace.jsonl"]
    for name in names:
        original=(output / name).read_bytes()
        rendered=mask_text(original.decode("utf-8"))[0]
        if name.endswith("-report.json"):
            report=json.loads(rendered)
            report["trace_path"]=str(target / name.replace("-report.json","-trace.jsonl"))
            report["report_markdown_path"]=None
            rendered=json.dumps(report,indent=2,ensure_ascii=False)+"\n"
        destination=target / name
        destination.write_text(rendered,encoding="utf-8")
        records[name]={"raw_sha256":hashlib.sha256(original).hexdigest(),
            "export_sha256":hashlib.sha256(destination.read_bytes()).hexdigest()}
    (target / "export.json").write_text(json.dumps({"kind":"masked publication copies",
        "raw_directory_name":output.name,"files":records},indent=2,sort_keys=True)+"\n")


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",required=True,type=Path)
    parser.add_argument("--export-dir",type=Path)
    args=parser.parse_args(argv)
    result=run_world_acceptance(args.output_dir)
    if args.export_dir:
        export_proof(args.output_dir,args.export_dir)
    print(json.dumps({"engine_acceptance":result["engine_acceptance"],"output_dir":str(args.output_dir)}))
    return 0 if result["engine_acceptance"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
