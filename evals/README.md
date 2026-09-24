# Evaluations

The organisers award bonus points for **shipping evaluations**. This directory holds them.

The intent: prove the agent actually works, with numbers, rather than asserting it in the
demo video. Judging weights Technical (20) and Impact (30); evidence serves both.

## Suggested shape

```
evals/
├── cases/          # input/expected-output pairs, versioned
├── run.py          # (or run.sh / run.ts) runs the suite, writes results
└── results/        # dated run output, committed
```

## What to measure

Pick what matters for the chosen track, then hold it steady so runs are comparable:

- **Task success rate** — did the agent achieve the goal, pass/fail per case
- **Reasoning steps** — and where it retried, branched or escalated
- **Failure handling** — does it fail loudly and recover, or silently produce nonsense
- **Cost and latency** — tokens and seconds per task; the NVIDIA token layer is
  relevant here
- **Consistency** — same input, repeated runs, same outcome

## Entries

_(none yet — pre-build)_
