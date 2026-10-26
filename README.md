# Driftwatch — an OCI tenancy auditor that argues with itself

Submission for the [Open Agent Hackathon 2026](https://hackathon.genai.works/event/open-agent-hackathon-2026)
by GenAI Works. **Track 02 — Autonomous Agent.**

Driftwatch audits an Oracle Cloud tenancy for cost waste and unattributed ("shadow")
infrastructure. Four named agents do the work: a **Planner** that owns the run, a **Scout** that
gathers evidence and proposes findings, a **Skeptic** that can reject a finding and force a
re-investigation, and a **Writer** that reports only what the evidence supports.

It is not a fixed pipeline. The Skeptic's ruling changes what the Scout does next, and the final
report shows both the finding and the reason the agent changed its mind.

## Contents

- [Run it](#run-it)
- [The money shot](#the-money-shot)
- [How it works](#how-it-works)
- [Where the sponsor technologies fit](#where-the-sponsor-technologies-fit)
- [Evidence: traces, inputs, outputs](#evidence-traces-inputs-outputs)
- [Evaluation](#evaluation)
- [Disclosure](#disclosure)

## Run it

Nothing installs after the app starts, no model or dataset is downloaded, and no GPU is used.
**Python 3.11 or newer.**

```bash
git clone https://github.com/antnoumous/antynomoushackathon26.git
cd antynomoushackathon26
python3.11 -m venv .venv && . .venv/bin/activate    # 3.11+; the app says so plainly if not
pip install -r requirements.txt

# Audits the bundled sample scenario on cached data. No credentials, no network.
python run.py

# The same agent behind HTTP.
python run.py --serve           # POST http://localhost:8000/run
```

`run.py` takes a JSON request and writes a JSON report, so it is drivable without a human:

```bash
python run.py --input input_examples/example_1.json \
              --scenario data/scenarios/example_1 \
              --out output_examples/example_1.json
```

```bash
curl -sS -X POST http://localhost:8000/run -H "Content-Type: application/json" \
  -d @input_examples/example_1.json
```

Container, if you prefer:

```bash
docker build -t driftwatch .
docker run --rm -p 8000:8000 -e SAMPLE_MODE=true driftwatch
```

**The container path is fully verified on x86**: built and served on Docker Desktop
(Engine 29.6.2, `linux/amd64`, Windows 11) from a public-repo clone — image builds amd64 at
684 MB, `/health` returns `{"status":"ok"}`, and `POST /run` with
`input_examples/example_1.json` returns byte-identical figures to the committed artifacts
($196.18 spend / $105.66 waste, 4 accepted / 1 rejected / 1 undetermined) — cross-architecture
determinism proven, arm64 sandbox and x86 PC agree. It was also built and served on arm64
(podman, Ubuntu 24.04). Evidence: `output_examples/fresh_verify.txt`.

**Sample mode is the judged path; the live path is real and has been run against a tenancy.**
`SAMPLE_MODE=true` runs the full agent on the bundled scenarios with no credentials and no
network. `SAMPLE_MODE=false` wires the real OCI adapters — inventory (instances, volumes,
reserved IPs), telemetry (`CpuUtilization` via the Monitoring service), and the file-backed IaC
and policy sources — against a lab tenancy (`docs/lab-tenancy.md`); the first live runs found
and fixed five defects (telemetry query scoping, terminated-instance ghosts, missing price rows,
a skipped fixture fallback in the Scout, and an unmasked-id join). Without reachable credentials
every OCI source raises `SourceError`, the loop degrades to the bundled fixtures, the run reports
`status: partial` with `summary.backends` naming what actually answered, and a warning is printed
to stderr. `oci` is imported lazily, so sample mode never touches the SDK.

## The money shot

In `example_1`, one instance is genuinely interesting.

**Round 1.** The Scout reads seven days of CPU telemetry for `batch-01`, finds a mean of 0.766% and
a peak of 0.888%, and proposes a cost-waste finding: idle instance, $90.52/month.

**The Skeptic refuses to accept it.** Its declaration says the instance runs a month-end batch job.
A month-end cadence is invisible in a seven-day window, so the mean is not evidence of anything.
The Skeptic neither accepts nor rejects — it returns `recheck`, with a request for a wider window.

**Round 2.** The Planner narrows the assignment to that one resource and widens the lookback to
31 days. The burst appears: mean 1.002%, peak 58.0%. The Scout's conclusion changes — this is not an
idle instance, it is a **mis-sized** one, provisioned around the clock for two hours of work a
month.

**The Writer reports both findings:** the revised one (`C-005`, `revised`), and the original
(`C-001`, `rejected`, *superseded by C-005*), with the reason it was withdrawn. That pair is the
whole point of the submission.

You can watch this happen in `logs/samples/trace-example_1.jsonl`, and read it in
`output_examples/example_1_report.md`.

## How it works

```
                     ┌──────────────────────────────────────────┐
   four sources      │  inventory  telemetry  iac  policy       │   live adapters: built, offline-
   one interface     │  ── each with a fixture twin ──          │   tested, tenancy-unverified
                     └──────────────────────────────────────────┘
                                        │
        ┌───────────────┬───────────────┴────────────┬───────────────┐
        │   Planner     │        Scout               │   Skeptic     │   Writer
        │  owns the run │  evidence → candidates     │  accept /     │  accepted +
        │  caps, rounds │  returns Candidates        │  reject /     │  rejected-with-
        │  assignment   │                            │  recheck      │  reasons
        └───────────────┴────────────────────────────┴───────────────┘
                                        │
                        one append-only RunState + one JSONL trace
```

Each agent's permission set is enforced by the shape of what it returns, not by a prompt: the Scout
cannot set a finding's status (a `Candidate` has no such field), the Skeptic cannot propose a
finding (it returns only `Ruling` objects), and the Writer cannot investigate (it reads the ledger
and makes no source calls). Two limits are worth stating plainly. First, the four agents share one
`AgentContext`, so the boundary is the *type each one returns* rather than a sandbox. Second, the
Scout's inability to see verdicts is convention, not structure — it holds the same state the
rulings are written into. The types enforce the handoffs; they do not enforce secrecy.

**The determinism boundary is the design's spine.** Code decides enumeration, cost arithmetic,
coverage checks, tag parsing, IaC matching, threshold comparisons, cap enforcement, evidence IDs
and verdict eligibility. A model decides interpretation, ambiguous judgement, explanation and
prose. **No figure in a report is produced by a model**: every number in a claim, a revised claim,
a verdict's reason and the run narrative is checked against the evidence ledger by
`app/agents/writer.py:assert_figures_traceable`, which raises rather than publish. Money is a
stricter tier than magnitude: currency has to come from computed arithmetic or a resolved payload,
so a `300` in the text is not allowed merely because 300 is the soft wall clock. The constants a
report may state about *itself* — caps, round counts, the requested window — are derived from the
run's own configuration rather than hardcoded, so lowering a cap through the request cannot leave a
stale allowance behind.

What that guarantee is *not* is a truthfulness oracle. It stops a number without evidence; it
cannot stop a false sentence that contains no number. The defence there is structural: the prose a
model writes is scoped to one candidate at a time, and the facts in it come from the rule engine's
computed context rather than from the model's own recall.

**Caps are enforced and always visible.** Every cap is real and every one that fires names itself in
`caps_hit` and writes a `cap_hit` trace line — a truncated investigation never reads as a finished
one.

| Cap | Value | What firing looks like |
|---|---|---|
| Rounds | 3 | `max_rounds`; outstanding re-checks are recorded, not silently dropped |
| Resources per run | 25 | `max_resources`; `summary.resources_examined` counts what was examined, not what exists, and `summary.resources_in_scope` shows the difference |
| Re-checks per finding | 2 | `max_rechecks_per_finding`; keyed by resource and finding class, because each round mints a new candidate id |
| Wall clock | 300 s soft / 540 s hard | `wall_clock_soft_s` / `wall_clock_hard_s`; checked between rounds *and* before each resource, and each model call's timeout is trimmed to the remaining budget |
| Model call | 60 s, or the remaining budget | `GeneratorUnavailableError` / a degraded judgement, never a hung run |

Two consequences are worth calling out. A finding the Skeptic asked to re-check, which the run then
never got back to, is **not** reported as accepted: it moves to `undetermined` with the reason
(`app/loop.py`). And `status` states the harshest truth available — a cap outranks degradation in
that one field (`capped` beats `partial`), while both facts stay separate and visible in `caps_hit`
and `sources[].degraded`.

**Degradation is not fabrication.** A source that fails is retried once, then falls back to fixture
data with the degradation logged and the source named in the report; if there is no fallback the run
finishes `partial` and says which source was unavailable. Telemetry is the sharp edge of this: it
has no fixture fallback, because a CPU verdict computed from substitute data would be a lie rather
than a degradation. When telemetry is unavailable the Scout therefore raises **no CPU finding at
all** — the resources move to `undetermined` with the reason "no telemetry was retrieved" — while
shape-based findings (detached volumes, unattached IPs, undeclared instances) still stand, because
those never needed a series. `summary.backends` and `summary.sources_degraded` say what actually
answered.

### Reproduce the canonical run

```bash
python run.py --scenario data/scenarios/example_1          # marks: the rejected + revised pair
python -m evals.run_eval                                   # precision / recall / determinism
```

## Where the sponsor technologies fit

**Zetaris is mounted, and it did real work.** The `policy` source adapter (a swappable interface
in `app/sources/`) has an opt-in Zetaris backend: set `DRIFTWATCH_POLICY_SOURCE=zetaris` and the
rules are fetched from the live Zetaris AI Data Gateway over its documented REST/SQL surface —
two pinned SELECTs against a published snapshot of **synthetic** policy data, with row-count,
content-digest and scope-hash re-validated *after* transport and *before* any agent consumes a
rule; a failure degrades explicitly to the file source, never silently. The acceptance artifact
`output_examples/zetaris_acceptance_2026-10-22/` proves causality, not just connectivity:
republishing the policy without rule R-1 as a new immutable snapshot removed **exactly** the
finding R-1 produced, computed through the full Scout→Skeptic→Writer loop with `provider:
zetaris` lineage on every rule hit. Runbook, grants, rollback and the supplier defect we found
and worked around are in `docs/zetaris-policy-operations.md` and
`notes/zetaris-engine-defects-2026-10-22.md`. Sample mode is unchanged: `SAMPLE_MODE=true`
forces the file source before any sponsor variable is read, with no credentials and no network.

**Meterless is mounted as two separate things, and only one of them has run against the real
runtime.** The **World Model engine** is implemented in `app/world_model/` as a minimal Python
adaptation of the sponsor's reference engine — not their package, and no conformance claim: an
immutable observation store, a validated ingestion pipeline and a context builder whose selections
are pinned to an exact run and source revision. It is not decoration: **Scout and Skeptic both read
their context through it**, every finding carries the provenance of the observation that produced
it, and an observation cannot be rewritten in place. `scripts/verify_world_model.py` regenerates
that proof offline, with no credentials and no network, into
`output_examples/world_model_review_2026-10-26/`; `tests/test_world_integration.py` fails if an
agent stops consuming it or if a candidate's pinned context can be rewritten by a later snapshot.

The **Nightshift** side is an explicit `meterless` generator behind the same interface as `rules`
and `openai-compatible`. It implements the documented provider contract — bearer auth plus the
`meterless-app` header, authenticated `/v1/models` discovery before selection, the three named
JSON schemas validated on the way back, a 60-second budget bounded further by the audit deadline,
redirects and automatic retries refused, and truthful accounting that reports zero attempts as
`not_used` rather than pretending a configured fallback was a success. **It has not yet served a
request.** The vendor's Mac installer is ad-hoc signed with no TeamIdentifier and macOS Gatekeeper
rejects it, so no trusted runtime could be installed; see `docs/meterless-operations.md`. Until a
request actually returns, every committed artifact's prose still comes from the deterministic rule
engine, and `summary.integrations.meterless_nightshift` says so rather than implying otherwise.

| Sponsor | Layer | Status in this submission |
|---|---|---|
| Zetaris | Data | **Mounted.** Policy snapshot published to the live engine, fetched through the two-SELECT source with end-to-end digest validation; acceptance = R-1 removal changes exactly one finding. Inventory/telemetry stay on OCI adapters — Zetaris is the governed-data seam. |
| Meterless | Engine + models | **World Model mounted and load-bearing; Nightshift adapter implemented but not yet exercised live.** The engine is consumed by Scout and Skeptic with pinned provenance and generated offline acceptance. The Nightshift adapter is contract-tested end to end; no live inference has succeeded yet (blocked on a trusted vendor build), so the adapter reports `not_used` in committed runs instead of claiming model output. |
| NVIDIA | Models/workflow | Route present, not exercised. A Nightshift runtime would hold the NVIDIA key in its own Providers tab and the app would speak only OpenAI-format HTTP to it (`app/generator.py`); no NVIDIA model has answered a Driftwatch request. |

## Evidence: traces, inputs, outputs

Everything under `output_examples/` and `logs/samples/` is **generated** by `scripts/run_examples.sh`
and the runs it starts. Nothing in them is hand-written or edited, and two tests keep that honest:
no unmasked OCID exists anywhere in the repository (`tests/test_mask_ocids.py`), and every committed
trace, state file and rendered report carries its **own** run's id and narrative
(`tests/test_committed_evidence.py`). Re-running the script reproduces the same findings, statuses,
claims and caps; the run id and timestamps differ, because each run mints a fresh `run_id` by design.

| Evidence | Where |
|---|---|
| Three input requests | `input_examples/example_{1,2,3}.json` |
| Three matching JSON reports | `output_examples/example_{1,2,3}.json` |
| Three rendered audits | `output_examples/example_{1,2,3}_report.md` |
| Full stdout of each run, including every trace line | `output_examples/example_{1,2,3}.log` |
| Agent trace (one JSONL line per action) | `logs/samples/trace-example_{1,2,3}.jsonl` |
| Shared run state (append-only) | `logs/samples/state-example_{1,2,3}.jsonl` |
| Evaluation results | `output_examples/eval.txt` |
| Held-out scoring on generated tenancies | `output_examples/held_out.txt` |

The three scenarios differ meaningfully rather than cosmetically:

1. **example_1 — the false positive.** Six resources, five pathologies, and one instance whose
   seven-day window hides a monthly burst. The run rejects its own first finding and revises it.
2. **example_2 — the clean tenancy.** Five resources, all declared, all appropriately loaded. The
   correct output is **no findings at all**. A scanner that invents work fails here.
3. **example_3 — the tag that changes the answer.** An idle instance declared *idle by design* must
   not be reported; an untagged idle instance yields two findings; an instance with 20 hours of the
   168 requested (about 12%) lands in `undetermined`; an attached IP is correctly ignored.

Every trace line carries `timestamp`, `run_id`, `agent_name`, `action`, `input_summary`,
`output_summary`, `target_agent`, `confidence`, `retry_count` and `status`, plus `round` and
`evidence_refs`. Traces are written to stdout **and** to a file.

## Evaluation

```
example_1    precision 1.0   recall 1.0    verdicts 1.0   findings 5   status success  deterministic True
  must-not-flag: 2 resource(s) must stay unreported — 0 violation(s)
example_2    precision n/a   recall n/a    verdicts n/a   findings 0   status success  deterministic True
  must-not-flag: 5 resource(s) must stay unreported — 0 violation(s)
example_3    precision 1.0   recall 1.0    verdicts 1.0   findings 4   status success  deterministic True
  must-not-flag: 3 resource(s) must stay unreported — 0 violation(s)

3 scenarios, 0 failing
```

`evals/run_eval.py` scores every scenario against a hand-written `ground_truth.json`:

- **precision / recall** over the accepted findings, so a missed finding and an invented one both
  cost something. Where a scenario has no expected findings there is nothing to divide by, so the
  scorer prints **`n/a`** rather than a 1.0 that would read as a measured perfect score — exactly
  why `must_not_flag` exists as the non-vacuous check for the clean tenancy;
- **verdict accuracy**, which is what makes `rejected` and `revised` scoreable rather than just
  `accepted`;
- **`must_not_flag`**, an explicit list of resources that must stay unreported — the clean tenancy
  and the deliberately idle standby are both here;
- **determinism**, by running the pipeline twice and comparing every finding and status.

### Held-out scoring: tenancies that did not exist when the agent was written

The three scenarios above were written by the same person who wrote the agent, which is the weakest
form of evidence for "these outputs are computed, not hardcoded". So they are not the only inputs it
is scored on. `scripts/make_scenario.py` derives a complete tenancy — instances, volumes, reserved
IPs, their telemetry series, their Terraform declarations — **and its own ground truth** from a
single integer seed, and the same evaluator scores it:

```
held_out_1    precision 1.0  recall 1.0  verdicts 1.0  findings 8   status success  deterministic True
...
held_out_6    precision 1.0  recall 1.0  verdicts 1.0  findings 6   status success  deterministic True

6 held-out tenancies, 0 failing
```

Everything in that block is generated: nobody chose which instances are idle, which are declared,
which carry a month-end schedule, or what the right answer is. Ground truth is derived from the same
random choices that shaped each resource, never written beside it.

**This is not a decorative harness.** Seed 6 carries a shape none of the committed scenarios have —
an idle, bursty, *undeclared* instance — and it found a real defect: the re-check re-derived that
instance's `unattributed` finding identically, and the loop superseded the untouched original, so
the report claimed a change of mind that never happened. Held-out scoring caught what three
hand-written scenarios missed, and `tests/test_make_scenario.py` now pins that seed.

```bash
# in the venv created above — --score needs the app's dependencies, --seed does not
python scripts/make_scenario.py --seed 7 --out /tmp/held_out_7   # one tenancy, with its truth
python scripts/make_scenario.py --score 8                        # generate and score eight
```

## Disclosure

- **Models and providers:** live mode calls one OpenAI-compatible `chat/completions` endpoint,
  configured by `LLM_BASE_URL` and `LLM_MODEL` (`.env`, gitignored, points at an Alibaba Cloud
  Model Studio token-plan endpoint running `qwen3.8-flash`; sample mode and the judge's run need
  no key and call no model). **Every committed artifact — `output_examples/`, `logs/samples/`,
  `evals/` — was produced by the deterministic rule engine** (`app/generator.py:RulesGenerator`),
  so results are reproducible without a provider. The model path is exercised live: on the lab
  tenancy it proposed claims that the figure guard rejected for unbacked numbers and rewrote from
  rule templates — visible as `figure_guard_rewrite` events on the run trace, which is the
  designed behaviour. Any model prose is checked by the figure guard in all four places it can
  appear (claim, revised claim, verdict reason, run narrative).
- **Agent frameworks:** none. The loop is hand-rolled in `app/loop.py` — no LangGraph, CrewAI or
  AutoGen.
- **Partner technologies:** Zetaris as the governed policy source (above); a Meterless **World Model**
  engine implemented in `app/world_model/` and consumed by Scout and Skeptic, with generated offline
  acceptance; and a Meterless **Nightshift** provider adapter implementing the documented contract,
  covered by contract tests, but **never served a live request** — the official Mac installer fails
  macOS Gatekeeper and has not been installed or bypassed. No NVIDIA model has been exercised. The
  earlier statement that no partner technology was mounted no longer describes this branch.
- **Live path:** built and **run against a live lab tenancy** (created 28 Sep per
  `docs/lab-tenancy.md`). `app/sources/oci_inventory.py` and `oci_telemetry.py` are real OCI SDK
  adapters behind the `Source` interface, exercised offline against SDK-shaped stubs
  (`tests/test_live_adapters.py`) and live against compute, block volume, public IP and Monitoring
  APIs; the first live + degraded runs surfaced five defects, all fixed with regression tests. IaC
  and policy stay file-backed in both modes (they are files, not OCI services). Without reachable
  credentials a `SAMPLE_MODE=false` run degrades to fixtures, reports `status: partial` with
  `summary.backends` naming what answered, and warns on stderr. `.env.example` documents every
  variable the adapters read.
- **External tools and libraries:** `pydantic` (models), `fastapi` + `uvicorn` (`POST /run`),
  `httpx` (API tests), `requests` (model calls), `pytest`, and `oci` — pinned for the live
  adapters, imported lazily inside their fetch paths so sample mode never loads the SDK.
- **Data sources:** `data/scenarios/example_1..3` and `iac`/`policy` are synthetic fixtures —
  example telemetry is **materialised deterministically** from the compact specs in
  `data/scenarios/*/telemetry.json` (CRC32-seeded, so identical across processes) rather than
  captured from any real system. One exception, disclosed on its face: `data/scenarios/lab_live`
  is a **capture of the author's own lab tenancy** (four throwaway instances, one orphan volume,
  one reserved IP), with every OCID masked by `scripts/mask_ocids.py` before it was committed and
  a `README.md` inside the directory saying so. It exists as the fixture fallback the live path
  degrades to. `data/pricing.json` holds rounded OCI list rates for cost estimation only.
  **No employer, customer or third-party data is present anywhere in this repository**, and a
  test fails the build if an unmasked OCID appears in any tracked file
  (`tests/test_mask_ocids.py`). `scripts/mask_ocids.py` masks real OCIDs before any artifact is
  committed or filmed.
- **Adapted open-source code:** none. Every file was written for this submission.
- **Known limitations:** the audit covers compute instances, block volumes and reserved public
  IPs only — not databases, load balancers, object storage or networking. Every committed result
  comes from fixtures or from the masked lab capture described above; the live adapters have run
  against the lab tenancy. The 5 October live audit had 93.3% coverage of its 168-hour window,
  but no re-check/revision: the batch burst was still inside that window. The 744-hour
  re-check needs 80% coverage, which this young lab cannot reach before submissions close;
  do not interpret insufficient-history abstention as a completed live revision. The next
  read-only observation is 9 October 00:00 SGT — see `docs/lab-tenancy.md`. Cost figures are list prices
  from a bundled catalog,
  not your invoice. A finding with `usd_per_month_upper_bound` impact is an upper bound, never a
  promised saving. Telemetry is CPU only, and a resource whose window is short has no CPU verdict
  at all rather than a hedged one. The IaC check reads file-backed declarations; the lab's
  Terraform-shaped labels are not evidence of a Terraform apply. A resource absent from those
  declarations is reported as unattributed by design, which is the intended behaviour and
  also a way to be annoying. A run examines at most 25 resources and says so when it truncates.
  The figure guard stops unsupported *numbers*, not unsupported *sentences* that contain none.
  The held-out generator multiplies the shapes that get tested; it does not widen the resource
  classes the audit covers, which remain the three above. Nothing is remediated: findings are
  recommendations, and the agent is read-only.
- **Sample mode:** `SAMPLE_MODE=true` runs the complete agent on fixture backends with no network
  and no credentials, and does not call a model. All four agents, the critique loop, the caps, the
  cost arithmetic and the report still execute for real; only the judgement source changes. A test
  monkeypatches `socket.socket` to prove no network call happens
  (`tests/test_loop.py::test_sample_mode_makes_no_network_calls`).
- **Packaging verification:** the fresh-clone path was verified end to end — a new clone, a
  Python 3.11.16 venv, `pip install -r requirements.txt`, the full suite via `pytest -q`, a
  credential-free `run.py`, and `POST /run` returning HTTP 200 in 20 ms. The `Dockerfile` was
  **not executed**: there is no Docker daemon on the build machine. It runs the same verified
  command (`python run.py --serve`) on `python:3.11-slim` with the same `0.0.0.0:8000` binding, but
  it is offered unverified and should be treated as such.
- **Review:** this branch was audited by an independent reviewer whose findings are recorded in
  `docs/decisions.md` (2026-09-24, "An independent review found five blockers"). Five of them were
  real and are fixed; the fixes each carry a regression test.

## Repository layout

| Path | Purpose |
|---|---|
| `run.py` | CLI entry point (`--serve` for HTTP) |
| `app/sources/` | Four source adapters: fixtures plus live OCI inventory/telemetry (offline-tested and run against the personal lab) |
| `app/agents/` | Planner, Scout, Skeptic, Writer — one file, one permission set each |
| `app/loop.py` | Bounded orchestrator: caps, degradation, termination |
| `app/analysis.py` | Every number the report contains |
| `app/generator.py` | The Generator seam: rule engine or model |
| `data/scenarios/` | Three scenarios plus their `ground_truth.json` |
| `evals/run_eval.py` | Precision, recall, verdict accuracy, determinism |
| `scripts/` | `run_examples.sh` (regenerates evidence), `make_scenario.py` (held-out generator), `mask_ocids.py` |
| `docs/` | Event brief, decision log, insights, spec and implementation plan |
