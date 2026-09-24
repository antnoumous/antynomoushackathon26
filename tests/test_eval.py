# tests/test_eval.py
from pathlib import Path
from evals.run_eval import evaluate


def test_example_1_scores_full_precision_and_recall():
    result = evaluate(Path("data/scenarios/example_1"))
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["deterministic"] is True


def test_example_2_produces_no_findings_at_all():
    result = evaluate(Path("data/scenarios/example_2"))
    assert result["findings_count"] == 0
    # Nothing to divide by, so the metrics are undefined rather than a perfect score: this
    # scenario's real check is must_not_flag, which is not vacuous.
    assert result["precision"] is None
    assert result["recall"] is None
    assert result["must_not_flag_checked"] == 5
    assert result["must_not_flag_violations"] == []


def test_example_3_respects_must_not_flag():
    result = evaluate(Path("data/scenarios/example_3"))
    assert result["must_not_flag_violations"] == []
    assert result["recall"] == 1.0
    assert result["verdict_accuracy"] == 1.0
