# Meterless World Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Scout and Skeptic consume a persistent, sourced, duplicate-safe World Model without changing the offline audit's verdicts or arithmetic.

**Architecture:** Three services implement immutable SQLite storage, transactional source ingestion and deterministic context selection. Existing agents retain their responsibilities and the evidence ledger retains its report-level IDs. Current-run snapshots, not a global latest view, define what each agent can read.

**Tech Stack:** Python 3.11+, standard-library sqlite3/hashlib/json, existing Pydantic models and pytest. No new production dependencies.

**Spec:** `docs/superpowers/specs/2026-10-26-meterless-split-deployment-design.md`, approved by the user on 26 October. Read it in full before execution.

## Global Constraints

- Python 3.11+; use `.venv/bin/python` from the repository root, never system Python 3.9.
- Preserve the sample run as CPU-only, offline, deterministic and dependency-light.
- No new OCI instances, GPUs, disks, snapshots, paid subscriptions, cloud-model purchases or hardware resizing.
- No employer resources or employer data. No credentials on the Windows work machine.
- Preserve 3 rounds, 25 resources, 2 rechecks, 300-second soft and 540-second hard caps; request caps may be lowered, not raised.
- SQLite busy wait: 250 ms; 10,000 observations per run; 2 MiB per observation payload; 128 MiB database page budget; 256 context records per resource.
- Do not lower telemetry sufficiency thresholds or change resource declarations to manufacture a revision.
- No installation, remote write, push, public sharing or submission is part of this code milestone.
- Only modify this milestone's named files. Preserve pre-existing dirty README/media/notes/metadata work; never `git add -A`.
- Speculative snippets below define new code to implement during execution, not code that exists or tests that have already passed.

## Review Focus

1. Two namespaces with the same resource/display name must not share facts; test this in Task 2.
2. A current empty/failed policy snapshot must not resurrect a prior snapshot's rule; test this in Tasks 2–3.
3. Fixture telemetry for a live resource must keep its fixture backend and reject an ambiguous masked join; test this in Task 4.
4. Caller mutation after ingestion or context return must not mutate stored/pinned facts; test this in Tasks 1–3.
5. Store creation/lock/disk-limit failure must produce a partial report, close all handles and never report direct-read success; test this in Tasks 2 and 4.

## File structure and dependencies

Create `app/world_model/` with: `contracts.py` (immutable observation/snapshot/context DTOs and classified errors),
`identity.py` (canonical bytes and hashes), `store.py` (SQLite only), `ingest.py` (existing source/domain
model adaptation), `context.py` (read selection), `runtime.py` (per-audit service lifecycle and manifest),
and `__init__.py` (exports only). Keep each boundary focused; no SQL inside agents.

Create `tests/test_world_identity.py`, `test_world_store.py`, `test_world_ingest.py`,
`test_world_context.py`, `test_world_integration.py` and `tests/world_helpers.py`.
Modify `app/agents/base.py`, `app/pipeline.py`, `app/loop.py`, `app/agents/scout.py`,
`app/agents/skeptic.py` and, only for explicit lineage, `app/models.py`/`app/evidence.py`.

Runtime/provider changes belong to the companion Nightshift plan, not these tasks.

## Baseline and common RED–GREEN protocol

Before Task 1, use the selected execution workflow's isolated worktree procedure. The source tree is
dirty; do not stash, reset or silently omit the user's changes. Record `git status --short`, base SHA
and which pre-existing changes were intentionally brought into the execution branch. Never copy `.env`
or private credentials into a worktree as part of that operation.

Run a baseline before modifying production code:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m evals.run_eval
.venv/bin/python scripts/make_scenario.py --score 10 --out "$TMPDIR/driftwatch-world-baseline"
```

Capture stdout/stderr under gitignored `logs/`, preserving each command's own exit status. A baseline
failure is a recorded blocker, not a reason to weaken existing tests.

For each tracer bullet below: write only its named failing test, run that test and record its expected
failure, implement that one behaviour, rerun it, then refactor while green. An initial missing module
is a valid first RED; subsequent bullets must fail on their asserted behaviour, not import typos.
Do not write a pile of speculative tests before building the first vertical slice. End each task with
the task module(s), the full suite and a path-scoped commit.

## Shared interfaces

Task 1 owns these frozen DTOs; later tasks must use the same names and signatures:

```python
@dataclass(frozen=True)
class Observation:
    entity_type: str
    external_key: str
    source: str
    backend: str
    payload_json: str  # canonical JSON string; payload property returns a fresh decoded value
    source_version: str | None = None
    lookback_hours: int | None = None
    resolution_minutes: int | None = None
    measured_at: str | None = None

    @classmethod
    def from_payload(cls, *, entity_type: str, external_key: str, source: str,
                     backend: str, payload: dict, source_version: str | None = None,
                     lookback_hours: int | None = None,
                     resolution_minutes: int | None = None,
                     measured_at: str | None = None) -> "Observation": ...
    @property
    def payload(self) -> dict: ...

@dataclass(frozen=True)
class SnapshotRef:
    snapshot_id: str
    source: str
    observation_ids: tuple[str, ...]
    complete: bool
    degraded: bool

@dataclass(frozen=True)
class ContextSelection:
    resource_id: str
    inventory_snapshot: str
    iac_snapshot: str
    policy_snapshot: str
    telemetry_snapshot: str | None
    observation_ids: tuple[str, ...]
    lookback_hours: int
    resolution_minutes: int

@dataclass(frozen=True)
class ResourceContext:
    selection: ContextSelection
    resource: Resource
    declaration: IaCDeclaration | None
    iac_match_rule: str | None
    rules: tuple[PolicyRule, ...]
    series: MetricSeries | None
    complete: bool
    reasons: tuple[str, ...]

class WorldError(Exception):
    category: str  # configuration/schema/provenance/storage/limit/context
    def __init__(self, category: str) -> None: ...
```

Use copies/frozen values at boundaries. Returning a frozen wrapper around a mutable shared dictionary
is not immutability. The complete Task 1 implementation provides all imports, constructors, validation
and methods omitted from these interface-only declarations.

### Task 1: Content identity and immutable validated observations

**Files:** Create `app/world_model/{__init__,contracts,identity}.py`, `tests/test_world_identity.py`.

**Interfaces:** Consumes existing domain types from `app.models`. Produces the shared DTOs above plus
`canonical_json(value: object) -> str`, `entity_id(namespace: str, observation: Observation) -> str`,
`observation_id(namespace: str, observation: Observation) -> str` and classified `WorldError`.

- [ ] **Step 1 — RED: equivalent canonical payloads, copied payload and meaningful identity changes.**

```python
from app.world_model.contracts import Observation
from app.world_model.identity import observation_id

def test_identity_ignores_dict_order_but_preserves_window_and_namespace():
    a = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload={"b": 2, "a": 1})
    b = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload={"a": 1, "b": 2})
    assert observation_id("scenario:a", a) == observation_id("scenario:a", b)
    assert observation_id("scenario:b", a) != observation_id("scenario:a", a)

def test_caller_mutation_cannot_rewrite_observation():
    payload = {"tags": {"schedule": "monthly"}}
    obs = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload=payload)
    payload["tags"]["schedule"] = "nightly"
    exposed = obs.payload
    exposed["tags"]["schedule"] = "weekly"
    assert obs.payload["tags"]["schedule"] == "monthly"
```

Run `.venv/bin/python -m pytest tests/test_world_identity.py -q` and establish RED. Then implement the
minimum slice. Canonicalisation uses sorted JSON keys, compact separators, `allow_nan=False`, finite
numbers and UTC-normalised aware datetimes. Reject naive datetimes and missing/unknown source/backend,
not provenance-free defaults. Preserve identifiers exactly; do not lowercase external IDs or silently
repair malformed input. Include schema version in both hashes, exclude fetch time/run IDs and include
source version plus measurement window. Build the hash preimage explicitly, not `repr(object)`.

- [ ] **Step 2 — repeat RED→GREEN for 168h vs 744h, fixture vs live, changed snapshot/version, NaN,
Unicode payloads, naive datetime and unknown provenance.** Use `dataclasses.replace` to vary one field;
assert changed identities where required and `WorldError` with the exact category for rejected data.
- [ ] **Step 3 — run targeted/full suites and commit only these files.**

```bash
.venv/bin/python -m pytest tests/test_world_identity.py -q
.venv/bin/python -m pytest -q
git add app/world_model/__init__.py app/world_model/contracts.py app/world_model/identity.py tests/test_world_identity.py
git commit -m "feat(world): immutable sourced observations and stable content identity"
```

### Task 2: Transactional store, source snapshots and restart recovery

**Files:** Create `app/world_model/store.py`, `tests/test_world_store.py`.

**Interfaces:** Consumes Task 1 DTOs/hash functions. Produces:

```python
class WorldStoreService:
    def __init__(self, path: Path, *, max_observations: int = 10_000,
                 max_payload_bytes: int = 2*1024*1024,
                 max_database_bytes: int = 128*1024*1024) -> None: ...
    def put_batch(self, *, run_id: str, namespace: str, source: str,
                  observations: Sequence[Observation], complete: bool,
                  degraded: bool = False) -> SnapshotRef: ...
    def snapshot(self, *, run_id: str, namespace: str,
                 snapshot_id: str) -> SnapshotRef: ...
    def read(self, *, run_id: str, namespace: str,
             snapshot_id: str) -> tuple[Observation, ...]: ...
    def counts(self, *, run_id: str, namespace: str) -> dict[str, int]: ...
    def rebuild_projections(self) -> None: ...
    def close(self) -> None: ...
```

- [ ] **Step 1 — RED: append, dedup and reopening the actual SQLite database.**

```python
from app.world_model.store import WorldStoreService
from app.world_model.contracts import Observation

def test_retry_and_reopen_do_not_duplicate_observations(tmp_path):
    path = tmp_path / "world.sqlite3"
    obs = Observation.from_payload(entity_type="resource", external_key="r1",
        source="inventory", backend="fixture", payload={"name": "one"})
    store = WorldStoreService(path)
    first = store.put_batch(run_id="run-a", namespace="n", source="inventory",
        observations=[obs], complete=True)
    before = store.counts(run_id="run-a", namespace="n")
    store.close()
    store = WorldStoreService(path)
    second = store.put_batch(run_id="run-a", namespace="n", source="inventory",
        observations=[obs], complete=True)
    assert first == second
    assert store.counts(run_id="run-a", namespace="n") == before
    assert store.read(run_id="run-a", namespace="n", snapshot_id=first.snapshot_id)[0].payload == {"name": "one"}
    store.close()
```

Run the exact test; after RED create versioned tables for entities, observations, snapshots, snapshot
membership, run membership and sourced relationships. Unique content IDs prevent duplicates; every
read joins run and namespace membership. Empty complete snapshots are real snapshots with zero members.
Incomplete snapshots remain explicit and cannot resolve an old snapshot. Use SQLite transactions,
`PRAGMA busy_timeout=250`, a page-count-derived storage limit, private directory/file permissions and
parameterised SQL. Open existing stores without truncation. Reject unknown versions before writes.

- [ ] **Step 2 — transactional failure RED→GREEN.** Use a real SQLite trigger in a test to `RAISE(ABORT)`
on the second observation, then assert the first observation and memberships were rolled back. Drop
the test trigger, reopen and retry; compare semantic state with a clean store. Store exceptions are
classified without echoing payloads or filesystem secrets.
- [ ] **Step 3 — isolation and stale-policy RED→GREEN.** Put the same resource key in namespaces A/B,
assert a cross-namespace/run read raises `WorldError(category="context")`. In run B ingest a complete
empty policy snapshot and assert its `read` result is empty, not run A's rules. Repeat with an incomplete
snapshot and assert its `complete` flag is false. Test after closing/reopening.
- [ ] **Step 4 — bounded failures RED→GREEN.** Hold a competing `BEGIN EXCLUSIVE` using a second
SQLite connection, verify a classified bounded failure, then release it and verify recovery. Inject
small constructor budgets to reach row, payload and page limits cheaply. Enforce budgets in the real
write path, not a helper unreachable from ingestion. Verify failed batches are rolled back. Test
corrupt database and a different `PRAGMA user_version` without destroying either file.
- [ ] **Step 5 — projection rebuild and full verification.** Rebuild projections from canonical rows,
compare semantic snapshots and relationship links before/after, and ensure payload mutation cannot
change a subsequent read. Run both new test modules and the full suite; commit the store/tests only.

### Task 3: Source ingestion and budgeted pinned context

**Files:** Create `app/world_model/ingest.py`, `context.py`, `tests/world_helpers.py`,
`tests/test_world_ingest.py`, `tests/test_world_context.py`.

**Interfaces:** Consumes store/DTOs plus `Resource`, `IaCDeclaration`, `PolicyRule`, `MetricSeries`,
`SourceResult` and existing `match_iac`. Produces:

```python
class IngestPipelineService:
    def __init__(self, store: WorldStoreService, *, run_id: str,
                 namespace: str) -> None: ...
    def ingest(self, source: str, result: SourceResult, *,
               complete: bool = True) -> SnapshotRef: ...
    def ingest_series(self, resource_id: str, series: MetricSeries, *, backend: str,
                      degraded: bool, source_version: str | None = None) -> SnapshotRef: ...

class ContextBuilderService:
    def __init__(self, store: WorldStoreService, *, run_id: str,
                 namespace: str, max_records: int = 256) -> None: ...
    def build(self, *, resource_id: str, inventory_snapshot: str, iac_snapshot: str,
              policy_snapshot: str, telemetry_snapshot: str | None,
              lookback_hours: int, resolution_minutes: int) -> ResourceContext: ...
    def replay(self, selection: ContextSelection) -> ResourceContext: ...
```

- [ ] **Step 1 — define an actual fixture source helper and the first failing ingest/context test.**

```python
# tests/world_helpers.py
from pathlib import Path
from app.config import RunConfig
from app.sources import get_source
from app.sources.base import Scope

def fetch_fixture(source, scenario="example_1", lookback_hours=168):
    cfg = RunConfig(sample_mode=True)
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=lookback_hours, resolution_minutes=5)
    return get_source(source, cfg, scenario_dir=Path("data/scenarios") / scenario).fetch(scope)
```

The first test uses `fetch_fixture("inventory")`, ingests it twice and verifies store counts and
payloads are unchanged. Its next vertical slice ingests IaC and policy, chooses an existing resource
from inventory, builds context and compares resource, matched declaration and rules against the
existing domain models/`match_iac` using that fixture data. No copied prewritten report is input.

- [ ] **Step 2 — implement normalise/resolve/validate/append/project using typed existing models.**
Stage validation of the entire batch before the store transaction. Reject unknown source names and
invalid records; do not accept an arbitrary dictionary as a policy or resource. Preserve Zetaris
provenance (`snapshot_id`, digest, provider) and actual backend. A complete fixture fallback may be
usable while `degraded=True`; do not conflate degradation with incomplete data. Record a source
snapshot even when its validated record set is empty. Model each resource as an entity and source
snapshot/window as a context; persist membership relationships rather than merely unused IDs.

- [ ] **Step 3 — RED→GREEN: ingest both telemetry windows, build each exact selection and replay.**

```python
def test_builder_keeps_short_and_long_windows(seeded_world):
    # seeded_world is a fixture defined in this test module using fetch_fixture and the interfaces above.
    store, ingest, builder, refs, resource_id, short, long = seeded_world
    short_ref = ingest.ingest_series(resource_id, short, backend="fixture", degraded=False)
    long_ref = ingest.ingest_series(resource_id, long, backend="fixture", degraded=False)
    before = builder.build(resource_id=resource_id, **refs,
        telemetry_snapshot=short_ref.snapshot_id, lookback_hours=168, resolution_minutes=5)
    after = builder.build(resource_id=resource_id, **refs,
        telemetry_snapshot=long_ref.snapshot_id, lookback_hours=744, resolution_minutes=5)
    assert before.series.lookback_hours == 168
    assert after.series.lookback_hours == 744
    assert before.selection.observation_ids != after.selection.observation_ids
    assert builder.replay(before.selection).series.model_dump() == before.series.model_dump()
```

Define `seeded_world` in this module with the following fixture, then implement only the behaviour
its first failing assertion requires:

```python
import pytest
from app.models import MetricSeries
from app.world_model.store import WorldStoreService
from app.world_model.ingest import IngestPipelineService
from app.world_model.context import ContextBuilderService
from tests.world_helpers import fetch_fixture

@pytest.fixture
def seeded_world(tmp_path):
    store = WorldStoreService(tmp_path / "world.sqlite3")
    ingest = IngestPipelineService(store, run_id="run-test", namespace="fixture:test")
    refs = {}
    inventory = fetch_fixture("inventory")
    for name, result in (("inventory", inventory), ("iac", fetch_fixture("iac")),
                         ("policy", fetch_fixture("policy"))):
        refs[name + "_snapshot"] = ingest.ingest(name, result).snapshot_id
    resource = next(r for r in inventory.records if r.get("tags", {}).get("schedule") == "month-end")
    rid = resource["resource_id"]
    short = MetricSeries(**next(r for r in fetch_fixture("telemetry", lookback_hours=168).records
                                if r["resource_id"] == rid))
    long = MetricSeries(**next(r for r in fetch_fixture("telemetry", lookback_hours=744).records
                               if r["resource_id"] == rid))
    builder = ContextBuilderService(store, run_id="run-test", namespace="fixture:test")
    try:
        yield store, ingest, builder, refs, rid, short, long
    finally:
        store.close()
```

- [ ] **Step 4 — RED→GREEN: provenance, absence, mutation and record budget.** A missing/incomplete
IaC snapshot cannot establish declaration absence. An incomplete policy snapshot cannot supply a
subset of apparently authoritative rules. A changed later snapshot cannot alter a pinned selection.
Mutating returned `Resource.tags` or `MetricSeries.points` cannot change replayed context. Build with
`max_records=1` and sufficient input to exceed it; return an explicit incomplete context/reasons,
not truncated `complete=True`. Cross-resource or wrong-window telemetry is rejected/incomplete.
- [ ] **Step 5 — full suite and path-scoped commit.** Test rebuilt projections yield the same pinned
context, selection/exclusion reasons are deterministic, and rules still evaluate through the existing
`qualifying_rules` rather than new sponsor-specific rules. Commit ingestion/context/helpers/tests only.

### Task 4: Make both agents consume the engine and fail honestly

**Files:** Create `app/world_model/runtime.py`, `tests/test_world_integration.py`.
Modify `app/agents/base.py`, `app/pipeline.py`, `app/loop.py`, `app/agents/scout.py`,
`app/agents/skeptic.py`, `app/agents/writer.py`; extend `tests/test_entrypoints.py`,
`tests/test_scout.py`, `tests/test_skeptic.py` and `tests/test_writer.py`. Modify `app/evidence.py`
only to attach explicit observation provenance through existing payloads; do not replace evidence-ID allocation.

**Interfaces:** Produces `WorldRuntime.from_context(ctx, *, scenario_dir: Path | None)`,
`WorldRuntime.ingest_hydration(results: dict[str, SourceResult | None]) -> None`,
`WorldRuntime.ingest_series(...) -> SnapshotRef`, `.context(resource_id, lookback_hours,
resolution_minutes, telemetry_snapshot) -> ResourceContext`, `.pin(candidate_id, context) -> None`,
`.for_candidate(candidate_id) -> ResourceContext`, `.manifest() -> dict`, `.close() -> None`.
Add `world: WorldRuntime | None = None` to `AgentContext` without breaking existing positional fields.
The type import is under `TYPE_CHECKING` to avoid circular agent/world imports.

- [ ] **Step 1 — RED: real pipeline exposes consumed observations and preserves the revision.**

```python
from pathlib import Path
from app.pipeline import run_pipeline

def test_real_loop_consumes_world_context(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGS_DIR", str(tmp_path))
    report, _ = run_pipeline({"sample_mode": True},
                            scenario_dir=Path("data/scenarios/example_1"))
    world = report.summary["integrations"]["meterless_world_model"]
    assert world["status"] == "used"
    assert {"Scout", "Skeptic"} <= set(world["consumers"])
    batch = [f.status for f in report.findings if f.resource_id.endswith("bbb2")]
    assert batch == ["rejected", "revised"]
```

Then patch `ContextBuilderService.build` with a wrapper recording invocation/selected IDs and assert
trace `world_context` records match actual consumptions. A flag set without calls must not pass.

- [ ] **Step 2 — wire lifecycle, hydration and Scout's actual runtime path.** Construct/own a world
runtime in the orchestrator so direct `Orchestrator(ctx)` tests and the production pipeline use it.
The pipeline's `finally` closes the world, trace and state even if construction/ingestion failed.
The direct `Orchestrator.run` path also closes its owned World Model in `finally`; `WorldRuntime.close`
is idempotent and `manifest` remains readable from cached counters after close. This prevents extra
SQLite handles in direct-orchestrator tests. Route the existing standalone `Scout.hydrate` through
the same ingestion service rather than leaving it as a direct-read bypass. Convert direct-agent
fixtures in `tests/test_scout.py` and `tests/test_skeptic.py` to yield/teardown their worlds.

The existing Skeptic falsifier test adds an extra declaration only to the ledger. Extend its setup
to ingest a valid `IaCDeclaration` with the same declared-purpose text, build/pin the candidate's
selection to that source snapshot, and retain the original rejection/reason assertions. Do not
allow unsourced ledger extras to silently mutate an already pinned observation or weaken the
falsifier requirement.

Hydrate the existing source responses once; keep Planner's inventory count/map as a projection for
assignment accounting, not an alternative Scout/Skeptic evidence path. Namespace sample data using
scenario-relative identity and canonical source-content fingerprint (never absolute paths). For live
inventory require explicit region and globally scoped compartment identity from source records or
configured scope; if neither exists, report configuration failure rather than use a shared default.

Scout fetches each required telemetry window through its current recovery path, ingests the selected
matching series with the response's real backend and then builds context. It uses the context's
resource/declaration/rules/series for existing arithmetic, coverage and rule functions. Preserve the
established real-ID/fixture-ID join only when unambiguous; an ambiguous masked join is incomplete.
Attach selected World Model refs to evidence payloads, store candidate->selection and emit bounded
context-selection traces. Do not make a second source request solely for ingestion.

- [ ] **Step 3 — wire Skeptic's pinned context without expanding authority.** Its purpose/schedule
signal check resolves the candidate's pinned World Model selection alongside ledger refs, not global
current state. Pinning must be persisted in run evidence/trace so a later snapshot cannot rewrite an
old ruling. Preserve count keys, recheck caps, existing verdict reasons and the Writer's figure guard.
Missing required pinned context results in abstention/partial, not an accepted invented ruling.

- [ ] **Step 4 — RED→GREEN: world failure, ambiguous joins and clean shutdown.** Inject a constructor
`WorldError("storage")`, a context failure after one valid resource and a locked store. Assert report
status is partial (or capped if an independently hit cap wins), limitations are named, no affected
success finding is published and all created handles close. Add a fixture/live fallback test asserting
stored backend is fixture and degradation is visible. Add two possible masked matches and require
abstention rather than choosing whichever appears first. Do not print exception payloads.

- [ ] **Step 5 — trace ordering and deterministic regression.** In Writer.synthesise add World Model
metadata/status after narrative figure validation but before the final `_emit("synthesise")`; never
add observation hashes, counters or metadata to the narrative's numeric allow-list. Preserve the
final `synthesise` trace and final `report` state event expected by committed-evidence tests. The
orchestrator records the returned report's final status, not a stale pre-Writer local variable.
Test CLI/HTTP equivalents and direct orchestrator tests. Run the full suite, three
curated scenarios and ten held-out seeds. Compare semantic verdict/impact sets against the saved
baseline; ignore only declared volatile run IDs, timestamps and paths, not statuses or quantities.
Commit runtime/agent integration/tests with the actual verification result, never an invented count.

### Task 5: Reproducible engine evidence and offline packaging gate

**Files:** Create `scripts/verify_world_model.py`, `tests/test_world_acceptance.py`,
`docs/meterless-world-model.md`, `output_examples/world_model/` (generated JSON/JSONL only).
Modify `scripts/run_examples.sh` only to keep the touched generation path fail-loud and scratch-safe.

**Interfaces:** `run_world_acceptance(output_dir: Path) -> dict` returns computed acceptance booleans,
source/content identities, actual consumers, dedup counts, both telemetry selections and semantic
comparison results. It refuses an existing output directory. CLI:

```bash
.venv/bin/python scripts/verify_world_model.py --output-dir logs/world-acceptance-new
```

- [ ] **Step 1 — RED→GREEN for the acceptance generator.** The test runs the real fixture pipeline
and actual store services, not a stub emitting fixed success. It then changes a selected input and
requires the corresponding observation/context and audit result to change. Assert a failed guard
makes the acceptance field false and the CLI nonzero. Mask only separate published copies.
- [ ] **Step 2 — add the full offline test with hostile provider environment.**

```python
import socket
import pytest
from pathlib import Path
from app.pipeline import run_pipeline

@pytest.mark.parametrize("name", ["example_1", "example_2", "example_3"])
def test_world_path_is_offline_even_with_bad_provider_env(name, tmp_path, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("offline audit attempted network access")
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setenv("LLM_PROVIDER", "meterless")
    monkeypatch.setenv("METERLESS_BASE_URL", "not a valid URL")
    monkeypatch.setenv("METERLESS_TOKEN", "rt-local")
    monkeypatch.setenv("LOGS_DIR", str(tmp_path))
    report, _ = run_pipeline({"sample_mode": True},
                            scenario_dir=Path("data/scenarios") / name)
    assert report.status == "success"
    assert report.summary["integrations"]["meterless_world_model"]["status"] == "used"
```

- [ ] **Step 3 — repair only the generation script defects that affect this gate.** Its current
`grep ... || true` hides evaluator failures and it writes held-out scenarios under `/tmp`. Capture the
Python command's stdout to a scratch file, check its exit directly, and filter afterwards in Python;
use `TMPDIR`. Increase its actual held-out run to 10 to match the stated gate. Test a deliberately
failing evaluator in the script wrapper so generation cannot falsely succeed. Do not hand-edit logs.
- [ ] **Step 4 — regenerate/validate.** Run the generator, `PY=.venv/bin/python bash scripts/run_examples.sh`,
full suite, curated evals and `--score 10` under scratch. Preserve undefined metrics as null/n/a.
Write a source-attributed guide saying minimum Python adaptation, not complete Meterless conformance.
Keep generic README/metadata claims unverified until their specific delivery gate; do not overwrite
pre-existing dirty text. Commit only this milestone's code/tests/generated evidence/guide.

## Milestone completion evidence

Record the real RED/GREEN commands and exit results, final full-suite output, actual curated/held-out
results, engine acceptance path and commit SHA. No runtime success or full sponsor compliance is
claimed here. Handoff to the Nightshift plan and split-deployment runbook only after the engine's
independently runnable offline path is green.
