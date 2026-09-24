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

Run against a real tenancy by setting `SAMPLE_MODE=false` and the `OCI_*` variables from
`.env.example`. A live run needs an OCI API key; sample mode never does.

## The money shot

In `example_1`, one instance is genuinely interesting.

**Round 1.** The Scout reads seven days of CPU telemetry for `batch-01`, finds a mean of 0.77% and
a peak of 0.89%, and proposes a cost-waste finding: idle instance, $90.52/month.

**The Skeptic rejects it.** Its declaration says the instance runs a month-end batch job. A
month-end cadence is invisible in a seven-day window, so the mean is not evidence of anything.
The Skeptic does not accept or reject — it returns `recheck`, with a request for a wider window.

**Round 2.** The Planner narrows the assignment to that one resource and widens the lookback to
31 days. The burst appears: mean 1.00%, peak 58%. The Scout's conclusion changes — this is not an
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
   four sources      │  inventory  telemetry  iac  policy       │   live backends (OCI SDK)
   one interface     │  ── each with a fixture twin ──          │   or bundled JSON fixtures
                     └──────────────────────────────────────────┘
                                        │
        ┌───────────────┬───────────────┴────────────┬───────────────┐
        │   Planner     │        Scout               │   Skeptic     │   Writer
        │  owns the run │  evidence → candidates     │  accept /     │  accepted +
        │  caps, rounds │  cannot see rulings        │  reject /     │  rejected-with-
        │  assignment   │                            │  recheck      │  reasons
        └───────────────┴────────────────────────────┴───────────────┘
                                        │
                        one append-only RunState + one JSONL trace
```

Each agent has a permission set that is structurally enforced, not described: the Scout cannot set
a finding's status (it has no such field), the Skeptic cannot propose a finding, and the Writer
cannot investigate — it only renders what the other three produced.

**The determinism boundary is the design's spine.** Code decides enumeration, cost arithmetic,
coverage checks, tag parsing, IaC matching, threshold comparisons, cap enforcement, evidence IDs
and verdict eligibility. A model decides interpretation, ambiguous judgement, explanation and
prose. **No number in a report is produced by a model**, and the Writer refuses to emit a figure
that no evidence in the ledger supports (`app/agents/writer.py:assert_figures_traceable`).

**Caps are enforced and always visible.** `MAX_ROUNDS=3`, ≤25 resources per run, ≤2 Skeptic
re-checks per finding, a 300 s soft / 540 s hard wall clock, and timeouts on every external call.
Any cap that fires sets the run's `status` to `capped` and names itself in `caps_hit` — a truncated
investigation never reads as a finished one. A finding the Skeptic asked to re-check, which the run
then never got back to, is not reported as accepted: it moves to `undetermined` with the reason
(`app/loop.py`), because the whole point of the caps is that a run which gives up must say so.

**Degradation is not fabrication.** A source that fails is retried once, then falls back to fixture
data with the degradation logged and the source named in the report; if there is no fallback the
run finishes `partial` and says which source was unavailable. There is no path that invents data.

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
and the runs it starts. Nothing in them is hand-written or edited. If the code changes, re-run the
script and the diff shows exactly what changed.

| Evidence | Where |
|---|---|
| Three input requests | `input_examples/example_{1,2,3}.json` |
| Three matching JSON reports | `output_examples/example_{1,2,3}.json` |
| Three rendered audits | `output_examples/example_{1,2,3}_report.md` |
| Full stdout of each run, including every trace line | `output_examples/example_{1,2,3}.log` |
| Agent trace (one JSONL line per action) | `logs/samples/trace-example_{1,2,3}.jsonl` |
| Shared run state (append-only) | `logs/samples/state-example_{1,2,3}.jsonl` |
| Evaluation results | `output_examples/eval.txt` |

The three scenarios differ meaningfully rather than cosmetically:

1. **example_1 — the false positive.** Six resources, five pathologies, and one instance whose
   seven-day window hides a monthly burst. The run rejects its own first finding and revises it.
2. **example_2 — the clean tenancy.** Five resources, all declared, all appropriately loaded. The
   correct output is **no findings at all**. A scanner that invents work fails here.
3. **example_3 — the tag that changes the answer.** An idle instance declared *idle by design* must
   not be reported; an untagged idle instance yields two findings; an instance with only 20% of the
   requested history lands in `undetermined`; an attached IP is correctly ignored.

Every trace line carries `timestamp`, `run_id`, `agent_name`, `action`, `input_summary`,
`output_summary`, `target_agent`, `confidence`, `retry_count` and `status`, plus `round` and
`evidence_refs`. Traces are written to stdout **and** to a file.

## Evaluation

```
example_1    precision 1.0    recall 1.0    verdicts 1.0    findings 5   status success  deterministic True
example_2    precision 1.0    recall 1.0    verdicts 1.0    findings 0   status success  deterministic True
example_3    precision 1.0    recall 1.0    verdicts 1.0    findings 4   status success  deterministic True

3 scenarios, 0 failing
```

`evals/run_eval.py` scores every scenario against a hand-written `ground_truth.json`:

- **precision / recall** over the accepted findings, so a missed finding and an invented one both
  cost something;
- **verdict accuracy**, which is what makes `rejected` and `revised` scoreable rather than just
  `accepted`;
- **`must_not_flag`**, an explicit list of resources that must stay unreported — the clean tenancy
  and the deliberately idle standby are both here;
- **determinism**, by running the pipeline twice and comparing every finding and status.

## Disclosure

- **Models and providers:** live mode calls one OpenAI-compatible `chat/completions` endpoint,
  configured by `LLM_BASE_URL` and `LLM_MODEL`. **No live provider is configured in this
  repository**, and both committed sample runs used the deterministic rule engine in
  `app/generator.py:RulesGenerator`. Setting `LLM_API_KEY` switches the judgement path to a model
  without any other change.
- **Agent frameworks:** none. The loop is hand-rolled in `app/loop.py` — no LangGraph, CrewAI or
  AutoGen.
- **Partner technologies:** none mounted, as stated above.
- **External tools and libraries:** `pydantic` (models), `fastapi` + `uvicorn` (`POST /run`),
  `httpx` (API tests), `requests` (model calls), `pytest`, and `oci` on the live path only.
- **Data sources:** all synthetic. The scenarios under `data/scenarios/` are fixtures; their
  telemetry series are **materialised deterministically** from the compact specs in
  `data/scenarios/*/telemetry.json` (CRC32-seeded, so identical across processes) rather than
  captured from any real system. `data/pricing.json` holds rounded OCI list rates for cost
  estimation only. **No employer, customer or third-party data is present anywhere in this
  repository**, and OCIDs in every fixture are masked placeholders. `scripts/mask_ocids.py` masks
  real OCIDs before any artifact is committed or filmed.
- **Adapted open-source code:** none. Every file was written for this submission.
- **Known limitations:** the audit covers compute instances, block volumes and reserved public
  IPs only — not databases, load balancers, object storage or networking. Cost figures are list
  prices from a bundled catalog, not your invoice. A finding with
  `usd_per_month_upper_bound` impact is an upper bound, never a promised saving. Telemetry is CPU
  only. The IaC check reads Terraform declarations; a resource managed by hand in the console is
  reported as unattributed by design, which is the intended behaviour and also a way to be
  annoying. Nothing is remediated: findings are recommendations, and the agent is read-only.
- **Sample mode:** `SAMPLE_MODE=true` runs the complete agent on fixture backends with no network
  and no credentials, and does not call a model. All four agents, the critique loop, the caps, the
  cost arithmetic and the report still execute for real; only the judgement source changes. A test
  monkeypatches `socket.socket` to prove no network call happens
  (`tests/test_loop.py::test_sample_mode_makes_no_network_calls`).
- **Packaging verification:** the fresh-clone path was verified end to end — a new clone, a
  Python 3.11.16 venv, `pip install -r requirements.txt`, `pytest` (63 passed), a credential-free
  `run.py`, and `POST /run` returning HTTP 200 in 20 ms. The `Dockerfile` was **not executed**:
  there is no Docker daemon on the build machine. It runs the same verified command
  (`python run.py --serve`) on `python:3.11-slim` with the same `0.0.0.0:8000` binding, but it is
  offered unverified and should be treated as such.
- **Determinism:** every figure in a report comes from `app/analysis.py`, and the Writer refuses to
  emit a number that no evidence supports.

## Repository layout

| Path | Purpose |
|---|---|
| `run.py` | CLI entry point (`--serve` for HTTP) |
| `app/sources/` | Four source adapters, each with a fixture backend and a live twin |
| `app/agents/` | Planner, Scout, Skeptic, Writer — one file, one permission set each |
| `app/loop.py` | Bounded orchestrator: caps, degradation, termination |
| `app/analysis.py` | Every number the report contains |
| `app/generator.py` | The Generator seam: rule engine or model |
| `data/scenarios/` | Three scenarios plus their `ground_truth.json` |
| `evals/run_eval.py` | Precision, recall, verdict accuracy, determinism |
| `scripts/` | `run_examples.sh` (regenerates evidence), `mask_ocids.py` |
| `docs/` | Event brief, decision log, insights, spec and implementation plan |
