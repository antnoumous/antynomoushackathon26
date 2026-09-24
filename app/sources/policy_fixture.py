# app/sources/policy_fixture.py
from __future__ import annotations

import json
from pathlib import Path

from app.sources.base import Scope, SourceResult


class PolicyFixtureSource:
    name = "policy"

    def __init__(self, scenario_dir: Path) -> None:
        self._path = scenario_dir / "policy.json"

    def fetch(self, scope: Scope) -> SourceResult:
        payload = json.loads(self._path.read_text())
        return SourceResult(source=self.name, backend="fixture", records=payload["rules"])
