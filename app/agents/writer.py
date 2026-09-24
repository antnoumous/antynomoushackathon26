from __future__ import annotations

import re

from app.agents.base import Agent
from app.models import (Candidate, Finding, RunReport, Ruling, SourceStatus, Undetermined,
                        VerdictRecord)

NUMERIC = re.compile(r"\d+(?:\.\d+)?")
CURRENCY = re.compile(r"\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:USD|usd)")
# Structural constants the report prints about itself: round counts, the cap values, the lookback
# windows. These are safe because they describe the run rather than a resource.
ALLOWED_LITERALS = {"1", "2", "3", "4", "5", "7", "10", "20", "25", "41", "60", "168", "300",
                    "540", "730", "744", "0"}


class UntraceableFigureError(Exception):
    """Raised when prose contains a number that no evidence supports."""


def figures_in(text: str) -> set[str]:
    return set(NUMERIC.findall(text))


def currency_figures_in(text: str) -> set[str]:
    return {match.group(1) or match.group(2) for match in CURRENCY.finditer(text)}


def assert_figures_traceable(text: str, allowed: set[str]) -> None:
    for token in figures_in(text):
        if token not in allowed and token not in ALLOWED_LITERALS:
            raise UntraceableFigureError(f"figure {token!r} in {text!r} has no supporting evidence")
    # A money figure is never a structural constant. "300 USD" is not allowed just because 300 is
    # the soft wall clock: currency has to come from a resolved payload.
    for token in currency_figures_in(text):
        if token not in allowed:
            raise UntraceableFigureError(
                f"currency figure {token!r} in {text!r} has no supporting evidence")


class Writer(Agent):
    name = "Writer"

    def allowed_figures(self, candidates: list[Candidate]) -> set[str]:
        """Every figure must come from the ledger or from code-computed arithmetic.

        `candidate.stats` is deliberately *not* a source: a claim could otherwise vouch for its own
        numbers. The same values reach the allow-list through the telemetry evidence payload that
        the Scout wrote alongside them.
        """
        allowed = set(ALLOWED_LITERALS)
        for item in self.ctx.ledger.all():
            allowed |= figures_in(str(item.payload))
        for candidate in candidates:
            allowed |= figures_in(str(candidate.impact))
        return allowed

    def _mask(self, text: str, resource_id: str) -> str:
        """A resource's own name is an identifier, not an asserted quantity: the digits in
        `vol-orphan-100g` are not a figure anyone has to support with evidence."""
        resource = self.ctx.state.facts["resources"].get(resource_id)
        return text if resource is None else text.replace(resource.display_name, "[resource]")

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
            # Whatever reaches the report as prose is checked, whichever field produced it: the
            # claim, a revision of the claim, and the verdict's reason.
            claim_text = ruling.revised_claim or candidate.claim
            assert_figures_traceable(self._mask(claim_text, candidate.resource_id), allowed)
            assert_figures_traceable(
                self._mask(ruling.reason, candidate.resource_id),
                allowed | figures_in(str(ruling.request or {})))
            if ruling.verdict == "reject" or candidate.superseded_by:
                finding_status = "rejected"
            elif (candidate.resource_id, candidate.finding_class) in withdrawn:
                finding_status = "revised"
            else:
                finding_status = "accepted"
            findings.append(Finding(
                finding_id=candidate.candidate_id, resource_id=candidate.resource_id,
                resource_class=candidate.resource_class, **{"class": candidate.finding_class},
                claim=claim_text,
                evidence_refs=candidate.evidence_refs, impact=candidate.impact,
                confidence=round(candidate.confidence if ruling.verdict != "reject" else 0.0, 2),
                status=finding_status, falsifier=candidate.falsifier,
                superseded_by=candidate.superseded_by,
                history=[VerdictRecord(round=ruling.round, verdict=ruling.verdict,
                                       reason=ruling.reason)]))

        accepted = [f for f in findings if f.status in {"accepted", "revised"}]
        rejected = [f for f in findings if f.status == "rejected"]
        spend = sum(f.impact.get("value", 0.0) for f in findings)
        reported = sum(f.impact.get("value", 0.0) for f in accepted)
        # What was actually examined, not what happened to be in the tenancy: a capped run must not
        # read as full coverage.
        in_scope = len(self.ctx.state.facts["resources"])
        examined = self.ctx.state.facts.get("examined")
        examined_count = len(examined) if examined else in_scope

        summary = {
            "resources_examined": examined_count,
            "resources_in_scope": in_scope,
            "findings_accepted": len(accepted),
            "findings_rejected": len(rejected),
            "spend_audited_usd_per_month": round(spend, 2),
            "waste_found_usd_per_month": round(reported, 2),
            "unattributed_ratio": round(
                len([f for f in accepted if f.finding_class == "unattributed"])
                / max(1, examined_count), 3),
            # Which backends actually answered. In a run pointed at a real tenancy this says
            # `fixture` until the live adapters exist, and no reader has to infer it.
            "backends": sorted({s.backend for s in sources}),
            "sources_degraded": len([s for s in sources if s.degraded]),
        }
        generated = self.ctx.generator.complete(
            prompt="", schema={"name": "run_summary"},
            context={"resources": summary["resources_examined"], "sources": len(sources),
                     "accepted": len(accepted), "rejected": len(rejected),
                     "undetermined": len(undetermined)})
        narrative = str(generated["summary"])
        # The narrative may restate numbers this run computed; it may not introduce any.
        assert_figures_traceable(narrative, allowed | figures_in(str(summary)))
        summary["narrative"] = narrative

        self._emit("synthesise", input_summary=f"{len(accepted)} accepted, {len(rejected)} rejected",
                   output_summary=summary["narrative"], confidence=1.0,
                   evidence_refs=[ref for f in findings for ref in f.evidence_refs])

        return RunReport(run_id=self.ctx.config.run_id, status=status,
                         mode="sample" if self.ctx.config.sample_mode else "live",
                         sources=sources, summary=summary, findings=findings,
                         undetermined=undetermined, caps_hit=caps_hit)
