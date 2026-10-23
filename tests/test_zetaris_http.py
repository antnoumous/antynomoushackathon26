"""Secret-safe Zetaris REST settings and supervised fetch (Task 2)."""
from __future__ import annotations

import json
import multiprocessing
import os
import socket
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

import pytest
from pydantic import SecretStr

# ---------------------------------------------------------------------------
# Test-local settings constructor (plan Step 1)
# ---------------------------------------------------------------------------

VALID_DIGEST = "a" * 64
TOKEN = "test-only-token"


def settings(
    *,
    base_url: str | None = None,
    api_key: str = TOKEN,
    org_id: str = "6",
    policy_object: str = "DRIFTWATCH_REF.policy_rules_base_v1",
    manifest_object: str = "DRIFTWATCH_REF.policy_manifest_base_v1",
    snapshot_id: str = "example1_base_v1",
    expected_sha256: str = VALID_DIGEST,
    port: int | None = None,
):
    from app.sources.zetaris_http import ZetarisSettings

    if base_url is None:
        host_port = f"127.0.0.1:{port}" if port is not None else "127.0.0.1:9"
        base_url = f"http://{host_port}/api/v1.0"
    return ZetarisSettings(
        base_url=base_url,
        api_key=SecretStr(api_key),
        org_id=org_id,
        policy_object=policy_object,
        manifest_object=manifest_object,
        snapshot_id=snapshot_id,
        expected_sha256=expected_sha256,
    )


# ---------------------------------------------------------------------------
# Local ThreadingHTTPServer fixture — daemon threads, no access log
# ---------------------------------------------------------------------------

NORMAL_BODY = {"headers": ["one"], "data": [["1"]], "total": 1, "timeUsed": 1}
ENDPOINT = "/api/v1.0/sql-editor/sqls/run"


class _Recorder:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests: list[dict[str, Any]] = []
        self.saw_post = False
        self.mode: str = "ok"
        self.redirect_to: str | None = None
        self.custom_status: int | None = None
        self.custom_body: bytes | None = None
        self.drip: bool = False
        self.close_after_accept: bool = False
        self.auth_tokens_seen: list[str] = []
        self.orgs_seen: list[str] = []


def _make_handler(recorder: _Recorder) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return  # no access log

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            auth = self.headers.get("Authorization", "")
            org = self.headers.get("X-Org-ID", "")
            try:
                body = json.loads(raw.decode("utf-8")) if raw else None
            except Exception:
                body = None
            with recorder.lock:
                recorder.saw_post = True
                recorder.requests.append({
                    "path": self.path,
                    "auth": auth,
                    "org": org,
                    "body": body,
                    "headers": {k: v for k, v in self.headers.items()},
                })
                recorder.auth_tokens_seen.append(auth)
                recorder.orgs_seen.append(org)

            if recorder.close_after_accept:
                try:
                    self.connection.close()
                except Exception:
                    pass
                return

            if recorder.drip:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                payload = json.dumps(NORMAL_BODY).encode("utf-8")
                for i, byte in enumerate(payload):
                    chunk = f"1\r\n{chr(byte)}\r\n".encode("latin-1")
                    try:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except Exception:
                        return
                    time.sleep(0.05)
                try:
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                except Exception:
                    pass
                return

            if recorder.redirect_to is not None:
                self.send_response(302)
                self.send_header("Location", recorder.redirect_to)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            status = recorder.custom_status if recorder.custom_status is not None else 200
            if recorder.custom_body is not None:
                body_bytes = recorder.custom_body
            elif status == 200:
                body_bytes = json.dumps(NORMAL_BODY).encode("utf-8")
            else:
                body_bytes = b'{"error":"x"}'

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            if status != 204:
                self.wfile.write(body_bytes)

        def do_GET(self) -> None:  # noqa: N802
            self.send_response(404)
            self.end_headers()

    return Handler


@pytest.fixture
def http_server():
    recorder = _Recorder()
    handler = _make_handler(recorder)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield recorder, port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2.0)


def _child_pids() -> set[int]:
    """OS-visible children of this process (macOS/Linux)."""
    try:
        import subprocess
        out = subprocess.check_output(
            ["pgrep", "-P", str(os.getpid())], text=True, stderr=subprocess.DEVNULL
        )
        return {int(line) for line in out.splitlines() if line.strip()}
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# Step 1 — settings / credential / URL validation
# ---------------------------------------------------------------------------

def test_expired_budget_starts_no_worker(monkeypatch):
    import app.sources.zetaris_http as http

    def forbidden(*args, **kwargs):
        raise AssertionError("worker created after deadline")

    monkeypatch.setattr(http.multiprocessing, "get_context", forbidden)
    with pytest.raises(http.ZetarisError) as error:
        http.run_sql_batch(settings(), ("SELECT 1",), time.monotonic() - 1)
    assert error.value.category == "deadline"


@pytest.mark.parametrize("org_id", ["", "6a", "6.0", " 6", "6 ", "+6", "-1", "0x6", "6e0"])
def test_malformed_numeric_org_rejected(org_id):
    from app.sources.zetaris_http import ZetarisError

    with pytest.raises(ZetarisError) as err:
        settings(org_id=org_id)
    assert err.value.category == "configuration"
    assert TOKEN not in str(err.value)


def test_non_string_org_rejected():
    from app.sources.zetaris_http import ZetarisError, ZetarisSettings

    with pytest.raises(ZetarisError) as err:
        ZetarisSettings(
            base_url="http://127.0.0.1:9/api/v1.0",
            api_key=SecretStr(TOKEN),
            org_id=6,  # type: ignore[arg-type]
            policy_object="DRIFTWATCH_REF.policy_rules_base_v1",
            manifest_object="DRIFTWATCH_REF.policy_manifest_base_v1",
            snapshot_id="example1_base_v1",
            expected_sha256=VALID_DIGEST,
        )
    assert err.value.category == "configuration"
    assert TOKEN not in str(err.value)


@pytest.mark.parametrize("bad_url", [
    "http://user:pass@127.0.0.1:9/api/v1.0",
    "http://127.0.0.1:9/api/v1.0?x=1",
    "http://127.0.0.1:9/api/v1.0#frag",
    "http://user@127.0.0.1:9/api/v1.0",
])
def test_url_userinfo_query_fragment_rejected(bad_url):
    from app.sources.zetaris_http import ZetarisError

    with pytest.raises(ZetarisError) as err:
        settings(base_url=bad_url)
    assert err.value.category == "configuration"


def test_non_loopback_http_rejected():
    from app.sources.zetaris_http import ZetarisError

    with pytest.raises(ZetarisError) as err:
        settings(base_url="http://example.com/api/v1.0")
    assert err.value.category == "configuration"


def test_unknown_backend_scheme_rejected():
    from app.sources.zetaris_http import ZetarisError

    with pytest.raises(ZetarisError) as err:
        settings(base_url="ftp://127.0.0.1:9/api/v1.0")
    assert err.value.category == "configuration"
    with pytest.raises(ZetarisError) as err2:
        settings(base_url="file:///tmp/x")
    assert err2.value.category == "configuration"


@pytest.mark.parametrize("field,value", [
    ("policy_object", "DRIFTWATCH_REF.policy;DROP"),
    ("policy_object", "a.b.c"),
    ("policy_object", "onlyone"),
    ("policy_object", "DRIFTWATCH_REF.policy' OR '1'='1"),
    ("policy_object", "DRIFTWATCH_REF.policy--"),
    ("manifest_object", "REF.obj;SELECT"),
    ("snapshot_id", "bad;DROP"),
    ("snapshot_id", "has space"),
    ("snapshot_id", "x" * 65),
    ("snapshot_id", ""),
    ("expected_sha256", "A" * 64),  # uppercase rejected
    ("expected_sha256", "g" * 64),
    ("expected_sha256", "a" * 63),
])
def test_identifier_snapshot_injection_rejected(field, value):
    from app.sources.zetaris_http import ZetarisError

    kwargs = {field: value}
    with pytest.raises(ZetarisError) as err:
        settings(**kwargs)
    assert err.value.category == "configuration"
    assert TOKEN not in str(err.value)
    assert TOKEN not in repr(err.value)


def test_direct_constructor_cannot_bypass_validation():
    from app.sources.zetaris_http import ZetarisError, ZetarisSettings

    with pytest.raises(ZetarisError) as err:
        ZetarisSettings(
            base_url="http://evil.example/api/v1.0",
            api_key=SecretStr(TOKEN),
            org_id="6",
            policy_object="DRIFTWATCH_REF.policy_rules_base_v1",
            manifest_object="DRIFTWATCH_REF.policy_manifest_base_v1",
            snapshot_id="example1_base_v1",
            expected_sha256=VALID_DIGEST,
        )
    assert err.value.category == "configuration"


def test_https_required_except_explicit_loopback():
    from app.sources.zetaris_http import ZetarisError

    # loopback HTTP allowed
    for host in ("localhost", "127.0.0.1", "[::1]"):
        s = settings(base_url=f"http://{host}:9/api/v1.0")
        assert s.base_url.startswith("http://")
    # non-loopback must be HTTPS
    s2 = settings(base_url="https://example.com/api/v1.0")
    assert s2.base_url.startswith("https://")
    with pytest.raises(ZetarisError) as err:
        settings(base_url="http://10.0.0.1:9/api/v1.0")
    assert err.value.category == "configuration"


def test_repr_and_exception_exclude_token():
    from app.sources.zetaris_http import ZetarisError

    s = settings()
    text = repr(s)
    assert TOKEN not in text
    assert "test-only" not in text
    err = ZetarisError("authentication", retryable=False)
    assert str(err) == "zetaris:authentication"
    assert TOKEN not in str(err)
    assert TOKEN not in repr(err)
    try:
        raise err
    except ZetarisError:
        tb = traceback.format_exc()
    assert TOKEN not in tb
    assert str(err) in tb


def test_from_env_reads_process_environment(monkeypatch):
    from app.sources.zetaris_http import ZetarisSettings

    monkeypatch.setenv("ZETARIS_REST_URL", "http://127.0.0.1:9/api/v1.0")
    monkeypatch.setenv("ZETARIS_API_KEY", TOKEN)
    monkeypatch.setenv("ZETARIS_ORG_ID", "6")
    monkeypatch.setenv("ZETARIS_POLICY_OBJECT", "DRIFTWATCH_REF.policy_rules_base_v1")
    monkeypatch.setenv("ZETARIS_MANIFEST_OBJECT", "DRIFTWATCH_REF.policy_manifest_base_v1")
    monkeypatch.setenv("ZETARIS_POLICY_SNAPSHOT", "example1_base_v1")
    monkeypatch.setenv("ZETARIS_POLICY_SHA256", VALID_DIGEST)
    s = ZetarisSettings.from_env()
    assert s.org_id == "6"
    assert TOKEN not in repr(s)
    assert s.api_key.get_secret_value() == TOKEN


# ---------------------------------------------------------------------------
# Transport shape / status taxonomy (via real spawn worker)
# ---------------------------------------------------------------------------

def test_post_path_uuid_org_and_body_shape(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    s = settings(port=port)
    responses = http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert len(responses) == 1
    assert responses[0]["headers"] == ["one"]
    assert len(recorder.requests) == 1
    req = recorder.requests[0]
    assert req["path"] == ENDPOINT
    assert req["org"] == "6"
    assert req["auth"] == f"Bearer {TOKEN}"
    body = req["body"]
    assert body["source"] == "SqlEditor"
    assert body["limit"] == 257
    assert body["sql"] == "SELECT 1"
    assert "queryId" in body
    uuid.UUID(body["queryId"])  # raises if not a UUID
    # fresh UUID (syntactically valid UUID string)
    assert body["queryId"] != ""


def test_fresh_uuid_per_request(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    s = settings(port=port)
    http.run_sql_batch(s, ("SELECT 1", "SELECT 2"), time.monotonic() + 15)
    assert len(recorder.requests) == 2
    ids = [r["body"]["queryId"] for r in recorder.requests]
    assert ids[0] != ids[1]
    for qid in ids:
        uuid.UUID(qid)


@pytest.mark.parametrize("status,category,retryable", [
    (401, "authentication", False),
    (403, "authentication", False),
    (429, "transport", True),
    (500, "transport", True),
    (502, "transport", True),
    (503, "transport", True),
])
def test_status_taxonomy_auth_and_transport(http_server, status, category, retryable):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    recorder.custom_status = status
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert err.value.category == category
    assert err.value.retryable is retryable
    assert TOKEN not in str(err.value)


def test_http_202_is_bounded_query_failure(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    recorder.custom_status = 202
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert err.value.category == "query"
    assert err.value.retryable is False


def test_redirect_rejected_without_forwarding_authorization():
    import app.sources.zetaris_http as http

    # Secondary sink that must never see Authorization
    sink_recorder = _Recorder()
    sink = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(sink_recorder))
    sink.daemon_threads = True
    sink_thread = threading.Thread(target=sink.serve_forever, daemon=True)
    sink_thread.start()
    sink_port = sink.server_address[1]

    primary_recorder = _Recorder()
    primary_recorder.redirect_to = f"http://127.0.0.1:{sink_port}{ENDPOINT}"
    primary = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(primary_recorder))
    primary.daemon_threads = True
    primary_thread = threading.Thread(target=primary.serve_forever, daemon=True)
    primary_thread.start()
    primary_port = primary.server_address[1]
    try:
        s = settings(port=primary_port)
        with pytest.raises(http.ZetarisError) as err:
            http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
        assert err.value.category in {"transport", "query", "authentication"}
        assert err.value.retryable is False or err.value.category == "transport"
        # Authorization must not be forwarded to the redirect target
        assert sink_recorder.requests == []
        assert primary_recorder.saw_post is True
    finally:
        primary.shutdown()
        primary.server_close()
        primary_thread.join(2.0)
        sink.shutdown()
        sink.server_close()
        sink_thread.join(2.0)


def test_non_json_body_safe_failure(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    recorder.custom_body = b"not-json<<"
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert err.value.category in {"schema", "transport", "query"}
    assert TOKEN not in str(err.value)


def test_oversized_body_safe_failure(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    # Just over 2 MiB
    recorder.custom_body = b"x" * (2 * 1024 * 1024 + 64)
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 15)
    assert err.value.category == "transport"
    assert TOKEN not in str(err.value)


# ---------------------------------------------------------------------------
# decode_response (pure; no network)
# ---------------------------------------------------------------------------

def test_decode_response_happy_path():
    from app.sources.zetaris_http import decode_response

    rows = decode_response(
        {"headers": ["one", "two"], "data": [["a", "b"], ["c", "d"]], "total": 2, "timeUsed": 1},
        ("one", "two"),
    )
    assert rows == [{"one": "a", "two": "b"}, {"one": "c", "two": "d"}]


def test_decode_response_exact_headers_order():
    from app.sources.zetaris_http import ZetarisError, decode_response

    with pytest.raises(ZetarisError) as err:
        decode_response(
            {"headers": ["two", "one"], "data": [["a", "b"]], "total": 1, "timeUsed": 1},
            ("one", "two"),
        )
    assert err.value.category == "schema"


def test_decode_response_list_of_list_and_row_width():
    from app.sources.zetaris_http import ZetarisError, decode_response

    with pytest.raises(ZetarisError) as err:
        decode_response(
            {"headers": ["one"], "data": [{"one": 1}], "total": 1, "timeUsed": 1},
            ("one",),
        )
    assert err.value.category == "schema"
    with pytest.raises(ZetarisError) as err2:
        decode_response(
            {"headers": ["one", "two"], "data": [["a"]], "total": 1, "timeUsed": 1},
            ("one", "two"),
        )
    assert err2.value.category == "schema"


def test_decode_response_total_rules():
    from app.sources.zetaris_http import ZetarisError, decode_response

    # false total: total < length
    with pytest.raises(ZetarisError) as err:
        decode_response(
            {"headers": ["one"], "data": [["1"], ["2"]], "total": 1, "timeUsed": 1},
            ("one",),
        )
    assert err.value.category == "schema"
    # incomplete: total > length
    with pytest.raises(ZetarisError) as err2:
        decode_response(
            {"headers": ["one"], "data": [["1"]], "total": 2, "timeUsed": 1},
            ("one",),
        )
    assert err2.value.category == "incomplete"
    # non-integer total
    with pytest.raises(ZetarisError) as err3:
        decode_response(
            {"headers": ["one"], "data": [["1"]], "total": 1.0, "timeUsed": 1},
            ("one",),
        )
    assert err3.value.category == "schema"
    with pytest.raises(ZetarisError) as err4:
        decode_response(
            {"headers": ["one"], "data": [["1"]], "total": True, "timeUsed": 1},
            ("one",),
        )
    assert err4.value.category == "schema"


def test_decode_response_rejects_top_level_and_embedded_query_failures():
    from app.sources.zetaris_http import ZetarisError, decode_response

    with pytest.raises(ZetarisError) as err:
        decode_response({"error": "boom", "message": "no"}, ("one",))
    assert err.value.category == "query"
    # HTTP-200 shaped but embedded failure object
    with pytest.raises(ZetarisError) as err2:
        decode_response(
            {
                "headers": ["one"],
                "data": [["1"]],
                "total": 1,
                "timeUsed": 1,
                "error": {"code": "QUERY_FAILED"},
            },
            ("one",),
        )
    assert err2.value.category == "query"
    with pytest.raises(ZetarisError) as err3:
        decode_response(
            {"headers": ["one"], "data": [["1"]], "total": 1, "timeUsed": 1, "success": False},
            ("one",),
        )
    assert err3.value.category == "query"


def test_header_mismatch_via_transport_is_safe(http_server):
    """Worker returns response; decode_response (caller) rejects mismatch — also
    ensure worker itself tolerates returning the object. Mismatch checked here via decode."""
    from app.sources.zetaris_http import ZetarisError, decode_response

    with pytest.raises(ZetarisError) as err:
        decode_response(
            {"headers": ["wrong"], "data": [["1"]], "total": 1, "timeUsed": 1},
            ("one",),
        )
    assert err.value.category == "schema"


# ---------------------------------------------------------------------------
# Step 4 — slow body, concurrency, worker failure modes
# ---------------------------------------------------------------------------

def test_drip_bytes_past_deadline_reaps_children(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    recorder.drip = True
    s = settings(port=port)
    before = _child_pids()
    # Fixture is already up; measure only the transport call.
    start = time.monotonic()
    deadline = start + 1.5
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), deadline)
    elapsed = time.monotonic() - start
    assert err.value.category == "deadline"
    assert elapsed < 3.0
    assert recorder.saw_post is True
    # Allow a brief moment for reaping, still outside "measured" claim window for fixture.
    time.sleep(0.3)
    after = _child_pids()
    assert after == before


def test_concurrent_calls_no_crosstalk():
    import app.sources.zetaris_http as http

    rec_a = _Recorder()
    srv_a = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(rec_a))
    srv_a.daemon_threads = True
    t_a = threading.Thread(target=srv_a.serve_forever, daemon=True)
    t_a.start()
    port_a = srv_a.server_address[1]

    rec_b = _Recorder()
    srv_b = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(rec_b))
    srv_b.daemon_threads = True
    t_b = threading.Thread(target=srv_b.serve_forever, daemon=True)
    t_b.start()
    port_b = srv_b.server_address[1]

    token_a, token_b = "test-only-token", "test-only-token-b"
    org_a, org_b = "6", "7"
    results: dict[str, Any] = {}
    errors: dict[str, Any] = {}

    def call(label: str, port: int, token: str, org: str, sql: str) -> None:
        try:
            s = settings(port=port, api_key=token, org_id=org)
            results[label] = http.run_sql_batch(s, (sql,), time.monotonic() + 15)
        except Exception as exc:
            errors[label] = exc

    try:
        th_a = threading.Thread(target=call, args=("a", port_a, token_a, org_a, "SELECT A"))
        th_b = threading.Thread(target=call, args=("b", port_b, token_b, org_b, "SELECT B"))
        th_a.start()
        th_b.start()
        th_a.join(20)
        th_b.join(20)
        assert errors == {}, errors
        assert "a" in results and "b" in results
        assert len(rec_a.requests) == 1 and len(rec_b.requests) == 1
        assert rec_a.requests[0]["auth"] == f"Bearer {token_a}"
        assert rec_b.requests[0]["auth"] == f"Bearer {token_b}"
        assert rec_a.requests[0]["org"] == org_a
        assert rec_b.requests[0]["org"] == org_b
        assert rec_a.requests[0]["body"]["sql"] == "SELECT A"
        assert rec_b.requests[0]["body"]["sql"] == "SELECT B"
        # no swapped bodies
        assert rec_a.requests[0]["body"]["sql"] != rec_b.requests[0]["body"]["sql"]
    finally:
        srv_a.shutdown()
        srv_a.server_close()
        t_a.join(2.0)
        srv_b.shutdown()
        srv_b.server_close()
        t_b.join(2.0)


def _dying_worker(settings_obj, queries, output_path):
    raise SystemExit(1)


def _bad_envelope_worker(settings_obj, queries, output_path):
    from pathlib import Path
    Path(output_path).write_text("{not-json", encoding="utf-8")


def _weird_category_worker(settings_obj, queries, output_path):
    from pathlib import Path
    Path(output_path).write_text(
        json.dumps({"status": "error", "category": "not-a-real-category", "retryable": True}),
        encoding="utf-8",
    )


def test_worker_exit_before_write(monkeypatch, http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server

    monkeypatch.setattr(http, "_worker", _dying_worker)
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert err.value.category == "transport"
    assert err.value.retryable is True


def test_malformed_envelope(monkeypatch, http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server

    monkeypatch.setattr(http, "_worker", _bad_envelope_worker)
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert err.value.category == "transport"
    assert TOKEN not in str(err.value)


def test_malformed_envelope_unknown_category(monkeypatch, http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server

    monkeypatch.setattr(http, "_worker", _weird_category_worker)
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert err.value.category == "transport"
    assert "not-a-real-category" not in str(err.value)


def test_client_socket_error(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    recorder.close_after_accept = True
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    # Whichever bound fires first is contract-safe: the child classifies the aborted
    # read as transport, or the parent's deadline kills it. Both are bounded failures.
    assert err.value.category in {"transport", "deadline"}
    assert TOKEN not in str(err.value)


def test_query_count_limits(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, (), time.monotonic() + 5)
    assert err.value.category == "configuration"
    with pytest.raises(http.ZetarisError) as err2:
        http.run_sql_batch(s, ("a", "b", "c"), time.monotonic() + 5)
    assert err2.value.category == "configuration"


def test_two_query_batch_returns_two_responses(http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server
    s = settings(port=port)
    responses = http.run_sql_batch(s, ("SELECT 1", "SELECT 2"), time.monotonic() + 15)
    assert len(responses) == 2
    assert len(recorder.requests) == 2


def test_start_failure_is_classified(monkeypatch, http_server):
    import app.sources.zetaris_http as http

    recorder, port = http_server

    class _BoomProcess:
        def __init__(self, *a, **k):
            pass

        def start(self):
            raise OSError("resource exhausted")

        def is_alive(self):
            return False

        def join(self, timeout=None):
            pass

        def close(self):
            pass

    class _Ctx:
        Process = _BoomProcess

    monkeypatch.setattr(http.multiprocessing, "get_context", lambda kind: _Ctx())
    s = settings(port=port)
    with pytest.raises(http.ZetarisError) as err:
        http.run_sql_batch(s, ("SELECT 1",), time.monotonic() + 10)
    assert err.value.category == "transport"
    assert err.value.retryable is True
