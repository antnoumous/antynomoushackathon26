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

## 2026-09-24 — A capped run may not publish a claim its critic refused

**Decision:** A candidate the Skeptic answered with `recheck` that the loop never returned to is
removed from the findings and reported under `undetermined` with the reason, and a
`not_concluded` line is written to the trace.

**Why:** Found by testing the hard wall clock, which had never been exercised. The Writer's status
branches fell through to `accepted` for a `recheck` verdict, so a run that hit its hard budget
would have published the contested claim verbatim — the one outcome the caps exist to prevent.
The three committed scenarios regenerate identically after the fix, which is the evidence that it
changed nothing except the path where the loop gives up.

## 2026-09-24 — An independent review found five blockers; all five are fixed

**Decision:** A fresh reviewer audited the whole must-ship branch, read-only, with instructions to
verify claims by running code rather than reading prose, and to hunt for anything that would
embarrass the author in front of a judge. Every finding was reproduced independently before being
fixed, and every fix carries a regression test.

**What it found, and what changed:**

1. **The README advertised a live path that does not exist.** `app/sources/live.py` raises for all
   four sources, so `SAMPLE_MODE=false` degraded to fixtures and still produced a report labelled
   `mode: live`. Reproduced: eight findings including "averages 0.0% CPU", no warning anywhere.
   *Fixed by telling the truth* — the README's quickstart, diagram, library list and disclosure now
   say only sample mode is implemented; the report carries `summary.backends` and
   `summary.sources_degraded`; and `run_pipeline` prints a stderr warning when a live run got no
   live backend. After the fix the same command yields three shapes-based findings, zero CPU claims,
   `backends: ['fixture','none']`, and `status: partial`.
2. **The 25-resource cap truncated silently** while `resources_examined` reported the full tenancy
   count — a report that overstates its own coverage. *Fixed:* the Planner records `max_resources`,
   emits a `cap_hit` trace line naming how many were dropped, and the summary now distinguishes
   `resources_examined` from `resources_in_scope`.
3. **The Scout invented telemetry when telemetry was unavailable** — a hardcoded
   `mean 0.0 / coverage_ratio 1.0 / sufficient True` fallback that published "averages 0.0% CPU"
   with no telemetry evidence, defeating the very guard meant to catch it (the numbers in
   `candidate.stats` were vouchable by the candidate itself). *Fixed:* there is now a single
   `NO_TELEMETRY_STATS` shape with `sufficient: False`, so a resource with no series lands in
   `undetermined` and no CPU rule can fire; `candidate.stats` is no longer a source for the Writer's
   allow-list; and whether a rule needs telemetry is derived from its own `when` keys, so the
   volume and IP findings that never needed a series still stand.
4. **The figure guard covered only one of four prose fields.** `summary['narrative']` and every
   `ruling.reason` reached the report and the rendered Markdown unchecked, so a bad model could put
   "41,998.37 USD" in the audit with no evidence behind it. *Fixed:* all four fields are checked, and
   currency figures are checked against evidence specifically — `300` in the text is no longer
   acceptable merely because 300 is the soft wall clock.
5. **The re-check cap was unreachable.** `recheck_counts` was keyed by candidate id, and every round
   mints a new id, so the counter could never reach 2; and the branch returned a rejection instead of
   recording a cap. *Fixed:* keyed by resource and finding class, and firing now names
   `max_rechecks_per_finding` in `caps_hit` with a `cap_hit` trace line.

**Also fixed from the same review:** the wall clock is now checked before each resource and each
model call's timeout is trimmed to the remaining budget (a budget sampled once per round cannot
bound the round in progress); a missing or malformed fixture degrades the source instead of raising
out of `run()`; `run_pipeline` closes its trace and state handles; the evaluator prints `n/a` instead
of a vacuous 1.0 for a scenario with no expected findings; `mask_ocids.py` catches short-suffix
OCIDs (and the plan's own example token is now masked, which is how that was proven); and three
README claims that overstated the code are corrected.

**Why this entry exists:** the review found the exact failure mode this project cannot afford —
confident, precise-looking output that no evidence supports. The lesson is recorded rather than
summarised away: **every claim in the README is now something a script can check**, and
`tests/test_mask_ocids.py` keeps the OCID claim honest by testing the tool and scanning the repo.

### Follow-up pass on the same review

Re-reading the full findings list the next day (the middle of it had been truncated in the session
context) turned up three items that the first pass had left half-closed, and they are worth naming
because the pattern is the same each time — the fix was right and the coverage was narrow:

- **The magnitude whitelist was still a standing allowance** (finding 6). Currency was already
  evidence-only, but a fabricated *non-currency* figure equal to a cap constant still sailed through
  `assert_figures_traceable`, because the allowed set was a hardcoded list (`0-5, 7, 10, 20, 25, 41,
  60, 168, 300, 540, 730, 744`). It is now derived from the run: `structural_literals(config)` reads
  the caps, round count, re-check budget and lookback out of the configuration, so a request that
  lowers `max_resources` also drops `25` from the allowance. Fixing it exposed a second flaw in our
  own rule — with `300` legitimately a structural constant, `"300 USD"` became publishable — so the
  guard now takes **two tiers**: `allowed` for magnitudes, `computed` (payload or code arithmetic)
  for money. A single set cannot express the difference between a duration and a price.
- **The cap's narrative half was untested** (finding 2). `summary.resources_examined` was fixed and
  tested, but the narrative — the line a human reads first — was only correct by construction. The
  cap test now asserts `"Audited 25 resources"` and that the tenancy size `30` appears nowhere.
- **The corrupt-fixture path was untested** (finding 9). A *missing* fixture directory was covered; a
  half-written JSON file is the realistic corruption, and it is now a test too.

The three scenarios regenerate byte-identically apart from the run id, which is the evidence that
tightening the allowance changed nothing published.

## 2026-09-24 — Held-out scoring (Task 16), and the two defects it found

**Decision:** build the held-out scenario generator now rather than waiting for the 17 Oct
checkpoint. It needs no credentials and no OCI tenancy, so unlike Task 15 it is verifiable today, and
it is the strongest available answer to "are these outputs hardcoded" — the agent is scored on
tenancies that did not exist when it was written. Three hand-written scenarios were written by the
same person as the agent; generated ones were not.

**What it found, in the first ten seeds:**

1. **A re-check that changed nothing was reported as a revision.** Seed 6 generates an idle, bursty,
   *undeclared* instance: round 1 proposes a `cost_waste` finding and an `unattributed` one, the
   schedule signal sends the cost finding back for a wider window, and the Scout — working per
   resource, not per class — re-derives the `unattributed` finding identically. The supersede rule
   matched on resource and class alone, so it marked the untouched original `rejected` and its
   identical repeat `revised`. That is a claim about the agent's reasoning that is simply false, in
   the one document meant to make that reasoning visible. Fixed: supersede now requires a *different*
   conclusion (rules, claim, impact — never the candidate id, which is new every round by design);
   an identical re-derivation is recorded as `duplicate_finding` and dropped, and the earlier ruling
   stands. `tests/test_loop.py` pins the shape, and seed 6 is pinned in the held-out test.
2. **The committed traces were one scenario behind.** `scripts/run_examples.sh` filed each run's
   trace, state and report by file mtime ("the newest file in `logs/`"), and two consecutive runs
   land in the same second. `-nt` is false for equal timestamps, so the loop kept the earlier
   candidate: `trace-example_2.jsonl` was committed carrying example_1's run (19 lines, "Audited 6
   resources ... 4 findings accepted") and example_3 carried example_2's clean tenancy. The evidence
   a judge reads was describing a different input. Fixed by reading `trace_path` and
   `report_markdown_path` out of the report the run just wrote — the fact is already recorded, so
   guessing was never necessary — and guarded by `tests/test_committed_evidence.py`, which asserts
   every committed trace carries its own report's run id and narrative and that the state file's
   tenancy count agrees with the report's.

**Deviation from the plan, recorded rather than smoothed over:** Task 16's draft placed the
month-end burst at a fixed absolute date 34 days before the scenario's `now` — outside both the
7-day window the run requests and the 31-day window the Skeptic widens to. The burst would never
have materialised, so the ground truth's `revised` verdict could not have occurred and the test
would have failed against a *correct* agent. The burst is now derived from `now` (20 days back:
inside 31 days, outside 7), which is the arrangement the re-check mechanism needs; the arithmetic is
explained in the module docstring because it is the load-bearing part.

**Lesson, recorded in `docs/insights.md`:** three scenarios written by the author test the author's
assumptions. A generator tests the space. Both defects above were invisible to the committed
scenarios and to a full-length independent review of them.

## 2026-09-26 — Task 15 adapters built now; only the live run waits for the tenancy

**Decision:** build the live OCI adapters (Task 15 Steps 1–4) immediately rather than at the
17 Oct checkpoint. The checkpoint gate was about *risk* — whether to spend window hours on a path
that might not verify. It was never a rules constraint: only the Tinkerer Track is limited to
work built during the window, and spec §5.2 already treats the lab tenancy as pre-window
infrastructure. Steps 1–4 need no tenancy and no credentials; only Step 5's live run does.
Building now converts the 17 Oct question from "should we build the live path?" into "did the
live run work?" — a far smaller thing to answer with two weeks of window left.

**The time-critical fact that forced the date.** The lab's false-positive workload is a *monthly*
cron. Its burst must exist in Monitoring history during the window (15–20 Oct), and the only
month-end inside reach is **1 Oct** — 1 Nov falls after submissions close. 5-minute-resolution
metrics are retained 30 days, so a 1 Oct burst is still queryable on 20 Oct, but only if the
tenancy and the cron exist by **29 Sep**. `docs/lab-tenancy.md` is the operational checklist
(compartments, IAM read-only policy, four instances with their exact tags, the two orphans, the
cron and load scripts, verification steps, masking rules). This is the entrant's errand, not
code: the tenancy must be provisioned this week or the live re-check→revision demo is impossible
and the live path shrinks to idle + orphan findings.

**Deviations from the plan's draft, each caught by checking the pinned SDK rather than the
draft:** inventory enumerates volumes and reserved IPs too (the draft's instances-only adapter
would leave R-1/R-2 unfireable live); `list_volume_attachments` is on `ComputeClient`; telemetry
resolution widens to hourly beyond 720 h because 5-minute data is retained only 30 days and a
744 h re-check at 5 m would silently come back short; file-backed IaC/policy sources take the
run's scenario directory instead of a hardcoded path. Full record in the plan's Task 15 section.

**Hermeticity rule added:** every live-path test pins `OCI_CONFIG_FILE` at a nonexistent path —
including the pre-existing degradation test in `tests/test_entrypoints.py`, which would otherwise
have started auditing a real tenancy on any machine that has `~/.oci/config`. A test suite must
never depend on the absence of credentials on the machine running it.

## 2026-09-28 — Lab tenancy home region: ap-batam-1

**Decision:** the lab tenancy's home region is **ap-batam-1** (Jakarta/Batam, Indonesia), not the
ap-singapore-1 used in earlier drafts. `.env.example` and `docs/lab-tenancy.md` updated; the
`ap-singapore-1` strings in `tests/test_mask_ocids.py` stay — they are synthetic OCID fixtures,
not a region assumption.

**Consequences.** Always Free compute must be created in the home region, which ap-batam-1 is —
fine. It is a newer, single-AD region, so the A1 (ARM) capacity-retry-across-ADs fallback in the
checklist does not apply there: verify A1 availability via the Console's Always Free badge or
Limits page before planning around ARM instances. Pricing is OCI-published USD and uniform
across regions, so the ≈ $8.6/month orphan estimate stands.

## 2026-09-28 — Lab moves to a fresh trial tenancy; ap-batam-1 abandoned for the live path

**Findings, all verified by live API calls:** the original tenancy (created 15 Jul 2026) passed
its 30-day trial credit ~mid-Aug; it can no longer launch paid shapes. In ap-batam-1 it also
sees *no* E2.1.Micro shapes at all (`list_shapes` → A1.Flex + A2.Flex only), and A1.Flex is
"Out of host capacity" with no second AD to retry in. A bare A2 launch fails with the
unpayable-account signature ("valid ratio range: 0-0"). The Always-Free compute story the
checklist assumed does not hold in this region/account.

**Decision:** build the lab in a new trial tenancy (singapore recommended) whose $300 credit
covers the run; if A1 crunches again there, launch 1-OCPU E4.Flex on credit (~$100 for the
window, alert at $50). Risk noted honestly: OCI permits one free account per person, so the
fresh trial is a ToS-grey choice the entrant carries personally; the Batam lab remains intact
as a free-tier fallback and its IAM/network/volume assets are already built. The month-end
deadline (cron installed before 1 Oct) is unchanged.

## 2026-09-28 — Lab rebuilt in the trial tenancy; first live run found three defects, all fixed

**What happened:** the new trial tenancy (home region ap-batam-1, same keys re-uploaded) has
working capacity: A1.Flex launched instantly where the dead Free-Tier tenancy was blocked. Full
lab built via API: compartments, VCN, both orphans, four instances with checklist tags and
cloud-installed workloads — batch-01's month-end cron verified in place, web-01 reporting a
steady ~50.5% CPU. The trial's $300 credit covers the paid-side costs; A1s stay inside the
free 3,000 OCPU-h envelope.

**Defects the first live run (Task 15 Step 5) found — none visible to any offline test:**
1. `app/sources/oci_telemetry.py` built queries as `mean() {compartmentId = "…"}`, which the
   live Monitoring service rejects ("Not Supported yet" / parse errors). The service scopes by
   the compartment_id *argument*; the adapter now issues one call per compartment.
2. `app/sources/oci_inventory.py` kept TERMINATED instances. A deleted shape-probe entered the
   inventory, and its old E5 shape — which no running resource can report — crash-locked
   pricing with a KeyError. Terminated means deleted: filtered at the source.
3. `data/pricing.json` was missing A2.Flex and E5.Flex rates that real tenancies report. Added
   from OCI list pricing. (Also: the whole-repo OCID guard now scans git-tracked files instead
   of every file on disk — live-run scratch under logs/ made the suite unrunnable on the very
   machine doing the live work, while the contract is only about *committed* content.)

**Verified after fixes:** 112 tests pass; a full live audit returns status success, mixed
backends inventory+telemetry live / iac+policy fixture, 6 resources, 3 findings (both orphans
as cost_waste, sandbox as unattributed), 4 compute instances honestly undetermined because
metric coverage (17 h of 168 h) cannot satisfy min_coverage_ratio until ~5 Oct. The live path
works; what it says is limited by the tenancy's age, which is exactly what it should say.

**Lab facts for later steps:** scenario dir `data/scenarios/lab_live/` (iac/policy committed;
its inventory/telemetry fallback fixtures per checklist §6 still pending — captured from a
mask_ocids pass first). Request JSON with both compartment OCIDs lives at /tmp (ephemeral);
regenerate from docs/lab-tenancy.md §6. LLM_* keys unset: the live run used the deterministic
writer, not the model.
