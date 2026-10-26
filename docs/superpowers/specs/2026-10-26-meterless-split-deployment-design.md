# Driftwatch Meterless integration — split deployment design

Date: 26 October 2026 (Singapore time)

Status: **Written specification approved by the user on 26 October 2026. Implementation-plan review and execution-method selection remain the next gate.**

The user approved the recommended topology: Driftwatch, a minimal Meterless World Model,
and Zetaris on existing personal OCI infrastructure; Nightshift inference on the personal Mac,
connected through an encrypted SSH tunnel. That approval authorises this design document, not
unreviewed production code, software installation, cloud provisioning, or publication.

## 1. Outcome and constraints

Close the Meterless integration gap with a feature the agents actually consume and a real
Nightshift model call. Preserve the four-agent audit, its deterministic financial arithmetic,
critique/recheck behaviour, safety caps, programmatic entry points and credential-free judged path.

The World Model is a Python adaptation of the sponsor's minimum headless reference architecture,
not an installed Meterless Python package or a claim of full reference-suite conformance. It
implements `WorldStoreService`, `IngestPipelineService` and `ContextBuilderService`.

This concretises the unbuilt World Model/model-runtime follow-ons in the earlier 18 October
sponsor proposal. The user-approved split replaces its proposed Nemotron-only explanation choice
with a real Nightshift local provider; no NVIDIA usage or prize eligibility is claimed. The shipped
Zetaris policy milestone remains intact. Moving IaC declarations into Zetaris is deferred, not
silently claimed as complete or added to this deadline-critical scope.

The live acceptance must prove both the engine and Nightshift. Neither renaming `RunState` nor
calling a different OpenAI-compatible server qualifies as a Meterless implementation.

Constraints:

- No new OCI instances, GPUs, disks, snapshots, paid subscriptions, cloud-model purchases or
  hardware resizing. No extension of existing resource retention is authorised by this design.
- No employer resources or employer data. No credentials on the Windows work machine.
- Preserve the sample run as CPU-only, offline, deterministic and dependency-light. Nightshift's
  optional inference path uses the personal Mac's GPU; it is not required for the offline path.
- Keep the current CLI and HTTP report contracts, caps and evidence validation. Do not lower
  telemetry sufficiency thresholds or change resource declarations to manufacture a revision.
- Preserve all existing recordings and genuine live evidence. Update sponsor claims only after
  the corresponding checks pass.
- Binding event deadline last verified 26 October: **27 October 2026 23:45 UTC**, equivalently
  **28 October 2026 07:45 SGT**. Reserve time to refresh evidence, deck, video and submission form.

## 2. Verified context and current deployment blocker

Read-only OCI API inventory on 26 October identified the personal lab `antworld`, region
`ap-batam-1`, with four RUNNING `VM.Standard.A1.Flex` lab hosts (1 OCPU, 6 GB RAM, no GPU each)
and RUNNING `zetaris-01` (`VM.Standard.E5.Flex`, 2 OCPUs, 16 GB RAM, no GPU).

The intended application host is **the existing `zetaris-01`**, not an audited A1 workload.
This avoids adding inference or deployment activity to the resources whose CPU history the audit
is trying to interpret. The existing Zetaris installation must remain unchanged.

**Blocker:** a read-only SSH check to `zetaris-01` timed out. OCI VNIC discovery confirmed that
the SSH configuration targets the current public address; a separate TCP/22 connection also did
not succeed. RUNNING state does not establish SSH or data-gateway reachability. Free RAM, disk
headroom and the remote Python version could not be measured. No firewall, NSG, route, SSH
configuration or remote process was changed.

Before deployment, require authenticated SSH, Python 3.11+, at least 2 GiB available RAM and
2 GiB free disk, plus a successful baseline Zetaris check. Do not silently move the workload,
resize the host or open ingress if any gate fails. Report the precise blocker for a separate
authorised remedy; local development and hermetic verification may proceed independently.

The personal Mac reports Apple M6 and 34,359,738,368 bytes RAM. Its free disk was measured at
350,558,990,336 bytes during discovery. Meterless's current Mac page advertises M5-or-later
support and free insider access through 28 October; the installer link resolves to a DMG. This
establishes availability, **not** successful installation, licence activation or model capability.

The DGX Linux installer is headless and ARM64, but the installation guide targets DGX Spark,
with a 64 GB minimum and NVIDIA hardware. That is not a supported substitute for the current
CPU-only OCI VMs. The proposed split avoids that compatibility experiment and new cloud spend.

## 3. Architecture and trust boundaries

```text
Personal Mac                                      Personal OCI: zetaris-01
+----------------------------+                    +-----------------------------+
| Nightshift M5+              |                    | Driftwatch CLI               |
| local model only           |                    | Planner / Scout / Skeptic /  |
| 127.0.0.1:8088/v1           |                    | Writer                       |
+-------------^--------------+                    |             |               |
              |                                   | World Model: SQLite          |
              +-- encrypted SSH reverse tunnel ---| 127.0.0.1:18088 -> Mac:8088  |
                                                  |             |               |
                                                  | Existing Zetaris policy      |
                                                  | snapshot adapter             |
                                                  +-----------------------------+
```

The Mac initiates the connection to OCI. The reverse listener is bound explicitly to OCI
loopback, not a public interface. A separate local SSH profile/process is used; do not overwrite
or kill the existing Zetaris tunnel. Forwarding failure must terminate that tunnel attempt.
Use server-alive checks and strict host-key verification. Do not enable `GatewayPorts`, expose
8088/18088 to the Internet, enable Nightshift LAN hotspot mode, or add public HTTP API access.

Acceptance uses the CLI, not `run.py --serve` (which currently binds `0.0.0.0`). HTTP interface
regression tests remain local. A public application deployment is out of scope.

The runtime bearer token is read from Nightshift's protected local state without printing it.
Transmit it only over authenticated SSH stdin into the remote audit process's environment; never
put it in command-line arguments, repository files, transcripts, logs or chat. OCI API keys stay
on their existing authorised machine unless a separate deployment credential decision is needed.
The hybrid sponsor acceptance uses synthetic inventory/telemetry/IaC and needs no copied OCI key.

## 4. World Model data and services

### 4.1 Identity and immutable observations

Use SQLite from the Python standard library. Schema version 1 has immutable entities,
observations, relationship records and per-run observation membership. Schema/version metadata is
explicit. Derived projections are rebuildable from immutable observations; there is no independent
agent-maintained copy of canonical resource facts.

An entity ID is a SHA-256 over schema version, namespace, entity type and stable external key.
Do not hash a display name alone. A live namespace includes the configured tenancy/region scope;
a sample namespace includes the scenario identity and source-content fingerprint. Raw identifiers
remain private; exported copies continue through the established masking procedure.

An observation ID is a SHA-256 over namespace, entity identity, source kind, actual backend,
source snapshot/version, measurement window/resolution and canonical validated payload. Canonical
JSON has stable ordering and explicit datetime normalisation. Exclude ingestion wall-clock time,
run IDs, allocation-order evidence IDs and absolute local paths from content identity.

Retain both fetch time and source measurement time where available. A fetch timestamp must not
be represented as the time a metric was measured. Missing source timestamps are marked unknown.
The 168-hour and 744-hour metric series are distinct observations, never competing replacements.

Observations retain provenance, relationship to the resource/context, schema version and payload.
Zetaris policy observations preserve the existing snapshot ID, content digest and provider lineage.
Absence and source failure are explicit states; an old successful observation cannot conceal a
current missing source or reintroduce a rule removed from the current policy snapshot.

### 4.2 `WorldStoreService`

Responsibilities: transactional append/deduplication, run membership, immutable lookups and
rebuildable projections. Default storage is a private per-run database under `logs/`; reopening a
specific database is supported for inspection and ingestion recovery. Stable identities are
consistent across equivalent runs even when their default databases are separate.

Explicitly sharing a database must still isolate run membership and scenario/tenancy namespaces.
Normal tests, evaluations and sample runs never retrieve another run's state. Full orchestration
resume, learned memory across audits and migration from arbitrary old schema versions are out of
scope; unsupported schemas fail with an actionable error rather than being silently rewritten.

Use a single writer and atomic transactions. SQLite busy wait is bounded at 250 ms, with no
unbounded retry loop. Limits: 10,000 observations per run, 2 MiB per validated observation payload,
and 128 MiB database page budget. All are named and visible when hit. Reaching a limit cannot
silently truncate evidence and still claim a complete context.

### 4.3 `IngestPipelineService`

Normalise, resolve identity, validate payload/provenance, append once and project. An equivalent
second ingestion adds no duplicate entity/observation. A batch either commits completely or leaves
no partial world. A crash followed by reopening and retrying yields the same semantic world.

Feed inventory, IaC and policy results from the existing orchestrator hydration path. Feed each
telemetry result at Scout's existing per-resource fetch point. Do not double external source calls
or bypass the existing retry/fallback/deadline behaviour.

The adapter records the source that actually answered. A fixture fallback is a fixture observation,
not a successful live observation. Failed validation or unavailable storage yields an explicit
World Model failure and a partial/abstained audit, not an invisible return to direct state reads.

### 4.4 `ContextBuilderService`

Return typed resource context: current resource, matched declaration or explicit absence, the
current pinned policy snapshot/rules, requested telemetry window, source status, observation IDs,
and selection/exclusion reasons. Consumers cannot query an arbitrary global 'latest' view.

Selection is deterministic and limited to current-run membership, namespace, resource and exact
requested measurement window. Return at most 256 selected records per resource. If essential
records cannot fit, report incomplete context and abstain rather than using a partial policy set.
Do not compress away raw measurements, provenance or the existing coverage/sufficiency checks.

Scout consumes this service to assemble candidate evidence and rule inputs. Skeptic consumes
context pinned to the candidate's observation references when checking purpose and schedule
signals. Later ingestion must not retroactively alter the facts behind a prior ruling.

Keep the existing evidence ledger and report evidence IDs (`E-*`) as the report-level contract.
Add World Model references as provenance, not replacements for ledger resolution. The Planner
continues to own assignments/caps; the Writer continues to guard figures and publish accepted,
rejected, revised and undetermined results. Do not grant new verdict-writing permissions to Scout.

## 5. Runtime integration and honest provider accounting

Introduce an explicit generator provider selection: existing rules/OpenAI-compatible behaviour,
and a `meterless` provider. Sample mode overrides remote provider settings before reading tokens,
URLs or running discovery. It still uses `RulesGenerator`, but it runs the same World Model engine.

The Meterless adapter:

- Normalises the configured base URL exactly once to `/v1`, including a pasted completion or
  model-list URL; reject unsupported schemes and accidental `/v1/v1`.
- Uses the runtime's real bearer token. Add `meterless-app: driftwatch` on every request and
  `meterless-scope: user` on chat requests. Never accept `rt-local` as a working token.
- Uses authenticated `/v1/models` for readiness. Distinguish unauthorised (401/403), offline,
  a process-only health response and a valid Meterless model list.
- Requests the discovered `meterless/local` routing mode for the approved local-only deployment.
  It must be present; do not relabel another model ID or silently enable a cloud route.
- Requests the existing structured schemas and validates complete JSON, required fields and
  appropriate value types. Do not rely on a plain text ping as proof of structured generation.
- Keeps the existing 60-second per-call upper bound and the run's remaining absolute deadline.
  Prewarm the selected model before the audit, under a separate bounded readiness check. Do not
  raise the 300/540-second audit caps to accommodate cold model loading.
- Emits provider-attempt/result/fallback events with configured provider, actual backend, routing
  ID, success/failure classification, timeout and latency. Never log request headers or secrets.

The current `ModelGenerator.complete` silently returns rules on exceptions. Replace that
observability gap without changing financial/rule eligibility logic: a deterministic fallback is
allowed for continuity, but the run records `actual_backend=rules` for that call and has a partial
provider status. Provider summaries count real attempts, successes and fallbacks; zero attempts
are `not_used`, not a 100% success rate.

For sponsor acceptance, require at least one successful schema-valid Nightshift response for
each schema actually used (`finding_claim`, `verdict_reason`, `run_summary`) and no provider
fallback during the accepted run. Also verify the existing figure guard accepts the final prose.
A model failure, malformed JSON or exhausted time can produce a usable partial audit, but cannot
pass this sponsor acceptance gate.

## 6. Installation, host and spending limits

Installation starts only after written-spec approval, implementation-plan review and execution
selection. Use the official Mac M5+ insider download only while its stated no-charge offer is
available; never enter checkout or accept a paid licence as a workaround. Verify the downloaded
artifact, code signature/notarisation and app identity before first execution; do not disable
Gatekeeper or change system-wide security settings. Licence/terms acceptance and OS permission
prompts belong to the user.

Install non-destructively in the user's Applications location; do not overwrite an existing
Nightshift installation or its state. Select one small local text model from the actual catalog,
with a weight download cap of 4 GiB and total setup-download cap of 8 GiB. Do not activate a fleet,
media engines, extra providers, automatic overnight jobs or cloud relay. If setup requires a larger
model, payment, an unavailable local routing mode or a security bypass, stop and report it.

Before starting model downloads, measure available disk and memory and record the selected
model, download size and relevant licence. Model downloads happen during setup, never during a
judged audit or offline sample run. A single bounded prewarm/readiness window is 10 minutes after
the chosen model finishes downloading; if it cannot respond, retain the blocker rather than
looping indefinitely.

No new cloud compute is requested. Existing OCI credit balance/expiry and actual charges were
not freshly revalidated for this task. The earlier Zetaris deployment record remains the budget
and retention baseline: a **7 November 00:00 UTC checkpoint**, not an automatically scheduled
teardown. This design does not extend that checkpoint or infer free eligibility from RUNNING
state. Use only existing allocation and verified free headroom, with one audit at a time and a
1 GiB application memory limit; do not change Zetaris's container/resources or the A1 workloads.
Confirm any post-event retention separately.

On completion or abort, close this task's tunnel and stop only its temporary audit processes.
Keep reports, databases and source evidence for review. Do not stop Zetaris or uninstall the app
as an automatic cleanup. Do not enable a persistent boot service without separate approval.

## 7. Failure behaviour and observability

Every selected context records the observations it consumed and why. Emit `world_ingest`,
`world_context`, `world_unavailable` and limit/degradation events in the existing JSONL trace,
with the established trace fields retained. Emit a machine-readable runtime manifest describing
wired services, active store, namespace, selected sources and actual provider behaviour.

Add sponsor status under the existing report summary dictionary rather than replacing the
report schema. Distinguish World Model wired/used/failed, Nightshift configured/attempted/answered,
and data-source fixture/live/none. A requested integration that did not execute must not be
reported as mounted-and-verified for that run.

Storage errors, unsupported schema, missing provenance, incomplete essential context or namespace
mismatch must not publish a normal success from the old direct-read path. Keep whatever evidence
was safely captured, mark partial/abstained and give the precise reason. No invented default facts,
no stale replay as current telemetry, and no hidden backend substitution.

## 8. Acceptance matrix

All new behaviour is implemented with RED–GREEN–REFACTOR: run a failing test before its production
change, then the targeted and full suites. Generated evidence is never hand-edited.

| Gate | Required observable result |
|---|---|
| Identity | Equivalent payloads/orderings yield stable IDs; changed facts/window/backend produce distinct observations. |
| Deduplication | Re-ingesting the same batch does not grow entity/observation counts or duplicate findings. |
| Atomicity/recovery | Injected mid-batch failure leaves no partial commit; reopen/retry yields the expected world. |
| Isolation | Scenario, tenancy and run membership prevent stale policy/telemetry and held-out answer leakage. |
| Window preservation | Both 168h and 744h observations coexist; the requested context reads the correct one and retains original coverage. |
| Actual consumption | Scout and Skeptic use builder-selected observations on the real loop path; targeted changed evidence changes context and the appropriate decision. |
| Ledger | Every published report evidence ref resolves; World Model lineage agrees with consumed data and pinned policy snapshot. |
| Bounded failure | Lock, disk/page/row/payload/context limit and corrupt/unknown schema cases fail visibly, without an old-path success. |
| Offline | All curated scenarios run with socket creation blocked and provider variables absent or malformed; no runtime/model download. |
| Provider contract | URL normalisation, required headers, invalid-token classification, valid discovery and all structured schemas are tested. |
| Provider truth | Timeout, malformed output and disconnected tunnel report rules fallback/partial correctly; zero attempts never imply a successful provider. |
| Live provider | Authenticated real Nightshift responses for the used schemas, zero fallback in the accepted run and figure-guarded output. |
| Live policy | Existing Zetaris base/variant acceptance still removes only the R-1-dependent detached-volume finding. |
| Combined sponsor proof | World Model context is consumed with real Zetaris policy and real Nightshift inference; synthetic inventory/IaC/telemetry is labelled as such. |
| Regression | Full suite, three curated scenarios, ten existing held-out seeds and CLI/HTTP checks pass without changed verdict/financial semantics. |
| Packaging | A clean clone of the published commit installs and runs the offline path; no local environment or secrets are required. |
| Delivery | README, metadata, deck, current video and submission description match the verified code and actual integration limitations. |

Do not call the combined hybrid test a live OCI tenancy audit. Do not interpret synthetic financial
figures as a real invoice or measured cash savings. Live-only paths that could not be exercised
remain explicitly unverified even if hermetic tests pass.

## 9. Scope exclusions and delivery order

Exclude H-MEM, Markovian, Scout Intent, new agents, graph/vector databases, broad enrichment,
learned multi-audit memory, full engine conformance certification, public hosting, GPU provisioning,
cloud-provider keys, Windows installation and changes to live telemetry workloads.

Delivery sequence for the later implementation plan:

1. Establish the failing acceptance checks and preserve the current offline baseline.
2. Build the three World Model services and route existing agent context through them.
3. Add provider selection, contract validation and honest fallback accounting.
4. Pass hermetic regressions and generated evidence checks.
5. Verify free Mac installation/model readiness and OCI SSH/headroom gates; connect loopback tunnel.
6. Run combined sponsor acceptance, then regenerate and inspect the proof artifacts.
7. Update source attribution/limitations, deck and demo scenes/approved synthetic narration.
8. Review published claims, scan deliverables and fresh-clone-verify the published commit.

No push, submission creation or public sharing is authorised by design approval. The worktree
already contains unrelated/uncommitted media and documentation work; commit only this design and
its dated `docs/decisions.md` entry. The current narrated MP4 matches the repository's broad
`*.mp4` ignore rule, so the later packaging
pass must explicitly address tracked media rather than assuming that generated footage is published.

## 10. Source authority and design review

Sources inspected for the proposal and this design:

- Binding event record: `https://hackathon-server.genai.works/api/v1/hackathons/019fd164-82b9-7382-a536-d9093c576ed2/`, re-read 26 October. It requires Zetaris and Meterless; Cursor is optional.
- Signed-in Resource Hub Official Rules (`01a08ff1-54cc-709a-bfe7-6b34452b676b`), re-read 26 October: its sponsor table asks for an engine plus Nightshift as primary provider; the document identifies the event page as binding.
- Hub Meterless README/World Model headless material: minimum-service analysis in `notes/meterless-docs-2026-10-24.md`, supplemented by `notes/meterless.md`.
- Public World Model architecture: `https://github.com/Meterless/Meterless/tree/main/engines/world-model`.
- Runtime provider contract: `https://github.com/Meterless/Meterless/blob/main/docs/agent-ready/add-meterless-provider.md`.
- Runtime edition/setup distinction: `https://www.meterless.ai/nightshift-getting-started.md` and `https://www.meterless.ai/cli.html`.
- Mac availability: `https://www.meterless.ai/mac.html`; the M5+ link resolves to the official installer endpoint. Advertised promotion and a downloadable file are not activation proof.
- Linux installer, read but not executed: `https://meterless.ai/Nightshift/DGX/install.sh`.
- Current project seams: `app/pipeline.py`, `app/state.py`, `app/loop.py`, `app/agents/base.py`, `app/agents/scout.py`, `app/agents/skeptic.py`, `app/evidence.py`, `app/generator.py`, `app/config.py`, `app/models.py` and `app/trace.py`.

Older `AGENTS.md` statements making Cursor mandatory and old calendar/teardown assumptions are
not new authorisation and do not override the refreshed binding rules. `AGENTS.md` is not modified
by this task without its separate write approval.

Review requested: approve or revise this written spec before implementation planning. This document
makes the split design concrete; it does not assert that Nightshift, SSH connectivity, World Model
services or combined acceptance are already working.
