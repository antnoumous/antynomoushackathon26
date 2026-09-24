# run.py
"""Driftwatch entry point.

With no arguments this audits the bundled sample scenario on cached data, with no credentials
and no network. Point it at real infrastructure by setting SAMPLE_MODE=false plus the OCI_*
variables, and at your own fixtures with --scenario.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.pipeline import run_pipeline

DEFAULT_SCENARIO = Path("data/scenarios/example_1")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an OCI tenancy for waste and drift.")
    parser.add_argument("--input", type=Path, default=None,
                        help="JSON request file, e.g. input_examples/example_1.json")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO,
                        help="fixture scenario directory (default: %(default)s)")
    parser.add_argument("--out", type=Path, default=None, help="write the JSON report here")
    parser.add_argument("--serve", action="store_true", help="run the HTTP API instead")
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        uvicorn.run("app.api:app", host="0.0.0.0", port=8000)
        return 0

    request = json.loads(args.input.read_text()) if args.input else {}
    # Demo-friendly default, so a bare `python run.py` works with no credentials. An explicit
    # SAMPLE_MODE or sample_mode always wins over this.
    if "sample_mode" not in request and not os.environ.get("SAMPLE_MODE"):
        request["sample_mode"] = True

    report, markdown = run_pipeline(request, scenario_dir=args.scenario)
    payload = json.dumps(report.model_dump(by_alias=True), indent=2)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    print(f"\n--- report ---\n{markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
