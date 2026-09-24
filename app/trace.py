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
