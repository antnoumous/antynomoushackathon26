# app/sources/inventory_fixture.py
from __future__ import annotations
import json
from pathlib import Path
from app.sources.base import Scope, SourceResult


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
            records = [r for r in records if r["compartment_id"] in scope.compartment_ids]
        return SourceResult(source=self.name, backend="fixture", records=records)
