from pathlib import Path
from app.config import RunConfig
from app.sources import get_source
from app.sources.base import Scope


def fetch_fixture(source, scenario="example_1", lookback_hours=168):
    cfg = RunConfig(sample_mode=True)
    scope = Scope(compartment_ids=[], resource_types=cfg.resource_types,
                  lookback_hours=lookback_hours, resolution_minutes=5)
    return get_source(source, cfg, scenario_dir=Path("data/scenarios") / scenario).fetch(scope)
