# Host documents — digest

Digest of the twelve documents shared by the organisers, read on 2026-09-24.
Source files live outside the repo (attachments); this file is the reference copy.

**Read this alongside `docs/event-brief.md`.** They disagree in places — see
[Conflicts with this repo](#conflicts-with-this-repo) before trusting either.

---

## 1. What was shared, and how binding each one is

| File | What it is | Authority |
|---|---|---|
| `official-rules.md` | 24-section rules document | **WORKING DRAFT.** Header says the binding rules are on the event page. Contains `[VERIFY]` and `[LEGAL]` markers. Do not treat as final. |
| `a072c660079743618ec31252a7b8409d.pdf` | Participant onboarding deck, 14 Oct | Organiser deck. Good for facts, silent on detail. |
| `submission-requirements.md` | Technical execution guide | Recommendation, "not a rule unless the Rules say so" |
| `technical-execution-requirements.md` | Byte-identical duplicate of the above (md5 `473f0054…`) | Same document, two filenames |
| `disqualification-checklist.md` | Pre-submission self-check | Preparation guidance; says the binding disqualifiers are in the Official Rules |
| `ai-usage-policy.md` | AI use during the event | Policy, Rules override it |
| `code-of-conduct.md` | Conduct | Policy, Rules override it |
| `meterless-agent-engines-index.md` | Index of the three engines | Sponsor material, non-binding |
| `meterless-readme.md` | How to use the engines | Sponsor material, non-binding |
| `meterless-h-mem-agent-engine.md` | H-MEM: shared memory | Sponsor material |
| `meterless-markovian-agent-engine.md` | Markovian: long-task reasoning | Sponsor material |
| `meterless-world-model-agent-engine.md` | World Model: shared world state | Sponsor material |

Every one of the four guidance docs repeats the same escape clause: **where it disagrees
with the Official Rules on the event page, the Official Rules win.** The `[VERIFY]` items
are the host's own to-do list, not ours.

---

## 2. The facts that matter

- **Event:** Open Agent Hackathon 2026, GenAI Works. Fully online, free, worldwide, 16+.
- **Build window:** 15 Oct 00:00 → 20 Oct 23:45 UTC. 144 hours. Hard deadline.
- **Registration closes 13 Oct 00:00 UTC.** Judging opens 20 Oct 00:00, while submissions
  are still arriving. Results 30 Oct 16:00 UTC, live call.
- **Platform:** HackOS. Announcements there are the official source of truth. Check daily.
- **Partners, one layer each:** Zetaris **data**, Neo4j **knowledge**, Meterless
  **cognition**. Sponsor Tech = 10 points, not mandatory.
- **Scoring (100):** Impact 30 · Technical 20 · Innovation 15 · Demo 15 · Product & UX 10
  · Sponsor Tech 10. Ties for 3rd decided on Impact.
- **Prize pool:** "up to $20,000". No breakdown given in any of these documents.
- **Models/frameworks open.** Any provider, incl. closed-source and paid. The framework
  itself is not scored. You pay for your own API calls.

### What the deck says the mission is

> "Not another chatbot. An agent that does the work." Find information, understand how the
> pieces relate, reason across several steps, hold on to what matters, turn it into an
> outcome someone can use.

Weak vs strong, per the deck — worth reading as a spec:

| Weak | Strong |
|---|---|
| A fixed chain: A → B → C | Tasks delegated based on context |
| Agents that are prompt wrappers | Outputs challenged and revised |
| No critique, no validation | Planner / executor / evaluator loops |
| No shared state or memory | Shared context carried across steps |
| No retries or recovery | Branching, retries, escalation |
| A demo path that only works once | Traces showing how it got there |

"Quality of interaction matters more than number of agents."

---

## 3. The four tracks (real names)

Pick **exactly one**. Name, from the deck and the Rules:

1. **Fragmented** — query information scattered across disconnected systems, APIs and
   databases; turn it into decisions, reports or recommendations.
2. **Autonomous Intelligence** — investigate complex questions across multiple sources,
   connect findings, produce evidence-backed answers.
3. **Persistent Memory Agents** — remember previous interactions, maintain state, continue
   useful work across longer-running tasks.
4. **Real-World Industry Agents** — one industry or community, a concrete operational
   problem that could realistically be used in practice.

`[VERIFY]` still open in the Rules: whether you may change track mid-window, and whether
multiple submissions across tracks are allowed.

---

## 4. What the submission contains

From the deck (section 6 of the Rules is the binding list):

1. Working prototype — runs from a clean setup
2. Demo video — 2–3 minutes, agent in action
3. Architecture notes — agent roles, flow, tools, decisions
4. Repository — README, run instructions, env guide
5. Logs or traces — evidence of how the agent worked
6. Sample inputs and outputs — enough to show more than one case

The self-check guide gives the layout a judge can navigate without help. Not mandated, but
it is clearly what the docs were written around:

```text
/project-root
│── app/                 # Core agent logic
│── data/                # Small samples or download scripts
│── scripts/             # Helper scripts
│── run.py               # Entry point
│── requirements.txt     # Dependencies
│── Dockerfile           # Strongly recommended
│── input_examples/      # ≥3 sample inputs
│── output_examples/     # ≥3 matching outputs
│── logs/                # Agent traces
│── .env.example         # Placeholders only
│── README.md            # Setup, run, architecture, limitations
```

### What does not meet the bar (Rules §7.3)

- A fixed chain with no feedback, critique or validation
- Prompt wrappers, or one agent with several labels
- Hardcoded outputs or fabricated agent activity
- A UI with no working system behind it

---

## 5. The technical standard — the ten-rules-in-one-line version

Runnable · Reachable · Reproducible · CPU-compatible · Bounded · Secure · Data-conscious
· Observable · Agentic.

Concretely:

| Area | Standard |
|---|---|
| Startup | Clean checkout + one documented command, no manual fixing |
| Interface | **Programmatic entry point**, not only a UI — e.g. `POST /run` taking JSON and returning JSON |
| Build | Docker, or fully documented setup; **nothing installs after the app starts** |
| Hardware | CPU only. No GPU, CUDA, drivers or local weights needing an accelerator |
| Runtime | Full run in minutes. Timeouts: API 10–30s, model 30–90s, agent iteration 1–3 min, run target 5–10 min. **Cap agent loops** — unbounded debate is the top cause of a hung run |
| Secrets | Env vars only. `.env.example` placeholders only. `.env` gitignored. Never in logs or on screen |
| Data | Small samples in repo, or automated download scripts (no login, no manual clicks), or runtime public APIs with timeouts + fallback |
| Logs | stdout **and** `logs/`, one JSONL file per run, `logs/trace-<run_id>.jsonl` |
| Examples | ≥3 inputs and ≥3 matching outputs |
| Sample mode | `SAMPLE_MODE=true` runs everything with **no credentials and no network**, on cached data, still executing real agent logic |

If the API binds inside Docker it must bind `0.0.0.0`, not `127.0.0.1`.

### Logs are the score

Technical and Demo both rest on them. Required shape per line:

```json
{"timestamp":"2026-10-17T18:42:11Z","run_id":"demo-001","agent_name":"Planner",
 "action":"delegate_task","input_summary":"…","output_summary":"…",
 "target_agent":"Researcher","confidence":0.91,"retry_count":0,"status":"success"}
```

What they must show: ≥2 named agents doing distinct things · handoffs · critique or
validation · retries/fallbacks/recovery · the final synthesis · errors and what happened
next · statuses · and they must correspond to the input actually being processed.

Weak: `Agent A -> Agent B -> Agent C -> final answer`.
Strong: planner requests evidence → researcher returns findings with uncertainty →
planner asks evaluator for critique → evaluator flags a missing source → planner requests a
narrower retry → revised evidence → evaluator approves → writer synthesises.

**Never hand-write a trace.** A trace that doesn't match the code is an integrity problem,
not a shortcut.

### The one test people skip

```bash
rm .env
docker run --rm -p 8000:8000 -e SAMPLE_MODE=true oah-submission
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" -d @input_examples/example_1.json
```

Judges may not have credentials for whichever provider you picked. This is how they will
experience the project.

---

## 6. Integrity rules (AI policy)

Allowed and encouraged: AI inside your agent, AI-assisted coding, vibe coding, AI-assisted
documentation, prompt engineering, testing. Closed-source models and paid APIs. Any
framework. You remain responsible for every line — "the AI wrote it" is not an answer to a
judge.

Not allowed — each is a disqualification trigger:

- Hardcoded outputs: same answer regardless of input, known-input→prewritten-output
  mapping, final answers stored in files, a demo-only branch, faking model calls
- Fabricated or edited logs
- Plagiarism, or code from another team
- Committed keys, tokens, passwords, credentials
- A README that claims more than the code does
- A single agent or fixed chain presented as something it is not
- Unauthorised private, personal or restricted data

Required README disclosure section: model providers/models · agent frameworks · **partner
technologies and where each sits** · external tools and libraries · data sources and
whether any is sample or synthetic · materially adapted open-source code · known
limitations · fallback/sample-mode behaviour.

Secrets procedure if one ever lands in a commit: **rotate with the provider first**, then
clean. Removing it from the latest commit does not remove it from history.

### Disqualifiers, per the self-check guide

Only two are *confirmed* from the published rules: **late submission** and **duplicate
accounts** (one account per participant; duplicates disqualify the whole team). The rest of
the list — can't be run, no evidence, committed secrets, hardcoded outputs, misrepresented
authorship or results — is preparation guidance pointing at the Official Rules.

---

## 7. The Meterless agent engines

**What they are:** three standalone *reference architectures*, not a library you install.
Headless (no UI, no human at runtime), provider-agnostic, auditable. Meterless is the
cognition-layer partner. Source primitives: https://meterless.ai.

| Engine | Role | Minimum to implement |
|---|---|---|
| **H-MEM** | Persistent, hierarchical, auditable **memory** the whole agent graph reads/writes | `MemoryStoreService` + `MemoryRetrievalService` (skip dreaming/sleep) |
| **Markovian** | **Bounded-context long-task reasoning**, compressed carryover, ~O(1) per step | Config + chunk manager + carryover cascade + orchestrator loop |
| **World Model** | **Shared, queryable world state** — entities, contexts, relationships, provenance | `WorldStoreService` + `IngestPipelineService` + `ContextBuilderService` |

You do **not** have to implement all three. Ship the minimum column first.

### How they compose

World Model holds grounded state and uses H-MEM as its memory subsystem. H-MEM supplies
ranked context that Markovian injects at the **first chunk only**, then carries forward
compressed. All three emit JSONL audit/telemetry/provenance into `logs/`.

The four-step integration recipe: **1** hydrate H-MEM at run start, mine each agent step
into it, retrieve top-N and inject as structured context. **2** hand long tasks to the
Markovian orchestrator instead of one giant prompt. **3** write observations through the
World Model ingest pipeline; other agents query its context builder instead of re-deriving
entities. **4** write every engine's JSONL to `logs/`.

### The one rule that makes them portable

Every engine takes an **injected generator** instead of calling a model itself. Provider is
a one-line change at that seam — which matters when a rate limit, cost surprise or outage
lands on day four. Never call a model inside the engine.

### Track mapping, per the index

| Track | Fits first |
|---|---|
| Fragmented | World Model — reconciling disconnected sources into one grounded, provenance-stamped picture |
| Autonomous Intelligence | Markovian for the long investigation, World Model for the evidence trail |
| Persistent Memory Agents | H-MEM — tiered, decaying, conflict-resolved memory is the track's whole subject |
| Real-World Industry Agents | Whatever the problem needs; often H-MEM for state across sessions |

### Scoring mapping, per the index

- **Technical (20)** — all three: provider-agnostic services, structured contracts,
  measurable token efficiency (Markovian), idempotent resumable ingest (World Model)
- **Innovation (15)** — World Model (self-improving grounded state), H-MEM (programmable
  approval boundary, dreaming)
- **Demo (15)** — Markovian (projected-vs-actual savings curve), H-MEM (three sessions
  showing what carried over)
- **Impact (30)** — explicitly **not** the engines' job. "The engines make the solution
  credible, not valuable."
- **Sponsor Tech (10)** — document which engines you mounted and where

### Hackathon checklist from the engines' own README

- One shared `generator`, pointed at the provider through configuration, not hardcoded
- H-MEM retrieval injected into prompts, trace written to `logs/`
- Long tasks routed through Markovian; projected-vs-actual savings saved to `logs/`
- World Model ingest idempotent and resumable (a crashed run recovers, doesn't corrupt)
- All audit/telemetry/provenance as JSONL in `logs/`
- A sample mode that runs without live credentials
- No UI dependency, no human-in-the-loop at runtime, no provider lock-in
- README says which engines you mounted and where — this is the 10-point Sponsor Tech item

### Common mistakes they name

Implementing everything before anything works · calling a model inside the engine · storing
data no agent reads (their "**stored ≠ loaded**" rule) · tying long jobs to an agent's turn
(Markovian runs and World Model ingest must outlive the step that started them) · no logs ·
unbounded loops against a paid API.

---

## 8. Design patterns worth stealing regardless of whether you use the engines

These recur across all three engine docs and all four guidance docs, and they are the same
things the judges are described as rewarding:

1. **Injected generator / provider abstraction.** One seam, swappable provider, no lock-in.
   Also what makes sample mode possible.
2. **Structured payloads, never pre-rendered strings.** Return data plus trace metadata
   (`retrievalReason`, relevance scores, strategy label) so any consumer formats it and a
   judge can inspect *why* that context was chosen.
3. **Append-only JSONL audit trail as first-class output.** In every engine the audit
   ledger "doubles as submission evidence".
4. **Agent attribution on every record** — `agentId`, `runId`, `taskId` — so a swarm can be
   filtered, replayed, and its traces shown per agent.
5. **Idempotent, resumable, interrupt-safe pipelines.** A crashed or rate-limited run
   resumes the world instead of corrupting it.
6. **Programmable approval boundary.** Replace "human approves" with policy + supervisor
   agent + audit record. Same for destructive ops ("nuke and rebuild" behind a policy gate).
7. **Graceful degradation everywhere.** Four-tier carryover fallback ladder (explicit →
   LLM compression → heuristics → truncation); no-model fallback in memory mining;
   timeouts + fallbacks on every partner call.
8. **"Stored ≠ loaded" / the wired-vs-helper trap.** Audit what is *actually* injected at
   runtime, not what could be, and record the gap in the run manifest.
9. **Bounded everything.** Chunk caps, round caps, retry caps, token caps. You are paying.
10. **Honest measurement.** The token accounting is a `chars/4` heuristic — say so. "Judges
    reward honest measurement more than an impressive number."

---

## 9. Conflicts with this repo

The repo's `docs/event-brief.md` and `AGENTS.md` record some things these documents do not
confirm, and in two cases contradict.

> **Source of the repo's version, confirmed by the builder (2026-09-24): the HackOS event
> pages and an organiser channel.** The repo's facts are therefore *not* assumed wrong.
> Where they conflict with these drafts, the likely explanation is that the drafts are
> older or less specific — the repo already carries workshop dates these documents list as
> "TBA", which points that way. Treat the table below as **a list of items to re-verify on
> HackOS before the build window**, not as a list of errors to fix.

| Item | Repo currently says | These host documents say | Note |
|---|---|---|---|
| **Partner stack** | Zetaris (data), **NVIDIA** (token), Meterless (orchestration) | Zetaris (data), **Neo4j** (knowledge), Meterless (cognition) | Five of the twelve documents agree on Neo4j, and the tech guide's `.env.example` ships `ZETARIS_API_KEY` / `NEO4J_*` / `METERLESS_API_KEY`. NVIDIA appears in none of them — but the repo names an NVIDIA workshop with a date, so check HackOS rather than assuming either way |
| **Track names** | Connected Agent Context · Autonomous Agent · The Agent That Can Explain Why · Reasoning Architecture | Fragmented · Autonomous Intelligence · Persistent Memory Agents · Real-World Industry Agents | Different sets. The second is used consistently by the Rules, the engines index and the onboarding deck — the first is plausibly an earlier naming. **The track you pick must be named the way HackOS names it at submission time** |
| **Workshop dates** | Zetaris 7 Oct, NVIDIA 8 Oct, Meterless 12 Oct, all recorded | "Sponsor workshops: TBA", "announced on HackOS" | Repo is more specific. Watch the recordings wherever they are |
| **Bonus points** | "up to 30 bonus points" for open-sourcing, evals, insights | Silent. The deck's scoring table is 100 points with no bonus row | Nothing in these documents mentions bonus points. If they exist, `evals/` and `docs/insights.md` earn them; that scaffold is cheap either way. Worth confirming on HackOS because 30 points would be a third of the base score |
| **Prize breakdown** | $8,000 / $4,000 / $2,000 | "up to $20,000" only | Unconfirmed here |
| **Fifth track** | Mentions a "Tinkerer Track" | Four tracks only | Unconfirmed here |
| **Meterless layer** | Meterless = "orchestration", for running autonomous multi-step workflows | Meterless = **cognition** layer | The engines index says "Meterless is the cognition layer partner". Low stakes; affects README wording for Sponsor Tech |

`AGENTS.md` is auto-injected into every session, so whichever version is current needs to
be the one sitting there. Reconciling is a HackOS tab and a two-minute edit, best done
before the build window opens.

### What the repo is missing against the recommended layout

Present: `README.md`, `AGENTS.md`, `.env.example`, `.gitignore`, `docs/`, `evals/`, `notes/`.
Absent (nothing to build yet, but this is the day-one skeleton worth having): `run.py`,
`Dockerfile`, `requirements.txt`, `app/`, `data/`, `scripts/`, `input_examples/`,
`output_examples/`, `logs/`.

---

## 10. The plan, compressed

Weeks before the window — complete the deck's eight onboarding actions. The four that
matter: decide the track, watch the workshop recordings, set up the partner tools, and
**start logging agent activity from day one**.

Day one of the window — a small working loop, end to end, with logs. Not a module.

Halfway (17 Oct) — the repo's own checkpoint question: *"If the submission deadline were
tomorrow, what would fail?"* Fix that.

Day four (18 Oct) — run the full validation flow from a fresh clone, while there are still
two days to fix what it finds. "Almost everything on this list is preventable with 48
hours' notice and unfixable with two."

Submit with hours to spare, never at 23:44. There is no margin left when something breaks,
and something will.
