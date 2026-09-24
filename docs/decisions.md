# Decision log

One entry per significant choice. Record **what** and **why**. Append; don't rewrite
history. If a decision is reversed, add a new entry saying so and why.

---

## 2026-09-24 — Solo entry

**Decision:** Entering solo, not as a team.

**Why:** Confirmed by the builder. Constrains scope: the 144-hour window is one person's
attention, so the build must be small and deep rather than broad.

## 2026-09-24 — Design the repo backwards from the submission requirements

**Decision:** Scaffold README, `.gitignore`, `.env.example`, `evals/` and `docs/insights.md`
before any product code exists.

**Why:** The organisers' submission requirements (clean setup, env-var credentials, no
committed secrets, logs, sample I/O, documented sponsor fit) and the 30 bonus points for
open-sourcing, evaluations and insights are all cheap on day one and expensive at 23:00 on
20 October. Structural homes now beat good intentions later.

## 2026-09-24 — Project lives at ~/projects/open-agent-hackathon

**Decision:** Local path `/Users/ant/projects/open-agent-hackathon`, remote
`https://github.com/antnoumous/antynomoushackathon26` (public).

**Why:** No pre-existing dev-directory convention on this machine. A public repo supports
the open-sourcing bonus criterion from the first commit.

## 2026-09-24 — Organiser documents digested into `notes/host-docs-digest.md`

**Decision:** Digest the twelve host-shared documents into one reference file in `notes/`
rather than copying the originals into the repo.

**Why:** The raw files stay with the organisers' own material; the repo gets the distilled
version plus a conflict table. `submission-requirements.md` and
`technical-execution-requirements.md` are byte-identical duplicates, and `official-rules.md`
is explicitly a *working draft* whose binding version lives on the event page — both worth
recording so no session treats a draft as final.

**Open:** the digest flags seven factual conflicts with `docs/event-brief.md` and
`AGENTS.md`, including the partner stack (host docs say Zetaris / Neo4j / Meterless — no
NVIDIA), the four track names, and the claimed 30 bonus points. The builder confirmed the
repo's version came from the **HackOS event pages and an organiser channel**, so
`event-brief.md` and `AGENTS.md` were left unchanged and the conflict table is framed as a
re-verification list, not an error list. Confirm on HackOS before the build window; the
track name in particular must match HackOS at submission time.

## 2026-09-24 — Track and stack deliberately deferred

**Decision:** No track, problem statement, language or framework chosen yet.

**Why:** Deciding these before understanding the builder's strengths and interests risks
six days spent building the wrong thing. Next conversation.

## 2026-09-24 — Track 02, and the problem statement: an OCI tenancy auditor

**Decision:** Enter **Track 02 — Autonomous Agent** with *Driftwatch*: an agent that audits an
Oracle Cloud tenancy for cost waste and unattributed ("shadow") infrastructure, where a
dedicated critic agent can reject a finding and force a re-investigation.

**Why:** The builder is an Oracle Cloud specialist (OIC, networking, firewall), so the domain
credibility is real rather than researched — which is what Impact (30 points) actually tests.
The problem is genuinely fragmented across four disconnected systems (control-plane inventory,
monitoring time-series, the Terraform repository, a policy/pricing reference). And the naive
version of the task is *wrong in a way a critic exists to catch*: a mean-CPU threshold flags
the month-end batch job that finance depends on. That gives the required multi-agent critique a
real job instead of a decorative one.

**Rejected:** Tinkerer Track (requires a pre-existing project to extend; there is none), an OIC
integration-flow auditor (no free-tier OIC instance, worse API surface, less legible to a judge
in three minutes), a firewall/rule-drift auditor over public corpora (no live integration).

## 2026-09-24 — Runs against the builder's own tenancy, never the employer's

**Decision:** The demo and all sample data come from a purpose-built personal OCI tenancy.

**Why:** "Unauthorised private, personal or restricted data" is a disqualification trigger, and
employer infrastructure telemetry, tags and cost data in a public repo and demo video is exactly
that. Owning the tenancy also means the judge's credential-free path and the builder's path run
the same code, and that drift is real rather than staged (some resources are created by CLI,
outside Terraform). Lab resources are created *before* the window so seven-day metric history
exists by 15 Oct; infrastructure created early is not code written early.

## 2026-09-24 — Four agents, a hand-rolled bounded loop, and no security findings

**Decision:** Ship exactly two finding classes (cost waste, unattributed infrastructure), four
named agents with distinct permission sets, a ~20-hour scope with a frozen ~15-hour must-ship
list, and no orchestration framework, no UI, and no compliance/security scoring.

**Why:** Rules §7.3 disqualifies prompt wrappers, "one agent with several labels" and fixed
chains with no critique, so the agent split is a scored requirement rather than a flourish —
hence the permission table in the spec, which makes the split structural. LangGraph is dropped
because the framework is not scored and a bounded loop emits the exact JSONL trace shape the
organisers specified. A UI is dropped because it can never be the only entry point. Security
findings are dropped because they are a second rule set and a second report format for no extra
demo value. The budget is ~20 hours with no slack, so the must-ship list is a complete
submission on its own and everything else is earnable stretch, decided at the 17 Oct checkpoint.

## 2026-09-24 — Fixtures first, live OCI second

**Decision:** Build sample mode end-to-end behind a `Source` interface before writing any live
OCI adapter, and treat the live path as stretch.

**Why:** `SAMPLE_MODE=true` is how a judge without credentials experiences the project, so it is
the primary path, not a fallback. Building it first also makes it the fastest development loop
(no network, no rate limits, deterministic) and reduces the Monitoring API to an optional
adapter rather than a critical-path dependency. A `Generator` seam keeps the model provider
equally swappable, which is what lets sample mode run with no credentials at all.

## 2026-09-24 — An unsupported interpreter fails with one line, not thirteen

**Decision:** `app/__init__.py` refuses to import on Python below 3.11 and prints the exact
command that fixes it. `requirements.txt` states the requirement in a header comment; the
README's quickstart and the Dockerfile both pin 3.11.

**Why:** Found by the fresh-clone check, not by reasoning: this machine's `python3` is 3.9.6, and
because pydantic evaluates annotations at runtime, `str | None` in the domain models surfaced as
**thirteen** unrelated `TypeError`s during test collection. A judge on a stock macOS or Ubuntu
`python3` would have hit exactly that wall and had no idea which of the thirteen errors was the
real one. The guard converts a misleading failure into an actionable one, which is worth more
than the line of code it costs.

## 2026-09-24 — Evidence is generated, never written by hand

**Decision:** Every file under `output_examples/` and `logs/samples/` is produced by
`scripts/run_examples.sh` and the runs it starts. Hand-editing them is prohibited, and the
`.gitignore` is written to match: working runs under `logs/` are ignored, `logs/samples/` is not.

**Why:** The organisers score the logs as evidence of how the agent worked, which means a
curated log is worse than useless — it is a fabricated trace, and the rules treat that as the
most serious kind of dishonesty. Making the generator a committed script means the evidence can
be regenerated and diffed, so a claim about the agent's behaviour is checkable rather than
asserted.

## 2026-09-24 — A published falsifier has to be executable

**Decision:** The Skeptic gained a declared-purpose check. A cost finding whose evidence states
a deliberate purpose (`by design`, `intentionally`, `do not delete`, `for now`, `left running`)
is **rejected** and withdrawn, before any threshold logic runs.

**Why:** The Scout attaches a `falsifier` to every candidate — the thing that would disprove it.
Building scenario 3 exposed that for a resource declared *idle by design* nothing in the code
could act on that falsifier, so the field was decoration and the scenario's correct answer was
unreachable. Either the falsifier means something or it should not be published; the test
`test_a_declared_purpose_withdraws_a_cost_finding` now pins it.

## 2026-09-24 — No sponsor technology mounted, stated plainly

**Decision:** Ship with no Zetaris, NVIDIA or Meterless integration, and say so in the README's
"Where the sponsor technologies fit" table rather than implying an integration the code does not
have.

**Why:** The partner stack is unverified against HackOS and the layer was scoped out early so the
critique loop and the honesty guarantees could actually be finished. A decorative integration
would be inspectable in seconds and would cost more credibility than an honest "not mounted",
especially since the rules score whether each sponsor technology is load-bearing. The seam is
left in place — the `policy` source adapter and the `Generator` interface — so the work is
additive rather than cosmetic if it is picked up at the 17 Oct checkpoint.

## 2026-09-24 — The plan is corrected in place when the build proves it wrong

**Decision:** When a task in
`docs/superpowers/plans/2026-09-24-driftwatch-implementation.md` contradicted what the code
needed, the plan was edited in the same commit as the fix, with the reason recorded.

**Why:** Seven plan defects were found only by running the tests — two tasks' tests never
hydrated their subjects, one asserted `"idle" not in reason` against a template that literally
says "not an idle resource", one required a `class` attribute that is a Python keyword, one
pinned a rounding artefact, and one rule field made its own promised output impossible. A plan
that is silently out of step with the code is worse than no plan, because the next session
trusts it; correcting it keeps it usable as the record of what was intended and why it changed.

