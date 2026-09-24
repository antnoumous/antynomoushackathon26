from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import run_pipeline

ACCEPTED = {"accepted", "revised"}


def _finding_keys(report) -> set[tuple[str, str]]:
    return {(f.resource_id, f.finding_class) for f in report.findings if f.status in ACCEPTED}


def _ratio(numerator: int, denominator: int) -> float | None:
    """Undefined rather than 1.0 when there is nothing to divide by.

    A scenario with no expected findings has no recall to report; printing 1.0 would read as a
    measured perfect score. `None` means "not measurable here", and the scorer says so.
    """
    return round(numerator / denominator, 3) if denominator else None


def evaluate(scenario_dir: Path) -> dict:
    truth = json.loads((scenario_dir / "ground_truth.json").read_text())
    expected = {(f["resource_id"], f["class"]) for f in truth["findings"]}
    verdicts = {(f["resource_id"], f["class"]): f["expected_verdict"] for f in truth["findings"]}

    first, _ = run_pipeline({"sample_mode": True}, scenario_dir=scenario_dir)
    second, _ = run_pipeline({"sample_mode": True}, scenario_dir=scenario_dir)

    got = _finding_keys(first)
    hits = expected & got
    precision = _ratio(len(hits), len(got))
    recall = _ratio(len(hits), len(expected))

    correct_verdicts = 0
    for finding in first.findings:
        key = (finding.resource_id, finding.finding_class)
        if key in verdicts and finding.status == verdicts[key]:
            correct_verdicts += 1
    verdict_accuracy = _ratio(correct_verdicts, len(verdicts))

    flagged = {f.resource_id for f in first.findings if f.status in ACCEPTED}
    must_not_flag = list(truth.get("must_not_flag", []))
    violations = sorted(set(must_not_flag) & flagged)

    first_keys = sorted((f.resource_id, f.finding_class, f.status) for f in first.findings)
    second_keys = sorted((f.resource_id, f.finding_class, f.status) for f in second.findings)

    return {
        "scenario": scenario_dir.name,
        "findings_count": len(first.findings),
        "precision": precision,
        "recall": recall,
        "verdict_accuracy": verdict_accuracy,
        "must_not_flag_checked": len(must_not_flag),
        "must_not_flag_violations": violations,
        "deterministic": first_keys == second_keys,
        "status": first.status,
    }


def _cell(value: float | None, width: int = 6) -> str:
    return "n/a".ljust(width) if value is None else f"{value:<{width}}"


def main() -> int:
    scenarios = sorted(Path("data/scenarios").glob("example_*"))
    failures = 0
    for scenario in scenarios:
        result = evaluate(scenario)
        print(f"{result['scenario']:<12} precision {_cell(result['precision'])}"
              f"recall {_cell(result['recall'])} verdicts {_cell(result['verdict_accuracy'])}"
              f"findings {result['findings_count']:<3} status {result['status']:<8} "
              f"deterministic {result['deterministic']}")
        if result["must_not_flag_checked"]:
            print(f"  must-not-flag: {result['must_not_flag_checked']} resource(s) must stay "
                  f"unreported — {len(result['must_not_flag_violations'])} violation(s)")
        if result["must_not_flag_violations"]:
            print(f"  must-not-flag violations: {result['must_not_flag_violations']}")
        if any(metric is not None and metric < 1.0 for metric in
               (result["precision"], result["recall"], result["verdict_accuracy"])) \
                or result["must_not_flag_violations"] or not result["deterministic"]:
            failures += 1
    print(f"\n{len(scenarios)} scenarios, {failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
