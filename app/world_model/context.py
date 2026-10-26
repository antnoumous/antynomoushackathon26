from __future__ import annotations

from app.analysis import match_iac
from app.models import Resource, IaCDeclaration, PolicyRule, MetricSeries
from dataclasses import asdict
from app.world_model.contracts import ContextSelection, ResourceContext, WorldError
from app.world_model.identity import observation_id
from app.world_model.store import WorldStoreService


class ContextBuilderService:
    def __init__(self, store: WorldStoreService, *, run_id: str, namespace: str,
                 max_records: int = 256) -> None:
        self.store, self.run_id, self.namespace = store, run_id, namespace
        self.max_records = max_records

    def build(self, *, resource_id: str, inventory_snapshot: str, iac_snapshot: str,
              policy_snapshot: str, telemetry_snapshot: str | None,
              lookback_hours: int, resolution_minutes: int) -> ResourceContext:
        scope = dict(run_id=self.run_id, namespace=self.namespace)
        snapshots = {"inventory": inventory_snapshot, "iac": iac_snapshot, "policy": policy_snapshot}
        if telemetry_snapshot:
            snapshots["telemetry"] = telemetry_snapshot
        statuses = {}
        for source, sid in snapshots.items():
            ref = self.store.snapshot(**scope, snapshot_id=sid)
            if ref.source != source:
                raise WorldError("context")
            statuses[source] = ref
        reasons = [source + ":incomplete" for source, ref in statuses.items() if not ref.complete]
        complete = not reasons
        inventory = self.store.read(**scope, snapshot_id=inventory_snapshot)
        matches = [o for o in inventory if o.external_key == resource_id]
        if len(matches) != 1:
            raise WorldError("context")
        resource_observation = matches[0]
        resource = Resource(**resource_observation.payload)
        iac = self.store.read(**scope, snapshot_id=iac_snapshot)
        declarations = sorted([IaCDeclaration(**o.payload) for o in iac], key=lambda d: d.address)
        match_rule, declaration = match_iac(resource, declarations)
        policy = self.store.read(**scope, snapshot_id=policy_snapshot)
        rules = tuple(sorted([PolicyRule(**o.payload) for o in policy], key=lambda r: r.rule_id))
        selected = [resource_observation, *policy]
        if declaration:
            selected.extend(o for o in iac if o.external_key == declaration.address)
        series = None
        if telemetry_snapshot:
            telemetry = self.store.read(**scope, snapshot_id=telemetry_snapshot)
            exact = [o for o in telemetry if o.external_key == resource_id
                     and o.lookback_hours == lookback_hours and o.resolution_minutes == resolution_minutes]
            if len(exact) == 1:
                series = MetricSeries(**exact[0].payload)
                selected.append(exact[0])
            else:
                complete = False
                reasons.append("telemetry:resource_or_window_mismatch")
        if not statuses["iac"].complete:
            declaration, match_rule = None, None
        if not statuses["policy"].complete:
            rules = ()
        if len(selected) > self.max_records:
            complete = False
            reasons.append("context_limit")
            selected, rules, declaration, match_rule, series = [resource_observation], (), None, None, None
        ids = tuple(sorted(observation_id(self.namespace, o) for o in selected))
        selection = ContextSelection(resource_id, inventory_snapshot, iac_snapshot,
            policy_snapshot, telemetry_snapshot, ids, lookback_hours, resolution_minutes)
        return ResourceContext(selection, resource, declaration, match_rule, rules, series, complete,
            tuple(reasons) if reasons else
            ("resource:exact", "iac:" + (match_rule or "absent"), "policy:pinned"))

    def replay(self, selection: ContextSelection) -> ResourceContext:
        fields = asdict(selection)
        ids = fields.pop("observation_ids")
        context = self.build(**fields)
        if context.selection.observation_ids != ids:
            raise WorldError("context")
        return context
