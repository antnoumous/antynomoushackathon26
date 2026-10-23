"""Canonical identity and semantic validation for immutable policy snapshots (Task 1)."""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest

from app.sources.policy_snapshot import policy_digest, scope_digest, validate_rules, validate_snapshot
from scripts.export_zetaris_policy import export_policy

BASE = json.loads(Path("data/scenarios/example_1/policy.json").read_text())["rules"]

SNAPSHOT_ID = "example1_base_v1"
SCOPE_HASH = "a" * 64  # placeholder; replaced by real digest in helpers that need a match


def _manifest(**overrides):
    normalized = validate_rules(copy.deepcopy(BASE))
    digest = policy_digest(normalized)
    base = {
        "snapshot_id": SNAPSHOT_ID,
        "schema_version": 1,
        "expected_count": len(normalized),
        "content_sha256": digest,
        "requested_scope_hash": SCOPE_HASH,
        "observed_at_utc": "2026-10-19T12:00:00+00:00",
    }
    base.update(overrides)
    return base


def _rows(rules=None, snapshot_id=SNAPSHOT_ID):
    rules = rules if rules is not None else copy.deepcopy(BASE)
    out = []
    for rule in rules:
        out.append({
            "snapshot_id": snapshot_id,
            "rule_id": rule["rule_id"],
            "class": rule["class"],
            "when_json": json.dumps(rule["when"], separators=(",", ":"), ensure_ascii=False),
            "note": rule["note"],
        })
    return out


def test_digest_is_order_independent():
    assert policy_digest(BASE) == policy_digest(list(reversed(BASE)))


@pytest.mark.parametrize("bad", [True, "5", float("nan"), float("inf"), -1, 101])
def test_cpu_threshold_is_finite_numeric_percent_not_boolean(bad):
    rows = copy.deepcopy(BASE)
    rows[2]["when"]["mean_cpu_lt"] = bad
    with pytest.raises(ValueError):
        validate_rules(rows)


def test_unknown_predicate_is_not_silently_ignored():
    rows = copy.deepcopy(BASE)
    rows[2]["when"]["mean_cup_lt"] = rows[2]["when"].pop("mean_cpu_lt")
    with pytest.raises(ValueError):
        validate_rules(rows)


@pytest.mark.parametrize("mutate", [
    "duplicate_ids",
    "unknown_id",
    "wrong_class",
    "r1_compute",
    "r5_incomplete",
    "string_bool",
    "missing_note",
    "note_too_long",
])
def test_rule_identity_and_field_constraints(mutate):
    rows = copy.deepcopy(BASE)
    if mutate == "duplicate_ids":
        rows[1]["rule_id"] = "R-1"
    elif mutate == "unknown_id":
        rows[0]["rule_id"] = "R-9"
    elif mutate == "wrong_class":
        rows[0]["class"] = "unattributed"
    elif mutate == "r1_compute":
        rows[0]["when"]["resource_class"] = "compute_instance"
    elif mutate == "r5_incomplete":
        rows[4]["when"] = {"compute_instance": True}
    elif mutate == "string_bool":
        rows[0]["when"]["attached"] = "false"
    elif mutate == "missing_note":
        del rows[0]["note"]
    elif mutate == "note_too_long":
        rows[0]["note"] = "x" * 2049
    with pytest.raises(ValueError):
        validate_rules(rows)


def test_extra_record_fields_are_rejected():
    rows = copy.deepcopy(BASE)
    rows[0]["extra"] = "nope"
    with pytest.raises(ValueError):
        validate_rules(rows)


def test_empty_rules_are_valid():
    assert validate_rules([]) == []
    assert policy_digest([]) == policy_digest([])


def test_when_json_over_4096_bytes_is_rejected():
    rows = _rows()
    huge = {"resource_class": "block_volume", "attached": False, "pad": "y" * 4100}
    rows[0]["when_json"] = json.dumps(huge)
    assert len(rows[0]["when_json"].encode("utf-8")) > 4096
    manifest = _manifest()
    with pytest.raises(ValueError):
        validate_snapshot(manifest, rows, snapshot_id=SNAPSHOT_ID,
                          expected_sha256=manifest["content_sha256"],
                          requested_scope_hash=SCOPE_HASH)


def test_duplicate_keys_in_when_json_are_rejected():
    rows = _rows()
    rows[0]["when_json"] = '{"resource_class":"block_volume","attached":false,"attached":true}'
    manifest = _manifest()
    with pytest.raises(ValueError):
        validate_snapshot(manifest, rows, snapshot_id=SNAPSHOT_ID,
                          expected_sha256=manifest["content_sha256"],
                          requested_scope_hash=SCOPE_HASH)


def test_mixed_snapshot_ids_are_rejected():
    rows = _rows()
    rows[2]["snapshot_id"] = "other_snapshot"
    manifest = _manifest()
    with pytest.raises(ValueError):
        validate_snapshot(manifest, rows, snapshot_id=SNAPSHOT_ID,
                          expected_sha256=manifest["content_sha256"],
                          requested_scope_hash=SCOPE_HASH)


@pytest.mark.parametrize("count", [-1, "1e2", "01", "5.0", True, 5.5, "abc"])
def test_negative_or_non_decimal_expected_count_is_rejected(count):
    manifest = _manifest(expected_count=count)
    with pytest.raises(ValueError):
        validate_snapshot(manifest, _rows(), snapshot_id=SNAPSHOT_ID,
                          expected_sha256=manifest["content_sha256"],
                          requested_scope_hash=SCOPE_HASH)


@pytest.mark.parametrize("ts", [None, "2026-10-19T12:00:00", "", "not-a-time"])
def test_missing_or_timezone_naive_timestamps_are_rejected(ts):
    if ts is None:
        manifest = _manifest()
        del manifest["observed_at_utc"]
    else:
        manifest = _manifest(observed_at_utc=ts)
    with pytest.raises(ValueError):
        validate_snapshot(manifest, _rows(), snapshot_id=SNAPSHOT_ID,
                          expected_sha256=manifest["content_sha256"],
                          requested_scope_hash=SCOPE_HASH)


def test_count_257_is_rejected():
    rules = copy.deepcopy(BASE)
    # Fabricate 257 copies with unique IDs would violate identity; instead pass 257 row shells
    # that validate_snapshot rejects on count before per-rule identity of invents.
    rows = _rows()
    while len(rows) < 257:
        rows.append(copy.deepcopy(rows[0]))
    manifest = _manifest(expected_count=257)
    with pytest.raises(ValueError):
        validate_snapshot(manifest, rows, snapshot_id=SNAPSHOT_ID,
                          expected_sha256=manifest["content_sha256"],
                          requested_scope_hash=SCOPE_HASH)


@pytest.mark.parametrize("field,value", [
    ("content_sha256", "b" * 64),
    ("requested_scope_hash", "c" * 64),
    ("schema_version", 2),
    ("snapshot_id", "wrong_id"),
])
def test_wrong_pinned_hash_scope_or_version_is_rejected(field, value):
    manifest = _manifest(**{field: value})
    expected = manifest["content_sha256"] if field != "content_sha256" else policy_digest(BASE)
    scope = SCOPE_HASH if field != "requested_scope_hash" else SCOPE_HASH
    snap = SNAPSHOT_ID if field != "snapshot_id" else SNAPSHOT_ID
    kwargs = {
        "snapshot_id": snap if field != "snapshot_id" else SNAPSHOT_ID,
        "expected_sha256": expected if field != "content_sha256" else ("d" * 64),
        "requested_scope_hash": scope if field != "requested_scope_hash" else SCOPE_HASH,
    }
    if field == "content_sha256":
        kwargs["expected_sha256"] = "d" * 64
    elif field == "requested_scope_hash":
        kwargs["requested_scope_hash"] = SCOPE_HASH  # caller pin correct; manifest wrong
    elif field == "snapshot_id":
        kwargs["snapshot_id"] = SNAPSHOT_ID  # caller pin correct; manifest wrong
    elif field == "schema_version":
        kwargs["expected_sha256"] = manifest["content_sha256"]
    with pytest.raises(ValueError):
        validate_snapshot(manifest, _rows(), **kwargs)


def test_expected_5_but_returned_4_is_rejected():
    manifest = _manifest(expected_count=5)
    rows = _rows()[:4]
    with pytest.raises(ValueError):
        validate_snapshot(manifest, rows, snapshot_id=SNAPSHOT_ID,
                          expected_sha256=manifest["content_sha256"],
                          requested_scope_hash=SCOPE_HASH)


def test_empty_complete_validates_to_no_rules():
    digest = policy_digest([])
    manifest = {
        "snapshot_id": SNAPSHOT_ID,
        "schema_version": 1,
        "expected_count": 0,
        "content_sha256": digest,
        "requested_scope_hash": SCOPE_HASH,
        "observed_at_utc": "2026-10-19T12:00:00+00:00",
    }
    got = validate_snapshot(manifest, [], snapshot_id=SNAPSHOT_ID,
                            expected_sha256=digest, requested_scope_hash=SCOPE_HASH)
    assert got == []


def test_valid_baseline_snapshot_round_trips():
    manifest = _manifest()
    got = validate_snapshot(manifest, _rows(), snapshot_id=SNAPSHOT_ID,
                            expected_sha256=manifest["content_sha256"],
                            requested_scope_hash=SCOPE_HASH)
    assert [r["rule_id"] for r in got] == [r["rule_id"] for r in BASE]
    assert policy_digest(got) == manifest["content_sha256"]


def test_exporter_round_trip_and_refuses_overwrite(tmp_path):
    out = tmp_path / "example1_base_v1"
    export_policy(
        policy=Path("data/scenarios/example_1/policy.json"),
        snapshot_id=SNAPSHOT_ID,
        scope_json=Path("input_examples/example_1.json"),
        out=out,
    )
    from app.sources.zetaris_policy import decode_when_json
    with (out / "rules.csv").open(encoding="utf-8", newline="") as handle:
        rows = [dict(r, when_json=decode_when_json(r["when_json"]))
                for r in csv.DictReader(handle)]
    with (out / "manifest.csv").open(encoding="utf-8", newline="") as handle:
        manifests = list(csv.DictReader(handle))
    assert len(manifests) == 1
    manifest = manifests[0]
    # CSV yields strings; validate_snapshot accepts decimal count strings.
    got = validate_snapshot(
        manifest,
        rows,
        snapshot_id=SNAPSHOT_ID,
        expected_sha256=manifest["content_sha256"],
        requested_scope_hash=manifest["requested_scope_hash"],
    )
    assert got == validate_rules(copy.deepcopy(BASE))
    assert policy_digest(got) == manifest["content_sha256"]
    from app.config import RunConfig
    from app.sources.base import Scope
    request = json.loads(Path("input_examples/example_1.json").read_text())
    cfg = RunConfig.from_env_and_request(request)
    scope = Scope(compartment_ids=cfg.compartment_ids, resource_types=cfg.resource_types,
                  lookback_hours=cfg.lookback_hours, resolution_minutes=cfg.resolution_minutes)
    assert manifest["requested_scope_hash"] == scope_digest(scope)
    with pytest.raises(FileExistsError):
        export_policy(
            policy=Path("data/scenarios/example_1/policy.json"),
            snapshot_id=SNAPSHOT_ID,
            scope_json=Path("input_examples/example_1.json"),
            out=out,
        )


def test_export_emits_concrete_registration_sql(tmp_path):
    """Registration statements are generated from the ACTUAL export values, never prose."""
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "scripts"))
    from export_zetaris_policy import export_policy

    policy = _P("data/scenarios/example_1/policy.json")
    out = tmp_path / "dw_concrete"
    manifest = export_policy(
        policy=policy, snapshot_id="example1_base_v1",
        scope_json=_P("input_examples/example_1.json"), out=out,
        reference_db="DRIFTWATCH_REF",
        rules_table="policy_rules_base_v1",
        manifest_table="policy_manifest_base_v1",
    )
    sql = (out / "proposed_registration.sql").read_text(encoding="utf-8")
    assert f'content_sha256={manifest["content_sha256"]}' in sql          # generated, not copied
    assert "CREATE LIGHTNING DATABASE DRIFTWATCH_REF" in sql
    assert ('CREATE LIGHTNING FILESTORE TABLE policy_rules_base_v1 FROM DRIFTWATCH_REF '
            'FORMAT CSV OPTIONS (\n  path "file:///home/zetaris/customer-data/shared/'
            'driftwatch-policy/example1_base_v1/rules.csv",\n  header "true"\n)') in sql or \
           ('path "file:///home/zetaris/customer-data/shared/driftwatch-policy/'
            'example1_base_v1/rules.csv"') in sql
    assert ('path "file:///home/zetaris/customer-data/shared/driftwatch-policy/'
            'example1_base_v1/manifest.csv"') in sql


def test_export_when_json_is_quote_safe(tmp_path):
    """Engine CSV parsers mangle RFC-4180 escaped quotes; exported cells must contain
    no double quotes and no bare commas, while staying exactly decodable."""
    import sys
    from urllib.parse import unquote
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "scripts"))
    from export_zetaris_policy import export_policy

    out = tmp_path / "dw_v2"
    manifest = export_policy(
        policy=_P("data/scenarios/example_1/policy.json"), snapshot_id="example1_base_v2",
        scope_json=_P("input_examples/example_1.json"), out=out,
        reference_db="DRIFTWATCH_REF", rules_table="policy_rules_base_v2",
        manifest_table="policy_manifest_base_v2")
    raw = (out / "rules.csv").read_text(encoding="utf-8")
    cell_lines = [ln for ln in raw.splitlines() if "%22" in ln]
    assert cell_lines, "when_json cells must be percent-encoded"
    for ln in raw.splitlines():
        # a data line for a rule with embedded JSON must carry no bare double-quote pairs
        assert '""' not in ln
    import csv as _csv
    rows = list(_csv.DictReader(raw.splitlines()))
    import json as _json
    for r in rows:
        parsed = _json.loads(unquote(r["when_json"]))   # decodes to valid JSON
        assert isinstance(parsed, dict)
    # digest is over parsed rule content — the encoding must not move it
    assert manifest["content_sha256"] == (
        "58729b59912976e202d4c002c144e4701193f6a54a7300b50869cbbab1bc205f")
