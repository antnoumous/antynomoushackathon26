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
