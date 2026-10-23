# Driftwatch — hackathon demo recording script (vhs)
# Render:  ~/bin/vhs scripts/demo.driftwatch.tape --output docs/demo/driftwatch-demo.mp4
# Every command below is a real, reproducible invocation of this repo.

Set Theme "Dracula"
Set Width 1280
Set Height 720
Set FontSize 15
Set Padding 40
CD "."

# ── Scene 1 · what this is ───────────────────────────────────────────
Type "echo 'DRIFTWATCH — an OCI tenancy auditor that shows its work'"
Enter
Wait
Sleep 1.5
Type "git log --oneline -4"
Enter
Wait
Sleep 3
Clear

# ── Scene 2 · sample mode: full agent, zero credentials ──────────────
Type `echo '── sample mode: no keys, no network, the whole agent still runs ──'`
Enter
Wait
Sleep 1
Type `SAMPLE_MODE=true .venv/bin/python run.py --input input_examples/example_1.json --out /tmp/demo-report.json | sed -n '/--- report ---/,$p'`
Enter
Wait
Sleep 6
Clear

# ── Scene 3 · the trace is the product ───────────────────────────────
Type `echo '── every finding: which agent, which evidence, which critique ──'`
Enter
Wait
Sleep 1
Type ".venv/bin/python scripts/demo_show_trace.py 12"
Enter
Wait
Sleep 5
Clear

# ── Scene 4 · live sponsor integration: the causal experiment ────────
Type `echo '── LIVE Zetaris: republish the policy without rule R-1 — what breaks? ──'`
Enter
Wait
Sleep 1.5
Type ".venv/bin/python scripts/verify_zetaris_policy.py --scenario data/scenarios/example_1 --base-settings ~/.oci/zetaris-deployment/acceptance-2026-10-22/base.json --variant-settings ~/.oci/zetaris-deployment/acceptance-2026-10-22/variant.json --output-dir /tmp/demo-acc-$(date +%s)"
Enter
Wait
Sleep 7
Type `grep -m2 -o '"provider": "[a-z]*"' /tmp/demo-acc-*/base/trace-*.jsonl`
Enter
Wait
Sleep 2
Clear

# ── Scene 5 · measured, not promised ─────────────────────────────────
Type `echo '── three curated scenarios, scored, deterministic ──'`
Enter
Wait
Sleep 1
Type ".venv/bin/python -m evals.run_eval 2>/dev/null | tail -4"
Enter
Wait
Sleep 3
Type ".venv/bin/python -m pytest -q 2>&1 | tail -1"
Enter
Wait
Sleep 3
Clear

# ── Scene 6 · honesty close ──────────────────────────────────────────
Type `echo 'held-out artifacts: output_examples/  ·  runbook + defects: docs/ notes/'`
Enter
Wait
Sleep 2
Type `echo 'Driftwatch — every claim traces to evidence, every failure degrades honestly.'`
Enter
Wait
Sleep 4
