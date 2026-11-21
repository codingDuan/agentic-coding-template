---
name: pr-ready
description: Use when preparing, reviewing, or updating a PR description or pre-merge handoff, especially after code changes, to ensure RULES.md, diagrams, compatibility, verification, and review context are complete.
---

# PR Ready

## Overview

Use this skill before opening, updating, or handing off a PR. It verifies that reviewers have enough
business context and that the diff satisfies project rules.

Announce at start: "I'm using the pr-ready skill to prepare the PR context."

## Required Reads

Read:

1. `RULES.md`
2. `AGENTS.md`
3. `docs/plans/README.md`
4. Relevant design and implementation docs under `docs/plans/**`
5. `git diff --stat` and the actual diff for changed files

For every relevant main plan, run its deterministic contract after plan statuses and actual changes
have been synchronized:

```bash
python skills/executing-plans/scripts/check_plan_completion.py \
  --repo-root . --plan <main-plan-path> --run-commands
```

If no plan applies under the repository's documented exceptions, record that reason instead of
inventing a plan path.

## Pre-PR Gates

Run these after implementation and verification, before `gh pr create` or handing off the PR,
**in this order**: simulated flight first, local review loop last. The review must cover every
commit, including the plan commit that records the flight; the review record itself never needs a
commit, so the loop terminates.

PRs created by CI workflows (for example the `pr-lessons` rolling `lessons/pending` PR) are exempt:
a human reviews them at merge.

### 1. Simulated flight (high-risk plans)

For a plan classified high-risk against `docs/agents/high-risk.md`, **REQUIRED SUB-SKILL:** use
`control-gates` to run the simulated flight with the human partner who drives the change, record it
in the plan's `## 模拟飞行`, and commit. Other plans record
`不适用：<理由>` there. Do not create or hand off the PR until it passes. Code or tests changed
because of the flight go back through full verification and plan sync before the review loop.

### 2. Local review loop (every PR)

1. Run `code-review-request` against `origin/main...HEAD`, then handle the report with
   `code-review-response`.
2. If any finding is blocking (🔴), fix it, rerun the affected verification, and record that
   round in the plan's 实际改动 section (when a plan applies) **in the same commit as the fix**.
   If the fix changes behavior covered by a flight exercise, re-fly that exercise against the fix
   commit and commit the updated `## 模拟飞行` record separately (a record cannot name the commit
   that contains it). Then start a new round. Repeat until one round reports no 🔴 for the current
   HEAD.
3. The final round (no 🔴) is recorded **only in the PR description**, never in a tracked file:
   committing it would change HEAD and invalidate the record. The PR description lists every round:
   round number, reviewed commit, findings, and the treatment of each. An unfixed non-blocking
   finding needs a reason.
4. When the round for the current HEAD has no 🔴, run
   `bash skills/pr-ready/scripts/mark-review-passed.sh`. It records HEAD as reviewed. Never run it
   before the review finishes or while a 🔴 remains.
5. Only then create the PR, from the branch's own worktree and without `--head`. Any later commit
   invalidates the record: changes after review need a new round before creating or updating the
   PR.

Claude Code enforces step 5 with the project `PreToolUse` hook in `.claude/settings.json`
(`.claude/hooks/require-local-review.sh`). It blocks `gh pr create` unless the record matches the
HEAD of the session's working directory, blocks `--head` / `-H`, and blocks when `jq` is missing.
It does not gate `git push` to an already open PR; updating a PR relies on step 5 being followed.
Codex has no hook; follow the steps manually.

## PR Description Checklist

The PR description must include these sections in this order. The order is the human reading
order: a reviewer reads the first group, which gives the problem and the evidence, and opens the
diff only where a claim looks doubtful. The reviewer then uses the reference group to check scope.

Read-first sections:

- **关联文档**: links to design and implementation docs. If absent, explain why.
- **需求背景**: user problem and business scenario.
- **不变量与故障拦截**: one row per invariant this PR creates, changes, or relies on:

  | 不变量 | 守在哪（文件:行） | 拦截的故障 | 测试 | 修复前红的证据 |
  |---|---|---|---|---|

  An invariant is a condition that must hold after the change, such as "`previous_path` is at
  most 512 characters" or "one callback fulfills an order at most once". 拦截的故障 names a
  concrete input or event, not "covers the logic". 修复前红的证据 shows that the test fails without
  the change: a red run, a reverted-line run, or the reason no red run is possible. For an
  invariant the PR relies on but does not change, name the existing test that already guards it.
  When no repository code enforces an invariant, 守在哪 may cite the instruction text, an external
  contract, a platform guarantee, or an explicit assumption. A row with no test must also appear
  in **残余风险**. Write "无" only when the PR changes informational docs alone (`docs/plans/**`,
  `docs/product-docs/**`, `docs/sprint/**`, `docs/discuss/**`, `docs/static/**`, README files),
  and give the reason. Runtime code, copy, styling, and docs that steer agents or contracts
  (`skills/**`, `docs/agents/**`, `docs/api-contract/**`, root `RULES.md` / `REVIEW.md` /
  `AGENTS.md` / `CLAUDE.md`) need rows. This boundary is separate from the RULES.md #8
  `make test-critical` exemption.
- **残余风险**: known risks that tests do not cover, and how to observe them after release
  (log line, dashboard, query). Reproduce verbatim any sign-off the responsible human wrote in the
  plan's `## 模拟飞行`; never draft that wording for them. Write "无" only
  after checking third-party dependencies, production-only concurrency, release order, and
  observability, and give the reason.
- **回滚/恢复**: mandatory for every PR. For an ordinary change one line is enough, such as
  "revert this commit and redeploy; no persisted data changes". Migrations, payment,
  subscription, permission, notification, and scheduler changes must give the rollback method and
  data effect for each release batch, as `docs/agents/release-dimensions.md` requires.
- **重点 review 范围**: files, contracts, and risks to inspect.

Reference sections:

- **设计约束**: intentional behaviors and boundaries reviewers should not misclassify as gaps.
- **图纸索引**: flowchart, sequence diagram, state machine locations, or N/A reasons.
- **数据流**: inputs, persisted objects, state transitions, outputs.
- **非目标**: what this PR explicitly does not support.
- **兼容性**: API, database, migration, every client in RULES.md §3 plus Worker/Internal impact.
- **状态流转**: changed states, driving actions, rejected actions.
- **验证结果**: commands run and final outputs.
  Include each relevant plan path, the exact completion-checker command, and its exit-0 result.
  Include the local review rounds and, for a high-risk plan, the simulated-flight conclusion with
  its verified commit.
- **上线步骤**: mandatory for every PR. Enumerate all eight dimensions, marking untouched
  ones "无" rather than omitting the row, then state 发布顺序 and post-deploy verification.
  **Read `docs/agents/release-dimensions.md` and follow it** — it holds the dimension table,
  the Worker/MCP import greps, and the release-cycle rules for Miniprogram/Mobile.

## Review Gates

Block or revise the handoff when:

- `RULES.md` impact is not addressed.
- A technical plan lacks required diagrams without explicit N/A reasons.
- API/schema/auth/payment/subscription/permission changes lack all-client compatibility.
- Data-layer bug fixes do not explain historical data handling.
- Verification is missing for touched high-risk paths (`docs/agents/high-risk.md`).
- **`make test-critical-scope` output is not in 验证结果, or it reports `REQUIRED` and no green
  `make test-critical` is recorded** (RULES.md §8). A reused run must name its commit and match the
  `SINCE` in the scope output.
- The PR description says only "frontend updated" or "tests passed" without concrete scope.
- **不变量与故障拦截 is missing, a row names no concrete fault, or the table says "无" while the
  PR changes more than informational docs.** A row without a test must reappear
  in 残余风险.
- **回滚/恢复 is missing.** It is mandatory for every PR, not only high-risk categories.
- **上线步骤 is missing, a dimension is omitted instead of marked "无", or a multi-component
  change lacks 发布顺序.**
- **No local review round reports zero 🔴 for the current HEAD**, or rounds are not recorded.
- **A high-risk plan lacks a passing explain-back in §0 `确认记录`, or a passing simulated flight
  whose recorded commit still covers the current behavior.** A non-high-risk plan lacks the
  `不适用：<理由>` lines.
- A relevant plan completion checker was not run in full command mode, returned non-zero, or its
  concrete result is absent from 验证结果.
- **A backend-only diff claims Worker / MCP need nothing without running the import greps**
  from `docs/agents/release-dimensions.md`. "I only touched the API directory" is not evidence —
  a real PR shipped with this exact gap on 2026-07-29.

## Diff Review

Before finalizing:

1. Run `git status -sb`.
2. Confirm unrelated user changes are not staged.
3. Review `git diff --stat`.
4. Review changed docs and code for consistency.
5. Run `git diff --check`.
6. Confirm the `make test-critical-scope` result and, when required, a green `make test-critical`; confirm the path-scoped tests from `docs/09-test-guide.md` were run.
7. Re-run every relevant plan's completion checker with `--run-commands`; treat any non-zero result
   as a blocking gap, even when the broader suite is green.

## Output

Produce either:

- A ready-to-use PR description, or
- A concise list of blocking gaps with exact docs/files to update.

Keep the output concrete. Include commands and file paths, not generic advice.
