---
name: code-review-response
description: Use when acting on code review findings — from a dispatched reviewer, a GitHub PR review, the CI review bot, or a human — before implementing any suggested change, and when deciding whether to push back on a finding.
---

# Code Review Response

## Overview

Evaluate findings against this codebase before touching anything, then fix in an order that
converges instead of spawning another round.

Announce at start: "I'm using the code-review-response skill to work through the findings."

**Core principle:** Verify before implementing. A finding is a hypothesis about this codebase
until you have checked it against this codebase.

## The Response Pattern

```
1. READ      all findings before reacting to any of them
2. TRIAGE    real / wrong / needs-clarification — with evidence for each
3. CLARIFY   ask about every unclear item BEFORE implementing any item
4. FIX       blocking → mechanical → structural, one at a time
5. SWEEP     grep for siblings of each fix
6. VERIFY    make test-critical-scope (→ make test-critical) + path-scoped tests
7. RECORD    where the next reviewer will actually look
```

## Never Perform Agreement

**NEVER:** "You're absolutely right!" / "Great catch!" / "Thanks for flagging!" / "Let me
implement that now" (before verifying).

**INSTEAD:** restate the technical requirement, ask a specific question, push back with evidence,
or just fix it and show the diff. Actions carry the acknowledgment.

If you pushed back and were wrong: "Checked — you're right, `X` does `Y`. Fixing." One line, no
apology, no re-litigating why you pushed back.

## Triage Before Implementing

For each finding, produce a verdict with evidence:

| Verdict | Requires |
|---|---|
| **Real** | The failing path, reproduced or traced in the code |
| **Wrong** | The code/test/constraint that disproves it |
| **Unclear** | The specific question that would resolve it |

Reviewers routinely misjudge this project on these — check before accepting:

- **Intentional designs read as bugs.** Idempotent duplicate operations, generation-time
  snapshots, no standalone cash flow. These are documented in the plan docs and PR 设计约束.
  If a finding contradicts a stated design constraint, that is pushback territory — and a signal
  the constraint needs a short comment near the code.
- **"Add a fallback."** Removing pricing/config fallbacks was deliberate work here. Fail-closed
  beats a silent wrong number in a payment path. Do not re-add one on review advice alone.
- **"This is unused, remove it."** Grep all three clients plus Worker/MCP/agent first. Mini
  Program and Mobile ship on slow release cycles, so "no caller in the web client" is not "no caller."
- **"Just mock it."** Payment, subscription, and permission findings need real transactional
  assertions, not call-count mocks.

**If ANY item is unclear, stop and ask about all of them before implementing any of them.**
Findings are frequently related; a partial understanding produces a wrong fix and another round.

## Fix Order

1. **Blocking (🔴)** — data loss, resource loss, permission bypass, transaction/concurrency
   defects, security, RULES.md violations
2. **Mechanical** — typos, imports, dead code, misleading comments
3. **Structural** — refactors, extracted helpers, test restructuring

One at a time. Test each before starting the next.

## Sweep for Siblings — Do Not Play Whack-a-Mole

**Every fix must be followed by a grep for the same shape elsewhere.** This repo's hard-won rule:
these bugs come in pairs. The 2026-08-16 dashboard `GroupingError` had an identical sibling query
that only escaped notice because the first one crashed earlier. A one-line fix that leaves its
twin in place is how a review reaches round 10.

| You fixed | Grep for |
|---|---|
| A repeated literal across SELECT/GROUP BY | Every other `func.coalesce(...)` / `case(...)` in a grouped query |
| A bare status literal | `== "<value>"`, `.in_((...))`, `filter(status=...)`, frontend `=== '<value>'` |
| A transaction boundary | Other callers of the same service function |
| A guard on one client | The same endpoint's other two clients |
| A `String(n)` overflow | Other fixed identifiers written to the same column |

## Verify

Evidence before assertions. Never claim fixed without the command output in hand.

- `make test-critical-scope`, then `make test-critical` when it reports `REQUIRED` (RULES.md §8). A fix that only touches exempt paths after a green run reuses that run with `SINCE=<run commit>`.
- Path-scoped tests per `AGENTS.md` 测试约定
- Pin settings switches with `monkeypatch`. A local `.env` hides failures that CI will surface,
  because CI has no `.env` and switches fall back to defaults.
- In a worktree, override `PYTHONPATH` to the worktree itself, or you are testing the main
  workspace's stale code:
  ```bash
  W=$PWD; {{WORKTREE_ENV_OVERRIDE}} {{FULL_BACKEND_TEST_COMMAND}}
  ```
- Distinguish pre-existing flakiness from new breakage before reporting a failure as yours.

## Record the Outcome

Findings and their resolutions must land where the next reviewer looks — not only in chat:

- **Commit message** — what the finding was and how it was fixed
- **PR description** — update 验证结果 and the 不变量与故障拦截 table (fixes often add guards or
  move line numbers), 残余风险, and 回滚/恢复. Correct 设计约束 / 上线步骤 if the fixes changed
  restart requirements, rollback semantics, or all-client impact. Use **pr-ready**.
- **Plan doc under `docs/plans/**`** — when the fix changed the design, extend the existing topic
  doc rather than starting a parallel one
- **A short comment near the code** — when a design constraint was misread as a defect, so the
  next reviewer does not re-file it

Respect RULES.md #5: no new `.md` outside the whitelist. A one-off finding write-up belongs in the
commit message or PR description, not a new file.

## Replying on GitHub

Reply inside the comment thread, not as a top-level comment:

```bash
gh api repos/{{GITHUB_REPO}}/pulls/<PR>/comments/<COMMENT_ID>/replies -f body='...'
```

State the resolution: fixed (with the commit), disputed (with evidence), or deferred (with why and
where it is tracked).

## Common Mistakes

| Mistake | Fix |
|---|---|
| Performative agreement | State the requirement or just fix it |
| Implementing before verifying | Triage with evidence first |
| Fixing the reported line only | Grep for siblings — they come in pairs |
| Partial implementation while items are unclear | Clarify everything, then implement |
| Skipping `make test-critical` because "I only touched X" | Let `make test-critical-scope` decide; paste its output |
| Claiming green without running it | Evidence before assertions |
| Re-adding a fallback on review advice | Fail-closed is deliberate here |
| Accepting "unused, remove it" | Grep all three clients + Worker/MCP first |
| Findings resolved only in chat | Record in commit / PR / plan doc |
| Fixes silently invalidating the PR description | Re-run pr-ready |
