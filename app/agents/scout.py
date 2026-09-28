from __future__ import annotations

import json
from pathlib import Path

from app.agents.base import Agent
from app.analysis import (NO_TELEMETRY_STATS, match_iac, monthly_cost, qualifying_rules,
                          requires_telemetry, stats_from_series)
from app.models import (Assignment, Candidate, IaCDeclaration, MetricSeries, PolicyRule, Resource,
                        SourceStatus, Undetermined)
from app.sources.base import Scope


class Scout(Agent):
    name = "Scout"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._undetermined: list[Undetermined] = []
        self._source_status: dict[str, SourceStatus] = {}

    def source_statuses(self) -> list[SourceStatus]:
        return list(self._source_status.values())

    # --- hydrating the shared state once per run -------------------------------------------
    def hydrate(self) -> None:
        inventory = self.ctx.sources["inventory"].fetch(self.ctx.scope)
        for record in inventory.records:
            resource = Resource(**record)
            self.ctx.state.facts["resources"][resource.resource_id] = resource

        iac = self.ctx.sources["iac"].fetch(self.ctx.scope)
        self.ctx.state.facts["declarations"] = [IaCDeclaration(**d) for d in iac.records]

        policy = self.ctx.sources["policy"].fetch(self.ctx.scope)
        self.ctx.state.facts["rules"] = [PolicyRule(**r) for r in policy.records]

        self.ctx.state.append("hydrate", {
            "resources": len(self.ctx.state.facts["resources"]),
            "declarations": len(self.ctx.state.facts["declarations"]),
            "rules": len(self.ctx.state.facts["rules"]),
        })
        self._emit("hydrate", input_summary="inventory, iac, policy",
                   output_summary=f"{len(self.ctx.state.facts['resources'])} resources, "
                                  f"{len(self.ctx.state.facts['declarations'])} declarations",
                   confidence=1.0)

    def _series_for(self, resource_id: str, lookback_hours: int) -> MetricSeries | None:
        scope = Scope(compartment_ids=self.ctx.scope.compartment_ids,
                      resource_types=self.ctx.scope.resource_types,
                      lookback_hours=lookback_hours,
                      resolution_minutes=self.ctx.scope.resolution_minutes)
        result = self._fetch_with_recovery("telemetry", scope)
        if result is None:
            return None
        # A live inventory carries real OCIDs while a fixture fallback carries masked ones; the
        # join compares both masked (idempotent, so masked-vs-masked matches unchanged) or a
        # mixed degraded run would abstain on every resource while holding usable series.
        from scripts.mask_ocids import mask_text
        wanted = mask_text(resource_id)[0]
        for record in result.records:
            if mask_text(record["resource_id"])[0] == wanted:
                return MetricSeries(**record)
        return None

    def _fetch_with_recovery(self, name: str, scope: Scope):
        """One retry, then the fixture backend, then None. Never invents records."""
        source = self.ctx.sources[name]
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                result = source.fetch(scope)
                self._source_status[name] = SourceStatus(name=name, backend=result.backend)
                return result
            except Exception as exc:                      # noqa: BLE001 - logged, then degraded
                last_error = exc
                self._emit("source_call_failed", input_summary=f"{name} attempt {attempt}",
                           output_summary=f"{type(exc).__name__}: {exc}", status="retrying",
                           retry_count=attempt - 1)
        # The docstring promised the fixture backend; the Planner's hydrate path has it, and a
        # per-resource telemetry fetch must degrade the same way or a mid-run API failure would
        # silently downgrade every cost rule to abstain (found on the lab's first degraded run).
        if self.ctx.scenario_dir is not None:
            try:
                from app.sources import get_source
                fallback = get_source(name, self.ctx.config.model_copy(
                    update={"sample_mode": True}), scenario_dir=self.ctx.scenario_dir)
                result = fallback.fetch(scope)
            except Exception as exc:                      # noqa: BLE001 - a missing fixture degrades
                self._emit("source_unavailable", input_summary=name,
                           output_summary=f"fallback failed: {type(exc).__name__}: {exc}",
                           status="failed", retry_count=1)
                self._source_status[name] = SourceStatus(
                    name=name, backend="none", degraded=True,
                    reason=f"fallback failed: {exc}")
                return None
            self._emit("source_degraded", input_summary=name,
                       output_summary="fell back to fixture data", status="degraded",
                       retry_count=1)
            self._source_status[name] = SourceStatus(name=name, backend="fixture",
                                                     degraded=True, reason=str(last_error))
            return result
        self._emit("source_call_failed", input_summary=name,
                   output_summary="both attempts failed; source treated as unavailable",
                   status="failed", retry_count=1)
        self._source_status[name] = SourceStatus(name=name, backend="none", degraded=True,
                                                 reason="both attempts failed")
        return None

    def investigate(self, assignment: Assignment) -> list[Candidate]:
        candidates: list[Candidate] = []
        resources: dict[str, Resource] = self.ctx.state.facts["resources"]
        declarations: list[IaCDeclaration] = self.ctx.state.facts["declarations"]
        rules: list[PolicyRule] = self.ctx.state.facts["rules"]

        examined: set[str] = self.ctx.state.facts.setdefault("examined", set())
        for index, resource_id in enumerate(assignment.resource_ids):
            if self.ctx.out_of_time():
                # The budget is checked before each resource, not only between rounds, so a slow
                # round cannot outrun the cap it is running under.
                skipped = assignment.resource_ids[index:]
                for remaining in skipped:
                    self._undetermined.append(Undetermined(
                        resource_id=remaining,
                        reason="the run's wall-clock budget was exhausted before this resource "
                               "was examined"))
                self._emit("abstain", round=assignment.round, input_summary="wall clock",
                           output_summary=f"{len(skipped)} resource(s) not examined",
                           status="capped", confidence=1.0)
                break
            examined.add(resource_id)
            resource = resources[resource_id]
            attached = getattr(resource, "attached", None)

            is_compute = resource.resource_class == "compute_instance"
            series = (self._series_for(resource_id, assignment.lookback_hours)
                      if is_compute else None)
            # No telemetry means no CPU figure may be published at all. `sufficient: False`
            # suppresses every cost rule below and routes this resource to `undetermined`.
            stats = stats_from_series(series) if series is not None else dict(NO_TELEMETRY_STATS)

            match_rule, declaration = match_iac(resource, declarations)
            absent = declaration is None
            if resource.resource_class == "compute_instance" and absent:
                self._emit("flag_unattributed", round=assignment.round, target_agent="Skeptic",
                           input_summary=resource.display_name,
                           output_summary="no IaC declaration matched",
                           confidence=0.75)
            fired = qualifying_rules(resource, stats, attached, absent, rules)

            if is_compute and not stats["sufficient"]:
                reason = (series.insufficient_reason or "insufficient telemetry coverage"
                          if series is not None
                          else "no telemetry was retrieved for this resource, so no CPU-based "
                               "conclusion could be drawn")
                self._undetermined.append(Undetermined(resource_id=resource_id, reason=reason))
                summary_text = (f"insufficient coverage ({stats['coverage_ratio']:.2f}); "
                                f"no cost finding raised") if series is not None else \
                               "no telemetry retrieved; no cost finding raised"
                self._emit("abstain", round=assignment.round,
                           input_summary=f"{resource.display_name} telemetry",
                           output_summary=summary_text,
                           status="abstained", confidence=1.0)

            for rule in fired:
                # A verdict that rests on CPU statistics needs the window behind it. A verdict that
                # rests on the resource's shape — detached, unattached, undeclared — needs no
                # telemetry, so it still stands when telemetry is missing.
                if requires_telemetry(rule) and not stats["sufficient"]:
                    continue

                evidence = [
                    self.ctx.evidence(source="inventory", kind="resource",
                                      resource_id=resource_id,
                                      summary=f"{resource.display_name} {resource.shape} "
                                              f"{resource.ocpus} OCPU/{resource.memory_gb} GB "
                                              f"{resource.lifecycle_state}",
                                      payload={"shape": resource.shape, "ocpus": resource.ocpus,
                                               "memory_gb": resource.memory_gb,
                                               "size_gb": resource.size_gb,
                                               "tags": resource.tags,
                                               "lifecycle_state": resource.lifecycle_state}),
                ]
                if series is not None:
                    evidence.append(self.ctx.evidence(
                        source="telemetry", kind="cpu_stats", resource_id=resource_id,
                        summary=f"mean {stats['mean']}% peak {stats['peak']}% over "
                                f"{series.coverage_hours:.0f}h",
                        payload={**stats, "lookback_hours": series.lookback_hours,
                                 "resolution_minutes": series.resolution_minutes,
                                 "coverage_hours": series.coverage_hours}))
                if declaration is not None:
                    evidence.append(self.ctx.evidence(
                        source="iac", kind="declaration", resource_id=resource_id,
                        summary=f"{declaration.address} in {declaration.file_path} "
                                f"({declaration.commit_message})",
                        payload=declaration.model_dump()))
                if absent and resource.resource_class == "compute_instance":
                    evidence.append(self.ctx.evidence(
                        source="iac", kind="absent", resource_id=resource_id,
                        summary="no matching declaration (tag, name, or normalised name)",
                        payload={"match_rule": None}))
                evidence.append(self.ctx.evidence(
                    source="policy", kind="rule_hit", resource_id=resource_id,
                    summary=f"{rule.rule_id}: {rule.note}", payload={"rule_id": rule.rule_id}))

                generated = self.ctx.generator.complete(
                    prompt=f"State the finding for {resource.display_name} under {rule.rule_id}.",
                    schema={"name": "finding_claim"},
                    context={"rule_id": rule.rule_id, "resource_name": resource.display_name,
                             "stats": stats, "iac_match_rule": match_rule,
                             "size_gb": resource.size_gb})

                pricing = json.loads((Path("data/pricing.json")).read_text())
                impact_kind = "usd_per_month" if rule.rule_id in {"R-1", "R-2", "R-3", "R-5"} \
                    else "usd_per_month_upper_bound"
                candidate = Candidate(
                    candidate_id=f"C-{len(self.ctx.state.facts['candidates']) + 1:03d}",
                    resource_id=resource_id, resource_class=resource.resource_class,
                    **{"class": rule.finding_class}, claim=generated["claim"],
                    evidence_refs=[e.evidence_id for e in evidence],
                    impact={"kind": impact_kind, "value": monthly_cost(resource, pricing)},
                    confidence=generated["confidence"],
                    falsifier="a current, declared, owned purpose for this resource would "
                              "withdraw this finding",
                    matched_rule_ids=[rule.rule_id], iac_match_rule=match_rule,
                    absent_from_iac=absent, stats=stats)

                self.ctx.state.facts["candidates"][candidate.candidate_id] = candidate
                self.ctx.state.append("candidate", {"candidate_id": candidate.candidate_id,
                                                    "resource_id": resource_id,
                                                    "rules": [rule.rule_id],
                                                    "round": assignment.round})
                candidates.append(candidate)
                self._emit("propose_finding", round=assignment.round, target_agent="Skeptic",
                           input_summary=f"{resource.display_name} under {rule.rule_id}",
                           output_summary=f"{candidate.candidate_id}: {rule.finding_class}",
                           confidence=candidate.confidence,
                           evidence_refs=candidate.evidence_refs)
        return candidates

    def undetermined(self) -> list[Undetermined]:
        return list(self._undetermined)
