# tests/test_make_scenario.py
"""Task 16: the strongest available answer to "are these outputs hardcoded" is to score the agent
on inputs that did not exist when it was written."""
import json
from pathlib import Path

from evals.run_eval import evaluate
from scripts.make_scenario import build_scenario

SEEDS = (6, 11, 29)
# Seed 6 is pinned because of the shape it carries and no committed scenario does: an idle, bursty,
# *undeclared* instance, where the re-check re-derives a second (untouched) finding for the same
# resource. It scored 0.8 verdict accuracy before the loop learned to tell a duplicate from a
# revision (see tests/test_loop.py), which is the clearest demonstration of what this task is for.
COMMITTED = sorted(Path("data/scenarios").glob("example_*"))


def _resource_ids(scenario_dir: Path) -> set[str]:
    inventory = json.loads((scenario_dir / "inventory.json").read_text())
    return {resource["resource_id"] for resource in inventory["resources"]}


def test_generated_scenarios_score_well_and_are_not_the_committed_ones(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    for seed in SEEDS:
        out = build_scenario(seed, tmp_path / f"held_out_{seed}")
        result = evaluate(out)

        assert result["precision"] == 1.0, f"seed {seed}: {result}"
        assert result["recall"] == 1.0, f"seed {seed}: {result}"
        assert result["verdict_accuracy"] == 1.0, f"seed {seed}: {result}"
        assert result["must_not_flag_violations"] == []
        assert result["deterministic"] is True
        assert result["status"] == "success"
        # "Held-out" is the whole point: no generated tenancy may be a committed one wearing a hat.
        generated = _resource_ids(out)
        assert generated
        for committed in COMMITTED:
            assert not generated & _resource_ids(committed)


def test_two_seeds_produce_different_tenancies(tmp_path):
    a = json.loads((build_scenario(11, tmp_path / "a") / "inventory.json").read_text())
    b = json.loads((build_scenario(11, tmp_path / "b") / "inventory.json").read_text())
    c = json.loads((build_scenario(29, tmp_path / "c") / "inventory.json").read_text())
    assert a == b                      # same seed, same tenancy
    assert a != c                      # different seed, different tenancy


def test_a_generated_scenario_carries_its_own_ground_truth(tmp_path):
    """The scoring is only meaningful if the truth is generated with the scenario, not beside it."""
    out = build_scenario(29, tmp_path / "held_out_29")
    truth = json.loads((out / "ground_truth.json").read_text())
    ids = _resource_ids(out)

    assert truth["findings"], "a generated tenancy must have something to find"
    for finding in truth["findings"]:
        assert finding["resource_id"] in ids
        assert finding["class"] in {"cost_waste", "unattributed"}
        assert finding["expected_verdict"] in {"accepted", "revised", "rejected"}
    for resource_id in truth["must_not_flag"]:
        assert resource_id in ids
