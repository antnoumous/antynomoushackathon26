"""Pure policy-snapshot validation and canonical digests. No network or env reads."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any

from app.sources.base import Scope

ALLOWED_PREDICATES = frozenset({
    "resource_class",
    "compute_instance",
    "attached",
    "absent_from_iac",
    "min_coverage_ratio",
    "mean_cpu_lt",
    "peak_cpu_lt",
    "peak_cpu_gte",
})
RESOURCE_CLASSES = frozenset({"compute_instance", "block_volume", "reserved_public_ip"})
KNOWN_RULE_IDS = frozenset({"R-1", "R-2", "R-3", "R-4", "R-5"})
BOOL_PREDICATES = frozenset({"compute_instance", "attached", "absent_from_iac"})
PERCENT_PREDICATES = frozenset({"mean_cpu_lt", "peak_cpu_lt", "peak_cpu_gte"})
MAX_NOTE_CHARS = 2048
MAX_WHEN_JSON_BYTES = 4096
MAX_RULES = 256
SCHEMA_VERSION = 1

# ValueError messages are fixed categories only — never echo untrusted payloads.
_SCHEMA = "schema"
_INCOMPLETE = "incomplete"
_MISMATCH = "mismatch"


def _raise(category: str) -> None:
    raise ValueError(category)


def _require_bool(value: Any) -> None:
    if type(value) is not bool:
        _raise(_SCHEMA)


def _require_finite_number(value: Any) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        _raise(_SCHEMA)
    number = float(value)
    if not math.isfinite(number):
        _raise(_SCHEMA)
    return number


def _validate_when(when: Any) -> dict[str, Any]:
    if not isinstance(when, dict):
        _raise(_SCHEMA)
    out: dict[str, Any] = {}
    for key, value in when.items():
        if key not in ALLOWED_PREDICATES:
            _raise(_SCHEMA)
        if key == "resource_class":
            if value not in RESOURCE_CLASSES:
                _raise(_SCHEMA)
            out[key] = value
        elif key in BOOL_PREDICATES:
            _require_bool(value)
            out[key] = value
        elif key == "min_coverage_ratio":
            number = _require_finite_number(value)
            if number < 0.0 or number > 1.0:
                _raise(_SCHEMA)
            out[key] = value  # preserve int/float identity
        elif key in PERCENT_PREDICATES:
            number = _require_finite_number(value)
            if number < 0.0 or number > 100.0:
                _raise(_SCHEMA)
            out[key] = value
        else:
            _raise(_SCHEMA)
    return out


def _enforce_identity(rule_id: str, finding_class: str, when: dict[str, Any]) -> None:
    if rule_id == "R-1":
        if finding_class != "cost_waste":
            _raise(_SCHEMA)
        if when.get("resource_class") != "block_volume" or when.get("attached") is not False:
            _raise(_SCHEMA)
    elif rule_id == "R-2":
        if finding_class != "cost_waste":
            _raise(_SCHEMA)
        if when.get("resource_class") != "reserved_public_ip" or when.get("attached") is not False:
            _raise(_SCHEMA)
    elif rule_id == "R-3":
        if finding_class != "cost_waste":
            _raise(_SCHEMA)
        if when.get("resource_class") != "compute_instance":
            _raise(_SCHEMA)
        if "mean_cpu_lt" not in when or "peak_cpu_lt" not in when:
            _raise(_SCHEMA)
        if "peak_cpu_gte" in when:
            _raise(_SCHEMA)
    elif rule_id == "R-4":
        if finding_class != "cost_waste":
            _raise(_SCHEMA)
        if when.get("resource_class") != "compute_instance":
            _raise(_SCHEMA)
        if "mean_cpu_lt" not in when or "peak_cpu_gte" not in when:
            _raise(_SCHEMA)
        if "peak_cpu_lt" in when:
            _raise(_SCHEMA)
    elif rule_id == "R-5":
        if finding_class != "unattributed":
            _raise(_SCHEMA)
        if when.get("compute_instance") is not True or when.get("absent_from_iac") is not True:
            _raise(_SCHEMA)
    else:
        _raise(_SCHEMA)


def validate_rules(records: list[dict]) -> list[dict]:
    if not isinstance(records, list):
        _raise(_SCHEMA)
    if len(records) > MAX_RULES:
        _raise(_SCHEMA)
    seen: set[str] = set()
    normalized: list[dict] = []
    for record in records:
        if not isinstance(record, dict):
            _raise(_SCHEMA)
        allowed_keys = {"rule_id", "class", "when", "note"}
        if set(record) - allowed_keys:
            _raise(_SCHEMA)
        if "rule_id" not in record or "class" not in record or "when" not in record or "note" not in record:
            _raise(_SCHEMA)
        rule_id = record["rule_id"]
        if not isinstance(rule_id, str) or rule_id not in KNOWN_RULE_IDS:
            _raise(_SCHEMA)
        if rule_id in seen:
            _raise(_SCHEMA)
        seen.add(rule_id)
        finding_class = record["class"]
        if finding_class not in {"cost_waste", "unattributed"}:
            _raise(_SCHEMA)
        note = record["note"]
        if not isinstance(note, str) or len(note) > MAX_NOTE_CHARS:
            _raise(_SCHEMA)
        when = _validate_when(record["when"])
        _enforce_identity(rule_id, finding_class, when)
        normalized.append({
            "rule_id": rule_id,
            "class": finding_class,
            "when": when,
            "note": note,
        })
    return normalized


def policy_digest(records: list[dict]) -> str:
    normalized = validate_rules(records)
    payload = json.dumps(sorted(normalized, key=lambda r: r["rule_id"]),
                         sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def scope_digest(scope: Scope) -> str:
    payload = json.dumps(
        {
            "compartment_ids": sorted(scope.compartment_ids),
            "resource_types": sorted(scope.resource_types),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _parse_expected_count(value: Any) -> int:
    if type(value) is bool:
        _raise(_SCHEMA)
    if type(value) is int:
        count = value
    elif type(value) is str:
        if not re.fullmatch(r"0|[1-9][0-9]*", value):
            _raise(_SCHEMA)
        count = int(value)
    else:
        _raise(_SCHEMA)
    if count < 0 or count > MAX_RULES:
        _raise(_SCHEMA)
    return count


def _parse_schema_version(value: Any) -> int:
    if type(value) is bool:
        _raise(_SCHEMA)
    if type(value) is int:
        return value
    if type(value) is str and re.fullmatch(r"0|[1-9][0-9]*", value):
        return int(value)
    _raise(_SCHEMA)


def _object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            _raise(_SCHEMA)
        out[key] = value
    return out


def _reject_nonfinite_constant(token: str) -> None:
    _raise(_SCHEMA)


def _decode_when_json(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, str):
        _raise(_SCHEMA)
    if len(raw.encode("utf-8")) > MAX_WHEN_JSON_BYTES:
        _raise(_SCHEMA)
    try:
        decoded = json.loads(
            raw,
            object_pairs_hook=_object_pairs_hook,
            parse_constant=_reject_nonfinite_constant,
        )
    except ValueError:
        raise
    except Exception:
        _raise(_SCHEMA)
    if not isinstance(decoded, dict):
        _raise(_SCHEMA)
    return decoded


def _require_aware_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        _raise(_SCHEMA)
    try:
        normalized = value.replace("Z", "+00:00")
        moment = datetime.fromisoformat(normalized)
    except ValueError:
        _raise(_SCHEMA)
    if moment.tzinfo is None:
        _raise(_SCHEMA)
    return value


def validate_snapshot(
    manifest: dict,
    rows: list[dict],
    *,
    snapshot_id: str,
    expected_sha256: str,
    requested_scope_hash: str,
) -> list[dict]:
    if not isinstance(manifest, dict) or not isinstance(rows, list):
        _raise(_SCHEMA)
    required = {
        "snapshot_id",
        "schema_version",
        "expected_count",
        "content_sha256",
        "requested_scope_hash",
        "observed_at_utc",
    }
    if set(manifest) < required:
        _raise(_SCHEMA)

    if manifest.get("snapshot_id") != snapshot_id:
        _raise(_MISMATCH)
    if _parse_schema_version(manifest["schema_version"]) != SCHEMA_VERSION:
        _raise(_SCHEMA)
    if manifest.get("requested_scope_hash") != requested_scope_hash:
        _raise(_MISMATCH)
    if manifest.get("content_sha256") != expected_sha256:
        _raise(_MISMATCH)
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        _raise(_SCHEMA)
    if not isinstance(requested_scope_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", requested_scope_hash):
        _raise(_SCHEMA)

    _require_aware_timestamp(manifest["observed_at_utc"])
    expected_count = _parse_expected_count(manifest["expected_count"])
    if len(rows) != expected_count:
        _raise(_INCOMPLETE)
    if len(rows) > MAX_RULES:
        _raise(_SCHEMA)

    records: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            _raise(_SCHEMA)
        if row.get("snapshot_id") != snapshot_id:
            _raise(_MISMATCH)
        for key in ("rule_id", "class", "when_json", "note"):
            if key not in row:
                _raise(_SCHEMA)
        when = _decode_when_json(row["when_json"])
        records.append({
            "rule_id": row["rule_id"],
            "class": row["class"],
            "when": when,
            "note": row["note"],
        })

    try:
        normalized = validate_rules(records)
    except ValueError:
        raise
    digest = policy_digest(normalized)
    if digest != expected_sha256 or digest != manifest["content_sha256"]:
        _raise(_MISMATCH)
    return normalized
