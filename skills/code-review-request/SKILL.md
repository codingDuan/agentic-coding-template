---
name: code-review-request
description: Use when a change needs review before merge — a PR is open, a branch is finished, a plan task is done, or work is about to land on main. Also use when a previously dispatched reviewer went idle, died, or returned nothing.
---

# Code Review Request

## Overview

Dispatch one reviewer with a self-contained brief, and make its report survive the reviewer.

Announce at start: "I'm using the code-review-request skill to dispatch the review."

**Core principle:** The report is a file on disk, not a subagent's return value. A return value
disappears when the agent idles, dies, or is interrupted; a file does not. Every re-dispatch that
happens because nobody wrote the report down is pure waste.

## The Two Failures This Skill Exists to Prevent

Both are observed history in this repo, not hypotheticals:

1. **Idle without report.** The reviewer signals `available` and exits having produced nothing.
   The parent has burned a full diff read and has zero output.
2. **Re-dispatch churn.** The parent re-derives SHAs, PR body, diff stat and established facts
   from scratch for the replacement reviewer. `re-dispatch` appears 35 times across this repo's
   session history.

## Workflow

```
1. PRE-FLIGHT   → gather facts once, write the brief file
2. DISPATCH     → one reviewer, no name, report path in the prompt
3. RECOVER      → on idle/death, READ THE FILE before considering re-dispatch
4. RELAY        → surface findings to the user; then switch to code-review-response
```

### 1. Pre-flight (in the parent, once)

Resolve the review target and write everything the reviewer needs into a brief file. Use your
session scratchpad directory; fall back to `/tmp/agent-review/` if you have none.

```bash
mkdir -p "$SCRATCH"
# PR target:
gh pr view <N> --json number,title,body,headRefName,baseRefName,files
git fetch origin pull/<N>/head:pr-<N>-review -f && git fetch origin main
BASE=$(git merge-base origin/main pr-<N>-review); HEAD=$(git rev-parse pr-<N>-review)
# Branch target:
BASE=$(git merge-base origin/main HEAD); HEAD=$(git rev-parse HEAD)
git log --oneline $BASE..$HEAD && git diff --stat $BASE..$HEAD
```

Write `$SCRATCH/review-brief-<target>.md` containing: BASE/HEAD SHAs, commit list, changed-file
list, the PR description, linked `docs/plans/**` docs, and — critically — **facts you have already
verified yourself**. Anything you establish in the parent and do not write down, a replacement
reviewer pays to rediscover.

**For a PR target, put the PR description in the brief once, with its 不变量与故障拦截 table and
残余风险 section moved to the top.** If the table is missing, record that; the reviewer reports it
as 🔴. For a branch or plan-task target, record that no PR description
exists yet.

**Always check scope drift during pre-flight**, and record the answer in the brief: does the PR
description match the actual diff? A description written for the first commit and never updated
after later commits added production code is a recurring failure here. If it drifted, tell the
reviewer it is already confirmed so it spends its budget elsewhere.

### 2. Dispatch

Fill in `reviewer-prompt.md` (in this skill's directory) and dispatch **one** `general-purpose`
subagent.

**REQUIRED dispatch settings:**

| Setting | Value | Why |
|---|---|---|
| `subagent_type` | `general-purpose` | — |
| `name` | **omit it** | A named agent enters addressable/mailbox mode and idles instead of returning a final report. This is the observed idle-without-report cause. |
| report path | passed in the prompt | Makes the report survive the agent. |

The prompt must carry, in this order: the report file path, the brief file path, BASE/HEAD SHAs,
the already-verified facts, the target questions, the read-only constraint, and `REVIEW.md`'s
severity taxonomy. One reviewer only — never dispatch a second for a "second opinion."

### 3. Recover (before any re-dispatch)

```
Reviewer went idle / died / returned nothing?
  → cat "$REPORT_PATH"          # partial report is still useful
  → report usable?  YES → relay it, note it is partial
                    NO  → re-dispatch ONCE, pointing at the brief file
  → second attempt also empty?  → review inline yourself and say so plainly
```

**Never re-dispatch without reading the report file first.** That check costs nothing; a blind
re-dispatch costs a full diff read.

**Never re-dispatch with a freshly rebuilt prompt.** Point the replacement at the existing brief
and tell it what the dead reviewer already established.

**Cap re-dispatch at one.** Two empty attempts means the dispatch path is broken, not unlucky —
do the review inline and tell the user that is what happened.

### 4. Relay

The reviewer's report is not shown to the user. Relay the findings yourself: 🔴 in full, 🟡 and 🟣
summarized. State the verdict. Then use **code-review-response** to act on them.

## What the Reviewer Must Check

Point the reviewer at `REVIEW.md` and `RULES.md` rather than restating them — they are the single
source of truth for severity and hard rules. The evidence-table check below is the one addition:
the owner applies it to locally dispatched reviewers only, and the CI review bot does not run it.

**Evidence table first (PR target only).** Before reading the rest of the diff, the reviewer
verifies each row of the 不变量与故障拦截 table against the code. Any of these is 🔴, because the PR
then presents false evidence:

- The table is missing, or the table says "无" while the PR changes more than informational docs
  (see `pr-ready`).
- 守在哪 cites repository code that does not enforce the invariant, or cites no source. An
  external contract, platform guarantee, or explicit assumption is valid when the row also
  appears in 残余风险.
- Reading the test shows that it cannot reach the guard, or that it has no assertion on the named
  fault.
- 修复前红的证据 is absent and no reason is given.
- A row has no test and does not appear in 残余风险.
- The diff changes behavior that no row covers. Report the missing invariant.

The reviewer judges tests by reading them and does not run them. When reading cannot settle whether
a test would fail without the guard (fixtures, mocks, parametrization, indirect API calls), the
reviewer marks the row `unverified` as 🟡 and asks the author to add a guard-reverted run to
修复前红的证据.

For a branch or plan-task target there is no PR description yet. The reviewer skips this check and
lists the invariants the diff introduces, so the author can fill the table later.

Additionally require an explicit verdict on whichever of these the diff touches:

| Trigger in diff | Must be answered |
|---|---|
| Any SQL / ORM query | SQLite **and** PostgreSQL. `SELECT ... FOR UPDATE` is a no-op on SQLite, so green local tests prove nothing about production locking. Repeated literals in SELECT + GROUP BY → `GroupingError` (RULES.md #1). |
| Transaction boundaries, `db.commit()` / `flush()` | Every success **and** every error branch. Any write path with no commit at all? Any double commit? |
| Status/enum values, new event types | RULES.md #2.1 semantic drift — grep for filters on the value (`== "x"`, `.in_((...))`, `filter(status=...)`, frontend `=== 'x'`), not just the field name. |
| Backend API surface | Client compatibility matrix (RULES.md §3). "Frontend updated" is not an answer. |
| Backend-only diff | Whether Worker/MCP restart claims were backed by the import greps in `docs/agents/release-dimensions.md`. |
| Data-layer bug fix | How existing wrong-shaped rows are handled (RULES.md #4). |
| New/changed tests | Do they assert committed state from a fresh session, or only mock call counts? Are settings switches pinned with `monkeypatch` rather than inherited from local `.env`? |
| `requirements.in` / `pyproject.toml` | `requirements.lock` refreshed (RULES.md #7). |
| Any new `.md` | Location whitelist (RULES.md #5). |

## Review Rounds

This repo has reached round 10+ on a single PR. Convergence is a requirement, not a nicety.
Follow `REVIEW.md`'s second-round rules: suppress new 🟡 on unchanged code, comment only on new or
unresolved 🔴, and mark the round number. Tell the reviewer which round it is and what earlier
rounds already raised — a reviewer that does not know the history will re-report resolved findings.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Naming the reviewer agent | Omit `name`. Named agents idle instead of reporting. |
| Only the return value carries the report | Require a report file path. Always. |
| Re-dispatching on idle without checking disk | `cat "$REPORT_PATH"` first. |
| Rebuilding the prompt for the replacement | Point at the brief file. |
| Dispatching a second reviewer for confirmation | One reviewer. A self-spawned second opinion counts for nothing. |
| Inventing Critical/Important/Minor | Use `REVIEW.md`'s 🔴/🟡/🟣 and its 5/3 caps. |
| Letting the reviewer re-derive what you proved | Put verified facts in the brief. |
| Reviewing the stated scope | Review the actual diff. Descriptions go stale mid-branch. |
