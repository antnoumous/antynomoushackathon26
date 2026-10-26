from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.world_model.contracts import Observation


def _normalise(value: object) -> object:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            from app.world_model.contracts import WorldError
            raise WorldError("schema")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            from app.world_model.contracts import WorldError
            raise WorldError("schema")
        return {key: _normalise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    return value


def canonical_json(value: object) -> str:
    from app.world_model.contracts import WorldError
    try:
        return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise WorldError("schema") from None


def entity_id(namespace: str, observation: Observation) -> str:
    value = {"schema": 1, "namespace": namespace,
             "entity_type": observation.entity_type, "external_key": observation.external_key}
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def observation_id(namespace: str, observation: Observation) -> str:
    value = {"schema": 1, "namespace": namespace, **asdict(observation)}
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
