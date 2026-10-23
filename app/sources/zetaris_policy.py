"""Opt-in Zetaris policy source: two pinned SELECTs, complete snapshot or nothing.

This class performs no writes, no DDL, no authentication login, no auto-create, no SDK
calls, no polling and no retry of its own. Settings are immutable per instance; there is
no global client, token or scope cache. Every failure leaves this module as a sanitized
ZetarisError (a SourceError subtype) that the orchestrator's degradation path can handle.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import time
from typing import Callable

from app.source_metadata import SourceProvenance
from app.sources.base import Scope, SourceResult
from app.sources.policy_snapshot import (
    MAX_RULES,
    policy_digest,
    scope_digest,
    validate_snapshot,
)
from app.sources.zetaris_http import (
    Category,
    ZetarisError,
    ZetarisSettings,
    decode_response,
    run_sql_batch,
)

MANIFEST_COLUMNS = (
    "snapshot_id",
    "schema_version",
    "expected_count",
    "content_sha256",
    "requested_scope_hash",
    "observed_at_utc",
)
RULE_COLUMNS = ("snapshot_id", "rule_id", "class", "when_json", "note")

MAX_FETCH_SECONDS = 30.0
"""One source fetch, including both queries, decoding and validation, never exceeds this."""

RUN_RESERVE_SECONDS = 5.0
"""When the run carries a deadline, the source stops this early so finalisation can finish."""

# validate_snapshot raises ValueError with fixed categories; they map onto transport
# categories so only allowlisted ZetarisError categories leave this module.
_VALUE_CATEGORY: dict[str, Category] = {
    "schema": "schema",
    "incomplete": "incomplete",
    "mismatch": "query",
}


def _select(columns: tuple[str, ...], object_name: str, snapshot_id: str,
            *, order_by: str | None = None) -> str:
    cols = ", ".join(f"`{c}`" for c in columns)
    sql = f"SELECT {cols} FROM {object_name} WHERE `snapshot_id` = '{snapshot_id}'"
    if order_by is not None:
        sql += f" ORDER BY `{order_by}`"
    return sql


def decode_when_json(value: str) -> str:
    """The Zetaris FORMAT CSV engine truncates cells at embedded RFC-4180 quotes, so the
    exporter percent-encodes quotes/commas in when_json cells (see scripts/export_zetaris_policy.py).
    Undo that encoding *only* when the cell is not valid JSON as-is; raw JSON whose text
    happens to contain a literal '%22' therefore passes through untouched (collision-safe).
    Raises ValueError (as json.loads) when neither form parses."""
    import json as _json
    from urllib.parse import unquote
    try:
        _json.loads(value)
        return value
    except ValueError:
        decoded = unquote(value)
        _json.loads(decoded)          # may raise — original garbage stays garbage
        return decoded


class ZetarisPolicySource:
    name = "policy"

    def __init__(self, settings: ZetarisSettings,
                 transport: Callable = run_sql_batch) -> None:
        if not isinstance(settings, ZetarisSettings):
            raise ZetarisError("configuration", retryable=False)
        self._settings = settings
        self._transport = transport

    def fetch(self, scope: Scope) -> SourceResult:
        cutoff = time.monotonic() + MAX_FETCH_SECONDS
        if scope.deadline_monotonic is not None:
            cutoff = min(cutoff, scope.deadline_monotonic - RUN_RESERVE_SECONDS)
        if cutoff - time.monotonic() <= 0:
            raise ZetarisError("deadline", retryable=False)

        s = self._settings
        queries = (
            _select(MANIFEST_COLUMNS, s.manifest_object, s.snapshot_id),
            _select(RULE_COLUMNS, s.policy_object, s.snapshot_id, order_by="rule_id"),
        )
        try:
            responses = self._transport(s, queries, cutoff)
            manifest_rows = decode_response(responses[0], MANIFEST_COLUMNS)
            rule_rows = decode_response(responses[1], RULE_COLUMNS)
            for row in rule_rows:
                if isinstance(row.get("when_json"), str):
                    row["when_json"] = decode_when_json(row["when_json"])
            if len(manifest_rows) == 0:
                raise ZetarisError("incomplete", retryable=False)
            if len(manifest_rows) > 1:
                raise ZetarisError("schema", retryable=False)
            manifest = manifest_rows[0]
            if len(rule_rows) > MAX_RULES:
                raise ZetarisError("schema", retryable=False)
            records = validate_snapshot(
                manifest,
                rule_rows,
                snapshot_id=s.snapshot_id,
                expected_sha256=s.expected_sha256,
                requested_scope_hash=scope_digest(scope),
            )
        except ZetarisError:
            raise
        except ValueError as exc:
            raise ZetarisError(
                _VALUE_CATEGORY.get(str(exc), "query"), retryable=False
            ) from None

        # A slow body must not smuggle a "success" past the cutoff.
        if time.monotonic() >= cutoff:
            raise ZetarisError("deadline", retryable=False)

        digest = policy_digest(records)
        provenance = SourceProvenance(
            provider="zetaris",
            object_name=s.policy_object,
            manifest_object=s.manifest_object,
            snapshot_id=s.snapshot_id,
            schema_version=int(str(manifest["schema_version"])),
            requested_scope_hash=scope_digest(scope),
            content_sha256=digest,
            row_count=len(records),
            expected_count=int(str(manifest["expected_count"])),
            complete=True,
            observed_at_utc=str(manifest["observed_at_utc"]),
            fetched_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            query_sha256=hashlib.sha256("\n".join(queries).encode("utf-8")).hexdigest(),
        )
        return SourceResult(
            source="policy",
            backend="live",
            degraded=False,
            records=records,
            provenance=provenance,
        )
