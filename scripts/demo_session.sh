# scripts/demo_session.sh
# The 3-minute Driftwatch demo, as a script: every line is a real invocation.
# Requires nothing but the repo + its venv. The live-Zetaris scene is skipped
# automatically unless the operator SSH tunnel (127.0.0.1:8888) is up — the rest
# runs credential-free.
#   RECORD:  asciinema rec --idle-time-limit 2 -c "bash scripts/demo_session.sh" demo.cast
#   RENDER:  agg demo.cast driftwatch-demo.gif
set -u
PY=.venv/bin/python
D="docs/superpowers"  # unused guard var to keep shellcheck quiet
S(){ sleep "${1:-1}"; }
CLS(){ printf '\033[2J\033[H'; }
BAR(){ echo "── $1 ──────────────────────────────────────────────"; }

CLS; echo
echo "   D R I F T W A T C H"
echo "   an agent that audits an OCI tenancy and shows its work"
S 2
BAR "in-window commits"
git log --oneline -4
S 4

CLS; BAR "sample mode: no keys, no network — the whole agent still runs"
S 1
SAMPLE_MODE=true $PY run.py --input input_examples/example_1.json \
  --out /tmp/demo-report.json 2>/dev/null | sed -n '/--- report ---/,$p'
S 7

CLS; BAR "every finding traces to an agent, an evidence id, a critique"
$PY scripts/demo_show_trace.py 12
S 6

CLS; BAR "LIVE Zetaris: republish the policy without rule R-1 — what changes?"
if nc -z 127.0.0.1 8888 2>/dev/null; then
  echo "\$ python scripts/verify_zetaris_policy.py --scenario example_1 \\"
  echo "      --base-settings <v2 snapshot> --variant-settings <v2 minus R-1>"
  S 2
  OUT=/tmp/demo-acc-$(date +%s)
  $PY scripts/verify_zetaris_policy.py \
    --scenario data/scenarios/example_1 \
    --base-settings ~/.oci/zetaris-deployment/acceptance-2026-10-22/base.json \
    --variant-settings ~/.oci/zetaris-deployment/acceptance-2026-10-22/variant.json \
    --output-dir "$OUT"
  S 3
  echo "── rule-hit lineage inside the accepted run:"
  F=$(ls "$OUT"/base/trace-*.jsonl | head -1)
  $PY scripts/demo_show_trace.py --prov "$F"
  S 4
else
  echo "(SSH tunnel down — skipping the live sponsor scene; see docs/zetaris-policy-operations.md)"
  S 3
fi

CLS; BAR "measured, not promised"
$PY -m evals.run_eval 2>/dev/null | tail -4
S 3
$PY -m pytest -q 2>&1 | tail -1
S 4

CLS; BAR "where everything lives"
echo "input_examples/ + output_examples/   curated + held-out artifacts (generated)"
echo "logs/samples/                        committed trace samples"
echo "docs/zetaris-policy-operations.md    sponsor runbook + execution record"
echo "notes/                               sponsor findings incl. engine defect"
S 4
echo
echo "   every claim traces to evidence — every failure degrades honestly"
S 4
