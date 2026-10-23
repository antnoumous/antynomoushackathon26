# Demo storyboard — Driftwatch (1–4 min, Rules §6)

Base capture: `scripts/demo_session.sh` recorded with asciinema (66s at idle-limit 2),
rendered by `agg` → `docs/demo/driftwatch-demo.mp4`. To re-record verbatim:

```bash
asciinema rec --idle-time-limit 2 -c "bash scripts/demo_session.sh" demo.cast
agg demo.cast driftwatch-demo.gif && ffmpeg -i driftwatch-demo.gif -pix_fmt yuv420p demo.mp4
```

Voice target ~90–110s total → final video lands ≈ 2 min 0 s–2 min 30 s with pauses.

| # | Scene (screen) | ~time | Voiceover |
|---|---|---|---|
| 1 | Title + 4 in-window commits | 0:08 | "Driftwatch audits an OCI tenancy for cost waste and shadow infrastructure. It's a four-agent loop — Planner, Scout, Skeptic, Writer — and everything you're about to see is generated live, including the git history: that's the build window talking." |
| 2 | Sample-mode run → report | 0:14 | "First, sample mode: no credentials, no network — yet the whole agent runs, produces findings, critiques them, and writes a trace. Judges can reproduce this exact run from a fresh clone." |
| 3 | Trace viewer | 0:12 | "The trace *is* the product. Every line: which agent acted, on what input, with what status. Findings cite evidence ids; the Skeptic's rejections are as visible as the accepted findings." |
| 4 | Live Zetaris dual-run | 0:18 | "Now the sponsor integration, against the real Zetaris engine. We publish a policy snapshot as immutable tables, then republish one *without* rule R-1. Result: exactly one finding disappears — the detached volume that R-1 flagged — and nothing else moves. Rule-hit lineage inside the trace names provider zetaris and the snapshot digest. Cause and effect, on a live data gateway." |
| 5 | Evals + pytest | 0:12 | "And it's measured: three curated scenarios at precision one, recall one, deterministic — plus two hundred fifty-nine tests and a held-out scenario generator that scores ten generated tenancies. When we found the engine silently truncating quoted CSV cells, our own digest guard caught it — that failure story is in the repo, written up as a supplier defect note." |
| 6 | Where-everything-lives + close | 0:10 | "Artifacts, runbook, decisions, insights — all in the repo. Driftwatch: every claim traces to evidence, and every failure degrades honestly. That's the end of the tour." |

## Recording notes

- Speak over scenes 1→6 in one take, or record per-scene and stitch; the GIF keeps its own
  pace — leave 1–2s of silence at each Clear boundary (they're already padded by `Sleep`).
- If the live scene is skipped (no tunnel), say so *or* re-record with the tunnel up:
  `ssh -F ~/.oci/zetaris-deployment/ssh_config -N zetaris-01` — the video must never fake it.
- No secrets on screen: every command in this script prints synthetic ids and digests only.
  Verified: the captured video contains no key material (checked post-render).
