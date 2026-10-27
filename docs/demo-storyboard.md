# Demo storyboard — Driftwatch (1–4 min, Rules §6)

Base capture: `scripts/demo_session.sh` recorded with asciinema (66s at idle-limit 2),
rendered by `agg` → `docs/demo/driftwatch-demo.mp4`. To re-record verbatim:

```bash
asciinema rec --idle-time-limit 2 -c "bash scripts/demo_session.sh" demo.cast
agg demo.cast driftwatch-demo.gif && ffmpeg -i driftwatch-demo.gif -pix_fmt yuv420p demo.mp4
```

Voice target ~90–110s total → final video lands ≈ 2 min 0 s–2 min 30 s with pauses.

## Current cut — 26 October 2026 (Meterless integration)

`docs/demo/driftwatch-demo-narrated.mp4`, **130.82 s** (2.18 min), with the standalone soundtrack in
`docs/demo/driftwatch-voiceover.mp3`. The silent capture `docs/demo/driftwatch-demo.mp4` is
unchanged (SHA-256 identical before and after assembly, asserted by the assembler).

Six scenes are the original recorded session; two closing **cards** were added because the
Meterless work has no footage of its own. The cards are rendered with ffmpeg `drawtext` from the
committed run's own `summary.integrations` block — they are captions of real output, not
constructed terminal transcripts — and the assembler refuses a card scene that does not record
where it came from in `manifest.json`.

| # | Scene | Kind | Output seconds | Narration chars |
|---|---|---|---|---|
| 1 | 01-introduction | source | 0.0–15.9 | 199 |
| 2 | 02-sample-audit | source | 15.9–35.5 | 249 |
| 3 | 03-agent-critique | source | 35.5–51.1 | 210 |
| 4 | 04-zetaris-acceptance | source | 51.1–73.4 | 293 |
| 5 | 05-recorded-evaluation | source | 73.4–85.3 | 151 |
| 6 | 06-reproduction-and-status | source | 85.3–96.0 | 114 |
| 7 | 07-world-model | card | 96.0–112.6 | 242 |
| 8 | 08-nightshift-status | card | 112.6–130.8 | 265 |

Rebuild: `python3.11 scripts/assemble_demo_voiceover.py --ffmpeg <path>`; it re-reads
`docs/demo/narration/manifest.json`, re-measures each MP3, refuses scene gaps, requires at least
0.89 s of silence after every spoken line, asserts the 1–4 minute rule, verifies H.264/AAC, fully
decodes the delivered bitstream and fails if the silent original's hash changed.

Verified on this build: full decode passed, `Duration` 130.82 s matches the planned timeline
130.80 s, -19.5 dB mean and -2.0 dB peak,
video `ea63b907bf310a44…`, audio `298dab2cf055b805…`. Representative frames at
6, 25, 60, 104, 121 and 130 s were inspected: scene order is correct, both cards are legible and
unclipped, and the final frame still holds content rather than going blank.

**What the narration now claims, and what backs it:** Zetaris executed live (unchanged); the
Meterless World Model is implemented and consumed by Scout and Skeptic (frame 2 shows the run's own
`status: used`, `consumers: Scout, Skeptic`); the Nightshift provider is implemented and
contract-tested but **has served no request** because the vendor's Mac installer fails Gatekeeper
(frame 3 shows `status: not_used`, `attempts 0`). The cut does not claim live Nightshift inference.
Editorial holds are extended for readability; nothing here measures execution time.

## Deck changes (same date)

`docs/demo/driftwatch-deck.pptx` is 11 slides, 16:9, rebuilt from scratch by
`scripts/build_deck.py` on an explicit grid (1 in side margins, 12.33 in content width).

The old deck was built on layout placeholders from python-pptx's 4:3 default template, so on a
16:9 canvas every slide's content occupied a 9 in column at 0.5 in and left the right third empty;
titles were centred with no fixed baseline, one line of the title slide overflowed the canvas, and
text sat at layout default sizes with no visual hierarchy. The rebuild places every element
explicitly: a kicker label, a left-aligned title, a short accent rule, a body block vertically
centred in its band, and a footer with the slide number. Two capability slides carry stat cards;
the causal-experiment slide carries a real table; the close carries a monospaced command block.

Claims were corrected at the same time: the test count is now **465** (it was 259 before the
integration work), the attribution slide no longer says Meterless was "unmounted", and the
Nightshift slide states `not_used` with zero attempts rather than implying a live integration.

**Verified visually, not just structurally.** LibreOffice *is* installed on this machine
(`/Applications/LibreOffice.app`), so each slide was rendered to PNG with the skill's
`pptx_render.py` and inspected. Three defects were found and fixed this way: a 34 pt two-line stat
value overflowed its card on the World Model slide; the attempts panel had a dead gap and text
floating mid-box; guard rows were centre-aligned against left-aligned body copy. A second pass also
removed theme drop shadows (a preset shape carries a `<p:style>` effect reference that survives an
emptied `effectLst`) and set the table's borders explicitly.


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
