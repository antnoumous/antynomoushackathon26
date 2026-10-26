"""Fixed, secret-in-stdin acceptance runner; this module performs no work on import."""
from __future__ import annotations
import json
import re
from urllib.parse import urlsplit
from pathlib import Path
import shlex
import subprocess
from scripts.verify_zetaris_policy import validate_settings

ALLOWED_ENV = {"LLM_PROVIDER", "METERLESS_BASE_URL", "METERLESS_TOKEN", "METERLESS_MODEL",
               "ZETARIS_REST_URL", "ZETARIS_API_KEY", "ZETARIS_ORG_ID"}


def validate_runtime_env(payload: dict) -> dict[str, str]:
    if (not isinstance(payload, dict) or set(payload) != ALLOWED_ENV
            or any(not isinstance(value, str) or not value.strip() or len(value) > 8192
                   or any(ord(char) < 32 or ord(char) == 127 for char in value) for value in payload.values())
            or payload["LLM_PROVIDER"] != "meterless" or payload["METERLESS_MODEL"] != "meterless/local"
            or payload["METERLESS_TOKEN"] == "rt-local"):
        raise ValueError("invalid runtime environment")
    for key in ("METERLESS_BASE_URL", "ZETARIS_REST_URL"):
        try:
            url = urlsplit(payload[key])
            if (url.scheme not in {"http", "https"} or url.hostname not in {"127.0.0.1", "localhost", "::1"}
                    or url.username is not None or url.password is not None or url.query or url.fragment
                    or url.port == 0):
                raise ValueError()
        except ValueError:
            raise ValueError("invalid runtime endpoint") from None
    return dict(payload)


def _safe_path(value: str, prefix: str) -> str:
    if (not isinstance(value, str) or len(value) > 240 or not value.startswith(prefix)
            or re.fullmatch(r"[A-Za-z0-9_./-]+", value) is None
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("invalid remote path")
    return value


def read_runtime_payload(stream) -> dict:
    raw = stream.read(65537)
    if not isinstance(raw, bytes) or len(raw) > 65536:
        raise ValueError("runtime payload exceeds byte limit")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or set(payload) != {"env", "base_settings", "variant_settings"}:
            raise ValueError()
        return {"env": validate_runtime_env(payload["env"]),
                "base_settings": validate_settings(payload["base_settings"]),
                "variant_settings": validate_settings(payload["variant_settings"])}
    except (ValueError, TypeError, KeyError):
        raise ValueError("invalid runtime payload") from None


def run_remote_acceptance(*, ssh_config: Path, release_dir: str, runtime_env: dict[str, str],
                          base_settings: dict, variant_settings: dict, output_dir: str,
                          run_subprocess=subprocess.run) -> int:
    _safe_path(release_dir, "driftwatch-meterless/")
    _safe_path(output_dir, "logs/")
    payload = {"env": validate_runtime_env(runtime_env), "base_settings": validate_settings(base_settings),
               "variant_settings": validate_settings(variant_settings)}
    command = (f"cd {shlex.quote(release_dir)} && systemd-run --user --scope --quiet"
               " -p MemoryMax=1073741824 -p TasksMax=64 .venv/bin/python scripts/verify_meterless_sponsors.py"
               f" --stdin-env --scenario data/scenarios/example_1 --output-dir {shlex.quote(output_dir)}")
    serialized = json.dumps(payload, allow_nan=False)
    if len(serialized.encode("utf-8")) > 65536:
        raise ValueError("runtime payload exceeds byte limit")
    try:
        result = run_subprocess(["ssh", "-F", str(ssh_config), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=yes", "zetaris-01", command],
            input=serialized, text=True, capture_output=True, timeout=1200)
    except Exception:
        raise RuntimeError("remote acceptance transport failed") from None
    return result.returncode
