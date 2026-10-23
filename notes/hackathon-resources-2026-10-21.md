# HackOS resource hub — ingestion, 21 October 2026

**What this is:** an incremental digest of the live Resource Hub at
`https://hackathon.genai.works/resources` for the Open Agent Hackathon 2026, read on
**21 October 2026 (SGT)** through the signed-in embedded browser. It records what the hub
contains, what was actually read, and where the hub disagrees with what this repo
already records. It does **not** overwrite those recorded facts — see
[§6 Re-verification list](#6-re-verification-list).

Raw page text and screenshots stay outside the repo, under
`~/projects/open-agent-hackathon-reference/resources-2026-10-21/`
(`read-manifest.json`, `coverage.json`, one `.txt` per document). Nothing here is
copied from a supplier document beyond short quotations.

---

## 1. Coverage — 63 entries, reconciled

The hub reports **63 resources**: 56 documents, 4 videos, 3 dataset catalogues, across 11
folders. Every entry was classified; the counts add up to 63.

| Status | Count | Meaning |
|---|---:|---|
| Read, full visible text archived | 22 | Body captured this session and stored as text |
| Preview only (PDF render) | 2 | Card shows a paginated PDF viewer; body not extractable as text |
| Previously assessed from an earlier copy | 14 | Same document already digested in `notes/` |
| External link, previously reviewed by URL | 17 | Card is a link out; already covered by the 19-URL assessment |
| Not read | 8 | Videos, dataset catalogues (`View details`), one deck, one conduct doc |

### Folder counts as displayed

| Folder | Count |
|---|---:|
| Start here | 7 |
| Rules and Requirements | 7 |
| NVIDIA | 1 |
| Zetaris | 18 (16 link-outs + 2 documents) |
| Cursor | 1 |
| Meterless | 6 |
| Builder Resources | 3 |
| Demo and Submission Resources | 4 |
| Judge and Mentor Resources | 2 |
| Community and Support | 6 |
| Ungrouped | 1 |

Two entries share the title **FAQ** and are **different documents**: a required onboarding
FAQ (Ungrouped) and a Community and Support FAQ. Both were read. The filter chip counts
them as 63 total; the folder chips sum to 56 after the type filter, so use the top-line
63 as the authority.

### The 8 entries not read, and why

| Entry | Reason |
|---|---|
| Open Agent Hackathon Workshop — Data Day with Zetaris | video, not transcribed |
| Zetaris: Getting Started Repository Walkthrough | video, not transcribed |
| Zetaris: Create a REST Source | video, not transcribed |
| Zetaris: Creating and Analysing a Semantic Layer with Claude Code | video, not transcribed |
| Zetaris Open Data: REST API Sources | `View details` catalogue; assessed as U07 |
| Zetaris Open Data: Parquet and CSV Sources | `View details` catalogue; assessed as U06 |
| Zetaris Open Data: Unified Semantic Layers | `View details` catalogue; assessed as U05 |
| Community Moderation Guide | conduct/moderation procedure; no build impact |

Also preview-only, therefore not text-archived: **Creating Better Agents — Learning
Session Deck** (19 pages) and **5 GitHub Repos to Build Faster** (7 pages).

---

## 2. Inventory and authority

Binding tier = published rules and organiser operational guidance. Everything else is
preparation guidance that defers to the rules.

| Document | Folder | What it is | Authority |
|---|---|---|---|
| **Official Rules** | Rules | 24-section rules document, still headed **WORKING DRAFT**; §§12, 13, 22 flagged for counsel | **Draft** — binding rules live on the event page |
| Team Formation Rules | Rules | Roster, locking, prize-split procedure | Guidance; defers to Official Rules |
| Technical Execution Requirements | Rules | Runnable/reproducible/logs standard | Guidance; defers to Rules |
| Submission Requirements | Rules | Deliverables and grading evidence | Guidance; defers to Rules |
| Disqualification Checklist | Rules | Self-check | Guidance; defers to Rules |
| Code of Conduct | Rules | Conduct | Policy; Rules override |
| AI Usage Policy | Rules | AI assistance and integrity | Policy; Rules override |
| **Welcome Guide** | Onboarding | Event orientation: calendar, sponsor requirements, submission list | Organiser guidance, current |
| **Hackathon Overview** | Onboarding | Executive summary: prizes, tracks, eligibility | Organiser guidance, current |
| **Participant Journey Map** | Onboarding | Stage-by-stage path and decision gates | Organiser guidance, current |
| **Event Calendar** | Onboarding | Full dated calendar, UTC | Organiser guidance, current |
| **How APPROACH Solutioning For Your Use Case** | Onboarding | Scoping method, ambition levels, runtime budget | Organiser guidance |
| **FAQ** (onboarding, Required) | Ungrouped | 10-section FAQ | Organiser guidance |
| NVIDIA: Sponsor Overview | NVIDIA | Credits, links, `[TBC]` access steps | Sponsor material |
| Cursor: Sponsor Overview | Cursor | Access, links, `[TBC]` access steps | Sponsor material |
| Zetaris: Sponsor Overview / Getting Started Prompt | Zetaris | Already digested | Sponsor material |
| Meterless ×6 | Meterless | Already digested | Sponsor material |
| Participant Setup Guide | Builder | Already digested (16 Oct Google Doc) | Organiser setup guidance |
| **Vibe Coding Starter Guide** | Builder | Cursor workflow, scaffold prompt, anti-hardcoding checks | Organiser guidance |
| **Strong Submission Examples** | Demo & Submission | Full worked example: architecture, traces, README, deck, demo script | Guidance; Rules apply |
| **Weak Submission Examples** | Demo & Submission | 16 failure patterns with fixes | Guidance; Rules apply |
| **Submission Form Preview** | Demo & Submission | What the form asks for, before you open it | Guidance; form + Rules apply |
| **Demo Video Guide** | Demo & Submission | 1–4 min structure, shot list, script | Guidance; Rules apply |
| **Office Hours Guide** | Judge & Mentor | Booking, triage, session formats | Organiser process |
| **Mentor Playbook** | Judge & Mentor | Internal mentor guide | Organiser process — **contains stale track names** |
| **Troubleshooting Guide** | Community | Docker, deps, provider auth, rate limits, sponsor setup, runaway loops, logs | Organiser guidance |
| **Help Desk Instructions** | Community | How to ask, severity labels, templates | Organiser process |
| **Escalation Path** | Community | Routing, severity, private escalation | Organiser process |
| **Channel Directory** | Community | Where everything lives on HackOS | Organiser process |
| **FAQ** (Community) | Community | 16-section FAQ | Organiser guidance |
| Orientation Session Deck | Start here | Preview only | Organiser deck |
| Creating Better Agents deck | Featured | Preview only (19 pages) | Organiser deck |

Every guidance document in the batch repeats the same escape clause: **where it disagrees
with the Official Rules on the event page, the Official Rules win.**

---

## 3. Facts that change decisions

Copied from the document's own tables, not paraphrased.

### Calendar (all UTC)

| Date | Milestone |
|---|---|
| 14 Aug, 00:00 | Registration opens |
| 12 Oct | Data Day workshop (Zetaris) — recording on HackOS |
| **21 Oct, 12:00–13:30** | **Participant onboarding** (= 20:00–21:30 SGT today) |
| 22 Oct, 00:00 | Build window opens |
| 22 Oct, **23:45** | Registration closes (hard) |
| 27 Oct, **23:45** | Submissions close (hard) |
| 28 Oct | Judging opens, immediately after close |
| 6 Nov, 16:00 | Results, live call |

### Required sponsor technology (Rules §8.1, Welcome Guide, Overview, FAQ)

| Sponsor | Requirement |
|---|---|
| Zetaris | **Required** — every submission must integrate Zetaris |
| Meterless | **Required** — every submission must integrate Meterless |
| Cursor (with Space XAI) | **Required** — must be the development environment |
| NVIDIA | *"Integrate wherever it contributes to the project, workflow or use case"* |

Sponsor Tech is **10 of 100 points**. The `metadata.json` attribution instruction appears
in the NVIDIA, Cursor and Meterless overview cards: name where each sits in README **and**
`metadata.json`.

### Submission components (rules, form preview and demo guide agree)

1. **Demo video, 1–4 minutes** — workflow, challenge fit, key features, Zetaris + Meterless
2. **Slide deck** — problem/users, solution, architecture, stack, sponsor use, what was
   unique, product visuals, future work
3. **GitHub repository** — must be **public**, README covering setup, usage, dependencies
4. **Sponsor technology explanation** — Zetaris, Meterless, Cursor, NVIDIA, what was unique

Recommended, and scored through Technical/Demo: logs or traces, ≥3 sample inputs and
matching outputs, a sample mode, `.env.example` only, no committed secrets, a programmatic
entry point (`run.py` or `POST /run`).

### Judging (100 points)

Impact 30 · Technical 20 · Innovation 15 · Demo 15 · Product & UX 10 · Sponsor Tech 10.
Ties → Impact, then submission timestamp. At least three judges per submission.

### Prizes (per track)

| Track | 1st | 2nd | 3rd |
|---|---:|---:|---:|
| Solving Fragmented Intelligence | $2,000 | $1,350 | $1,000 |
| The Agent That Can Explain Why | $2,000 | $1,350 | $1,000 |
| Reasoning Architecture | $2,000 | $1,300 | $1,000 |
| Wildcard [Tinkerer] | $1,000 | $600 | $400 |

Pool up to $20,000 = $15,000 cash + $5,000 in-kind. Cash by bank transfer within 30 days.
Split equally by default unless the team files a different split in writing.

### Eligibility and team mechanics

- 16+, worldwide, free, one account per participant (duplicates disqualify the team).
- Teams 1–5; **solo entries compete in the same pool**.
- **Team composition locks when the first submission is created.**
- Track can be changed any time before the submission deadline.
- Pre-existing components must be **declared in the submission form**; work committed
  before 22 Oct 00:00 UTC is otherwise ineligible.

### The collaboration bar (repeated in every guidance document)

Weak: `A → B → C`, prompt wrappers, no critique, no retries, no shared state, no evidence.
Strong: dynamic delegation, critique/validation, planner↔executor↔evaluator loops, shared
state or memory, branching, retries, escalation, recovery, and traces that show it.

The Strong Submission Examples document carries a full worked architecture, a 14-line JSONL
trace, a README, a slide outline and a 3:30 demo script. Its **trace field names match the
schema this repo already emits** (`timestamp`, `trace_id`, `agent_name`, `action`,
`input_summary`, `output_summary`, `target_agent`, `confidence`, `retry_count`, `status`).
No change needed there.

---

## 4. What was already covered

These hub entries were digested earlier and were not re-done: the eleven 24 September
organiser documents (`host-docs-digest.md`), the Meterless set (`meterless.md`), the Zetaris
attachments and 19 URLs (`zetaris-docs-assessment-2026-10-17.md`), the 16 October
Participant Setup Guide (`participant-setup-guide-2026-10-17.md`), and the 14 October
meeting (`zetaris.md`).

---

## 5. New material not in this repo before today

Read and archived this session, and **not** previously digested:

1. **Welcome Guide** — the participant-facing orientation: calendar, sponsor requirement
   table, security rule, 30-minute start checklist, 6-day build plan.
2. **Hackathon Overview** — prizes by track and place, eligibility, judging priorities.
3. **Participant Journey Map** — nine stages with decision gates and per-stage actions.
4. **Event Calendar** — full dated calendar plus a mid-build checkpoint on 24 Oct and a
   submission-preparation day on 26 Oct.
5. **How APPROACH Solutioning For Your Use Case** — scoping method, three ambition levels,
   data-availability checklist, runtime budget table (5–10 minutes total), red flags.
6. **Official Rules (current copy)** — 24 sections, still a working draft.
7. **Team Formation Rules** — roster, locking, merge/split, prize-split procedure.
8. **NVIDIA: Sponsor Overview** — Nemotron credits via API keys; access steps still `[TBC]`.
9. **Cursor: Sponsor Overview** — team access; access steps still `[TBC]`.
10. **Submission Form Preview** — the nine things to prepare, worksheet, common mistakes.
11. **Strong Submission Examples** — the worked example above.
12. **Weak Submission Examples** — 16 patterns with fixes.
13. **Demo Video Guide** — timing segments, narration template, backup plan, shot list.
14. **Vibe Coding Starter Guide** — Cursor workflow, a scaffold prompt, hardcoded-output
    audit prompts, golden-path validation.
15. **Office Hours Guide** — booking, triage categories, session formats.
16. **Mentor Playbook** — internal mentor rules; **contains stale track names** (§13).
17. **FAQ (onboarding, Required)** and **FAQ (Community)** — two different documents.
18. **Troubleshooting Guide** — the most operationally useful document in the set.
19. **Help Desk Instructions**, **Escalation Path**, **Channel Directory** — support routing.

---

## 6. Re-verification list

Disagreements with what `AGENTS.md` and `notes/` already record. **Nothing below has been
written into the recorded facts** — these are checks, not corrections.

| # | Item | This repo records | Resource hub says | What to do |
|---|---|---|---|---|
| 1 | **Judging opens** | `AGENTS.md`: "27 Oct 00:00" | **28 Oct**, immediately after submissions close | Looks stale. Update `AGENTS.md` on confirmation |
| 2 | **Registration closes** | `AGENTS.md`: "22 Oct 23:59" | **23:45 UTC** in all eight documents; the dashboard countdown widget says **11:59 PM UTC** | Genuine 15-minute conflict between hub documents and the dashboard widget. We are already registered, so it does not block us — but do not rely on the widget |
| 3 | **Prize pool and breakdown** | Recorded as "unconfirmed" | Up to $20,000 = $15,000 cash + $5,000 in-kind, with per-track 1st/2nd/3rd | New fact; add to `event-brief.md` |
| 4 | **Sponsor list** | Zetaris (data), NVIDIA (token), Meterless (cognition), Cursor (dev) | **Space XAI (with Cursor)**, NVIDIA, Zetaris, Meterless | New: Space XAI is named as the sponsor carrying Cursor. Wording for the README |
| 5 | **NVIDIA requirement** | Unresolved: rules say "where it contributes", Setup Guide says "must run on Nemotron" | Rules §8.1, Welcome Guide, Overview and FAQ all say *"integrate wherever it contributes"*; Mentor Playbook §6.2 says partner tech is "Not mandatory" | Still unresolved. The rules-conforming reading is contribution-dependent; the Setup Guide's Nemotron expectation is the stronger organiser signal. **Ask at onboarding (today, 12:00 UTC)** |
| 6 | **Repository visibility** | `README.md` does not state it | Must be **public** — "a judge must open it without requesting access" | Check the remote is public before submission |
| 7 | **Team lock** | Not recorded | Composition locks when the **first submission** is created | Add to the pre-submission checklist. The builder's HackOS team currently shows 1 member |
| 8 | **Track count** | 3 tracks + Wildcard bonus | Same | Consistent — no action |

### Contradictions *inside* the hub itself

Recorded so a later reader is not surprised:

1. **Mentor Playbook §6.2** says Zetaris/NVIDIA/Cursor/Meterless are "available and
   Sponsor Tech is worth 10 points. **Not mandatory**." This contradicts Rules §8.1, the
   Welcome Guide, the Overview, the FAQ and the Channel Directory, all of which state
   Zetaris and Meterless are required in every submission. **The Rules win.**
2. **Mentor Playbook §13** uses an outdated track taxonomy — "Fragmented", "Autonomous
   Intelligence", "Persistent Memory Agents", "Real-World Industry Agents". It also
   references an unrelated "G42 playbook". That section is stale.
3. **Office Hours Guide §6.4** lists "Demo video 2–3 minutes". Every other document,
   including the rules, says **1–4 minutes**. Use 1–4.
4. **Mentor Playbook** has `[TBC]` private-escalation route; the Escalation Path supplies it
   (`hackathons@genai.works`). Use the Escalation Path.
5. Several `[TBC]` placeholders remain across the hub: NVIDIA and Cursor access steps,
   Meterless prompt library, Build Day / Power Day dates, private escalation route (now
   resolved by Escalation Path).

---

## 7. Actions this implies

Ordered, and none of them taken by this digest:

1. **Attend participant onboarding, 21 October 12:00–13:30 UTC (20:00–21:30 SGT, today).**
   The Overview states additional challenges and prizes are announced there. Resolve the
   NVIDIA/Nemotron question in the Q&A.
2. **Confirm the repository is public** and re-test the clone URL logged out.
3. **Declare the September baseline** in the submission form. `AGENTS.md` already calls it
   a declared pre-existing baseline; the form needs the declaration itself, with the
   before/after split for Wildcard [Tinkerer].
4. **Add `metadata.json`** naming Zetaris, Meterless, Cursor and (if used) NVIDIA — named
   on three sponsor cards as part of the Sponsor Tech evidence.
5. **Reconcile `AGENTS.md`**: judging-opens date and registration-close time (items 1–2).
   That write is approval-gated and was not attempted here.
6. **Build the slide deck** — it is a required component and does not exist yet.

---

## 8. How this was read, and its limits

- The hub requires a signed-in session. It was read through the desktop app's embedded
  preview pane, using the user's existing browser session. **No dashboard checklist item,
  "Mark as read" or "Save" flag was toggled** — the hub still shows 0/6 reviewed.
- Documents were captured as **rendered visible text**, not as original attachments.
  Headings, tables and code blocks survive; the original file bytes and formatting do not.
  Hashes in `read-manifest.json` identify the captured text, not the source file.
- Two PDFs were only previewed; four videos were not transcribed; three dataset catalogues
  open detail views rather than bodies.
- The `Download` button offers Markdown/PDF/DOCX, but the download endpoint returns 401 to
  anything outside the signed-in browser session, and the file never reached a path this
  session can read. Nothing was downloaded.
