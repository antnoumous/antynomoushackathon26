# AGENTS.md — Open Agent Hackathon 2026

Auto-injected into every session and every coding agent working in this directory.
Keep it short, current, and factual. Update **State** as things change.

## What this is

A solo entry to the **Open Agent Hackathon 2026** (GenAI Works). Goal: build an agent
that does real work — not a chatbot, not a demo. Judged against published criteria.

## Read first

- **`notes/host-docs-digest.md`** — digest of the twelve documents the organisers shared:
  working-draft rules, AI usage policy, code of conduct, pre-submission self-check,
  onboarding deck, and the three Meterless agent-engine specs. Read it before deciding
  anything. It is the distilled reference; the raw attachments live outside the repo.
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

- **Track:** 02 — **Autonomous Agent** (as named on the event pages; exact HackOS spelling still
  to be confirmed before submitting — digest §3 uses a different set of names).
- **Idea / use case:** chosen. *Driftwatch* — an OCI tenancy auditor for cost waste and
  unattributed (shadow) infrastructure, with a critic agent that can reject a finding and force
  a re-investigation. Design approved 2026-09-24; see
  `docs/superpowers/specs/2026-09-24-oci-tenancy-auditor-design.md`.
- **Stack:** Python. Hand-rolled bounded agent loop, no orchestration framework. Bundled JSON
  fixtures drive sample mode; the `oci` SDK is pinned and imported lazily by the live adapters
  (Task 15 built, offline-tested **and run live against the lab tenancy**). No UI. Reasoning in the spec §5.
- **Budget:** ~20 h in the window; a frozen ~15 h must-ship list. Spec §11.
- **Must-ship path: built, reviewed and verified** (2026-09-24). Tasks 1–14 of the plan are
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
  satisfies the rules' 0.8 ratio from ~4 Oct.
- **Lab tenancy (trial, ap-batam-1):** everything provisioned via API — `lab-prod`/`lab-test`, VCN,
  4× A1 instances with checklist tags + cloud-init workloads, both orphans. Credentials:
  `~/.oci/config` `[DRIFTWATCH2]` (read-only) / `[PROVISIONER2]` (build-time only); repo `.env`
  wired. The original Free-Tier tenancy (credit expired mid-Aug) is untouched as fallback. Paid
  costs ride the $300 trial credit (expires ~27 Oct); teardown due 21 Oct.
- **Still open pre-window:** confirm track name and partner stack on HackOS; watch the 7 Oct
  Zetaris recording. **Packaging fully verified** (2026-09-28): repo pushed to the public remote
  (was 39 commits stale — caught by the first x86 verification attempt); fresh anonymous clone →
  116 tests → credential-free `run.py` pass; container verified on **x86** (Docker Desktop
  linux/amd64, Windows 11 work machine — build, `/health`, `POST /run` with figures identical to
  committed artifacts) and on **arm64** (podman, lab sandbox); fresh-export (git-less tar)
  install→pytest→run→/run→evals verified; the OCID guard was fixed for the git-less path
  (`output_examples/fresh_verify.txt`). Model provider wired: `qwen3.8-flash` via Alibaba Token
  Plan in `.env` (sample mode stays credential-free); first model-driven live run exercised the
  figure-guard rewrite path.
- **Build window:** 15 Oct 2026 00:00 UTC → 20 Oct 2026 23:45 UTC (144 hours).

## Hard dates (all UTC)

| Date | What |
|---|---|
| 7 Oct 16:00–17:30 | Zetaris workshop (data layer) — recorded |
| 8 Oct 16:00–17:30 | NVIDIA workshop (token layer) — recorded |
| 12 Oct 16:00–17:30 | Meterless workshop (orchestration layer) — recorded |
| 14 Oct 16:00–17:30 | Participant onboarding |
| **15 Oct 00:00** | **Build window opens** |
| **20 Oct 23:45** | **Submissions close — hard deadline** |
| 30 Oct 16:00 | Results announced (live call) |

## Tracks (pick exactly one)

1. **Connected Agent Context** — connect to real, fragmented data
2. **Autonomous Agent** — multi-step work without hand-holding
3. **The Agent That Can Explain Why** — reasoning transparency, provenance
4. **Reasoning Architecture** — the reasoning design itself

A fifth, the **Tinkerer Track**, is judged only on work built during the window.
Scope not yet confirmed from the official source.

## Sponsor tech — one layer each

| Sponsor | Layer | Use it to |
|---|---|---|
| Zetaris | Data | Connect to real, fragmented data via MCP |
| NVIDIA | Token | Scale reasoning cost-effectively |
| Meterless | Orchestration | Run autonomous multi-step workflows |

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
