# app/sources/inventory_fixture.py
from __future__ import annotations
import json
from pathlib import Path
from app.sources.base import Scope, SourceResult
from scripts.mask_ocids import mask_text


def _mask_set(ids: list[str]) -> set[str]:
    # Masked fixtures meet unmasked requests on masked ground: mask_text is idempotent, so
    # this is a no-op for fixture runs and rescues a degraded live run whose scope carries
    # real OCIDs (without it, the compartment filter would empty the fallback and a mid-demo
    # source failure would audit nothing).
    return {mask_text(i)[0] for i in ids}


class InventoryFixtureSource:
    name = "inventory"

    def __init__(self, scenario_dir: Path) -> None:
        self._path = scenario_dir / "inventory.json"

    def fetch(self, scope: Scope) -> SourceResult:
        payload = json.loads(self._path.read_text())
        records = payload["resources"]
        if scope.resource_types:
            records = [r for r in records if r["resource_class"] in scope.resource_types]
        if scope.compartment_ids:
            wanted = _mask_set(scope.compartment_ids)
            records = [r for r in records if r["compartment_id"] in wanted]
        return SourceResult(source=self.name, backend="fixture", records=records)
