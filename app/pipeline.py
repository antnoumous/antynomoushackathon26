from __future__ import annotations

from pathlib import Path

from app.agents.base import AgentContext
from app.config import RunConfig
from app.evidence import EvidenceLedger
from app.generator import get_generator
from app.loop import Orchestrator
from app.models import RunReport
from app.report import render_markdown
from app.sources import get_source
from app.sources.base import Scope
from app.state import RunState
from app.trace import Tracer


def run_pipeline(request: dict, scenario_dir: Path | None = None) -> tuple[RunReport, str]:
    config = RunConfig.from_env_and_request(request)
    scope = Scope(compartment_ids=config.compartment_ids, resource_types=config.resource_types,
                  lookback_hours=config.lookback_hours, resolution_minutes=config.resolution_minutes)
    sources = {name: get_source(name, config, scenario_dir=scenario_dir)
               for name in ("inventory", "telemetry", "iac", "policy")}
    ctx = AgentContext(config=config, sources=sources, generator=get_generator(config),
                       state=RunState(config.run_id, config.logs_dir),
                       trace=Tracer(config.run_id, config.logs_dir),
                       ledger=EvidenceLedger(), scope=scope)
    report = Orchestrator(ctx, scenario_dir=scenario_dir).run()
    markdown = render_markdown(report)
    report_path = config.logs_dir / f"report-{config.run_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    report.report_markdown_path = str(report_path)
    return report, markdown
