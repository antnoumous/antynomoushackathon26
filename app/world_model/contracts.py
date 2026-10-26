from __future__ import annotations

from dataclasses import dataclass
import json


class WorldError(Exception):
    """Sanitised World Model failure; never includes a source payload."""
    CATEGORIES = {"configuration", "schema", "provenance", "storage", "limit", "context"}

    def __init__(self, category: str) -> None:
        self.category = category if category in self.CATEGORIES else "storage"
        super().__init__(f"world:{self.category}")


@dataclass(frozen=True)
class Observation:
    entity_type: str
    external_key: str
    source: str
    backend: str
    payload_json: str
    source_version: str | None = None
    lookback_hours: int | None = None
    resolution_minutes: int | None = None
    measured_at: str | None = None

    def __post_init__(self) -> None:
        if (self.source not in {"inventory", "iac", "policy", "telemetry"}
                or self.backend not in {"live", "fixture"}
                or not isinstance(self.external_key, str) or not self.external_key.strip()
                or not isinstance(self.entity_type, str) or not self.entity_type.strip()):
            raise WorldError("provenance")
        from app.world_model.identity import canonical_json
        try:
            decoded = json.loads(self.payload_json)
        except (ValueError, TypeError, RecursionError):
            raise WorldError("schema") from None
        if not isinstance(decoded, dict):
            raise WorldError("schema")
        object.__setattr__(self, "payload_json", canonical_json(decoded))
        for value in (self.lookback_hours, self.resolution_minutes):
            if value is not None and (type(value) is not int or value <= 0):
                raise WorldError("schema")
        if self.source_version is not None and not isinstance(self.source_version, str):
            raise WorldError("schema")

    @classmethod
    def from_payload(cls, *, payload: dict, **fields) -> Observation:
        from app.world_model.identity import canonical_json
        return cls(payload_json=canonical_json(payload), **fields)

    @property
    def payload(self) -> dict:
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class SnapshotRef:
    snapshot_id: str
    source: str
    observation_ids: tuple[str, ...]
    complete: bool
    degraded: bool
