# Insights

The organisers award bonus points for **documenting insights**. This file is the home for
them. Write as you go — reconstructing this at the end produces something thin, and the
whole point of the bonus is that the substance is real.

## What belongs here

Non-obvious things learned while building, especially:

- What the agent framework got wrong, and what you had to work around
- Where the sponsor technology surprised you (good or bad)
- Design choices that failed, and what replaced them
- Measurements: latency, cost, token usage, accuracy before/after a change

## Format

Short and specific beats long and vague. Each entry:

> **What we observed** → **why it happens** → **what we did about it**

## Entries

### The traceability guard caught the generator, not the model

> **What we observed** → The first end-to-end loop run crashed with `UntraceableFigureError`,
> raised by the Writer against a claim the rules generator had produced: the claim said "0.77%"
> while the ledger held 0.767. → **why it happens** → the claim templates formatted numbers to two
> decimals for readability, which silently changes the assertion from "the evidence says this" to
> "something like this". A second defect surfaced in the same pass: rule R-1's template hardcoded
> "50 GB" instead of quoting the volume's actual size. → **what we did about it** → templates now
> interpolate computed values verbatim, and `size_gb` is threaded from the Scout's context into
> the template. The guard earned its place on its first real run, and it caught *our own* code —
> which is the strongest argument that the same guard will catch a model's arithmetic later.

### A published field that does nothing is worse than no field

> **What we observed** → Building the third scenario required an idle instance to stay
> *unreported* because its declaration says "idle by design". No code path could produce that
> outcome: the Scout published a `falsifier` for every candidate ("a declared purpose would
> disprove this") and nothing could act on it. → **why it happens** → the falsifier was written as
> documentation for a human reader, so it was never wired to the decision it describes. →
> **what we did about it** → the Skeptic gained a declared-purpose check that withdraws the
> finding before any threshold logic runs. The scenario that exposed it is now the regression test.

### Applying a strict regex to free text finds figures that are not figures

> **What we observed** → The Writer rejected a claim about `vol-orphan-100g` because "100" was not
> a number any evidence item supported. It was not an asserted quantity at all — it was part of
> the resource's *name*; the supported figure was "100.0 GB", a few words later. → **why it
> happens** → the guard scans prose, and prose contains identifiers, versions, ports and region
> names that look like measurements. → **what we did about it** → the resource's own display name
> is masked before scanning, which keeps "168h" checked while ignoring digits inside identifiers.

### The fresh-clone check found a packaging bug that no test could

> **What we observed** → 63 tests green on the development venv (Python 3.11.16), then **13
> collection errors** on a clean clone. Cause: this machine's `python3` is 3.9.6, and because
> pydantic evaluates annotations at runtime, `str | None` in the domain models raised thirteen
> unrelated `TypeError`s. → **why it happens** → `pyproject.toml`-less projects carry no
> interpreter metadata, so `pip install -r requirements.txt` happily installs into an interpreter
> the code cannot run on. → **what we did about it** → `app/__init__.py` refuses to import below
> 3.11 and prints the one command that fixes it, so a judge sees one actionable line instead of a
> wall of errors. **The clean-clone run is a test, and it caught something the suite never would.**

### Measured, not assumed

| What | Measurement |
|---|---|
| Full test suite | 109 tests, under 1 s on a fresh clone |
| `POST /run`, sample mode | HTTP 200, 20 ms for 6 resources / 5 findings |
| End-to-end CLI audit | ~1 s per scenario including all four agents |
| Evaluation (3 scenarios) | precision 1.0, recall 1.0, verdict accuracy 1.0, deterministic |
| Held-out scoring (10 generated tenancies) | precision 1.0, recall 1.0, verdict accuracy 1.0, deterministic, 0 failing |
| Model calls in sample mode | 0 — enforced by a test that replaces `socket.socket` |

The 20 ms figure matters for the design, not for speed: it means a judge can run all three
scenarios and the evaluator in under five seconds, so the demo is about the agent's reasoning
rather than a progress bar.

### A guard you wrote can still agree with itself

> **What we observed** → the Writer refuses to print a figure that no evidence supports, and it was
> passing its own tests. The review broke it anyway: with telemetry unavailable the Scout fell back
> to `mean 0.0 / coverage 1.0 / sufficient True`, and because a candidate's own `stats` were part of
> the Writer's allow-list, the invented number **vouched for itself** and appeared in an accepted
> finding as "web-01 averages 0.0% CPU". → **why it happens** → a guard proves consistency, not
> truth: it checks that a claim agrees with something, and if the something is the claimant, the
> check is a tautology. → **what we did about it** → missing telemetry is now a single named
> `NO_TELEMETRY_STATS` shape with `sufficient: False`, no CPU rule may fire without a series, and a
> candidate's own numbers are no longer evidence for its own claim. **A fallback that produces
> numbers is a lie with good manners; a fallback that produces `None` is a degradation.**

### Three scenarios you wrote test your assumptions; a generator tests the space

> **What we observed** → the agent passed 88 tests, three hand-written scenarios at precision 1.0 /
> recall 1.0 / verdict accuracy 1.0, and a full-length adversarial review of the whole branch. Then
> ten tenancies generated from integer seeds found **two** defects in the first run: a re-check that
> changed nothing was reported as a revision (seed 6), and the committed traces had been filed under
> the wrong scenario since the day they were generated. → **why it happens** → every hand-written
> scenario was written by the person who wrote the agent, so it encodes the shapes that person
> thought of. A generator samples the space instead, including the combinations that are obvious in
> hindsight and invisible while writing: an idle, bursty, *undeclared* instance is the intersection
> of three independent choices, and none of the curated scenarios happened to be in it. →
> **what we did about it** → ground truth is generated from the same random choices that shape each
> resource, so it cannot drift from the fixture; ten seeds score 1.0 across the board; seed 6 is
> pinned in a test with a comment saying exactly which shape it carries. **Hold-out a slice of the
> input space, or the tests only measure how well you anticipated yourself.**

### The evidence was filed by the wrong key

> **What we observed** → `scripts/run_examples.sh` chose each run's trace, state and report as "the
> newest file in `logs/`". Two runs finish in the same second, `-nt` is false for equal timestamps,
> so the loop kept the earlier candidate: the committed `trace-example_2.jsonl` carried example_1's
> run — 19 lines describing a tenancy with six resources and four findings, filed under a scenario
> that has five and none. → **why it happens** → mtime is a *proxy* for identity, and proxies fail
> exactly when the thing they approximate moves fast. The run had already recorded which files it
> wrote (`trace_path`, `report_markdown_path`); the script guessed anyway. → **what we did about it**
> → read the paths out of the report the run just wrote, and add a test that every committed trace
> carries its own report's run id and narrative. **Never infer identity from a timestamp when the
> artifact names itself — and make the evidence you ship subject to a test, because a mismatched log
> is worse than no log.**

### The plan's SDK calls were remembered, not checked

> **What we observed** → Task 15's draft adapter code, written a day earlier from memory, put
> `list_volume_attachments` on `BlockstorageClient` (it is on `ComputeClient`), enumerated
> instances only while the rule set also judges volumes and reserved IPs, and requested a 31-day
> re-check window at 5-minute resolution — a combination Monitoring silently truncates, because
> 5-minute data is retained for 30 days. → **why it happens** → a plan is written without the
> library open; prose and code drafts age differently, and API shapes are exactly the detail
> memory smooths over. → **what we did about it** → before writing any adapter, introspect the
> pinned SDK offline (`inspect.signature`, `attribute_map`, `hasattr`) and search the provider's
> retention docs; three of the four deviations were caught before a line of implementation existed.
> **When a plan quotes an API, verify the quote against the pinned version before building it —
> the plan is a hypothesis, the library is the fact.**

### The cap that could never fire

> **What we observed** → `MAX_RECHECKS_PER_FINDING = 2` was implemented, tested and unreachable:
> the counter was keyed by candidate id, and every round mints a new id, so the count reset forever.
> → **why it happens** → the test that proved the cap worked constructed the state a cap needs —
> three re-checks of the *same* candidate id — which the loop cannot produce, because an id belongs
> to one round. The test encoded the implementation's assumption instead of the run's reality. →
> **what we did about it** → counts are keyed by resource and finding class, which is stable across
> rounds, and the test drives three real rounds. **When a cap is keyed by something the loop
> recreates every cycle, the cap is decoration; test it by running the loop, not by building state.**
