from __future__ import annotations

import json
import time
from pathlib import Path

from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.agents.scout import Scout
from app.agents.skeptic import Skeptic
from app.agents.writer import Writer
from app.models import Candidate, Ruling, SourceStatus, Undetermined
from app.sources.base import Scope
from app.sources import get_source
from app.world_model.contracts import WorldError
from app.world_model.runtime import record_failure


def _same_conclusion(previous: Candidate, current: Candidate) -> bool:
    """Whether a re-check re-derived the very finding it was handed.

    Compared on the rules that justified it and the conclusion itself, not on the candidate id: the
    id is new every round by design (that is what made the re-check cap unreachable once), so it can
    never be the thing that tells two rounds apart.
    """
    return (sorted(previous.matched_rule_ids) == sorted(current.matched_rule_ids)
            and previous.claim == current.claim
            and previous.impact == current.impact)


class Orchestrator:
    def __init__(self, ctx: AgentContext, scenario_dir: Path | None = None) -> None:
        self.ctx = ctx
        self.scenario_dir = scenario_dir
        self.planner = Planner(ctx)
        self.scout = Scout(ctx)
        self.skeptic = Skeptic(ctx)
        self.writer = Writer(ctx)
        self.rulings: dict[str, Ruling] = {}
        self.caps_hit: list[str] = []
        self.sources_status: list[SourceStatus] = []
        self._started = time.monotonic()
        # One deadline for the whole run, shared with every agent and every outbound call, so no
        # agent starts work the run cannot finish paying for.
        self.deadline = self._started + ctx.config.wall_clock_hard_s
        ctx.extras["deadline"] = self.deadline
        ctx.extras["clock"] = time.monotonic
        ctx.generator.set_deadline(self.deadline)
        from app.generation_status import GenerationRecorder
        recorder = getattr(ctx.generator, "recorder", None)
        if isinstance(recorder, GenerationRecorder):
            recorder.set_observer(self._provider_event)
        from app.world_model.runtime import WorldRuntime
        if ctx.world is None:
            try:
                ctx.world = WorldRuntime.from_context(ctx, scenario_dir=scenario_dir)
            except WorldError as error:
                record_failure(ctx,error)

    def _provider_event(self, action: str, data: dict) -> None:
        self.ctx.trace.emit(agent_name="Generator", action=action,
            input_summary=data["schema_name"], output_summary=json.dumps(data, sort_keys=True, allow_nan=False),
            status="degraded" if data.get("fallback") else "started" if action == "provider_attempt" else "success")

    # --- source access with retry, then fixture fallback, then honest failure ---------------
    def _clock(self) -> float:
        """The orchestrator's own clock, swappable in tests via ctx.extras["clock"]."""
        return self.ctx.extras.get("clock", time.monotonic)()

    def _usable(self, reserve: float = 0.0) -> float:
        return self.deadline - self._clock() - reserve

    def _fetch(self, name: str, scope: Scope):
        source = self.ctx.sources[name]
        # Every attempt carries the run's absolute deadline; a deadline-aware source bounds
        # itself by it, a naive source simply ignores the field.
        fetch_scope = scope.model_copy(update={"deadline_monotonic": self.deadline})
        last_error: Exception | None = None
        for attempt in (1, 2):
            # The remote policy path is deadline-aware from its first call; generic sources
            # keep their pre-existing behaviour and only lose the retry once time is out.
            # Short-circuit first so ordinary attempts do not perturb the shared clock.
            if (attempt == 2 or name == "policy") and self._usable() <= 0:
                break
            try:
                result = source.fetch(fetch_scope)
                self.ctx.trace.emit(agent_name="Planner", action="source_ok",
                                    input_summary=f"{name} attempt {attempt}",
                                    output_summary=f"{len(result.records)} records",
                                    retry_count=attempt - 1,
                                    status="success" if not result.degraded else "degraded")
                if result.provenance is not None:
                    self.ctx.extras.setdefault("source_provenance", {})[name] = result.provenance
                    self.ctx.trace.emit(agent_name="Planner", action="source_snapshot",
                                        input_summary=f"{name} {result.backend}",
                                        output_summary=json.dumps(
                                            result.provenance.model_dump(), sort_keys=True),
                                        retry_count=attempt - 1, status="success")
                return result, SourceStatus(name=name, backend=result.backend,
                                            degraded=result.degraded, reason=result.reason,
                                            provenance=result.provenance)
            except Exception as exc:                      # noqa: BLE001 - degraded, not swallowed
                last_error = exc
                # A retry or fallback must never inherit lineage from an attempt that failed.
                self.ctx.extras.setdefault("source_provenance", {}).pop(name, None)
                self.ctx.trace.emit(agent_name="Planner", action="source_call_failed",
                                    input_summary=f"{name} attempt {attempt}",
                                    output_summary=f"{type(exc).__name__}: {exc}",
                                    retry_count=attempt - 1, status="retrying")
                if getattr(exc, "retryable", True) is False:
                    break                                 # a second auth/schema call fails alike

        # A fixture fallback is local work: it may run while finalisation budget remains, but
        # past the deadline nothing new — remote or file-backed — is started at all.
        if self.scenario_dir is not None and self._usable() > 0:
            try:
                fallback = get_source(name, self.ctx.config.model_copy(update={"sample_mode": True}),
                                      scenario_dir=self.scenario_dir)
                result = fallback.fetch(scope)
            except Exception as exc:                  # noqa: BLE001 - a missing fixture degrades
                self.ctx.trace.emit(agent_name="Planner", action="source_unavailable",
                                    input_summary=name,
                                    output_summary=f"fallback failed: {type(exc).__name__}: {exc}",
                                    status="failed", retry_count=1)
                return None, SourceStatus(name=name, backend="fixture", degraded=True,
                                          reason=f"fallback failed: {exc}")
            self.ctx.trace.emit(agent_name="Planner", action="source_degraded",
                                input_summary=name, output_summary="fell back to fixture data",
                                status="degraded", retry_count=1)
            return result, SourceStatus(name=name, backend="fixture", degraded=True,
                                        reason=str(last_error))

        self.ctx.trace.emit(agent_name="Planner", action="source_unavailable",
                            input_summary=name, output_summary="no fallback available",
                            status="failed", retry_count=1)
        return None, SourceStatus(name=name, backend="none", degraded=True, reason=str(last_error))

    def _load(self, name: str, result) -> None:
        if name == "inventory":
            from app.models import Resource
            # Build the whole mapping first: a malformed later row must not leave earlier rows
            # applied — a half-loaded inventory is a different tenancy than the one audited.
            staged: dict = {}
            for record in result.records:
                resource = Resource(**record)
                staged[resource.resource_id] = resource
            self.ctx.state.facts["resources"].update(staged)
        elif name == "iac":
            from app.models import IaCDeclaration
            self.ctx.state.facts["declarations"] = [IaCDeclaration(**d) for d in result.records]
        else:
            from app.models import PolicyRule
            self.ctx.state.facts["rules"] = [PolicyRule(**r) for r in result.records]

    def _hydrate(self) -> None:
        scope = self.ctx.scope
        results = {}
        for name in ("inventory", "iac", "policy"):
            result, status = self._fetch(name, scope)
            if result is not None:
                try:
                    self._load(name, result)
                except Exception as exc:      # noqa: BLE001 - malformed records degrade, never crash
                    status.degraded = True
                    status.reason = f"records could not be loaded: {type(exc).__name__}: {exc}"
                    self.ctx.trace.emit(agent_name="Planner", action="source_degraded",
                                        input_summary=name,
                                        output_summary=status.reason,
                                        status="degraded", retry_count=1)
            self.sources_status.append(status)
            results[name] = result.model_copy(update={"degraded":status.degraded}) if result is not None else None
        if self.ctx.world is not None:
            try:
                self.ctx.world.ingest_hydration(results)
            except WorldError as error:
                record_failure(self.ctx,error)
        self.ctx.state.append("hydrate", {
            "resources": len(self.ctx.state.facts["resources"]),
            "declarations": len(self.ctx.state.facts["declarations"]),
            "rules": len(self.ctx.state.facts["rules"])})
        self.ctx.trace.emit(agent_name="Scout", action="hydrate",
                            input_summary="inventory, iac, policy",
                            output_summary=f"{len(self.ctx.state.facts['resources'])} resources",
                            confidence=1.0)

    def _budget_exceeded(self) -> bool:
        elapsed = time.monotonic() - self._started
        if elapsed > self.ctx.config.wall_clock_hard_s:
            self.caps_hit.append("wall_clock_hard_s")
            self.ctx.trace.emit(agent_name="Planner", action="cap_hit",
                                input_summary="wall clock",
                                output_summary=f"{elapsed:.0f}s exceeds "
                                               f"{self.ctx.config.wall_clock_hard_s}s",
                                status="capped")
            return True
        if elapsed > self.ctx.config.wall_clock_soft_s and "wall_clock_soft_s" not in self.caps_hit:
            self.caps_hit.append("wall_clock_soft_s")
            self.ctx.trace.emit(agent_name="Planner", action="cap_hit", input_summary="wall clock",
                                output_summary=f"{elapsed:.0f}s exceeds soft budget",
                                status="capped")
        return False

    def _merge_source_statuses(self, statuses: list[SourceStatus]) -> None:
        for status in statuses:
            self.sources_status = [s for s in self.sources_status if s.name != status.name]
            self.sources_status.append(status)

    def _rules_available(self) -> bool:
        """No policy rules means nothing can be justified. Say so; never invent a finding."""
        if self.ctx.state.facts["rules"]:
            return True
        prov = self.ctx.extras.get("source_provenance", {}).get("policy")
        if prov is not None and prov.complete and prov.row_count == 0:
            # A complete-but-empty snapshot is a fact about the policy, not an outage. The
            # report still abstains; the reason must not misattribute the abstention.
            self.ctx.trace.emit(agent_name="Planner", action="cannot_audit",
                                input_summary="policy rules",
                                output_summary="the policy source returned a complete empty "
                                               "snapshot (0 rules); there is nothing to flag",
                                status="partial")
            return False
        self.ctx.trace.emit(agent_name="Planner", action="cannot_audit",
                            input_summary="policy rules",
                            output_summary="no rules loaded; no finding can be justified",
                            status="failed")
        return False

    def run(self):
        try:
            return self._run()
        finally:
            if self.ctx.world:
                self.ctx.world.close()

    def _run(self):
        self.ctx.state.facts["examined"] = set()
        self._hydrate()
        if self.ctx.world is None or not self._rules_available():
            report = self.writer.synthesise(
                candidates=[], rulings={}, sources=self.sources_status, status="partial",
                caps_hit=self._state_caps(),
                undetermined=[Undetermined(
                    resource_id="scope",
                    reason=("World Model unavailable: " + ",".join(self.ctx.extras.get("world_failures",[]))
                        if self.ctx.world is None else "no policy rules were loaded, so no finding could be justified"))])
            report.trace_path = str(self.ctx.trace.path)
            self.ctx.state.append("report", {"status":report.status,"findings":len(report.findings)})
            return report
        all_candidates: list[Candidate] = []
        recheck_requests: list[dict] = []
        round_number = 0

        while round_number < self.ctx.config.max_rounds:
            round_number += 1
            self.ctx.state.facts["round"] = round_number
            assignment = self.planner.assign(
                round=round_number,
                resources=list(self.ctx.state.facts["resources"].values()),
                recheck_requests=recheck_requests)

            # The Scout owns the telemetry fetch: it needs a per-resource window and its own
            # recovery, and a second fetch here would double every live API call.
            candidates = self.scout.investigate(assignment)
            self._merge_source_statuses(self.scout.source_statuses())

            if assignment.focus == "recheck":
                # A re-check that reaches a *different* conclusion supersedes the earlier finding;
                # the superseded candidate is still reported, rejected, with its reason.
                #
                # A re-check that re-derives the identical finding is not a change of mind. It is a
                # duplicate: the re-investigation looked at a resource for one class and produced
                # every class it could justify again. Publishing the repeat would report one class
                # twice for a resource and hang the word "revised" on a finding nobody touched —
                # a false claim about the agent's reasoning, which is the one thing this report is
                # supposed to make visible. The earlier ruling stands and the repeat is dropped.
                current_ids = {c.candidate_id for c in candidates}
                repeated: set[str] = set()
                for candidate in candidates:
                    for previous in all_candidates:
                        if (previous.candidate_id in current_ids
                                or previous.resource_id != candidate.resource_id
                                or previous.finding_class != candidate.finding_class
                                or previous.superseded_by is not None):
                            continue
                        if _same_conclusion(previous, candidate):
                            repeated.add(candidate.candidate_id)
                            self.ctx.state.append("duplicate_finding", {
                                "candidate_id": candidate.candidate_id,
                                "already_found_as": previous.candidate_id,
                                "round": round_number})
                            self.ctx.trace.emit(
                                agent_name="Planner", action="drop_duplicate_finding",
                                input_summary=f"{candidate.candidate_id} under "
                                              f"{','.join(candidate.matched_rule_ids)}",
                                output_summary=f"already found as {previous.candidate_id}: the "
                                               f"re-check reached the same conclusion",
                                target_agent="Writer", status="duplicate", confidence=1.0,
                                round=round_number)
                            break
                        previous.superseded_by = candidate.candidate_id
                        self.ctx.state.append("supersede", {
                            "superseded": previous.candidate_id,
                            "superseded_by": candidate.candidate_id,
                            "round": round_number})
                candidates = [c for c in candidates if c.candidate_id not in repeated]
            all_candidates.extend(candidates)

            recheck_requests = []
            for candidate in candidates:
                try:
                    ruling = self.skeptic.judge(candidate, round=round_number)
                except WorldError as error:
                    record_failure(self.ctx,error)
                    all_candidates = [c for c in all_candidates if c.candidate_id != candidate.candidate_id]
                    for previous in all_candidates:
                        if previous.superseded_by == candidate.candidate_id:
                            previous.superseded_by = None
                    self.ctx.extras.setdefault("world_undetermined",[]).append(Undetermined(
                        resource_id=candidate.resource_id,reason="World Model: " + str(error)))
                    continue
                self.rulings[candidate.candidate_id] = ruling
                self.ctx.state.facts["rulings"][candidate.candidate_id] = ruling.model_dump()
                if ruling.verdict == "recheck":
                    counts = self.ctx.state.facts["recheck_counts"]
                    # Keyed by resource and class, not candidate id: a new round mints a new id, and
                    # a per-id counter could therefore never reach the re-check cap.
                    key = f"{candidate.resource_id}|{candidate.finding_class}"
                    counts[key] = counts.get(key, 0) + 1
                    recheck_requests.append(ruling.request)
                self.ctx.state.append("ruling", {"candidate_id": candidate.candidate_id,
                                                 "verdict": ruling.verdict,
                                                 "round": round_number})

            if self._budget_exceeded():
                break
            if not recheck_requests:
                break

        if round_number >= self.ctx.config.max_rounds and recheck_requests:
            self.caps_hit.append("max_rounds")
            self.ctx.trace.emit(agent_name="Planner", action="cap_hit", input_summary="rounds",
                                output_summary=f"{self.ctx.config.max_rounds} rounds reached with "
                                               f"{len(recheck_requests)} request(s) outstanding",
                                status="capped")

        # Precedence, stated so it cannot be mistaken for a clean run: a cap outranks degradation in
        # the single `status` field, but both facts are always in the report — `caps_hit` names
        # every cap that fired, and every degraded source names itself in `sources`. The agents'
        # own caps are folded in first, so a status can never disagree with the caps list.
        caps_hit = self._state_caps()
        status = "capped" if caps_hit else ("partial" if self._any_source_unavailable() else "success")
        # A candidate the Skeptic asked to re-check that the loop never got back to is not a
        # conclusion. It is reported as undetermined with the reason, never as accepted: the caps
        # exist precisely so a truncated run cannot present an unverified claim as a finding.
        unresolved = [c for c in all_candidates
                      if self.rulings[c.candidate_id].verdict == "recheck" and not c.superseded_by]
        for candidate in unresolved:
            self.ctx.trace.emit(agent_name="Writer", action="not_concluded",
                                input_summary=candidate.candidate_id,
                                output_summary="re-check requested but never honoured",
                                evidence_refs=candidate.evidence_refs, status="capped")
        unresolved_ids = {c.candidate_id for c in unresolved}
        undetermined = self.scout.undetermined() + self.ctx.extras.get("world_undetermined",[]) + [
            Undetermined(resource_id=c.resource_id,
                         reason=f"{c.candidate_id} was not concluded: the re-check the Skeptic "
                                f"asked for did not run")
            for c in unresolved]
        report = self.writer.synthesise(
            candidates=[c for c in all_candidates if c.candidate_id not in unresolved_ids],
            rulings=self.rulings, undetermined=undetermined, sources=self.sources_status,
            status=status, caps_hit=caps_hit)
        report.trace_path = str(self.ctx.trace.path)
        self.ctx.state.append("report", {"status": report.status, "findings": len(report.findings)})
        return report

    def _state_caps(self) -> list[str]:
        """Caps recorded by the agents themselves (the resource cap, the re-check cap), folded into
        the loop's own list so every fired cap reaches the report through one field."""
        for cap in self.ctx.state.facts.get("caps_hit", []):
            if cap not in self.caps_hit:
                self.caps_hit.append(cap)
        return list(self.caps_hit)

    def _any_source_unavailable(self) -> bool:
        return any(s.degraded for s in self.sources_status)
