from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import run_pipeline

ACCEPTED = {"accepted", "revised"}


def _finding_keys(report) -> set[tuple[str, str]]:
    return {(f.resource_id, f.finding_class) for f in report.findings if f.status in ACCEPTED}


def evaluate(scenario_dir: Path) -> dict:
    truth = json.loads((scenario_dir / "ground_truth.json").read_text())
    expected = {(f["resource_id"], f["class"]) for f in truth["findings"]}
    verdicts = {(f["resource_id"], f["class"]): f["expected_verdict"] for f in truth["findings"]}

    first, _ = run_pipeline({"sample_mode": True}, scenario_dir=scenario_dir)
    second, _ = run_pipeline({"sample_mode": True}, scenario_dir=scenario_dir)

    got = _finding_keys(first)
    hits = expected & got
    precision = len(hits) / len(got) if got else 1.0
    recall = len(hits) / len(expected) if expected else 1.0

    correct_verdicts = 0
    for finding in first.findings:
        key = (finding.resource_id, finding.finding_class)
        if key in verdicts and finding.status == verdicts[key]:
            correct_verdicts += 1
    verdict_accuracy = correct_verdicts / len(verdicts) if verdicts else 1.0

    flagged = {f.resource_id for f in first.findings if f.status in ACCEPTED}
    violations = sorted(set(truth.get("must_not_flag", [])) & flagged)

    first_keys = sorted((f.resource_id, f.finding_class, f.status) for f in first.findings)
    second_keys = sorted((f.resource_id, f.finding_class, f.status) for f in second.findings)

    return {
        "scenario": scenario_dir.name,
        "findings_count": len(first.findings),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "verdict_accuracy": round(verdict_accuracy, 3),
        "must_not_flag_violations": violations,
        "deterministic": first_keys == second_keys,
        "status": first.status,
    }


def main() -> int:
    scenarios = sorted(Path("data/scenarios").glob("example_*"))
    failures = 0
    for scenario in scenarios:
        result = evaluate(scenario)
        print(f"{result['scenario']:<12} precision {result['precision']:<6} "
              f"recall {result['recall']:<6} verdicts {result['verdict_accuracy']:<6} "
              f"findings {result['findings_count']:<3} status {result['status']:<8} "
              f"deterministic {result['deterministic']}")
        if result["must_not_flag_violations"]:
            print(f"  must-not-flag violations: {result['must_not_flag_violations']}")
        if (result["precision"] < 1.0 or result["recall"] < 1.0
                or result["must_not_flag_violations"] or not result["deterministic"]):
            failures += 1
    print(f"\n{len(scenarios)} scenarios, {failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
