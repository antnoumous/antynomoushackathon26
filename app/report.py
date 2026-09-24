from __future__ import annotations

from app.models import RunReport

STATUS_ORDER = {"accepted": 0, "revised": 1, "rejected": 2}


def render_markdown(report: RunReport) -> str:
    lines = [
        f"# Tenancy audit — run `{report.run_id}`",
        "",
        f"- **Status:** {report.status}",
        f"- **Mode:** {report.mode}",
        f"- **Sources:** " + ", ".join(f"{s.name} ({s.backend}{', degraded' if s.degraded else ''})"
                                       for s in report.sources),
        f"- **Caps hit:** {', '.join(report.caps_hit) if report.caps_hit else 'none'}",
        "",
        "## Summary",
        "",
    ]
    lines += [f"- **{k.replace('_', ' ')}:** {v}" for k, v in report.summary.items()]
    lines += ["", "## Findings", ""]
    for finding in sorted(report.findings, key=lambda f: STATUS_ORDER[f.status]):
        lines += [
            f"### {finding.finding_id} — {finding.claim}",
            "",
            f"- Resource: `{finding.resource_id}` ({finding.resource_class})",
            f"- Class: {finding.finding_class}",
            f"- Verdict: **{finding.status}** (confidence {finding.confidence})",
            f"- Impact: {finding.impact.get('value')} {finding.impact.get('kind')}",
            f"- Evidence: {', '.join(finding.evidence_refs)}",
            f"- Would be withdrawn by: {finding.falsifier}",
        ]
        for record in finding.history:
            lines.append(f"- Round {record.round}: {record.verdict} — {record.reason}")
        if finding.superseded_by:
            lines.append(f"- Superseded by: `{finding.superseded_by}`")
        lines.append("")
    if report.undetermined:
        lines += ["## Not determined", ""]
        lines += [f"- `{u.resource_id}` — {u.reason}" for u in report.undetermined]
        lines.append("")
    return "\n".join(lines)
