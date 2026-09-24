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
