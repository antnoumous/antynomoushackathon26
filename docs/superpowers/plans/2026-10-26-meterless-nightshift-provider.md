# Meterless Nightshift Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route optional model generation through real Meterless Nightshift, with bounded calls, validated structured output and truthful fallback accounting.

**Architecture:** A dedicated provider adapter implements the existing Generator contract. Explicit provider selection retains the sample-mode rules override. A parent-supervised transport prevents slow HTTP bodies from outliving the audit budget; metadata is finalised after the Writer's last generation call.

**Tech Stack:** Python 3.11+, existing requests/Pydantic/pytest, standard-library multiprocessing and HTTP test server. No new production dependencies.

**Spec:** `docs/superpowers/specs/2026-10-26-meterless-split-deployment-design.md`, approved 26 October. Read it in full.

## Global Constraints

- Preserve the sample run as CPU-only, offline, deterministic and dependency-light.
- No new OCI instances, GPUs, disks, snapshots, paid subscriptions, cloud-model purchases or hardware resizing.
- No employer resources or employer data. No credentials on the Windows work machine.
- Audit calls: 60-second per-call maximum, shortened to the remaining absolute deadline; preserve 300/540-second run caps.
- Nightshift base: Mac `http://127.0.0.1:8088/v1`, OCI tunnel `http://127.0.0.1:18088/v1`; selected route `meterless/local` must actually be discovered.
- Headers: real bearer token, `meterless-app: driftwatch` for every request, `meterless-scope: user` for chat requests.
- Never print/log token values, response bodies, raw HTTP exceptions or request headers. No cloud keys or cloud relay.
- No app/model installation, remote write, public port, push or submission in this code milestone.
- Use `.venv/bin/python`; keep pre-existing dirty work untouched; commit exact named paths only.
- Code snippets below are planned implementation/tests, not claims about existing code or execution.

## Review Focus

1. A response with `confidence=true`, NaN, a JSON list or missing keys is invalid, not a successful structured generation (Task 3).
2. A server that sends bytes slowly must be stopped at the parent's deadline even if requests' read timeout keeps resetting (Task 2).
3. A failure in Writer's final summary call must appear in the report and final state event, not be missed by an earlier metadata snapshot (Task 4).
4. A redirect or exception must not leak the token to another host or to logs, including process-start failures (Tasks 1–2).
5. Zero attempts, a health-only endpoint or a replayed success from an earlier run must not pass sponsor acceptance (Tasks 1, 4–5).

## Files and owned interfaces

Create `app/providers/{__init__,meterless_settings,meterless_transport,meterless}.py` and
`app/generation_status.py`. Modify `app/generator.py`, `app/config.py`, `app/agents/writer.py`,
`app/loop.py`, `.env.example`. Extend `tests/test_generator.py`, `tests/test_writer.py`,
`tests/test_loop.py`; create `tests/test_meterless_settings.py`, `test_meterless_transport.py`,
`test_meterless_generator.py`, `test_generation_status.py`, `test_meterless_acceptance.py`.
Create `scripts/verify_meterless_sponsors.py` and `docs/meterless-nightshift.md`.

This adapter milestone is independently testable without the World Model or a real Nightshift app.
Combined acceptance in Task 5 requires the completed World Model plan. Do not edit World Model
interfaces concurrently; execute the two code plans sequentially on the same reviewed branch.

For each new behaviour, write its failing test first, observe RED, implement the minimum slice,
observe GREEN, then refactor. No network/service response in this plan is evidence of a real run.

### Task 1: Secret-safe settings and authenticated discovery

**Files:** `app/providers/__init__.py`, `meterless_settings.py`, `tests/test_meterless_settings.py`.

**Interfaces:**

```python
@dataclass(frozen=True)
class MeterlessReadiness:
    state: str  # online/unauthorized/offline/unsupported_mode
    model_ids: tuple[str, ...]

class MeterlessError(Exception):
    category: str  # configuration/unauthorized/offline/unsupported_mode/timeout/schema/transport
    def __init__(self, category: str) -> None: ...

class MeterlessSettings(BaseModel):
    base_url: str
    token: SecretStr
    model: str = "meterless/local"
    app_id: str = "driftwatch"
    timeout_s: float = 60.0

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "MeterlessSettings": ...

def normalize_base_url(value: str) -> str: ...
def discover(settings: MeterlessSettings, *, transport: Callable,
             timeout_s: float) -> MeterlessReadiness: ...
```

`transport(method, url, *, headers, payload, timeout_s) -> dict` is the exact transport injection
contract shared with Task 2; it returns parsed JSON or raises classified `MeterlessError`.
Settings read only `METERLESS_BASE_URL`, `METERLESS_TOKEN`, `METERLESS_MODEL`, with the base/model
defaults above. Token is required for readiness; blank/`rt-local` is a configuration failure.

- [ ] **Step 1 — RED→GREEN for URL normalisation and unsafe inputs.**

```python
import pytest
from app.providers.meterless_settings import normalize_base_url, MeterlessError

@pytest.mark.parametrize("value", [
    "127.0.0.1:8088", "http://127.0.0.1:8088/v1/",
    "http://127.0.0.1:8088/v1/models",
    "http://127.0.0.1:8088/v1/chat/completions",
    "http://127.0.0.1:8088/healthz",
])
def test_url_is_normalized_once(value):
    assert normalize_base_url(value) == "http://127.0.0.1:8088/v1"

@pytest.mark.parametrize("value", [
    "file:///etc/passwd", "http://user:secret@localhost:8088/v1",
    "http://localhost:8088/v1?token=secret", "http://localhost:8088/v1/v1",
])
def test_unsafe_url_is_rejected_without_echoing_input(value):
    with pytest.raises(MeterlessError) as caught:
        normalize_base_url(value)
    assert caught.value.category == "configuration"
    assert "secret" not in str(caught.value)
```

Use `urllib.parse`; permit http/https, strip only documented suffixes and reject query, fragment,
userinfo, control characters and unexpected paths. Preserve host/port correctness, including IPv6.
Do not silently repair duplicate `/v1` segments. Never include the original unsafe string in errors.

- [ ] **Step 2 — RED→GREEN for readiness using a complete deterministic transport fake.**

```python
def test_discovery_requires_meterless_ids_and_authorization():
    from app.providers.meterless_settings import MeterlessSettings, discover
    settings = MeterlessSettings(base_url="http://127.0.0.1:8088/v1", token="unit-test-only")
    seen = []
    def transport(method, url, *, headers, payload, timeout_s):
        seen.append((method, url, headers, timeout_s))
        return {"data": [{"id": "meterless/local"}, {"id": "meterless/new-mode"}]}
    result = discover(settings, transport=transport, timeout_s=2)
    assert result.state == "online"
    assert result.model_ids == ("meterless/local", "meterless/new-mode")
    assert seen[0][0:2] == ("GET", "http://127.0.0.1:8088/v1/models")
    assert seen[0][2]["meterless-app"] == "driftwatch"
    assert seen[0][2]["Authorization"] == "Bearer unit-test-only"
```

Add vertical cases for unauthorized transport classification, only `healthz` answering, malformed
model list, a list without `meterless/local`, and unknown `meterless/*` IDs that must be retained.
Use `SecretStr`, sanitised exceptions and repr tests to prove settings/error output does not expose
the test sentinel. A successful process-health probe alone cannot report online.

- [ ] **Step 3 — run the module/full suite and commit exact settings files.**

```bash
.venv/bin/python -m pytest tests/test_meterless_settings.py -q
.venv/bin/python -m pytest -q
git add app/providers/__init__.py app/providers/meterless_settings.py tests/test_meterless_settings.py
git commit -m "feat(meterless): secret-safe runtime settings and authenticated discovery"
```

### Task 2: Parent-supervised, deadline-bound HTTP transport

**Files:** `app/providers/meterless_transport.py`, `tests/test_meterless_transport.py`.

**Interfaces:**

```python
def request_json(method: str, url: str, *, headers: dict[str, str],
                 payload: dict | None, timeout_s: float,
                 max_response_bytes: int = 1024*1024) -> dict: ...
```

The actual worker is a module-level function, uses requests with redirects disabled and streams a
bounded body. The parent supervises a spawned process using an absolute monotonic deadline, a
bounded response pipe and unconditional terminate/join/kill cleanup. Follow the proven structure in
`app/sources/zetaris_http.py`; do not refactor its public contract or share its sponsor-specific SQL
settings. Load the TDD skill's Python timing/concurrency pitfalls reference before implementing.

- [ ] **Step 1 — RED→GREEN using a real local HTTP server for success/auth/schema/body size.**
Write the first real-HTTP test and fixture as follows, observe RED, then implement only the bounded
success/auth path before adding the remaining routes:

```python
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from app.providers.meterless_transport import request_json
from app.providers.meterless_settings import MeterlessError

@pytest.fixture
def runtime_server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.headers.get("Authorization") != "Bearer unit-http-only":
                self.send_response(401)
                self.end_headers()
                return
            body = json.dumps({"data": [{"id": "meterless/local"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            if self.path != "/drip":
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                if self.path == "/drip":
                    for _ in range(300):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        time.sleep(0.05)
                else:
                    self.wfile.write(body)
            except OSError:
                pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def test_real_http_discovery_and_wrong_token(runtime_server):
    result = request_json("GET", runtime_server + "/v1/models",
        headers={"Authorization": "Bearer unit-http-only"}, payload=None, timeout_s=3)
    assert result == {"data": [{"id": "meterless/local"}]}
    with pytest.raises(MeterlessError) as caught:
        request_json("GET", runtime_server + "/v1/models",
            headers={"Authorization": "Bearer wrong-unit-token"}, payload=None, timeout_s=3)
    assert caught.value.category == "unauthorized"
```

Extend the handler with 403, 500, invalid JSON, a JSON list and an over-limit body one RED/GREEN
slice at a time; no raw response or token may appear in `str(error)`/captured output. Each response
has valid framing so an accidental truncated HTTP body cannot masquerade as the branch under test.

- [ ] **Step 2 — RED→GREEN for slow bodies and expired time.** The handler's `/drip` sends small
chunks periodically for longer than the test's total budget while keeping individual reads active.
Verify the parent stops it at the declared budget with an explicit scheduler tolerance, returns a
classified timeout and leaves no new child process:

```python
import multiprocessing

def test_slow_body_cannot_extend_total_budget(runtime_server):
    before = {p.pid for p in multiprocessing.active_children()}
    started = time.monotonic()
    with pytest.raises(MeterlessError) as caught:
        request_json("GET", runtime_server + "/drip",
            headers={"Authorization": "Bearer unit-http-only"}, payload=None, timeout_s=0.75)
    assert caught.value.category == "timeout"
    assert time.monotonic() - started < 3.5  # 0.75s budget plus spawn/scheduler/cleanup tolerance
    assert {p.pid for p in multiprocessing.active_children()} <= before
```

Also use a controllable fake monotonic clock/process factory to prove an expired budget starts no
worker and that the remaining budget shrinks at every wait. Never simulate success by directly
setting final counters.

- [ ] **Step 3 — RED→GREEN for redirect and start-failure safety.** Point a 302 at another local
server; assert that server receives no request or bearer header. Make the process factory's
`start()` raise an exception containing the test token: the caller receives only a classified
transport failure, with no leaked token and no unjoined partial child. Test response size overflow
before decoding and missing/closed pipe. All cleanup paths have bounded joins.
- [ ] **Step 4 — run targeted/full suites and path-scoped commit.** Use actual spawn on macOS,
not fork. Record real wall-clock boundary tests separately from fake-clock branches. Never assert
Linux-only child behaviour as a Mac result.

### Task 3: Structured Meterless generator and explicit provider selection

**Files:** `app/providers/meterless.py`, `app/generation_status.py`, `app/generator.py`,
`app/config.py`, `.env.example`, `tests/test_meterless_generator.py`,
`tests/test_generation_status.py`, `tests/test_generator.py`, `tests/test_config.py`.

**Interfaces:**

```python
@dataclass(frozen=True)
class GenerationOutcome:
    schema_name: str
    configured_provider: str
    actual_backend: str  # meterless/openai-compatible/rules
    model: str | None
    attempted: bool
    fallback: bool
    category: str | None
    latency_s: float

class GenerationRecorder:
    def __init__(self, configured_provider: str) -> None: ...
    def record(self, outcome: GenerationOutcome) -> None: ...
    def summary(self) -> dict: ...
    def outcomes(self) -> tuple[GenerationOutcome, ...]: ...

class MeterlessGenerator:
    def __init__(self, settings: MeterlessSettings | None, *,
                 transport=request_json, recorder: GenerationRecorder | None = None,
                 configuration_error: str | None = None): ...
    def set_deadline(self, deadline: float | None) -> None: ...
    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict: ...
    def diagnostics(self) -> dict: ...

def generator_diagnostics(generator: object) -> dict: ...
```

Keep `RulesGenerator`/`ModelGenerator` concrete selection compatibility with existing tests. Add
diagnostics support to the project's generators; `generator_diagnostics` returns explicitly
unverified/unknown information for a third-party test double without diagnostics, never a fabricated
successful Meterless run. `get_generator` remains the one production selection point.

- [ ] **Step 1 — RED: a schema-valid call records a real attempt and correct headers.**

```python
def test_meterless_call_uses_local_route_and_records_success():
    from app.providers.meterless import MeterlessGenerator
    from app.providers.meterless_settings import MeterlessSettings
    seen = []
    def transport(method, url, *, headers, payload, timeout_s):
        seen.append((method, url, headers, payload, timeout_s))
        return {"choices": [{"message": {"content": '{"reason":"duty cycle","confidence":0.8}'}}]}
    gen = MeterlessGenerator(MeterlessSettings(base_url="http://127.0.0.1:8088/v1", token="unit-only"),
                            transport=transport)
    out = gen.complete(prompt="", schema={"name":"verdict_reason"},
                       context={"reason_key":"frequency_mismatch"})
    assert out["reason"] == "duty cycle"
    assert seen[0][2]["meterless-scope"] == "user"
    assert seen[0][3]["model"] == "meterless/local"
    assert gen.diagnostics()["attempts"] == 1
    assert gen.diagnostics()["successes"] == 1
    assert gen.diagnostics()["fallbacks"] == 0
```

After RED, implement prompt/schema rendering using `ModelGenerator.SCHEMAS`. The model call returns
only validated JSON of the matching schema. Use existing RulesGenerator for a fallback result and
record it explicitly. Move shared schema rendering/validation into named helpers inside generator.py
only if needed; do not duplicate rules or financial calculations in the provider adapter.

- [ ] **Step 2 — RED→GREEN for schema/type failures.** Parameterise model content as JSON list,
`null`, missing confidence, confidence `true`, string confidence, NaN, values outside [0,1], non-string
claim/reason/summary and unknown schema name. Known schema + bad output falls back and increments
fallback counters; unknown schema is a programming error and raises without pretending provider
failure. Use real fallback-required context so a malformed fake cannot hide a `KeyError`.
- [ ] **Step 3 — RED→GREEN for exact budgets and no automatic POST retries.** When no time remains,
start no request and record a non-attempted timeout/fallback. Otherwise pass
`min(60.0, deadline - monotonic())`, never clamp a negative remaining time to a fresh second. A
transport failure produces exactly one POST attempt; no internal retry or cloud route substitution.
Count configured/actual backend separately and emit only bounded diagnostic fields.
- [ ] **Step 4 — RED→GREEN for provider registry and hostile sample settings.**

```python
def test_sample_ignores_even_invalid_remote_provider_configuration(monkeypatch):
    from app.config import RunConfig
    from app.generator import RulesGenerator, get_generator
    monkeypatch.setenv("LLM_PROVIDER", "not-a-provider")
    monkeypatch.setenv("METERLESS_BASE_URL", "file:///wrong")
    monkeypatch.setenv("METERLESS_TOKEN", "rt-local")
    assert isinstance(get_generator(RunConfig(sample_mode=True)), RulesGenerator)
```

Non-sample `LLM_PROVIDER` accepts exactly rules/openai-compatible/meterless, defaulting to the
existing compatible behaviour. Explicit Meterless selection without valid settings uses a classified
unavailable Meterless generator whose future rules fallbacks stay visible; it must not silently
select OpenAI. Preserve the existing tests that instantiate default ModelGenerator and live-without-
key RulesGenerator. Add config/env examples for `METERLESS_BASE_URL`, `METERLESS_TOKEN` and
`METERLESS_MODEL`; leave actual secrets blank and sample mode true. Remove no unrelated provider
settings in this change.
- [ ] **Step 5 — recorder boundary tests and commit.** Zero attempts => `not_used`, no success ratio.
Require consistency between outcome rows and counts, finite latencies, per-instance isolation and
no token in summaries/repr. New run/new generator has no inherited success. Run provider modules,
existing generator/config tests and full suite before the exact-path commit.

### Task 4: Trace/report accounting including the Writer's last call

**Files:** `app/agents/writer.py`, `app/loop.py`, `app/generator.py`,
`tests/test_writer.py`, `tests/test_loop.py`, `tests/test_generation_status.py`.

**Interfaces:** Existing `Generator.complete` return dictionaries stay unchanged. Report metadata uses
`summary.integrations.meterless_nightshift`; World Model metadata, when available, uses its separately
owned `summary.integrations.meterless_world_model`. The two milestones must not overwrite each other.

- [ ] **Step 1 — RED: only the final run-summary generation fails.** Use a real fixture loop and a
generator/transport whose finding/reason schemas succeed with RulesGenerator-produced valid text,
but whose `run_summary` transport raises a classified timeout. Assert the report is partial, its
provider summary counts the final fallback, the last state `report.status` is partial and its final
trace action remains `synthesise`. Repeat with a cap: overall status remains capped while provider
partial/fallback information remains visible. This prevents a success snapshot taken too early.
Use the following first failing integration test; extend it with the cap and persisted-state checks
in separate RED/GREEN slices:

```python
import json
from tests.test_loop import build
from app.generator import RulesGenerator
from app.loop import Orchestrator
from app.providers.meterless import MeterlessGenerator
from app.providers.meterless_settings import MeterlessSettings, MeterlessError

def test_summary_fallback_is_not_missed(tmp_path):
    cfg, ctx = build(tmp_path)
    rules = RulesGenerator()
    def transport(method, url, *, headers, payload, timeout_s):
        system = payload["messages"][0]["content"]
        name = ("run_summary" if '"summary"' in system else
                "finding_claim" if '"claim"' in system else "verdict_reason")
        if name == "run_summary":
            raise MeterlessError("timeout")
        user = payload["messages"][1]["content"]
        context = json.loads(user[user.index("{"):])
        result = rules.complete(prompt="", schema={"name":name}, context=context)
        return {"choices":[{"message":{"content":json.dumps(result)}}]}
    ctx.generator = MeterlessGenerator(MeterlessSettings(
        base_url="http://127.0.0.1:8088/v1", token="unit-final-call"), transport=transport)
    report = Orchestrator(ctx).run()
    assert report.status == "partial"
    assert report.summary["integrations"]["meterless_nightshift"]["fallbacks"] >= 1
    events = [json.loads(line) for line in ctx.trace.path.read_text().splitlines()]
    assert events[-1]["action"] == "synthesise"
    ctx.trace.close()
    ctx.state.close()
```

Use the actual renderer's JSON schema in the system message and actual context in the user message;
if the rendering helper changes its format, update the test's extraction helper to parse that
published contract, not to insert an unrelated prewritten response. The fake proves accounting only,
not a successful Nightshift call. Add a check that context/manifest numeric IDs do not widen the
Writer's allowed-figures set. `GenerationRecorder.summary` returns `configured_provider`, `attempts`,
`successes`, `fallbacks`, `status`, `models` and per-schema counts under `schemas`. Zero remote
attempts must remain `not_used`; configuration-driven rules fallbacks can still make the overall
audit partial via their explicit fallback/error fields. Never infer a remote attempt from a rules call.

- [ ] **Step 2 — implement finalisation at the correct boundary.** In Writer.synthesise, after its
last complete/figure-check and before `_emit("synthesise")`, collect diagnostics and available world
manifest, compose integration metadata and apply status precedence `capped > partial > success`.
Use the final RunReport.status when Orchestrator appends its `report` state event, including the
early no-policy return path. Never append provider events after the final synthesize event.
- [ ] **Step 3 — add per-call observer events before finalisation.** Wire safe bounded observer
callbacks for attempts/results/fallbacks so provider diagnostics are generated when calls happen,
not reverse-engineered from output prose. The observer is optional on direct generator construction
and enabled by the normal orchestrator. Token, context body and raw exception are never event data.
Exercise RulesGenerator-only sample runs, arbitrary writer test doubles and mixed provider outcomes.
- [ ] **Step 4 — source/provider distinctions and full verification.** A successful model must not
make fixture inventory appear live; a healthy model with no policy must not produce a normal audit.
Ensure the pipeline warning about data sources remains intact. Run entrypoint, Writer, loop, trace,
state and full suites, then commit only the accounted metadata/observer changes.

### Task 5: Falsifiable combined sponsor acceptance and runtime guide

**Prerequisite:** World Model plan complete. This task does not install Nightshift or operate OCI.

**Files:** `scripts/verify_meterless_sponsors.py`, `tests/test_meterless_acceptance.py`,
`docs/meterless-nightshift.md`.

**Interfaces:**

```python
def run_acceptance(*, scenario: Path, base_settings: dict, variant_settings: dict,
                   output_dir: Path, env: dict, make_source=None,
                   make_generator=None) -> dict: ...
```

The defaults select production ZetarisPolicySource and MeterlessGenerator. Factories are injectable
for hermetic tests, not a production mode that changes the known scenario's answer. Consume existing
`validate_settings`/`build_settings` from `scripts.verify_zetaris_policy`, not a new secret-bearing
settings format. CLI options: `--scenario`, `--base-settings`, `--variant-settings`, `--output-dir`.
Refuse an existing output directory. Use fixture sources explicitly for inventory/telemetry/IaC,
real selected policy/generator adapters and the same Orchestrator/World Model. Do not relax sample
mode's provider override; this harness explicitly constructs a hybrid context and labels it hybrid.

- [ ] **Step 1 — RED→GREEN for programmatic acceptance, then false-positive probes.** Run two real
fixture loops with injected typed policy sources and a deterministic fake transport, and derive
finding deltas from produced reports. Acceptance requires world ingestion/Scout+Skeptic consumption,
matching source snapshot digests, the exact R-1-dependent semantic finding disappearing, correct
other semantic findings/impacts, successful Meterless outcomes for all three used schemas and zero
fallbacks. Compare resource/class/verdict/impact, not allocation-order evidence/candidate IDs.
- [ ] **Step 2 — prove each false-positive path fails.** Parameterise zero calls, a healthy status
without model success, missing World Model consumption, stale snapshot, no policy effect, one
summary fallback and a figure guard failure. Assert acceptance is false or the run aborts classified,
CLI exits nonzero and artifacts cannot claim sponsor success. Do not let a test stub's self-reported
`success=True` satisfy a gate; build counts from actual per-call observer records and source lineage.
- [ ] **Step 3 — artifacts and guide.** Generate a runtime manifest, source outcomes, per-schema
attempt results, context IDs/selections, semantic base/variant diff and exact report-linked traces.
Use separate raw/private and masked/public output destinations. Guide documents endpoint headers,
local mode, authentication, offline override, sample/hybrid/live labels, fallback semantics, caps,
no full World Model conformance claim, and the companion deployment runbook's installation gates.
- [ ] **Step 4 — full hermetic suite, generated-evidence consistency and commit.** Do not call a fake-
transport unit test a real Nightshift acceptance. Real installation, tunnel, generation and the live
combined test are separate deployment gates in the master runbook. Commit code/tests/guide only;
mount/verification claims remain conditional on those gates.

## Completion evidence and handoff

Record exact RED/GREEN outputs, adapter and observer tests, final suite result and commit. This
milestone proves the adapter against controlled inputs; a real runtime model response and combined
policy/engine/provider acceptance are still required. Proceed only through
`2026-10-26-meterless-split-delivery.md` for real operations and regenerated submission assets.
