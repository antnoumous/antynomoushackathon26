from __future__ import annotations

from app.agents.base import Agent
from app.models import Candidate, Ruling

SCHEDULE_SIGNALS = ("month-end", "monthly", "weekly", "nightly", "batch", "cron", "schedule")
PURPOSE_SIGNALS = ("by design", "intentionally", "deliberately", "do not delete", "for now",
                   "left running")
RECHECK_LOOKBACK_HOURS = 744


class Skeptic(Agent):
    name = "Skeptic"

    def _schedule_signal(self, candidate: Candidate) -> str | None:
        return self._signal(candidate, SCHEDULE_SIGNALS)

    def _purpose_signal(self, candidate: Candidate) -> str | None:
        """A declared purpose is the falsifier the Scout itself published. Honour it."""
        return self._signal(candidate, PURPOSE_SIGNALS)

    def _recheck_key(self, candidate: Candidate) -> str:
        """Keyed by resource and finding class, never by candidate id: every round mints a new id,
        so a per-id counter could never reach the cap."""
        return f"{candidate.resource_id}|{candidate.finding_class}"

    def _recheck_count(self, candidate: Candidate) -> int:
        counts = self.ctx.state.facts.setdefault("recheck_counts", {})
        return counts.get(self._recheck_key(candidate), 0)

    def _signal(self, candidate: Candidate, needles: tuple[str, ...]) -> str | None:
        context = self._pinned_context
        texts = [str(context.resource.model_dump())]
        if context.declaration:
            texts.append(str(context.declaration.model_dump()))
        haystack = " ".join(texts).lower()
        for needle in needles:
            if needle in haystack:
                return needle
        return None

    def judge(self, candidate: Candidate, round: int) -> Ruling:
        """The only entry point. Every ruling leaves here carrying the round that produced it."""
        self._pinned_context = self.ctx.world.for_candidate(candidate.candidate_id)
        ruling = self._judge(candidate, round)
        return ruling.model_copy(update={"round": round})

    def _judge(self, candidate: Candidate, round: int) -> Ruling:
        # 1. A declaration that states a deliberate purpose withdraws the finding outright —
        #    this is the finding's own published falsifier being triggered by real evidence.
        if candidate.finding_class == "cost_waste":
            purpose = self._purpose_signal(candidate)
            if purpose:
                reason = self.ctx.generator.complete(
                    prompt="", schema={"name": "verdict_reason"},
                    context={"reason_key": "declared_purpose", "signal": purpose})["reason"]
                return self._reject(candidate, round, reason)

        # 2. An idle verdict (R-3) is only safe if nothing suggests the window is unrepresentative.
        if "R-3" in candidate.matched_rule_ids:
            signal = self._schedule_signal(candidate)
            if signal:
                count = self._recheck_count(candidate)
                if count >= self.ctx.config.max_rechecks_per_finding:
                    # A cap that fired is named, exactly like the round and wall-clock caps.
                    self.ctx.state.facts.setdefault("caps_hit", []).append(
                        "max_rechecks_per_finding")
                    self._emit("cap_hit", round=round, input_summary="re-check cap",
                               output_summary=f"{candidate.candidate_id} already re-investigated "
                                              f"{count} time(s); no further re-check granted",
                               status="capped")
                    reason = self.ctx.generator.complete(
                        prompt="", schema={"name": "verdict_reason"},
                        context={"reason_key": "recheck_cap", "n": count})["reason"]
                    return self._reject(candidate, round, reason)
                request = {"resource_id": candidate.resource_id,
                           "lookback_hours": RECHECK_LOOKBACK_HOURS,
                           "reason": f"schedule signal {signal!r} suggests the window excludes a run"}
                self._emit("request_recheck", round=round, target_agent="Scout",
                           input_summary=f"{candidate.candidate_id} under R-3",
                           output_summary=f"widen to {RECHECK_LOOKBACK_HOURS}h "
                                          f"({signal} found in evidence)",
                           status="recheck", confidence=0.7,
                           evidence_refs=candidate.evidence_refs)
                self.ctx.state.append("recheck", {"candidate_id": candidate.candidate_id,
                                                  "round": round, "signal": signal,
                                                  "lookback_hours": RECHECK_LOOKBACK_HOURS})
                return Ruling(candidate_id=candidate.candidate_id, verdict="recheck",
                              reason=f"a schedule signal ({signal}) is present, so the requested "
                                     f"window may exclude the most recent run",
                              request=request)

        # 2. A low mean with a real peak is a duty-cycle problem, not idleness.
        if "R-4" in candidate.matched_rule_ids:
            reason = self.ctx.generator.complete(
                prompt="", schema={"name": "verdict_reason"},
                context={"reason_key": "frequency_mismatch"})["reason"]
            self._emit("validate_finding", round=round, target_agent="Writer",
                       input_summary=f"{candidate.candidate_id} under R-4",
                       output_summary="accepted: duty cycle, not idle",
                       confidence=0.85, evidence_refs=candidate.evidence_refs)
            return Ruling(candidate_id=candidate.candidate_id, verdict="accept",
                          reason=reason, revised_claim=candidate.claim)

        # 3. Everything else: accept, with the confidence the evidence supports.
        self._emit("validate_finding", round=round, target_agent="Writer",
                   input_summary=candidate.candidate_id,
                   output_summary=f"accepted under {','.join(candidate.matched_rule_ids)}",
                   confidence=candidate.confidence, evidence_refs=candidate.evidence_refs)
        return Ruling(candidate_id=candidate.candidate_id, verdict="accept",
                      reason="no contradicting evidence found in the consulted sources")

    def _reject(self, candidate: Candidate, round: int, reason: str) -> Ruling:
        self._emit("validate_finding", round=round, target_agent="Planner",
                   input_summary=candidate.candidate_id, output_summary=f"rejected: {reason}",
                   status="rejected", confidence=0.8, evidence_refs=candidate.evidence_refs)
        return Ruling(candidate_id=candidate.candidate_id, verdict="reject", reason=reason)
