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
