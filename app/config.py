from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

HARD_LIMITS = {
    "max_rounds": 3,
    "max_resources": 25,
    "max_rechecks_per_finding": 2,
    "wall_clock_soft_s": 300,
    "wall_clock_hard_s": 540,
}

DEFAULT_RESOURCE_TYPES = ["compute_instance", "block_volume", "reserved_public_ip"]


def _new_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class RunConfig(BaseModel):
    run_id: str = Field(default_factory=_new_run_id)
    objective: str = "audit this tenancy for cost waste and unattributed resources"
    compartment_ids: list[str] = Field(default_factory=list)
    resource_types: list[str] = Field(default_factory=lambda: list(DEFAULT_RESOURCE_TYPES))
    lookback_hours: int = 168
    resolution_minutes: int = 5
    max_rounds: int = HARD_LIMITS["max_rounds"]
    max_resources: int = HARD_LIMITS["max_resources"]
    max_rechecks_per_finding: int = HARD_LIMITS["max_rechecks_per_finding"]
    wall_clock_soft_s: int = HARD_LIMITS["wall_clock_soft_s"]
    wall_clock_hard_s: int = HARD_LIMITS["wall_clock_hard_s"]
    sample_mode: bool = False
    policy_source: Literal["file", "zetaris"] = "file"
    model: str | None = None
    logs_dir: Path = Path("logs")

    @classmethod
    def from_env_and_request(cls, request: dict) -> "RunConfig":
        req = dict(request or {})
        scope = dict(req.get("scope") or {})
        tele = dict(req.get("telemetry") or {})
        caps = dict(req.get("caps") or {})

        for key, value in caps.items():
            if key not in HARD_LIMITS:
                raise ValueError(f"unknown cap {key!r}")
            if int(value) > HARD_LIMITS[key]:
                raise ValueError(f"cap {key} may be lowered but not raised (hard limit {HARD_LIMITS[key]})")

        sample_env = os.environ.get("SAMPLE_MODE", "").strip().lower() in {"1", "true", "yes"}
        sample = sample_env or bool(req.get("sample_mode"))
        # Sample mode forces the fixture path before any remote selection is looked at —
        # even malformed sponsor variables cannot pull a sample run onto a network path.
        if sample:
            policy_source = "file"
        else:
            selected = os.environ.get("DRIFTWATCH_POLICY_SOURCE", "file").strip().lower()
            if selected == "zetaris":
                policy_source = "zetaris"
            elif selected in ("", "file"):
                policy_source = "file"
            else:
                raise ValueError("DRIFTWATCH_POLICY_SOURCE must be 'file' or 'zetaris'")
        cfg = cls(
            objective=req.get("objective") or cls.model_fields["objective"].default,
            compartment_ids=list(scope.get("compartment_ids") or []),
            resource_types=list(scope.get("resource_types") or list(DEFAULT_RESOURCE_TYPES)),
            lookback_hours=int(tele.get("lookback_hours", 168)),
            resolution_minutes=int(tele.get("resolution_minutes", 5)),
            sample_mode=sample,
            policy_source=policy_source,
            model=os.environ.get("LLM_MODEL"),
            logs_dir=Path(os.environ.get("LOGS_DIR", "logs")),
        )
        merged = cfg.model_dump() | {"caps": {}}
        for key in HARD_LIMITS:
            merged[key] = min(int(caps.get(key, HARD_LIMITS[key])), HARD_LIMITS[key])
        cfg = cls(**{**merged, "run_id": _new_run_id()})
        if not re.fullmatch(r"[A-Za-z0-9_-]+", cfg.run_id):
            raise ValueError("run_id must be filename safe")
        return cfg
