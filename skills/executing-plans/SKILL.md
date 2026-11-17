---
name: executing-plans
description: Use when executing an existing implementation plan with review checkpoints, verification, docs synchronization, and RULES.md compliance.
---

# Executing Plans

## Overview

Load the plan, verify it satisfies project rules, execute all tasks, run the required tests, **verify plan completion**, and **sync plan docs with implementation reality**.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** If subagents are available (Claude Code, Codex), carry out **Step 3** with superpowers:subagent-driven-development — fresh context per task plus review checkpoints produces markedly better results. It replaces only Step 3: Steps 1–2 (context, plan gate) and 4–7 (verification, doc sync, finalize) still run here, because the superpowers skill has none of the project rules.

## Step 1: Load Required Context

Read these before implementation:

1. `RULES.md`
2. `AGENTS.md`
3. `docs/plans/README.md`
4. The **main plan document** (architecture + task index)
5. Every **sub-task document** referenced in the index, for the requested scope

If the plan touches API, data model, web UI, mobile, worker, payment, subscription, notification, or permission behavior, also read the corresponding core docs listed in `AGENTS.md`.

Then review the plan critically. Raise any questions or concerns with your human partner **before** starting. If none, create a todo per task and proceed.

## Step 2: Plan Gate

Before touching code, check the plan has:

- The plan exists under `docs/plans/**`, is linked from its topic index, and the user has confirmed it.
- Flowchart, sequence diagram, and state machine — or explicit N/A reasons.
- The single source of truth for business state, identified.
- Data flow and compatibility impact for every client in RULES.md §3 plus Worker·Internal·MCP.
- Verification commands matching the affected paths.
- **上线步骤**: all eight dimensions from `docs/agents/release-dimensions.md`, untouched ones marked "无" rather than omitted, plus 发布顺序.
- Rollback or recovery notes for high-risk domains.

If any required item is missing, update the plan first or ask the user. **Do not silently bypass `RULES.md`.**

## Step 3: Execute Tasks

For each task:

1. Mark it in progress.
2. Follow the planned steps exactly — the plan has bite-sized steps. Prefer existing code patterns.
3. Start with a failing test when behavior changes; confirm it fails for the right reason before implementing.
4. Keep edits scoped to the task.
5. **If implementation deviates from the plan** (unexpected issue, better approach discovered), say so — never silently change course. Then update the affected artifact before continuing:
   - User path changed → update the flowchart.
   - Cross-system call order changed → update the sequence diagram.
   - State or transition changed → update the state machine.
   - A consequential design decision, risk boundary, or non-goal changed → update the plan and get the user's confirmation before continuing.
6. Run the task-level verification before moving on.
7. Mark completed.

## Step 4: Verify Completion

After all tasks are marked complete:

1. **Re-read the main plan document** and confirm every task in the index is actually complete — not just the ones you remember doing. Anything skipped or partially done gets finished, and reported. Fill the plan's §9 completion-reconciliation table one row at a time: each consequential requirement/non-goal needs implementation evidence, its caller or materialization-boundary command, and the fresh result. A removal/prohibition needs repository-wide absence evidence; a helper test does not replace the named boundary.
2. Compare the planned "Files" per task with what actually changed.
3. Run `make test-critical-scope` and follow RULES.md §8: on `REQUIRED`, run `make test-critical`; on `NOT REQUIRED`, keep the output (and the reused run commit, if any) for the PR. Then run the path-scoped tests from `docs/09-test-guide.md`, raising to broader tests for high-risk paths: payment, subscription, permission, notifications, auth, trading execution, migrations.
4. Run formatting/static checks that apply to touched code.
5. Run `git diff --check`.
6. Confirm every verification promise in the plan names a real check, that the check ran, and that its result is recorded. Add missing coverage or record an explicit gap and reason.

If reconciliation finds that implementation contradicts a confirmed constraint, return to Step 3.
Do not make the table green by weakening the plan after seeing the implementation; a consequential
design change follows Step 3's plan-update and confirmation rule.

**Do not claim success until commands have completed and you have read their output.** **REQUIRED SUB-SKILL:** superpowers:verification-before-completion governs every claim in this step.

## Step 5: Sync Plan Docs with Reality

This is a **critical step** — plans routinely deviate during implementation, and stale docs are worse than no docs.

For each **sub-task document**:

1. Update status: `待开始` → `✅ 已完成` (or note if skipped/changed).
2. Fill in **"实际改动"**: what was actually implemented (may differ from 计划改动), exact files modified, any extra fixes discovered along the way.
3. Fill in **"踩坑记录"**: unexpected issues, root cause, solution.

For the **main plan document**:

1. Update status: `进行中` → `已完成`.
2. Fill in the **"实际改动清单"** table with the final file list.
3. Fill in the **"踩坑记录"** table with key learnings.
4. Record deviations from the original design **and why**.
5. Record final verification commands and their results.
6. Update any diagram that implementation discoveries invalidated.
7. Verify task index links and dependency notes are still accurate.
8. Run the plan's deterministic completion contract after statuses, checkboxes, actual changes, and
   final commands have been synchronized:

   ```bash
   python skills/executing-plans/scripts/check_plan_completion.py \
     --repo-root . --plan <main-plan-path> --run-commands
   ```

   A non-zero result returns the work to Step 3 or Step 5. It blocks finalization; do not replace it
   with a verbal completion judgment.

If implementation deliberately leaves a gap, record it as a non-goal or follow-up **with a reason** — not silence.

**Why this matters:** future developers read these documents to understand what was done and why. If the docs say one thing and the code does another, the docs mislead instead of help.

## Step 6: Finalize

Before the final response or PR handoff:

- Check `git status -sb`.
- **Stage only task-related files.** Never `git add -A` / `git add .` blindly: the working tree usually contains the user's own untracked drafts, and a blanket add sweeps them into your commit. Stage explicit paths, then run `git diff --cached --name-only` and confirm every entry belongs to this task before committing. A real session shipped six unrelated draft docs into a PR this way on 2026-07-29.
- Leave unrelated user changes untouched.
- If asked to commit/push, use a focused message and push the current branch.
- Report verification results and note any untracked unrelated files you deliberately left alone.

## Step 7: Complete Development

After plan docs are synced and the branch is clean:

- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow it to verify tests, present options, and execute the choice.

## Stop Conditions

**Stop and ask, or update the plan before continuing, when:**

- The plan violates `RULES.md`.
- A required diagram is missing for a stateful or cross-system change.
- You hit a blocker: missing dependency, repeated verification failure, unclear instruction.
- A test failure reveals the **design** is wrong, not just the implementation incomplete.
- You find an unplanned API compatibility break.
- You cannot identify how existing data will be migrated or intentionally left alone.
- The plan completion checker returns non-zero.

**Ask for clarification rather than guessing. Don't force through blockers.**

## When to Revisit Earlier Steps

**Return to Step 1 (Load and Review) when:**

- Your partner updates the plan based on your feedback.
- The fundamental approach needs rethinking.

## Remember

- Review the plan critically first; run the Plan Gate before any code
- Follow plan steps exactly; don't skip verifications
- Reference the skills the plan tells you to
- Stop when blocked, don't guess
- **Never start implementation on main/master without explicit user consent** — branch first
- **Stage explicit paths, never `git add -A`**
- **Always sync plan docs with reality before declaring done**
- **Check ALL tasks are actually complete, not just the ones you remember doing**

## Integration

**Required workflow skills:**

- **superpowers:using-git-worktrees** — set up an isolated workspace before starting
- **writing-plans** — creates the plan this skill executes
- **superpowers:subagent-driven-development** — preferred way to carry out Step 3 when subagents are available (other steps still run here)
- **superpowers:finishing-a-development-branch** — complete development after all tasks
- **pr-ready** — PR description and pre-merge handoff; its 上线步骤 dimensions must match the plan's
