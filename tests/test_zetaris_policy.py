"""Task 3: opt-in Zetaris policy source over a LOCAL fake transport — no network at any point.

Fixtures build the snapshot payloads from the real example_1 policy through Task 1 helpers,
so what the source validates here is exactly what the exporter publishes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.sources.base import Scope
from app.sources.policy_snapshot import policy_digest, scope_digest, validate_rules
from app.sources.zetaris_http import ZetarisError, ZetarisSettings
from app.sources.zetaris_policy import (
    MANIFEST_COLUMNS,
    RULE_COLUMNS,
    ZetarisPolicySource,
)

SCEN = Path("data/scenarios/example_1")
BASE = json.loads((SCEN / "policy.json").read_text())["rules"]
SNAP = "example1_base_v1"
POLICY_OBJECT = "DRIFTWATCH.DW_POLICY_RULES"
MANIFEST_OBJECT = "DRIFTWATCH.DW_POLICY_MANIFEST"

NORMALIZED = validate_rules(copy.deepcopy(BASE))
DIGEST = policy_digest(NORMALIZED)
EMPTY_DIGEST = policy_digest([])


def rule_rows(rows=None, snapshot=SNAP):
    rows = NORMALIZED if rows is None else rows
    return [
        {
            "snapshot_id": snapshot,
            "rule_id": r["rule_id"],
            "class": r["class"],
            "when_json": json.dumps(r["when"], sort_keys=True, separators=(",", ":")),
            "note": r["note"],
        }
        for r in rows
    ]


def manifest_row(expected=5, digest=DIGEST, snapshot=SNAP, scope_hash=None, **overrides):
    row = {
        "snapshot_id": snapshot,
        "schema_version": "1",
        "expected_count": str(expected),
        "content_sha256": digest,
        "requested_scope_hash": scope_hash if scope_hash is not None else _SCOPE_HASH,
        "observed_at_utc": "2026-10-22T07:00:00+00:00",
    }
    row.update(overrides)
    return row


def _scope():
    return Scope(
        compartment_ids=[],
        resource_types=["compute_instance", "block_volume", "reserved_public_ip"],
        lookback_hours=168,
        resolution_minutes=5,
    )


_SCOPE_HASH = scope_digest(_scope())


def sql_response(columns, rows):
    return {
        "headers": list(columns),
        "data": [[row[c] for c in columns] for row in rows],
        "total": len(rows),
        "timeUsed": 1,
    }


def settings_for(digest=DIGEST):
    return ZetarisSettings(
        base_url="http://127.0.0.1:8888/api/v1.0",
        api_key=SecretStr("test-only-token"),
        org_id="6",
        policy_object=POLICY_OBJECT,
        manifest_object=MANIFEST_OBJECT,
        snapshot_id=SNAP,
        expected_sha256=digest,
    )


def fake_transport(manifest_resp, rules_resp):
    calls = []

    def transport(config, queries, deadline):
        calls.append((queries, deadline))
        return [manifest_resp, rules_resp]

    return transport, calls


def payloads(manifest=None, rows=None, snapshot=SNAP):
    m = manifest if manifest is not None else manifest_row(scope_hash=_SCOPE_HASH)
    rule_list = rule_rows(snapshot=snapshot) if rows is None else rows
    return (
        sql_response(MANIFEST_COLUMNS, [m]),
        sql_response(RULE_COLUMNS, rule_list),
    )


def test_complete_snapshot_returns_live_provider_provenance():
    manifest_resp, rules_resp = payloads()
    transport, calls = fake_transport(manifest_resp, rules_resp)
    result = ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())
    assert result.backend == "live"
    assert result.provenance.provider == "zetaris"
    assert result.provenance.complete is True
    assert result.provenance.row_count == len(result.records) == 5
    assert len(calls) == 1 and len(calls[0][0]) == 2
    assert result.provenance.expected_count == 5
    assert result.provenance.snapshot_id == SNAP
    assert result.provenance.object_name == POLICY_OBJECT
    assert result.provenance.manifest_object == MANIFEST_OBJECT
    assert result.provenance.requested_scope_hash == _SCOPE_HASH
    assert result.provenance.content_sha256 == DIGEST
    assert result.provenance.observed_at_utc == "2026-10-22T07:00:00+00:00"
    assert "T" in result.provenance.fetched_at_utc  # distinct from source observation time
    assert result.degraded is False
    assert all(r["rule_id"].startswith("R-") for r in result.records)


def test_queries_are_two_pinned_selects_and_hash_covers_query_text_only():
    manifest_resp, rules_resp = payloads()
    transport, calls = fake_transport(manifest_resp, rules_resp)
    result = ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())
    manifest_sql, rules_sql = calls[0][0]
    assert "`class`" in rules_sql  # reserved word quoted
    assert rules_sql.endswith("ORDER BY `rule_id`")
    for q in (manifest_sql, rules_sql):
        assert q.upper().startswith("SELECT")
        assert SNAP in q
        assert "test-only-token" not in q
    expected_hash = hashlib.sha256("\n".join((manifest_sql, rules_sql)).encode("utf-8")).hexdigest()
    assert result.provenance.query_sha256 == expected_hash


def test_deadline_expired_before_fetch_raises_without_calling_transport():
    manifest_resp, rules_resp = payloads()
    transport, calls = fake_transport(manifest_resp, rules_resp)
    s = _scope()
    s.deadline_monotonic = time.monotonic() - 1
    with pytest.raises(ZetarisError) as err:
        ZetarisPolicySource(settings_for(), transport=transport).fetch(s)
    assert err.value.category == "deadline"
    assert err.value.retryable is False
    assert calls == []


def test_cutoff_beyond_run_deadline_capped_at_thirty_seconds():
    manifest_resp, rules_resp = payloads()
    transport, calls = fake_transport(manifest_resp, rules_resp)
    s = _scope()
    s.deadline_monotonic = time.monotonic() + 3600  # generous run budget
    before = time.monotonic()
    ZetarisPolicySource(settings_for(), transport=transport).fetch(s)
    deadline_seen = calls[0][1]
    assert deadline_seen <= before + 31  # source cap, not the run deadline


def test_count_mismatch_is_incomplete_not_partial():
    m = manifest_row(expected=6)  # claims 6, ships 5
    manifest_resp, rules_resp = payloads(manifest=m)
    transport, _ = fake_transport(manifest_resp, rules_resp)
    with pytest.raises(ZetarisError) as err:
        ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())
    assert err.value.category == "incomplete"


def test_pinned_digest_mismatch_fails_closed():
    manifest_resp, rules_resp = payloads()
    transport, _ = fake_transport(manifest_resp, rules_resp)
    with pytest.raises(ZetarisError) as err:
        ZetarisPolicySource(settings_for(digest="0" * 64), transport=transport).fetch(_scope())
    assert err.value.category == "query"  # mismatch maps to a sanitized category


def test_scope_hash_mismatch_rejected():
    m = manifest_row(scope_hash="f" * 64)
    manifest_resp, rules_resp = payloads(manifest=m)
    transport, _ = fake_transport(manifest_resp, rules_resp)
    with pytest.raises(ZetarisError):
        ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())


def test_wrong_snapshot_in_a_later_row_rejected():
    rows = rule_rows()
    rows[-1] = dict(rows[-1], snapshot_id="other_snapshot")
    manifest_resp, rules_resp = payloads(rows=rows)
    transport, _ = fake_transport(manifest_resp, rules_resp)
    with pytest.raises(ZetarisError) as err:
        ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())
    assert err.value.category == "query"


def test_duplicate_rule_ids_rejected():
    rows = rule_rows()
    rows[1] = dict(rows[0])  # duplicate R-1
    manifest_resp, rules_resp = payloads(rows=rows)
    transport, _ = fake_transport(manifest_resp, rules_resp)
    with pytest.raises(ZetarisError):
        ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())


def test_bad_final_row_never_returns_partial_result():
    rows = rule_rows()
    rows[-1] = dict(rows[-1], when_json='{"mean_cup_lt": 5}')  # poisoned last predicate
    manifest_resp, rules_resp = payloads(rows=rows)
    transport, _ = fake_transport(manifest_resp, rules_resp)
    with pytest.raises(ZetarisError) as err:
        ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())
    assert err.value.category == "schema"


def test_truncated_response_total_above_rows_is_incomplete():
    m = manifest_row(expected=5)
    rule_resp = sql_response(RULE_COLUMNS, rule_rows()[:4])
    rule_resp["total"] = 5  # server claims five, shipped four
    transport, _ = fake_transport(sql_response(MANIFEST_COLUMNS, [m]), rule_resp)
    with pytest.raises(ZetarisError):
        ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())


def test_reordered_headers_rejected():
    resp = sql_response(RULE_COLUMNS, rule_rows())
    resp["headers"] = list(RULE_COLUMNS)[::-1]
    transport, _ = fake_transport(payloads()[0], resp)
    with pytest.raises(ZetarisError):
        ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())


def test_257_rows_rejected_over_max():
    rows = [
        {
            "snapshot_id": SNAP,
            "rule_id": f"R-{i}",
            "class": "cost_waste",
            "when_json": "{}",
            "note": "n",
        }
        for i in range(257)
    ]
    m = manifest_row(expected=257, digest="0" * 64)
    transport, _ = fake_transport(sql_response(MANIFEST_COLUMNS, [m]), sql_response(RULE_COLUMNS, rows))
    with pytest.raises(ZetarisError):
        ZetarisPolicySource(settings_for(digest="0" * 64), transport=transport).fetch(_scope())


def test_complete_empty_snapshot_is_live_not_degraded():
    empty = [
        {
            "snapshot_id": SNAP,
            "schema_version": "1",
            "expected_count": "0",
            "content_sha256": EMPTY_DIGEST,
            "requested_scope_hash": _SCOPE_HASH,
            "observed_at_utc": "2026-10-22T07:00:00+00:00",
        }
    ]
    transport, _ = fake_transport(
        sql_response(MANIFEST_COLUMNS, empty),
        sql_response(RULE_COLUMNS, []),
    )
    result = ZetarisPolicySource(settings_for(digest=EMPTY_DIGEST), transport=transport).fetch(_scope())
    assert result.records == []
    assert result.backend == "live"
    assert result.degraded is False
    assert result.provenance.complete is True
    assert result.provenance.row_count == 0


def test_transport_error_propagates_unmodified():
    def raising(config, queries, deadline):
        raise ZetarisError("transport", retryable=True)

    with pytest.raises(ZetarisError) as err:
        ZetarisPolicySource(settings_for(), transport=raising).fetch(_scope())
    assert err.value.category == "transport"
    assert err.value.retryable is True


def test_source_decodes_quote_safe_transport_encoding():
    """The engine mangles RFC-4180 quoted cells; percent-encoded when_json rows must
    decode to identical rules with the SAME digest, and raw JSON containing a literal
    %22 must pass through untouched (collision-safe heuristic)."""
    from urllib.parse import quote
    encoded_rows = [dict(r, when_json=quote(r["when_json"], safe="[]{}"))
                    for r in rule_rows()]
    assert all('"' not in r["when_json"] and "," not in r["when_json"]
               for r in encoded_rows)
    m_resp, r_resp = payloads(rows=encoded_rows)
    transport, _ = fake_transport(m_resp, r_resp)
    res = ZetarisPolicySource(settings_for(), transport=transport).fetch(_scope())
    assert res.provenance.content_sha256 == DIGEST
    assert [rec["rule_id"] for rec in res.records] == [r["rule_id"] for r in NORMALIZED]


def test_decode_when_json_is_collision_safe():
    from urllib.parse import quote
    from app.sources.zetaris_policy import decode_when_json
    raw = '{"note":"keep the %22 text literal","resource_class":"block_volume"}'
    assert decode_when_json(raw) == raw                     # parses as-is, never decoded
    enc = quote('{"resource_class":"block_volume"}', safe="[]{}")
    assert decode_when_json(enc) == '{"resource_class":"block_volume"}'
    for bad in ('{"broken":', 'nonsense'):
        try:
            decode_when_json(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("garbage must still raise")
