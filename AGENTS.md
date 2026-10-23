# AGENTS.md — Open Agent Hackathon 2026

Auto-injected into every session and every coding agent working in this directory.
Keep it short, current, and factual. Update **State** as things change.

## What this is

A solo entry to the **Open Agent Hackathon 2026** (GenAI Works). Goal: build an agent
that does real work — not a chatbot, not a demo. Judged against published criteria.

## Read first

- **`notes/zetaris.md`** — 14 Oct meeting/code analysis and direct live-rule verification.
  **Current published rules supersede the older event assumptions below:** build window
  **22 Oct 00:00 → 27 Oct 23:45 UTC**; Zetaris + Meterless integrations and Cursor development
  are mandatory. NVIDIA wording differs between the event rules and Academy; confirm it.
  The September no-sponsor build is a declared pre-existing baseline, not a compliant entry.
  Builder selected **Wildcard [Tinkerer]** on 22 Oct (working; changeable until deadline).
  No integration or track switch is authorised by that analysis alone. The 21 Oct lab teardown now precedes kickoff;
  do not extend resource lifetime without balance/expiry verification and approval.
- **`notes/host-docs-digest.md`** — digest of the twelve documents the organisers shared:
  working-draft rules, AI usage policy, code of conduct, pre-submission self-check,
  onboarding deck, and the three Meterless agent-engine specs. Read it before deciding
  anything. It is the distilled reference; the raw attachments live outside the repo.
- **`notes/meterless.md`** — 9 Oct sponsor analysis, version/source distinctions and actual
  Driftwatch integration seams. Recommends minimal World Model first; optional H-MEM,
  Markovian only with measured need. Recommendation only: no engine mounted, no scope
  approval. Its optional-sponsor/event-calendar assumptions are superseded by the 14 Oct
  live-rule check in `notes/zetaris.md`; a scoped sponsor implementation is still unapproved.
- The Official Rules document is a **working draft**. The binding rules are published on the
  event page. Sections marked `[VERIFY]` in the host docs are the organisers' own to-do
  list, not ours.
- The digest carries a **re-verification list** of facts where those drafts disagree with
  this file — partner stack, track names, bonus points. This file's versions came from the
  HackOS event pages and an organiser channel. Re-check on HackOS before the build window.
Recommended pre-submission layout lives in the digest §4. Present: `run.py`, `Dockerfile`,
`requirements.txt`, `app/`, `data/`, `scripts/`, `input_examples/`, `output_examples/`, `logs/`
(with committed samples under `logs/samples/`), `evals/`.

## State

- **Track:** **Wildcard [Tinkerer]: Bring Your Own Project** — builder-approved 22 Oct as the
  working selection; changeable until 27 Oct 23:45 UTC. The September baseline is declared
  pre-existing and the submission is scored on in-window new work; see `notes/zetaris.md` and
  `docs/decisions.md` 2026-10-22.
- **Idea / use case:** chosen. *Driftwatch* — an OCI tenancy auditor for cost waste and
  unattributed (shadow) infrastructure, with a critic agent that can reject a finding and force
  a re-investigation. Design approved 2026-09-24; see
  `docs/superpowers/specs/2026-09-24-oci-tenancy-auditor-design.md`.
- **Stack:** Python. Hand-rolled bounded agent loop, no orchestration framework. Bundled JSON
  fixtures drive sample mode; the `oci` SDK is pinned and imported lazily by the live adapters
  (Task 15 built, offline-tested **and run live against the lab tenancy**). No UI. Reasoning in the spec §5.
- **Budget:** ~20 h in the window; a frozen ~15 h must-ship list. Spec §11.
- **Pre-existing baseline: built, reviewed and verified** (2026-09-24; sponsor requirements
  not yet met). Tasks 1–14 of the plan are
  complete: the full suite passes (`pytest -q`), and the fresh-clone path was verified end to end —
  Python 3.11.16 venv, `pip install -r requirements.txt`, credential-free `run.py`, `POST /run`
  returning HTTP 200, and `evals/run_eval.py` scoring three scenarios at precision 1.0, recall 1.0,
  verdict accuracy 1.0, deterministic. An independent whole-branch review found five blockers and
  eleven lesser issues; all are fixed with regression tests. Evidence is generated, never
  hand-written: `scripts/run_examples.sh` produces `output_examples/` and `logs/samples/`.
- **Task 16 (held-out scenario generator): shipped** (2026-09-24). `scripts/make_scenario.py` derives
  a complete tenancy *and its ground truth* from an integer seed; ten seeds score precision 1.0,
  recall 1.0, verdict accuracy 1.0, deterministic. It earned its place immediately by finding two
  defects that neither the curated scenarios nor the review had surfaced — a no-op re-check reported
  as a revision (`app/loop.py`) and committed traces filed under the wrong scenario
  (`scripts/run_examples.sh`) — both fixed and guarded (`tests/test_committed_evidence.py`). Held-out
  numbers live in `output_examples/held_out.txt`.
- **Task 15 (live OCI adapters): Steps 1–4 built** (2026-09-26); **Step 5 — live runs against the
  lab tenancy — done** (2026-09-28). `app/sources/oci_inventory.py` and `oci_telemetry.py` are real
  SDK adapters behind the `Source` interface; 113 tests pass, hermetic offline suite intact. The first
  live + degraded runs found five defects, all fixed with regression tests: telemetry query grammar
  (compartmentId must be the API argument, not a filter), terminated-instance ghosts, missing
  A2/E5 pricing rows, the Scout's missing fixture fallback, and the real-OCID→masked fixture join.
  Committed fixtures live in `data/scenarios/lab_live/`. The month-end cron is verified installed on
  `lab-batch-01` for 1 Oct 02:00 **UTC** (= 10:00 SGT; instance clock is UTC); metric coverage
  reached 93.3% of the initial 168 h window in the 5 Oct live run. Mixed findings, no re-check or
  revision: the burst was still inside seven days; reports was rejected for declared purpose.
  The 13 Oct assessment records a real 744 h re-check followed by abstention at 359 h coverage.
  Its earliest continuous-span sufficiency estimate, 23 Oct 06:27 SGT, now lies inside the
  shifted build window; sufficient live coverage/revision still needs measurement, not a promise.
  Preserve originals; see `notes/oci-expiry-impact-2026-10-13.md` and `notes/zetaris.md`.
- **Lab tenancy (trial, ap-batam-1):** everything provisioned via API — `lab-prod`/`lab-test`, VCN,
  4× A1 instances with checklist tags + cloud-init workloads, both orphans. Credentials:
  `~/.oci/config` `[DRIFTWATCH2]` (read-only) / `[PROVISIONER2]` (build-time only); repo `.env`
  wired. The original Free-Tier tenancy (credit expired mid-Aug) is untouched as fallback. Paid
  costs ride the $300 trial credit (expires ~27 Oct); teardown due 21 Oct.
- **Still open pre-window:** confirm track/pre-existing eligibility, the final challenge and
  NVIDIA/Nemotron requirement; obtain sponsor access and approve a bounded integration scope.
  The supplied Zetaris meeting was analysed on 14 Oct, not installed or queried.
  **Packaging fully verified** (2026-09-28): repo pushed to the public remote
  (was 39 commits stale — caught by the first x86 verification attempt); fresh anonymous clone →
  116 tests → credential-free `run.py` pass; container verified on **x86** (Docker Desktop
  linux/amd64, Windows 11 work machine — build, `/health`, `POST /run` with figures identical to
  committed artifacts) and on **arm64** (podman, lab sandbox); fresh-export (git-less tar)
  install→pytest→run→/run→evals verified; the OCID guard was fixed for the git-less path
  (`output_examples/fresh_verify.txt`). Model provider wired: `qwen3.8-flash` via Alibaba Token
  Plan in `.env` (sample mode stays credential-free); first model-driven live run exercised the
  figure-guard rewrite path.
- **Sponsor integration (Zetaris): MOUNTED and live-accepted 22 Oct.** Policy snapshots
  (`example1_base_v2` / `example1_no_volume_v2`, synthetic, digests `58729b…`/`833ee5…`) published
  to the live engine via the builder-approved runbook `docs/zetaris-policy-operations.md`;
  least-privilege runtime user + key (builder-held); acceptance `sponsor_acceptance: true` with
  the R-1-removal causal proof in `output_examples/zetaris_acceptance_2026-10-22/`. A supplier CSV
  defect (embedded-quote truncation) was found by our own digest guard and worked around as v2 —
  see `notes/zetaris-engine-defects-2026-10-22.md`. Meterless/NVIDIA remain unmounted (honest
  status in README). Cursor free-tier quota died after Tasks 1–2; Tasks 3–6 are Hermes-executed,
  attribution in `notes/m1-build-log-2026-10-22.md`.
- **Build window:** 22 Oct 2026 00:00 UTC → 27 Oct 2026 23:45 UTC (live event rules, verified 14 Oct).

## Current hard dates (all UTC; live event page verified 14 Oct)

| Date | What |
|---|---|
| **22 Oct 00:00** | **Build window opens** |
| 22 Oct 23:59 | Registration closes |
| 27 Oct 00:00 | Judging opens |
| **27 Oct 23:45** | **Submissions close — hard deadline** |
| 6 Nov 16:00 | Results announced |

Earlier workshop/onboarding calendar entries are historical, not re-verified here.

## Current tracks (new selection pending; live event page verified 14 Oct)

1. **Solving Fragmented Intelligence**
2. **The Agent That Can Explain Why**
3. **Reasoning Architecture**

Plus **Wildcard [Tinkerer]: Bring Your Own Project**, scored on new work, not the existing
baseline. The page calls it a bonus track while requiring one primary selection; confirm the
submission-form mapping. Declared pre-existing components are allowed by Rules §§4–5.

## Current submission gate

Published Rules §6 requires a **1–4 minute demo, slide deck, GitHub repo/README**, and an
explanation of Zetaris/Meterless integration, Cursor development and NVIDIA contribution.
The quality safeguards below remain the project's bar; earlier draft guidance is not the
current binding deliverable list. Sponsor integration scope is still pending approval.

## Sponsor tech — runtime roles, not mounted yet

| Sponsor | Layer | Use it to |
|---|---|---|
| Zetaris | Data | Required integration; documented SQL access over REST/JDBC, proposed policy/IaC adapter |
| Meterless | Cognition/context | Required integration; proposed minimal World Model (`notes/meterless.md`) |
| Cursor | Development | Required development tool (rules §5, unchanged as of 22 Oct). **No event credits — free tier only** (announced 22 Oct 08:53 UTC); the $2,000 Cursor money is a prize pool, per the onboarding call. Guide update pending. Actual free-tier Cursor sessions retained as evidence. |
| NVIDIA | Models/workflow | Event rules require contribution where useful; Academy specifies Nemotron — confirm |

## Non-negotiables (these are scored, and are expensive to retrofit)

**Packaging** — a judge must be able to run it without us.

- Runs from a **clean setup, no manual steps**, verified from a fresh clone.
- A **programmatic entry point** — `run.py` or `POST /run` taking JSON and returning JSON.
  A UI must never be the only way in. Technical and Demo both depend on this.
- **CPU-only.** Nothing installs after the app starts, no runtime model or dataset downloads.
- A run finishes in **minutes** (target 5–10), with timeouts on every external call and
  **capped agent loops** — unbounded debate is the top cause of a hung run.
- `SAMPLE_MODE=true` runs the **whole agent on cached data with no credentials and no
  network**, still doing real work. This is how a judge without our keys experiences it.

**Truth** — integrity, not polish.

- Outputs are **generated, never hardcoded**. No known-input→prewritten-output mapping, no
  demo-only branch, no hand-written traces. A fabricated log is worse than no log.
- Credentials come from **environment variables only**. Nothing hardcoded.
- **No secrets, keys or tokens committed** — not in code, logs, examples or the demo video.
  `.env` is gitignored; `.env.example` is the template. If one ever lands in a commit,
  rotate the key with the provider *first*.
- README states limitations honestly. Never claim more than the code does.

**Evidence** — how the agent worked is the score.

- **Logs to stdout and `logs/trace-<run_id>.jsonl`** — ≥2 named agents doing distinct
  things, handoffs, critique or validation, retries and recovery, tied to the input actually
  processed. Technical and Demo both rest on this.
- Sample **inputs and outputs** included — at least three, each matching, each differing
  meaningfully.
- **Where each sponsor technology fits** is written down, and each is load-bearing rather
  than decorative. Partner calls get a timeout and a fallback.
- README discloses: models, frameworks, partner tech and where each sits, data sources and
  whether any is sample or synthetic, adapted open-source code, limitations, sample mode.

## Conventions

- Record every significant choice in `docs/decisions.md` with the reason.
- Sponsor findings go in `notes/`.
- `evals/` and `docs/insights.md` exist to earn bonus points — populate them as you go,
  not at the end.
- Repo remote: https://github.com/antnoumous/antynomoushackathon26
