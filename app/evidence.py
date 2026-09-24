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
