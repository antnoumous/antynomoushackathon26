from __future__ import annotations

import sys
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
    state = RunState(config.run_id, config.logs_dir)
    trace = Tracer(config.run_id, config.logs_dir)
    ctx = None
    try:
        ctx = AgentContext(config=config, sources=sources, generator=get_generator(config),
                           state=state, trace=trace, ledger=EvidenceLedger(), scope=scope,
                           scenario_dir=scenario_dir)
        report = Orchestrator(ctx, scenario_dir=scenario_dir).run()
    finally:
        # Both writers hold an open handle for the whole run; closing them here keeps a long-lived
        # process (the API, a batch of scenarios) from leaking a descriptor per run.
        if ctx is not None and ctx.world is not None:
            ctx.world.close()
        trace.close()
        state.close()

    if not config.sample_mode:
        _warn_if_no_live_backend(report)

    markdown = render_markdown(report)
    report_path = config.logs_dir / f"report-{config.run_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    report.report_markdown_path = str(report_path)
    return report, markdown


def _warn_if_no_live_backend(report: RunReport) -> None:
    """A run that asked for live data and got fixtures says so out loud, not only in the JSON.

    Nothing here changes what the report contains; it makes the one fact a human watching stdout
    could otherwise miss impossible to miss.
    """
    backends = sorted({source.backend for source in report.sources})
    if "live" in backends:
        return
    unavailable = [source.name for source in report.sources if source.degraded]
    print(f"WARNING: SAMPLE_MODE is false but no live backend answered. Every result below came "
          f"from bundled fixtures, so this is not an audit of your tenancy. Sources degraded: "
          f"{', '.join(unavailable) or 'none'}. See the README for the live-adapter status.",
          file=sys.stderr)
