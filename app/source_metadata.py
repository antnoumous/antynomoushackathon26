"""Typed source provenance, kept free of source-package imports to avoid cycles."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SourceProvenance(BaseModel):
    provider: Literal["zetaris"]
    object_name: str
    manifest_object: str
    snapshot_id: str
    schema_version: int
    requested_scope_hash: str
    content_sha256: str
    row_count: int
    expected_count: int
    complete: bool
    observed_at_utc: str
    fetched_at_utc: str
    query_sha256: str
