from __future__ import annotations

from app.agents.base import Agent
from app.models import Candidate, Ruling

SCHEDULE_SIGNALS = ("month-end", "monthly", "weekly", "nightly", "batch", "cron", "schedule")
RECHECK_LOOKBACK_HOURS = 744


class Skeptic(Agent):
    name = "Skeptic"

    def _schedule_signal(self, candidate: Candidate) -> str | None:
        for item in self.ctx.ledger.resolve(candidate.evidence_refs):
            haystack = " ".join(str(v) for v in list(item.payload.values()) + [item.summary]).lower()
            for signal in SCHEDULE_SIGNALS:
                if signal in haystack:
                    return signal
        return None

    def _recheck_count(self, candidate_id: str) -> int:
        return self.ctx.state.facts.setdefault("recheck_counts", {}).get(candidate_id, 0)

    def judge(self, candidate: Candidate, round: int) -> Ruling:
        """The only entry point. Every ruling leaves here carrying the round that produced it."""
        ruling = self._judge(candidate, round)
        return ruling.model_copy(update={"round": round})

    def _judge(self, candidate: Candidate, round: int) -> Ruling:
        # 1. An idle verdict (R-3) is only safe if nothing suggests the window is unrepresentative.
        if "R-3" in candidate.matched_rule_ids:
            signal = self._schedule_signal(candidate)
            if signal:
                if self._recheck_count(candidate.candidate_id) >= self.ctx.config.max_rechecks_per_finding:
                    reason = self.ctx.generator.complete(
                        prompt="", schema={"name": "verdict_reason"},
                        context={"reason_key": "recheck_cap",
                                 "n": self._recheck_count(candidate.candidate_id)})["reason"]
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
