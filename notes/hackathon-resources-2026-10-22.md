# HackOS resource hub — 22 October delta + live event-page rules

**What this is:** the incremental pass on the live Resource Hub the day the build window
opened, and the first capture of the **event-page rules through the public backend API**.
It deltas [`hackathon-resources-2026-10-21.md`](hackathon-resources-2026-10-21.md); that
digest remains the full-inventory reference. Read with
[`zetaris.md`](zetaris.md) (live-rule verification) and
[`zetaris-oci-deployed-2026-10-19.md`](zetaris-oci-deployed-2026-10-19.md) (approved scope).

Captured **22 October 2026, ~06:45–07:10 UTC (14:45–15:10 SGT)** from the signed-in
embedded preview pane, plus anonymous API reads. Raw captures stay outside the repo under
`~/projects/open-agent-hackathon-reference/resources-2026-10-22/`
(`hackathon_api_live_2026-10-22.json`, `official_rules_event_page_2026-10-22.txt`,
`delta_vs_2026-10-21.json`). Nothing on the user's hub dashboard was toggled —
the onboarding tracker still reads **0/7 reviewed, 0/2 required**.

## 1. Hub delta — 63 → 67 entries

| | 21 Oct | 22 Oct |
|---|---:|---:|
| Documents | 56 | 56 |
| Videos | 4 | **8** |
| Datasets | 3 | 3 |

**All four additions are videos, created 21 October** (UUIDv7 creation times decoded from
the resource IDs): Power Day 05:52 UTC, Build Day 08:46 UTC, "BUILD with Meterless and
Cursor, Session 2" 14:50 UTC, **Onboarding call 14:59 UTC** (the 21 Oct 12:00–13:30 UTC
session). Video cards open a **player-only modal** — no description or transcript text is
rendered in the hub DOM, so no body was archived. The Academy course data endpoint is
authenticated (its public `courses/` list is seed content), so **transcripts remain an
explicit gap**. The onboarding call matters: the Overview said additional challenges and
prizes would be announced there — **watch it before locking the track decision.**

Ids: Power Day `01a15d04-b8cf…`, Build Day `01a15da3-daaf…`, Session 2 `01a15ef1-a1ff…`,
Onboarding call `01a15ef9-ad49…` (full ids in `delta_vs_2026-10-21.json`).

**Restructurings (no content change to my knowledge):** Participant Setup Guide moved into
the onboarding grid and is now badged **REQUIRED** (content was digested in
[`participant-setup-guide-2026-10-17.md`](participant-setup-guide-2026-10-17.md)); the
onboarding FAQ is badged REQUIRED (archived 21 Oct as `01a08ff1-5780-…faq.txt` — verify
which of the two FAQ snapshots matches the required one before trusting that); Orientation
deck and PokéAPI cards renamed. **The two "new to us" items I flagged earlier today
(Submission Form Preview, Strong Submission Examples) were in fact already captured 21 Oct** —
full text archives exist; they were new only relative to the September digest.

## 2. New source class: the live event page via public API

`GET https://hackathon-server.genai.works/api/v1/hackathons/019fd164-82b9-7382-a536-d9093c576ed2/`
answers **without authentication** and carries the published structured event record
(`updated_at 2026-10-21T07:16:57Z`). The hub's own resource endpoints 401 anonymously, so
this is the authoritative public mirror of "the binding rules published on the event page".

Rules text (§§1–10, 4,164 B, archived above) **confirms the 14 October live-rule
verification unchanged**: build window 22 Oct 00:00 → 27 Oct 23:45 UTC (§4); Zetaris +
Meterless integration and Cursor development required, NVIDIA "wherever it contributes"
(§5); pre-existing product code allowed only when declared on the submission form (§4/§5);
demo 1–4 min + slide deck + public GitHub repo + sponsor explanation (§6); scoring
30/20/15/15/10/10, ≥3 judges, ties on Impact then timestamp (§7); track changeable until
the deadline; team composition locks at first submission (§2/§3).

### Structured fields that differ from hub documents

| Fact | Event-page field (this API) | Hub documents (21 Oct) | Bearing |
|---|---|---|---|
| Judging opens | `judging_starts_at` **2026-10-27T00:00Z** | "28 Oct, immediately after close" | AGENTS.md matches the field; docs disagree. No action needed from us (deadline unchanged) |
| Registration closes | `registration_end` **22 Oct 23:59Z** | 23:45 in eight documents | Already registered; moot. Use 23:45 as the safe reading if ever re-checking |
| Prize cash split | **$13,000 cash + $7,000 in-kind** | $15,000 + $5,000 | Record; no build impact |
| Per-track cash | 1,600/1,200/900 (Tracks 01–02), **1,500**/1,200/900 (03), 1,000/600/400 (Wildcard) | 2,000/1,350/1,000 table in Overview | Field vs doc conflict; neither changes what we build |
| **In-kind prize** | **"Best use of NVIDIA Nemotron" — NVIDIA DGX Spark Founder's Edition, $4,699** | **absent from every hub document read** | New. The approved scope already includes honest Nemotron usage/explanation; this prize raises its expected value but authorises no scope change |
| Sponsor label | "SpaceX AI" (x.ai) alongside NVIDIA/Zetaris/Meterless | "Space XAI (with Cursor)" | Use both forms carefully in README wording; Rules §5 wording is what counts |
| Other fields | `agent_rate_limit_per_hour: 20`, `auto_lock_new_submissions: false`, 40 featured judges/mentors, per-track prize tiers | — | Platform config, not event rules for us |

## 3. Limits of this pass

- Documents were **not re-read** today; comparison is title/id/folder-level. Only the
  Welcome Guide modal was opened to confirm the required-docs workflow; it re-rendered
  the same document as the 21 Oct archive (visible head/tail match; not byte-verified).
- Video bodies and any onboarding-call announcements are **not ingested** — player-only
  from here. That is the single largest unread gap, and it is time-critical.
- The API record is dated `updated_at 2026-10-21T07:16Z`, before the last two video
  uploads — expected; the videos are hub resources, not rules fields.

## 4. Re-verification list carried forward

Items 1–3 below are **flipped or sharpened** by this pass; 4–7 stand from the 21 Oct digest:

1. Judging-opens date — event-page field now supports AGENTS.md (27 Oct 00:00 UTC);
   hub docs say 28. Resolved in favour of the field for our calendar, immaterial either way.
2. Registration-close conflict (23:45 docs vs 23:59 field) — moot, registered.
3. NVIDIA/Nemotron — still the same operative wording ("wherever it contributes"), but a
   $4,699 dedicated **Nemotron** in-kind prize now exists; decide within the approved
   Option-B scope whether the Nemotron story gets explicit treatment (README, deck).
4. Repository public — unchanged requirement.
5. Team lock at first submission — confirm before creating any submission shell.
6. `metadata.json` sponsor attribution — still expected by sponsor cards.
7. Slide deck — still a required component that does not exist yet.

**Not done here:** no dashboard flags toggled, no documents downloaded (endpoint 401s
outside the session and rendered-text archives already exist), no video watched,
no AGENTS.md write (approval-gated; deltas above are for the builder's decision),
no product-code or scope change.
