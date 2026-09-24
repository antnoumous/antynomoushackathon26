# Decision log

One entry per significant choice. Record **what** and **why**. Append; don't rewrite
history. If a decision is reversed, add a new entry saying so and why.

---

## 2026-09-24 — Solo entry

**Decision:** Entering solo, not as a team.

**Why:** Confirmed by the builder. Constrains scope: the 144-hour window is one person's
attention, so the build must be small and deep rather than broad.

## 2026-09-24 — Design the repo backwards from the submission requirements

**Decision:** Scaffold README, `.gitignore`, `.env.example`, `evals/` and `docs/insights.md`
before any product code exists.

**Why:** The organisers' submission requirements (clean setup, env-var credentials, no
committed secrets, logs, sample I/O, documented sponsor fit) and the 30 bonus points for
open-sourcing, evaluations and insights are all cheap on day one and expensive at 23:00 on
20 October. Structural homes now beat good intentions later.

## 2026-09-24 — Project lives at ~/projects/open-agent-hackathon

**Decision:** Local path `/Users/ant/projects/open-agent-hackathon`, remote
`https://github.com/antnoumous/antynomoushackathon26` (public).

**Why:** No pre-existing dev-directory convention on this machine. A public repo supports
the open-sourcing bonus criterion from the first commit.

## 2026-09-24 — Track and stack deliberately deferred

**Decision:** No track, problem statement, language or framework chosen yet.

**Why:** Deciding these before understanding the builder's strengths and interests risks
six days spent building the wrong thing. Next conversation.
