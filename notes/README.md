# Sponsor technology notes

**22 October hub delta + live rules via public API:** [`hackathon-resources-2026-10-22.md`](hackathon-resources-2026-10-22.md)
records the hub growing 63→67 (four workshop recordings added 21 Oct, including the
**Onboarding call — player-only, still unwatched**), the Participant Setup Guide becoming a
REQUIRED onboarding doc, and the anonymous event-page API carrying the current rules
record — with structured fields that contradict hub documents (judging-start, registration
close, prize split) and a new **$4,699 NVIDIA DGX Spark in-kind prize for best use of
Nemotron**. Raw captures outside the repo under `resources-2026-10-22/`. Nothing toggled.

**21 October resource-hub ingestion:** [`hackathon-resources-2026-10-21.md`](hackathon-resources-2026-10-21.md)
digests the live HackOS Resource Hub — 63 entries, 22 read in full, every entry classified.
It adds the participant-facing organiser set (Welcome Guide, Journey Map, Overview, Event
Calendar, APPROACH scoping guide, current Official Rules copy, Team Formation Rules), the
submission-quality set (Strong/Weak Submission Examples, Submission Form Preview, Demo Video
Guide, Vibe Coding Starter Guide) and the support set (FAQ ×2, Troubleshooting, Help Desk,
Escalation Path, Channel Directory). It carries an eight-item **re-verification list** where
the hub disagrees with `AGENTS.md`, plus five contradictions *inside* the hub itself.
Nothing was toggled on the dashboard and no recorded fact was overwritten.

**19 October Cursor setup:** [installation verification](cursor-setup-2026-10-19.md)
records Cursor 3.24.18 installed/running on the personal Mac, valid signature/notarization
and working editor CLI. User sign-in/onboarding and safe project-context setup remain pending;
installation alone is not actual Cursor development evidence.

**19 October scope approval and plan:** Option B (Zetaris policy/declarations, consumed World
Model, Nemotron explanations) is approved, delivered policy-first. The
[detailed M1 implementation plan](../docs/superpowers/plans/2026-10-19-zetaris-policy-integration.md)
contains six test-driven delivery tasks and explicit M2–M5 handoffs. Plan review, execution method,
actual Cursor work surface and the stated live-access/publication gates remain prerequisites;
no product code or new platform objects were changed by planning.

**19 October deployment verified:** [`zetaris-oci-deployed-2026-10-19.md`](zetaris-oci-deployed-2026-10-19.md)
and [generated evidence](evidence/2026-10-19-zetaris-deployment.json) supersede the registry-blocked
status below. The dedicated OCI platform passes nine vendor checks and seven checks each via
direct REST and in-container JDBC. Private loopback-tunnel access works. This is infrastructure
preparation, not a completed product integration or event-eligibility determination.

**18 October readiness and integration proposal:**
[`zetaris-oci-readiness-2026-10-18.md`](zetaris-oci-readiness-2026-10-18.md)
records live `antworld` identity, listed x86 shapes/Ubuntu image, quota headroom, current
Oracle SKU costs, inspected-bundle differences and generated evidence. The
[deployment runbook](../docs/zetaris-oci-runbook.md) specifies isolated SSH-only access and
explicit cleanup; the [integration proposal](../docs/superpowers/specs/2026-10-18-sponsor-integration-proposal.md)
defines Zetaris policy/IaC, minimal World Model consumption and honest Nemotron generation.
At that assessment's cutoff, readiness work and baseline tests were complete; registry access,
deployment and proposed product acceptance tests were not. Deployment completed on 19 October;
product acceptance tests remain future work.

**Approved OCI deployment direction:** [`zetaris-oci-deployment.md`](zetaris-oci-deployment.md)
records the builder's approval to deploy Zetaris in `antworld`, the screenshot-supported
26 November trial expiry correction, obtained account/bundle and historical registry-access issue
(resolved and verified on 19 October).
Dedicated OCI resources were created on 19 October. Earlier personal-Mac installation approval gates below
are historical; the audited lab's teardown remains a separate decision.

**Latest 17 October update:**
[`participant-setup-guide-2026-10-17.md`](participant-setup-guide-2026-10-17.md)
assesses the newly supplied organiser Google Doc (dated 16 October). It directs local
Zetaris installation rather than supplying a shared URL, explicitly expects Nemotron,
and retains Meterless/credit placeholders and eligibility ambiguities. User-approved
read-only onboarding produced a clean pinned checkout and a failing prerequisite check;
Docker/platform installation and product changes still require separate approval.

**17 October documentation supplement:**
[`zetaris-docs-assessment-2026-10-17.md`](zetaris-docs-assessment-2026-10-17.md)
assesses both attachments and all 19 supplied links. Shared participant-instance access
comes first; JDBC onboarding and a possible REST runtime are separate decisions.
The supplier preflight has protocol/endpoint caveats; its runtime helpers need tighter
bounds. No installation, query or integration was performed or authorised.

**Current event verification (14 October):** [`zetaris.md`](zetaris.md) analyses the supplied
meeting against Driftwatch's actual adapters and the directly retrieved published rules.
The build window is now **22–27 October**; Zetaris/Meterless integrations and Cursor
development are mandatory. The older calendar/track/optional-sponsor assumptions below are
historical. Product changes, a new track selection and lab retention remain unapproved.

Findings on Zetaris, NVIDIA and Meterless, gathered from the recorded workshops and the
HackOS sponsor resource areas. One file per sponsor once there is enough to say.

> **Start here:** [`host-docs-digest.md`](host-docs-digest.md) — digest of the twelve
> documents shared by the organisers (rules, policies, self-check, onboarding deck, and the
> three Meterless agent engines). It includes a conflict table for facts where the host
> documents disagree with `docs/event-brief.md` and `AGENTS.md` — **including the partner
> stack: the host docs say Zetaris / Neo4j / Meterless, with no NVIDIA.**

| Sponsor | Layer | Workshop | Notes file |
|---|---|---|---|
| Zetaris | Data — real, fragmented data via MCP | 7 Oct, 16:00–17:30 UTC | `zetaris.md` |
| NVIDIA | Token — cost-effective reasoning at scale | 8 Oct, 16:00–17:30 UTC | `nvidia.md` |
| Meterless | Orchestration — autonomous multi-step workflows | 12 Oct, 16:00–17:30 UTC | `meterless.md` |

Check HackOS for workshop access and recordings as they become available. On 9 October,
the 12 October Meterless session is still upcoming; this analysis did not watch a recording.

## Detailed Meterless analysis

Read [`zetaris.md`](zetaris.md) first for the 14 October rule update. The 9 October
Meterless integration recommendation remains technically useful, but its optional-sponsor
eligibility assumptions and old event calendar are superseded.

[`meterless.md`](meterless.md) — six-document source inventory and 9 October analysis,
public-reference cross-checks, and the proposed Driftwatch integration order: minimal
World Model first, H-MEM only with demonstrable cross-run benefit, Markovian only after a
measured context-growth need. This is a recommendation, not a mounted integration or a
reversal of the existing no-sponsor decision. Event track/scoring/partner wording remains
subject to live HackOS verification.

## What to capture per sponsor

- What the layer actually does, in one paragraph
- Access and setup steps, and whether they are completed
- The smallest thing worth building with it
- Limits: quotas, latency, cost, what it cannot do
- **Where it fits in this project** — this is scored under "Sponsor tech" (10 points)
  and must be written down before submission
