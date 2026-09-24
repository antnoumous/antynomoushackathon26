# app/sources/iac_fixture.py
from __future__ import annotations

import json
from pathlib import Path

from app.sources.base import Scope, SourceResult


class IaCFixtureSource:
    name = "iac"

    def __init__(self, scenario_dir: Path) -> None:
        self._path = scenario_dir / "iac.json"

    def fetch(self, scope: Scope) -> SourceResult:
        payload = json.loads(self._path.read_text())
        return SourceResult(source=self.name, backend="fixture",
                            records=payload["declarations"])
