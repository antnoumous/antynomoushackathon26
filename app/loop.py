from __future__ import annotations

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

    # --- source access with retry, then fixture fallback, then honest failure ---------------
    def _fetch(self, name: str, scope: Scope):
        source = self.ctx.sources[name]
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                result = source.fetch(scope)
                self.ctx.trace.emit(agent_name="Planner", action="source_ok",
                                    input_summary=f"{name} attempt {attempt}",
                                    output_summary=f"{len(result.records)} records",
                                    retry_count=attempt - 1, status="success")
                return result, SourceStatus(name=name, backend=result.backend)
            except Exception as exc:                      # noqa: BLE001 - degraded, not swallowed
                last_error = exc
                self.ctx.trace.emit(agent_name="Planner", action="source_call_failed",
                                    input_summary=f"{name} attempt {attempt}",
                                    output_summary=f"{type(exc).__name__}: {exc}",
                                    retry_count=attempt - 1, status="retrying")

        if self.scenario_dir is not None:
            fallback = get_source(name, self.ctx.config.model_copy(update={"sample_mode": True}),
                                  scenario_dir=self.scenario_dir)
            result = fallback.fetch(scope)
            self.ctx.trace.emit(agent_name="Planner", action="source_degraded",
                                input_summary=name, output_summary="fell back to fixture data",
                                status="degraded", retry_count=1)
            return result, SourceStatus(name=name, backend="fixture", degraded=True,
                                        reason=str(last_error))

        self.ctx.trace.emit(agent_name="Planner", action="source_unavailable",
                            input_summary=name, output_summary="no fallback available",
                            status="failed", retry_count=1)
        return None, SourceStatus(name=name, backend="live", degraded=True, reason=str(last_error))

    def _hydrate(self) -> None:
        scope = self.ctx.scope
        for name in ("inventory", "iac", "policy"):
            result, status = self._fetch(name, scope)
            self.sources_status.append(status)
            if result is None:
                continue
            if name == "inventory":
                from app.models import Resource
                for record in result.records:
                    resource = Resource(**record)
                    self.ctx.state.facts["resources"][resource.resource_id] = resource
            elif name == "iac":
                from app.models import IaCDeclaration
                self.ctx.state.facts["declarations"] = [IaCDeclaration(**d) for d in result.records]
            else:
                from app.models import PolicyRule
                self.ctx.state.facts["rules"] = [PolicyRule(**r) for r in result.records]
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
        self.ctx.trace.emit(agent_name="Planner", action="cannot_audit",
                            input_summary="policy rules",
                            output_summary="no rules loaded; no finding can be justified",
                            status="failed")
        return False

    def run(self):
        self._hydrate()
        if not self._rules_available():
            report = self.writer.synthesise(
                candidates=[], rulings={}, sources=self.sources_status, status="partial",
                caps_hit=[],
                undetermined=[Undetermined(
                    resource_id="scope",
                    reason="no policy rules were loaded, so no finding could be justified")])
            report.trace_path = str(self.ctx.trace.path)
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
                # A re-check that reaches a different conclusion supersedes the earlier finding.
                # The superseded candidate is still reported: rejected, with its reason.
                current_ids = {c.candidate_id for c in candidates}
                for candidate in candidates:
                    for previous in all_candidates:
                        if (previous.candidate_id not in current_ids
                                and previous.resource_id == candidate.resource_id
                                and previous.finding_class == candidate.finding_class
                                and previous.superseded_by is None):
                            previous.superseded_by = candidate.candidate_id
                            self.ctx.state.append("supersede", {
                                "superseded": previous.candidate_id,
                                "superseded_by": candidate.candidate_id,
                                "round": round_number})
            all_candidates.extend(candidates)

            recheck_requests = []
            for candidate in candidates:
                ruling = self.skeptic.judge(candidate, round=round_number)
                self.rulings[candidate.candidate_id] = ruling
                self.ctx.state.facts["rulings"][candidate.candidate_id] = ruling.model_dump()
                if ruling.verdict == "recheck":
                    counts = self.ctx.state.facts["recheck_counts"]
                    counts[candidate.candidate_id] = counts.get(candidate.candidate_id, 0) + 1
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

        status = "capped" if self.caps_hit else ("partial" if self._any_source_unavailable() else "success")
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
        undetermined = self.scout.undetermined() + [
            Undetermined(resource_id=c.resource_id,
                         reason=f"{c.candidate_id} was not concluded: the re-check the Skeptic "
                                f"asked for did not run")
            for c in unresolved]
        report = self.writer.synthesise(
            candidates=[c for c in all_candidates if c.candidate_id not in unresolved_ids],
            rulings=self.rulings, undetermined=undetermined, sources=self.sources_status,
            status=status, caps_hit=self.caps_hit)
        report.trace_path = str(self.ctx.trace.path)
        self.ctx.state.append("report", {"status": status, "findings": len(report.findings)})
        return report

    def _any_source_unavailable(self) -> bool:
        return any(s.degraded for s in self.sources_status)
