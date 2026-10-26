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

## 2026-10-05 — Preserve the mixed live outcome; observe again after the burst ages out

**Verified record:** the completed 5 October midnight SGT job (`afb3343baf63`) produced
`run-f515942db7`, status success, six resources examined, five findings accepted and one
rejected. Inventory and telemetry were live; declarations and policy were file-backed;
no source degraded. All four CPU streams had 156.75/168 hours (93.3%) of coverage.
The saved 19-event trace carries the report's run ID throughout and only the initial
168-hour assignment: **no re-check or revision occurred**.

**Correction to the earlier prediction:** the 1 October 02:00–04:00 UTC batch burst was still
inside seven days on 5 October. Batch and sandbox matched R-4 (low mean, high peak), not
R-3 idle. Reports' R-4 finding was rejected because its declaration says "intentionally
running"; web was unflagged; both orphans and sandbox's R-5 finding were accepted. Low
average CPU alone does not prove idle waste, and declared intent is a real falsifier in
this agent. A successful audit is not an all-pass demo narrative.

**Evidence preservation:** keep the original report, metric capture and trace under ignored
`logs/`. `logs/checkpoint-20261005-originals.zip` also preserves the scheduler's saved report
and a generated SHA-256 manifest. The archive was read back, all four embedded artifact
hashes verified, and the original files confirmed unchanged. These raw artifacts are local
only; mask separate copies before any publication. No rules, declarations, thresholds,
source metrics or tenancy resources were changed for this follow-up.

**Decision:** scheduled a one-shot read-only audit at **9 October 2026 00:00 SGT
(8 October 16:00 UTC)**, with Telegram delivery. Job `f4aa6765456c`
(`driftwatch-post-burst-check`) was read back as enabled with that exact timestamp, target
`telegram:74067080`, repo workdir and persisted read-only/evidence-preservation instructions.
The scheduled burst leaves the rolling
168-hour window on **8 October 12:00 SGT**. Inspect the actual rule/critic path rather than
requiring a revision: other peaks can still yield R-4; if R-3 fires, schedule evidence should
request 744 hours. Preserve new outputs under distinct paths and compare against this run.

**Newly quantified limit:** the 744-hour re-check requires 595.2 hours at the unchanged 0.8
coverage threshold. The earliest saved CPU datapoint is 28 September 03:15 UTC; even with
continuous reporting, that span cannot clear before **23 October 06:27 SGT**, after the
20 October submission deadline. At the 9 October checkpoint the span can cover at most
about 34% of 744 hours. The adapter also widens that query to hourly resolution, so the
actual returned span may be shorter. Do not promise a completed live revision during the
build window or relax the threshold to manufacture one. A genuine re-check followed by
insufficient-history abstention is valid live evidence; the bundled scenarios demonstrate
the completed revision path separately.

**Next gates unchanged:** verify track and partner requirements on HackOS and review workshop
recordings before the build window; assess the real evidence at the 17 October checkpoint;
prepare the masked demo/submission during 15–20 October; retain the 21 October teardown plan.

## 2026-10-09 — Meterless material retained; integration recommendation, not scope approval

**Recorded:** the six supplied sponsor documents were analysed into `notes/meterless.md`,
with a hashed inventory, authority grading, public-primary-source cross-checks and a
mapping to the actual state/evidence/generator/agent code. A corresponding reference note
was saved in the default-profile Obsidian vault and linked from its Reference index.

**Recommendation, pending approval:** evaluate the minimum World Model (store, idempotent
ingest, context builder actually consumed by Scout/Skeptic) first; H-MEM only if a
multi-run test proves useful recall and correct supersession; Markovian only after a
benchmark reveals a growing-context problem. The current model path already uses local
structured context, not a full accumulated transcript, so token savings are not assumed.

**Unchanged:** the 24 September no-sponsor decision and 17 October reassessment gate.
This analysis did not mount an engine, change product code, modify fixtures or evidence,
run a live audit, or authorise a scope increase. README's "not mounted" disclosure stays.

**Open:** confirm the Python-adaptation eligibility/minimum evidence for Sponsor Tech,
the current track name, partner stack and scoring against the live event source. The
new World Model attachment removes one Neo4j reference; it does not settle the complete
partner list. The public Meterless hackathon rubric conflicts with the supplied event-specific
sponsor overview; neither supplier source settles the binding event rubric.
The 12 October Meterless workshop is still future on this entry's date; no recording was
watched here. Recalled knowledge must never substitute for the missing live metric history.

## 2026-10-14 — Zetaris meeting analysed; published event requirements changed

**Verified:** the supplied automated meeting capture was read in full and analysed in
`notes/zetaris.md` against the implemented source/critic/pricing paths and official Zetaris
connection/install/client references. Direct retrieval of the live event page, including
its expanded-rules payload, establishes **22 October 00:00 → 27 October 23:45 UTC**,
mandatory **Zetaris + Meterless integrations and Cursor development**, a different track
list, declared pre-existing code, and a **1–4 minute demo plus slide deck**. Search-index
content was stale and was not used as the calendar authority. NVIDIA wording conflicts
between the published event rules and Academy, so the exact Nemotron requirement stays open.

**Recorded consequence:** the September no-sponsor build is a useful pre-existing baseline,
not a submission-compliant final entry. Current published rules supersede our earlier
optional-sponsor strategy and event calendar; this is not merely a conflict between drafts.
The earlier decisions remain in this append-only log as history. A replacement for the old
Autonomous Agent selection requires the builder's decision; Wildcard [Tinkerer] is the
clearest existing-project route, with a main challenge track conditional on eligibility.

**Recommendation, not scope approval:** start with shared event-instance access and one
verified query, then a bounded runtime policy/IaC adapter, alongside the previously proposed
minimal Meterless World Model. Keep OCI SDK inventory/telemetry and the four-agent critic
loop. Pricing is separately loaded from `data/pricing.json`, so a policy adapter does not
automatically virtualise prices. Preserve credential-free sample mode and honest degradation.

**Lab impact:** the existing 21 October teardown now precedes kickoff. Do not silently
extend lifetime or incur spend: verify the lab's own balance/expiry and obtain approval.
The recorded 23 October 06:27 SGT earliest continuous-span estimate now precedes the new
submission deadline, so a sufficient live 744-hour re-check is possible in principle,
not demonstrated. Actual coverage and verdict must be measured; preserved originals,
unchanged thresholds and offline evidence remain the safeguards.

**Documentation only:** current-event warning pointers and verified calendar/track facts
were added without authorising a product/track change. No sponsor service was queried,
software installed, credentials accessed, Cursor use verified, live OCI audit run,
cloud resource changed, commit created or remote pushed.

## 2026-10-17 — Supplied Zetaris docs assessed; access before deployment

**Recorded:** `notes/zetaris-docs-assessment-2026-10-17.md` inventories both distinct
attachments and all 19 supplied URLs, distinguishes official supplier guidance from
personal walkthroughs and event rules, and maps the proposal to the current source
contracts. GitHub `main` matched the attachment's pinned commit
`44668b267ad7ee0fae25ce7588e9620121d47cae` during retrieval. The live event rules were
retrieved again; the mandatory sponsor/development requirements and shifted build window
remain, despite the sponsor overview's TBC access text.

**Recommendation, not scope approval:** obtain shared participant-instance access first;
then approve a read-only check in a separate pinned supplier checkout. The supplied
prompt chooses JDBC onboarding; REST remains a lower-dependency runtime candidate, not
a substitute for the requested JDBC check or an already-working integration. Supplier
preflight combines protocol results and probes localhost; its REST helper's 600-second
timeout exceeds Driftwatch's total 540-second budget. Interpret checks separately and
require bounded/error-explicit runtime code rather than copying helpers unchanged.

**Why:** the docs establish sufficient interface detail for a narrow policy/IaC adapter,
but not our endpoint, account, driver, permissions, entitlement or service availability.
Videos are not a prerequisite unless a specific blocker remains. Local Docker and managed
AWS are separate deployment decisions, not evidence of free participant access. Keep OCI
SDK collection, fixture-only sample mode and the existing critic. Proposed implementation
and Meterless scope still need approval; track/NVIDIA gates remain unresolved.

**Documentation only:** no supplier script, authenticated query, install, signup, platform
image download, cloud/resource change, secret read, product-code change, commit or push.
No lab lifetime extension or employer-machine credential transfer is authorised.

## 2026-10-17 — Organiser setup guide changes access advice; bounded check approved

**New source:** the user supplied the organiser's Participant Setup Guide, header dated
16 October. `notes/participant-setup-guide-2026-10-17.md` records its source hash,
local-install instructions, actual default endpoints, Nemotron expectation and remaining
organiser placeholders. This corrects our earlier shared-instance-first advice: do not
assume a shared allocation will be issued or that it satisfies the new eligibility wording.
The local Meterless wording and published-rule/Nemotron difference remain explicit questions.

**Approved and executed:** user approved the preceding bounded read-only onboarding
request. A separate clean checkout at
`/Users/ant/projects/zetaris-getting-started-readonly-44668b2` is verified at
`44668b267ad7ee0fae25ce7588e9620121d47cae`. Local prerequisite inspection and the actual
supplier `preflight.py --jdbc` (Python 3.11, inherited sponsor settings excluded) returned
exit 1 / NOT READY, 10 failed checks. Docker absent; no discovered JDK; supplier config,
venv/package and JAR path missing. REST/JDBC were not authenticated. Independent local
TCP probe confirmed connection refused, errno 61, not a permission restriction.

**Stop gate:** no dependencies installed, account registered, platform downloaded/started,
object created, model changed or product code edited. No SQL result claimed. New approval
is needed for personal-Mac Docker/Zetaris installation, with user-controlled account and
credential steps; Java/Python JDBC dependencies are separately scoped. No AWS provisioning,
lab retention change, employer-machine install or retry of the protected AGENTS write.

## 2026-10-17 — Zetaris deployment in antworld approved; trial expiry corrected

**Approved:** the builder explicitly approved implementing Zetaris in the `antworld`
OCI tenancy instead of on the personal Mac. `notes/zetaris-oci-deployment.md` records
the scope and current access prerequisites. Infrastructure approval is no longer pending;
product integration/model changes and existing audited-lab retention are separate scopes.

**Evidence correction:** the supplied console screenshot shows subscription expiry on
26 November 2026, not the earlier approximate 27 October assumption, and low usage against
the allocation. The screenshot does not display tenancy identity; `antworld` is the
builder's identification and must be matched to the API target before provisioning.
Personal subscription identifiers and the raw billing screenshot are not copied here.

**Gate:** user obtains the vendor portal account, self-managed platform bundle, matching
configuration/registry access and applicable evaluation/hackathon entitlement. Official
documentation does not establish an indefinite licence from signup. The account and any
terms acceptance stay user-controlled. Priced VM configuration and teardown plan must
precede resource creation; no OCI resource, portal account or service was created here.

## 2026-10-18 — Read-only OCI readiness verified; deployment and product design prepared

**Authorised preparation:** the builder requested the OCI readiness/cost assessment and
integration design, then approved continuing the activities while away. This phase did
not launch resources or turn a not-yet-written design into an implemented integration.

**Verified:** `DRIFTWATCH2` resolves to the exact `antworld` tenancy in `ap-batam-1`.
E5.Flex, E6.Flex and Standard3.Flex are listed; compatible Ubuntu 24.04 images are returned.
The auditor cannot read limits (404); the separately verified `PROVISIONER2` identity was
used for read-only allowance checks, not writes. Ordinary E5 headroom is 83 OCPUs/1250 GB;
storage and VCN headroom also fit the proposal. Physical host capacity and launch success
were not tested. No permissions, lab workloads or teardown schedules were changed.

**Proposed configuration:** separate sponsor-services compartment/network, E5.Flex
2 OCPU/16 GB, 50 GB Balanced boot, SSH-only ingress and localhost tunnels. Oracle's current
official USD catalog was independently retrieved; Decimal calculations put E5/E6 compute
plus boot at about USD 2.28/day or USD 13.66–13.67 for 144 hours. These exclude unresolved
IPv4/network/vendor costs, taxes and account-specific credit treatment. Do not launch an
idle VM while legitimate registry access is blocked.

**Artifacts:** `notes/zetaris-oci-readiness-2026-10-18.md`,
`docs/zetaris-oci-runbook.md`, generated sanitized evidence/pricing JSON under
`notes/evidence/`, and `docs/superpowers/specs/2026-10-18-sponsor-integration-proposal.md`.
The bundle has six default services plus optional Caddy, not the older guide's service
set; UI port publication needs hardening. Shell syntax/integrity checks passed without
executing vendor scripts or reading bundled env files. Full existing suite: 116 passed.

**Product recommendation:** Zetaris policy then declarations, an actually consumed minimal
World Model, and observable Nemotron-generated explanations while deterministic audit
branches/figure guards stay authoritative. Unknown/incomplete declarations must not
become absence evidence; unknown predicates, partial batches, dropped degradation and
silent model fallback are explicit implementation gates. Model-chosen actions, H-MEM,
Markovian, UI and remote pricing are excluded. The written proposal awaits the normal
design review/implementation-plan stage; new code must be attributed to the build window.

**Not done:** no registry authentication/image pull, deployment, sponsor SQL/DDL, model
call, product implementation, secret publication, commit or push. Existing dirty work
was preserved. The protected AGENTS write was not retried; current notes/index pointers
provide discoverability through the already-linked project assessments.

## 2026-10-19 — Dedicated Zetaris platform deployed and read-only acceptance verified

**Authority:** prior explicit antworld deployment approval plus continued-activity approval;
the user supplied the issued registry command through a private local file. TextEdit saved
RTF; it was privately converted, both copies restricted to 0600, and the command parsed as
data rather than evaluated as shell. Actual manifest authentication for all three issued
images passed before VM creation. No credentials were displayed or committed.

**Actual infrastructure:** new sponsor-services compartment and dedicated VCN/subnet,
internet gateway/route, SSH-only builder /32 ingress; E5.Flex 2 OCPU/16 GB with 50 GB Balanced
boot and ephemeral public IP. Exact resources were read back. All product ports publish
only to loopback; the active strict-host-key SSH tunnel serves the personal Mac. No changes
to audited lab resources or its teardown, no extra disks, NAT/LB, DNS or reserved IP.

**Actual acceptance:** vendor preflight and all 9 verification checks pass; four services
healthy, both setup jobs exit 0. Engine reports 2.4.3.1. Seven general direct-REST SQL checks
and the same seven JDBC checks pass; catalogs enumerate 15 NY_TAXI and 24 TPCDS_DB tables,
and the limited customer SELECT returns five rows. JDBC used the supplied JAR and existing
Java 17 compiler module inside the driver container, not a new Mac JDK/Python install.
Local tunneled configuration and admin login return 200; public application probes do not connect.

**Repairs:** our extraction permissions initially denied UID 1001 entrypoint access, and
our initial random hex admin secret failed the engine's character-class password policy.
Both were corrected from observed logs without volume deletion or hand-edited metastore
records. The SELECT-only REST route rejects SHOW; the documented SQL-editor route handles
the full read-only sequence. These are recorded as real diagnostics, not hidden as a clean
first attempt. Source snapshots/image digests and sanitized evidence are retained.

**Operations:** private IDs/keys/credentials/logs live outside Git under
`~/.oci/zetaris-deployment/`; the generated admin secret is in `platform-admin.json` (0600).
Cost basis remains approximately USD 2.28/day gross compute/boot, exclusions unchanged.
The manifest checkpoint is 7 November 00:00 UTC with USD 46 gross compute/boot envelope;
automatic teardown has not been scheduled. Earlier cleanup is preferred when no longer needed.

**Disclosure:** infrastructure was prepared before the new-work window. No Driftwatch
reference objects, runtime adapter, World Model or Nemotron change; no model/track switch,
no product-code edits or commit/push. Admin-token technical acceptance is not least-privilege
runtime authentication or written licensing/OCI-event eligibility approval. Full results:
`notes/zetaris-oci-deployed-2026-10-19.md`; generated evidence:
`notes/evidence/2026-10-19-zetaris-deployment.json`.

## 2026-10-19 — Option B approved; policy-first implementation plan prepared

**User approval:** the builder approved the presented Option B scope (Zetaris policy then
declarations, consumed minimal World Model, Nemotron explanations with deterministic verdict
safeguards), with the explicit next stage being a written implementation plan, not immediate
product code. The overall destination is split into independently reviewed milestones.

**Plan:** `docs/superpowers/plans/2026-10-19-zetaris-policy-integration.md` details M1 in six
test-driven tasks: pure immutable snapshot contract/exporter; bounded secret-safe REST;
opt-in Source; truthful orchestrator/Scout recovery and lineage; reviewed synthetic publication
and least-privilege runtime access; actual source-effect/offline/packaging acceptance. M2–M5
are explicit follow-ons, not counted as implemented by policy provenance alone.

**Verified planning context:** actual Source/Scope/RunConfig and agent/test call paths were
read; the recorded direct REST response has headers/data/total/timeUsed, unlike SELECT-only
records pagination. The existing evaluator has no --help parser; the plan uses the actual
module invocation and explicit held-out output path. Scope/deadline/metadata imports are
defined to avoid circular imports through the source registry.

**Remaining gates:** user review of this plan and execution-method selection; recorded build
window; actual Cursor development surface; organiser eligibility interpretations; concrete
source-registration/access dry-run approval and a non-admin runtime key. Cursor.app was not
found in the two standard personal-Mac application locations; no install was attempted.
Read-only source publication and runtime-token capabilities are not inferred from the deployed
administrator smoke test. No object creation, permission change, product edit, commit or push
occurred during this planning stage.

## 2026-10-19 — Cursor installation approved and verified on the personal Mac

**Approval:** after the explicit live-rule explanation, the builder approved proceeding.
The action taken was editor setup, not pre-window product implementation or a paid plan.

**Verified:** official current download page's arm64 link, valid DMG checksum, deep/strict
code signature, Gatekeeper notarization before/after user-local installation, actual version
3.24.18 and running main process. Dedicated editor CLI symlink was created without replacing
an existing command. No Gatekeeper bypass, system app overwrite or shell-profile edit.

**Pending:** GUI capture failed because the computer-use backend is unavailable. User account
onboarding, privacy/context exclusions and actual development evidence remain unverified.
No repository/credential file was opened in Cursor, no secret entered, and no subscription
or account terms accepted. Installation does not itself satisfy actual development use.
See `notes/cursor-setup-2026-10-19.md`; M1 plan review/execution method/build-window gates remain.

## 2026-10-19 — Cursor sign-in reported; secret-context exclusions prepared

The builder reports successful sign-in. No account token or subscription state was read to
independently verify it. App capture remains unavailable. Created root `.cursorignore` using
the official Git-compatible syntax, retaining placeholder `.env.example` and sanitized
submission samples while excluding secret/state/working-log/cache paths. An isolated parser
check verified 17 exclusions and 7 permitted template/source/sample paths; actual Cursor
enforcement remains untested. No product implementation, repo opening or platform write.

Official documentation confirms ignore files do not block terminal/MCP tool access and that
Privacy Mode is a separate data-handling setting, not local-only AI. Privacy Mode requires
user confirmation through the app; no undocumented local setting/account database was edited.
Setup status and source references live in `notes/cursor-setup-2026-10-19.md`.

## 2026-10-21 — HackOS Resource Hub ingested; recorded facts left unchanged pending re-check

The live Resource Hub was read through the signed-in embedded preview pane: **63 entries
classified, 22 read in full as rendered text, 2 PDFs preview-only, 8 not read** (videos,
dataset catalogues, one deck, one conduct document). No dashboard checklist item, read flag
or save flag was toggled — the hub still shows 0/6 reviewed.

**Why a digest and not a rewrite:** the hub disagrees with `AGENTS.md` on two dates and adds
five facts we had recorded as unknown. Under this project's rule, a newer-looking source does
not silently overwrite a recorded one. So the hub's version was written to
`notes/hackathon-resources-2026-10-21.md` with an explicit re-verification list, and the
recorded facts were left as they were.

**Disagreements recorded:** judging opens 28 Oct (repo says 27 Oct 00:00); registration closes
23:45 UTC in all hub documents but 11:59 PM UTC in the dashboard widget (repo says 23:59);
prize breakdown now published; Space XAI named as the sponsor carrying Cursor; repository must
be public; team locks at the first submission.

**NVIDIA still unresolved.** Rules §8.1, the Welcome Guide, the Overview and both FAQs say
"integrate wherever it contributes"; the 16 October Participant Setup Guide says the product
must run on Nemotron; the Mentor Playbook says partner tech is "not mandatory" — the last
directly contradicts §8.1 for Zetaris and Meterless and is treated as stale. The question
stays open for the 21 October onboarding Q&A rather than being resolved here.

**Stale documents noted, not used:** the Mentor Playbook's track taxonomy (Fragmented /
Autonomous Intelligence / Persistent Memory Agents / Real-World Industry Agents) predates the
current three-track-plus-Wildcard structure, and the Office Hours Guide quotes a 2–3 minute
demo against the rules' 1–4 minutes.

Raw captures live outside the repo at
`~/projects/open-agent-hackathon-reference/resources-2026-10-21/`. The matching `AGENTS.md`
edit is approval-gated and was not attempted.

---

## 2026-10-22 — Resource-hub delta ingested; event-page rules captured via public API

**Decision:** ingest only the delta against the 21 October digest rather than
re-reading the hub; record the anonymous `hackathon-server.genai.works` event-page
API as a source class for the published rules.

**Why:** the hub grew by exactly four entries, all 21-Oct workshop recordings
(Onboarding call included). Documents were unchanged by title/id/folder, and
rendered-text archives already exist — a full re-read would burn window hours for
no new facts while the API gives the binding rules record (`updated_at` 21 Oct
07:16 UTC) directly, without the session wall.

**Outcome of the comparison:** rules §§4–7 confirm the 14 Oct verification
unchanged (window, sponsor requirements, deliverables, scoring). Structured
fields disagree with hub documents on judging-start (27 vs 28 Oct) and
registration-close (23:59 vs 23:45) — both immaterial now; prize figures differ
($13k cash + $7k in-kind) and a new **NVIDIA DGX Spark in-kind prize for best use
of Nemotron ($4,699)** appears in the event record only. The four videos are
player-only in the hub and were not watched or transcribed — the onboarding-call
content (possible challenge/prize announcements) is the main remaining gap.

Digest: [`notes/hackathon-resources-2026-10-22.md`](../notes/hackathon-resources-2026-10-22.md).
No dashboard flags toggled, no recorded fact overwritten, no scope change; the
`AGENTS.md` deltas remain the builder's call (approval-gated file).

---

## 2026-10-22 — Track selection and execution mode for the build window (builder-approved)

**Track (working selection):** **Wildcard [Tinkerer]: Bring Your Own Project.** The builder
chose it explicitly on 22 Oct; it maps the honest story — declared September baseline plus
new in-window work (Zetaris policy adapter, Meterless World Model consumption, Nemotron
treatment) scored on the new work. Per the live rules and the kickoff notification, the
track remains changeable until 27 Oct 23:45 UTC, so this supersedes only the
"selection pending" state in `AGENTS.md`, not any other recorded fact.

**Execution mode:** install the official `cursor-agent` CLI and drive the approved M1 plan
tasks through Cursor's own agent, so the mandatory Cursor development is native and
attributable rather than relabelled work from another assistant. Cursor GUI and Hermes
sessions stay as support evidence, not the primary development claim.

**Onboarding-call gap:** explicitly deferred by the builder. The event-page rules record,
hub documents and the HackOS notifications (registration 22 Oct **23:59 UTC**; team
"Antnynomous" formed; kickoff notice names a **Help Bright Data** channel — a sponsor
presence absent from the rules sponsor list, noted for later confirmation) cover
current decisions. Track statements from the call remain unverified material; revisit if
the Wildcard submission mapping needs the "additional challenges with new prizes".

---

## 2026-10-22 (evening) — Cursor credits denied; execution re-based to Hermes-primary with preserved Cursor evidence

**Trigger (verified in HackOS Help Cursor, Bright Gasu, 22 Oct 08:53 UTC, @everyone):**
"Cursor won't be providing tokens or credits for this event… participants can still use
the free version… We're currently updating the Participant Setup Guide."

**Reconciliation from the onboarding-call transcript (YouTube 48GKYJfwoB8, archived 22 Oct):**
the only Cursor money mentioned at onboarding is "$2,000 of Cursor credits… additional
PRIZE pool" — they were always prizes, never a dev grant. This explains the perpetual
[TBC] in the sponsor folder and the empty task-board "Get sponsor credits" placeholders.

**Facts still standing:** event-page rules §5 unchanged as of this check (Cursor mandatory
until re-published); free-tier CLI quota ≈5 agent requests; Tasks 1–2 already produced
genuine, transcripted Cursor-agent development evidence.

**Decision (builder informed):** build continues Hermes-primary immediately (Task 3 was
already completed this way; Tasks 4–6 proceed the same), while deliberately using the
free Cursor tier/editor for bounded real tasks at quota resets, so the Cursor claim stays
evidenced, not just asserted. README/metadata will state the split honestly; if the
updated Setup Guide publishes an own-agent or relaxed-Cursor clause, the watcher flags it
and this disclosure simplifies accordingly. Track-choice and sponsor-integration scope
unchanged.

## 2026-10-22 — Zetaris publication executed as v2 (quote-safe CSV), builder-approved

**Decision:** after live registration exposed the engine's embedded-quote truncation in
`FORMAT CSV` cells (v1 incident, full evidence in `notes/zetaris-engine-defects-2026-10-22.md`),
re-publish as immutable `*_v2` snapshots with percent-encoded `when_json` cells and decode them
client-side only when raw JSON parsing fails.
**Why:** the engine parser silently truncates RFC-4180 escaped quotes; digests are computed over
*parsed* records, so the encoding preserves content identity (58729b…/833ee5… unchanged) while
making the cells safe for the naive parser. Overwriting v1 staged files would have broken our own
immutability rule; the scalar-column redesign would have torn up Task 1/3 contracts inside the
window. v1 tables were revoked and dropped so the namespace contains only what is consumed.
**Guardrail validation:** the defect surfaced *because* every fetch re-validates digest+scope —
the orchestrator degraded to fixtures rather than consuming corrupted rules, twice. Acceptance
required the Zetaris-backed dual run (sponsor_acceptance=true) and proved the causal claim:
unpublishing R-1 removes exactly the `eee5/cost_waste` finding.
**Attribution:** Cursor quota-blocked before Tasks 5–6; this work is Hermes-executed with the
build log recording the split honestly.

## 2026-10-26 — Meterless split topology approved; written design prepared, deployment gated

**User decision:** follow the recommendation to keep Driftwatch, a consumed minimal Meterless
World Model and the existing Zetaris data layer on personal OCI, with Nightshift inference on
the personal Mac through a loopback-bound encrypted SSH reverse tunnel. No new cloud resources,
paid licences, GPU instances or changes to audited A1 workloads are included.

**Artifact:** `docs/superpowers/specs/2026-10-26-meterless-split-deployment-design.md`.
This is the written-spec review stage, not product implementation or installation approval.
It specifies SQLite-backed immutable observations, duplicate-safe transactional ingestion,
Scout/Skeptic context consumption, real Nightshift provider acceptance, visible rules fallback,
hermetic sample operation, scenario isolation and refreshed submission evidence. It concretises
the earlier unbuilt Meterless/model follow-ons; remote IaC declarations and NVIDIA claims are
outside this narrowed scope. The existing M1 policy adapter is preserved.

**Discovery:** the signed current-region inventory confirms the four A1 lab hosts and the
E5.Flex Zetaris host RUNNING, without GPUs. The official Mac M5+ download exists and the Mac
meets its stated chip-generation requirement, but application installation/activation and
model calls have not been verified. The documented DGX Linux edition is not evidence that
the small CPU-only OCI hosts can run Nightshift.

**Deployment blocker:** SSH to `zetaris-01` timed out; current VNIC discovery confirms the
configured public address, and a separate TCP/22 probe also failed. Remote RAM/disk/Python
readiness is therefore unverified. Do not change ingress, routes, host keys, Zetaris resources
or host retention to make this check pass without the appropriate approval. The earlier
7 November 00:00 UTC sponsor-host checkpoint is unchanged; billing was not revalidated here.

**Not done:** no product-code edits, app/model installation, remote writes, provisioning,
secret copying, tunnel creation, paid action, push or submission. The design and this decision
entry are committed locally for written review; existing unrelated work remains untouched.
