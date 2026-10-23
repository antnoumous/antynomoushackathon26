"""Secret-safe Zetaris REST settings and absolute-deadline supervised SQL fetch.

No ambient proxy/env trust. Worker runs under multiprocessing spawn; parent enforces
the monotonic cutoff and never surfaces tokens, raw bodies or headers in errors.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests
from pydantic import SecretStr

from app.sources.base import SourceError

Category = Literal[
    "configuration",
    "authentication",
    "transport",
    "deadline",
    "query",
    "schema",
    "incomplete",
]

_ALLOWED_CATEGORIES = frozenset({
    "configuration",
    "authentication",
    "transport",
    "deadline",
    "query",
    "schema",
    "incomplete",
})

ENDPOINT_PATH = "/api/v1.0/sql-editor/sqls/run"
SQL_SOURCE = "SqlEditor"
SQL_LIMIT = 257
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_RESULT_BYTES = 4 * 1024 * 1024
CLEANUP_RESERVE = 0.5
MAX_QUERIES = 2
_CONNECT_TIMEOUT_S = 5.0
_READ_TIMEOUT_S = 25.0

_QUALIFIED_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")
_SNAPSHOT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ORG_ID = re.compile(r"^[0-9]+$")
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class ZetarisError(SourceError):
    """Sanitized transport/settings failure. str() exposes only the category."""

    def __init__(self, category: Category, *, retryable: bool) -> None:
        if category not in _ALLOWED_CATEGORIES:
            category = "transport"
            retryable = True
        self.category: Category = category  # type: ignore[assignment]
        self.retryable = bool(retryable)
        super().__init__(f"zetaris:{self.category}")

    def __str__(self) -> str:
        return f"zetaris:{self.category}"


def _raise_config() -> None:
    raise ZetarisError("configuration", retryable=False)


def _validate_base_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url:
        _raise_config()
    parsed = urlparse(base_url)
    if parsed.username is not None or parsed.password is not None:
        _raise_config()
    if parsed.query or parsed.fragment:
        _raise_config()
    # urlparse puts userinfo in username/password; also reject netloc with '@'
    if "@" in (parsed.netloc or ""):
        _raise_config()
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        _raise_config()
    host = parsed.hostname
    if host is None:
        _raise_config()
    # Normalize bracketed IPv6 for comparison
    host_key = host.lower()
    if scheme == "http" and host_key not in _LOOPBACK_HOSTS:
        _raise_config()
    if parsed.port is not None and (parsed.port < 1 or parsed.port > 65535):
        _raise_config()
    # Keep path for documentation parity with ZETARIS_REST_URL; request path is fixed.
    return base_url.rstrip("/")


def _validate_identifier(value: str) -> str:
    if not isinstance(value, str) or not _QUALIFIED_ID.fullmatch(value):
        _raise_config()
    return value


def _validate_snapshot(value: str) -> str:
    if not isinstance(value, str) or not _SNAPSHOT_ID.fullmatch(value):
        _raise_config()
    return value


def _validate_digest(value: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        _raise_config()
    return value


def _validate_org(value: Any) -> str:
    if not isinstance(value, str) or not _ORG_ID.fullmatch(value):
        _raise_config()
    return value


def _origin(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    # Preserve IPv6 brackets in the request URL
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port is not None:
        netloc = f"{host}:{parsed.port}"
    else:
        netloc = host
    return f"{parsed.scheme}://{netloc}"


@dataclass(frozen=True)
class ZetarisSettings:
    base_url: str
    api_key: SecretStr
    org_id: str
    policy_object: str
    manifest_object: str
    snapshot_id: str
    expected_sha256: str

    def __post_init__(self) -> None:
        # Validate even for direct construction — no bypass.
        if not isinstance(self.api_key, SecretStr):
            _raise_config()
        object.__setattr__(self, "base_url", _validate_base_url(self.base_url))
        object.__setattr__(self, "org_id", _validate_org(self.org_id))
        object.__setattr__(self, "policy_object", _validate_identifier(self.policy_object))
        object.__setattr__(self, "manifest_object", _validate_identifier(self.manifest_object))
        object.__setattr__(self, "snapshot_id", _validate_snapshot(self.snapshot_id))
        object.__setattr__(self, "expected_sha256", _validate_digest(self.expected_sha256))

    @classmethod
    def from_env(cls) -> "ZetarisSettings":
        try:
            key = os.environ["ZETARIS_API_KEY"]
            return cls(
                base_url=os.environ["ZETARIS_REST_URL"],
                api_key=SecretStr(key),
                org_id=os.environ["ZETARIS_ORG_ID"],
                policy_object=os.environ["ZETARIS_POLICY_OBJECT"],
                manifest_object=os.environ["ZETARIS_MANIFEST_OBJECT"],
                snapshot_id=os.environ["ZETARIS_POLICY_SNAPSHOT"],
                expected_sha256=os.environ["ZETARIS_POLICY_SHA256"],
            )
        except ZetarisError:
            raise
        except Exception:
            raise ZetarisError("configuration", retryable=False) from None


def decode_response(response: dict, columns: tuple[str, ...]) -> list[dict]:
    """Validate a verified SQL-editor response and zip rows to column names."""
    if not isinstance(response, dict):
        raise ZetarisError("schema", retryable=False)
    if "error" in response or response.get("success") is False:
        raise ZetarisError("query", retryable=False)
    if "headers" not in response or "data" not in response or "total" not in response:
        raise ZetarisError("schema", retryable=False)
    headers = response["headers"]
    data = response["data"]
    total = response["total"]
    if not isinstance(columns, tuple) or not all(isinstance(c, str) for c in columns):
        raise ZetarisError("schema", retryable=False)
    if headers != list(columns):
        raise ZetarisError("schema", retryable=False)
    if not isinstance(data, list):
        raise ZetarisError("schema", retryable=False)
    width = len(columns)
    for row in data:
        if not isinstance(row, list) or len(row) != width:
            raise ZetarisError("schema", retryable=False)
    if type(total) is not int:  # reject bool and float
        raise ZetarisError("schema", retryable=False)
    if total < len(data):
        raise ZetarisError("schema", retryable=False)
    if total > len(data):
        raise ZetarisError("incomplete", retryable=False)
    return [dict(zip(columns, row)) for row in data]


def _write_envelope(path: str, payload: dict[str, Any]) -> None:
    directory = str(Path(path).parent)
    fd, tmp = tempfile.mkstemp(prefix="zetaris-result-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, allow_nan=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _fail_envelope(category: Category, *, retryable: bool) -> dict[str, Any]:
    return {"status": "error", "category": category, "retryable": retryable}


def _read_limited(response: requests.Response) -> bytes:
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise ZetarisError("transport", retryable=True)
        chunks.append(chunk)
    return b"".join(chunks)


def _classify_status(status: int) -> tuple[Category, bool] | None:
    if status in (401, 403):
        return "authentication", False
    if status == 429 or status >= 500:
        return "transport", True
    if status == 202:
        return "query", False
    if 300 <= status < 400:
        return "transport", False
    if status != 200:
        return "transport", True
    return None


def _parse_success_body(raw: bytes) -> dict[str, Any]:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        raise ZetarisError("schema", retryable=False) from None
    if not isinstance(obj, dict):
        raise ZetarisError("schema", retryable=False)
    if "error" in obj or obj.get("success") is False:
        raise ZetarisError("query", retryable=False)
    for key in ("headers", "data", "total"):
        if key not in obj:
            raise ZetarisError("schema", retryable=False)
    if not isinstance(obj["headers"], list) or not isinstance(obj["data"], list):
        raise ZetarisError("schema", retryable=False)
    if type(obj["total"]) is not int:
        raise ZetarisError("schema", retryable=False)
    return obj


def _worker(settings: ZetarisSettings, queries: tuple[str, ...], output_path: str) -> None:
    """Top-level spawn target: run at most two SQL POSTs and write a bounded envelope."""
    try:
        if not isinstance(queries, tuple) or not (1 <= len(queries) <= MAX_QUERIES):
            _write_envelope(output_path, _fail_envelope("configuration", retryable=False))
            return
        if not all(isinstance(q, str) for q in queries):
            _write_envelope(output_path, _fail_envelope("configuration", retryable=False))
            return

        url = _origin(settings.base_url) + ENDPOINT_PATH
        token = settings.api_key.get_secret_value()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Org-ID": settings.org_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        responses: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="driftwatch-zetaris-worker-"):
            session = requests.Session()
            session.trust_env = False
            # No HTTPAdapter retry mounts — default session has none beyond urllib3 Retry(0)
            session.adapters  # keep explicit session without remounting retries
            try:
                for sql in queries:
                    body = {
                        "queryId": str(uuid.uuid4()),
                        "sql": sql,
                        "source": SQL_SOURCE,
                        "limit": SQL_LIMIT,
                    }
                    try:
                        resp = session.post(
                            url,
                            headers=headers,
                            json=body,
                            timeout=(_CONNECT_TIMEOUT_S, _READ_TIMEOUT_S),
                            allow_redirects=False,
                            stream=True,
                        )
                    except requests.RequestException:
                        _write_envelope(output_path, _fail_envelope("transport", retryable=True))
                        return
                    classified = _classify_status(resp.status_code)
                    if classified is not None:
                        category, retryable = classified
                        _write_envelope(output_path, _fail_envelope(category, retryable=retryable))
                        return
                    try:
                        raw = _read_limited(resp)
                        parsed = _parse_success_body(raw)
                    except ZetarisError as exc:
                        _write_envelope(
                            output_path,
                            _fail_envelope(exc.category, retryable=exc.retryable),
                        )
                        return
                    responses.append(parsed)
            finally:
                session.close()

        _write_envelope(
            output_path,
            {"status": "ok", "responses": responses},
        )
    except ZetarisError as exc:
        try:
            _write_envelope(output_path, _fail_envelope(exc.category, retryable=exc.retryable))
        except Exception:
            pass
    except Exception:
        try:
            _write_envelope(output_path, _fail_envelope("transport", retryable=True))
        except Exception:
            pass


def _read_worker_result(path: Path, expected_responses: int) -> list[dict]:
    try:
        size = path.stat().st_size
    except OSError:
        raise ZetarisError("transport", retryable=True) from None
    if size > MAX_RESULT_BYTES:
        raise ZetarisError("transport", retryable=True)
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_RESULT_BYTES:
            raise ZetarisError("transport", retryable=True)
        envelope = json.loads(raw.decode("utf-8"))
    except ZetarisError:
        raise
    except Exception:
        raise ZetarisError("transport", retryable=True) from None
    if not isinstance(envelope, dict):
        raise ZetarisError("transport", retryable=True)
    status = envelope.get("status")
    if status == "error":
        category = envelope.get("category")
        retryable = envelope.get("retryable")
        if category not in _ALLOWED_CATEGORIES or type(retryable) is not bool:
            raise ZetarisError("transport", retryable=True)
        raise ZetarisError(category, retryable=retryable)  # type: ignore[arg-type]
    if status != "ok":
        raise ZetarisError("transport", retryable=True)
    responses = envelope.get("responses")
    if not isinstance(responses, list) or len(responses) != expected_responses:
        raise ZetarisError("transport", retryable=True)
    if not all(isinstance(item, dict) for item in responses):
        raise ZetarisError("transport", retryable=True)
    # Allow only expected envelope keys on success
    allowed = {"status", "responses"}
    if set(envelope) - allowed:
        raise ZetarisError("transport", retryable=True)
    return responses


def run_sql_batch(
    settings: ZetarisSettings,
    queries: tuple[str, ...],
    deadline: float,
) -> list[dict]:
    if not isinstance(queries, tuple) or not (1 <= len(queries) <= MAX_QUERIES):
        raise ZetarisError("configuration", retryable=False)
    if not all(isinstance(q, str) for q in queries):
        raise ZetarisError("configuration", retryable=False)

    cleanup_reserve = CLEANUP_RESERVE
    remaining = deadline - time.monotonic()
    if remaining <= cleanup_reserve:
        raise ZetarisError("deadline", retryable=False)

    ctx = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory(prefix="driftwatch-zetaris-") as directory:
        output = str(Path(directory) / "result.json")
        process = ctx.Process(target=_worker, args=(settings, queries, output))
        try:
            try:
                process.start()
            except Exception:
                # A child that never launched is a transport failure; nothing
                # escapes run_sql_batch except ZetarisError.
                raise ZetarisError("transport", retryable=True) from None
            process.join(max(0.0, deadline - time.monotonic() - cleanup_reserve))
            if process.is_alive():
                raise ZetarisError("deadline", retryable=False)
            if process.exitcode != 0 or not Path(output).is_file():
                raise ZetarisError("transport", retryable=True)
            return _read_worker_result(Path(output), expected_responses=len(queries))
        finally:
            if process.is_alive():
                process.terminate()
                process.join(0.25)
            if process.is_alive():
                process.kill()
                process.join(0.25)
            if process.is_alive():
                raise ZetarisError("transport", retryable=False)
            process.close()
