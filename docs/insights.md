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
| Full test suite | 84 tests, under 1 s on a fresh clone |
| `POST /run`, sample mode | HTTP 200, 20 ms for 6 resources / 5 findings |
| End-to-end CLI audit | ~1 s per scenario including all four agents |
| Evaluation (3 scenarios) | precision 1.0, recall 1.0, verdict accuracy 1.0, deterministic |
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

### The cap that could never fire

> **What we observed** → `MAX_RECHECKS_PER_FINDING = 2` was implemented, tested and unreachable:
> the counter was keyed by candidate id, and every round mints a new id, so the count reset forever.
> → **why it happens** → the test that proved the cap worked constructed the state a cap needs —
> three re-checks of the *same* candidate id — which the loop cannot produce, because an id belongs
> to one round. The test encoded the implementation's assumption instead of the run's reality. →
> **what we did about it** → counts are keyed by resource and finding class, which is stable across
> rounds, and the test drives three real rounds. **When a cap is keyed by something the loop
> recreates every cycle, the cap is decoration; test it by running the loop, not by building state.**
