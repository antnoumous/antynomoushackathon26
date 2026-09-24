# app/sources/live.py
"""Live backends. Every one of these raises until Task 15 wires the OCI SDK behind it, which is
what lets the loop's degradation path be exercised from the first day of the build."""
from __future__ import annotations

from app.config import RunConfig
from app.sources.base import SourceError


class UnimplementedLiveSource:
    def __init__(self, name: str) -> None:
        self.name = name

    def fetch(self, scope):
        raise SourceError(f"live backend for {self.name!r} is not implemented")


def get_live_source(name: str, config: RunConfig):
    if name not in {"inventory", "telemetry", "iac", "policy"}:
        raise KeyError(name)
    return UnimplementedLiveSource(name)
