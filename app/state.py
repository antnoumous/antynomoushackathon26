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
