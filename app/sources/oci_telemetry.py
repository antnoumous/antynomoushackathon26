# app/sources/oci_telemetry.py
"""Live OCI telemetry: CpuUtilization from the Monitoring service.

Same coverage arithmetic as the fixture source and the same record shape — one constant
(`MIN_COVERAGE_RATIO`) governs both, so a rule can never disagree with the data that judges it.
The differences are honest ones: coverage is measured from the datapoints the service actually
returned (the span between the first and the last), because unlike a fixture the adapter cannot
know when a resource began reporting; and no stream means no record — never a fabricated zero.

The SDK is imported lazily inside the fetch path, so sample mode never touches it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import RunConfig
from app.sources.base import MIN_COVERAGE_RATIO, Scope, SourceError, SourceResult
from app.sources.oci_inventory import (TIMEOUT_S, load_sdk_config, resolve_compartments)

NAMESPACE = "oci_computeagent"
METRIC = "CpuUtilization"

# Monitoring keeps 1-minute-resolution data for 7 days and 5-minute data for 30 days; hourly and
# coarser are kept 90 days. Asking for a window beyond a resolution's retention returns silently
# short data, so the adapter widens the resolution instead — the Skeptic's 744 h re-check is the
# case this exists for: at 5 m it would overrun the 30-day edge, at 60 m it fits inside 90 days.
_RETENTION_HOURS = {1: 168, 5: 720}
_RETENTION_DEFAULT_HOURS = 2160


def resolution_for(lookback_hours: int, resolution_minutes: int) -> int:
    if lookback_hours <= _RETENTION_HOURS.get(resolution_minutes, _RETENTION_DEFAULT_HOURS):
        return resolution_minutes
    if lookback_hours <= _RETENTION_DEFAULT_HOURS:
        return 60
    return resolution_minutes      # beyond 90 days no resolution helps; the coverage math reports it


def series_records(streams: list[Any], lookback_hours: int, resolution_minutes: int,
                   now: datetime) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for stream in streams:
        resource_id = (stream.dimensions or {}).get("resourceId")
        if resource_id is None:
            continue                       # a stream we cannot attribute is a stream we cannot use
        timestamps = sorted(point.timestamp for point in (stream.aggregated_datapoints or []))
        points = [{"ts": point.timestamp, "value": round(point.value, 3)}
                  for point in sorted(stream.aggregated_datapoints or [],
                                      key=lambda p: p.timestamp)]
        coverage_hours = round((timestamps[-1] - timestamps[0]).total_seconds() / 3600.0, 3) \
            if len(timestamps) > 1 else 0.0
        sufficient = coverage_hours >= MIN_COVERAGE_RATIO * lookback_hours
        records.append({
            "resource_id": resource_id,
            "metric": stream.name or METRIC,
            "lookback_hours": lookback_hours,
            "resolution_minutes": resolution_minutes,
            "coverage_hours": coverage_hours,
            "sufficient": sufficient,
            "insufficient_reason": None if sufficient else (
                f"coverage {coverage_hours:.0f}h of {lookback_hours}h requested"
                if points else "the service returned no datapoints for this resource"),
            "points": points,
        })
    return records


def _query(resolution_minutes: int) -> str:
    # The live Monitoring service rejects compartmentId as a query filter in the
    # oci_computeagent namespace ("Not Supported yet"); scoping happens via the
    # compartment_id argument of summarize_metrics_data, one call per compartment.
    return f"{METRIC}[{resolution_minutes}m].mean()"


class OCITelemetrySource:
    name = "telemetry"

    def __init__(self, config: RunConfig) -> None:
        self.config = config

    def fetch(self, scope: Scope) -> SourceResult:
        problems: list[str] = []
        sdk = None
        try:
            compartments = resolve_compartments(scope, self.config)
        except SourceError as exc:
            problems.append(str(exc))
            compartments = []
        try:
            sdk = load_sdk_config()
        except SourceError as exc:
            problems.append(str(exc))
        if problems or sdk is None:
            raise SourceError("; ".join(problems) or "OCI telemetry is unavailable")

        now = datetime.now(timezone.utc)
        resolution = resolution_for(scope.lookback_hours, scope.resolution_minutes)
        import oci
        from oci.monitoring import MonitoringClient
        from oci.monitoring.models import SummarizeMetricsDataDetails
        streams: list[Any] = []
        try:
            client = MonitoringClient(sdk, timeout=TIMEOUT_S)
            for cid in compartments:      # the service scopes by argument, not by query filter
                response = client.summarize_metrics_data(
                    cid,
                    SummarizeMetricsDataDetails(
                        namespace=NAMESPACE,
                        query=_query(resolution),
                        start_time=now - timedelta(hours=scope.lookback_hours),
                        end_time=now,
                        resolution=f"{resolution}m",
                    ),
                    retry_strategy=oci.retry.NoneRetryStrategy())
                streams.extend(response.data or [])
        except Exception as exc:                      # noqa: BLE001 - named, degraded upstream
            raise SourceError(f"summarize_metrics_data failed: {exc}") from exc

        records = series_records(streams, scope.lookback_hours, resolution, now)
        return SourceResult(source=self.name, backend="live", records=records)
