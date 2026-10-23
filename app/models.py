from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.source_metadata import SourceProvenance

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
    size_gb: float | None = None
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
    superseded_by: str | None = None
    """Set when a later round reached a different conclusion: the reason this finding is
    `rejected` and which finding replaced it."""


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


class Ruling(BaseModel):
    candidate_id: str
    verdict: Verdict
    reason: str
    request: dict[str, Any] | None = None
    revised_claim: str | None = None
    round: int = 0


class Undetermined(BaseModel):
    resource_id: str
    reason: str


class Assignment(BaseModel):
    assignment_id: str
    round: int
    resource_ids: list[str]
    lookback_hours: int
    focus: str = "initial"


class SourceStatus(BaseModel):
    name: str
    # `none` means the source answered nothing at all: it is not a backend, it is the absence of
    # one, and saying so is what keeps a fixture-only run from reading as a live audit.
    backend: Literal["live", "fixture", "none"]
    degraded: bool = False
    reason: str | None = None
    provenance: SourceProvenance | None = None


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
