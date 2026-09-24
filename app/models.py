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
