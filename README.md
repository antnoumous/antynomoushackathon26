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

**Only sample mode is implemented.** `SAMPLE_MODE=true` runs the full agent on the bundled
scenarios with no credentials and no network, and that is how this submission is meant to be
judged. Setting `SAMPLE_MODE=false` does **not** currently audit a real tenancy: every live
adapter is a placeholder that raises, so all four sources degrade to the bundled fixtures, the run
reports `status: partial` with `summary.backends` naming what actually answered, and a warning is
printed to stderr. The live OCI adapters are planned stretch work (Task 15 of the implementation
plan) and are not built. `oci` is pinned in `requirements.txt` for them, and nothing imports it
today.

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
   four sources      │  inventory  telemetry  iac  policy       │   live adapters: placeholders,
   one interface     │  ── each with a fixture twin ──          │   not built (Task 15 stretch)
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

**No sponsor technology is mounted.** That is a deliberate, recorded decision rather than an
omission: the sponsor layer was scoped out so the four-agent critique loop and the honesty
guarantees could be finished properly, and the design reasons are in
`docs/superpowers/specs/2026-09-24-oci-tenancy-auditor-design.md` §3.2 and §5.11. Stating this
plainly is better than claiming an integration the code does not contain.

The design does leave the seam for one: the `policy` source adapter is a swappable interface
(`app/sources/`), so a data-layer sponsor could supply the rule and price reference behind it
without touching any agent. Without it, the adapter reads `data/scenarios/*/policy.json`.

| Sponsor | Layer | Status in this submission |
|---|---|---|
| Zetaris | Data | Not mounted. The `policy` adapter is the seam it would occupy. |
| NVIDIA | Token | Not mounted. The model path is one OpenAI-compatible HTTP call, provider-agnostic (`app/generator.py:ModelGenerator`). |
| Meterless | Orchestration | Not mounted. The bounded loop in `app/loop.py` implements the same discipline — capped rounds, explicit termination, no unbounded debate. |

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
  configured by `LLM_BASE_URL` and `LLM_MODEL`. **No live provider is configured in this
  repository**, and every committed run used the deterministic rule engine in
  `app/generator.py:RulesGenerator`. Setting `LLM_API_KEY` switches the judgement path to a model
  without any other change — and the figure guard then applies to that model's prose in all four
  places it can appear (claim, revised claim, verdict reason, run narrative).
- **Agent frameworks:** none. The loop is hand-rolled in `app/loop.py` — no LangGraph, CrewAI or
  AutoGen.
- **Partner technologies:** none mounted, as stated above.
- **Live path:** not implemented. `app/sources/live.py` raises for every source, so
  `SAMPLE_MODE=false` degrades to the bundled fixtures, reports `status: partial` with
  `summary.backends` naming what answered, and warns on stderr. The OCI adapters are Task 15 of the
  plan. `.env.example` documents the variables they will need.
- **External tools and libraries:** `pydantic` (models), `fastapi` + `uvicorn` (`POST /run`),
  `httpx` (API tests), `requests` (model calls), `pytest`, and `oci` — pinned for the live adapters,
  which are not built, so **nothing imports it today**.
- **Data sources:** all synthetic. The scenarios under `data/scenarios/` are fixtures; their
  telemetry series are **materialised deterministically** from the compact specs in
  `data/scenarios/*/telemetry.json` (CRC32-seeded, so identical across processes) rather than
  captured from any real system. `data/pricing.json` holds rounded OCI list rates for cost
  estimation only. **No employer, customer or third-party data is present anywhere in this
  repository**, and a test fails the build if an unmasked OCID appears in any tracked file
  (`tests/test_mask_ocids.py`). `scripts/mask_ocids.py` masks real OCIDs before any artifact is
  committed or filmed.
- **Adapted open-source code:** none. Every file was written for this submission.
- **Known limitations:** the audit covers compute instances, block volumes and reserved public
  IPs only — not databases, load balancers, object storage or networking. It reads no live system:
  every committed result comes from fixtures. Cost figures are list prices from a bundled catalog,
  not your invoice. A finding with `usd_per_month_upper_bound` impact is an upper bound, never a
  promised saving. Telemetry is CPU only, and a resource whose window is short has no CPU verdict
  at all rather than a hedged one. The IaC check reads Terraform declarations; a resource managed by
  hand in the console is reported as unattributed by design, which is the intended behaviour and
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
| `app/sources/` | Four source adapters: fixture backends are real, live twins are placeholders (Task 15) |
| `app/agents/` | Planner, Scout, Skeptic, Writer — one file, one permission set each |
| `app/loop.py` | Bounded orchestrator: caps, degradation, termination |
| `app/analysis.py` | Every number the report contains |
| `app/generator.py` | The Generator seam: rule engine or model |
| `data/scenarios/` | Three scenarios plus their `ground_truth.json` |
| `evals/run_eval.py` | Precision, recall, verdict accuracy, determinism |
| `scripts/` | `run_examples.sh` (regenerates evidence), `make_scenario.py` (held-out generator), `mask_ocids.py` |
| `docs/` | Event brief, decision log, insights, spec and implementation plan |
