# Meterless — sponsor material and Driftwatch fit

Analysed **9 October 2026 (SGT)**. This is a source-backed digest and an integration recommendation, **not an approved implementation plan or a claim that Meterless is mounted**. Read alongside `notes/host-docs-digest.md`, especially its source-authority and conflict tables.

## 1. Executive recommendation

**Evaluate a minimal World Model integration first; add H-MEM only if it changes a subsequent audit; defer Markovian unless measurements expose a real growing-context problem. Do not implement all three.**

Driftwatch's useful differentiator is an evidence-grounded critic that rejects or re-investigates a finding. Meterless should strengthen that behaviour, not replace the working four-agent loop or add an ornamental sponsor call. The existing decision to ship without sponsor integrations remains in force until a scoped change is approved; the recorded reassessment gate is 17 October.

A meaningful integration must be read by an agent on the actual runtime path, survive relevant failure tests, and emit generated evidence. Merely renaming `RunState` to World Model, storing unused memories, or labelling round caps Markovian would not meet that bar.

## 2. Supplied sources, authority and version comparison

All six files are **supplier material, non-binding**. They explain designs and sponsor expectations, not the binding event rules. Raw documents remain outside the public repository; the table records the supplied bytes without copying them.

| Ref | Supplied filename | Role | Bytes | SHA-256 |
|---|---|---|---:|---|
| A1 | `meterless-agent-engines-index-2.md` | Composition, track/scoring suggestions | 6461 | `3d2f167012de85b4dbef7c4ec681f0bd81855e727de08c5478853962d1bcce79` |
| A2 | `meterless-h-mem-agent-engine-2.md` | H-MEM headless architecture v1.0 | 18100 | `e9bd17fe650e20d8fe41c7d15a8b12cdc4d71caea012bd25f4cc6fd1179f50be` |
| A3 | `meterless-markovian-agent-engine-2.md` | Markovian headless architecture v1.0 | 15810 | `99e74c18743841a03f70052a99adf5531760930264ba05e8830a5dab892ffad3` |
| A4 | `meterless-readme-2.md` | Minimum implementations and integration recipe | 6926 | `c8330fa2832c89789f00369616b496da0dc6864a9c99ae6573a3cb101cb178eb` |
| A5 | `meterless-world-model-agent-engine-2.md` | World Model headless architecture v1.0 | 45353 | `ebccafa42fe79c10a9271d1cb01988f83e915670fdcc072d9abfc96edc5a7509` |
| A6 | `meterless-sponsor-overview.md` | Sponsor entry points and submission attribution | 988 | `a4d938aec4c47744b8e9913cca8464d517aa944198772be9efc77ae26a3e5f41` |

Hash comparison verified **six supplied files, six distinct byte contents**. Against the earlier unsuffixed attachments, A1–A4 are byte-identical. A5 has **one textual change**: §17 removes the sentence fragment naming Neo4j as the knowledge/graph layer. It still calls Meterless the cognition layer. This weakens one old partner reference, but **does not confirm the complete current partner stack** or override the other organiser documents. A6 adds the practical instruction to identify used engines in both README and `metadata.json`.

### Public-primary-source cross-check

The attached documents are reference architectures, not a Python package to install (A4 §1). The public repository additionally offers runnable references and conformance suites; these are useful implementation examples, not evidence that they already work inside Driftwatch.[1]

The public H-MEM guide still describes human approval of dreaming proposals, whereas A2 §9 deliberately replaces that boundary with policy/supervisor decisions. Do not accidentally import the UI assumptions back into this headless build.[2]

Markovian defaults differ: A3 §3 gives carryover 256 and maxChunks 12; the public README gives carryover 800 and maxChunks 24. These are different reference configurations, not Driftwatch requirements. Choose and disclose a bounded configuration rather than mixing them.[3]

The public World Model README describes a six-stage observation path inside a ten-step aggregate cycle. A5 §6 emphasises the aggregate lifecycle. They can be reconciled by separating per-observation validation/append/projection from batch reconciliation.[4]

The sponsor website provides engine entry points/template material. Its memory-plus-long-tasks template retrieves H-MEM before **every chunk**, unlike A3/A4's **first-chunk-only** injection. These are different composition choices: choose one explicitly and account for repeated retrieval rather than silently mixing contracts.[5]

The general GitHub hackathon guide uses a **25% engine-usage rubric and different tracks**.[6] The website links that guide from an Open Agent Hackathon prompt, so this is a substantive conflict with the supplied event-specific sponsor claim (10 points, A6), not proof that one rubric supersedes the other.[5] Neither supplier page establishes the binding event rules: verify the current rubric on HackOS before making a scoring claim.

## 3. What the three engines actually do

### H-MEM: what the agent learned

Source: **A2 §§4–12**, minimum in §13.

- Three layers: short-term/run context, durable working knowledge, validated long-term knowledge.
- Records retain source, confidence, entities, lineage (`derivedFrom`, `supersedes`), and agent/run/task attribution.
- Runtime events acquire knowledge; hybrid retrieval ranks it and returns structured context with selection reasons. Retrieval, not storage alone, is the operational benefit.
- Critic feedback changes future reliability/ranking; contradictions are retained and resolved explicitly rather than silently overwritten.
- Dreaming proposes new knowledge under an approval boundary; sleep consolidates/archives/synthesises under backup/restore guardrails. These are optional advanced stages, not minimum hackathon scope.
- No-model acquisition falls back to direct capture. Sample mode must not need an extraction or embedding API.

**Driftwatch use:** carry forward a validated operational fact such as a resource's scheduled purpose, then retrieve it during the next audit to trigger the right verification rather than confidently repeating an old verdict. A rejected finding is not itself timeless truth: retain its evidence, resource scope, policy version and validity conditions.

### Markovian: how a long investigation carries state

Source: **A3 §§3–8, 11–13**.

- Split a genuinely long task into capped chunks.
- Initial context enters the first chunk; subsequent chunks receive a bounded goal summary and compressed carryover.
- Explicit checkpoint/completion markers govern continuation; the engine strips controls from returned content.
- Compression fallback order: explicit state → model compression → heuristic extraction → last-resort truncation.
- Abort/error handling preserves partial work; optional reflection must not turn a completed run into failure.
- JSONL records expose carryover, completion and estimated token economics.

**Important qualification:** constant *context per step* does not mean constant total run cost or total storage. The savings claim is relative to a naive accumulated-history baseline, not automatically relative to Driftwatch's already-small structured prompts. The public efficiency guide separates modeled results from provider usage and acknowledges compression/tool overhead.[7]

**Driftwatch use:** a future large-tenancy or multi-compartment investigation might justify this. Current code does not send the entire `RunState` transcript on every model call, so adding compression now may add work rather than remove it.

### World Model: what is observed about the tenancy

Source: **A5 §§3–6, 10–13**.

- Canonical entities, contexts and relationships represent grounded shared state.
- Immutable observations retain provenance; canonical/aggregate views are derived rather than independently edited by each agent.
- Stable identity, schema versions and idempotent ingestion support retries and recovery.
- A budgeted context builder returns selected facts plus reasons, so each consuming agent reads the same relevant evidence.
- Enrichment is explicit, bounded work; query/maintenance surfaces make state inspectable without a UI.
- A runtime manifest identifies which helpers are actually wired. **Stored does not mean consumed.**

**Driftwatch use:** join inventory, telemetry windows, IaC declarations and policy evidence around the same resource; make the critic's proof trail reproducible, including which window or degraded source justified a decision. A SQLite-backed adapter and simple typed links are sufficient to evaluate this fit; a graph database is not a prerequisite.

### Composition without conflation

A1/A4: World Model supplies observations and entity identity; H-MEM supplies learned knowledge; Markovian supplies bounded continuation state. All emit audit evidence and route any model work through an injected provider adapter. Historical observations, recalled hypotheses and current authoritative evidence must remain distinct.

## 4. What Driftwatch already has — inspected, not inferred

This is a code-reading assessment on 9 October, **not a fresh runtime/test result**.

| Existing seam | What it already does | Gap against a meaningful engine implementation |
|---|---|---|
| `app/state.py:8–32` | Shared in-memory facts and flushed JSONL events | Constructor opens the state log with `w`; no warm-start replay. Hydration log stores counts, not complete reconstructable observations. |
| `app/evidence.py:12–39` | Resolves finding evidence and rejects dangling refs | In-memory ledger with allocation-order IDs; not a durable, content-deduplicated multi-run store. |
| `app/models.py:15–71` | Typed resources, metric series, IaC, rules and evidence | No general observation envelope with schema/source time, agent attribution and tenancy-isolated relationships. |
| `app/loop.py:89–124` | Loads sources into the shared state | Not yet a transactional, resumable ingestion pipeline. |
| `app/agents/scout.py:110–239` | Joins evidence and generates candidates | Reads and constructs context directly, rather than using a common query/context-builder service. |
| `app/agents/skeptic.py:31–107` | Resolves evidence; checks declared purpose/schedule; requests re-investigation | No persisted learned-fact retrieval influencing a subsequent audit. |
| `app/generator.py:41–43,123–158` | Injected structured generator; model prompts contain the supplied local context | No cumulative transcript in this path; no provider usage retained for savings accounting. |
| `app/config.py:10–16` / `app/loop.py:173–247` | Bounded rounds/resources/rechecks and wall clock | Safety caps are useful, but they are not a Markovian chunk/compression protocol. |
| `README.md:194–198` | Says each sponsor is not mounted | Preserve this disclosure until real code and evidence justify changing it. |

## 5. Smallest worthwhile integration — proposed, not authorised

### Priority 1: minimal World Model

Retain the four agents, deterministic rule outcomes and existing report contracts. Add the **WorldStore + ingest + context-builder** minimum from A4 §3, initially around existing domain models.

1. **Identity and observation envelope.** Resource identity uses its stable external key scoped to tenancy/region, not just display name. Observation identity deduplicates source + resource + measurement window + stable payload. Changed evidence produces a new observation, not destructive replacement. Mask only publication copies and preserve established joins.
2. **Persistence.** Use a schema-versioned local store behind an adapter, with immutable observations and rebuildable projections. Keep data partitions separate for live tenancy and each sample/evaluation scenario.
3. **Ingest/recovery.** Validate provenance, commit atomically and resume after interruption. A retry cannot double the resource count, duplicate a finding or change a prior immutable observation. Signal storage degradation honestly.
4. **Actual consumption.** Route Scout/Skeptic evidence assembly through the context builder. Include source backend, observation time/window, coverage, declared purpose and evidence references; log selected IDs/reasons and exclusions.
5. **Bounded scope.** No UI, broad enrichment queue, new supervisor agent, graph database or cloud service unless a demonstrated requirement demands one. Preserve resource/round/recheck/deadline limits.

**Tests that make it earn its place:** ingest the same observation twice; restart after a partial ingest; rebuild projections; query a resource with conflicting sources; retain both short and long telemetry windows; prove another agent consumes the new context; check scenario/tenancy isolation; run the existing curated and held-out evaluations unchanged.

**Demo:** Scout proposes idle waste; Skeptic reads the resource's shared declaration and telemetry window, requests a wider window, then revises or abstains based on the actual returned evidence. Export the observation IDs/context-selection event and resulting verdict together. Do not invent an outage, revision or source measurement for the demo.

### Priority 2: minimal H-MEM, only with a multi-run acceptance test

Implement the store/retrieval minimum and audit provenance; skip dreaming/sleep/vector infrastructure initially. Exact resource/type matching, recency and reliability can provide a deterministic, credential-free first retrieval strategy, disclosed as a subset rather than full semantic H-MEM.

- Run A learns a scheduled-purpose fact from traceable evidence.
- Run B retrieves it, logs why, and uses it to request verification or an appropriate window.
- Run C supplies changed evidence; the old memory is invalidated/superseded, without hiding the history or treating high confidence as authority.

Fixture inputs may demonstrate this sequence, but each output and memory mutation must be computed by the running agent. Normal evaluation runs need isolated fresh stores so a prior seed cannot leak answers into another seed. A learned fact must never suppress auditing indefinitely or overrule missing/current contrary evidence.

### Priority 3: Markovian only after a measured need

Benchmark current prompts before adding a long-task engine. If needed, carry structured decision state (resource/evidence references, pending verification, uncertainty, coverage and caps), not an opaque narrative that loses the falsifier. Keep raw evidence outside the summary and query it when required.

Measure full input/output usage, compression/reflection overhead and verdict quality against the actual existing pipeline. Provider-reported usage is measured; `chars/4` is estimated; a full-history comparator that Driftwatch never used is hypothetical. No sponsor percentage is a result for this project.

### Do not use memory to disguise the live-history constraint

`docs/decisions.md:434–442` records that the live lab's 744-hour re-check cannot reach the unchanged coverage threshold before submission closes. Recalled purpose can guide a recheck, but cannot manufacture missing datapoints. Use real live abstention and separately labelled fixture-based completed revision as distinct evidence.

## 6. Submission and authority gates

- A6 asks for the engine name and placement in **README and `metadata.json`**. If an integration ships, disclose whether it is a Python adaptation of the headless guide or reused reference code, the implemented subset, fallbacks and generated evidence. Do not claim full conformance unless actually verified.
- **Sponsor eligibility remains unconfirmed:** ask the organiser whether a Python implementation of the supplied reference architecture qualifies, and what minimum proof is required. Do not assume documentation alone earns 10 points, or that all partners must be used.
- Existing track naming comes from HackOS/event pages and an organiser channel, confirmed in `notes/host-docs-digest.md:326–331`. The supplied track names differ; keep the recorded track unchanged until live verification.
- This new A5 removes a Neo4j reference, but does not conclusively settle NVIDIA/Neo4j or official Meterless layer terminology. Use cognition/context to explain the engines technically; verify the event's sponsor wording separately.
- The Meterless workshop is scheduled in the repo for **12 October 2026, 16:00–17:30 UTC (13 October, 00:00–01:30 SGT)**. On the analysis date it is still in the future, despite the notes index's blanket wording about recorded workshops. Verify availability on HackOS; no recording was watched for this analysis.
- Preserve the working packaging, credential-free full pipeline, held-out integrity and demo preparation. Reassess sponsor work under the existing checkpoint; this digest does not silently reverse the no-sponsor decision.

## 7. What was saved and what was not done

This digest, its source inventory, recommendations and unresolved gates are durable project reference. A corresponding Obsidian reference note is linked from the vault index. No product code, fixtures, generated outputs, cloud resources, secrets or public remote were changed for this analysis. Public references were read, not installed or executed.

## Sources

[1] https://raw.githubusercontent.com/Meterless/Meterless/main/README.md
[2] https://raw.githubusercontent.com/Meterless/Meterless/main/engines/hmem/README.md
[3] https://raw.githubusercontent.com/Meterless/Meterless/main/engines/markovian/README.md
[4] https://raw.githubusercontent.com/Meterless/Meterless/main/engines/world-model/README.md
[5] https://meterless.ai/engines.html
[6] https://raw.githubusercontent.com/Meterless/Meterless/main/docs/community/hackathon-guide.md
[7] https://raw.githubusercontent.com/Meterless/Meterless/main/engines/markovian/docs/efficiency-model.md
