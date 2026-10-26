from __future__ import annotations

from pydantic import ValidationError
from app.models import Resource, IaCDeclaration, PolicyRule, MetricSeries
from app.sources.base import SourceResult
from app.world_model.contracts import Observation, SnapshotRef, WorldError
from app.world_model.identity import canonical_json
from app.world_model.store import WorldStoreService


class IngestPipelineService:
    def __init__(self, store: WorldStoreService, *, run_id: str, namespace: str) -> None:
        self.store, self.run_id, self.namespace = store, run_id, namespace

    def ingest(self, source: str, result: SourceResult, *, complete: bool = True) -> SnapshotRef:
        models = {"inventory": (Resource, "resource", "resource_id"),
            "iac": (IaCDeclaration, "declaration", "address"),
            "policy": (PolicyRule, "policy", "rule_id")}
        if source not in models or result.source != source:
            raise WorldError("provenance")
        model, entity_type, key = models[source]
        provenance = result.provenance
        lineage = provenance.model_dump(exclude={"fetched_at_utc"}) if provenance else None
        version = canonical_json(lineage) if lineage else None
        staged = []
        try:
            for row in result.records:
                item = model.model_validate(row)
                payload = item.model_dump()
                if lineage:
                    payload["_provenance"] = lineage
                staged.append(Observation.from_payload(entity_type=entity_type,
                    external_key=getattr(item, key), source=source, backend=result.backend,
                    payload=payload, source_version=version,
                    measured_at=provenance.observed_at_utc if provenance else None,
                    fetched_at=provenance.fetched_at_utc if provenance else None))
        except (ValidationError, TypeError, ValueError):
            raise WorldError("schema") from None
        return self.store.put_batch(run_id=self.run_id, namespace=self.namespace, source=source,
            observations=staged, complete=complete and (provenance.complete if provenance else True),
            degraded=result.degraded)

    def ingest_series(self, resource_id: str, series: MetricSeries, *, backend: str,
                      degraded: bool, source_version: str | None = None) -> SnapshotRef:
        if series.resource_id != resource_id:
            raise WorldError("provenance")
        item = Observation.from_payload(entity_type="telemetry", external_key=resource_id,
            source="telemetry", backend=backend, payload=series.model_dump(),
            source_version=source_version, lookback_hours=series.lookback_hours,
            resolution_minutes=series.resolution_minutes)
        return self.store.put_batch(run_id=self.run_id, namespace=self.namespace, source="telemetry",
            observations=[item], complete=True, degraded=degraded)
