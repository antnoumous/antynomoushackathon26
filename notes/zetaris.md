# Zetaris — meeting analysis and Driftwatch fit

**Assessed: 14 October 2026 (SGT).** Technical recommendation, not approval to implement, switch track, spend money or extend the lab's lifetime. No Zetaris or Meterless integration is mounted.

**17 October supplement:** [supplied documentation assessment](zetaris-docs-assessment-2026-10-17.md)
reviews the new pinned JDBC prompt and full link set. It qualifies §7's REST-first advice:
JDBC is the supplied onboarding workflow; the eventual Python runtime protocol is a
separate readiness-gated choice. It also records concrete preflight/timeout caveats,
reconfirms the published event requirements, and lists access/approval gates. No service
was queried or deployed.

## 1. Bottom line

**Zetaris can usefully supply Driftwatch's policy and IaC declaration data at runtime, without replacing the four agents or the OCI SDK. More importantly, the current published rules require Zetaris and Meterless integrations and Cursor development. The existing no-sponsor build is a pre-existing baseline, not a compliant submission as it stands.**[1]

The event has moved to **22 October 2026 00:00 UTC → 27 October 2026 23:45 UTC**: **22 October 08:00 SGT → 28 October 07:45 SGT**.[1] The old 15–20 October calendar is superseded. This is confirmed by direct retrieval of the live event page and its expanded-rules page payload, not by relying on the meeting alone. The sponsor's current onboarding guide independently repeats 22–27 October.[12]

Recommended order: resolve entry/track eligibility and sponsor access; prove one authenticated Zetaris query; then approve the smallest runtime data integration plus the previously proposed minimal Meterless World Model. Keep the credential-free full pipeline and existing critic behaviour intact. Do not add a new cloud account or provision anything for this analysis.

## 2. Sources and authority

| Source | Authority and limits |
|---|---|
| `OCI-meeting-2026-10-14.txt` | Supplied automated transcript. Capture starts `2026-10-14T08:47:58.001Z`; this is a capture timestamp, not proof of the original broadcast date. Sponsor technical guidance and organiser remarks, not the binding rulebook. Cite by System-output timestamp. |
| Live event page, including expanded Rules §§3–7 | **Published rules**, higher authority than the older working draft and meeting paraphrases.[1] |
| Academy course FAQ | Current organiser guidance, but disagrees with the event page on NVIDIA and prize details. It defers final required technology details to the “How the Week Runs” lesson.[2] |
| Zetaris `getting-started` repository | Official supplier installation, connections, recipes and client implementation. Evidence of documented interfaces and prerequisites, not proof of a successful Driftwatch integration.[5][6][7][8][10][13][14] |
| Driftwatch source files and existing decisions | Evidence of what this project currently implements, not authority over event eligibility. |

The supplied attachment is **50,195 bytes**, SHA-256 `e7b6bd972c4dee4a30cf691a7b3165da34ca4f013232f9769a7fa69dd4524d1f`. The whole file was read. Microphone entries are unrelated background conversation and were excluded from the analysis and publication; raw transcript bytes were not copied into the repository. Capture gaps and the final transcription failure limit completeness.

Direct HTTP retrieval was used because the extraction backend could not extract URLs and the automation browser was unavailable. The event's server-delivered React payload contained the expanded official rules. A search result returned an obsolete 7–9 October version of the same event URL; **that indexed copy was not used to set the calendar**. Public page/guide snapshots were retained in local scratch during analysis, not committed as raw supplier material.

## 3. What changes for our entry

| Area | Current live source | Consequence |
|---|---|---|
| Sponsors | Rules §5 requires Zetaris, Meterless and Cursor development.[1] | Sponsor work is no longer merely an optional scoring stretch. |
| NVIDIA | Event rules say integrate where it contributes; Academy says run on Nemotron.[1][2] | Confirm the operative requirement with the organiser; do not silently replace the current model. |
| Existing code | Rules §§4–5 allow declared pre-existing components/product code.[1] | Disclose the September baseline and separately identify new window work. |
| Track | Three challenge tracks and Wildcard [Tinkerer]; no “Autonomous Agent” option.[1] | Obtain a new user-approved selection. |
| Submission | Demo 1–4 minutes, slide deck, GitHub/README and sponsor/development explanation.[1] | Add a slide deck; the old deliverable list is incomplete. |

**Track recommendation (not selected):** Wildcard [Tinkerer]: Bring Your Own Project is the clearest route for extending an already-built Driftwatch baseline. If the organiser confirms a declared baseline is appropriate in a main challenge track, **The Agent That Can Explain Why** is the strongest fit for the critic/evidence story; **Solving Fragmented Intelligence** fits a genuinely useful federated data addition. The published page calls Wildcard a bonus track while requiring exactly one primary selection: confirm how that maps to the actual submission form rather than assuming a dual entry.[1]

**Administrative gate:** at transcript `08:50:00–08:50:13Z`, the organiser says solo participants still need a team account and submissions go through that team. This analysis did not inspect or create the user's HackOS team. At `09:24:37Z`, the organiser says the actual challenge statements will be announced on the day: retain the use case, but check the final challenge before treating its fit as settled.

### The shifted window affects the OCI lab

The existing **21 October teardown plan now precedes kickoff**. Do not automatically cancel teardown or keep paid resources longer: verify the lab's own credit balance/expiry and obtain approval for any retention change. The 13 October expiry note attributes the notice to the original tenancy, not the live lab; it does not verify the lab's balance or expiry.

The prior “744-hour re-check cannot become sufficient before submissions close” conclusion was made against the old deadline. Its recorded earliest continuous-span estimate, **23 October 06:27 SGT**, is now inside the build window. A completed live wider-window verdict is therefore a **possibility to measure**, not a proven result. Actual returned coverage, hourly resolution, source availability and the real critic path must still justify it. Do not lower the coverage threshold, alter declarations or invent missing telemetry. Keep the preserved originals and the offline demo.

## 4. What Zetaris actually contributes

At transcript `08:56:09–09:00:24Z`, Zetaris is presented as a federated SQL engine: register sources, define a Unified Semantic Layer (USL) of tables/relationships, then query it from an external client. At `09:07:44–09:08:23Z`, the presenter explicitly separates the running agent loop from Zetaris and describes REST or JDBC between them. The official connection guide documents both routes.[14]

For Driftwatch that means:

- **Zetaris:** consistent access to reference data and, eventually, joins across evidence sources.
- **Meterless World Model (proposed separately):** grounded observations, provenance and shared context actually consumed by agents.
- **Existing four-agent loop:** investigation, critique, re-check decisions and reporting.
- **OCI SDK:** authenticated inventory and telemetry retrieval.

These roles should remain distinct. SQL federation is not a critic, USL is not automatically persistent learned memory, and merely using Zetaris from a coding assistant does not prove the running audit uses it.

The meeting's business advice also supports the use case: `09:15:49–09:16:56Z` emphasises prioritised actionable insight and combining sources. Driftwatch's strongest story is **which apparent waste is actually actionable, and why a critic rejected or re-investigated it**—not another utilisation dashboard or a new OCR feature.

## 5. Actual code seams — inspected on 14 October

| Code | Existing behaviour | Proposed change, if approved |
|---|---|---|
| `app/sources/base.py:24–35` | `Source.fetch(Scope)` returns records with live/fixture provenance. | Add an adapter returning the same record contracts; retain explicit provider/query provenance separately. |
| `app/sources/__init__.py:18–29` | Sample mode selects fixture adapters and imports no live backend. | Preserve this early branch: sample mode must not contact Zetaris. |
| `app/sources/live.py:23–36` | IaC and policy remain file-backed in live mode. | Opt-in Zetaris implementation for those two sources. |
| `app/sources/policy_fixture.py:10–18` | Reads `policy.json` rule records. | Smallest single-source insertion point. |
| `app/loop.py:89–124` | Loads validated resources, declarations and policy rules into shared state. | Keep hydration contracts and critic loop unchanged. |
| `app/agents/scout.py:142–205` | Matches declarations, evaluates rules and attaches evidence. | Returned reference records must actually drive these decisions. |
| `app/agents/scout.py:214` and `app/analysis.py:38–47` | Pricing is independently read from `data/pricing.json`. | **A policy adapter does not virtualise pricing.** Leave pricing unchanged initially; a remote pricing catalog would need a separate approved change. |

**Recommended minimum:** provide the existing policy catalog and IaC declarations through Zetaris, queried at runtime using fixed, read-only queries. This gives the sponsor a real job in the false-positive story: the rule proposes a candidate; the declaration supplies the scheduled/intentional purpose that the critic checks. Start with policy only to prove the adapter, then add declarations if access and schema mapping work. Do not claim a multi-source federated investigation after only mounting one JSON rule file.

The first semantic model can expose rule identifiers/classes/conditions/notes and declaration addresses/names/files/commit metadata. Exact SQL and remote object names must be derived from the actual instance schema and assigned team namespace; none were created or assumed here. If using imported snapshots rather than source-backed federation, disclose that accurately—do not call an exported snapshot “zero-copy live OCI”.

### Why not replace the OCI adapters?

The documented REST recipes demonstrate source registration and JSON flattening, not verified OCI control-plane/Monitoring integration.[11] OCI request signing, inventory pagination and time-window query behaviour are already handled by the existing SDK adapters. A generic REST-table example does not establish that those requirements work through Zetaris. Keep the working SDK path, and defer any inventory/telemetry bridge until there is a measured reason and explicit scope approval.

## 6. Deployment choice

### First choice: ask for shared event-instance access

The current README and Start Here explicitly describe an existing/shared event instance.[5][12] Obtain the actual URL, account, numeric organisation ID, assigned team prefix and query/create permissions. The connection docs distinguish the **UI proxy** from the **direct REST API**; do not interchange their URLs or guess a driver's location.[10][14]

Only already-public/synthetic policy and declaration data should be used on a shared instance initially. No employer data, private OCI keys, unmasked telemetry or personal resource identifiers should be sent there. Confirm permissions before registering objects, and never change another team's namespace.

### Second choice: local Docker on the personal Mac

The local machine was inspected: **arm64, 32 GiB RAM, 12 logical CPUs, 329 GiB available disk**, and no `docker` executable on PATH. It has nominal host capacity, but **Docker installation, allocated resources and amd64 emulation are still prerequisites**, not verified capabilities.

The official guide recommends **4 CPUs, 8 GB RAM available to Docker and at least 15 GB disk**, with preflight failing below 6 GB memory. Its platform images are **amd64**; Apple Silicon needs emulation.[6] Start Here directs Apple Silicon users to enable Rosetta as the portal instructs.[12] Local setup is possible on paper, but no bundle was downloaded, daemon installed or container run here.

Do not put this new sponsor service on the OCI A1 lab by default: it adds an emulated amd64 stack, changes the audited workload and ties sponsor availability to the lab's unresolved expiry. The work-machine clone remains sample-only; do not transfer personal credentials or install the sponsor stack there without explicit approval.

### Correct the transcript's risky shorthand

- At `09:00:51Z`, “80GB” conflicts with the later spoken 8 GB and the official guide. Use the documented sizing, not an assumed 80 GB requirement.[6]
- “Free forever” in the meeting is **not sufficient evidence of our platform entitlement**. The installation guide requires a licence/evaluation entitlement, describes a limited evaluation without an Order and says the Apache repository licence covers recipes, not platform images. Confirm the hackathon entitlement with Zetaris before promising indefinite use or redistributing a bundle.[6]
- AWS is not needed to begin. The local guide includes a credited AWS option, not a zero-bill guarantee.[6] No AWS account, spend or provisioning is recommended by this analysis.

## 7. What would prove the integration

These are proposed acceptance gates, not completed work:

1. **Access:** authenticated `SELECT 1` returns the actual expected row through the chosen client route. The PokéAPI starter proves external-source connectivity only; it is not the Driftwatch integration.[9][14]
2. **Schema and completeness:** real Zetaris rule/declaration rows map to `PolicyRule`/`IaCDeclaration`. Check types, JSON conditions, nulls, explicit limits and independent row counts. The connection guide notes REST string values and result limits; the REST HOWTO calls for independent source-count comparisons.[10][11]
3. **Runtime consumption:** a full audit fetches the reference rows from Zetaris, logs query/provider/object/version/count provenance without secrets, and the Scout/Skeptic uses them. Prove a source change can affect an appropriate finding/critic decision in an isolated synthetic test, rather than a decorative `SELECT 1` call.
4. **Parity:** equivalent fixture and Zetaris reference records yield equivalent findings, critic rulings and arithmetic. Re-run curated and held-out evaluations.
5. **Failure:** test timeout, authentication failure, malformed records, truncation and unavailable service. Raise `SourceError` into the existing degradation path rather than silently succeeding; report fixture fallback and actual backend. Never substitute historical CPU data as current live evidence.
6. **Bounds:** trim external timeouts to the remaining run budget; cap retries and returned rows. The supplier's `zetaris_sql.py` uses a **600-second** REST timeout, longer than Driftwatch's **540-second** hard budget; do not copy it unchanged.[8]
7. **Offline:** prove sample mode still executes all agents with sockets blocked and no sponsor/model credentials; a separately verified live sponsor run supplies integration evidence.
8. **Packaging/disclosure:** document the implemented subset, runtime data path, actual Cursor development, model choice, any adapted source code, platform entitlement and judge reproduction route. The required sponsor explanation must reflect executed code.[1]

For Python, prefer the documented HTTP path first to avoid adding a JVM/JDBC-driver dependency. The UI helper uses org-scoped authenticated requests with a 30-second timeout; its query helper and the direct REST runner use different routes.[7][8][13] Fetch the real instance contract and test the chosen path before implementation. Use scoped read-only runtime access; DDL/setup permissions are a separate build-time concern.

## 8. Decisions still needed

- Confirm HackOS team setup, the operative NVIDIA/Nemotron rule, the pre-existing-baseline declaration and the chosen track.
- Obtain shared Zetaris instance access or approve local installation and confirm licence entitlement.
- Approve a bounded policy/declaration adapter and minimal Meterless World Model scope. The old optional-sponsor gate cannot remain the eligibility strategy under the current published rules, but this analysis does not authorise product changes.
- Decide whether to retain the OCI lab past 21 October only after checking its own balance/expiry, with explicit cost/teardown approval. Offline operation remains independent.
- Inspect the actual final challenge statement and organise a slide deck plus a generated integration demo.

**Not done:** no sponsor instance queried, login performed, container installed, reference object created, Cursor use verified, live OCI audit run, track changed, cloud resource modified or remote repository pushed. This is a source/code assessment and documentation update, not an executed sponsor integration.

## Sources

[1] https://hackathon.genai.works/event/open-agent-hackathon-2026
[2] https://academy.genai.works/courses/open-agent-hackathon-2026/details
[5] https://raw.githubusercontent.com/zetaris/getting-started/main/README.md
[6] https://raw.githubusercontent.com/zetaris/getting-started/main/docs/install/updated_zetaris_installation_guide.md
[7] https://raw.githubusercontent.com/zetaris/getting-started/main/scripts/zetaris_api.py
[8] https://raw.githubusercontent.com/zetaris/getting-started/main/scripts/zetaris_sql.py
[9] https://raw.githubusercontent.com/zetaris/getting-started/main/docs/guides/first-dataset.md
[10] https://raw.githubusercontent.com/zetaris/getting-started/main/docs/connections/cursor-connection.md
[11] https://raw.githubusercontent.com/zetaris/getting-started/main/open_data/rest_apis/HOWTO.md
[12] https://raw.githubusercontent.com/zetaris/getting-started/main/START-HERE.md
[13] https://raw.githubusercontent.com/zetaris/getting-started/main/scripts/query_zetaris.py
[14] https://raw.githubusercontent.com/zetaris/getting-started/main/docs/connections/README.md
