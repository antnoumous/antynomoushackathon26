#!/usr/bin/env python3
"""Offline immutable policy-snapshot exporter for Zetaris publication (Task 1).

Writes UTF-8 rules.csv + manifest.csv into a new private output directory, plus a non-secret
local manifest and proposed registration SQL. No network, no DDL, no credential reads.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.config import RunConfig  # noqa: E402
from app.sources.base import Scope  # noqa: E402
from app.sources.policy_snapshot import policy_digest, scope_digest, validate_rules  # noqa: E402

RULE_COLUMNS = ("snapshot_id", "rule_id", "class", "when_json", "note")
MANIFEST_COLUMNS = (
    "snapshot_id",
    "schema_version",
    "expected_count",
    "content_sha256",
    "requested_scope_hash",
    "observed_at_utc",
)


def _load_policy(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rules = payload["rules"] if isinstance(payload, dict) and "rules" in payload else payload
    return validate_rules(rules)


def _scope_from_request(path: Path) -> Scope:
    request = json.loads(path.read_text(encoding="utf-8"))
    config = RunConfig.from_env_and_request(request)
    return Scope(
        compartment_ids=config.compartment_ids,
        resource_types=config.resource_types,
        lookback_hours=config.lookback_hours,
        resolution_minutes=config.resolution_minutes,
    )


def export_policy(*, policy: Path, snapshot_id: str, scope_json: Path, out: Path,
                  reference_db: str = "DRIFTWATCH_REF",
                  rules_table: str | None = None,
                  manifest_table: str | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", snapshot_id):
        raise ValueError("schema")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", reference_db):
        raise ValueError("schema")
    for table in (rules_table, manifest_table):
        if table is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise ValueError("schema")
    rules = _load_policy(policy)
    scope = _scope_from_request(scope_json)
    content_sha256 = policy_digest(rules)
    requested_scope_hash = scope_digest(scope)
    observed_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    out.mkdir(mode=0o700, parents=True, exist_ok=False)

    rules_path = out / "rules.csv"
    with rules_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RULE_COLUMNS))
        writer.writeheader()
        for rule in sorted(rules, key=lambda r: r["rule_id"]):
            when_json = json.dumps(rule["when"], separators=(",", ":"),
                                   ensure_ascii=False, allow_nan=False)
            # The Zetaris FORMAT CSV engine truncates cells at embedded RFC-4180 quotes
            # (verified live on 2.4.3.1, 22 Oct 2026 — see notes). Percent-encode quotes
            # and commas so the cell never needs CSV quoting; ZetarisPolicySource
            # .decode_when_json restores it. Decoded content — every digest — unchanged.
            cell = quote(when_json, safe="[]{}")
            for key, value in (("snapshot_id", snapshot_id), ("rule_id", rule["rule_id"]),
                               ("class", rule["class"]), ("note", rule["note"])):
                # Embedded double quotes are the PROVEN fatal character for this engine's
                # CSV parser (v1 live incident, 22 Oct 2026). A bare comma only triggers
                # QUOTE_MINIMAL wrapping, which the engine handled correctly in the same
                # run; and because policy_digest covers the note text, any future
                # mangling is caught by validation rather than silently accepted.
                if any(c in str(value) for c in ('"', "\n", "\r")):
                    raise ValueError(
                        f"schema-unsafe: column {key} contains embedded quotes/newlines; "
                        "the engine's CSV parser truncates at them")
            writer.writerow({
                "snapshot_id": snapshot_id,
                "rule_id": rule["rule_id"],
                "class": rule["class"],
                "when_json": cell,
                "note": rule["note"],
            })

    manifest_row = {
        "snapshot_id": snapshot_id,
        "schema_version": "1",
        "expected_count": str(len(rules)),
        "content_sha256": content_sha256,
        "requested_scope_hash": requested_scope_hash,
        "observed_at_utc": observed_at_utc,
    }
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MANIFEST_COLUMNS))
        writer.writeheader()
        writer.writerow(manifest_row)

    local_manifest = {
        "snapshot_id": snapshot_id,
        "schema_version": 1,
        "expected_count": len(rules),
        "content_sha256": content_sha256,
        "requested_scope_hash": requested_scope_hash,
        "observed_at_utc": observed_at_utc,
        "rules_csv": "rules.csv",
        "manifest_csv": "manifest.csv",
        "source_policy": str(policy),
        "scope_json": str(scope_json),
    }
    (out / "local_manifest.json").write_text(
        json.dumps(local_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    registration_sql = (
        "-- Proposed registration only. Do not execute from this script.\n"
        f"-- snapshot_id={snapshot_id}\n"
        f"-- content_sha256={content_sha256}\n"
        f"-- requested_scope_hash={requested_scope_hash}\n"
        f"-- expected_count={len(rules)}\n"
        "-- Register immutable CSV objects under a dedicated reference catalog, then pin\n"
        "-- ZETARIS_POLICY_SNAPSHOT / ZETARIS_POLICY_SHA256 to these exact values.\n"
        "-- NOTE: the file:// path scheme is a capability gate — it must be verified on the\n"
        "-- actual instance (one statement per request) after approval; customer-data is\n"
        "-- mounted READ-ONLY into the driver, so registration reads work but no table write\n"
        "-- back to this path may be attempted.\n"
    )
    if rules_table and manifest_table:
        staged = f"file:///home/zetaris/customer-data/shared/driftwatch-policy/{snapshot_id}"
        registration_sql += (
            "-- One statement per request. Skip the DATABASE statement once it exists.\n"
            f'CREATE LIGHTNING DATABASE {reference_db} DESCRIBE BY "Driftwatch synthetic reference policies";\n'
            f"CREATE LIGHTNING FILESTORE TABLE {rules_table} FROM {reference_db} FORMAT CSV OPTIONS (\n"
            f'  path "{staged}/rules.csv",\n  header "true");\n'
            f"CREATE LIGHTNING FILESTORE TABLE {manifest_table} FROM {reference_db} FORMAT CSV OPTIONS (\n"
            f'  path "{staged}/manifest.csv",\n  header "true");\n'
        )
    (out / "proposed_registration.sql").write_text(registration_sql, encoding="utf-8")
    return local_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export an immutable Driftwatch policy snapshot for Zetaris publication.",
    )
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--snapshot-id", type=str, required=True)
    parser.add_argument("--scope-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reference-db", type=str, default="DRIFTWATCH_REF")
    parser.add_argument("--rules-table", type=str, default=None)
    parser.add_argument("--manifest-table", type=str, default=None)
    args = parser.parse_args(argv)
    manifest = export_policy(
        policy=args.policy,
        snapshot_id=args.snapshot_id,
        scope_json=args.scope_json,
        out=args.out,
        reference_db=args.reference_db,
        rules_table=args.rules_table,
        manifest_table=args.manifest_table,
    )
    print(json.dumps({
        "snapshot_id": manifest["snapshot_id"],
        "expected_count": manifest["expected_count"],
        "content_sha256": manifest["content_sha256"],
        "requested_scope_hash": manifest["requested_scope_hash"],
        "out": str(args.out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
