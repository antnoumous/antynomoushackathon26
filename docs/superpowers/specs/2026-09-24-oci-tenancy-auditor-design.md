# Design spec — Driftwatch: an OCI tenancy auditor that argues with itself

**Entry:** Open Agent Hackathon 2026 (GenAI Works), solo.
**Track:** 02 — Autonomous Agent. *(Name to be confirmed against HackOS before submission; the
digest's four track names differ from the current event pages. See Open items.)*
**Build window:** 15 Oct 2026 00:00 → 20 Oct 2026 23:45 UTC.
**Status:** design approved in conversation 2026-09-24. Not yet implemented.

---

## 1. Intent

**Decided outcome for this entry:** a *finished, credible submission that can place* — scope
chosen so the final 24 hours are polish rather than panic. This is the constraint every
decision below is tested against.

**What success looks like on 20 Oct:** a judge with no OCI account and no API keys clones the
repo, runs one command, and gets a real audit report plus a trace showing four named agents
disagreeing, one of them reversing a conclusion for a stated reason. Nothing in that path
requires a credential.

**Who it is for:** a cloud platform or FinOps engineer responsible for a tenancy they did not
entirely build, who needs to know which resources are costing money for no reason and which
running resources nobody owns.

---

## 2. Problem statement

Cloud infrastructure drifts from its declared state. Resources are created for a test and
never torn down; instances are sized for a burst and left running around the clock; a
reserved IP is detached and forgotten; a machine runs in a compartment nobody tracks and
appears in no Terraform file. The information needed to find these exists, but it is
fragmented across systems that do not talk to each other: the live control plane, the
monitoring time-series, the infrastructure-as-code repository, and whatever policy or
pricing reference the team maintains.

The failure mode of naive automation is **false confidence**. A script that flags every
instance whose mean CPU is under 5% will recommend deleting the month-end batch job that
finances depends on. That is worse than no audit, because it destroys trust in the audit.

**Therefore the product is not a scanner. It is an investigator that can be wrong and can
correct itself, with the correction visible.**

What makes this credible for this entrant specifically: OCI tenancy operations, networking
and firewall policy are the entrant's working domain, and the demo runs against a tenancy
the entrant owns outright.

---

## 3. Scope

### 3.1 In scope

- Two finding classes only:
  - **`cost_waste`** — idle, mis-sized, orphaned, or detached resources that cost money for
    no attributable purpose.
  - **`unattributed`** — resources running in the live tenancy that are absent from the IaC
    repository (shadow infrastructure), or present but drifted from it.
- Four data sources, genuinely disconnected (see §5).
- Four named agents with a bounded, evidence-driven loop and a real critic (§5.3–§5.5).
- A fixture-backed sample mode that runs the whole agent with no credentials and no network.
- Three sample scenarios, an evaluation harness, and a held-out scenario generator.

### 3.2 Non-goals

Explicitly excluded, and named here so no session quietly reintroduces them:

- **Security and compliance findings** (CIS benchmarks, MFA posture, policy entitlements).
  A second rule set and a second report format for no additional demo value. This was
  considered and deferred; it is the first candidate if time remains after the checkpoint.
- **Any user interface.** A UI may never be the only entry point, so a UI is pure cost here.
  Output is a JSON report plus a rendered Markdown report.
- **Remediation.** The agent is read-only against the tenancy. No destructive or mutating
  calls, no "apply fix" path. Recommendations are text.
- **Multi-tenancy, multi-region, or scale beyond a bounded resource set.** §5.9 caps a run.
- **LangGraph, CrewAI, AutoGen, or any orchestration framework.** The framework is not
  scored; a hand-rolled bounded loop is smaller, debuggable at speed, and emits the exact
  trace shape the organisers require.
- **Real-time or scheduled operation.** One run, one input, one output.

### 3.3 The scope philosophy

An audit demonstration is judged on **case variety and evidence quality, not fleet size**.
A six-resource lab tenancy carrying six distinct pathologies demonstrates better than six
hundred undifferentiated resources, because every finding is legible in the first 30 seconds
of the video.

---

## 4. Constraints

| Constraint | Consequence for this design |
|---|---|
| Solo, ~20 hours inside the window | Must-ship list in §11 is ~15 h; everything else is earnable stretch |
| CPU only, nothing installs after start | Pure Python + `oci` SDK + one HTTP framework; no local models, no GPU |
| Run completes in minutes | §5.9: capped rounds, resources, re-checks, and wall-clock |
| No credentials for a judge | §5.6: sample mode is the judge's path and the first thing built |
| No restricted or employer data | The demo tenancy is the entrant's own personal tenancy. No employer tenancy, ever. See §12 |
| Secrets from environment only | `.env` gitignored, `.env.example` placeholders only, OCIDs masked in shipped artifacts |

---

## 5. Architecture

```
                       POST /run  (JSON in, JSON out)   ← the only required entry point
                                  │
                      ┌───────────▼───────────┐
                      │       Planner         │  owns the run, enforces every cap
                      └───┬───────────┬───────┘
             delegate ↓   │           │   ↑ verdicts, re-check requests
        ┌─────────────────▼──┐   ┌────┴──────────────────┐
        │       Scout        │   │       Skeptic         │
        │  proposes findings │──▶│  accepts / rejects /  │
        │  never concludes   │◀──│  demands a re-check   │
        └────────┬───────────┘   └────────┬──────────────┘
                 │                        │
        ┌────────▼────────────────────────▼──────────────┐
        │  Source adapters (one interface, two backends) │
        │  inventory · telemetry · iac · policy          │
        │  live: OCI SDK / git    fixtures: bundled JSON │
        └────────────────────┬───────────────────────────┘
                             │  accepted findings + rejections
                      ┌──────▼──────┐
                      │   Writer    │  synthesis; may not invent a number
                      └──────┬──────┘
                             ▼
               report.json + report.md + logs/trace-<run_id>.jsonl
```

### 5.1 Data sources

Four sources, each behind one `Source` protocol returning structured records with stable
evidence IDs. Each has two backends: **live** (real system) and **fixture** (bundled JSON
snapshot). The agent code is identical in both cases; `SAMPLE_MODE` selects the backend.

| Source | Live backend | Records |
|---|---|---|
| `inventory` | OCI SDK (`core`, `network`) | compute instances (shape, OCPUs, memory, compartment, tags, lifecycle state, created), block volumes with attachment state, reserved public IPs with assigned-entity state |
| `telemetry` | OCI Monitoring API | per-instance CPU (and memory where a monitoring agent reports it) over a **configurable** lookback window, at a resolution that preserves peaks |
| `iac` | local git checkout (Terraform) | declared resources, file path, last-modifying commit, commit message, author |
| `policy` | bundled JSON | shape price catalog and declarative waste-interpretation rules |

The four are genuinely disconnected systems. This is not one API called four times, which is
the point the Connected-Data framing rests on and the reason the IaC and policy sources are
load-bearing rather than decorative.

**`telemetry` must distinguish "quiet" from "unknown".** When the requested lookback exceeds
available history, the source returns an explicit `insufficient_history` marker with the
coverage it does have. No defaulting, no interpolation, and no finding may be raised on an
insufficient window. This is a scored behaviour: a judge will probe it.

**How a live resource is matched to its IaC declaration** — deterministic, in this order, and
recorded on every finding so the match is auditable:

1. exact match on the OCI freeform tag `iac_address` (e.g. `oci_core_instance.batch_01`);
2. exact match on resource display name against a declared resource name;
3. case-insensitive normalised match on display name.

No match on any rule → `unattributed` candidate. A match on rules 2–3 but not 1 → `unattributed`
candidate with lower confidence and a note that the link is inferred rather than declared. The
match rule that fired, and the IaC commit that last touched the declaration, are part of the
finding's evidence.

### 5.2 The lab tenancy

Built by the entrant **before the window opens**, so that metric history exists by the demo.
Infrastructure created before 15 Oct is not code written before 15 Oct and does not touch the
Tinkerer-track rule.

| Element | Detail | Cost |
|---|---|---|
| Free envelope | 2× `VM.Standard.E2.1.Micro` (AMD) + 2× `VM.Standard.A1.Flex` at 1 OCPU / 6 GB = **4 instances**, 188 GB of the 200 GB boot allowance | $0 |
| Compartments | `lab-prod`, `lab-test` — so "wrong compartment" is a findable condition | $0 |
| Management split | Terraform manages 2–3 instances; **1–2 created by CLI**, so the drift is real and not staged | $0 |
| Workload: false positive | cron pegging CPU ~2 h on a monthly cadence, otherwise quiet → low mean, real peak | $0 |
| Workload: genuinely busy | steady 40–60% CPU → must **not** be flagged | $0 |
| Workload: clean idle | flat-idle, no owner tag → the unambiguous waste case | $0 |
| Orphan 1 | unattached 50 GB block volume | ≈$1.27/month at list, part of which falls inside the 200 GB allowance |
| Orphan 2 | unattached reserved public IP | ≈$7.30/month, billed whether attached or not |

List rates used above: A1 `$0.01`/OCPU-hour + `$0.0015`/GB-hour; block volume ≈`$0.0255`/GB-month;
reserved public IP ≈`$0.01`/hour. **The price catalog is itself a source fixture**, so verifying
these rates is not overhead — the agent reads them.

Two facts that shaped this table:

- Oracle **halved** the Always Free Ampere A1 allowance on 15 June 2026 to 1,500 OCPU-hours
  and 9,000 GB-hours per month (2 OCPUs / 12 GB continuous). Some users report Oracle support
  telling them PAYG accounts retained the earlier 4 OCPU / 24 GB — unconfirmed, and worth
  checking against the tenancy's own usage before sizing anything.
- A1 capacity is frequently unavailable ("out of host capacity"). The two `E2.1.Micro`
  instances are the reliable ones; do not block on the ARM instances.

**Budget decision:** spend **nothing** until the 17 Oct checkpoint. If two more instances are
genuinely needed for the demo, they cost ≈$9.82 for 10 days and ≈$19.63 for 20 days.

**The small-numbers problem, and its answer.** A lab tenancy produces small absolute waste
("$22/month"). The fix is not inflation. Findings report **scale-free ratios** ("12% of
monthly compute spend is unattributable to any owner") alongside absolute figures, and any
extrapolation is labelled as extrapolation in the report text and in `report.json`. The host
documents state the standard directly: *"judges reward honest measurement more than an
impressive number."*

### 5.3 Agents and permissions

Four named agents. Each has a distinct permission set, so the submission cannot be read as one
agent with several labels (Rules §7.3 names that pattern as not meeting the bar).

| Agent | Input | Output | May do | May **not** do |
|---|---|---|---|---|
| **Planner** | objective, source catalogue, `RunState` | task assignments, re-check requests, run termination | choose enumeration targets; route findings; decide accept / re-check / stop; enforce caps | investigate; write the report |
| **Scout** | Planner assignment, sources | *candidate* findings with evidence refs and provisional confidence | read `inventory`, `telemetry`, `iac`; propose candidates | conclude; reject; write the report |
| **Skeptic** | candidate findings, `telemetry` distributions, `policy`, `iac` | `accept` / `reject(reason)` / `recheck(request)` per finding | read distributions and rules; falsify; demand narrower queries | propose findings; write the report |
| **Writer** | accepted findings, rejections with reasons, `RunState` | `report.json`, `report.md` | synthesise, cite, state what could not be determined | investigate; state any number absent from the evidence set |

**The structural test of agency:** the Skeptic can send the Scout back, and the Planner acts
on that. A single loop of `discover → analyse → report` cannot express this, and the trace
shows the difference.

### 5.4 The loop

Bounded at `MAX_ROUNDS = 3`.

```
hydrate RunState from sources
round r = 1 … MAX_ROUNDS
    Planner   select targets (≤ MAX_RESOURCES), emit assignments
    Scout     gather evidence, emit candidate findings
    Skeptic   judge each candidate → accept | reject(reason) | recheck(request)
    Planner   if re-check requests remain and r < MAX_ROUNDS:
                  emit narrower queries → next round
              else: terminate
Writer    synthesise accepted + rejected + undetermined
```

Termination conditions, all logged: all candidates resolved; `MAX_ROUNDS` reached; wall-clock
budget exhausted; no re-checks requested. Every premature stop is recorded as `status: capped`
with the cap that fired.

### 5.5 Determinism boundary

**Code decides:** enumeration; every cost, ratio and arithmetic figure; history-length and
coverage checks; tag parsing; IaC matching; threshold comparisons; evidence ID assignment;
verdict *eligibility*; all cap enforcement.

**The model decides:** interpreting ambiguous intent; judging cases no rule covers; explaining;
naming; drafting prose.

The model **never** produces a number that reaches the report. Consequences: report figures
cannot be hallucinated; sample mode can run with no model at all; and the auditor's
correctness is testable, because the decisions that matter are deterministic.

### 5.6 Generator seam and sample mode

One protocol, injected into every agent that needs language:

```python
class Generator(Protocol):
    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict: ...
```

- **Model-backed generator** — provider chosen by environment variables; one file to change.
- **`RulesGenerator`** — deterministic, offline, no credentials. Used when `SAMPLE_MODE=true`
  or when no API key is present. Interpretations come from the declarative rules in the
  `policy` source.

**No source adapter ever calls a model.** Provider is a one-line change at this seam.

`SAMPLE_MODE=true` therefore runs the entire agent — enumeration, correlation, cost
arithmetic, the critic loop, cap enforcement, report assembly — against fixture backends,
with no network and no credentials. What it does *not* do is call a live model, and the README
says exactly that. The trace still shows four agents, handoffs, a rejection, a re-check and a
revised conclusion.

### 5.7 RunState

A single append-only JSONL store at `logs/state-<run_id>.jsonl` — **a different artifact from**
the audit trace in §5.8 — hydrated once at run start and appended by every agent action. Each record carries `run_id`, `task_id`, `agent_name`, `action`, `input_summary`,
`output_summary`, `target_agent`, `confidence`, `retry_count`, `status`, `round`, and
`evidence_refs`. This is the shared context the deck asks for, and it is the seam where a
Meterless-style Markovian carryover or H-MEM-style tiered memory would mount if the sponsor
layer is built (§5.11).

The run manifest additionally records a **stored-vs-loaded audit**: what context was *available*
versus what was *actually injected* into each agent's prompt. The gap is recorded, not hidden.

### 5.8 Trace and logging

Logs go to **stdout** and to **`logs/trace-<run_id>.jsonl`**, one JSON object per line, with the
field shape the organisers specified:

```json
{"timestamp":"2026-10-17T18:42:11Z","run_id":"demo-001","agent_name":"Scout",
 "action":"propose_finding","input_summary":"instance batch-01, 168h CPU",
 "output_summary":"candidate: idle, $8.94/month","target_agent":"Skeptic",
 "confidence":0.6,"retry_count":0,"status":"success","round":1,
 "evidence_refs":["E-011","E-012"]}
```

The trace must show, and is tested for: ≥2 named agents doing distinct things; handoffs;
critique and validation; retries and recovery; the final synthesis; errors and what happened
next; and **correspondence to the input actually processed**. Traces are produced by the code
as it runs. No trace is ever hand-written or edited; a fabricated log is treated as an
integrity failure, not a shortcut.

### 5.9 Caps, timeouts, budgets

| Cap | Value | Rationale |
|---|---|---|
| `MAX_ROUNDS` | 3 | Unbounded debate is the top cause of a hung run |
| `MAX_RESOURCES` | 25 | Bounds enumeration and telemetry calls |
| `MAX_RECHECKS_PER_FINDING` | 2 | A critic that loops forever is not a critic |
| Wall clock | soft 300 s, hard 540 s | Target run time 5–10 minutes |
| Partner/source call timeout | 10–30 s | Every external call |
| Model call timeout | 30–90 s | Every model call |
| Agent iteration | 1–3 min | Per iteration |
| Token/cost ceiling | configured | The entrant pays |

Every cap that fires emits `status: capped`. Silent truncation is prohibited.

### 5.10 Failure, retry, degradation

A source call: timeout → one retry → fall back to the fixture backend **with the degradation
logged** → if it still fails, the run completes with `status: partial` and the report states
which source was unavailable and which findings were therefore not attempted.

Degraded and partial runs are first-class outcomes. Nothing is ever reported as successful
when it was not. This is what the trace's "retries and recovery" requirement is asking for.

### 5.11 Sponsor layer (deferred, earnable)

Mounted only if the free four instances and the critic loop are complete. Two candidate
mountings, both implementable from the published specs without an account:

- **Markovian** — round 3 injects a compressed carryover instead of the full `RunState`
  history, with a projected-vs-actual token curve written to `logs/` as demo evidence.
- **H-MEM** — tiered, retrievable memory; ranked context is injected at the first chunk of a
  long task and then carried forward compressed, per the engines' stated composition.

**Zetaris** would sit behind the `policy` source as a data-virtualisation adapter — designed
as a swappable adapter with a timeout and a fixture fallback, never on the critical path. It
slots in after the 7 Oct workshop recording if that shows a practical MCP endpoint.

Whichever mounts, the README states which and where — that documentation *is* the Sponsor Tech
item.

---

## 6. The canonical scenario

The run that the demo video shows, and the reason the architecture is what it is.

| Round | Agent | Event |
|---|---|---|
| 1 | Scout | "`batch-01`: mean CPU 0.8% over 168 h → idle → $X/month wasted" |
| 1 | Skeptic | **reject** — "the mean is misleading. p99 = 61%, clustered 02:00–04:00 on the 1st. Consistent with a scheduled month-end job." |
| 1 | Skeptic | **recheck** — "pull 30 days at a resolution that preserves peaks" |
| 2 | Scout | returns the distribution across 30 days |
| 2 | Skeptic | **accepts a changed conclusion** — "not waste: mis-sized. Provisioned for a 2-hour monthly burst on a 24/7 shape. Resize and schedule: $Y/month" |
| 3 | Writer | reports the revised finding, and reports the rejected one *with its reason*, and lists what remains undetermined |

Every step carries evidence references. The video's subject is the reversal, not the dollar
figure.

---

## 7. Finding model

```json
{
  "finding_id": "F-003",
  "resource_id": "ocid1.instance.oc1..••••3f2a",
  "resource_class": "compute_instance",
  "class": "cost_waste",
  "claim": "sized for a monthly burst, billed continuously",
  "evidence_refs": ["E-011", "E-012", "E-019"],
  "impact": {"kind": "usd_per_month", "value": 8.94,
             "ratio": {"kind": "pct_of_compute_spend", "value": 0.12}},
  "confidence": 0.72,
  "status": "accepted",
  "falsifier": "a documented scheduled batch job with an owner tag and an IaC entry",
  "history": [{"round": 1, "verdict": "recheck", "reason": "mean conceals a peak"}]
}
```

Every finding carries its evidence, its confidence, the observation that would falsify it, and
its full verdict history. Findings that were rejected are reported too, with reasons — an audit
that hides its own rejections cannot be trusted.

---

## 8. Evaluation

`evals/` runs the agent in sample mode across the scenarios and scores:

- **Detection precision and recall** against hand-labelled ground truth (`resource_id`, `class`).
- **Verdict accuracy** — was the month-end batch instance correctly *not* reported as waste?
- **Determinism** — identical fixture input produces identical *findings* across runs. Structured
  findings and every figure are deterministic; narrative prose may vary with the generator.
- **Degradation correctness** — a scenario with a missing source yields `partial`, not a
  silently short report.

Plus `scripts/make_scenario.py --seed N`, generating **held-out, never-seen** tenancy snapshots
with their own ground truth. This is the direct answer to "are these outputs generated or
hardcoded": the agent is scored on inputs that did not exist when it was written. The generator
produces data; the labels are ground truth; the agent derives its findings. Neither is a
prewritten answer.

---

## 9. Entry points

- `POST /run` — takes a JSON request, returns a JSON report. Binds `0.0.0.0` inside containers.
- `run.py --input <file>` — the same pipeline from the command line, and the path used by the
  evaluation harness and by sample mode.

A UI is not built. Either entry point alone satisfies the requirement; having both means the
harness and a judge use the same code path.

### 9.1 Request and response shape

Request (also the contents of each file in `input_examples/`):

```json
{
  "objective": "audit this tenancy for cost waste and unattributed resources",
  "scope": {
    "compartment_ids": ["ocid1.compartment.oc1..••••lab"],
    "resource_types": ["compute_instance", "block_volume", "reserved_public_ip"]
  },
  "telemetry": {"lookback_hours": 168, "resolution_minutes": 5},
  "caps": {"max_rounds": 3, "max_resources": 25, "wall_clock_seconds": 540},
  "sample_mode": true
}
```

Response, returned by `POST /run` and written to `output_examples/`:

```json
{
  "run_id": "demo-001",
  "status": "success",
  "mode": "sample",
  "sources": [{"name": "telemetry", "backend": "fixture", "degraded": false}],
  "summary": {"resources_examined": 6, "findings_accepted": 3, "findings_rejected": 2,
              "spend_audited_usd_per_month": 74.20,
              "unattributed_ratio": 0.12},
  "findings": [ /* §7 */ ],
  "undetermined": [{"resource_id": "…", "reason": "telemetry coverage 41h of 168h requested"}],
  "report_markdown_path": "output_examples/example_1_report.md",
  "trace_path": "logs/trace-demo-001.jsonl"
}
```

`status` is one of `success`, `partial` or `capped`. `mode` is `sample` or `live`. Both are
always present, so a reader never has to infer how the run was produced.

---

## 10. Repository layout

```text
/project-root
│── app/                     # agent logic: agents/, sources/, policy/, report/
│── data/                    # 3 fixture scenarios + price catalog
│── scripts/                 # make_scenario.py, mask_ocids.py
│── run.py                   # CLI + service entry point
│── requirements.txt
│── Dockerfile
│── input_examples/          # ≥3 inputs
│── output_examples/         # ≥3 matching outputs
│── logs/                    # trace-<run_id>.jsonl + state-<run_id>.jsonl per run
│── evals/                   # scoring harness + ground truth
│── docs/                    # event-brief, decisions, insights, this spec
│── .env.example             # placeholders only
└── README.md
```

---

## 11. Build order and budget

**Sample mode end-to-end is the first artifact, not the last.** It is the judge's path, the
fastest development loop, and what makes the live adapter optional rather than critical.

| # | Work | Hours | Deliverable |
|---|---|---|---|
| 1 | Skeleton, interfaces, **sample mode end-to-end** | 4.5 | `run.py` + `POST /run`, four fixture adapters, `Generator` seam, `RunState` JSONL, one scenario → real report + trace |
| 2 | The four agents + bounded loop | 4.0 | handoffs, reject / re-check / revision, caps, retry + degradation |
| 3 | Live OCI adapters | 2.5 | SDK inventory + Monitoring behind the same interface |
| 4 | Scenarios + evaluation | 2.0 | 3 scenarios, held-out generator, precision/recall scoring |
| 5 | Packaging + disclosures | 2.0 | Dockerfile, requirements, README with all required disclosures, 3+3 examples |
| 6 | Demo video | 3.0 | 2–3 min, live run, the reversal visible on screen |
| 7 | Adversarial pass + buffer | 2.0 | clean-clone and `rm .env` validation, honesty pass, insights/decisions |
| | **Total** | **20.0** | |

**Must ship (~15 h):** items 1, 2, 5, 6, and three handcrafted scenarios with a basic eval.
That is already a complete submission.

**Stretch (final ~5 h):** item 3 (live OCI) and item 4's held-out generator. Scope is re-decided
at the 17 Oct checkpoint.

**Not in scope:** sponsor layer, security findings, any UI.

**Day map (UTC+8):** Thu 15 → skeleton + sample mode. Fri 16 → agents. Sat 17 → live OCI, then
the checkpoint question *"if the deadline were tomorrow, what would fail?"*. Sun 18 → clean-clone
and Docker validation, then shoot the video against whatever works. Mon 19 → video edit, README,
examples, eval. Tue 20 → submit, **target 18:00 SGT**.

A submittable artifact exists by Sunday night. Monday and Tuesday only improve it.

---

## 12. Integrity and disclosure

Non-negotiable, and the reason several design choices above are shaped as they are:

- **No hardcoded outputs.** No input→output mapping, no demo-only branch, no stored final
  answers. §8's held-out generator exists to make this checkable rather than asserted.
- **No fabricated or edited logs.** Traces are emitted by the code as it runs.
- **The demo tenancy is the entrant's own personal tenancy.** Never an employer tenancy:
  unauthorised private or restricted data is a disqualification trigger, and corporate
  infrastructure telemetry, tags and cost data in a public repo and video is squarely that.
- **OCIDs are masked** in shipped fixtures, examples and the video — identifiers, not secrets,
  but there is no reason to publish real ones.
- **Secrets from environment variables only.** `.env` gitignored; `.env.example` placeholder-only.
  If a secret ever lands in a commit, rotate it with the provider *first*.
- **README discloses:** model providers and models; agent frameworks (none); partner
  technologies and where each sits; external tools and libraries; data sources and which are
  sample, synthetic or real; materially adapted open-source code; known limitations; and
  exactly what sample mode does and does not do.
- **The README never claims more than the code does.** Limitation sections are written from the
  code, not from intent.

---

## 13. Acceptance criteria

The submission is done when all of the following are true and were observed, not assumed:

1. `rm .env && docker run --rm -p 8000:8000 -e SAMPLE_MODE=true driftwatch` then
   `curl -X POST localhost:8000/run -H "Content-Type: application/json"
   -d @input_examples/example_1.json` returns a report — no network, no credentials.
2. The same command runs from a **fresh clone** with no manual steps beyond dependency install.
3. A run completes well inside 10 minutes with no cap silently exceeded.
4. `logs/trace-<run_id>.jsonl` for that run shows four named agents, at least one handoff, at
   least one rejection with a reason, at least one re-check, and a revised conclusion — all
   corresponding to the input processed.
5. Three input examples and three matching outputs exist and differ meaningfully.
6. `evals/` runs and reports precision/recall against the hand-labelled ground truth of the
   three scenarios. If the stretch item shipped, it also scores a held-out scenario generated
   with a seed the agent has never seen.
7. No secret, real OCID, or employer artifact appears in the repo, examples, logs or video.
8. README discloses every item listed in §12.

---

## 14. Open items

Each is recorded with a recommendation, not left as a placeholder.

| Item | Recommendation | When |
|---|---|---|
| **Track name** | Submit as Track 02 *Autonomous Agent* per the event pages; verify the exact spelling on HackOS, since the digest's four names differ | Before 15 Oct |
| **Partner stack** | Repo says Zetaris/NVIDIA/Meterless; host documents say Zetaris/Neo4j/Meterless. Confirm on HackOS — it only affects README wording | Before 15 Oct |
| **Model provider** | OpenAI-compatible API, one env var at the `Generator` seam; cheap fast model for Scout/Skeptic judgement, stronger model for the Writer only. Bounded at ~10–30 calls per run, so cents per run | Before 15 Oct (touches README disclosure) |
| **Bonus points** | Repo claims up to 30 for open-sourcing, evals and insights; host documents are silent. Treat as unconfirmed but pursue anyway: the repo is already public, `evals/` is item 4, `docs/insights.md` is filled as we go | Before 15 Oct |
| **Sponsor layer** | Markovian or H-MEM, from the published spec, no account required | After the 17 Oct checkpoint |

---

## 15. Risks

| Risk | Mitigation |
|---|---|
| OCI Monitoring API is fiddlier than expected | Fixtures-first build order; live adapters are stretch, not critical path; go/no-go at the 17 Oct checkpoint |
| A1 instance capacity unavailable | Rely on the two `E2.1.Micro` instances; A1 is a bonus, not a dependency |
| Metric history too short at demo time | Lab created before the window; lookback configurable; `insufficient_history` handled honestly |
| 20 hours is optimistic | Must-ship list frozen at ~15 h; submittable artifact by Sunday night |
| Small dollar figures weaken the Impact story | Scale-free ratios plus labelled extrapolation, per §5.2 |
| Video eats the final day | Recorded Sunday against a working system, not assembled Tuesday |
| Scope creep back into security findings | §3.2 names it explicitly as a non-goal |

---

## 16. Immediate next actions (pre-window)

1. Confirm track name and partner stack on HackOS; check the tenancy's actual Always Free
   allowance if it is a PAYG account.
2. Create the lab tenancy per §5.2 — **now**, so seven-day metric history exists by 15 Oct.
3. Watch the 7 Oct Zetaris recording and decide whether the sponsor adapter is practical.
4. Choose the model provider.
5. Write the implementation plan (next step after this spec is reviewed).
