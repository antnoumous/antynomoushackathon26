from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
import re
from pathlib import Path

from app.world_model.contracts import WorldError
from app.world_model.context import ContextBuilderService
from app.world_model.identity import canonical_json
from app.world_model.ingest import IngestPipelineService
from app.world_model.store import WorldStoreService


def record_failure(ctx, error):
    failures = ctx.extras.setdefault("world_failures", [])
    if error.category not in failures:
        failures.append(error.category)
        ctx.trace.emit(agent_name="Scout",action="world_unavailable",input_summary="World Model",
            output_summary="world:" + error.category,status="partial")


def world_manifest(ctx):
    if ctx.world is not None:
        return ctx.world.manifest()
    return {"status":"failed" if ctx.extras.get("world_failures") else "not_used",
        "consumers":[],"failures":list(ctx.extras.get("world_failures",[]))}


class WorldRuntime:
    def __init__(self, ctx, *, scenario_dir: Path | None = None):
        self.ctx, self.scenario_dir = ctx, scenario_dir or ctx.scenario_dir
        if not re.fullmatch(r"[A-Za-z0-9_-]+", ctx.config.run_id):
            raise WorldError("configuration")
        self.store = WorldStoreService(ctx.trace.path.parent / ("world-"+ctx.config.run_id) / "world.sqlite3")
        self.namespace = None
        self.refs, self.pins = {}, {}
        self.sources = {}
        self.consumers = set()
        self.context_calls = 0
        self.failures = ctx.extras.setdefault("world_failures", [])
        self._closed, self._cached = False, {}

    @classmethod
    def from_context(cls, ctx, *, scenario_dir=None):
        return cls(ctx, scenario_dir=scenario_dir)

    def ingest_hydration(self, results):
        from app.models import Resource
        from pydantic import ValidationError
        inventory = results.get("inventory")
        try:
            resources = tuple(Resource.model_validate(row) for row in inventory.records) if inventory is not None else ()
            canonical_json([resource.model_dump() for resource in resources]).encode("utf-8", errors="strict")
        except (ValidationError, TypeError, ValueError):
            raise WorldError("schema") from None
        body = {k: {"records": v.records, "backend": v.backend} if v else None for k,v in results.items()}
        digest = hashlib.sha256(canonical_json(body).encode()).hexdigest()
        inventory = results.get("inventory")
        if self.ctx.config.sample_mode or inventory is None or inventory.backend == "fixture":
            name = self.scenario_dir.name if self.scenario_dir else "default"
            self.namespace = "scenario:" + name + ":" + digest
        else:
            regions = {resource.resource_id.split(".")[3] for resource in resources
                       if len(resource.resource_id.split(".")) > 3 and resource.resource_id.split(".")[3]}
            region = os.environ.get("OCI_REGION") or (next(iter(regions)) if len(regions) == 1 else None)
            compartments = sorted(set(self.ctx.config.compartment_ids) |
                                  {resource.compartment_id for resource in resources if resource.compartment_id})
            if (not region or not compartments or any(
                    not key.startswith(("ocid1.compartment.","ocid1.tenancy.")) or "••••" in key
                    for key in compartments)):
                raise WorldError("configuration")
            self.namespace = "live:" + hashlib.sha256(canonical_json({"region":region,"compartments":compartments}).encode()).hexdigest()
        self.ingest = IngestPipelineService(self.store, run_id=self.ctx.config.run_id, namespace=self.namespace)
        self.builder = ContextBuilderService(self.store, run_id=self.ctx.config.run_id, namespace=self.namespace)
        for source in ("inventory", "iac", "policy"):
            result = results.get(source)
            ref = (self.ingest.ingest(source, result) if result is not None else
                self.store.put_batch(run_id=self.ctx.config.run_id,namespace=self.namespace,
                    source=source,observations=[],complete=False))
            self.refs[source+"_snapshot"] = ref.snapshot_id
            self.sources[source] = {"backends":[result.backend] if result else ["none"],
                "complete":ref.complete,"degraded":ref.degraded,"snapshots":[ref.snapshot_id]}
            self.ctx.trace.emit(agent_name="Planner",action="world_ingest",input_summary=source,
                output_summary=json.dumps(asdict(ref),sort_keys=True),status="success" if ref.complete else "partial")

    def ingest_series(self, resource_id, series, *, backend, degraded, source_version=None):
        source_id = series.resource_id
        if source_id != resource_id:
            from scripts.mask_ocids import mask_text
            wanted = mask_text(resource_id)[0]
            if backend != "fixture" or mask_text(source_id)[0] != wanted:
                raise WorldError("provenance")
            inventory = self.store.read(run_id=self.ctx.config.run_id,namespace=self.namespace,
                snapshot_id=self.refs["inventory_snapshot"])
            targets = [o.external_key for o in inventory if mask_text(o.external_key)[0] == wanted]
            if targets != [resource_id]:
                raise WorldError("context")
            series = series.model_copy(update={"resource_id":resource_id})
        ref = self.ingest.ingest_series(resource_id,series,backend=backend,degraded=degraded,
            source_version=source_version,source_resource_id=source_id if source_id != resource_id else None)
        previous = self.sources.get("telemetry",{})
        self.sources["telemetry"] = {"backends":sorted(set(previous.get("backends",[])) | {backend}),
            "complete":True,"degraded":degraded or previous.get("degraded",False),
            "snapshots":sorted(set(previous.get("snapshots",[])) | {ref.snapshot_id})}
        self.ctx.trace.emit(agent_name="Scout",action="world_ingest",input_summary="telemetry",
            output_summary=json.dumps(asdict(ref),sort_keys=True),status="degraded" if degraded else "success")
        return ref

    def _record(self, context, consumer):
        self.consumers.add(consumer)
        self.context_calls += 1
        self.ctx.trace.emit(agent_name=consumer,action="world_context",input_summary=consumer,
            output_summary=json.dumps({"selection":asdict(context.selection),"complete":context.complete,
                "reasons":context.reasons},sort_keys=True),status="success" if context.complete else "partial")
        return context

    def context(self, resource_id, lookback_hours, resolution_minutes, telemetry_snapshot=None):
        if len(self.refs) != 3:
            raise WorldError("context")
        return self._record(self.builder.build(resource_id=resource_id,**self.refs,
            telemetry_snapshot=telemetry_snapshot,lookback_hours=lookback_hours,
            resolution_minutes=resolution_minutes), "Scout")

    def pin(self, candidate_id, context):
        if not context.complete or (candidate_id in self.pins and self.pins[candidate_id] != context.selection):
            raise WorldError("context")
        self.pins[candidate_id] = context.selection
        self.ctx.state.append("world_pin", {"candidate_id":candidate_id,"selection":asdict(context.selection)})

    def for_candidate(self, candidate_id):
        if candidate_id not in self.pins:
            raise WorldError("context")
        return self._record(self.builder.replay(self.pins[candidate_id]), "Skeptic")

    def manifest(self):
        if not self._closed:
            try:
                self._cached = self.store.counts(run_id=self.ctx.config.run_id,namespace=self.namespace or "")
            except WorldError as error:
                record_failure(self.ctx,error)
        return {"status":"failed" if self.failures else "used" if self.consumers else "wired",
            "services":["WorldStoreService","IngestPipelineService","ContextBuilderService"],
            "namespace":self.namespace,"consumers":sorted(self.consumers),"counts":dict(self._cached),
            "store":str(self.store.path.relative_to(self.ctx.trace.path.parent)),
            "sources":json.loads(json.dumps(self.sources)),
            "contexts":self.context_calls,"failures":list(self.failures)}

    def close(self):
        if not self._closed:
            try:
                self.manifest()
            finally:
                self.store.close()
                self._closed = True
