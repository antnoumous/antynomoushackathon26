# scripts/make_scenario.py
"""Held-out scenario generator (plan Task 16).

The strongest available answer to "are these outputs hardcoded" is to score the agent on inputs that
did not exist when it was written. This builds a complete, never-seen tenancy *and its ground truth*
from one integer seed, so the evaluator can score it the same way it scores the committed scenarios.

**The window arithmetic is the load-bearing part.** The canonical behaviour this has to reproduce is
the re-check: an instance looks idle over the window the run was asked for, a schedule signal in its
evidence makes the Skeptic doubt that window, the Planner widens it to `RECHECK_WINDOW_HOURS`, and
the low mean with a real peak turns an "idle" verdict into a "mis-sized" one. For that to happen the
burst has to be *inside the widened window and outside the first one* — visible in the second look
and invisible in the first. A burst placed anywhere else produces a plain idle instance, and the
ground truth's `revised` would be wrong. So the burst date is derived from the scenario's `now`:

    FIRST_WINDOW_HOURS = 168  (7 days)   the lookback the run is asked for
    RECHECK_WINDOW_HOURS = 744 (31 days) what the Skeptic widens to
    BURST_DAYS_AGO = 20                  inside 31 days, outside 7 days

Run it:

    python scripts/make_scenario.py --seed 7 --out /tmp/held_out_7
    python scripts/make_scenario.py --score 8            # generate and score eight unseen tenancies
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "data/scenarios/example_1/policy.json"

MASK = "\u2022\u2022\u2022\u2022"
NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)
SHAPES = [("VM.Standard.A1.Flex", 1, 6), ("VM.Standard.E4.Flex", 2, 8),
          ("VM.Standard.E4.Flex", 4, 16)]
FIRST_WINDOW_HOURS = 168
RECHECK_WINDOW_HOURS = 744
SERIES_START_DAYS = 45           # older than both windows: coverage is never why a run abstains
BURST_DAYS_AGO = 20              # inside the re-check window, outside the first
CREATED_DAYS_AGO = 60
IDLE_BASELINE, IDLE_JITTER = 0.6, 0.4
BUSY_SPEED, BURST_VALUE = (35.0, 65.0), 58.0


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _rules() -> list[dict]:
    return json.loads(POLICY_PATH.read_text())["rules"]


def build_scenario(seed: int, out_dir: Path) -> Path:
    """Writes a complete, never-seen scenario with its own ground truth."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    series_start = NOW - timedelta(days=SERIES_START_DAYS)
    burst_start = (NOW - timedelta(days=BURST_DAYS_AGO)).replace(hour=2, minute=0, second=0,
                                                                microsecond=0)

    instances, volumes, addresses, series, declarations = [], [], [], [], []
    truth, must_not_flag = [], []

    for index in range(rng.randint(3, 6)):
        suffix = f"{seed:02d}{index:02d}"
        rid = f"ocid1.instance.oc1..{MASK}{suffix}"
        shape, ocpus, memory = rng.choice(SHAPES)
        declared = rng.random() < 0.6
        idle = rng.random() < 0.5
        bursty = rng.random() < 0.4
        name = f"{'worker' if idle else 'app'}-{suffix}"
        tags = {"env": "prod", "owner": "generated"}
        if declared:
            tags["iac_address"] = f"oci_core_instance.{name.replace('-', '_')}"
        if bursty:
            tags["schedule"] = "month-end"

        instances.append({
            "resource_id": rid, "resource_class": "compute_instance", "display_name": name,
            "compartment_id": f"ocid1.compartment.oc1..{MASK}lab",
            "lifecycle_state": "RUNNING", "time_created": _iso(NOW - timedelta(days=CREATED_DAYS_AGO)),
            "shape": shape, "ocpus": ocpus, "memory_gb": memory, "tags": tags})
        series.append({
            "resource_id": rid, "metric": "CpuUtilization", "start": _iso(series_start),
            "baseline": IDLE_BASELINE if idle else rng.uniform(*BUSY_SPEED),
            "jitter": IDLE_JITTER if idle else 6.0,
            "bursts": ([{"start": _iso(burst_start), "hours": 3, "value": BURST_VALUE}]
                       if bursty else [])})
        if declared:
            declarations.append({
                "address": tags["iac_address"], "resource_type": "oci_core_instance",
                "declared_name": name, "file_path": f"terraform/{name}.tf",
                "last_commit": f"{rng.getrandbits(28):07x}",
                "commit_message": ("month-end batch worker, runs on the 1st at 02:00" if bursty
                                   else "provisioned by IaC"),
                "author": "generated@example.invalid"})

        # Ground truth is derived from the same choices that shaped the resource, never guessed:
        # idle is measured, the burst decides revised-vs-accepted, and R-5 depends on the declaration.
        if idle:
            truth.append({"resource_id": rid, "class": "cost_waste",
                          "expected_verdict": "revised" if bursty else "accepted"})
        if not declared:
            truth.append({"resource_id": rid, "class": "unattributed",
                          "expected_verdict": "accepted"})
        if not idle and declared:
            must_not_flag.append(rid)          # busy and declared: the case that must stay quiet

    for kind, collection in (("volume", volumes), ("publicip", addresses)):
        for index in range(rng.randint(1, 2)):
            suffix = f"{seed:02d}{index:02d}{kind[0]}"
            rid = f"ocid1.{kind}.oc1..{MASK}{suffix}"
            attached = rng.random() < 0.5
            record = {
                "resource_id": rid, "resource_class": ("block_volume" if kind == "volume"
                                                       else "reserved_public_ip"),
                "display_name": f"{kind}-{suffix}",
                "compartment_id": f"ocid1.compartment.oc1..{MASK}lab",
                "lifecycle_state": "AVAILABLE",
                "time_created": _iso(NOW - timedelta(days=CREATED_DAYS_AGO)),
                "tags": {}, "attached": attached}
            if kind == "volume":
                record["size_gb"] = rng.choice([50, 100, 200])
            collection.append(record)
            if attached:
                must_not_flag.append(rid)      # attached: billed for a reason, must stay quiet
            else:
                truth.append({"resource_id": rid, "class": "cost_waste",
                              "expected_verdict": "accepted"})

    payloads = {
        # The seed alone determines the content, including the id: the same seed written to two
        # different directories produces byte-identical files, which is what makes held-out
        # evidence diffable.
        "inventory.json": {"scenario_id": f"held_out_{seed}",
                           "resources": instances + volumes + addresses},
        "telemetry.json": {"scenario_id": f"held_out_{seed}", "now": _iso(NOW), "series": series},
        "iac.json": {"scenario_id": f"held_out_{seed}", "declarations": declarations},
        "policy.json": {"scenario_id": f"held_out_{seed}", "rules": _rules()},
        "ground_truth.json": {"findings": truth, "must_not_flag": must_not_flag},
    }
    for name, payload in payloads.items():
        (out_dir / name).write_text(json.dumps(payload, indent=2) + "\n")
    return out_dir


def score(seeds: int, base_dir: Path) -> int:
    """Generate `seeds` unseen tenancies and score each with the committed evaluator.

    Each run's stdout trace goes to a per-seed log beside the scenarios, so the table below is the
    only thing printed: a scorer whose output is buried in six runs of trace lines is a scorer
    nobody reads.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from evals.run_eval import evaluate

    logs = base_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("LOGS_DIR", str(logs))

    failures = 0
    for seed in range(1, seeds + 1):
        scenario = build_scenario(seed, base_dir / f"held_out_{seed}")
        with (logs / f"held_out_{seed}.log").open("w") as sink, \
                contextlib.redirect_stdout(sink):
            result = evaluate(scenario)
        verdicts = "n/a" if result["verdict_accuracy"] is None else result["verdict_accuracy"]
        print(f"held_out_{seed:<4} precision {result['precision']}  recall {result['recall']}  "
              f"verdicts {verdicts}  findings {result['findings_count']:<3} "
              f"status {result['status']:<8} deterministic {result['deterministic']}")
        if (result["precision"], result["recall"], result["verdict_accuracy"]) != (1.0, 1.0, 1.0) \
                or result["must_not_flag_violations"] or not result["deterministic"]:
            failures += 1
            print(f"  violations: {result['must_not_flag_violations']}")
    print(f"\n{seeds} held-out tenancies, {failures} failing")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a held-out OCI tenancy and its truth.")
    parser.add_argument("--seed", type=int, default=1, help="one integer fully determines the tenancy")
    parser.add_argument("--out", type=Path, default=None,
                        help="directory to write the scenario into (required unless --score)")
    parser.add_argument("--score", type=int, default=0, metavar="N",
                        help="generate N unseen tenancies into --out (or a temp dir) and score them")
    args = parser.parse_args()

    if args.score:
        base = args.out or Path(f"/tmp/driftwatch-held-out")
        return score(args.score, base)
    if args.out is None:
        parser.error("--out is required (or use --score N)")
    print(build_scenario(args.seed, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
