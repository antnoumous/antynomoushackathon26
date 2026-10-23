# Driftwatch sponsor integration — proposed bounded design

**19 October approval update:** the builder approved **Option B, policy-first**, and the
planning stage. The [M1 implementation plan](../plans/2026-10-19-zetaris-policy-integration.md)
now details that first milestone, with M2–M5 follow-on boundaries. It awaits plan review and
execution-method selection; no product implementation was authorised by the plan's existence.
The [verified 19 October platform deployment](../../../notes/zetaris-oci-deployed-2026-10-19.md)
supersedes this proposal's historical registry-blocked/unprovisioned descriptions. Technical
access does not resolve the outstanding organiser/licensing interpretations.

**18 October 2026. Architectural proposal for review, not an implemented integration or a reviewed implementation plan.** Prepared while the builder approved continued readiness/design work and was away. No product files, model settings, sponsor objects or cloud resources were changed. New implementation must be attributed to the actual build window; declared preparation and the September baseline remain separate.

## 1. Intent, constraints and success

The objective is a submission-compliant extension of the existing OCI auditor, not a new chatbot or sponsor demo. A judge must see the same bounded four-agent investigation and an evidence-grounded critic, with sponsor components doing actual runtime work. Preserve the programmatic entry point, report meanings, arithmetic/figure guards, live OCI SDK collection, deterministic fixture mode and honest insufficient-history abstention.

The existing user constraints remain: Python, CPU-only judge path, no runtime installs/downloads, no employer data or credentials, no fabricated logs, bounded resources/rounds/rechecks, **540-second hard run budget**. Sponsor-runtime availability must not become a requirement for the credential-free sample run.

Success is **generated evidence of consumption and impact**, not merely connecting to an endpoint, renaming shared state, recording a model name, or storing unused observations. This design does not change the selected track or promise sponsor eligibility; organiser wording about local Meterless/Nemotron/OCI hosting still needs clarification.

## 2. Alternatives and recommendation

| Option | Scope | Trade-off |
|---|---|---|
| A: minimum data insertion | Zetaris policy only; World Model over existing sources; Nemotron explanations | Smallest surface; declaration data remains file-backed and sponsor data story is narrower |
| **B: recommended** | Zetaris policy **and** IaC declarations; minimal persistent World Model consumed by Scout/Skeptic; Nemotron explanations | Bounded, useful reference-data grounding and a complete critic/provenance story without replacing audit decisions |
| C: model-chosen investigation | B plus Nemotron choosing a validated next action/recheck | Genuine new model decision surface, but needs an action schema, permission/evidence validation, adversarial cases and a larger implementation plan |

Recommend **B, delivered policy-first then declarations**, with A as an explicitly disclosed scope reduction only if needed and still eligible. Defer C unless final organiser requirements demand that change. No H-MEM, Markovian engine, graph database, new supervisor, UI, broad enrichment queue, remote pricing catalog or OCI REST-signing bridge in this scope.

## 3. Existing code and required changes — inspected, not inferred

| Current path | Observed role / design consequence |
|---|---|
| `app/sources/__init__.py:18–29` | Fixture branch precedes live imports. Keep it: sample mode must not instantiate sponsor transports. |
| `app/sources/live.py:23–36` | Policy and declarations are file-backed. Add explicit opt-in remote selection; no silently changed default backend. |
| `app/models.py:46–62` | Exact declaration/policy record contracts; `PolicyRule.when` is a dictionary. Remote JSON requires decoding and semantic validation. |
| `app/sources/base.py:24–35` | `SourceResult` has only live/fixture backend and no snapshot/completeness/deadline provenance. Add optional explicit typed metadata; do not invent an already-existing `zetaris` backend enum. |
| `app/loop.py:48–120` | Central source retry/fallback/hydration. Validate whole batches before state projection. Source-returned degraded/reason metadata is currently lost on a successful fetch at `:53–58`; fix propagation as part of the new boundary. |
| `app/agents/scout.py:66–108` | Sibling recovery path also discards successful-result degradation at `:72–74`. Keep both status paths consistent. |
| `app/agents/scout.py:110–205` | Reads shared facts, matches declarations, evaluates policy and builds evidence. These operations must consume the World Model context, not parallel unused storage. |
| `app/agents/skeptic.py:31–107` | Resolves evidence, rejects declared purpose, requests wider windows, and selects verdicts deterministically. Resolve the same grounded observations through shared context. |
| `app/analysis.py:82–100` | Unknown policy predicates are ignored. A remote typo must not broaden a rule's match; whitelist supported keys/types. |
| `app/state.py:11–24`, `app/evidence.py:15–35` | Current state log opens with `w` and hydration stores counts; evidence IDs are in-memory/run-local. These are not durable replayable World Model observations. |
| `app/generator.py:123–158` | Broad exception fallback is silent; validation checks key presence only; JSON response is assumed and `stream=false` is not explicit. Provider use needs observable validation/fallback provenance. |
| `app/config.py:10–16`, `app/loop.py:39–45` | Preserve existing caps and shared monotonic deadline; new transports must actually enforce it. |

The registry-blocked service deployment is separately described in [the OCI runbook](../../zetaris-oci-runbook.md). Its approval does not mean this product design is already implemented.

## 4. Proposed data path and source contract

Live audit: **OCI SDK inventory/telemetry + Zetaris reference policy/declarations → validate complete batches → World Model ingest/projection → Scout/Skeptic context and evidence → existing bounded loop → Writer**, with Nemotron generating permitted explanatory text. Pricing stays in `data/pricing.json` in this scope; it is not automatically federated by a policy adapter.

### 4.1 Runtime transport and permissions

Prefer direct REST for the Python product **if its actual endpoint, permissions and schema work**; retain the supplied JDBC onboarding check as a separate diagnostic route. Do not add the proprietary JAR/JVM to the judge's sample-mode dependency chain. UI-proxy REST is another route and must be labelled/tested independently if chosen.

Use an assigned team namespace and read-only runtime principal. Runtime queries are fixed/allowlisted SELECTs over explicitly configured reference objects, not arbitrary SQL emitted by a model or user. Validate qualified identifiers rather than concatenating unrestricted input. Build-time source registration/DDL and reference publication are separate audited steps; never grant the runtime account creation/admin powers just to simplify setup.

Initially publish only approved public/synthetic reference data. Do not upload private OCI resource IDs, keys, employer declarations or raw telemetry. A platform on OCI is not automatically a zero-copy OCI integration: disclose whether references are immutable exported snapshots or actual source-backed federation. Remote file registration must point to storage reachable by the service; a laptop path is not a remote source. No new storage service is selected by this design before reviewing the actual source-registration capability and permissions.

### 4.2 Row schemas and semantic validation

Policy transport rows: `rule_id`, `class`, `when_json`, `note`, with catalog/schema/version metadata supplied by the batch manifest. Decode `when_json` into the existing dictionary contract; reject malformed JSON, duplicate rule IDs and unknown predicates/types. Supported initial predicates are the keys actually handled by `_matches`: `resource_class`, `compute_instance`, `attached`, `absent_from_iac`, `min_coverage_ratio`, `mean_cpu_lt`, `peak_cpu_lt`, `peak_cpu_gte`. Validate booleans/numeric ranges and finding/resource classes. Restrict rule IDs to the existing R-1–R-5 semantics because deterministic fallback templates are keyed by those IDs; introducing a new rule family is outside this scope.

Declaration rows retain all existing `IaCDeclaration` fields: address, resource type, declared name, file path, last commit, commit message and author. Preserve synthetic/non-Terraform provenance labels; do not convert `not-a-git-repo` into a fabricated commit.

Proposed explicit batch manifest: provider, qualified source object, schema version, query fingerprint, catalog/snapshot version, requested scope, observed/fetched times, actual row count, expected row count or equivalent completion proof, pagination exhaustion, truncation flag and completeness state. Metadata fields are proposed additions, not currently implemented SDK fields.

Initial safety caps: **256 policy records and 1024 declaration records per batch**, independent of the 25-resource audit cap. Query/fetch limits and expected counts must prove no truncation; a server's lower cap is a failure to prove completeness, not permission to accept a prefix. Refuse an oversized catalog rather than treating unreturned declarations as absent.

### 4.3 Snapshot consistency and absence

Use an immutable, versioned reference snapshot for the first integration. Read its manifest/version and only rows assigned to that version, then verify expected count/content identity. Repeated reads/pages must use the same immutable version. A drifting `COUNT(*)` before another query is not a snapshot guarantee; do not assume the federated service provides a multi-query transaction when it has not been verified. If the source cannot supply a consistent version/completion proof, treat that batch as incomplete and do not claim the adapter gate passed.

Distinguish **empty-complete**, **incomplete/truncated**, **unavailable** and **malformed**. A complete empty catalog can justify absence; all other cases mean unknown membership. Incomplete/unavailable declarations must suppress any finding whose premise requires known absence or known declaration membership and annotate affected resources as undetermined. Independently justified volume/IP rules may still run when their own inventory/policy premises are complete. Never erase unmatched inventory through an inner join.

Fallback fixtures remain explicitly degraded and retain their own scenario/backend provenance. They may not become successful live sponsor evidence or overwrite a complete live projection as though they were a newer authoritative source.

## 5. Minimal Meterless World Model

Implement a disclosed Python adaptation of the supplied World Model minimum: **store + idempotent ingest + context builder**, initially using standard-library SQLite and typed relationships. Public reference material describes stable identity, immutable observations and rebuildable/queryable projections; it is not proof of an already-mounted Python package.[M1]

Proposed observation envelope:

- schema version and isolated partition (`live tenancy/region` or one sample/evaluation scenario);
- canonical resource/entity key; source/provider/object/snapshot;
- source observation time and exact telemetry window/resolution/coverage, where relevant;
- normalized payload and canonical payload hash;
- source completeness and lineage/conflict/supersession links;
- ingestion receipt with run/agent/time attribution.

Observation identity uses partition, source/snapshot, canonical entity, measurement window and canonical payload—not receipt time or run ID. Identical retries deduplicate; receipt attribution is separate. Changed evidence appends a new observation. Display-name/normalised-name matches remain labelled inferences, not stable resource identity. Real live identities stay private; mask publication copies while preserving joins.

Validate a whole source batch before an atomic commit. Only committed complete/explicitly degraded batches become eligible context; no half-ingested projection appears after a crash. Keep multiple telemetry windows and conflicting declarations rather than overwriting the evidence that triggered re-investigation. A later incomplete batch cannot silently erase a complete historical snapshot, and historical state cannot masquerade as current evidence.

Proposed service surface (names are design proposals):

| Method | Responsibility |
|---|---|
| `ingest_batch(manifest, observations)` | Validate, deduplicate, atomically commit and return receipt/status |
| `resource_context(partition, resource_id, window, budget)` | Return relevant inventory, declarations, rules, telemetry, conflicts, completeness and selected IDs/reasons/exclusions |
| `resolve_observations(partition, ids)` | Retrieve exact immutable evidence within the permitted partition |
| `rebuild_projection(partition)` | Reconstruct equivalent query views from committed observations |
| `export_provenance(partition, run_id)` | Export sanitized ingest/context-selection/verdict lineage |

Scout must read `resource_context`; Skeptic must resolve the same selected observations and query relevant contrary purpose/schedule/window evidence. Preserve existing public report evidence IDs by linking them to durable observation IDs in payload/provenance rather than implying allocation-order IDs are cross-run identities. A transitional shared-facts projection is acceptable only if those agent consumers demonstrably use it and context-selection provenance remains visible.

If local persistence fails, continue only through an explicitly recorded in-memory degraded store with the same validated current-run contracts; do not claim persistence/restart proof for that run. Existing historical telemetry sufficiency thresholds remain unchanged. No memory or projection can create missing metric hours.

## 6. Nemotron: actual role, candidate and validation

**Honest default role:** generate finding explanations, critic reason text and report prose through the existing `Generator` seam. Current rule matching and critic branch selection are deterministic; neither a Nemotron model ID nor generated prose makes the model the verdict decision-maker. Confidence returned by the model is not calibrated evidence certainty. Option C would be a distinct later architecture change.

As checked against current official pages on 18 October, **`nvidia/nemotron-3.5-lightning-30b-a3b`** is a hosted candidate to capability-test, with the documented NVIDIA base `https://integrate.api.nvidia.com/v1`.[N1] It has **not** been called for this project. Do not treat it as a proven replacement for the current configured provider. Preserve `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` as the product's existing environment seam; the organiser tutorial's differently named settings do not automatically configure Driftwatch.

Required candidate capability probe, once legitimate access is available:

1. Explicit **`stream=false`**, a bounded `max_tokens` (initially 1024) and an intentionally chosen thinking mode. The hosted reference defaults streaming on and documents **202 pending**; current code assumes a normal JSON completion, so a provider-name-only switch is unsafe.[N2]
2. For this short structured-generation role, request thinking disabled through the model-supported parameter and validate actual behaviour. The public model example exposes `chat_template_kwargs.enable_thinking`; exact acceptance must be tested on the selected hosted route. Do not copy a self-hosted NIM parameter name into the hosted request without checking its contract.
3. Test `response_format=json_object` support explicitly. Self-hosted NIM examples support JSON mode, but that is not evidence every hosted model accepts `guided_json`, `json_schema` or identical fields.[N3] If the selected route cannot meet the required generation contract, record the result and assess a documented alternative; do not silently claim compatibility.
4. Strictly validate object type, required keys, scalar types/ranges, extra fields, nonempty text and finish reason. Reject truncated, reasoning-prefixed or malformed output; do not repair invented financial/telemetry figures into evidence. Preserve the existing figure guard over all published prose.
5. Treat pending/throttled responses as bounded states, not successful completions. Poll only through the actual documented API within the shared budget, otherwise fall back explicitly.
6. Emit generated provider events: requested/returned model, sanitized provider identifier, latency, finish reason, provider-reported usage where present, schema validation outcome, context hash/observation IDs and fallback category. Never log keys, raw auth/server bodies or private prompts. A run using only deterministic fallback is **not** Nemotron integration evidence.

No local weights, GPUs or model downloads are needed for the judge path. API account limits, costs and current endpoint entitlement must be checked separately. Optional prompt-library use, provider routing and mounted World Model behaviour are different claims; disclose each accurately.

## 7. Deadlines, retries and failure semantics

Preserve existing 3-round/25-resource/2-recheck caps and the overall monotonic deadline. Reserve **five seconds** for final report/trace flush; do not start new external work once its usable budget is exhausted.

Proposed new transport bounds: source operation at most **30 seconds**, model operation at most **60 seconds**, each further limited by the usable remaining budget. Preserve at most one source retry at the orchestration level; do not multiply it through hidden client retries. No model retry in the minimum path; deterministic fallback is immediate and observable on a failed/invalid generation.

A Requests connect/read timeout alone is not a total response-download deadline.[R1] For the new HTTP boundaries, use a parent-supervised cancellable worker process with an absolute cutoff; terminate and reap it when the operation/run budget expires. Do not leave timed-out background threads or requests running after a report claims completion. The sample path never spawns network workers. The written implementation plan must exercise this mechanism across the actual execution environments rather than asserting timeout correctness from configuration alone.

After deadline expiry: no one-second model-call floor, no new auth/query/poll operation, no retry/backoff. Existing `ModelGenerator.current_timeout()` floors to one second and needs a regression-backed correction at this new boundary. Source failures must be classified and sanitized: authentication, transport, deadline, query, parse/schema, incomplete snapshot and storage failure. Propagate source-returned degradation through **both** orchestrator and Scout recovery paths.

## 8. Acceptance matrix

These are future acceptance tests, not completed sponsor results:

| Gate | Required evidence |
|---|---|
| Offline integrity | Full four-agent sample run with sockets blocked and sponsor/model variables absent; no live imports, child network workers or downloads |
| Baseline parity | Same complete reference rows produce equivalent curated/held-out findings, critic outcomes and arithmetic; new degraded/unknown cases explicitly asserted |
| Real Zetaris consumption | Generated trace names provider/object/version/count/observation IDs; changing an approved synthetic reference changes an appropriate computed match, finding or critic outcome |
| Remote completeness | Empty-complete differs from unavailable; duplicate IDs, stale/mixed versions, truncation, unknown predicates and malformed JSON fail safely |
| No false absence | Missing/incomplete declarations cannot produce authoritative `absent` evidence or dependency-based shadow findings |
| World Model durability | Duplicate ingestion, interrupted ingest/restart, projection rebuild, changed payload, conflicting observations and short/long windows preserve invariants |
| Isolation | Live and every sample/held-out seed have separate partitions; no answer or historical-evidence leakage |
| Agent consumption | Both Scout and Skeptic emit actual context-selection/observation-resolution events; storage alone fails the gate |
| Model capability | Authenticated candidate returns accepted structured output; stream/pending/thinking/finish/usage handling verified; true fallback reported |
| Budget | Slow connect/body trickle, 202 polling, retry and store contention cannot exceed the total-operation/run contract or leave workers behind |
| Security | SQL/object allowlists, read-only service principal, no raw secret/server-response logging, no unsafe public ports; no employer/private data uploaded |
| Packaging/disclosure | Fresh CPU-only sample setup passes; README/metadata identify actual subset, generated evidence, adapted code/licence, model role and unresolved limitations |

The existing unmodified suite was run in the parent task: **116 passed**, one deprecation warning. That is baseline verification only; it does not satisfy this matrix.

## 9. Build sequence and exclusions

Preparation now: finish read-only OCI/bundle/cost assessment, propose interfaces/acceptance tests, preserve source/version evidence and obtain legitimate sponsor access. **No implementation plan or product code was executed under this proposal.** New submission work belongs in **22 October 2026 00:00 → 27 October 2026 23:45 UTC**, with the prior baseline declared.

After written-design review and the corresponding implementation-plan stage:

1. Establish source manifest/semantic validation and safe unknown-membership/degradation handling.
2. Prove the policy adapter with real source consumption and fixture parity; add declarations only after completeness/version mapping works.
3. Mount minimal World Model ingest/context consumption in Scout/Skeptic with isolation/restart proof.
4. Capability-test the chosen Nemotron route and observable structured generation; preserve deterministic safety.
5. Run the complete acceptance/evaluation/packaging gates and produce generated demonstration evidence.

Keep within the project's recorded attention budget. If scope must shrink, explicitly revisit B versus A and eligibility rather than ship untested persistence or rename existing structures to claim a sponsor engine. No public UI, new findings, cloud-pricing virtualization, arbitrary model SQL, model-chosen verdicts, H-MEM, Markovian, graph service or cross-tenant deployment is included.

## 10. Open decisions, not invented facts

- Written design review and subsequent implementation plan/execution method. The builder approved continued preparation while away; that does not establish review of this not-yet-existing artifact.
- Final track/challenge and pre-existing-baseline declaration; OCI-hosting interpretation; Meterless minimum qualifying Python adaptation; exact Nemotron runtime requirement. No organiser message was sent on the user's behalf.
- Actual assigned Zetaris reference-object names, reachable source publication and consistent-snapshot proof. No source registration is assumed successful.
- Authenticated hosted model compatibility and provider limits; no model call or API-key change has occurred.
- Platform startup/registry/entitlement gates remain separate from this product proposal.

## Primary sources and provenance

[M1] https://raw.githubusercontent.com/Meterless/Meterless/main/engines/world-model/README.md — public reference architecture, not installed conformance proof. Read alongside the supplied headless guide inventoried in `notes/meterless.md`.

[N1] https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b — current candidate and advertised hosted endpoint.

[N2] https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-5-lightning-30b-a3b-infer — hosted request/defaults/pending responses; parent directly retrieved this page.

[N3] https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started-nemotron-3.5-lightning.html and https://docs.nvidia.com/nim/large-language-models/1.15.0/structured-generation.html — versioned self-hosted examples, not blanket hosted compatibility guarantees.

[R1] https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts — timeout semantics.

Repository path/line references above were checked against the working tree on 18 October. The dirty baseline was preserved; no commit/push, product edit, sponsor query, credential publication or infrastructure write was performed.
