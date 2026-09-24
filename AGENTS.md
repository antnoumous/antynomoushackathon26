# AGENTS.md — Open Agent Hackathon 2026

Auto-injected into every session and every coding agent working in this directory.
Keep it short, current, and factual. Update **State** as things change.

## What this is

A solo entry to the **Open Agent Hackathon 2026** (GenAI Works). Goal: build an agent
that does real work — not a chatbot, not a demo. Judged against published criteria.

## State

- **Track:** NOT YET CHOSEN — deliberate. Next decision, before the build window.
- **Idea / use case:** NOT YET DEFINED.
- **Stack:** NOT YET CHOSEN. Do not add dependencies or assume a language until decided.
- **Build window:** 15 Oct 2026 00:00 UTC → 20 Oct 2026 23:45 UTC (144 hours).

## Hard dates (all UTC)

| Date | What |
|---|---|
| 7 Oct 16:00–17:30 | Zetaris workshop (data layer) — recorded |
| 8 Oct 16:00–17:30 | NVIDIA workshop (token layer) — recorded |
| 12 Oct 16:00–17:30 | Meterless workshop (orchestration layer) — recorded |
| 14 Oct 16:00–17:30 | Participant onboarding |
| **15 Oct 00:00** | **Build window opens** |
| **20 Oct 23:45** | **Submissions close — hard deadline** |
| 30 Oct 16:00 | Results announced (live call) |

## Tracks (pick exactly one)

1. **Connected Agent Context** — connect to real, fragmented data
2. **Autonomous Agent** — multi-step work without hand-holding
3. **The Agent That Can Explain Why** — reasoning transparency, provenance
4. **Reasoning Architecture** — the reasoning design itself

A fifth, the **Tinkerer Track**, is judged only on work built during the window.
Scope not yet confirmed from the official source.

## Sponsor tech — one layer each

| Sponsor | Layer | Use it to |
|---|---|---|
| Zetaris | Data | Connect to real, fragmented data via MCP |
| NVIDIA | Token | Scale reasoning cost-effectively |
| Meterless | Orchestration | Run autonomous multi-step workflows |

## Non-negotiables (these are scored, and are expensive to retrofit)

- Runs from a **clean setup, no manual steps**.
- Credentials come from **environment variables only**. Nothing hardcoded.
- **No secrets, keys or tokens committed.** `.env` is gitignored; `.env.example` is the template.
- **Logs** show how the agent actually worked.
- README setup steps are **complete and accurate**.
- Sample **inputs and outputs** are included.
- **Where each sponsor technology fits** is written down.

## Conventions

- Record every significant choice in `docs/decisions.md` with the reason.
- Sponsor findings go in `notes/`.
- `evals/` and `docs/insights.md` exist to earn bonus points — populate them as you go,
  not at the end.
- Repo remote: https://github.com/antnoumous/antynomoushackathon26
