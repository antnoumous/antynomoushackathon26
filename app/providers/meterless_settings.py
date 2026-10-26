from urllib.parse import urlsplit, urlunsplit
from dataclasses import dataclass
from typing import Mapping
from pydantic import BaseModel, ConfigDict, SecretStr, Field, ValidationError, field_validator


@dataclass(frozen=True)
class MeterlessReadiness:
    state: str
    model_ids: tuple[str, ...]


class MeterlessSettings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)
    base_url: str = "http://127.0.0.1:8088/v1"
    token: SecretStr
    model: str = "meterless/local"
    app_id: str = "driftwatch"
    timeout_s: float = Field(60.0, gt=0, le=60, allow_inf_nan=False, strict=True)

    @field_validator("base_url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        return normalize_base_url(value)

    @field_validator("token")
    @classmethod
    def require_real_token(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not raw.strip() or raw == "rt-local" or any(ord(c) < 32 or ord(c) == 127 for c in raw):
            raise MeterlessError("configuration")
        return value

    @field_validator("model")
    @classmethod
    def require_local_route(cls, value: str) -> str:
        if value != "meterless/local":
            raise MeterlessError("unsupported_mode")
        return value

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "MeterlessSettings":
        try:
            return cls(base_url=env.get("METERLESS_BASE_URL", "http://127.0.0.1:8088/v1"),
                       token=env.get("METERLESS_TOKEN", ""),
                       model=env.get("METERLESS_MODEL", "meterless/local"))
        except (ValidationError, TypeError):
            raise MeterlessError("configuration") from None


def discover(settings: MeterlessSettings, *, transport, timeout_s: float) -> MeterlessReadiness:
    try:
        data = transport("GET", settings.base_url + "/models", headers={
            "Authorization": "Bearer " + settings.token.get_secret_value(),
            "meterless-app": settings.app_id}, payload=None, timeout_s=min(settings.timeout_s, timeout_s))
    except MeterlessError as exc:
        return MeterlessReadiness("unauthorized" if exc.category == "unauthorized" else "offline", ())
    if (not isinstance(data, dict) or not isinstance(data.get("data"), list)
            or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in data["data"])):
        return MeterlessReadiness("offline", ())
    ids = tuple(dict.fromkeys(item["id"] for item in data["data"] if item["id"].startswith("meterless/")))
    state = "offline" if not ids else "online" if settings.model in ids else "unsupported_mode"
    return MeterlessReadiness(state, ids)



class MeterlessError(Exception):
    """Only bounded categories cross the provider boundary, never raw response text."""
    CATEGORIES = {"configuration", "unauthorized", "offline", "unsupported_mode", "timeout", "schema", "transport"}

    def __init__(self, category: str) -> None:
        self.category = category if category in self.CATEGORIES else "transport"
        super().__init__(f"meterless:{self.category}")


def normalize_base_url(value: str) -> str:
    if not isinstance(value, str) or not value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        raise MeterlessError("configuration")
    if "?" in value or "#" in value:
        raise MeterlessError("configuration")
    try:
        parts = urlsplit(value if "://" in value else "http://" + value)
        port = parts.port
        if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None
                or parts.password is not None or port == 0
                or parts.path.rstrip("/") not in {"", "/v1", "/v1/models", "/v1/chat/completions", "/healthz"}):
            raise MeterlessError("configuration")
        return urlunsplit((parts.scheme, parts.netloc, "/v1", "", ""))
    except ValueError:
        raise MeterlessError("configuration") from None
