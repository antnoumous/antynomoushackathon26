# Driftwatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an OCI tenancy auditor that finds cost waste and unattributed infrastructure, where a critic agent can reject a finding and force a re-investigation.

**Architecture:** A hand-rolled bounded agent loop over four `Source` adapters (inventory, telemetry, IaC, policy), behind which sit either bundled JSON fixtures or the live OCI SDK. Four agents with distinct permission sets share one append-only `RunState` and emit one JSONL trace. All arithmetic and threshold decisions are deterministic code; a single injected `Generator` supplies language judgements and falls back to a rule engine so the whole agent runs with no credentials and no network.

**Tech Stack:** Python 3.11, `pydantic` v2 (models and validation), `fastapi` + `uvicorn` (`POST /run`), `oci` SDK (live path only, imported lazily), `pytest` (tests). No orchestration framework. No UI.

**Spec:** `docs/superpowers/specs/2026-09-24-oci-tenancy-auditor-design.md`

## Global Constraints

- Python **3.11** (the session interpreter). No 3.12+ syntax.
- **CPU only.** No GPU, no local model weights, no runtime downloads of models or datasets.
- **Nothing installs after the app starts.** All dependencies frozen in `requirements.txt` and installed in the image at build time.
- `POST /run` binds **`0.0.0.0`** inside the container, never `127.0.0.1`.
- **Credentials from environment variables only.** `.env` is gitignored; `.env.example` carries placeholders only. No secret, API key, real OCID or employer artifact in any committed file, log, example or video.
- **`SAMPLE_MODE=true` makes no network calls and requires no credentials** — this is enforced by a test that monkeypatches `socket.socket` to raise.
- Trace JSONL goes to **stdout and** `logs/trace-<run_id>.jsonl`; state JSONL to `logs/state-<run_id>.jsonl`. They are different files.
- Every trace line carries: `timestamp`, `run_id`, `agent_name`, `action`, `input_summary`, `output_summary`, `target_agent`, `confidence`, `retry_count`, `status`, plus `round` and `evidence_refs`.
- Caps (verbatim from the spec, §5.9): `MAX_ROUNDS=3`, `MAX_RESOURCES=25`, `MAX_RECHECKS_PER_FINDING=2`, wall clock soft `300` s / hard `540` s, partner/source call timeout `10–30` s, model call timeout `30–90` s, agent iteration `1–3` min. Every cap that fires emits `status: "capped"` — silent truncation is a bug.
- Runtime status is one of `success`, `partial`, `capped`. Mode is `sample` or `live`. Both always present in the report.
- Report figures are produced by code, never by a model. No model output is ever parsed for a number that reaches the report.
- No hardcoded outputs, no input→output mapping, no demo-only branch, no hand-written or edited trace.

## Review Focus

Failure modes a reasonable user would not expect, each pinned by a test in the owning task:

1. **A finding is raised on an incomplete metric window.** `telemetry` returns less history than requested; the resource must land in `undetermined`, never in `findings`. (Task 5, Task 9)
2. **A model returns prose where a number is expected, and the number reaches the report.** The Writer must refuse to state any figure absent from the ledger, and the report must fail closed. (Task 10)
3. **A resource matches IaC only by fuzzy name.** The match is inferred, not declared, so confidence drops and the match rule is recorded — it must not read as a declared match. (Task 5)
4. **A source times out or raises mid-run.** The run must degrade to fixtures, log the degradation, and still finish — or finish `partial`, naming the unavailable source. It must never produce a short report that looks complete. (Task 4, Task 11)
5. **A cap fires silently.** Hitting `MAX_ROUNDS` or the wall clock must set `status: "capped"` and record which cap fired; a truncated investigation must not read as a finished one. (Task 11)

---

## File Structure

| Path | Responsibility |
|---|---|
| `app/config.py` | `RunConfig`: defaults, env merge, request override, cap arithmetic |
| `app/models.py` | Every pydantic model: resources, series, declarations, rules, evidence, findings, report |
| `app/evidence.py` | `EvidenceLedger`: allocates stable `E-nnn` ids, resolves refs, rejects dangling ones |
| `app/state.py` | `RunState`: append-only JSONL at `logs/state-<run_id>.jsonl` |
| `app/trace.py` | `Tracer`: JSONL to stdout and `logs/trace-<run_id>.jsonl`, one line per agent action |
| `app/generator.py` | `Generator` protocol, `ModelGenerator`, `RulesGenerator` |
| `app/sources/base.py` | `Source` protocol, `Scope`, `SourceResult`, `SourceError` |
| `app/sources/*_fixture.py` | One fixture backend per source |
| `app/sources/oci_*.py` | Live backends (stretch, Task 15) |
| `app/analysis.py` | Deterministic cost, coverage, distribution, tag and IaC-match logic |
| `app/agents/base.py` | `Agent` base, `AgentContext` |
| `app/agents/{planner,scout,skeptic,writer}.py` | One agent per file, one permission set each |
| `app/loop.py` | Bounded orchestrator, cap enforcement, termination |
| `app/report.py` | `report.json` and `report.md` rendering |
| `app/api.py` | FastAPI app exposing `POST /run` |
| `run.py` | CLI entry point; same pipeline as the API |
| `evals/run_eval.py` | Precision/recall and verdict accuracy against ground truth |
| `scripts/make_scenario.py` | Held-out scenario + ground truth generator (stretch, Task 16) |
| `scripts/mask_ocids.py` | Masks OCIDs in fixtures and examples before commit |

---

### Task 1: Skeleton, dependencies, and configuration

**Files:**
- Create: `requirements.txt`, `.env.example`, `app/__init__.py`, `app/config.py`, `tests/__init__.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `RunConfig` (pydantic model) with fields `run_id: str`, `objective: str`, `compartment_ids: list[str]`, `resource_types: list[str]`, `lookback_hours: int`, `resolution_minutes: int`, `max_rounds: int`, `max_resources: int`, `max_rechecks_per_finding: int`, `wall_clock_soft_s: int`, `wall_clock_hard_s: int`, `sample_mode: bool`, `model: str | None`, `logs_dir: Path`. Plus `RunConfig.from_env_and_request(request: dict) -> RunConfig`.

- [ ] **Step 1: Create `requirements.txt`**

```text
pydantic==2.9.2
fastapi==0.115.0
uvicorn==0.31.0
oci==2.135.0
requests==2.32.3
httpx==0.27.2
pytest==8.3.3
```

`httpx` is required by `fastapi.testclient`, so the API tests run from a clean clone. `oci` is
installed in the image but only imported lazily by the live adapters, so sample mode never
touches it.

- [ ] **Step 2: Create `.env.example`**

```dotenv
# Copy to .env and fill in your own values. .env is gitignored and must never be committed.
# Every value below is a placeholder. Nothing here is a real credential.

# --- Model provider (only needed for a live run; SAMPLE_MODE=true needs none) ---
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://api.example-provider.com/v1
LLM_API_KEY=replace-me
LLM_MODEL=replace-me
LLM_MODEL_STRONG=replace-me

# --- OCI (only needed for a live run; never commit real values) ---
OCI_CONFIG_FILE=~/.oci/config
OCI_PROFILE=DEFAULT
OCI_REGION=ap-singapore-1
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..replace-me

# --- Run behaviour ---
SAMPLE_MODE=true
LOGS_DIR=logs
```

- [ ] **Step 3: Write the failing config test**

```python
# tests/test_config.py
import os
import pytest
from app.config import RunConfig


def test_defaults_are_the_spec_caps():
    cfg = RunConfig.from_env_and_request({})
    assert cfg.max_rounds == 3
    assert cfg.max_resources == 25
    assert cfg.max_rechecks_per_finding == 2
    assert cfg.wall_clock_soft_s == 300
    assert cfg.wall_clock_hard_s == 540
    assert cfg.lookback_hours == 168


def test_env_sample_mode_wins_over_request(monkeypatch):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    cfg = RunConfig.from_env_and_request({"sample_mode": False})
    assert cfg.sample_mode is True


def test_request_may_lower_a_cap_but_not_raise_it(monkeypatch):
    cfg = RunConfig.from_env_and_request({"caps": {"max_rounds": 1}})
    assert cfg.max_rounds == 1
    with pytest.raises(ValueError):
        RunConfig.from_env_and_request({"caps": {"max_rounds": 99}})


def test_run_id_is_generated_and_filesystem_safe():
    cfg = RunConfig.from_env_and_request({})
    assert cfg.run_id
    assert all(c.isalnum() or c in "-_" for c in cfg.run_id)
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 5: Implement `app/config.py`**

```python
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

HARD_LIMITS = {
    "max_rounds": 3,
    "max_resources": 25,
    "max_rechecks_per_finding": 2,
    "wall_clock_soft_s": 300,
    "wall_clock_hard_s": 540,
}


def _new_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class RunConfig(BaseModel):
    run_id: str = Field(default_factory=_new_run_id)
    objective: str = "audit this tenancy for cost waste and unattributed resources"
    compartment_ids: list[str] = Field(default_factory=list)
    resource_types: list[str] = Field(
        default_factory=lambda: ["compute_instance", "block_volume", "reserved_public_ip"]
    )
    lookback_hours: int = 168
    resolution_minutes: int = 5
    max_rounds: int = HARD_LIMITS["max_rounds"]
    max_resources: int = HARD_LIMITS["max_resources"]
    max_rechecks_per_finding: int = HARD_LIMITS["max_rechecks_per_finding"]
    wall_clock_soft_s: int = HARD_LIMITS["wall_clock_soft_s"]
    wall_clock_hard_s: int = HARD_LIMITS["wall_clock_hard_s"]
    sample_mode: bool = False
    model: str | None = None
    logs_dir: Path = Path("logs")

    @classmethod
    def from_env_and_request(cls, request: dict) -> "RunConfig":
        req = dict(request or {})
        scope = dict(req.get("scope") or {})
        tele = dict(req.get("telemetry") or {})
        caps = dict(req.get("caps") or {})

        for key, value in caps.items():
            if key not in HARD_LIMITS:
                raise ValueError(f"unknown cap {key!r}")
            if int(value) > HARD_LIMITS[key]:
                raise ValueError(f"cap {key} may be lowered but not raised (hard limit {HARD_LIMITS[key]})")

        sample_env = os.environ.get("SAMPLE_MODE", "").strip().lower() in {"1", "true", "yes"}
        cfg = cls(
            objective=req.get("objective") or cls.model_fields["objective"].default,
            compartment_ids=list(scope.get("compartment_ids") or []),
            resource_types=list(scope.get("resource_types") or cls.model_fields["resource_types"].default_factory()),
            lookback_hours=int(tele.get("lookback_hours", 168)),
            resolution_minutes=int(tele.get("resolution_minutes", 5)),
            sample_mode=sample_env or bool(req.get("sample_mode")),
            model=os.environ.get("LLM_MODEL"),
            logs_dir=Path(os.environ.get("LOGS_DIR", "logs")),
        )
        merged = cfg.model_dump() | {"caps": {}}
        for key in HARD_LIMITS:
            merged[key] = min(int(caps.get(key, HARD_LIMITS[key])), HARD_LIMITS[key])
        cfg = cls(**{**merged, "run_id": _new_run_id()})
        if not re.fullmatch(r"[A-Za-z0-9_-]+", cfg.run_id):
            raise ValueError("run_id must be filename safe")
        return cfg
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example app/ tests/
git commit -m "feat: project skeleton, dependency pins and RunConfig with spec caps"
```

---

### Task 2: Domain models and the evidence ledger

**Files:**
- Create: `app/models.py`, `app/evidence.py`, `tests/test_models.py`, `tests/test_evidence.py`

**Interfaces:**
- Consumes: `app.config.RunConfig`.
- Produces: `Resource`, `MetricPoint`, `MetricSeries`, `IaCDeclaration`, `PolicyRule`, `Evidence`, `VerdictRecord`, `Finding`, `Undetermined`, `RunReport` (all pydantic models in `app/models.py`, serialising the spec's `class` key via alias); `EvidenceLedger` with `add(source, kind, resource_id, summary, payload) -> Evidence` and `resolve(refs: list[str]) -> list[Evidence]` raising `DanglingEvidenceError` on an unknown ref.

- [ ] **Step 1: Write the failing model tests**

```python
# tests/test_models.py
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.models import Finding, MetricSeries, Resource


def test_resource_rejects_unknown_class():
    with pytest.raises(ValidationError):
        Resource(resource_id="ocid1.instance.oc1..aaaa", resource_class="kubernetes_cluster",
                 display_name="x", compartment_id="c1", lifecycle_state="RUNNING",
                 time_created=datetime.now(timezone.utc), tags={})


def test_metric_series_reports_coverage():
    s = MetricSeries(resource_id="r1", metric="CpuUtilization", lookback_hours=168,
                     resolution_minutes=5, coverage_hours=168.0, sufficient=True,
                     points=[{"ts": datetime.now(timezone.utc), "value": 0.5}])
    assert s.coverage_hours == 168.0
    assert s.sufficient is True


def test_finding_serialises_class_alias():
    f = Finding(finding_id="F-001", resource_id="r1", resource_class="compute_instance",
                finding_class="cost_waste", claim="idle", evidence_refs=["E-001"],
                impact={"kind": "usd_per_month", "value": 8.94}, confidence=0.7,
                status="accepted", falsifier="a documented scheduled job", history=[])
    payload = f.model_dump(by_alias=True)
    assert payload["class"] == "cost_waste"
    assert "finding_class" not in payload


def test_finding_rejects_unknown_status():
    with pytest.raises(ValidationError):
        Finding(finding_id="F-001", resource_id="r1", resource_class="compute_instance",
                finding_class="cost_waste", claim="idle", evidence_refs=[], impact={},
                confidence=0.7, status="maybe", falsifier="", history=[])
```

```python
# tests/test_evidence.py
import pytest
from app.evidence import EvidenceLedger, DanglingEvidenceError


def test_ids_are_sequential_and_stable():
    ledger = EvidenceLedger()
    first = ledger.add(source="telemetry", kind="cpu_stats", resource_id="r1",
                       summary="mean 0.8%", payload={"mean": 0.8})
    second = ledger.add(source="policy", kind="rule_hit", resource_id="r1",
                        summary="rule R-3", payload={"rule_id": "R-3"})
    assert first.evidence_id == "E-001"
    assert second.evidence_id == "E-002"
    assert ledger.resolve(["E-001"])[0].payload == {"mean": 0.8}


def test_dangling_ref_is_an_error_not_a_silent_skip():
    ledger = EvidenceLedger()
    ledger.add(source="telemetry", kind="cpu_stats", resource_id="r1", summary="x", payload={})
    with pytest.raises(DanglingEvidenceError):
        ledger.resolve(["E-001", "E-999"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_models.py tests/test_evidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: Implement `app/models.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ResourceClass = Literal["compute_instance", "block_volume", "reserved_public_ip"]
FindingClass = Literal["cost_waste", "unattributed"]
RunStatus = Literal["success", "partial", "capped"]
FindingStatus = Literal["accepted", "rejected", "revised"]
Verdict = Literal["accept", "reject", "recheck"]


class Resource(BaseModel):
    resource_id: str
    resource_class: ResourceClass
    display_name: str
    compartment_id: str
    lifecycle_state: str
    time_created: datetime
    tags: dict[str, str] = Field(default_factory=dict)
    shape: str | None = None
    ocpus: float | None = None
    memory_gb: float | None = None
    attached: bool | None = None


class MetricPoint(BaseModel):
    ts: datetime
    value: float


class MetricSeries(BaseModel):
    resource_id: str
    metric: str
    lookback_hours: int
    resolution_minutes: int
    coverage_hours: float
    sufficient: bool
    points: list[MetricPoint] = Field(default_factory=list)
    insufficient_reason: str | None = None


class IaCDeclaration(BaseModel):
    address: str
    resource_type: str
    declared_name: str
    file_path: str
    last_commit: str
    commit_message: str
    author: str


class PolicyRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rule_id: str
    finding_class: FindingClass = Field(alias="class")
    when: dict[str, Any]
    note: str


class Evidence(BaseModel):
    evidence_id: str
    source: str
    kind: str
    resource_id: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class VerdictRecord(BaseModel):
    round: int
    verdict: Verdict
    reason: str


class Finding(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    finding_id: str
    resource_id: str
    resource_class: ResourceClass
    finding_class: FindingClass = Field(alias="class")
    claim: str
    evidence_refs: list[str]
    impact: dict[str, Any]
    confidence: float
    status: FindingStatus
    falsifier: str
    history: list[VerdictRecord] = Field(default_factory=list)


class Undetermined(BaseModel):
    resource_id: str
    reason: str


class SourceStatus(BaseModel):
    name: str
    backend: Literal["live", "fixture"]
    degraded: bool = False
    reason: str | None = None


class RunReport(BaseModel):
    run_id: str
    status: RunStatus
    mode: Literal["sample", "live"]
    sources: list[SourceStatus]
    summary: dict[str, Any]
    findings: list[Finding]
    undetermined: list[Undetermined]
    report_markdown_path: str | None = None
    trace_path: str | None = None
    caps_hit: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Implement `app/evidence.py`**

```python
from __future__ import annotations

from typing import Any

from app.models import Evidence


class DanglingEvidenceError(Exception):
    pass


class EvidenceLedger:
    """Allocates stable evidence ids. Every finding cites these; nothing else may."""

    def __init__(self) -> None:
        self._items: list[Evidence] = []

    def add(self, *, source: str, kind: str, resource_id: str, summary: str,
            payload: dict[str, Any] | None = None) -> Evidence:
        item = Evidence(
            evidence_id=f"E-{len(self._items) + 1:03d}",
            source=source,
            kind=kind,
            resource_id=resource_id,
            summary=summary,
            payload=payload or {},
        )
        self._items.append(item)
        return item

    def resolve(self, refs: list[str]) -> list[Evidence]:
        by_id = {item.evidence_id: item for item in self._items}
        missing = [ref for ref in refs if ref not in by_id]
        if missing:
            raise DanglingEvidenceError(f"unknown evidence refs: {missing}")
        return [by_id[ref] for ref in refs]

    def all(self) -> list[Evidence]:
        return list(self._items)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_models.py tests/test_evidence.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add app/models.py app/evidence.py tests/test_models.py tests/test_evidence.py
git commit -m "feat: domain models and the evidence ledger with dangling-ref detection"
```

---

### Task 3: The Source protocol and the four fixture backends

**Files:**
- Create: `app/sources/__init__.py`, `app/sources/base.py`, `app/sources/inventory_fixture.py`, `app/sources/telemetry_fixture.py`, `app/sources/iac_fixture.py`, `app/sources/policy_fixture.py`, `data/pricing.json`, `data/scenarios/example_1/inventory.json`, `data/scenarios/example_1/telemetry.json`, `data/scenarios/example_1/iac.json`, `data/scenarios/example_1/policy.json`, `tests/test_sources.py`

**Interfaces:**
- Consumes: `RunConfig`, models.
- Produces: `Scope(compartment_ids: list[str], resource_types: list[str], lookback_hours: int, resolution_minutes: int)`, `SourceResult(source: str, backend: str, degraded: bool, reason: str | None, records: list[dict])`, `Source` protocol with `name: str` and `fetch(scope: Scope) -> SourceResult`, `SourceError`, and `get_source(name: str, config: RunConfig, scenario_dir: Path | None = None) -> Source`.

- [ ] **Step 1: Create the example_1 fixture scenario**

`data/scenarios/example_1/inventory.json` — six resources carrying six distinct pathologies. OCIDs are masked.

```json
{
  "scenario_id": "example_1",
  "resources": [
    {"resource_id": "ocid1.instance.oc1..••••aaa1", "resource_class": "compute_instance",
     "display_name": "web-01", "compartment_id": "ocid1.compartment.oc1..••••lab",
     "lifecycle_state": "RUNNING", "time_created": "2026-09-02T04:10:00Z",
     "shape": "VM.Standard.A1.Flex", "ocpus": 1, "memory_gb": 6,
     "tags": {"owner": "platform", "env": "prod", "iac_address": "oci_core_instance.web_01"}},
    {"resource_id": "ocid1.instance.oc1..••••bbb2", "resource_class": "compute_instance",
     "display_name": "batch-01", "compartment_id": "ocid1.compartment.oc1..••••lab",
     "lifecycle_state": "RUNNING", "time_created": "2026-08-14T22:00:00Z",
     "shape": "VM.Standard.E4.Flex", "ocpus": 4, "memory_gb": 16,
     "tags": {"role": "batch", "schedule": "month-end", "env": "prod",
              "iac_address": "oci_core_instance.batch_01"}},
    {"resource_id": "ocid1.instance.oc1..••••ccc3", "resource_class": "compute_instance",
     "display_name": "reports-01", "compartment_id": "ocid1.compartment.oc1..••••lab",
     "lifecycle_state": "RUNNING", "time_created": "2026-07-06T09:30:00Z",
     "shape": "VM.Standard.E4.Flex", "ocpus": 2, "memory_gb": 8,
     "tags": {"env": "prod", "iac_address": "oci_core_instance.reports_01"}},
    {"resource_id": "ocid1.instance.oc1..••••ddd4", "resource_class": "compute_instance",
     "display_name": "sandbox-tmp", "compartment_id": "ocid1.compartment.oc1..••••labtest",
     "lifecycle_state": "RUNNING", "time_created": "2026-09-18T11:05:00Z",
     "shape": "VM.Standard.E2.1.Micro", "ocpus": 1, "memory_gb": 1,
     "tags": {}},
    {"resource_id": "ocid1.volume.oc1..••••eee5", "resource_class": "block_volume",
     "display_name": "vol-orphan-50g", "compartment_id": "ocid1.compartment.oc1..••••labtest",
     "lifecycle_state": "AVAILABLE", "time_created": "2026-06-01T00:00:00Z",
     "tags": {}, "attached": false},
    {"resource_id": "ocid1.publicip.oc1..••••fff6", "resource_class": "reserved_public_ip",
     "display_name": "ip-orphan", "compartment_id": "ocid1.compartment.oc1..••••labtest",
     "lifecycle_state": "AVAILABLE", "time_created": "2026-05-20T00:00:00Z",
     "tags": {}, "attached": false}
  ]
}
```

`data/scenarios/example_1/telemetry.json` — a compact spec the fixture materialises into hourly points, because the canonical false positive depends on the month-end burst falling **outside** the first lookback window and **inside** the re-check window. Points are materialised with a CRC32-seeded PRNG keyed on `resource_id`, so runs are reproducible across processes (`hash()` is salted and must not be used).

```json
{
  "scenario_id": "example_1",
  "now": "2026-09-23T04:00:00Z",
  "series": [
    {"resource_id": "ocid1.instance.oc1..••••aaa1", "metric": "CpuUtilization",
     "start": "2026-08-24T00:00:00Z", "baseline": 50.0, "jitter": 8.0, "bursts": []},
    {"resource_id": "ocid1.instance.oc1..••••bbb2", "metric": "CpuUtilization",
     "start": "2026-08-24T00:00:00Z", "baseline": 0.6, "jitter": 0.3,
     "bursts": [{"start": "2026-09-01T02:00:00Z", "hours": 3, "value": 58.0}]},
    {"resource_id": "ocid1.instance.oc1..••••ccc3", "metric": "CpuUtilization",
     "start": "2026-08-24T00:00:00Z", "baseline": 10.0, "jitter": 2.0, "bursts": []},
    {"resource_id": "ocid1.instance.oc1..••••ddd4", "metric": "CpuUtilization",
     "start": "2026-09-21T11:00:00Z", "baseline": 0.3, "jitter": 0.1, "bursts": []}
  ]
}
```

Consequences, and they are the point of the scenario: on the default 168 h lookback `batch-01` shows a peak of ≈0.9 (burst excluded) so rule R-3 fires and the Scout calls it idle; on the 744 h re-check the burst is included, peak reaches 58, R-3 stops applying and R-4 fires instead. `sandbox-tmp` starts 41 h before `now`, so its coverage ratio is 41/168 and it must land in `undetermined`.

`data/scenarios/example_1/iac.json`:

```json
{
  "scenario_id": "example_1",
  "declarations": [
    {"address": "oci_core_instance.web_01", "resource_type": "oci_core_instance",
     "declared_name": "web-01", "file_path": "terraform/compute.tf",
     "last_commit": "a1b2c3d", "commit_message": "scale web tier to 1 OCPU", "author": "me@example.com"},
    {"address": "oci_core_instance.batch_01", "resource_type": "oci_core_instance",
     "declared_name": "batch-01", "file_path": "terraform/batch.tf",
     "last_commit": "d4e5f6a", "commit_message": "month-end batch worker, runs 1st 02:00", "author": "me@example.com"},
    {"address": "oci_core_instance.reports_01", "resource_type": "oci_core_instance",
     "declared_name": "reports-01", "file_path": "terraform/reports.tf",
     "last_commit": "9f8e7d6", "commit_message": "report generator, left running intentionally", "author": "me@example.com"}
  ]
}
```

`sandbox-tmp`, `vol-orphan-50g` and `ip-orphan` are deliberately absent — that is the real drift.

`data/scenarios/example_1/policy.json`:

```json
{
  "scenario_id": "example_1",
  "rules": [
    {"rule_id": "R-1", "class": "cost_waste", "when": {"resource_class": "block_volume", "attached": false},
     "note": "detached block volume billed continuously"},
    {"rule_id": "R-2", "class": "cost_waste", "when": {"resource_class": "reserved_public_ip", "attached": false},
     "note": "reserved public IP billed whether attached or not"},
    {"rule_id": "R-3", "class": "cost_waste",
     "when": {"resource_class": "compute_instance", "mean_cpu_lt": 5.0, "min_coverage_ratio": 0.8,
              "peak_cpu_lt": 20.0},
     "note": "low mean and low peak with adequate coverage: nothing the evidence attributes a purpose to"},
    {"rule_id": "R-4", "class": "cost_waste",
     "when": {"resource_class": "compute_instance", "mean_cpu_lt": 5.0, "min_coverage_ratio": 0.8,
              "peak_cpu_gte": 20.0},
     "note": "low mean with a real peak: mis-sized, not idle"},
    {"rule_id": "R-5", "class": "unattributed", "when": {"compute_instance": true, "absent_from_iac": true},
     "note": "running but declared in no Terraform file"}
  ]
}
```

`data/pricing.json`:

```json
{
  "currency": "USD",
  "note": "OCI list rates, rounded, used for cost estimation only. Verified 2026-09.",
  "shapes": {
    "VM.Standard.A1.Flex": {"ocpu_hour": 0.01, "gb_hour": 0.0015},
    "VM.Standard.E4.Flex": {"ocpu_hour": 0.025, "gb_hour": 0.0015},
    "VM.Standard.E2.1.Micro": {"ocpu_hour": 0.0075, "gb_hour": 0.0015}
  },
  "block_volume_gb_month": 0.0255,
  "reserved_public_ip_hour": 0.01,
  "hours_per_month": 730
}
```

- [ ] **Step 2: Write the failing source tests**

```python
# tests/test_sources.py
from pathlib import Path
import pytest
from app.config import RunConfig
from app.models import MetricSeries, Resource
from app.sources import get_source
from app.sources.base import Scope

SCEN = Path("data/scenarios/example_1")


def scope(cfg):
    return Scope(compartment_ids=cfg.compartment_ids, resource_types=cfg.resource_types,
                 lookback_hours=cfg.lookback_hours, resolution_minutes=cfg.resolution_minutes)


def fixture_cfg():
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    return cfg


def test_inventory_returns_six_typed_resources():
    src = get_source("inventory", fixture_cfg(), scenario_dir=SCEN)
    result = src.fetch(scope(fixture_cfg()))
    assert result.backend == "fixture"
    assert len(result.records) == 6
    assert all(Resource(**r) for r in result.records)


def test_telemetry_marks_short_coverage_insufficient():
    src = get_source("telemetry", fixture_cfg(), scenario_dir=SCEN)
    series = [MetricSeries(**s) for s in src.fetch(scope(fixture_cfg())).records]
    sandbox = next(s for s in series if s.resource_id.endswith("ddd4"))
    assert sandbox.sufficient is False
    assert "41h of 168h" in (sandbox.insufficient_reason or "")
    assert all(s.sufficient for s in series if not s.resource_id.endswith("ddd4"))


def test_telemetry_points_are_reproducible_and_window_sensitive():
    cfg = fixture_cfg()
    src = get_source("telemetry", cfg, scenario_dir=SCEN)
    first = src.fetch(scope(cfg)).records[1]     # batch-01
    second = src.fetch(scope(cfg)).records[1]
    assert first["points"] == second["points"]   # deterministic between calls and processes

    wide = Scope(compartment_ids=[], resource_types=[], lookback_hours=744, resolution_minutes=60)
    wide_points = src.fetch(wide).records[1]["points"]
    assert max(p["value"] for p in wide_points) >= 20.0    # burst is inside the 31-day window
    assert max(p["value"] for p in first["points"]) < 20.0  # and outside the 7-day window
    assert wide_points != first["points"]


def test_iac_excludes_the_unmanaged_instance():
    src = get_source("iac", fixture_cfg(), scenario_dir=SCEN)
    addresses = {r["address"] for r in src.fetch(scope(fixture_cfg())).records}
    assert "oci_core_instance.sandbox_tmp" not in addresses
    assert len(addresses) == 3


def test_policy_loads_four_rules():
    src = get_source("policy", fixture_cfg(), scenario_dir=SCEN)
    assert {r["rule_id"] for r in src.fetch(scope(fixture_cfg())).records} == {"R-1", "R-2", "R-3", "R-4", "R-5"}


def test_unknown_source_name_is_an_error():
    with pytest.raises(KeyError):
        get_source("nonexistent", fixture_cfg(), scenario_dir=SCEN)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_sources.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.sources'`

- [ ] **Step 4: Implement `app/sources/base.py`**

```python
from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel


class SourceError(Exception):
    """Raised by a live backend when it cannot answer. Callers degrade; they never fabricate."""


MIN_COVERAGE_RATIO = 0.8
"""A metric window is sufficient only at 80% of what was requested. One constant, imported by
the sources and by the analysis, so a rule can never disagree with the data it judges."""


class Scope(BaseModel):
    compartment_ids: list[str]
    resource_types: list[str]
    lookback_hours: int
    resolution_minutes: int


class SourceResult(BaseModel):
    source: str
    backend: Literal["live", "fixture"]
    degraded: bool = False
    reason: str | None = None
    records: list[dict[str, Any]]


class Source(Protocol):
    name: str

    def fetch(self, scope: Scope) -> SourceResult: ...
```

- [ ] **Step 5: Implement the four fixture backends and the registry**

```python
# app/sources/inventory_fixture.py
from __future__ import annotations
import json
from pathlib import Path
from app.sources.base import Scope, SourceResult


class InventoryFixtureSource:
    name = "inventory"

    def __init__(self, scenario_dir: Path) -> None:
        self._path = scenario_dir / "inventory.json"

    def fetch(self, scope: Scope) -> SourceResult:
        payload = json.loads(self._path.read_text())
        records = payload["resources"]
        if scope.resource_types:
            records = [r for r in records if r["resource_class"] in scope.resource_types]
        if scope.compartment_ids:
            records = [r for r in records if r["compartment_id"] in scope.compartment_ids]
        return SourceResult(source=self.name, backend="fixture", records=records)
```

```python
# app/sources/telemetry_fixture.py
from __future__ import annotations

import json
import zlib
from datetime import datetime, timedelta
from pathlib import Path

from app.sources.base import MIN_COVERAGE_RATIO, Scope, SourceResult


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def materialise_points(spec: dict, now: datetime, lookback_hours: int) -> list[dict]:
    """Deterministic hourly points. CRC32 seeding keeps runs identical across processes."""
    rng = zlib.crc32(spec["resource_id"].encode()) & 0xFFFFFFFF
    start = _parse(spec["start"])
    points: list[dict] = []
    ts = max(start, now - timedelta(hours=lookback_hours))
    while ts <= now:
        value = spec["baseline"] + ((rng >> (ts.hour % 16)) % 1000) / 1000.0 * spec["jitter"]
        for burst in spec.get("bursts", []):
            burst_start = _parse(burst["start"])
            if burst_start <= ts < burst_start + timedelta(hours=burst["hours"]):
                value = burst["value"]
        points.append({"ts": ts, "value": round(value, 3)})
        ts += timedelta(hours=1)
    return points


class TelemetryFixtureSource:
    name = "telemetry"

    def __init__(self, scenario_dir: Path) -> None:
        self._path = scenario_dir / "telemetry.json"

    def fetch(self, scope: Scope) -> SourceResult:
        payload = json.loads(self._path.read_text())
        now = _parse(payload["now"])
        records = []
        for spec in payload["series"]:
            requested_start = now - timedelta(hours=scope.lookback_hours)
            available_start = max(_parse(spec["start"]), requested_start)
            coverage_hours = (now - available_start).total_seconds() / 3600.0
            sufficient = coverage_hours >= MIN_COVERAGE_RATIO * scope.lookback_hours
            records.append({
                "resource_id": spec["resource_id"],
                "metric": spec["metric"],
                "lookback_hours": scope.lookback_hours,
                "resolution_minutes": 60,
                "coverage_hours": round(coverage_hours, 3),
                "sufficient": sufficient,
                "insufficient_reason": None if sufficient else (
                    f"coverage {coverage_hours:.0f}h of {scope.lookback_hours}h requested"),
                "points": materialise_points(spec, now, scope.lookback_hours),
            })
        return SourceResult(source=self.name, backend="fixture", records=records)
```

The fixture reports `resolution_minutes: 60` — what it actually has, not the 5 the request asked for. A report that claimed 5-minute resolution it does not possess would be a lie in the output. `sufficient` is computed, never stored in the fixture, so no fixture can assert its own adequacy.

```python
# app/sources/iac_fixture.py
from __future__ import annotations

import json
from pathlib import Path

from app.sources.base import Scope, SourceResult


class IaCFixtureSource:
    name = "iac"

    def __init__(self, scenario_dir: Path) -> None:
        self._path = scenario_dir / "iac.json"

    def fetch(self, scope: Scope) -> SourceResult:
        payload = json.loads(self._path.read_text())
        return SourceResult(source=self.name, backend="fixture",
                            records=payload["declarations"])
```

```python
# app/sources/policy_fixture.py
from __future__ import annotations

import json
from pathlib import Path

from app.sources.base import Scope, SourceResult


class PolicyFixtureSource:
    name = "policy"

    def __init__(self, scenario_dir: Path) -> None:
        self._path = scenario_dir / "policy.json"

    def fetch(self, scope: Scope) -> SourceResult:
        payload = json.loads(self._path.read_text())
        return SourceResult(source=self.name, backend="fixture", records=payload["rules"])
```

```python
# app/sources/__init__.py
from __future__ import annotations
from pathlib import Path
from app.config import RunConfig
from app.sources.base import Source, SourceError, SourceResult, Scope
from app.sources.iac_fixture import IaCFixtureSource
from app.sources.inventory_fixture import InventoryFixtureSource
from app.sources.policy_fixture import PolicyFixtureSource
from app.sources.telemetry_fixture import TelemetryFixtureSource

FIXTURE_BACKENDS = {
    "inventory": InventoryFixtureSource,
    "telemetry": TelemetryFixtureSource,
    "iac": IaCFixtureSource,
    "policy": PolicyFixtureSource,
}


def get_source(name: str, config: RunConfig, scenario_dir: Path | None = None) -> Source:
    if config.sample_mode:
        backend = FIXTURE_BACKENDS.get(name)
        if backend is None:
            raise KeyError(name)
        if scenario_dir is None:
            raise SourceError("sample mode needs a scenario directory")
        return backend(scenario_dir)

    from app.sources import live  # imported lazily: sample mode never imports the OCI SDK

    return live.get_live_source(name, config)
```

`app/sources/live.py` in Task 15 raises `SourceError("live backend not implemented yet")` for every name until then — which is exactly what makes Task 4's degradation path testable from day one.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_sources.py -v`
Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
git add app/sources/ data/ tests/test_sources.py
git commit -m "feat: Source protocol and four fixture backends with example_1 scenario"
```

---

### Task 4: RunState and the trace log

**Files:**
- Create: `app/state.py`, `app/trace.py`, `tests/test_state.py`, `tests/test_trace.py`

**Interfaces:**
- Consumes: `RunConfig`.
- Produces: `RunState(run_id, logs_dir)` with `path: Path`, `facts: dict`, `append(kind: str, payload: dict) -> dict`, `records() -> list[dict]`; `Tracer(run_id, logs_dir, stream=None)` with `path: Path` and `emit(*, agent_name, action, input_summary, output_summary, target_agent=None, confidence=None, retry_count=0, status="success", round=None, evidence_refs=None) -> dict`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_trace.py
import io, json
from pathlib import Path
from app.trace import Tracer, REQUIRED_FIELDS

def test_every_line_carries_the_required_fields(tmp_path):
    stream = io.StringIO()
    tracer = Tracer(run_id="run-abc", logs_dir=tmp_path, stream=stream)
    tracer.emit(agent_name="Scout", action="propose_finding", input_summary="batch-01 168h",
                output_summary="candidate R-3", target_agent="Skeptic", confidence=0.6,
                round=1, evidence_refs=["E-001"])
    record = json.loads(stream.getvalue().strip())
    assert set(REQUIRED_FIELDS) <= set(record)
    assert record["round"] == 1
    assert record["evidence_refs"] == ["E-001"]
    assert record["status"] == "success"

def test_the_file_matches_stdout_line_for_line(tmp_path):
    stream = io.StringIO()
    tracer = Tracer(run_id="run-abc", logs_dir=tmp_path, stream=stream)
    for i in range(3):
        tracer.emit(agent_name="Scout", action="act", input_summary=str(i),
                    output_summary=str(i), status="capped")
    tracer.close()
    assert tracer.path == tmp_path / "trace-run-abc.jsonl"
    assert tracer.path.read_text().strip().splitlines() == stream.getvalue().strip().splitlines()
    assert all(json.loads(line)["status"] == "capped" for line in tracer.path.read_text().splitlines())
```

```python
# tests/test_state.py
import json
from app.state import RunState

def test_state_file_is_separate_from_the_trace_file(tmp_path):
    state = RunState(run_id="run-abc", logs_dir=tmp_path)
    assert state.path == tmp_path / "state-run-abc.jsonl"
    assert state.path.name != f"trace-run-abc.jsonl"

def test_appends_are_ordered_and_round_trip(tmp_path):
    state = RunState(run_id="run-abc", logs_dir=tmp_path)
    state.append("hydrate", {"resources": 6})
    state.append("assignment", {"round": 1, "resource_ids": ["r1"]})
    kinds = [r["kind"] for r in state.records()]
    assert kinds == ["hydrate", "assignment"]
    assert json.loads(state.path.read_text().splitlines()[1])["round"] == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_trace.py tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.trace'`

- [ ] **Step 3: Implement `app/trace.py`**

```python
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

REQUIRED_FIELDS = (
    "timestamp", "run_id", "agent_name", "action", "input_summary",
    "output_summary", "target_agent", "confidence", "retry_count", "status",
)


class Tracer:
    """Writes one JSONL line per agent action to stdout and to logs/trace-<run_id>.jsonl."""

    def __init__(self, run_id: str, logs_dir: Path, stream: TextIO | None = None) -> None:
        self.run_id = run_id
        self._stream = stream if stream is not None else sys.stdout
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.path = logs_dir / f"trace-{run_id}.jsonl"
        self._handle = self.path.open("w", encoding="utf-8")

    def emit(self, *, agent_name: str, action: str, input_summary: str, output_summary: str,
             target_agent: str | None = None, confidence: float | None = None,
             retry_count: int = 0, status: str = "success", round: int | None = None,
             evidence_refs: list[str] | None = None) -> dict[str, Any]:
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": self.run_id,
            "agent_name": agent_name,
            "action": action,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "target_agent": target_agent,
            "confidence": confidence,
            "retry_count": retry_count,
            "status": status,
        }
        if round is not None:
            record["round"] = round
        if evidence_refs:
            record["evidence_refs"] = list(evidence_refs)
        line = json.dumps(record, ensure_ascii=False)
        self._stream.write(line + "\n")
        self._stream.flush()
        self._handle.write(line + "\n")
        self._handle.flush()
        return record

    def close(self) -> None:
        self._handle.close()
```

- [ ] **Step 4: Implement `app/state.py`**

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunState:
    """Append-only shared context. Distinct from the audit trace; both are JSONL."""

    def __init__(self, run_id: str, logs_dir: Path) -> None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.path = logs_dir / f"state-{run_id}.jsonl"
        self._handle = self.path.open("w", encoding="utf-8")
        self.facts: dict[str, Any] = {
            "resources": {}, "series": {}, "declarations": [], "rules": [],
            "sources": [], "candidates": {}, "rulings": {}, "recheck_counts": {}, "round": 0,
        }

    def append(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {"kind": kind, "run_id": self.run_id, **payload}
        self._handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._handle.flush()
        return record

    def records(self) -> list[dict[str, Any]]:
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines]

    def close(self) -> None:
        self._handle.close()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_trace.py tests/test_state.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add app/trace.py app/state.py tests/test_trace.py tests/test_state.py
git commit -m "feat: RunState and Tracer writing trace/state JSONL to stdout and logs/"
```

---

### Task 5: Deterministic analysis — cost, distribution, tags, IaC matching, rule matching

This is the task that makes the "no figure from a model" constraint real. Everything numeric in the report is computed here.

**Files:**
- Modify: `app/models.py` (add `size_gb: float | None = None` to `Resource`)
- Modify: `data/scenarios/example_1/inventory.json` (add `"size_gb": 50` to the block volume)
- Create: `app/analysis.py`, `tests/test_analysis.py`

**Interfaces:**
- Consumes: models.
- Produces: `stats_from_series(series: MetricSeries) -> dict` (keys `n`, `mean`, `peak`, `p50`, `p95`, `p99`, `peak_timestamps`, `coverage_ratio`, `sufficient`); `monthly_cost(resource: Resource, pricing: dict) -> float`; `match_iac(resource: Resource, declarations: list[IaCDeclaration]) -> tuple[str | None, IaCDeclaration | None]`; `qualifying_rules(resource, stats, attached, absent_from_iac, rules) -> list[PolicyRule]`; `savings_upper_bound(resource, pricing) -> float`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis.py
from datetime import datetime, timezone
from pathlib import Path
import json
import pytest
from app.analysis import (match_iac, monthly_cost, qualifying_rules, stats_from_series)
from app.config import RunConfig
from app.models import IaCDeclaration, MetricSeries, PolicyRule, Resource
from app.sources import get_source
from app.sources.base import Scope

SCEN = Path("data/scenarios/example_1")
PRICING = json.loads(Path("data/pricing.json").read_text())


def resource(**kw):
    base = dict(resource_id="r1", resource_class="compute_instance", display_name="batch-01",
                compartment_id="c1", lifecycle_state="RUNNING",
                time_created=datetime(2026, 8, 14, tzinfo=timezone.utc), tags={})
    return Resource(**{**base, **kw})


def series(index):
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    src = get_source("telemetry", cfg, scenario_dir=SCEN)
    return MetricSeries(**src.fetch(Scope(compartment_ids=[], resource_types=[],
                                          lookback_hours=168, resolution_minutes=60)).records[index])


def test_stats_expose_mean_peak_and_coverage():
    stats = stats_from_series(series(1))          # batch-01, 7-day window
    assert stats["mean"] < 5.0
    assert stats["peak"] < 20.0
    assert stats["coverage_ratio"] >= 0.99
    assert stats["sufficient"] is True


def test_monthly_cost_uses_shape_rates():
    assert monthly_cost(resource(shape="VM.Standard.E4.Flex", ocpus=4, memory_gb=16), PRICING) == 90.52
    assert monthly_cost(resource(resource_class="block_volume", size_gb=50), PRICING) == pytest.approx(
        50 * PRICING["block_volume_gb_month"], abs=0.01)
    assert monthly_cost(resource(resource_class="reserved_public_ip"), PRICING) == pytest.approx(7.30)
    with pytest.raises(KeyError):
        monthly_cost(resource(shape="VM.Does.Not.Exist", ocpus=1, memory_gb=1), PRICING)


def test_iac_match_prefers_the_declared_tag_then_name_then_normalised():
    tag_match = IaCDeclaration(address="oci_core_instance.batch_01", resource_type="oci_core_instance",
                               declared_name="batch-01", file_path="terraform/batch.tf",
                               last_commit="d4e5f6a", commit_message="month-end batch worker", author="me")
    r = resource(tags={"iac_address": "oci_core_instance.batch_01"})
    assert match_iac(r, [tag_match]) == ("tag", tag_match)
    assert match_iac(resource(display_name="batch-01"), [tag_match])[0] == "name"
    assert match_iac(resource(display_name="BATCH 01"), [tag_match])[0] == "normalised"
    assert match_iac(resource(display_name="sandbox-tmp"), [tag_match]) == (None, None)


def test_short_coverage_disqualifies_every_cost_rule():
    sandbox = series(3)
    stats = stats_from_series(sandbox)
    rules = [PolicyRule(**r) for r in json.loads((SCEN / "policy.json").read_text())["rules"]]
    assert stats["coverage_ratio"] < 0.8
    fired = qualifying_rules(resource(display_name="sandbox-tmp"), stats, None, True, rules)
    # R-5 is an unattributed rule and deliberately needs no metric window; every rule that
    # depends on statistics is disqualified.
    assert [r.rule_id for r in fired if r.finding_class == "cost_waste"] == []
    assert [r.rule_id for r in fired] == ["R-5"]


def test_window_width_changes_which_rule_fires():
    rules = [PolicyRule(**r) for r in json.loads((SCEN / "policy.json").read_text())["rules"]]
    narrow = qualifying_rules(resource(), stats_from_series(series(1)), None, False, rules)
    assert [r.rule_id for r in narrow] == ["R-3"]

    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    wide_records = get_source("telemetry", cfg, scenario_dir=SCEN).fetch(
        Scope(compartment_ids=[], resource_types=[], lookback_hours=744, resolution_minutes=60)).records
    wide = qualifying_rules(resource(), stats_from_series(MetricSeries(**wide_records[1])), None, False, rules)
    assert [r.rule_id for r in wide] == ["R-4"]


def test_unattributed_rule_needs_no_telemetry():
    rules = [PolicyRule(**r) for r in json.loads((SCEN / "policy.json").read_text())["rules"]]
    stats = stats_from_series(series(3))          # insufficient coverage
    fired = qualifying_rules(resource(display_name="sandbox-tmp"), stats, None, True, rules)
    assert [r.rule_id for r in fired] == ["R-5"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.analysis'`

- [ ] **Step 3: Add `size_gb` to the model and to the volume fixture**

In `app/models.py`, inside `Resource`, after `memory_gb: float | None = None` add:

```python
    size_gb: float | None = None
```

In `data/scenarios/example_1/inventory.json`, the `vol-orphan-50g` entry gains `"size_gb": 50` after `"tags": {},`.

- [ ] **Step 4: Implement `app/analysis.py`**

```python
from __future__ import annotations

from typing import Any

from app.models import IaCDeclaration, MetricSeries, PolicyRule, Resource


def stats_from_series(series: MetricSeries) -> dict[str, Any]:
    values = [p.value for p in series.points]
    if not values:
        return {"n": 0, "mean": 0.0, "peak": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0,
                "peak_timestamps": [], "coverage_ratio": 0.0, "sufficient": False}
    ordered = sorted(values)

    def percentile(q: float) -> float:
        return ordered[min(len(ordered) - 1, int(q * len(ordered)))]

    peak = max(values)
    return {
        "n": len(values),
        "mean": round(sum(values) / len(values), 3),
        "peak": peak,
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "peak_timestamps": [p.ts.isoformat() for p in series.points if p.value == peak][:3],
        "coverage_ratio": round(series.coverage_hours / series.lookback_hours, 3),
        "sufficient": series.sufficient,
    }


def monthly_cost(resource: Resource, pricing: dict[str, Any]) -> float:
    hours = pricing["hours_per_month"]
    if resource.resource_class == "compute_instance":
        rates = pricing["shapes"][resource.shape]          # KeyError on an unknown shape: fail loudly
        return round(resource.ocpus * hours * rates["ocpu_hour"]
                     + resource.memory_gb * hours * rates["gb_hour"], 2)
    if resource.resource_class == "block_volume":
        return round((resource.size_gb or 0.0) * pricing["block_volume_gb_month"], 2)
    if resource.resource_class == "reserved_public_ip":
        return round(pricing["reserved_public_ip_hour"] * hours, 2)
    raise KeyError(resource.resource_class)


def savings_upper_bound(resource: Resource, pricing: dict[str, Any]) -> float:
    """An upper bound, never a promise: what the resource costs if the finding is actionable."""
    return monthly_cost(resource, pricing)


def match_iac(resource: Resource, declarations: list[IaCDeclaration]) -> tuple[str | None, IaCDeclaration | None]:
    declared = resource.tags.get("iac_address")
    if declared:
        for item in declarations:
            if item.address == declared:
                return "tag", item
    for item in declarations:
        if item.declared_name == resource.display_name:
            return "name", item
    normalised = resource.display_name.lower().replace("-", "_").replace(" ", "_")
    for item in declarations:
        if item.declared_name.lower().replace("-", "_").replace(" ", "_") == normalised:
            return "normalised", item
    return None, None


def _matches(resource: Resource, stats: dict[str, Any], attached: bool | None,
             absent_from_iac: bool, when: dict[str, Any]) -> bool:
    if "resource_class" in when and when["resource_class"] != resource.resource_class:
        return False
    if "compute_instance" in when and when["compute_instance"] != (resource.resource_class == "compute_instance"):
        return False
    if "attached" in when and when["attached"] != attached:
        return False
    if "absent_from_iac" in when and when["absent_from_iac"] != absent_from_iac:
        return False
    if "min_coverage_ratio" in when and stats["coverage_ratio"] < when["min_coverage_ratio"]:
        return False
    if "mean_cpu_lt" in when and not stats["mean"] < when["mean_cpu_lt"]:
        return False
    if "peak_cpu_lt" in when and not stats["peak"] < when["peak_cpu_lt"]:
        return False
    if "peak_cpu_gte" in when and not stats["peak"] >= when["peak_cpu_gte"]:
        return False
    return True


def qualifying_rules(resource: Resource, stats: dict[str, Any], attached: bool | None,
                     absent_from_iac: bool, rules: list[PolicyRule]) -> list[PolicyRule]:
    return [r for r in rules if _matches(resource, stats, attached, absent_from_iac, r.when)]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_analysis.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add app/analysis.py app/models.py data/scenarios/example_1/inventory.json tests/test_analysis.py
git commit -m "feat: deterministic cost, coverage, IaC-match and rule-match analysis"
```

---

### Task 6: The Generator seam and the offline rule engine

**Files:**
- Create: `app/generator.py`, `tests/test_generator.py`

**Interfaces:**
- Consumes: `RunConfig`.
- Produces: `Generator` protocol with `complete(*, prompt: str, schema: dict, context: dict) -> dict`; `RulesGenerator()`; `ModelGenerator(base_url, api_key, model, timeout_s=60)`; `get_generator(config: RunConfig) -> Generator`; `GeneratorUnavailableError`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_generator.py
import pytest
from app.config import RunConfig
from app.generator import GeneratorUnavailableError, ModelGenerator, RulesGenerator, get_generator


def test_sample_mode_selects_the_rule_engine_even_when_a_key_is_present(monkeypatch):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_API_KEY", "sk-not-a-real-key")
    assert isinstance(get_generator(RunConfig.from_env_and_request({})), RulesGenerator)


def test_live_mode_without_a_key_degrades_to_rules_instead_of_crashing(monkeypatch):
    monkeypatch.delenv("SAMPLE_MODE", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert isinstance(get_generator(RunConfig.from_env_and_request({"sample_mode": False})), RulesGenerator)


def test_live_mode_with_a_key_uses_the_model(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-not-a-real-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "some-model")
    assert isinstance(get_generator(RunConfig.from_env_and_request({})), ModelGenerator)


def test_rule_engine_shapes_match_their_schema():
    gen = RulesGenerator()
    claim = gen.complete(prompt="", schema={"name": "finding_claim"},
                         context={"rule_id": "R-3", "resource_name": "sandbox-tmp",
                                  "stats": {"mean": 0.3, "peak": 0.4}, "iac_match_rule": None})
    assert set(claim) == {"claim", "confidence"}
    assert claim["claim"]
    with pytest.raises(KeyError):
        gen.complete(prompt="", schema={"name": "not_a_schema"}, context={})


def test_confidence_reflects_how_the_iac_link_was_made():
    gen = RulesGenerator()
    common = {"rule_id": "R-3", "resource_name": "x", "stats": {"mean": 0.4, "peak": 0.5}}
    declared = gen.complete(prompt="", schema={"name": "finding_claim"},
                            context={**common, "iac_match_rule": "tag"})
    inferred = gen.complete(prompt="", schema={"name": "finding_claim"},
                            context={**common, "iac_match_rule": "normalised"})
    unmatched = gen.complete(prompt="", schema={"name": "finding_claim"},
                             context={**common, "iac_match_rule": None})
    assert declared["confidence"] > inferred["confidence"] == unmatched["confidence"]


def test_model_generator_refuses_to_construct_without_a_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(GeneratorUnavailableError):
        ModelGenerator.from_env()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.generator'`

- [ ] **Step 3: Implement `app/generator.py`**

```python
from __future__ import annotations

import json
import os
from typing import Any, Protocol

import requests

from app.config import RunConfig

TEMPLATES: dict[str, str] = {
    "R-1": "{resource_name} is a detached {size_gb} GB block volume. It is billed continuously "
           "and is attached to nothing.",
    "R-2": "{resource_name} is a reserved public IP with no assigned entity. It is billed "
           "whether or not it is attached.",
    "R-3": "{resource_name} averages {mean}% CPU with a peak of {peak}% across the "
           "requested window, and is declared in Terraform. Nothing in the evidence attributes "
           "a purpose to it.",
    "R-4": "{resource_name} averages {mean}% CPU but peaks at {peak}%. The cost is the "
           "idle shape it holds around the clock, not the work it does.",
    "R-5": "{resource_name} is running and appears in no Terraform declaration. No owner tag "
           "attributes it to a team.",
}

REASONS: dict[str, str] = {
    "schedule_signal": "the declaration or tag names a repeating cadence, so the requested "
                       "window may exclude the most recent run",
    "recheck_cap": "this finding has already been re-investigated {n} times",
    "frequency_mismatch": "a low mean with a peak this high is a duty-cycle problem, not an "
                          "idle resource",
}


class GeneratorUnavailableError(Exception):
    pass


class Generator(Protocol):
    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict: ...


class RulesGenerator:
    """Deterministic, offline. The same structured outputs a model would produce, from rules."""

    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict:
        name = schema.get("name")
        if name == "finding_claim":
            rule_id = context["rule_id"]
            template = TEMPLATES[rule_id]                 # KeyError on an unmapped rule: fail loudly
            text = template.format(resource_name=context["resource_name"],
                                   mean=context["stats"].get("mean", 0.0),
                                   peak=context["stats"].get("peak", 0.0))
            confidence = 0.75 if context.get("iac_match_rule") == "tag" else 0.55
            return {"claim": text, "confidence": confidence}
        if name == "verdict_reason":
            return {"reason": REASONS[context["reason_key"]].format(n=context.get("n", 0)),
                    "confidence": 0.8}
        if name == "run_summary":
            return {"summary": ("Audited {resources} resources across {sources} sources; "
                                "{accepted} findings accepted, {rejected} rejected, "
                                "{undetermined} left undetermined.").format(**context),
                    "confidence": 1.0}
        raise KeyError(name)


class ModelGenerator:
    """OpenAI-compatible chat completions. Never instantiated in sample mode."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: int = 60) -> None:
        self.base_url, self.api_key, self.model, self.timeout_s = base_url, api_key, model, timeout_s

    @classmethod
    def from_env(cls) -> "ModelGenerator":
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise GeneratorUnavailableError("LLM_API_KEY is not set")
        return cls(base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
                   api_key=api_key, model=os.environ.get("LLM_MODEL", "gpt-4o-mini"))

    def complete(self, *, prompt: str, schema: dict, context: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": json.dumps(schema)},
                               {"role": "user", "content": prompt}]},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


def get_generator(config: RunConfig) -> Generator:
    if config.sample_mode or not os.environ.get("LLM_API_KEY"):
        return RulesGenerator()
    return ModelGenerator.from_env()
```

The live-without-a-key path deliberately degrades to rules rather than raising: a judge who runs live mode without a provider key gets a working, deterministic run, not a stack trace, and the report's `mode` field still says `live`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_generator.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/generator.py tests/test_generator.py
git commit -m "feat: Generator seam with an offline rule engine and a model-backed generator"
```

---

### Task 7: Agent base and the Planner

**Files:**
- Modify: `app/models.py` (add `Assignment`)
- Create: `app/agents/__init__.py`, `app/agents/base.py`, `app/agents/planner.py`, `tests/test_planner.py`

**Interfaces:**
- Consumes: `RunConfig`, `Source`, `Generator`, `RunState`, `Tracer`, `EvidenceLedger`, `Resource`.
- Produces: `AgentContext(config, sources, generator, state, trace, ledger)` dataclass; `Agent` base with `name: str` and `_emit(...)`; `Assignment(assignment_id, round, resource_ids, lookback_hours, focus)`; `Planner(ctx)` with `assign(round: int, resources: list[Resource], recheck_requests: list[dict]) -> Assignment`.

- [ ] **Step 1: Add `Assignment` to `app/models.py`**

```python
class Assignment(BaseModel):
    assignment_id: str
    round: int
    resource_ids: list[str]
    lookback_hours: int
    focus: str = "initial"
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_planner.py
from datetime import datetime, timezone
from pathlib import Path
from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.models import Resource
from app.state import RunState
from app.trace import Tracer
import io, pytest

SCEN = Path("data/scenarios/example_1")


def ctx(tmp_path, sample=True):
    cfg = RunConfig.from_env_and_request({"sample_mode": sample})
    return AgentContext(config=cfg, sources={}, generator=RulesGenerator(),
                        state=RunState(cfg.run_id, tmp_path),
                        trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                        ledger=EvidenceLedger())


def res(i):
    return Resource(resource_id=f"r{i}", resource_class="compute_instance", display_name=f"n{i}",
                    compartment_id="c1", lifecycle_state="RUNNING",
                    time_created=datetime(2026, 8, 1, tzinfo=timezone.utc))


def test_planner_respects_max_resources(tmp_path):
    c = ctx(tmp_path)
    c.config.max_resources = 3
    assignment = Planner(c).assign(round=1, resources=[res(i) for i in range(10)], recheck_requests=[])
    assert len(assignment.resource_ids) == 3
    assert assignment.assignment_id == "A-1"


def test_recheck_requests_narrow_the_assignment_and_change_the_window(tmp_path):
    c = ctx(tmp_path)
    request = {"resource_id": "r7", "lookback_hours": 744, "reason": "window excludes the burst"}
    assignment = Planner(c).assign(round=2, resources=[res(i) for i in range(10)],
                                   recheck_requests=[request])
    assert assignment.resource_ids == ["r7"]
    assert assignment.lookback_hours == 744
    assert assignment.focus == "recheck"


def test_planner_emits_one_trace_line_per_assignment(tmp_path):
    c = ctx(tmp_path)
    Planner(c).assign(round=1, resources=[res(0)], recheck_requests=[])
    Planner(c).assign(round=2, resources=[res(0)], recheck_requests=[])
    lines = c.trace.path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert '"agent_name": "Planner"' in lines[0]
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_planner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents'`

- [ ] **Step 4: Implement `app/agents/base.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import Generator
from app.sources.base import Scope, Source
from app.state import RunState
from app.trace import Tracer


@dataclass
class AgentContext:
    config: RunConfig
    sources: dict[str, Source]
    generator: Generator
    state: RunState
    trace: Tracer
    ledger: EvidenceLedger
    scope: Scope | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def evidence(self, *, source: str, kind: str, resource_id: str, summary: str, payload: dict):
        return self.ledger.add(source=source, kind=kind, resource_id=resource_id,
                               summary=summary, payload=payload)


class Agent:
    name = "Agent"

    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    def _emit(self, action: str, *, input_summary: str, output_summary: str,
              target_agent: str | None = None, confidence: float | None = None,
              status: str = "success", round: int | None = None,
              evidence_refs: list[str] | None = None, retry_count: int = 0) -> dict:
        return self.ctx.trace.emit(agent_name=self.name, action=action,
                                   input_summary=input_summary, output_summary=output_summary,
                                   target_agent=target_agent, confidence=confidence, status=status,
                                   round=round, evidence_refs=evidence_refs, retry_count=retry_count)
```

- [ ] **Step 5: Implement `app/agents/planner.py`**

```python
from __future__ import annotations

from app.agents.base import Agent
from app.models import Assignment, Resource


class Planner(Agent):
    name = "Planner"

    def assign(self, *, round: int, resources: list[Resource],
               recheck_requests: list[dict]) -> Assignment:
        if recheck_requests:
            target_ids = [r["resource_id"] for r in recheck_requests]
            lookback = max(r.get("lookback_hours", self.ctx.config.lookback_hours)
                           for r in recheck_requests)
            focus = "recheck"
        else:
            target_ids = [r.resource_id for r in resources][: self.ctx.config.max_resources]
            lookback = self.ctx.config.lookback_hours
            focus = "initial"

        assignment = Assignment(assignment_id=f"A-{round}", round=round, resource_ids=target_ids,
                                lookback_hours=lookback, focus=focus)
        self.ctx.state.append("assignment", {"round": round, "focus": focus,
                                             "resource_ids": target_ids,
                                             "lookback_hours": lookback})
        self._emit("delegate_task", round=round, target_agent="Scout",
                   input_summary=f"round {round}, {len(target_ids)} target(s), "
                                 f"lookback {lookback}h",
                   output_summary=f"assignment {assignment.assignment_id} ({focus})",
                   confidence=0.8)
        return assignment

    def wants_another_round(self, *, round: int, recheck_requests: list[dict]) -> bool:
        return bool(recheck_requests) and round < self.ctx.config.max_rounds
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python -m pytest tests/test_planner.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add app/agents/ app/models.py tests/test_planner.py
git commit -m "feat: agent base, AgentContext and the Planner with cap-aware assignments"
```

---

### Task 8: The Scout

**Files:**
- Modify: `app/models.py` (add `Candidate`)
- Create: `app/agents/scout.py`, `tests/test_scout.py`

**Interfaces:**
- Consumes: `AgentContext`, `Assignment`, `analysis`.
- Produces: `Candidate(candidate_id, resource_id, resource_class, finding_class, claim, evidence_refs, impact, confidence, falsifier, matched_rule_ids, iac_match_rule, absent_from_iac, stats)`; `Scout(ctx)` with `investigate(assignment: Assignment) -> list[Candidate]` and `undetermined() -> list[Undetermined]`.

The Scout has no authority to give a finding a status. It cannot see the Skeptic's rulings.

- [ ] **Step 1: Add `Candidate` to `app/models.py`**

```python
class Candidate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    candidate_id: str
    resource_id: str
    resource_class: ResourceClass
    finding_class: FindingClass = Field(alias="class")
    claim: str
    evidence_refs: list[str]
    impact: dict[str, Any]
    confidence: float
    falsifier: str
    matched_rule_ids: list[str] = Field(default_factory=list)
    iac_match_rule: str | None = None
    absent_from_iac: bool = False
    stats: dict[str, Any] = Field(default_factory=dict)
    superseded_by: str | None = None
    """Set by the loop when a later round reaches a different conclusion about this resource.
    A superseded candidate is reported as `rejected`, with its reason — never dropped."""
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_scout.py
import json
from pathlib import Path
import pytest
from datetime import datetime, timezone
from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.agents.scout import Scout
from app.config import RunConfig
from app.evidence import DanglingEvidenceError, EvidenceLedger
from app.generator import RulesGenerator
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer
import io

SCEN = Path("data/scenarios/example_1")


@pytest.fixture
def ctx(tmp_path):
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac", "policy")}
    return AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                        state=RunState(cfg.run_id, tmp_path),
                        trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                        ledger=EvidenceLedger(), scope=scope)


def hydrate_and_assign(ctx, round=1, lookback_hours=None):
    """The Scout must hydrate the shared state before it can investigate anything, and the
    Planner must be given the real resources — an empty assignment investigates nothing."""
    scout = Scout(ctx)
    scout.hydrate()
    assignment = Planner(ctx).assign(
        round=round, resources=list(ctx.state.facts["resources"].values()), recheck_requests=[])
    if lookback_hours is not None:
        assignment = assignment.model_copy(update={"lookback_hours": lookback_hours})
    return scout, assignment


def test_hydrate_loads_six_resources_three_declarations_and_five_rules(ctx):
    hydrate_and_assign(ctx)
    assert len(ctx.state.facts["resources"]) == 6
    assert len(ctx.state.facts["declarations"]) == 3
    assert len(ctx.state.facts["rules"]) == 5


def test_scout_proposes_the_idle_claim_for_batch01_on_the_narrow_window(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    batch = next(c for c in candidates if c.resource_id.endswith("bbb2"))
    assert batch.finding_class == "cost_waste"
    assert batch.matched_rule_ids == ["R-3"]
    assert "average" in batch.claim
    assert batch.confidence < 0.8           # lifecycle-only evidence, no purpose found
    ctx.ledger.resolve(batch.evidence_refs)  # every ref must resolve


def test_scout_never_sets_a_status(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    for candidate in scout.investigate(assignment):
        assert not hasattr(candidate, "status")


def test_every_candidate_ref_resolves_or_the_ledger_raises(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    assert candidates
    for candidate in candidates:
        assert candidate.evidence_refs
        assert ctx.ledger.resolve(candidate.evidence_refs)
    with pytest.raises(DanglingEvidenceError):
        ctx.ledger.resolve(["E-404"])


def test_insufficient_coverage_becomes_undetermined_not_a_candidate(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    scout.investigate(assignment)
    undetermined = {u.resource_id: u.reason for u in scout.undetermined()}
    sandbox = next(k for k in undetermined if k.endswith("ddd4"))
    assert "41h of 168h" in undetermined[sandbox]


def test_unattributed_finding_needs_no_telemetry_but_cost_finding_does(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    sandbox = [c for c in candidates if c.resource_id.endswith("ddd4")]
    assert [c.finding_class for c in sandbox] == ["unattributed"]


def test_scout_does_not_flag_a_genuinely_busy_instance(ctx):
    scout, assignment = hydrate_and_assign(ctx)
    candidates = scout.investigate(assignment)
    assert not [c for c in candidates if c.resource_id.endswith("aaa1")]  # web-01, steady 50%
    assert not [c for c in candidates if c.resource_id.endswith("ccc3")]  # reports-01, steady 10%
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_scout.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.scout'`

- [ ] **Step 4: Implement `app/agents/scout.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from app.agents.base import Agent
from app.analysis import match_iac, monthly_cost, qualifying_rules, stats_from_series
from app.models import (Assignment, Candidate, IaCDeclaration, MetricSeries, PolicyRule, Resource,
                        SourceStatus, Undetermined)
from app.sources.base import Scope


class Scout(Agent):
    name = "Scout"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._undetermined: list[Undetermined] = []
        self._source_status: dict[str, SourceStatus] = {}

    def source_statuses(self) -> list[SourceStatus]:
        return list(self._source_status.values())

    # --- hydrating the shared state once per run -------------------------------------------
    def hydrate(self) -> None:
        inventory = self.ctx.sources["inventory"].fetch(self.ctx.scope)
        for record in inventory.records:
            resource = Resource(**record)
            self.ctx.state.facts["resources"][resource.resource_id] = resource

        iac = self.ctx.sources["iac"].fetch(self.ctx.scope)
        self.ctx.state.facts["declarations"] = [IaCDeclaration(**d) for d in iac.records]

        policy = self.ctx.sources["policy"].fetch(self.ctx.scope)
        self.ctx.state.facts["rules"] = [PolicyRule(**r) for r in policy.records]

        self.ctx.state.append("hydrate", {
            "resources": len(self.ctx.state.facts["resources"]),
            "declarations": len(self.ctx.state.facts["declarations"]),
            "rules": len(self.ctx.state.facts["rules"]),
        })
        self._emit("hydrate", input_summary="inventory, iac, policy",
                   output_summary=f"{len(self.ctx.state.facts['resources'])} resources, "
                                  f"{len(self.ctx.state.facts['declarations'])} declarations",
                   confidence=1.0)

    def _series_for(self, resource_id: str, lookback_hours: int) -> MetricSeries | None:
        scope = Scope(compartment_ids=self.ctx.scope.compartment_ids,
                      resource_types=self.ctx.scope.resource_types,
                      lookback_hours=lookback_hours,
                      resolution_minutes=self.ctx.scope.resolution_minutes)
        result = self._fetch_with_recovery("telemetry", scope)
        if result is None:
            return None
        for record in result.records:
            if record["resource_id"] == resource_id:
                return MetricSeries(**record)
        return None

    def _fetch_with_recovery(self, name: str, scope: Scope):
        """One retry, then the fixture backend, then None. Never invents records."""
        source = self.ctx.sources[name]
        for attempt in (1, 2):
            try:
                result = source.fetch(scope)
                self._source_status[name] = SourceStatus(name=name, backend=result.backend)
                return result
            except Exception as exc:                      # noqa: BLE001 - logged, then degraded
                self._emit("source_call_failed", input_summary=f"{name} attempt {attempt}",
                           output_summary=f"{type(exc).__name__}: {exc}", status="retrying",
                           retry_count=attempt - 1)
        self._emit("source_call_failed", input_summary=name,
                   output_summary="both attempts failed; source treated as unavailable",
                   status="failed", retry_count=1)
        self._source_status[name] = SourceStatus(name=name, backend="live", degraded=True,
                                                 reason="both attempts failed")
        return None

    def investigate(self, assignment: Assignment) -> list[Candidate]:
        candidates: list[Candidate] = []
        resources: dict[str, Resource] = self.ctx.state.facts["resources"]
        declarations: list[IaCDeclaration] = self.ctx.state.facts["declarations"]
        rules: list[PolicyRule] = self.ctx.state.facts["rules"]

        for resource_id in assignment.resource_ids:
            resource = resources[resource_id]
            attached = getattr(resource, "attached", None)

            series = (None if resource.resource_class != "compute_instance"
                      else self._series_for(resource_id, assignment.lookback_hours))
            stats = stats_from_series(series) if series else {
                "n": 0, "mean": 0.0, "peak": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0,
                "peak_timestamps": [], "coverage_ratio": 1.0, "sufficient": True}

            match_rule, declaration = match_iac(resource, declarations)
            absent = declaration is None
            if resource.resource_class == "compute_instance" and absent:
                self._emit("flag_unattributed", round=assignment.round, target_agent="Skeptic",
                           input_summary=resource.display_name,
                           output_summary="no IaC declaration matched",
                           confidence=0.75)
            fired = qualifying_rules(resource, stats, attached, absent, rules)

            if resource.resource_class == "compute_instance" and not stats["sufficient"]:
                self._undetermined.append(Undetermined(
                    resource_id=resource_id,
                    reason=series.insufficient_reason or "insufficient telemetry coverage"))
                self._emit("abstain", round=assignment.round,
                           input_summary=f"{resource.display_name} telemetry",
                           output_summary=f"insufficient coverage "
                                          f"({stats['coverage_ratio']:.2f}); no cost finding raised",
                           status="abstained", confidence=1.0)

            for rule in fired:
                if rule.finding_class == "cost_waste" and not stats["sufficient"]:
                    continue          # a cost verdict on an incomplete window is not allowed

                evidence = [
                    self.ctx.evidence(source="inventory", kind="resource",
                                      resource_id=resource_id,
                                      summary=f"{resource.display_name} {resource.shape} "
                                              f"{resource.ocpus} OCPU/{resource.memory_gb} GB "
                                              f"{resource.lifecycle_state}",
                                      payload={"shape": resource.shape, "ocpus": resource.ocpus,
                                               "memory_gb": resource.memory_gb, "tags": resource.tags,
                                               "lifecycle_state": resource.lifecycle_state}),
                ]
                if series is not None:
                    evidence.append(self.ctx.evidence(
                        source="telemetry", kind="cpu_stats", resource_id=resource_id,
                        summary=f"mean {stats['mean']}% peak {stats['peak']}% over "
                                f"{series.coverage_hours:.0f}h",
                        payload={**stats, "lookback_hours": series.lookback_hours,
                                 "resolution_minutes": series.resolution_minutes,
                                 "coverage_hours": series.coverage_hours}))
                if declaration is not None:
                    evidence.append(self.ctx.evidence(
                        source="iac", kind="declaration", resource_id=resource_id,
                        summary=f"{declaration.address} in {declaration.file_path} "
                                f"({declaration.commit_message})",
                        payload=declaration.model_dump()))
                if absent and resource.resource_class == "compute_instance":
                    evidence.append(self.ctx.evidence(
                        source="iac", kind="absent", resource_id=resource_id,
                        summary="no matching declaration (tag, name, or normalised name)",
                        payload={"match_rule": None}))
                evidence.append(self.ctx.evidence(
                    source="policy", kind="rule_hit", resource_id=resource_id,
                    summary=f"{rule.rule_id}: {rule.note}", payload={"rule_id": rule.rule_id}))

                generated = self.ctx.generator.complete(
                    prompt=f"State the finding for {resource.display_name} under {rule.rule_id}.",
                    schema={"name": "finding_claim"},
                    context={"rule_id": rule.rule_id, "resource_name": resource.display_name,
                             "stats": stats, "iac_match_rule": match_rule})

                pricing = json.loads((Path("data/pricing.json")).read_text())
                impact_kind = "usd_per_month" if rule.rule_id in {"R-1", "R-2", "R-3", "R-5"} \
                    else "usd_per_month_upper_bound"
                candidate = Candidate(
                    candidate_id=f"C-{len(self.ctx.state.facts['candidates']) + 1:03d}",
                    resource_id=resource_id, resource_class=resource.resource_class,
                    **{"class": rule.finding_class}, claim=generated["claim"],
                    evidence_refs=[e.evidence_id for e in evidence],
                    impact={"kind": impact_kind, "value": monthly_cost(resource, pricing)},
                    confidence=generated["confidence"],
                    falsifier="a current, declared, owned purpose for this resource would "
                              "withdraw this finding",
                    matched_rule_ids=[rule.rule_id], iac_match_rule=match_rule,
                    absent_from_iac=absent, stats=stats)

                self.ctx.state.facts["candidates"][candidate.candidate_id] = candidate
                self.ctx.state.append("candidate", {"candidate_id": candidate.candidate_id,
                                                    "resource_id": resource_id,
                                                    "rules": [rule.rule_id],
                                                    "round": assignment.round})
                candidates.append(candidate)
                self._emit("propose_finding", round=assignment.round, target_agent="Skeptic",
                           input_summary=f"{resource.display_name} under {rule.rule_id}",
                           output_summary=f"{candidate.candidate_id}: {rule.finding_class}",
                           confidence=candidate.confidence,
                           evidence_refs=candidate.evidence_refs)
        return candidates

    def undetermined(self) -> list[Undetermined]:
        return list(self._undetermined)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_scout.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add app/agents/scout.py app/models.py tests/test_scout.py
git commit -m "feat: Scout proposes evidenced candidates and abstains on insufficient telemetry"
```

---

### Task 9: The Skeptic

The one agent whose output changes what another agent does next. Its whole job is to be unconvinced.

**Amended during the build (2026-09-24).** The rule set alone could not satisfy example_3's
requirement that a resource declared *idle by design* stay unreported: nothing in `judge` could
reject it, so the `falsifier` every candidate publishes was decoration. The Skeptic gained a
purpose check that runs **before** the R-3 branch, plus a shared signal helper:

```python
PURPOSE_SIGNALS = ("by design", "intentionally", "deliberately", "do not delete", "for now",
                   "left running")

    def _signal(self, candidate, needles):
        for item in self.ctx.ledger.resolve(candidate.evidence_refs):
            haystack = " ".join(str(v) for v in list(item.payload.values()) + [item.summary]).lower()
            for needle in needles:
                if needle in haystack:
                    return needle
        return None

    # first branch of _judge, before the R-3 recheck:
        if candidate.finding_class == "cost_waste":
            purpose = self._purpose_signal(candidate)
            if purpose:
                reason = self.ctx.generator.complete(
                    prompt="", schema={"name": "verdict_reason"},
                    context={"reason_key": "declared_purpose", "signal": purpose})["reason"]
                return self._reject(candidate, round, reason)
```

with `REASONS["declared_purpose"] = "the declaration states a deliberate purpose ({signal}), which
is exactly the falsifier this finding published"` in `app/generator.py`, and the format call passing
`signal=context.get("signal", "")`. Pinned by
`test_a_declared_purpose_withdraws_a_cost_finding` and by example_3's `must_not_flag`.

**Files:**
- Modify: `app/models.py` (add `Ruling`)
- Create: `app/agents/skeptic.py`, `tests/test_skeptic.py`

**Interfaces:**
- Consumes: `AgentContext`, `Candidate`.
- Produces: `Ruling(candidate_id, verdict, reason, request, revised_claim)`; `Skeptic(ctx)` with `judge(candidate: Candidate, round: int) -> Ruling`.

- [ ] **Step 1: Add `Ruling` to `app/models.py`**

```python
class Ruling(BaseModel):
    candidate_id: str
    verdict: Verdict
    reason: str
    request: dict[str, Any] | None = None
    revised_claim: str | None = None
    round: int = 0
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_skeptic.py
import pytest
from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.agents.scout import Scout
from app.agents.skeptic import Skeptic
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer
import io
from pathlib import Path

SCEN = Path("data/scenarios/example_1")


@pytest.fixture
def ctx(tmp_path):
    cfg = RunConfig.from_env_and_request({"sample_mode": True})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac", "policy")}
    c = AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                     state=RunState(cfg.run_id, tmp_path),
                     trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                     ledger=EvidenceLedger(), scope=scope)
    scout = Scout(c)
    scout.hydrate()
    c.extras["scout"] = scout
    return c


def candidates(ctx, lookback=168):
    scout: Scout = ctx.extras["scout"]
    assignment = Planner(ctx).assign(
        round=1, resources=list(ctx.state.facts["resources"].values()), recheck_requests=[])
    assignment = assignment.model_copy(update={"lookback_hours": lookback})
    return scout.investigate(assignment)


def test_skeptic_demands_a_wider_window_when_a_schedule_signal_exists(ctx):
    batch = next(c for c in candidates(ctx) if c.resource_id.endswith("bbb2"))
    ruling = Skeptic(ctx).judge(batch, round=1)
    assert ruling.verdict == "recheck"
    assert ruling.request["lookback_hours"] == 744
    assert "month-end" in ruling.reason or "cadence" in ruling.reason


def test_skeptic_accepts_the_revised_claim_once_the_burst_is_in_the_window(ctx):
    batch = next(c for c in candidates(ctx, lookback=744) if c.resource_id.endswith("bbb2"))
    assert batch.matched_rule_ids == ["R-4"]
    ruling = Skeptic(ctx).judge(batch, round=2)
    assert ruling.verdict == "accept"
    # The reason must state the revised conclusion — a duty cycle — rather than repeat "idle".
    assert "duty-cycle" in ruling.reason


def test_skeptic_accepts_a_clean_orphan_without_fuss(ctx):
    orphans = [c for c in candidates(ctx) if c.matched_rule_ids[0] in {"R-1", "R-2"}]
    assert len(orphans) == 2
    assert all(Skeptic(ctx).judge(o, round=1).verdict == "accept" for o in orphans)


def test_skeptic_refuses_a_third_recheck_on_the_same_finding(ctx):
    batch = next(c for c in candidates(ctx) if c.resource_id.endswith("bbb2"))
    skeptic = Skeptic(ctx)
    ctx.state.facts["recheck_counts"][batch.candidate_id] = 2   # already re-checked twice
    ruling = skeptic.judge(batch, round=3)
    assert ruling.verdict == "reject"
    assert "re-investigated" in ruling.reason
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_skeptic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.skeptic'`

- [ ] **Step 4: Implement `app/agents/skeptic.py`**

```python
from __future__ import annotations

from app.agents.base import Agent
from app.models import Candidate, Ruling

SCHEDULE_SIGNALS = ("month-end", "monthly", "weekly", "nightly", "batch", "cron", "schedule")
RECHECK_LOOKBACK_HOURS = 744


class Skeptic(Agent):
    name = "Skeptic"

    def _schedule_signal(self, candidate: Candidate) -> str | None:
        for item in self.ctx.ledger.resolve(candidate.evidence_refs):
            haystack = " ".join(str(v) for v in list(item.payload.values()) + [item.summary]).lower()
            for signal in SCHEDULE_SIGNALS:
                if signal in haystack:
                    return signal
        return None

    def _recheck_count(self, candidate_id: str) -> int:
        return self.ctx.state.facts.setdefault("recheck_counts", {}).get(candidate_id, 0)

    def judge(self, candidate: Candidate, round: int) -> Ruling:
        """The only entry point. Every ruling leaves here carrying the round that produced it."""
        ruling = self._judge(candidate, round)
        return ruling.model_copy(update={"round": round})

    def _judge(self, candidate: Candidate, round: int) -> Ruling:
        # 1. An idle verdict (R-3) is only safe if nothing suggests the window is unrepresentative.
        if "R-3" in candidate.matched_rule_ids:
            signal = self._schedule_signal(candidate)
            if signal:
                if self._recheck_count(candidate.candidate_id) >= self.ctx.config.max_rechecks_per_finding:
                    reason = self.ctx.generator.complete(
                        prompt="", schema={"name": "verdict_reason"},
                        context={"reason_key": "recheck_cap",
                                 "n": self._recheck_count(candidate.candidate_id)})["reason"]
                    return self._reject(candidate, round, reason)
                request = {"resource_id": candidate.resource_id,
                           "lookback_hours": RECHECK_LOOKBACK_HOURS,
                           "reason": f"schedule signal {signal!r} suggests the window excludes a run"}
                self._emit("request_recheck", round=round, target_agent="Scout",
                           input_summary=f"{candidate.candidate_id} under R-3",
                           output_summary=f"widen to {RECHECK_LOOKBACK_HOURS}h "
                                          f"({signal} found in evidence)",
                           status="recheck", confidence=0.7,
                           evidence_refs=candidate.evidence_refs)
                self.ctx.state.append("recheck", {"candidate_id": candidate.candidate_id,
                                                  "round": round, "signal": signal,
                                                  "lookback_hours": RECHECK_LOOKBACK_HOURS})
                return Ruling(candidate_id=candidate.candidate_id, verdict="recheck",
                              reason=f"a schedule signal ({signal}) is present, so the requested "
                                     f"window may exclude the most recent run",
                              request=request)

        # 2. A low mean with a real peak is a duty-cycle problem, not idleness.
        if "R-4" in candidate.matched_rule_ids:
            reason = self.ctx.generator.complete(
                prompt="", schema={"name": "verdict_reason"},
                context={"reason_key": "frequency_mismatch"})["reason"]
            self._emit("validate_finding", round=round, target_agent="Writer",
                       input_summary=f"{candidate.candidate_id} under R-4",
                       output_summary="accepted: duty cycle, not idle",
                       confidence=0.85, evidence_refs=candidate.evidence_refs)
            return Ruling(candidate_id=candidate.candidate_id, verdict="accept",
                          reason=reason, revised_claim=candidate.claim)

        # 3. Everything else: accept, with the confidence the evidence supports.
        self._emit("validate_finding", round=round, target_agent="Writer",
                   input_summary=candidate.candidate_id,
                   output_summary=f"accepted under {','.join(candidate.matched_rule_ids)}",
                   confidence=candidate.confidence, evidence_refs=candidate.evidence_refs)
        return Ruling(candidate_id=candidate.candidate_id, verdict="accept",
                      reason="no contradicting evidence found in the consulted sources")

    def _reject(self, candidate: Candidate, round: int, reason: str) -> Ruling:
        self._emit("validate_finding", round=round, target_agent="Planner",
                   input_summary=candidate.candidate_id, output_summary=f"rejected: {reason}",
                   status="rejected", confidence=0.8, evidence_refs=candidate.evidence_refs)
        return Ruling(candidate_id=candidate.candidate_id, verdict="reject", reason=reason)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_skeptic.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add app/agents/skeptic.py app/models.py tests/test_skeptic.py
git commit -m "feat: Skeptic rejects, demands a wider window, and accepts revised conclusions"
```

---

### Task 10: The Writer and the report renderer

**Files:**
- Create: `app/agents/writer.py`, `app/report.py`, `tests/test_writer.py`

**Interfaces:**
- Consumes: `AgentContext`, `Candidate`, `Ruling`, `EvidenceLedger`, `analysis`.
- Produces: `UntraceableFigureError`; `assert_figures_traceable(text: str, allowed: set[str]) -> None`; `Writer(ctx)` with `synthesise(*, candidates, rulings, undetermined, sources, status, caps_hit) -> RunReport`; `render_markdown(report: RunReport) -> str` in `app/report.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_writer.py
import pytest
from app.agents.writer import UntraceableFigureError, assert_figures_traceable


def test_a_figure_with_no_evidence_is_refused():
    allowed = {"168", "0.83", "5"}
    assert_figures_traceable("mean 0.83% over 168h against a 5% threshold", allowed)
    with pytest.raises(UntraceableFigureError):
        assert_figures_traceable("we will save 999.99 per month", allowed)


def test_allowed_set_is_built_from_ledger_payloads(tmp_path):
    from app.evidence import EvidenceLedger
    ledger = EvidenceLedger()
    ledger.add(source="telemetry", kind="cpu_stats", resource_id="r1", summary="mean 0.83%",
               payload={"mean": 0.83, "coverage_hours": 168.0})
    allowed = {token for item in ledger.all()
               for token in str(item.payload).replace(",", " ").replace(":", " ").replace("}", " ").replace("{", " ").split()}
    assert_figures_traceable("mean 0.83 over 168.0h", allowed | {"0.83", "168.0"})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_writer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.writer'`

- [ ] **Step 3: Implement `app/agents/writer.py`**

```python
from __future__ import annotations

import re

from app.agents.base import Agent
from app.models import (Candidate, Finding, RunReport, Ruling, SourceStatus, Undetermined,
                        VerdictRecord)

NUMERIC = re.compile(r"\d+(?:\.\d+)?")
ALLOWED_LITERALS = {"1", "2", "3", "4", "5", "7", "10", "20", "25", "41", "60", "168", "300",
                    "540", "730", "744", "0"}


class UntraceableFigureError(Exception):
    """Raised when prose contains a number that no evidence supports."""


def figures_in(text: str) -> set[str]:
    return set(NUMERIC.findall(text))


def assert_figures_traceable(text: str, allowed: set[str]) -> None:
    for token in figures_in(text):
        if token not in allowed and token not in ALLOWED_LITERALS:
            raise UntraceableFigureError(f"figure {token!r} in {text!r} has no supporting evidence")


class Writer(Agent):
    name = "Writer"

    def allowed_figures(self, candidates: list[Candidate]) -> set[str]:
        allowed = set(ALLOWED_LITERALS)
        for item in self.ctx.ledger.all():
            allowed |= figures_in(str(item.payload))
        for candidate in candidates:
            allowed |= figures_in(str(candidate.impact))
            allowed |= figures_in(str(candidate.stats))
        return allowed

    def synthesise(self, *, candidates: list[Candidate], rulings: dict[str, Ruling],
                   undetermined: list[Undetermined], sources: list[SourceStatus],
                   status: str, caps_hit: list[str]) -> RunReport:
        allowed = self.allowed_figures(candidates)
        # A finding is `revised` when an earlier finding about the same resource and class was
        # withdrawn — that pairing is the visible trace of the agent changing its mind.
        withdrawn = {(c.resource_id, c.finding_class) for c in candidates
                     if rulings[c.candidate_id].verdict == "reject" or c.superseded_by}
        findings: list[Finding] = []
        for candidate in candidates:
            ruling = rulings[candidate.candidate_id]
            resource = self.ctx.state.facts["resources"].get(candidate.resource_id)
            text = candidate.claim
            if resource is not None:
                # A resource's own name is an identifier, not an asserted quantity: the digits in
                # `vol-orphan-100g` are not a figure anyone has to support with evidence.
                text = text.replace(resource.display_name, "[resource]")
            assert_figures_traceable(text, allowed)
            if ruling.verdict == "reject" or candidate.superseded_by:
                finding_status = "rejected"
            elif (candidate.resource_id, candidate.finding_class) in withdrawn:
                finding_status = "revised"
            else:
                finding_status = "accepted"
            findings.append(Finding(
                finding_id=candidate.candidate_id, resource_id=candidate.resource_id,
                resource_class=candidate.resource_class, **{"class": candidate.finding_class},
                claim=ruling.revised_claim or candidate.claim,
                evidence_refs=candidate.evidence_refs, impact=candidate.impact,
                confidence=round(candidate.confidence if ruling.verdict != "reject" else 0.0, 2),
                status=finding_status, falsifier=candidate.falsifier,
                history=[VerdictRecord(round=ruling.round, verdict=ruling.verdict,
                                       reason=ruling.reason)]))

        accepted = [f for f in findings if f.status in {"accepted", "revised"}]
        rejected = [f for f in findings if f.status == "rejected"]
        spend = sum(f.impact.get("value", 0.0) for f in findings)
        reported = sum(f.impact.get("value", 0.0) for f in accepted)

        summary = {
            "resources_examined": len(self.ctx.state.facts["resources"]),
            "findings_accepted": len(accepted),
            "findings_rejected": len(rejected),
            "spend_audited_usd_per_month": round(spend, 2),
            "waste_found_usd_per_month": round(reported, 2),
            "unattributed_ratio": round(
                len([f for f in accepted if f.finding_class == "unattributed"])
                / max(1, len(self.ctx.state.facts["resources"])), 3),
        }
        generated = self.ctx.generator.complete(
            prompt="", schema={"name": "run_summary"},
            context={"resources": summary["resources_examined"], "sources": len(sources),
                     "accepted": len(accepted), "rejected": len(rejected),
                     "undetermined": len(undetermined)})
        summary["narrative"] = generated["summary"]

        self._emit("synthesise", input_summary=f"{len(accepted)} accepted, {len(rejected)} rejected",
                   output_summary=summary["narrative"], confidence=1.0,
                   evidence_refs=[ref for f in findings for ref in f.evidence_refs])

        return RunReport(run_id=self.ctx.config.run_id, status=status,
                         mode="sample" if self.ctx.config.sample_mode else "live",
                         sources=sources, summary=summary, findings=findings,
                         undetermined=undetermined, caps_hit=caps_hit)
```

Note: `monthly_cost` is imported but the Writer never calls it — figures arrive pre-computed on each `Candidate`. Remove the unused import at review; the plan keeps it visible here so the reviewer sees the intent that the Writer does not compute costs.

- [ ] **Step 4: Implement `app/report.py`**

```python
from __future__ import annotations

from app.models import RunReport

STATUS_ORDER = {"accepted": 0, "revised": 1, "rejected": 2}


def render_markdown(report: RunReport) -> str:
    lines = [
        f"# Tenancy audit — run `{report.run_id}`",
        "",
        f"- **Status:** {report.status}",
        f"- **Mode:** {report.mode}",
        f"- **Sources:** " + ", ".join(f"{s.name} ({s.backend}{', degraded' if s.degraded else ''})"
                                       for s in report.sources),
        f"- **Caps hit:** {', '.join(report.caps_hit) if report.caps_hit else 'none'}",
        "",
        "## Summary",
        "",
    ]
    lines += [f"- **{k.replace('_', ' ')}:** {v}" for k, v in report.summary.items()]
    lines += ["", "## Findings", ""]
    for finding in sorted(report.findings, key=lambda f: STATUS_ORDER[f.status]):
        lines += [
            f"### {finding.finding_id} — {finding.claim}",
            "",
            f"- Resource: `{finding.resource_id}` ({finding.resource_class})",
            f"- Class: {finding.finding_class}",
            f"- Verdict: **{finding.status}** (confidence {finding.confidence})",
            f"- Impact: {finding.impact.get('value')} {finding.impact.get('kind')}",
            f"- Evidence: {', '.join(finding.evidence_refs)}",
            f"- Would be withdrawn by: {finding.falsifier}",
        ]
        for record in finding.history:
            lines.append(f"- Round {record.round}: {record.verdict} — {record.reason}")
        lines.append("")
    if report.undetermined:
        lines += ["## Not determined", ""]
        lines += [f"- `{u.resource_id}` — {u.reason}" for u in report.undetermined]
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_writer.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add app/agents/writer.py app/report.py tests/test_writer.py
git commit -m "feat: Writer that refuses untraceable figures, plus the Markdown report renderer"
```

---

### Task 11: The bounded loop, degradation, and the canonical run end to end

**Amended during the build (2026-09-24).** Two changes, both forced by a real failure rather than a
preference:

1. **The wall clock was implemented but untested.** `pytest -k cap` covered the round, resource and
   re-check caps and never touched `_budget_exceeded`, so the DoD line "no silent caps" rested on
   inspection. Two tests now drive a fake monotonic clock (`Clock` in `tests/test_loop.py`): the
   soft cap must be logged as `capped` without killing the run, and the hard cap must stop the loop
   and still produce a report.
2. **The hard cap exposed an honesty defect.** A candidate the Skeptic answered with `recheck`, and
   that the loop then never returned to, fell through the Writer's status branches to `accepted` —
   so a truncated run published the very claim the Skeptic had refused to conclude, using its
   original unrevised text. The loop now collects unresolved candidates (verdict `recheck` with no
   `superseded_by`), emits a `not_concluded` trace line, and reports them under `undetermined` with
   the reason. The superseded case is unaffected: in the canonical run `C-001` carries
   `superseded_by = C-005` and is still reported as `rejected`, which is what the money shot needs.

Pinned by `test_the_hard_wall_clock_stops_the_run_rather_than_letting_it_hang`. Re-running
`scripts/run_examples.sh` after this change regenerated all three scenarios with identical findings,
statuses and claims — the fix touches only the path where the loop gives up.

**Files:**
- Create: `app/loop.py`, `tests/test_loop.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `Orchestrator(ctx, scenario_dir=None)` with `run() -> RunReport`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_loop.py
import io, json, socket
from pathlib import Path
import pytest
from app.agents.base import AgentContext
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import RulesGenerator
from app.loop import Orchestrator
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer

SCEN = Path("data/scenarios/example_1")


def build(tmp_path, **request):
    cfg = RunConfig.from_env_and_request({"sample_mode": True, **request})
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=60)
    sources = {name: get_source(name, cfg, scenario_dir=SCEN)
               for name in ("inventory", "telemetry", "iac", "policy")}
    ctx = AgentContext(config=cfg, sources=sources, generator=RulesGenerator(),
                       state=RunState(cfg.run_id, tmp_path),
                       trace=Tracer(cfg.run_id, tmp_path, stream=io.StringIO()),
                       ledger=EvidenceLedger(), scope=scope)
    return cfg, ctx


def actions(ctx):
    return [json.loads(line)["action"] for line in ctx.trace.path.read_text().splitlines()]


def agents(ctx):
    return {json.loads(line)["agent_name"] for line in ctx.trace.path.read_text().splitlines()}


def test_canonical_run_rejects_the_idle_claim_and_revises_it(tmp_path):
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()

    batch = [f for f in report.findings if f.resource_id.endswith("bbb2")]
    assert [f.status for f in batch] == ["rejected", "revised"]
    rejected, revised = batch
    assert revised.claim != rejected.claim      # the conclusion actually changed
    assert "peaks at" in revised.claim          # and cites the burst that forced the change
    assert report.status == "success"
    assert report.mode == "sample"
    assert report.caps_hit == []


def test_report_finds_both_orphans_and_the_unattributed_instance(tmp_path):
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()
    classes = {(f.resource_id[-4:], f.finding_class) for f in report.findings
               if f.status in {"accepted", "revised"}}
    assert ("eee5", "cost_waste") in classes        # detached block volume
    assert ("fff6", "cost_waste") in classes        # unattached reserved IP
    assert ("ddd4", "unattributed") in classes      # absent from every Terraform file
    assert report.summary["waste_found_usd_per_month"] > 0
    assert report.summary["findings_rejected"] == 1
    assert report.summary["unattributed_ratio"] > 0


def test_insufficient_telemetry_lands_in_undetermined(tmp_path):
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()
    reasons = {u.resource_id[-4:]: u.reason for u in report.undetermined}
    assert "ddd4" in reasons
    assert "41h of 168h" in reasons["ddd4"]


def test_the_trace_shows_at_least_two_agents_handing_off_and_a_recheck(tmp_path):
    cfg, ctx = build(tmp_path)
    Orchestrator(ctx).run()
    assert {"Planner", "Scout", "Skeptic", "Writer"} <= agents(ctx)
    assert "request_recheck" in actions(ctx)
    assert "validate_finding" in actions(ctx)
    handoffs = [json.loads(l)["target_agent"] for l in ctx.trace.path.read_text().splitlines()]
    assert "Scout" in handoffs and "Skeptic" in handoffs and "Writer" in handoffs


def test_sample_mode_makes_no_network_calls(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("sample mode attempted a network call")
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(socket, "create_connection", explode)
    cfg, ctx = build(tmp_path)
    report = Orchestrator(ctx).run()
    assert report.status == "success"


def test_max_rounds_is_enforced_and_logged_as_capped(tmp_path):
    cfg, ctx = build(tmp_path, caps={"max_rounds": 1})
    report = Orchestrator(ctx).run()
    assert "max_rounds" in report.caps_hit
    assert report.status == "capped"


def test_an_unavailable_source_degrades_and_is_named_in_the_report(tmp_path):
    cfg, ctx = build(tmp_path)

    class Broken:
        name = "policy"

        def fetch(self, scope):
            raise RuntimeError("simulated outage")

    ctx.sources["policy"] = Broken()
    report = Orchestrator(ctx, scenario_dir=SCEN).run()
    policy = next(s for s in report.sources if s.name == "policy")
    assert policy.degraded is True
    assert "outage" in (policy.reason or "")


def test_no_policy_rules_yields_partial_and_an_explanation(tmp_path):
    cfg, ctx = build(tmp_path)

    class EmptyPolicy:
        name = "policy"

        def fetch(self, scope):
            from app.sources.base import SourceResult
            return SourceResult(source="policy", backend="fixture", records=[])

    ctx.sources["policy"] = EmptyPolicy()
    report = Orchestrator(ctx).run()
    assert report.status == "partial"
    assert report.findings == []
    assert any(u.resource_id == "scope" for u in report.undetermined)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_loop.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.loop'`

- [ ] **Step 3: Implement `app/loop.py`**

```python
from __future__ import annotations

import time
from pathlib import Path

from app.agents.base import AgentContext
from app.agents.planner import Planner
from app.agents.scout import Scout
from app.agents.skeptic import Skeptic
from app.agents.writer import Writer
from app.models import Candidate, Ruling, SourceStatus, Undetermined
from app.sources.base import Scope
from app.sources import get_source


class Orchestrator:
    def __init__(self, ctx: AgentContext, scenario_dir: Path | None = None) -> None:
        self.ctx = ctx
        self.scenario_dir = scenario_dir
        self.planner = Planner(ctx)
        self.scout = Scout(ctx)
        self.skeptic = Skeptic(ctx)
        self.writer = Writer(ctx)
        self.rulings: dict[str, Ruling] = {}
        self.caps_hit: list[str] = []
        self.sources_status: list[SourceStatus] = []
        self._started = time.monotonic()

    # --- source access with retry, then fixture fallback, then honest failure ---------------
    def _fetch(self, name: str, scope: Scope):
        source = self.ctx.sources[name]
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                result = source.fetch(scope)
                self.ctx.trace.emit(agent_name="Planner", action="source_ok",
                                    input_summary=f"{name} attempt {attempt}",
                                    output_summary=f"{len(result.records)} records",
                                    retry_count=attempt - 1, status="success")
                return result, SourceStatus(name=name, backend=result.backend)
            except Exception as exc:                      # noqa: BLE001 - degraded, not swallowed
                last_error = exc
                self.ctx.trace.emit(agent_name="Planner", action="source_call_failed",
                                    input_summary=f"{name} attempt {attempt}",
                                    output_summary=f"{type(exc).__name__}: {exc}",
                                    retry_count=attempt - 1, status="retrying")

        if self.scenario_dir is not None:
            fallback = get_source(name, self.ctx.config.model_copy(update={"sample_mode": True}),
                                  scenario_dir=self.scenario_dir)
            result = fallback.fetch(scope)
            self.ctx.trace.emit(agent_name="Planner", action="source_degraded",
                                input_summary=name, output_summary="fell back to fixture data",
                                status="degraded", retry_count=1)
            return result, SourceStatus(name=name, backend="fixture", degraded=True,
                                        reason=str(last_error))

        self.ctx.trace.emit(agent_name="Planner", action="source_unavailable",
                            input_summary=name, output_summary="no fallback available",
                            status="failed", retry_count=1)
        return None, SourceStatus(name=name, backend="live", degraded=True, reason=str(last_error))

    def _hydrate(self) -> None:
        scope = self.ctx.scope
        for name in ("inventory", "iac", "policy"):
            result, status = self._fetch(name, scope)
            self.sources_status.append(status)
            if result is None:
                continue
            if name == "inventory":
                from app.models import Resource
                for record in result.records:
                    resource = Resource(**record)
                    self.ctx.state.facts["resources"][resource.resource_id] = resource
            elif name == "iac":
                from app.models import IaCDeclaration
                self.ctx.state.facts["declarations"] = [IaCDeclaration(**d) for d in result.records]
            else:
                from app.models import PolicyRule
                self.ctx.state.facts["rules"] = [PolicyRule(**r) for r in result.records]
        self.ctx.state.append("hydrate", {
            "resources": len(self.ctx.state.facts["resources"]),
            "declarations": len(self.ctx.state.facts["declarations"]),
            "rules": len(self.ctx.state.facts["rules"])})
        self.ctx.trace.emit(agent_name="Scout", action="hydrate",
                            input_summary="inventory, iac, policy",
                            output_summary=f"{len(self.ctx.state.facts['resources'])} resources",
                            confidence=1.0)

    def _budget_exceeded(self) -> bool:
        elapsed = time.monotonic() - self._started
        if elapsed > self.ctx.config.wall_clock_hard_s:
            self.caps_hit.append("wall_clock_hard_s")
            self.ctx.trace.emit(agent_name="Planner", action="cap_hit",
                                input_summary="wall clock",
                                output_summary=f"{elapsed:.0f}s exceeds "
                                               f"{self.ctx.config.wall_clock_hard_s}s",
                                status="capped")
            return True
        if elapsed > self.ctx.config.wall_clock_soft_s and "wall_clock_soft_s" not in self.caps_hit:
            self.caps_hit.append("wall_clock_soft_s")
            self.ctx.trace.emit(agent_name="Planner", action="cap_hit", input_summary="wall clock",
                                output_summary=f"{elapsed:.0f}s exceeds soft budget",
                                status="capped")
        return False

    def _merge_source_statuses(self, statuses: list[SourceStatus]) -> None:
        for status in statuses:
            self.sources_status = [s for s in self.sources_status if s.name != status.name]
            self.sources_status.append(status)

    def _rules_available(self) -> bool:
        """No policy rules means nothing can be justified. Say so; never invent a finding."""
        if self.ctx.state.facts["rules"]:
            return True
        self.ctx.trace.emit(agent_name="Planner", action="cannot_audit",
                            input_summary="policy rules",
                            output_summary="no rules loaded; no finding can be justified",
                            status="failed")
        return False

    def run(self):
        self._hydrate()
        if not self._rules_available():
            report = self.writer.synthesise(
                candidates=[], rulings={}, sources=self.sources_status, status="partial",
                caps_hit=[],
                undetermined=[Undetermined(
                    resource_id="scope",
                    reason="no policy rules were loaded, so no finding could be justified")])
            report.trace_path = str(self.ctx.trace.path)
            return report
        all_candidates: list[Candidate] = []
        recheck_requests: list[dict] = []
        round_number = 0

        while round_number < self.ctx.config.max_rounds:
            round_number += 1
            self.ctx.state.facts["round"] = round_number
            assignment = self.planner.assign(
                round=round_number,
                resources=list(self.ctx.state.facts["resources"].values()),
                recheck_requests=recheck_requests)

            # The Scout owns the telemetry fetch: it needs a per-resource window and its own
            # recovery, and a second fetch here would double every live API call.
            candidates = self.scout.investigate(assignment)
            self._merge_source_statuses(self.scout.source_statuses())

            if assignment.focus == "recheck":
                # A re-check that reaches a different conclusion supersedes the earlier finding.
                # The superseded candidate is still reported: rejected, with its reason.
                current_ids = {c.candidate_id for c in candidates}
                for candidate in candidates:
                    for previous in all_candidates:
                        if (previous.candidate_id not in current_ids
                                and previous.resource_id == candidate.resource_id
                                and previous.finding_class == candidate.finding_class
                                and previous.superseded_by is None):
                            previous.superseded_by = candidate.candidate_id
                            self.ctx.state.append("supersede", {
                                "superseded": previous.candidate_id,
                                "superseded_by": candidate.candidate_id,
                                "round": round_number})
            all_candidates.extend(candidates)

            recheck_requests = []
            for candidate in candidates:
                ruling = self.skeptic.judge(candidate, round=round_number)
                self.rulings[candidate.candidate_id] = ruling
                self.ctx.state.facts["rulings"][candidate.candidate_id] = ruling.model_dump()
                if ruling.verdict == "recheck":
                    counts = self.ctx.state.facts["recheck_counts"]
                    counts[candidate.candidate_id] = counts.get(candidate.candidate_id, 0) + 1
                    recheck_requests.append(ruling.request)
                self.ctx.state.append("ruling", {"candidate_id": candidate.candidate_id,
                                                 "verdict": ruling.verdict,
                                                 "round": round_number})

            if self._budget_exceeded():
                break
            if not recheck_requests:
                break

        if round_number >= self.ctx.config.max_rounds and recheck_requests:
            self.caps_hit.append("max_rounds")
            self.ctx.trace.emit(agent_name="Planner", action="cap_hit", input_summary="rounds",
                                output_summary=f"{self.ctx.config.max_rounds} rounds reached with "
                                               f"{len(recheck_requests)} request(s) outstanding",
                                status="capped")

        status = "capped" if self.caps_hit else ("partial" if self._any_source_unavailable() else "success")
        report = self.writer.synthesise(candidates=all_candidates, rulings=self.rulings,
                                        undetermined=self.scout.undetermined(),
                                        sources=self.sources_status, status=status,
                                        caps_hit=self.caps_hit)
        report.trace_path = str(self.ctx.trace.path)
        self.ctx.state.append("report", {"status": status, "findings": len(report.findings)})
        return report

    def _any_source_unavailable(self) -> bool:
        return any(s.degraded for s in self.sources_status)
```

Why this task is last: it is the only one that can invalidate the others. The supersession rule
(it writes `Candidate.superseded_by`) and the "no rules, no findings" guard both live here, so
any earlier task's change to the finding model has to be finished before this one can pass.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_loop.py -v`
Expected: 8 passed

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add app/loop.py app/agents/ app/models.py tests/test_loop.py
git commit -m "feat: bounded orchestrator with caps, degradation and the canonical end-to-end run"
```

---

### Task 12: Entry points — `run.py` and `POST /run`

A UI may never be the only way in, so both entry points call the same function.

**Files:**
- Create: `app/api.py`, `app/pipeline.py`, `run.py`, `tests/test_entrypoints.py`

**Interfaces:**
- Consumes: `RunConfig`, `Orchestrator`, `render_markdown`.
- Produces: `run_pipeline(request: dict, scenario_dir: Path | None = None) -> tuple[RunReport, str]` in `app/pipeline.py`; `app.api.app` (FastAPI) exposing `POST /run`; `run.py` with `--input`, `--scenario`, `--out`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_entrypoints.py
import json, subprocess, sys
from pathlib import Path
from fastapi.testclient import TestClient
from app.api import app

SCEN = Path("data/scenarios/example_1")
REQUEST = {"objective": "audit", "sample_mode": True}


def test_post_run_returns_the_documented_shape():
    client = TestClient(app)
    response = client.post("/run", json={**REQUEST, "scenario": str(SCEN)})
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"run_id", "status", "mode", "sources", "summary", "findings",
                         "undetermined", "trace_path"}
    assert body["mode"] == "sample"
    assert any(f["class"] == "cost_waste" for f in body["findings"])


def test_cli_and_http_return_the_same_findings(tmp_path):
    out = tmp_path / "result.json"
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps({**REQUEST, "scenario": str(SCEN)}))
    subprocess.run([sys.executable, "run.py", "--input", str(request_file),
                    "--scenario", str(SCEN), "--out", str(out)], check=True)
    cli = json.loads(out.read_text())
    http = TestClient(app).post("/run", json={**REQUEST, "scenario": str(SCEN)}).json()
    assert len(cli["findings"]) == len(http["findings"])


def test_unknown_scenario_is_a_400_not_a_crash():
    body = TestClient(app).post("/run", json={**REQUEST, "scenario": "data/scenarios/nope"}).json()
    assert "error" in body
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_entrypoints.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.api'`

- [ ] **Step 3: Implement `app/pipeline.py`**

```python
from __future__ import annotations

from pathlib import Path

from app.agents.base import AgentContext
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import get_generator
from app.loop import Orchestrator
from app.models import RunReport
from app.report import render_markdown
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer


def run_pipeline(request: dict, scenario_dir: Path | None = None) -> tuple[RunReport, str]:
    config = RunConfig.from_env_and_request(request)
    scope = Scope(compartment_ids=config.compartment_ids, resource_types=config.resource_types,
                  lookback_hours=config.lookback_hours, resolution_minutes=config.resolution_minutes)
    sources = {name: get_source(name, config, scenario_dir=scenario_dir)
               for name in ("inventory", "telemetry", "iac", "policy")}
    ctx = AgentContext(config=config, sources=sources, generator=get_generator(config),
                       state=RunState(config.run_id, config.logs_dir),
                       trace=Tracer(config.run_id, config.logs_dir),
                       ledger=EvidenceLedger(), scope=scope)
    report = Orchestrator(ctx, scenario_dir=scenario_dir).run()
    markdown = render_markdown(report)
    report_path = config.logs_dir / f"report-{config.run_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    report.report_markdown_path = str(report_path)
    return report, markdown
```

- [ ] **Step 4: Implement `app/api.py` and `run.py`**

```python
# app/api.py
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.pipeline import run_pipeline

app = FastAPI(title="Driftwatch", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run")
def run(request: dict) -> JSONResponse:
    scenario = request.pop("scenario", None)
    scenario_dir = Path(scenario) if scenario else None
    if scenario_dir is not None and not scenario_dir.is_dir():
        return JSONResponse({"error": f"unknown scenario directory: {scenario_dir}"}, status_code=400)
    report, _ = run_pipeline(request, scenario_dir=scenario_dir)
    return JSONResponse(report.model_dump(by_alias=True))
```

```python
# run.py
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an OCI tenancy for waste and drift.")
    parser.add_argument("--input", type=Path, default=None,
                        help="JSON request file, e.g. input_examples/example_1.json")
    parser.add_argument("--scenario", type=Path, default=None,
                        help="fixture scenario directory (sample mode)")
    parser.add_argument("--out", type=Path, default=None, help="write the JSON report here")
    parser.add_argument("--serve", action="store_true", help="run the HTTP API instead")
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        uvicorn.run("app.api:app", host="0.0.0.0", port=8000)
        return 0

    request = json.loads(args.input.read_text()) if args.input else {}
    report, markdown = run_pipeline(request, scenario_dir=args.scenario)
    payload = json.dumps(report.model_dump(by_alias=True), indent=2)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    print(f"\n--- report ---\n{markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`--serve` binds `0.0.0.0`, which is required inside a container.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_entrypoints.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add app/api.py app/pipeline.py run.py tests/test_entrypoints.py
git commit -m "feat: CLI and POST /run entry points sharing one pipeline"
```

---

### Task 13: The other two scenarios and the evaluation harness

Three scenarios that differ meaningfully, plus the scoring harness. This is the task that makes "generated, never hardcoded" checkable.

**Files:**
- Create: `data/scenarios/example_1/ground_truth.json`, `data/scenarios/example_2/{inventory,telemetry,iac,policy,ground_truth}.json`, `data/scenarios/example_3/{inventory,telemetry,iac,policy,ground_truth}.json`, `evals/__init__.py`, `evals/run_eval.py`, `tests/test_eval.py`

**Interfaces:**
- Consumes: `run_pipeline`.
- Produces: `evaluate(scenario_dir: Path) -> dict` with keys `precision`, `recall`, `verdict_accuracy`, `deterministic`; `main()` printing a table and exiting non-zero on any failure.

- [ ] **Step 1: Create the three ground-truth files and the other two scenarios**

`data/scenarios/example_1/ground_truth.json` — the expectations for the scenario built in Task 3.
Note that `batch-01` expects `revised`, not `recheck`: `recheck` is an in-flight verdict, and the
final status is what the harness scores.

```json
{
  "findings": [
    {"resource_id": "ocid1.instance.oc1..••••bbb2", "class": "cost_waste", "expected_verdict": "revised"},
    {"resource_id": "ocid1.volume.oc1..••••eee5",   "class": "cost_waste", "expected_verdict": "accepted"},
    {"resource_id": "ocid1.publicip.oc1..••••fff6", "class": "cost_waste", "expected_verdict": "accepted"},
    {"resource_id": "ocid1.instance.oc1..••••ddd4", "class": "unattributed", "expected_verdict": "accepted"}
  ],
  "must_not_flag": [
    "ocid1.instance.oc1..••••aaa1",
    "ocid1.instance.oc1..••••ccc3"
  ]
}
```

`must_not_flag` holds the two instances that are busy or appropriately loaded — web-01 at a steady
50% and reports-01 at a steady 10%. A run that flags either of them has failed the case the whole
architecture exists to get right.

`example_2` is a **clean tenancy**, and its purpose is to catch a scanner that invents findings: three instances all declared in Terraform with an `iac_address` tag, all with appropriate load (one steady 45%, one steady 70%, one bursty but tagged `schedule=nightly-declared` and present in IaC), no orphaned volumes or IPs. `ground_truth.json` is `{"findings": []}`.

`example_3` exercises a **different failure mode**: five resources where the discriminating evidence is a tag rather than a latency window.

- one instance tagged `role=dr-standby`, mean CPU 0.1%, declared in Terraform, whose declaration message reads `DR standby replica, idle by design` → must **not** be reported;
- one instance with mean CPU 3% and peak 4% over full coverage, untagged, absent from Terraform → **two** findings, `cost_waste` and `unattributed`;
- one instance with mean 30% but only 20% coverage of the requested window → `undetermined`, no finding;
- one detached block volume → `cost_waste`;
- one attached reserved public IP → **no** finding (attached, so R-2 must not fire).

`example_3`'s telemetry `now` is `2026-10-02T00:00:00Z` with the short-coverage series starting `2026-10-01T04:00:00Z`.

`ground_truth.json` shape, for both:

```json
{
  "findings": [
    {"resource_id": "ocid1.instance.oc1..••••cc01", "class": "cost_waste",
     "expected_verdict": "accepted"},
    {"resource_id": "ocid1.instance.oc1..••••cc01", "class": "unattributed",
     "expected_verdict": "accepted"}
  ],
  "must_not_flag": ["ocid1.instance.oc1..••••dd01"]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_eval.py
from pathlib import Path
from evals.run_eval import evaluate


def test_example_1_scores_full_precision_and_recall():
    result = evaluate(Path("data/scenarios/example_1"))
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["deterministic"] is True


def test_example_2_produces_no_findings_at_all():
    result = evaluate(Path("data/scenarios/example_2"))
    assert result["findings_count"] == 0
    assert result["precision"] == 1.0


def test_example_3_respects_must_not_flag():
    result = evaluate(Path("data/scenarios/example_3"))
    assert result["must_not_flag_violations"] == []
    assert result["recall"] == 1.0
    assert result["verdict_accuracy"] == 1.0
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_eval.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evals.run_eval'`

- [ ] **Step 4: Implement `evals/run_eval.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import run_pipeline

ACCEPTED = {"accepted", "revised"}


def _finding_keys(report) -> set[tuple[str, str]]:
    return {(f.resource_id, f.finding_class) for f in report.findings if f.status in ACCEPTED}


def evaluate(scenario_dir: Path) -> dict:
    truth = json.loads((scenario_dir / "ground_truth.json").read_text())
    expected = {(f["resource_id"], f["class"]) for f in truth["findings"]}
    verdicts = {(f["resource_id"], f["class"]): f["expected_verdict"] for f in truth["findings"]}

    first, _ = run_pipeline({"sample_mode": True}, scenario_dir=scenario_dir)
    second, _ = run_pipeline({"sample_mode": True}, scenario_dir=scenario_dir)

    got = _finding_keys(first)
    hits = expected & got
    precision = len(hits) / len(got) if got else 1.0
    recall = len(hits) / len(expected) if expected else 1.0

    correct_verdicts = 0
    for finding in first.findings:
        key = (finding.resource_id, finding.finding_class)
        if key in verdicts and finding.status == verdicts[key]:
            correct_verdicts += 1
    verdict_accuracy = correct_verdicts / len(verdicts) if verdicts else 1.0

    flagged = {f.resource_id for f in first.findings if f.status in ACCEPTED}
    violations = sorted(set(truth.get("must_not_flag", [])) & flagged)

    first_keys = sorted((f.resource_id, f.finding_class, f.status) for f in first.findings)
    second_keys = sorted((f.resource_id, f.finding_class, f.status) for f in second.findings)

    return {
        "scenario": scenario_dir.name,
        "findings_count": len(first.findings),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "verdict_accuracy": round(verdict_accuracy, 3),
        "must_not_flag_violations": violations,
        "deterministic": first_keys == second_keys,
        "status": first.status,
    }


def main() -> int:
    failures = 0
    for scenario in sorted(Path("data/scenarios").glob("example_*")):
        result = evaluate(scenario)
        print(json.dumps(result, indent=2))
        if (result["precision"] < 1.0 or result["recall"] < 1.0
                or result["must_not_flag_violations"] or not result["deterministic"]):
            failures += 1
    print(f"\n{len(list(Path('data/scenarios').glob('example_*')))} scenarios, {failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The determinism check runs the pipeline twice and compares findings including status — a fixture-driven run that is not reproducible is a bug, not a coincidence.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_eval.py -v && python -m evals.run_eval`
Expected: 3 passed; three scenarios, 0 failing

- [ ] **Step 6: Commit**

```bash
git add data/scenarios/ evals/ tests/test_eval.py
git commit -m "feat: three scenarios and the precision/recall/determinism evaluation harness"
```

---

### Task 14: Packaging, examples and disclosures

**Files:**
- Create: `Dockerfile`, `input_examples/example_{1,2,3}.json`, `output_examples/example_{1,2,3}.json`, `output_examples/example_{1,2,3}_report.md`, `logs/.gitkeep`, `scripts/run_examples.sh`
- Modify: `README.md`, `.gitignore`

**Interfaces:**
- Consumes: `run.py`.
- Produces: no code interfaces; produces the submission artifacts.

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY data/ data/
COPY evals/ evals/
COPY scripts/ scripts/
COPY input_examples/ input_examples/
COPY run.py README.md ./
RUN mkdir -p logs

ENV SAMPLE_MODE=true
EXPOSE 8000
CMD ["python", "run.py", "--serve"]
```

- [ ] **Step 2: Write the three input examples**

`input_examples/example_1.json`:

```json
{
  "objective": "audit this tenancy for cost waste and unattributed resources",
  "scope": {"compartment_ids": [], "resource_types": ["compute_instance", "block_volume", "reserved_public_ip"]},
  "telemetry": {"lookback_hours": 168, "resolution_minutes": 5},
  "caps": {"max_rounds": 3, "max_resources": 25, "wall_clock_seconds": 540},
  "sample_mode": true,
  "scenario": "data/scenarios/example_1"
}
```

`example_2.json` and `example_3.json` are identical apart from `"scenario"`. They differ meaningfully in what they contain — a clean tenancy and a tag-discriminated tenancy — not in their JSON shape.

- [ ] **Step 3: Generate the matching outputs and commit one trace per scenario**

```bash
mkdir -p output_examples logs
for n in 1 2 3; do
  python run.py --input input_examples/example_$n.json \
    --scenario data/scenarios/example_$n --out output_examples/example_$n.json \
    > output_examples/example_$n.log
done
python -m evals.run_eval
```

`output_examples/example_N.json` is the report, `output_examples/example_N_report.md` is the
rendered audit, and the run's `logs/trace-*.jsonl` and `logs/state-*.jsonl` are committed as the
evidence. These are **generated by the run that wrote them** — never edited afterwards. If the code
changes, regenerate them and let the diff show what changed.

- [x] **Step 4: Verify the clean-clone path from outside the build tree** — done 2026-09-24

```bash
rm -rf /tmp/driftwatch-clean && git clone . /tmp/driftwatch-clean && cd /tmp/driftwatch-clean
python3.11 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
rm -f .env
SAMPLE_MODE=true python run.py --input input_examples/example_1.json --scenario data/scenarios/example_1
```

Expected: a report on stdout, a trace in `logs/`, no network access needed, no credentials.

**Amended during the build.** The original recipe used `python -m venv`, which on this machine
resolves to 3.9.6 and produced **thirteen** collection errors (`str | None` annotations evaluated
at runtime by pydantic). Pin `python3.11` here — that is the whole point of the step: the
development venv hides this class of failure. The app now also refuses to import below 3.11 with
one actionable line, so a wrong interpreter cannot masquerade as thirteen unrelated bugs.

Verified: Python 3.11.16 venv, `pip install -r requirements.txt`, **63 tests passed** (the suite has
grown since — see the post-build review at the end of this plan), a credential-free `run.py` writing
a full report, and `POST /run` answering HTTP 200 in 20 ms. Re-verified from a fresh clone after the
review fixes: the full suite, CLI exit 0, `POST /run` HTTP 200, evaluator "3 scenarios, 0 failing".

- [ ] **Step 5: Verify the Docker path** — **NOT PERFORMED 2026-09-24: no Docker daemon on the build machine**

```bash
docker build -t driftwatch .
docker run --rm -p 8000:8000 -e SAMPLE_MODE=true driftwatch &
sleep 5
curl -sS -X POST http://localhost:8000/run -H "Content-Type: application/json" \
  -d @input_examples/example_1.json | head -40
```

Expected: JSON with `"mode": "sample"` and a non-empty `findings` array. Note `.env` was never created.

**What was verified instead, so the Dockerfile is not untested by accident:** the exact command the
container runs (`python run.py --serve`) was started locally and served `POST /run` with HTTP 200
in 20 ms on `0.0.0.0:8000`, and `COPY` sources were checked against the tree (`.dockerignore` added
so the build context excludes `.venv`, `logs/`, `output_examples/`). **Re-run this step on a machine
with Docker before submitting, or drop the Dockerfile from the README rather than shipping an
unverified claim.** The README currently states it was not executed.

- [ ] **Step 6: Write the README disclosure section**

Every line below must describe what the code does, not what it was meant to do. Three of them
depend on decisions made outside this plan; the plan states what to write in each case, so no
line can be left as a placeholder.

```markdown
## Disclosure

- **Models and providers:** live mode calls one OpenAI-compatible `chat/completions` endpoint,
  configured by `LLM_BASE_URL` and `LLM_MODEL`. Record the provider and exact model string you
  ran with. If you never configured one, write instead: *"no live provider was configured; both
  modes ran on the deterministic rule engine in `app/generator.py:RulesGenerator`."*
  **No figure in any report is produced by a model** — see "Determinism" below.
- **Agent frameworks:** none. The loop is hand-rolled in `app/loop.py`. No LangGraph, CrewAI,
  AutoGen or similar.
- **Partner technologies:** name each partner you actually mounted and where it sits — for
  example *"Zetaris — behind the `policy` source adapter (`app/sources/`), supplying the
  rule/price reference; without it the `policy` source falls back to `data/scenarios/*/policy.json`."*
  If you mounted none, write: *"no partner technology was mounted; the sponsor layer was
  deliberately out of scope and the design reasons are in `docs/superpowers/specs/`."*
- **External tools and libraries:** `pydantic`, `fastapi`, `uvicorn`, `requests`, `pytest`, and
  `oci` on the live path only.
- **Data sources:** the demo tenancy, the Terraform repository and the price catalog are the
  author's own. Scenarios under `data/scenarios/` are **synthetic**; their telemetry series are
  materialised from the specs in `data/scenarios/*/telemetry.json` rather than captured. No
  employer, customer or third-party data is present anywhere in this repository, and OCIDs in
  shipped artifacts are masked by `scripts/mask_ocids.py`.
- **Adapted open-source code:** list every file adapted from another project, with its licence,
  or write "none".
- **Known limitations:** write these from the code, not from intent. At minimum: the audit
  covers compute instances, block volumes and reserved public IPs only; cost figures are list
  rates from a bundled catalog rather than your actual invoice; `usd_per_month_upper_bound`
  impacts are upper bounds, not savings; findings are recommendations and nothing is remediated.
- **Sample mode:** runs the complete agent on fixture backends with no network and no
  credentials. It does not call a model. The rule engine supplies the same structured outputs a
  model would, so the judgements in a sample-mode run come from the declarative rules in
  `policy.json`, not from a language model.
- **Determinism:** every figure in a report comes from `app/analysis.py`, and the Writer refuses
  to emit a number that no evidence supports (`app/agents/writer.py`).
```

- [ ] **Step 7: Commit**

```bash
git add Dockerfile input_examples/ output_examples/ logs/ scripts/ README.md .gitignore
git commit -m "docs: packaging, three input/output example pairs, generated traces and the README disclosure"
```

---

### Task 15: Live OCI adapters — STRETCH, decided at the 17 Oct checkpoint

Do not start this task before Tasks 1–14 are complete and committed.

**Files:**
- Create: `app/sources/live.py`, `scripts/mask_ocids.py`, `tests/test_live_adapters.py`

**Interfaces:**
- Consumes: `RunConfig`, the `Source` protocol.
- Produces: `get_live_source(name: str, config: RunConfig) -> Source`.

- [x] **Step 1: Write the failing test (no tenancy required)** — done 2026-09-26. Built wider than
  the draft: besides construction and loud failure, the mapping functions are exercised against
  SDK-shaped stubs (instance/volume/IP records, coverage arithmetic, the no-stream case), and the
  whole module is hermetic via an autouse fixture pointing `OCI_CONFIG_FILE` at a path that does
  not exist. The draft's mask_ocids test already lives in `tests/test_mask_ocids.py`.

```python
# tests/test_live_adapters.py
import pytest
from app.config import RunConfig
from app.sources.base import Scope, SourceError
from app.sources.live import get_live_source


def test_live_sources_construct_without_credentials_and_fail_loudly_when_used():
    cfg = RunConfig.from_env_and_request({"sample_mode": False})
    for name in ("inventory", "telemetry", "iac", "policy"):
        source = get_live_source(name, cfg)
        assert source.name == name
    with pytest.raises(SourceError):
        get_live_source("telemetry", cfg).fetch(
            Scope(compartment_ids=[], resource_types=[], lookback_hours=1, resolution_minutes=5))


def test_mask_ocids_rewrites_every_ocid_but_keeps_the_shape():
    from scripts.mask_ocids import mask
    text = '{"id": "ocid1.instance.oc1.ap-singapore-1..••••3f2a"}'
    masked = mask(text)
    assert "ocid1.instance.oc1." in masked
    assert "an9hxljr3f2a" not in masked
```

- [x] **Step 2: Run the test to verify it fails** — done 2026-09-26; 9 failures, all
  `ModuleNotFoundError` for the two adapter modules, as expected.

- [x] **Step 3: Implement the adapters** — done 2026-09-26, deviating from the draft in four ways,
  all recorded in `docs/decisions.md`: volumes and reserved IPs are enumerated too (the draft's
  ComputeClient-only inventory would have left R-1 and R-2 unfireable live); `list_volume_attachments`
  lives on ComputeClient, not BlockstorageClient as the draft's shape implied; the telemetry adapter
  widens resolution past the retention edge (5-minute data is kept 30 days, so a 744 h re-check at
  5 m would silently come back short); and file-backed sources take the run's scenario directory
  instead of a hardcoded `example_1` path.

```python
# app/sources/live.py
from __future__ import annotations

from pathlib import Path

from app.config import RunConfig
from app.sources.base import SourceError
from app.sources.iac_fixture import IaCFixtureSource
from app.sources.oci_inventory import OCIInventorySource
from app.sources.oci_telemetry import OCITelemetrySource
from app.sources.policy_fixture import PolicyFixtureSource

# The IaC repository is a git checkout and the policy reference is a bundled catalog — neither is
# an OCI service, so the same file-backed adapter serves live and sample mode.
FILE_BACKED = {"iac": IaCFixtureSource, "policy": PolicyFixtureSource}
FILE_BACKED_DIR = Path("data/scenarios/example_1")


class UnimplementedLiveSource:
    def __init__(self, name: str) -> None:
        self.name = name

    def fetch(self, scope):
        raise SourceError(f"live backend for {self.name!r} is not implemented")


def get_live_source(name: str, config: RunConfig):
    if name == "inventory":
        return OCIInventorySource(config)
    if name == "telemetry":
        return OCITelemetrySource(config)
    if name in FILE_BACKED:
        return FILE_BACKED[name](FILE_BACKED_DIR)
    raise KeyError(name)
```

```python
# app/sources/oci_inventory.py
from __future__ import annotations

from app.sources.base import SourceError, SourceResult


class OCIInventorySource:
    """Live OCI inventory. Imports the SDK lazily so sample mode never touches it."""

    name = "inventory"
    TIMEOUT_S = 30

    def __init__(self, config) -> None:
        self.config = config

    def _client(self):
        import oci
        try:
            sdk = oci.config.from_file()
            sdk["region"] = sdk.get("region") or None
            return oci.core.ComputeClient(sdk, timeout=self.TIMEOUT_S)
        except Exception as exc:                          # noqa: BLE001
            raise SourceError(f"OCI credentials unavailable: {exc}") from exc

    def fetch(self, scope) -> SourceResult:
        client = self._client()
        compartments = scope.compartment_ids or [self.config.compartment_ids]
        records = []
        for compartment_id in compartments:
            try:
                response = client.list_instances(compartment_id=compartment_id,
                                                 retry_strategy=None)
            except Exception as exc:                      # noqa: BLE001
                raise SourceError(f"list_instances failed: {exc}") from exc
            for instance in response.data:
                shape_config = getattr(instance, "shape_config", None)
                records.append({
                    "resource_id": instance.id,
                    "resource_class": "compute_instance",
                    "display_name": instance.display_name,
                    "compartment_id": instance.compartment_id,
                    "lifecycle_state": instance.lifecycle_state,
                    "time_created": instance.time_created,
                    "shape": instance.shape,
                    "ocpus": getattr(shape_config, "ocpus", None),
                    "memory_gb": getattr(shape_config, "memory_in_gbs", None),
                    "tags": dict(instance.freeform_tags or {}),
                })
        return SourceResult(source=self.name, backend="live", records=records)
```

`app/sources/oci_telemetry.py` follows the same shape against
`oci.monitoring.MonitoringClient.summarize_metrics_data`, with namespace
`oci_computeagent`, metric `CpuUtilization`, `resolution` from
`scope.resolution_minutes`, and the same coverage arithmetic as the fixture: when the returned
window is shorter than requested, set `sufficient=False` and an `insufficient_reason`. It must
share `materialise`-free logic — no fixture code, no interpolation, no defaulting.

- [x] **Step 4: Implement `scripts/mask_ocids.py`** — already built during the review closure
  (2026-09-24), with a lower suffix threshold than this draft and tests in
  `tests/test_mask_ocids.py`; not rebuilt here.

```python
from __future__ import annotations

import re
import sys
from pathlib import Path

OCID = re.compile(r"ocid1\.[a-z0-9]+\.([a-z0-9.-]+)\.([A-Za-z0-9]+)")


def mask(text: str) -> str:
    """Keep the OCID's type and realm readable; replace the unique tail."""
    def replace(match: re.Match) -> str:
        return f"{match.group(1).split('.')[0]}.••••{match.group(2)[-4:]}"
    return OCID.sub(replace, text)


def main() -> int:
    for path in sys.argv[1:]:
        file = Path(path)
        file.write_text(mask(file.read_text()), encoding="utf-8")
        print(f"masked {file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests, then run live once against the lab tenancy** — tests done 2026-09-26
  (109 passing, including the degradation path). **The live run is blocked on the lab tenancy**:
  `docs/lab-tenancy.md` has the provisioning checklist; the month-end cron must be installed by
  29 Sep so the 1 Oct burst exists in history during the window.

Run: `python -m pytest tests/test_live_adapters.py -v`
Then, with `.env` populated from the tenancy: `python run.py --input input_examples/example_1.json`
Expected: `"mode": "live"` in the report and real OCIDs in stdout only — never in committed files.

- [ ] **Step 6: Commit**

```bash
git add app/sources/live.py app/sources/oci_*.py scripts/mask_ocids.py tests/test_live_adapters.py
git commit -m "feat: live OCI inventory and telemetry adapters behind the Source interface"
```

---

### Task 16: Held-out scenario generator — STRETCH

The strongest available answer to "are these outputs hardcoded": score the agent on inputs that did not exist when it was written.

**Files:**
- Create: `scripts/make_scenario.py`, `tests/test_make_scenario.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `build_scenario(seed: int, out_dir: Path) -> Path` writing a complete scenario directory plus its `ground_truth.json`.

- [x] **Step 1: Write the failing test** — done 2026-09-24; the draft's name promised a check it did
  not make ("…and are not the committed ones" asserted nothing about the committed ones), so the
  built test asserts verdict accuracy, determinism and that no generated tenancy shares a resource id
  with a committed one.

```python
# tests/test_make_scenario.py
import json
from pathlib import Path
from evals.run_eval import evaluate
from scripts.make_scenario import build_scenario


def test_generated_scenarios_score_well_and_are_not_the_committed_ones(tmp_path):
    for seed in (11, 29):
        out = build_scenario(seed, tmp_path / f"held_out_{seed}")
        result = evaluate(out)
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["must_not_flag_violations"] == []


def test_two_seeds_produce_different_tenancies(tmp_path):
    a = json.loads((build_scenario(11, tmp_path / "a") / "inventory.json").read_text())
    b = json.loads((build_scenario(11, tmp_path / "b") / "inventory.json").read_text())
    c = json.loads((build_scenario(29, tmp_path / "c") / "inventory.json").read_text())
    assert a == b                      # same seed, same tenancy
    assert a != c                      # different seed, different tenancy
```

- [x] **Step 2: Run the test to verify it fails** — done 2026-09-24; `ModuleNotFoundError: No module
  named 'scripts.make_scenario'`, as predicted.

Run: `python -m pytest tests/test_make_scenario.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.make_scenario'`

- [x] **Step 3: Implement `scripts/make_scenario.py`** — done 2026-09-24, with the amendments below.

```python
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

SHAPES = [("VM.Standard.A1.Flex", 1, 6, 0.01, 0.0015),
          ("VM.Standard.E4.Flex", 2, 8, 0.025, 0.0015),
          ("VM.Standard.E4.Flex", 4, 16, 0.025, 0.0015)]
RULES = json.loads(Path("data/scenarios/example_1/policy.json").read_text())["rules"]


def build_scenario(seed: int, out_dir: Path) -> Path:
    """Writes a complete, never-seen scenario with its own ground truth."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    now = "2026-10-05T00:00:00Z"

    instances, series, declarations, truth, must_not_flag = [], [], [], [], []
    for index in range(rng.randint(2, 5)):
        suffix = f"{seed:02d}{index:02d}"
        rid = f"ocid1.instance.oc1..••••{suffix}"
        shape, ocpus, memory = rng.choice(SHAPES)
        declared = rng.random() < 0.6
        idle = rng.random() < 0.5
        bursty = rng.random() < 0.3
        name = f"{'idle' if idle else 'busy'}-{suffix}"
        tags = {"iac_address": f"oci_core_instance.{name.replace('-', '_')}"} if declared else {}
        if bursty:
            tags["schedule"] = "month-end"
        instances.append({
            "resource_id": rid, "resource_class": "compute_instance", "display_name": name,
            "compartment_id": "ocid1.compartment.oc1..••••lab", "lifecycle_state": "RUNNING",
            "time_created": "2026-08-01T00:00:00Z", "shape": shape, "ocpus": ocpus,
            "memory_gb": memory, "tags": tags})
        spec = {"resource_id": rid, "metric": "CpuUtilization", "start": "2026-09-01T00:00:00Z",
                "baseline": 0.6 if idle else rng.uniform(35.0, 65.0), "jitter": 0.4 if idle else 6.0,
                "bursts": ([{"start": "2026-09-01T02:00:00Z", "hours": 3, "value": 58.0}]
                           if bursty else [])}
        series.append(spec)
        if declared:
            declarations.append({
                "address": tags["iac_address"], "resource_type": "oci_core_instance",
                "declared_name": name, "file_path": f"terraform/{name}.tf",
                "last_commit": f"{seed:07x}", "commit_message":
                    "month-end batch worker" if bursty else "provisioned by IaC",
                "author": "generated@example.invalid"})

        if idle:
            truth.append({"resource_id": rid, "class": "cost_waste",
                          "expected_verdict": "revised" if bursty else "accepted"})
        if not declared:
            truth.append({"resource_id": rid, "class": "unattributed",
                          "expected_verdict": "accepted"})
        if not idle and declared:
            must_not_flag.append(rid)      # busy and declared: the case that must stay quiet

    (out_dir / "inventory.json").write_text(json.dumps(
        {"scenario_id": out_dir.name, "resources": instances}, indent=2))
    (out_dir / "telemetry.json").write_text(json.dumps(
        {"scenario_id": out_dir.name, "now": now, "series": series}, indent=2))
    (out_dir / "iac.json").write_text(json.dumps(
        {"scenario_id": out_dir.name, "declarations": declarations}, indent=2))
    (out_dir / "policy.json").write_text(json.dumps(
        {"scenario_id": out_dir.name, "rules": RULES}, indent=2))
    (out_dir / "ground_truth.json").write_text(json.dumps(
        {"findings": truth, "must_not_flag": must_not_flag}, indent=2))
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(build_scenario(args.seed, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Expected ground truth for a bursty idle instance is `revised`, because R-3 fires first and the
Skeptic's schedule-signal check widens the window, after which R-4 fires. That is the canonical
behaviour reproducing itself on unseen input — the point of this task.

- [x] **Step 4: Run the tests** — done 2026-09-24; three tests pass, and `--score 10` reports ten
  unseen tenancies with precision 1.0, recall 1.0, verdict accuracy 1.0, deterministic, 0 failing.

Run: `python -m pytest tests/test_make_scenario.py -v`
Expected: 2 passed

- [x] **Step 5: Commit** — done 2026-09-24, as `3516933` (the loop defect it found was committed
  separately as `ccc0322`, and the evidence-filing fix as `23accdc`).

**Amendment (2026-09-24, as built).** Three things differ from the draft above, all recorded here
rather than smoothed over:

1. **The burst is placed by window arithmetic, not by a fixed date.** The draft pinned the month-end
   burst to `2026-09-01T02:00:00Z` with `now = 2026-10-05` — 34 days back, outside both the 7-day
   window the run requests *and* the 31-day window the Skeptic widens to. The burst would never have
   materialised, so the ground truth's `revised` verdict could not have happened and the test would
   have failed against a *correct* agent. The burst is now derived from the scenario's `now`, 20 days
   back: inside 31 days, outside 7. That is the only arrangement in which the re-check mechanism can
   reproduce itself, and it is explained in the module docstring because it is the load-bearing part.
2. **`scenario_id` comes from the seed, not the output directory** (found by the draft's own
   determinism test once it was written): the same seed written to two paths must produce
   byte-identical files, or held-out evidence can never be diffed.
3. **Ground truth covers volumes and reserved public IPs too**, with attached twins placed in
   `must_not_flag` — the draft generated only compute instances, so R-1 and R-2 were never exercised
   on unseen input. A `--score N` mode was added as well, and `scripts/run_examples.sh` writes its
   results to `output_examples/held_out.txt` so the held-out numbers are generated evidence rather
   than a claim in prose.

**What this task found, which is the point of it:** seed 6 carries a shape no committed scenario has
(an idle, bursty, *undeclared* instance) and exposed a real defect — the re-check re-derived that
instance's `unattributed` finding identically, and the loop superseded the untouched original, so the
report claimed a change of mind that never happened. Fixed in `app/loop.py` (`ccc0322`) with the
shape pinned in `tests/test_loop.py`. Ten seeds now score 1.0/1.0/1.0, 0 failing; before the fix,
seed 6 scored 0.8 on verdict accuracy.

```bash
git add scripts/make_scenario.py tests/test_make_scenario.py
git commit -m "feat: held-out scenario generator with ground truth, scored by the eval harness"
```

---

## Post-build review (added 2026-09-24, after Task 14)

The plan's execution mode called for one fresh reviewer over the whole branch once the must-ship
path was complete. That review ran read-only with a single instruction: verify every claim by
running code, not by reading prose. It found **five blockers and eleven lesser issues**, all
reproduced before being fixed, and all five blockers are now closed with regression tests.

| # | Blocker the review found | Where it was | Closed by |
|---|---|---|---|
| 1 | The README advertised a live OCI path that does not exist; `SAMPLE_MODE=false` degraded to fixtures and still reported `mode: live` with invented CPU figures | `app/sources/live.py:15`, README | Honest README (§Run it, diagram, disclosure), `summary.backends` / `sources_degraded`, stderr warning in `app/pipeline.py` |
| 2 | The 25-resource cap truncated silently and `resources_examined` reported the whole tenancy | `app/agents/planner.py:18`, `app/agents/writer.py` | `max_resources` recorded in `caps_hit` + `cap_hit` trace line; `resources_examined` vs `resources_in_scope` |
| 3 | With telemetry unavailable the Scout invented `mean 0.0 / coverage 1.0 / sufficient True` and published it as a finding | `app/agents/scout.py:91` | Single `NO_TELEMETRY_STATS` (`sufficient: False`) → `undetermined`, no CPU rule fires; `candidate.stats` removed as a self-vouching figure source |
| 4 | The figure guard covered only `candidate.claim`; the narrative and every verdict reason reached the report unchecked | `app/agents/writer.py:90` | Guard applied to claim, revised claim, reason and narrative, with a separate currency check |
| 5 | The re-check cap was unreachable (keyed by candidate id, and each round mints a new one) and wouldn't have been reported as a cap | `app/agents/skeptic.py:53` | Keyed by resource + finding class; firing records `max_rechecks_per_finding` |

Lesser issues closed in the same pass: the wall clock sampled only between rounds (now before each
resource, with model timeouts trimmed to the remaining budget); a missing fixture raising out of
`run()` (now degrades); leaked trace/state handles (now closed in `run_pipeline`); a vacuous 1.0
precision for a scenario with no expected findings (now `n/a`); `mask_ocids.py` missing short-suffix
OCIDs; and four README claims that overstated the code.

A follow-up pass over the same findings list closed three half-closed items: the magnitude whitelist
(finding 6) is now derived from the run's configuration instead of hardcoded, with money checked
against a second, stricter tier of computed figures; the cap's narrative half is asserted rather
than correct-by-construction (finding 2); and a corrupt — not merely missing — fixture is a test
(finding 9). The three scenarios regenerate byte-identically apart from the run id.

The three committed scenarios regenerate with identical findings, statuses, claims and caps — the
evidence that these fixes changed only the paths where something goes wrong. Full record:
`docs/decisions.md`, 2026-09-24.

### Held-out pass (Task 16, 2026-09-24)

Task 16 was built before the 17 Oct checkpoint because it needs no credentials and so is the one
stretch item that can be verified now. It paid for itself immediately: ten generated tenancies
exposed two defects that neither the three hand-written scenarios nor the independent review of them
had surfaced.

1. **A re-check that changed nothing was reported as a revision** (`app/loop.py`). An idle, bursty,
   *undeclared* instance is re-investigated for its cost verdict, and the Scout — working per
   resource, not per class — re-derives its `unattributed` finding identically. Supersede matched on
   resource and class alone, so the untouched original was marked `rejected` and its identical repeat
   `revised`: a change of mind the agent never had. Supersede now requires a genuinely different
   conclusion; a repeat is recorded as `duplicate_finding` and dropped.
2. **The committed traces were one scenario behind** (`scripts/run_examples.sh`). Artifacts were filed
   by file mtime, and two runs land in the same second, so `trace-example_2.jsonl` shipped carrying
   example_1's run. Paths are now read from the report the run wrote, and
   `tests/test_committed_evidence.py` asserts every committed artifact belongs to its own report.

Ten held-out seeds score precision 1.0, recall 1.0, verdict accuracy 1.0, deterministic, 0 failing;
before the loop fix, seed 6 scored 0.8 on verdicts. The lesson is in `docs/insights.md`.

### Task 15 adapters built early (2026-09-26)

Task 15's Steps 1–4 were built ahead of the 17 Oct checkpoint because none of them needs a tenancy —
only Step 5's live verification does, and that is gated on `docs/lab-tenancy.md` existing. The
checkpoint question changes from "should we build the live path?" to "did the live run work?",
which is a much smaller thing to answer with two weeks of window left.

Four deviations from the draft, all discovered by checking the pinned SDK (`oci==2.135.0`) rather
than assuming its shape:

1. **Inventory covers all three resource classes.** The draft enumerated instances only; R-1
   (unattached volume) and R-2 (unattached reserved IP) would then never fire on a live tenancy —
   two of the lab's six pathologies un-auditable. The built adapter lists volumes via
   `BlockstorageClient.list_volumes`, reserved IPs via `VirtualNetworkClient.list_public_ips`
   (`scope="REGION"`), and derives a volume's `attached` flag from `list_volume_attachments` —
   which lives on **ComputeClient**, not BlockstorageClient as the draft implied. A volume object
   says nothing about whether anything is mounted on it; the attachment does.
2. **Telemetry resolution respects retention.** Monitoring keeps 5-minute-resolution data for
   30 days. The Skeptic's re-check asks for 744 h (31 days) — at 5-minute resolution the service
   would silently return a short window, and the coverage math would report the *adapter's*
   request as the resource's insufficiency. `resolution_for()` widens to hourly past the 720 h
   edge (hourly is kept 90 days), which is also the resolution the fixture series use.
3. **File-backed sources take the run's scenario directory**, not a hardcoded `example_1` path —
   a live run against the lab tenancy must read `data/scenarios/lab_live/iac.json`, and a
   hardcoded path would have quietly scored the lab's resources against the demo's declarations.
4. **Credentials fail as one named error.** Missing compartment and unreachable config file are
   both reported together (`"; ".join(problems)`), naming `OCI_COMPARTMENT_ID` and the config
   path/profile, so the stderr line tells the operator which of two things to fix.

Hermeticity: every test pins `OCI_CONFIG_FILE` to a nonexistent path via an autouse fixture, and
`tests/test_entrypoints.py`'s degradation test now does too — on a machine that *has* real OCI
credentials, the suite must still exercise the failure path rather than silently auditing
someone's tenancy during `pytest`. The SDK itself is imported lazily inside fetch paths, so
sample mode never loads it (that claim is now tested by construction, not promised in prose).

**Still open — Step 5:** one live run against the lab tenancy, which needs the tenancy provisioned
by 29 Sep for the 1 Oct month-end burst to exist in history during the build window
(`docs/lab-tenancy.md`).

---

## Definition of done

Mapped to the spec's acceptance criteria (§13). Every line must be observed, not assumed.

| Spec | Where it is verified |
|---|---|
| 1. `rm .env` + Docker + `curl` returns a report | Task 14 Step 5 |
| 2. Fresh clone runs with no manual steps | Task 14 Step 4 |
| 3. A run finishes well inside 10 minutes, no silent caps | Task 11 `test_max_rounds_is_enforced_and_logged_as_capped`, `test_the_soft_wall_clock_is_logged_as_a_cap_but_does_not_stop_the_run`, `test_the_hard_wall_clock_stops_the_run_rather_than_letting_it_hang`; a capped run cannot present an un-concluded candidate as a finding |
| 4. Trace shows four agents, handoff, a rejection with a reason, a re-check, a revision | Task 11 `test_the_trace_shows_at_least_two_agents_handing_off_and_a_recheck` |
| 5. Three input examples and three matching outputs, differing meaningfully | Task 13, Task 14 Step 3 |
| 6. `evals/` reports precision/recall; held-out scoring if Task 16 shipped | Task 13, **Task 16 shipped 2026-09-24** — `output_examples/held_out.txt`, `tests/test_make_scenario.py` |
| 7. No secret, real OCID or employer artifact in the repo, examples, logs or video | `tests/test_mask_ocids.py` (tests the tool *and* scans every tracked file) |
| 8. README discloses every required item | Task 14 Step 6 |
| 9. Every README claim is one a script or a reviewer can check | Post-build review, above; `docs/decisions.md` |
| 10. Every committed trace, state file and report belongs to the run it is filed under | `tests/test_committed_evidence.py` |
| Regression sweep across every task | `python -m pytest -q` |

---

## Deliberately not planned

Named here so a future session does not quietly add them, and so the spec's coverage is
accountable rather than merely absent:

| Excluded | Spec reference | Why |
|---|---|---|
| **Sponsor layer** (Meterless Markovian or H-MEM, or a Zetaris adapter) | §5.11 | Earnable, not load-bearing. Mounted only after Tasks 1–14 are complete and green — it is the 10 Sponsor Tech points, not the 30 Impact points. `RunState` (`app/state.py`) is already the seam it would mount at. |
| **Security / compliance findings** | §3.2 | A second rule set and a second report format for no additional demo value. |
| **Any UI** | §3.2 | A UI may never be the only entry point, so it is pure cost. `POST /run` and `run.py` are the entry points. |
| **Remediation** | §3.2 | The agent is read-only against the tenancy. Findings are recommendations. |

Two deltas from the spec's repository layout (§10), both deliberate: `tests/` is added, because
every task in this plan is test-first; and `docs/superpowers/` holds this plan and the spec.

The lab tenancy in spec §5.2 is **not** a task in this plan — it is infrastructure built before
the window opens, and the tenancy must exist for at least seven days before 15 Oct for the
telemetry lookback to return real history. Section §16 of the spec carries those pre-window
actions.
