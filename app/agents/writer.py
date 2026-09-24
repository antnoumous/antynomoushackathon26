from __future__ import annotations

import re

from app.agents.base import Agent
from app.models import (Candidate, Finding, RunReport, Ruling, SourceStatus, Undetermined,
                        VerdictRecord)

NUMERIC = re.compile(r"\d+(?:\.\d+)?")
ALLOWED_LITERALS = {"1", "2", "3", "4", "5", "7", "10", "20", "25", "41", "60", "168", "300",
                    "540", "730", "744", "0"}


class UntraceableFigureError(Exception):
    """Raised when prose contains a number that no evidence supports."""


def figures_in(text: str) -> set[str]:
    return set(NUMERIC.findall(text))


def assert_figures_traceable(text: str, allowed: set[str]) -> None:
    for token in figures_in(text):
        if token not in allowed and token not in ALLOWED_LITERALS:
            raise UntraceableFigureError(f"figure {token!r} in {text!r} has no supporting evidence")


class Writer(Agent):
    name = "Writer"

    def allowed_figures(self, candidates: list[Candidate]) -> set[str]:
        allowed = set(ALLOWED_LITERALS)
        for item in self.ctx.ledger.all():
            allowed |= figures_in(str(item.payload))
        for candidate in candidates:
            allowed |= figures_in(str(candidate.impact))
            allowed |= figures_in(str(candidate.stats))
        return allowed

    def synthesise(self, *, candidates: list[Candidate], rulings: dict[str, Ruling],
                   undetermined: list[Undetermined], sources: list[SourceStatus],
                   status: str, caps_hit: list[str]) -> RunReport:
        allowed = self.allowed_figures(candidates)
        # A finding is `revised` when an earlier finding about the same resource and class was
        # withdrawn — that pairing is the visible trace of the agent changing its mind.
        withdrawn = {(c.resource_id, c.finding_class) for c in candidates
                     if rulings[c.candidate_id].verdict == "reject" or c.superseded_by}
        findings: list[Finding] = []
        for candidate in candidates:
            ruling = rulings[candidate.candidate_id]
            assert_figures_traceable(candidate.claim, allowed)
            if ruling.verdict == "reject" or candidate.superseded_by:
                finding_status = "rejected"
            elif (candidate.resource_id, candidate.finding_class) in withdrawn:
                finding_status = "revised"
            else:
                finding_status = "accepted"
            findings.append(Finding(
                finding_id=candidate.candidate_id, resource_id=candidate.resource_id,
                resource_class=candidate.resource_class, **{"class": candidate.finding_class},
                claim=ruling.revised_claim or candidate.claim,
                evidence_refs=candidate.evidence_refs, impact=candidate.impact,
                confidence=round(candidate.confidence if ruling.verdict != "reject" else 0.0, 2),
                status=finding_status, falsifier=candidate.falsifier,
                history=[VerdictRecord(round=ruling.round, verdict=ruling.verdict,
                                       reason=ruling.reason)]))

        accepted = [f for f in findings if f.status in {"accepted", "revised"}]
        rejected = [f for f in findings if f.status == "rejected"]
        spend = sum(f.impact.get("value", 0.0) for f in findings)
        reported = sum(f.impact.get("value", 0.0) for f in accepted)

        summary = {
            "resources_examined": len(self.ctx.state.facts["resources"]),
            "findings_accepted": len(accepted),
            "findings_rejected": len(rejected),
            "spend_audited_usd_per_month": round(spend, 2),
            "attributed_waste_usd_per_month": round(reported, 2),
            "unattributed_ratio": round(
                len([f for f in accepted if f.finding_class == "unattributed"])
                / max(1, len(self.ctx.state.facts["resources"])), 3),
        }
        generated = self.ctx.generator.complete(
            prompt="", schema={"name": "run_summary"},
            context={"resources": summary["resources_examined"], "sources": len(sources),
                     "accepted": len(accepted), "rejected": len(rejected),
                     "undetermined": len(undetermined)})
        summary["narrative"] = generated["summary"]

        self._emit("synthesise", input_summary=f"{len(accepted)} accepted, {len(rejected)} rejected",
                   output_summary=summary["narrative"], confidence=1.0,
                   evidence_refs=[ref for f in findings for ref in f.evidence_refs])

        return RunReport(run_id=self.ctx.config.run_id, status=status,
                         mode="sample" if self.ctx.config.sample_mode else "live",
                         sources=sources, summary=summary, findings=findings,
                         undetermined=undetermined, caps_hit=caps_hit)
