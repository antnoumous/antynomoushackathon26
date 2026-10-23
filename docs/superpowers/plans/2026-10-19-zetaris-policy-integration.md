# Zetaris Policy Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a complete, versioned Zetaris policy snapshot a genuinely consumed, opt-in Driftwatch source, with bounded requests, honest fallback and generated evidence of its effect on an audit.

**Architecture:** Keep the existing Source interface and fixture-first registry. A pure validator/exporter defines an immutable policy snapshot; a supervised HTTP worker retrieves it through the verified general SQL endpoint; the existing orchestrator and Scout consume validated rules and preserve their provenance. Source preparation uses administrator privileges only outside the audit; the runtime uses a separately established read-only bearer credential.

**Tech Stack:** Existing Python 3.11+, pydantic 2.9.2, requests 2.32.3, pytest 8.3.3; standard-library multiprocessing with spawn, tempfile, csv, hashlib and http.server. No dependency additions, JVM requirement, service-framework change or orchestration framework.

**Spec:** [Approved Option B proposal](../specs/2026-10-18-sponsor-integration-proposal.md), especially §§1–4, 7–9. The builder approved Option B and policy-first delivery on **19 October 2026**. [Actual platform acceptance](../../../notes/zetaris-oci-deployed-2026-10-19.md) supersedes the proposal's historical registry-blocked state.

**Status:** Planning only. This document is not approval to execute itself, register objects or claim an implemented sponsor integration. No execution method has been selected. No commit/push is authorised.

**19 October setup update:** [Cursor 3.24.18 is now installed and running](../../../notes/cursor-setup-2026-10-19.md)
following the builder's separate setup approval. Earlier absence discovery below is historical.
Application availability is verified. The builder subsequently reported signed in; root
.cursorignore patterns are prepared and parser-tested. Privacy Mode and Cursor UI enforcement,
genuine implementation evidence and the remaining execution gates are not yet verified.

## Global Constraints

- New submission implementation starts no earlier than **22 October 2026 00:00 UTC**; recorded close **27 October 2026 23:45 UTC**. Recheck binding organiser rules before execution and declare September baseline plus October infrastructure preparation.
- Preserve **540-second hard run budget**, **3 rounds**, **25 resources**, **2 rechecks per finding**; reserve **five seconds** before new sponsor operations for finalisation.
- Each new source fetch, including both SQL requests and decoding, has a **30-second** maximum, further limited by usable remaining run time. At most **one source retry** at orchestration level; no internal HTTP retries or unbounded polling.
- Runtime inputs, reports, matching rules, deterministic verdict branches, figure guards, OCI SDK adapters and existing degraded fixture recovery remain intact. This milestone does not establish that every pre-existing OCI/model call obeys a new absolute transport deadline.
- `SAMPLE_MODE=true` remains the complete credential-free/network-free path; do not import live sponsor transport, read sponsor secrets or create worker processes there. A dedicated hybrid acceptance harness is labelled as such, not advertised as normal sample mode or a live OCI audit.
- New metadata is additive: backend remains `live`/`fixture`/`none`; provider is a separate typed field. No invented existing `zetaris` backend enum.
- Maximum **256 policy records**, exact expected count, immutable snapshot ID and content digest. Empty-complete, unavailable, malformed and truncated are different outcomes. Validate all rows before replacing shared facts.
- Only existing R-1–R-5 meanings/classes; no new finding type. Unknown/ill-typed predicates fail the whole remote batch. Never weaken the existing telemetry sufficiency checks.
- No employer data, private OCIDs, registry credentials, metastore secrets, administrator token or raw private prompts in publication files. No secrets in command arguments, request/report JSON, exceptions or trace summaries.
- Personal OCI service remains SSH-only externally and loopback-published internally. No new cloud resource, public port or storage service in this plan. Existing lab teardown is not changed.
- CPU-only setup; no installation/download after application startup. Existing judge entry points remain sufficient with sponsors absent.
- Use Cursor for actual implementation and retain genuine, sanitized development evidence. A guide about Cursor is not evidence of use.

## Review Focus

1. **Silent server truncation:** a response with plausible headers and too few rows must fail against a pinned expected count/hash, not count as a complete policy source. Tasks 1 and 3 pin this.
2. **Usable budget exhausted during initial hydration:** no second attempt or child process may start at/after its cutoff; a slowly arriving body must not evade the deadline. Tasks 2 and 4 pin this.
3. **Remote schema surprises:** `true` as a numeric threshold, non-finite JSON, duplicate JSON keys/rule IDs, new predicates and a familiar rule ID with changed meaning must fail closed. Task 1 pins this.
4. **Successful-but-degraded results and fallback:** both recovery paths must preserve degradation; fixture results must never inherit Zetaris provenance. Task 4 pins this.
5. **Ambient credentials, scope and concurrency:** sample runs ignore malformed sponsor variables; different concurrent scopes/snapshots must not share credentials, subprocess files or evidence. Tasks 2, 3 and 6 pin this.

---

## Boundaries, milestones and execution gates

Option B is the approved destination, **not one indivisible implementation task**. This is the detailed plan only for milestone M1:

| Milestone | Deliverable / handoff | Boundary |
|---|---|---|
| **M1 — this plan** | Validated policy source, exact provenance, least-privilege access, real policy-change acceptance | No remote declaration collection, memory engine or model-provider switch |
| M2 — declarations | Equivalent version/completeness contract for IaC; explicit unknown membership and safe suppression of absence-dependent findings | New detailed plan reviewed after M1; cannot treat a missing catalog as no declarations |
| M3 — World Model | Atomic/idempotent persistent ingest, isolated partitions, context construction and actual Scout/Skeptic consumption | Needs its own detailed plan; SourceProvenance is not itself a World Model |
| M4 — Nemotron | Authenticated candidate capability test, structured explanations, observable fallback, unchanged deterministic safety | Needs its own detailed plan; no promise about model compatibility from a model name |
| M5 — combined acceptance | All-sponsor generated evidence, offline/fresh setup, evaluations, README/metadata/deck/demo | M1 passing cannot be described as Option B complete |

Execution gates, checked before product edits:

- [ ] Builder reviews this written plan and selects **Native** or **Subagent-driven** execution.
- [ ] Confirm the actual current build-window/rules wording and resolve or explicitly escalate OCI hosting, Meterless adaptation, Nemotron role, primary track and baseline eligibility. Do not assert eligibility or send an organiser message without authorisation.
- [ ] Record actual branch/status and baseline test output. The planning tree is dirty, with pre-existing edits including protected `AGENTS.md`; never stage all files, reset it, or write that protected file to record status.
- [ ] Choose the actual Cursor work surface with the builder. Read-only planning discovery did not find Cursor.app in /Applications or ~/Applications on this Mac; that does not establish whether it exists elsewhere. No installation is authorised by this plan. No public-repo-to-employer credential transfer. If Cursor availability is unresolved, that is a development-compliance blocker, not permission to falsely attribute Hermes work to Cursor.
- [ ] Record baseline commit `25b9e5b` as the planning reference only; recheck at execution. Create a working branch/worktree only through the selected workflow and without relocating the user's dirty work automatically.
- [ ] Concrete object/permission writes require the Task 5 dry-run package and approval before execution. Scope approval did not approve a DDL payload that did not yet exist.

## File map and responsibility

All **Create** paths below are proposed new files; they are not existing imports.

| File | Responsibility |
|---|---|
| Create `app/source_metadata.py` | Independent, dependency-light typed provenance used by source and report models; avoids circular imports through `app.sources.__init__` |
| Create `app/sources/policy_snapshot.py` | Pure predicate/row validation, canonical digest, scope identity, manifest validation; no network/env reads |
| Create `app/sources/zetaris_http.py` | Secret-safe settings, fixed SQL endpoint, bounded spawn worker, exact response decoding/error taxonomy |
| Create `app/sources/zetaris_policy.py` | Two fixed SELECTs, complete-snapshot assembly and SourceResult; no DDL or admin login |
| Create `scripts/export_zetaris_policy.py` | Explicit offline CSV snapshot exporter, immutable output directory and dry-run registration SQL |
| Modify `app/config.py:25–68` | Opt-in policy backend, ignoring remote selection in sample mode |
| Modify `app/sources/base.py:17–29` | Optional monotonic deadline on Scope; optional typed provenance on SourceResult |
| Modify `app/models.py:142–148` | Optional typed provenance on SourceStatus |
| Modify `app/sources/live.py:23–36` | Lazy, opt-in remote policy source; keep IaC file-backed |
| Modify `app/loop.py:48–120` | Forward deadline; preserve status/provenance; nonretryable failure handling; atomic hydration and provenance events |
| Modify `app/agents/scout.py:26–36,66–108,203–205` | Sibling status handling, atomic direct hydration, policy evidence linkage |
| Modify `.env.example` | Placeholder-only actual environment seam; no existing private `.env` edits by default |
| Create `tests/test_policy_snapshot.py`, `tests/test_zetaris_http.py`, `tests/test_zetaris_policy.py`, `tests/test_zetaris_integration.py` | Pure, transport, source and end-to-end tests |
| Modify `tests/test_loop.py`, `tests/test_sources.py` | Regressions at existing loop/registry seams |
| Create `docs/zetaris-policy-operations.md` | Exact reviewed publication/access/readback procedure and technical-vs-eligibility limits |
| Modify `README.md`, `docs/decisions.md`, `docs/insights.md` | Actual role, failures, offline guarantees and build attribution |
| Generated `output_examples/zetaris_policy/` and `logs/samples/zetaris-policy/` | Sanitized executed acceptance only; no handwritten report/trace files |

No change to requirements, Dockerfile, findings/pricing, generator or critic decision logic in M1. Update renderer only if a test demonstrates additive SourceStatus metadata is otherwise misrepresented; provenance must still appear in JSON and trace. Do not add a decorative unused service.

## Cross-task interfaces

These are **new contracts** to implement, not pre-existing symbols. All names below are defined by the owning task before a consumer uses them.

```python
# Task 1: app/source_metadata.py
class SourceProvenance(BaseModel):
    provider: Literal["zetaris"]
    object_name: str
    manifest_object: str
    snapshot_id: str
    schema_version: int
    requested_scope_hash: str
    content_sha256: str
    row_count: int
    expected_count: int
    complete: bool
    observed_at_utc: str
    fetched_at_utc: str
    query_sha256: str

# Task 1: app/sources/policy_snapshot.py
validate_rules(records: list[dict]) -> list[dict]
policy_digest(records: list[dict]) -> str
scope_digest(scope: Scope) -> str
validate_snapshot(manifest: dict, rows: list[dict], *, snapshot_id: str,
                  expected_sha256: str, requested_scope_hash: str) -> list[dict]

# Task 2: app/sources/zetaris_http.py
@dataclass(frozen=True)
class ZetarisSettings:
    base_url: str
    api_key: SecretStr
    org_id: str
    policy_object: str
    manifest_object: str
    snapshot_id: str
    expected_sha256: str
    @classmethod
    def from_env(cls) -> "ZetarisSettings": ...
class ZetarisError(SourceError):
    # str(error) is only "zetaris:<category>"; no raw body/URL/header.
    category: Literal["configuration", "authentication", "transport", "deadline",
                      "query", "schema", "incomplete"]
    retryable: bool
run_sql_batch(settings: ZetarisSettings, queries: tuple[str, ...],
              deadline: float) -> list[dict]
decode_response(response: dict, columns: tuple[str, ...]) -> list[dict]

# Task 3: app/sources/zetaris_policy.py
class ZetarisPolicySource:
    name = "policy"
    def __init__(self, settings: ZetarisSettings | None = None,
                 transport: Callable = run_sql_batch): ...
    def fetch(self, scope: Scope) -> SourceResult: ...
```

`Scope.deadline_monotonic: float | None = None`; `SourceResult.provenance` and
`SourceStatus.provenance` are `SourceProvenance | None = None`. Existing backend literals
are unchanged. New optional report fields are an additive schema change; compare baseline
semantics with those new null fields normalized, not by silently rewriting old numbers.
No source constructor performs network I/O. No new symbol is imported by fixture-first registry code.

Environment seam (all read in process environment, never from request JSON):

```dotenv
DRIFTWATCH_POLICY_SOURCE=file
ZETARIS_REST_URL=http://localhost:8888/api/v1.0
ZETARIS_API_KEY=replace-with-read-only-runtime-key
ZETARIS_ORG_ID=replace-with-actual-numeric-id
ZETARIS_POLICY_OBJECT=DRIFTWATCH_REF.policy_rules_base_v1
ZETARIS_MANIFEST_OBJECT=DRIFTWATCH_REF.policy_manifest_base_v1
ZETARIS_POLICY_SNAPSHOT=example1_base_v1
ZETARIS_POLICY_SHA256=replace-with-generated-lowercase-sha256
```

Runtime accepts only `file` or `zetaris` for policy source. The seven Zetaris settings must be
validated only when constructing the selected remote source; sample mode forces `file` before
looking at even malformed remote variables. A token minted from the administrator account is
not a read-only runtime key; supplier docs say a key inherits the account's permissions.

---

### Task 1: Complete policy snapshot contract and deterministic publication package

**Files:** Create `app/source_metadata.py`, `app/sources/policy_snapshot.py`, `scripts/export_zetaris_policy.py`, `tests/test_policy_snapshot.py`; modify `app/sources/base.py`, `app/models.py` for optional fields only.

**Consumes:** Existing Scope, PolicyRule, ResourceClass, FindingClass and baseline policy files.
**Produces:** The four pure functions and SourceProvenance above; exporter CLI below. No runtime backend yet.

- [ ] **Step 1: Write failing canonical/semantic tests.** Define `BASE` from the actual baseline file and test ordering, complete empty data and invalid predicates explicitly:

```python
import copy, json, math
from pathlib import Path
import pytest
from app.sources.policy_snapshot import validate_rules, policy_digest, validate_snapshot

BASE = json.loads(Path("data/scenarios/example_1/policy.json").read_text())["rules"]

def test_digest_is_order_independent():
    assert policy_digest(BASE) == policy_digest(list(reversed(BASE)))

@pytest.mark.parametrize("bad", [True, "5", float("nan"), float("inf"), -1, 101])
def test_cpu_threshold_is_finite_numeric_percent_not_boolean(bad):
    rows = copy.deepcopy(BASE)
    rows[2]["when"]["mean_cpu_lt"] = bad
    with pytest.raises(ValueError):
        validate_rules(rows)

def test_unknown_predicate_is_not_silently_ignored():
    rows = copy.deepcopy(BASE)
    rows[2]["when"]["mean_cup_lt"] = rows[2]["when"].pop("mean_cpu_lt")
    with pytest.raises(ValueError):
        validate_rules(rows)
```

Also parameterize duplicate rule IDs; unknown IDs; wrong finding class for a known rule;
R-1 aimed at compute; R-5 without true compute/absence conditions; string booleans; missing note;
note >2048 characters; `when_json` >4096 bytes; duplicate keys in `when_json`; mixed snapshot IDs;
negative/non-decimal expected count; missing/timezone-naive timestamps; count 257; wrong pinned
hash/scope/version; expected 5 but returned 4. For empty-complete use expected_count 0 and the digest
of `[]`; it validates to no rules rather than raising an outage. Define each parametrized case in
this test module, not in a live test helper that reads credentials.

- [ ] **Step 2: Run RED.** `python -m pytest tests/test_policy_snapshot.py -q` must fail because the new module/functions do not exist. Record the actual result, not the expected message alone.

- [ ] **Step 3: Implement canonical identity, semantic validation and optional metadata.** Canonical digest implementation:

```python
def policy_digest(records: list[dict]) -> str:
    normalized = validate_rules(records)
    payload = json.dumps(sorted(normalized, key=lambda r: r["rule_id"]),
                         sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

`validate_rules` returns dictionaries with `rule_id`, `class`, `when`, `note` only. Reject
extra record fields. Preserve existing numeric types after validation so exporter/importer
hashing agrees; do not coerce a boolean/string to a number. Whitelist the eight predicates actually
implemented by `_matches`: resource_class, compute_instance, attached, absent_from_iac,
min_coverage_ratio, mean_cpu_lt, peak_cpu_lt, peak_cpu_gte. Resource class must be one of the three
existing literals; boolean predicates require `type(value) is bool`; numeric predicates require
`type(value) in (int, float)`, `math.isfinite`, percent in [0,100] and coverage in [0,1]. Enforce
R-1/R-2 detached volume/IP meanings, R-3/R-4 compute cost class plus their existing low-mean and
opposing peak predicates, and R-5 compute/absence/unattributed meaning. Additional supported
predicates may narrow but not contradict those identities. Any subset including empty is valid;
new IDs or broadened identities are not. Global telemetry sufficiency remains independently enforced.

`scope_digest` hashes canonical JSON of sorted compartment_ids and resource_types, not lookback,
resolution, run ID or monotonic deadline. Publication stores only the digest, never real OCIDs.
Parse timestamp values with timezone; do not infer source freshness from fetch time. Version
selection is exact: no `latest`, mutable-pointer lookup or unapproved time-based expiry heuristic.

`validate_snapshot` requires exactly one manifest at the caller, schema version 1, exact selected
snapshot/scope/pinned digest, count 0–256, every row's snapshot ID equal, and digest after semantic
validation equal to both manifest and configuration. CSV integers must be ASCII decimal strings
or strict integers, never floating/exponent/bool values. Raise ValueError with fixed categories,
not attacker-supplied contents. `when_json` decoding must reject duplicate keys/non-finite constants.

- [ ] **Step 4: Add exporter and its failing-then-passing test in the same task.** CLI:

```sh
python scripts/export_zetaris_policy.py --policy data/scenarios/example_1/policy.json \
  --snapshot-id example1_base_v1 --scope-json input_examples/example_1.json \
  --out "$HOME/.oci/zetaris-deployment/policy-exports/example1_base_v1"
```

This is a new private publication directory below the existing operator handoff directory;
refuse if it already exists, and never overwrite a previously published version.
Like existing scripts/make_scenario.py, insert `Path(__file__).resolve().parents[1]` into
sys.path before importing app modules so direct script invocation works without PYTHONPATH.
Use argparse `Path` values, a new output directory (`mkdir(mode=0o700, parents=True, exist_ok=False)`), and the same
RunConfig/Scope resolution as the actual input request. Do not read sponsor credentials.
Write UTF-8 `rules.csv` with columns `snapshot_id,rule_id,class,when_json,note`, header even
when empty; use csv.DictWriter for JSON/commas/newlines. Write `manifest.csv` with columns
`snapshot_id,schema_version,expected_count,content_sha256,requested_scope_hash,observed_at_utc`.
Emit a non-secret local manifest and proposed registration SQL; no network/DDL. Source SHA is
of normalized logical rules, not CSV bytes. Refuse overwrite; changing policy requires a new
snapshot/object pair. Exporter test imports/reloads CSV with DictReader, passes rows through
`validate_snapshot` and asserts identity with input; a second export to the same directory fails.

- [ ] **Step 5: GREEN and review.** Run `python -m pytest tests/test_policy_snapshot.py tests/test_sources.py -q`. Check old SourceResult/SourceStatus construction still works and new metadata is optional. Review the diff; no unrelated model validation changes. Do not commit unless the builder separately authorises commits.

### Task 2: Secret-safe REST settings and absolute fetch cutoff

**Files:** Create `app/sources/zetaris_http.py`, `tests/test_zetaris_http.py`.
**Consumes:** Scope-independent deadline and endpoint settings; existing requests and SourceError.
**Produces:** ZetarisSettings, ZetarisError, run_sql_batch and decode_response contracts above.

- [ ] **Step 1: Write RED settings/transport tests.** Validate credential redaction and expired-budget behaviour:

```python
def test_expired_budget_starts_no_worker(monkeypatch):
    import time
    import app.sources.zetaris_http as http
    def forbidden(*args, **kwargs):
        raise AssertionError("worker created after deadline")
    monkeypatch.setattr(http.multiprocessing, "get_context", forbidden)
    with pytest.raises(http.ZetarisError) as error:
        http.run_sql_batch(settings(), ("SELECT 1",), time.monotonic() - 1)
    assert error.value.category == "deadline"
```

Here `settings()` is a test-local constructor using `SecretStr("test-only-token")`, numeric
org `"6"`, loopback URL and syntactically valid object/snapshot/digest fields. Define it in this
module. Test malformed numeric org, URL userinfo/query/fragment, non-loopback HTTP, unknown backend,
identifier/snapshot SQL injection, repr(settings) and exception/trace text excluding that token.
Reject redirects; never forward Authorization to an arbitrary host. HTTPS is required except
explicit loopback `localhost`, `127.0.0.1`, `[::1]` for the SSH-tunnel configuration.

Add a local ThreadingHTTPServer fixture with daemon request threads and no access-log output;
normal response uses verified shape `{"headers":["one"],"data":[["1"]],"total":1,"timeUsed":1}`.
Assert fixed POST path `/api/v1.0/sql-editor/sqls/run`, random UUID per request, numeric X-Org-ID,
and body `queryId/sql/source/limit`. Test HTTP 401/403 => nonretryable authentication; 429/5xx =>
retryable transport; 202 => bounded non-success query response, not invented polling; redirect,
non-JSON, oversized body, header mismatch, row-width mismatch and false total => safe failure.

- [ ] **Step 2: Run RED.** `python -m pytest tests/test_zetaris_http.py -q`.

- [ ] **Step 3: Implement settings and one supervised process per complete fetch.** Validate
qualified object identifiers with exactly two regex-checked segments, and snapshot ID with
`[A-Za-z0-9_-]{1,64}`; lowercase digest is exactly 64 hex characters. No arbitrary SQL input is
exposed to request JSON. `SecretStr` protects repr; manually classify configuration errors so
pydantic/raw server errors cannot echo inputs. Validate in the frozen dataclass's __post_init__
as well as from_env so programmatic/harness construction cannot bypass identifier/URL checks;
use object.__setattr__ only for validated normalization if needed. Add a direct-constructor
injection rejection test. `ZetarisError.__str__` exposes only category.

Worker algorithm, to implement as top-level `_worker(settings, queries, output_path)` so spawn
can import it: use a Requests session with trust_env=False, redirects disabled, no retry adapter,
explicit connect/read timeouts, streaming bodies, maximum **2 MiB per response** and two queries
maximum. Send exact SELECT texts supplied by the source, source `SqlEditor`, limit **257**,
fresh query/request UUIDs, bearer token and org header. Status errors write only categorized
failure; never persist raw body/header/token. Check HTTP status and JSON object/field types.
Use a private TemporaryDirectory per call; write a bounded JSON result atomically after both
queries complete. No stdout/stderr payloads and no large Queue/Pipe send that can deadlock a
parent waiting on join.

Parent control flow:

```python
cleanup_reserve = 0.5
remaining = deadline - time.monotonic()
if remaining <= cleanup_reserve:
    raise ZetarisError("deadline", retryable=False)
ctx = multiprocessing.get_context("spawn")
with tempfile.TemporaryDirectory(prefix="driftwatch-zetaris-") as directory:
    output = str(Path(directory) / "result.json")
    process = ctx.Process(target=_worker, args=(settings, queries, output))
    try:
        process.start()
        process.join(max(0.0, deadline - time.monotonic() - cleanup_reserve))
        if process.is_alive():
            raise ZetarisError("deadline", retryable=False)
        if process.exitcode != 0 or not Path(output).is_file():
            raise ZetarisError("transport", retryable=True)
        # Decode bounded worker envelope; return its two response objects or its safe error.
        return _read_worker_result(Path(output), expected_responses=len(queries))
    finally:
        if process.is_alive():
            process.terminate()
            process.join(0.25)
        if process.is_alive():
            process.kill()
            process.join(0.25)
        if process.is_alive():
            raise ZetarisError("transport", retryable=False)
        process.close()
```

Implement `_read_worker_result(path: Path, expected_responses: int) -> list[dict]` in this task: enforce a **4 MiB**
file limit, allowed success/error envelope fields and exactly two response objects for a
policy fetch; instantiate only allowlisted categories/retryability, not arbitrary exceptions.
Also support one-query transport tests without calling it a policy fetch; require one or two
input queries and response count equal to expected_responses, passing len(queries) consistently.
Temporary output is not a durable evidence store. DNS/connect/body delays are covered by the
parent cutoff; local worker death is **not proof of remote Spark query cancellation**.

`decode_response` requires exact requested header names/order, list-of-list data, matching row
widths, and a strict integer total at least returned length; total greater than returned length
is incomplete. Produce dict(zip(columns,row)) only after validating the entire response. Reject
unexpected top-level errors and query failure objects even on HTTP 200. The actual verified API
uses `headers`, `data`, `total`, `timeUsed`; do not use SELECT-only `records` pagination shape.

- [ ] **Step 4: Add measured slow-body and concurrent-call tests.** Drip bytes every 0.05 s
past a 1.5 s deadline, assert the handler saw the POST, elapsed <3 s and active child PIDs equal
the pre-call set. Run two independent calls with different tokens/orgs against separate local
servers and assert no swapped body/headers/output. Add worker exit-before-write, malformed envelope
and client socket-error cases. Keep fixture shutdown outside the measured transport interval.

- [ ] **Step 5: GREEN/review.** `python -m pytest tests/test_zetaris_http.py -q`. Run on macOS
spawn and the personal Linux environment during packaging; do not claim platform portability
from monkeypatched workers alone. No dependency install and no real external credential required.

### Task 3: Opt-in Zetaris policy Source with complete provenance

**Files:** Create `app/sources/zetaris_policy.py`, `tests/test_zetaris_policy.py`; modify `app/config.py:25–68`, `app/sources/live.py:23–36`, `.env.example`, `tests/test_sources.py`.
**Consumes:** Tasks 1–2 contracts and optional Scope.deadline_monotonic.
**Produces:** Production ZetarisPolicySource; default/sample source behaviour unchanged.

- [ ] **Step 1: Write RED adapter test with a local fake transport, not a network call.**

```python
def test_complete_snapshot_returns_live_provider_provenance(scope, snapshot_payloads, settings):
    # These are fixtures defined in this new test module, not presumed global fixtures.
    calls = []
    def transport(config, queries, deadline):
        calls.append((queries, deadline))
        return snapshot_payloads
    result = ZetarisPolicySource(settings, transport=transport).fetch(scope)
    assert result.backend == "live"
    assert result.provenance.provider == "zetaris"
    assert result.provenance.complete is True
    assert result.provenance.row_count == len(result.records) == 5
    assert len(calls) == 1 and len(calls[0][0]) == 2
```

Define fixtures by exporting/reloading actual example_1 rules with Task 1 helpers, exact response
headers and a Scope of empty compartment IDs/default resource types; settings hash equals the
generated manifest. Test count/hash/scope mismatch, 257 rows, truncated response, wrong snapshot
in a later row, duplicate IDs, header reordering, and complete-empty returning records=[] without
marking a network failure. Assert a bad final row never returns a partial SourceResult.

- [ ] **Step 2: Run RED.** `python -m pytest tests/test_zetaris_policy.py tests/test_sources.py -q`.

- [ ] **Step 3: Implement two fixed SELECTs and atomic result creation.** Columns:

```python
MANIFEST_COLUMNS = ("snapshot_id", "schema_version", "expected_count", "content_sha256",
                    "requested_scope_hash", "observed_at_utc")
RULE_COLUMNS = ("snapshot_id", "rule_id", "class", "when_json", "note")
```

Build SELECTs over the settings' validated object pair, with exact validated snapshot literal
and ORDER BY rule_id for rules. Quote the `class` identifier with backticks; query hash records
exact query texts, not a bearer header. A single `run_sql_batch` call encloses both requests.
Set cutoff `min(time.monotonic()+30, scope.deadline_monotonic-5)` when a run deadline exists;
when used standalone, cap at 30 seconds. If usable time <=0, raise nonretryable deadline before
calling transport. Require one manifest row, semantic+scope+count+dual-digest validation and
complete body before returning `SourceResult(source="policy",backend="live",records=rules,
provenance=...)`. Capture source observation time from manifest and separate UTC fetch time.
Convert validation failures into sanitized `ZetarisError` categories. Recheck the cutoff after
bounded decoding/validation and before returning a successful SourceResult. The worker join
reserves 0.5 seconds within the source operation for termination/reaping rather than adding
cleanup after a fully consumed 30-second wait; the separate five-second run reserve remains.

A policy definition is loaded once per audit; exact immutable object/version and independently
pinned digest prevent read drift even though the two calls are not a database transaction.
If an administrator mutates files under the same version, mismatched digest fails closed.
No writes, auth-login fallback, auto-create, SDK calls, source registration, polling or retry
in this class. Settings are immutable per instance; no global client/token/scope cache.

In RunConfig add `policy_source: Literal["file","zetaris"] = "file"`. During existing
from_env_and_request, resolve sample_mode first; set file for sample, otherwise read
DRIFTWATCH_POLICY_SOURCE. Do not read backend or credential selection from user request fields.
In live.get_live_source, only selected name==policy and policy_source==zetaris lazily imports
the new class; other source dispatch stays unchanged. Invalid remote configuration may fail
explicitly at setup, never silently select file. Record that setup validation precedes the run
budget but has no external I/O. Add only the actual settings above to .env.example.

- [ ] **Step 4: Add sample isolation tests.** With sample true, backend="invalid" and all
Zetaris variables malformed, get_source still returns PolicyFixtureSource. Block importing
zetaris_http/zetaris_policy and block socket constructors; ordinary pipeline still succeeds.
With sample false/file, policy remains file-backed and IaC still requires its scenario directory.
With sample false/zetaris, construction reads settings but performs zero network calls.

- [ ] **Step 5: GREEN/review.** `python -m pytest tests/test_zetaris_policy.py tests/test_sources.py tests/test_policy_snapshot.py tests/test_zetaris_http.py -q`. Verify required response-shape/constants are defined once and no default branch imports sponsor code.

### Task 4: Orchestration deadlines, truthful recovery and consumed policy lineage

**Files:** Modify `app/loop.py:48–120`, `app/agents/scout.py:26–36,66–108,203–205`; extend `tests/test_loop.py` and create `tests/test_zetaris_integration.py`.
**Consumes:** Validated SourceResult, SourceProvenance and deadline field.
**Produces:** Safe runtime integration, generated lineage on actual rule hits and recovery parity.

- [ ] **Step 1: Write RED at existing test seams.** Add this directly to tests/test_loop.py,
where build and actions are already defined:

```python
def test_source_returned_degradation_is_preserved(tmp_path):
    from app.sources.base import SourceResult
    _, ctx = build(tmp_path)
    original = ctx.sources["policy"]
    class Degraded:
        name = "policy"
        def fetch(self, scope):
            result = original.fetch(scope)
            return result.model_copy(update={"degraded": True, "reason": "test-degraded"})
    ctx.sources["policy"] = Degraded()
    report = Orchestrator(ctx).run()
    status = next(s for s in report.sources if s.name == "policy")
    assert status.degraded and status.reason == "test-degraded"
```

Add a sibling test replacing telemetry with a successful-but-degraded SourceResult and assert
Scout.source_statuses preserves it. Add a two-row inventory load with second malformed record
and assert no first-row mutation; equivalent policy load must leave previous rules unchanged.
Add a source that records Scope.deadline_monotonic and an advanced fake clock: no retry after
expiry; count transport starts and validate one fixed deadline across both attempts.

- [ ] **Step 2: Run RED.** `python -m pytest tests/test_loop.py -q` and record the actual failing regressions.

- [ ] **Step 3: Integrate the existing paths without broad refactoring.** At each _fetch call,
copy Scope to include the shared absolute deadline; check current usable budget before the
first/retry call for the new deadline-aware policy path. Keep pre-existing generic source
behaviour unchanged except for truthful status propagation. Honour `retryable=False` on a
ZetarisError instead of performing a pointless second auth/schema request. At deadline, do
not start a new source or fallback operation that performs external work. Fixture fallback
may run locally if finalisation budget remains, retaining its fixture/degraded identity.

Both existing success paths construct:

```python
SourceStatus(name=name, backend=result.backend, degraded=result.degraded,
             reason=result.reason, provenance=result.provenance)
```

Choose source_ok/source_degraded event status from the returned result rather than always
success. Fixture fallback must have provenance=None unless a real fixture provenance schema is
separately approved; it must never copy a failed Zetaris result's metadata. Store validated
per-source provenance in `ctx.extras["source_provenance"]` at hydration, clear any stale entry
before retries/fallback, and append its sanitized JSON to an actual source_snapshot state/trace
event using existing Tracer fields. Do not redesign Tracer around arbitrary extra kwargs.

Make Orchestrator._load inventory transactional in memory: first build the entire temporary
resource dict, then update shared facts once. Policy/IaC list comprehensions already evaluate
before assignment; preserve this property. Apply the same temporary-dict approach to direct
Scout.hydrate inventory. Do not validate remote schemas again after partial mutation.

For each actual policy rule_hit evidence, extend payload from {rule_id} with the current
source's snapshot_id/content_sha256/object_name/provider only if provenance exists; add a
stable lineage reference `policy:<content_sha256>:<rule_id>`. This is a content-based rule
reference, **not a claimed persisted World Model observation**. Existing sample evidence
without provenance remains unchanged. An empty-complete remote policy still yields the
existing no-rules partial/undetermined report, but status identifies a complete empty source,
not a transport outage or a fabricated finding.

- [ ] **Step 4: Pin no-partial-state, sanitization and source-effect tests.** In the new
integration module copy the small AgentContext construction from the inspected tests/test_loop.py
into a module-local helper; use existing fixture inventory/telemetry/IaC and RulesGenerator.
Inject the production remote policy source with an in-memory test transport. Run baseline and
variant snapshots through the exact Orchestrator/Scout/Skeptic/Writer path. Variant removes only
R-1; assert the detached volume cost_waste finding is present for baseline, absent for variant,
and unrelated accepted/revised findings match. Inspect ledger rule_hit payload and trace
source_snapshot event for matching digest/version. Do not compare random IDs/paths/times.
Test a failed remote source with fixture fallback and assert no Zetaris rule lineage survives.
Test without fallback => partial/no unsupported finding; successful degraded => partial status.
Test fake response containing a canary token and ensure no report/trace/stdout includes it.

- [ ] **Step 5: GREEN/review.** `python -m pytest tests/test_loop.py tests/test_zetaris_integration.py tests/test_scout.py tests/test_skeptic.py -q`; if an existing test path differs, locate it first rather than adding an empty file to satisfy the command. Re-evaluate task scope here: do not silently defer M2–M4 or drop safety tests to fit time.

### Task 5: Reviewed synthetic publication and real read-only runtime access

**Files:** Create `docs/zetaris-policy-operations.md`; generated private CSV/DDL/access evidence outside Git. No runtime registration feature.
**Consumes:** Task 1 exporter, deployed service, actual assigned object names and administrator-operated access workflow.
**Produces:** Proven base/variant immutable object pairs, read-only runtime token handoff and exact settings; no claim of product success yet.

- [ ] **Step 1: Prepare dry-run package after the build window opens.** Read current live
OpenAPI/schema and pinned supplier SQL reference before choosing administration endpoints.
Existing supplier references: docs/guides/zetaris-lightning-sql-commands.md §§5,20,21 and
docs/connections/client-setup.md §§API Tokens/permissions. API schema discovery uses Basic auth
and stays private; do not print credentials or a full resolved configuration. Product code
must not depend on administration endpoints.

Export base example_1 policies and a second reviewed input with only R-1 omitted. Give each a
separate immutable directory, snapshot ID and table pair; record exact generated hashes. No
private OCI inventory/declarations is uploaded. Proposed namespace DRIFTWATCH_REF, base objects
policy_rules_base_v1 / policy_manifest_base_v1, variant objects policy_rules_no_volume_v1 /
policy_manifest_no_volume_v1. Check existing objects/ownership before any reuse.

Review driver-visible storage without new cloud services: the existing shared customer-data
volume is mounted at `/home/zetaris/customer-data` in driver/API. Proposed staging location is
`shared/driftwatch-policy/<snapshot_id>/` in that volume, with synthetic CSV files readable by
UID 1001 and operator-controlled immutable contents. File-path registration on this instance
is a **capability gate**, not a previously successful operation. The SQL shape is documented;
local-file acceptance and exact filesystem mapping must be tested after approval:

```sql
CREATE LIGHTNING DATABASE DRIFTWATCH_REF DESCRIBE BY "Driftwatch synthetic reference policies";
CREATE LIGHTNING FILESTORE TABLE policy_rules_base_v1 FROM DRIFTWATCH_REF FORMAT CSV
OPTIONS (path "file:///home/zetaris/customer-data/shared/driftwatch-policy/example1_base_v1/rules.csv", header "true");
CREATE LIGHTNING FILESTORE TABLE policy_manifest_base_v1 FROM DRIFTWATCH_REF FORMAT CSV
OPTIONS (path "file:///home/zetaris/customer-data/shared/driftwatch-policy/example1_base_v1/manifest.csv", header "true");
```

Generate the second pair from the actual second export; do not copy a digest or snapshot ID
from prose. Send one statement per request. Show concrete source paths, table names, manifest
counts/hashes and access changes to the builder and wait for explicit dry-run approval before
registration/grants. If local file registration fails, stop that live gate and propose a
reviewed alternative; do not add an S3 bucket, expose HTTP, copy data into a cached catalog or
claim federation. Offline implementation tasks can still be reviewed independently.

- [ ] **Step 2: Establish a non-admin identity and runtime token through the supported workflow.**
Do not invent a CREATE USER SQL statement: the inspected SQL reference does not specify one.
Use actual UI/admin documentation or the live OpenAPI to identify user creation and permissions;
record their exact supported actions in the operations doc before applying the reviewed payload.
Create a dedicated non-admin runtime identity and restrict assignments/SELECT grants to the
four owned policy objects, with no grant option, user-management, access-control-write, insert,
cache or object-creation capability. Keep administrator and runtime credentials separate.

Supplier docs say API keys inherit the account's permissions and are shown once: **the builder
creates the key in Management → API Tokens while signed in as the runtime identity**, saves it
privately, and provides only its local path; never ask for it in chat, autonomously fetch it or
put an administrator key into runtime settings. The executor validates actual numeric org ID,
account level and grants readback, allowed SELECTs, and a denied SELECT on an existing unassigned
sample table. No destructive denial probe or dummy object creation without its own approved
payload. If the account has unexpected broad access, fail this gate; do not reinterpret it as
read-only because the adapter emits SELECTs.

- [ ] **Step 3: Execute and read back only approved operations.** Validate file/driver-visible
path, schema, returned string types, empty header-only CSV support, base count and both pinned
digests. Require runtime SELECT success on manifest and rules via the production transport,
with expected count/hash, and no runtime admin login. Confirm unassigned sample access is
refused and administrator-side capability/grant records show the narrow identity. Retain raw
private responses separately; publish only sanitized actual outcomes.

- [ ] **Step 4: Review the gate result.** If any identity/token/storage/permission capability
is not established, mark live acceptance blocked and report the precise missing capability.
Do not mark Task 5 complete based on previous administrator smoke checks. Document that these
are **exported versioned synthetic reference files queried through Zetaris**, not zero-copy
access to OCI Monitoring or an automatically synchronized policy system.

### Task 6: Real source-effect acceptance, offline parity and packaging

**Files:** Extend `tests/test_zetaris_integration.py`; create `scripts/verify_zetaris_policy.py`; modify README/docs/insights; generate sanitized outputs and traces only after execution.
**Consumes:** Tasks 1–5 complete; exact approved snapshot configurations and runtime credential from environment.
**Produces:** Working M1 acceptance artifact, red/green evidence and explicit remaining Option B gates.

- [ ] **Step 1: Write RED acceptance harness tests.** The proposed CLI accepts `--scenario`,
`--base-settings`, `--variant-settings`, `--output-dir`; the two settings files contain only
non-secret object/version/digest selections. Runtime bearer/base/org remain environment-only.
Reject files that try to supply secrets, malformed settings or an existing output directory.
Test output JSON must reflect computed reports/traces, not a fixed success map. Define
`run_acceptance(scenario: Path, base: dict, variant: dict, output_dir: Path) -> dict` in the
new script; have argparse main call it under a __main__ guard (spawn safe).

Use the same explicit repository-root sys.path setup as the exporter before importing app
modules. No top-level audit, network request or worker start during module import.

- [ ] **Step 2: Implement actual dual-run harness.** Build two normal AgentContexts with
RulesGenerator and fixture inventory/IaC/telemetry; select production ZetarisPolicySource for
policy in each. Force each run to get its own deadline/context/logs. This is an explicit
**hybrid integration test**, not a demo-only application branch: no production switch swaps
policy data based on known input. Compare only computed accepted/revised findings and policy
evidence. Assert base has the detached-volume cost_waste finding and variant does not; do not
require prewritten totals. Emit `hybrid=true`, actual backend/provider per source, snapshot
hashes, selected rules, source-call outcomes and changed finding keys. A fallback-only result
fails sponsor acceptance even if a report otherwise succeeds. Retain complete generated
reports privately; publish sanitized copies and trace through existing mask/check tooling.

- [ ] **Step 3: Execute all policy gates with actual read-only runtime credentials.**
Run the new CLI through the active private tunnel, first base then variant. Read back output
and match trace run IDs to reports. Require real provider=zetaris complete snapshots in both,
actual rule_hit lineage consumption, expected count/hash and computed finding difference.
Exercise an unreachable local endpoint separately and prove explicitly degraded fallback;
do not disable the service or change OCI ingress to simulate an outage. A full live OCI audit
is optional evidence and must keep real data private and insufficient-history abstention intact.

- [ ] **Step 4: Run offline/fresh setup and evaluations.** Minimum commands, all from the
chosen clean implementation environment, not by overwriting the current dirty workspace:

```sh
python -m pytest -q
python run.py --input input_examples/example_1.json --scenario data/scenarios/example_1
python -m evals.run_eval
python scripts/make_scenario.py --score 10 --out logs/heldout-policy-verification
```

The curated evaluator has no argument parser: `--help` would execute it, not display help.
The commands above match the inspected files; recheck if their interfaces change. Record
actual precision/recall/verdict accuracy/determinism,
not a forecast or an empty-ground-truth perfect score. Extend the existing sample test to
block sockets and worker creation with all sponsor/model variables absent, and another test
with invalid sponsor variables present. Compare the three curated and ten existing held-out
seeds against the September baseline. Regenerate committed examples only with existing generator
scripts when required by additive schema changes; preserve run/trace identity tests. Exercise
fresh CPU-only clone/export and HTTP /run sample path with no sponsor secrets. No runtime
network/install is needed. Existing Windows verification remains public-sample-only and never
receives the private settings/token/SSH material.

- [ ] **Step 5: Final review and factual handoff.** `git diff --check`, actual full tests,
secret/OCID/token scans over all publication files and targeted git status/diff; confirm no
unrelated dirty files were staged/reset. Review transport leaks, provenance loss and false
success claims. README states actual exported source data, adapter opt-in, runtime permissions,
model untouched, World Model not mounted, source deadlines, fallback, semantic/null metadata
changes and hybrid-vs-live distinction. Update decisions/insights from real failures. A fresh
reviewer checks the complete M1 branch after native execution, or task plus whole-branch
reviews under subagent execution. No commit/push without separate user authorisation.

---

## Coverage and explicit follow-on contracts

| Parent spec requirement | M1 owner / handoff |
|---|---|
| §§1–3 existing entry point, fixture-first and true runtime impact | Tasks 3,4,6 |
| §4 read-only transport/publication and supported predicate semantics | Tasks 1,2,3,5 |
| §4 complete immutable snapshots, bounds, errors and honest fallback | Tasks 1–4 |
| §4 declaration completeness / unknown absence | **M2**; M1 does not remotely replace IaC, and cannot claim that absent-source bug is fixed |
| §5 persistent World Model and shared context | **M3**; M1 supplies immutable source metadata/rule lineage, not store/ingest/context conformance |
| §6 Nemotron structured generation and provider observability | **M4**; current model, silent-fallback and one-second timeout-floor issues are not claimed fixed by M1 |
| §7 shared budget, new source cancellation, retry/degradation | Tasks 2–4 for policy; M4 for model changes |
| §8 offline/parity/security/evidence/packaging | Task 6 for M1; M5 for the combined sponsor stack |
| §9 no scope expansion, truthful build-window attribution | Global constraints and all task handoffs |
| §10 eligibility and access unknowns | Execution gates and Task 5; stop/report unresolved claims |

## Self-review and handoff status

- Interface ownership mapped before task decomposition; all new files are explicitly proposed.
- Task 2 reader uses `_read_worker_result(path, expected_responses)` consistently and reserves
  termination/reaping time inside the operation cutoff.
- Live file registration, runtime user creation and token handoff are executable decision gates,
  not facts inferred from the administrator deployment test. No invented admin API endpoint.
- Scope version/hash pinned; provider/backend distinct; fallback clears remote lineage; deadline
  never serialized into snapshot identity. No extra object/DDL privileges in the runtime worker.
- Five Review Focus cases assigned to concrete tests. Remaining Option B requirements assigned
  to M2–M5 rather than omitted or misreported as M1-complete.
- This plan awaits builder review and execution-method selection. No product work or cloud
  mutations are authorised merely by this plan existing, and no pre-window implementation is
  recommended.

**Recommended execution method:** Native agent execution, followed by one fresh independent
whole-branch review. Genuine Cursor development is a separate prerequisite: first establish a
personal Cursor work surface and how the selected execution workflow will use it and retain
evidence. Selecting Native here does not transform this Hermes session into Cursor or satisfy
that requirement. These tasks share validation,
metadata and deadline interfaces, so keeping implementation context together avoids repeated
handoff cost; security/behaviour tests plus the independent final review remain mandatory.
Subagent-driven task/reviewer pairs are the more review-intensive alternative if preferred.
