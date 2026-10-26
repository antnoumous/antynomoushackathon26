# Driftwatch — narrated review cut

Synthetic narration using the voice approved by the user. The silent original is unchanged.
Recorded execution with editorial scene holds; this is not an execution-time benchmark.
**Sponsor status:** Zetaris executed live; the Meterless World Model is implemented and consumed locally; the Nightshift provider is implemented and contract-tested but has served no live request, because the vendor's Mac installer fails macOS Gatekeeper.

Duration: 02:11 (130.82 seconds).

Rebuild from the stored MP3 segments: `python3.11 scripts/assemble_demo_voiceover.py`.

## Narration

### 00:00–00:16 · 01-introduction

Driftwatch audits an OCI tenancy for cost waste and shadow infrastructure. Four agents — Planner, Scout, Skeptic, Writer — one bounded loop. Everything you're about to see came out of the run itself.

### 00:16–00:36 · 02-sample-audit

Sample mode first: no credentials, no network, and the whole agent still runs. Scout proposes finding C-001, then withdraws it — the burst is a month-end schedule, not a missing declaration. A scanner that cannot retract a finding is not an auditor.

### 00:36–00:51 · 03-agent-critique

The trace is the product. Every line names the agent, the action, the target and the status. The Skeptic's rejections are as visible as the accepted findings, because that is what makes the reasoning checkable.

### 00:51–01:13 · 04-zetaris-acceptance

Then the sponsor data plane, live: policy published as immutable snapshots on the real Zetaris gateway, with digests re-verified after transport. Republish without rule R-1, and exactly one finding disappears — the detached volume — and nothing else moves. Cause and effect, not a demo branch.

### 01:13–01:25 · 05-recorded-evaluation

Measured, not promised: three curated scenarios at precision and recall of one, ten held-out generated tenancies, and four hundred and fifty-six tests.

### 01:25–01:36 · 06-reproduction-and-status

Inputs, reports, traces and runbooks. All in the repository, and all reproducible from a fresh clone with no keys.

### 01:36–01:53 · 07-world-model

The Meterless World Model engine is implemented and load-bearing. Scout and Skeptic read their context through it, each selection pinned to the exact run and source revision, and the acceptance proof is generated offline from this repository.

### 01:53–02:11 · 08-nightshift-status

The Nightshift provider is wired to the documented contract and contract-tested, but the vendor's Mac installer fails Gatekeeper, so no request has ever been served. The report says not used rather than pretending otherwise — and the repository says the same thing.
