---
name: control-gates
description: Use when a high-risk plan (per docs/agents/high-risk.md) needs its explain-back before implementation, a re-explain after a §0 decision change or review correction, or its simulated flight after verification and before the PR. Covers how to ask concrete questions, judge answers, and record rounds.
---

# Control Gates

## Overview

These gates check that the **responsible human** understands a high-risk change. The responsible
human is the person who drives the change, confirms the plan, and owns the result. Tests check the
code. These gates check the person. Neither replaces the other.

| Gate | When | Checks against | Record |
|---|---|---|---|
| Explain-back | After plan self-review, before implementation | Plan §0 | §0 `确认记录` |
| Simulated flight | After implementation and verification, before the local review loop | Current code and tests | Plan `## 模拟飞行` |

Run them only for plans that are high-risk according to `docs/agents/high-risk.md`. For other plans,
write `不适用：<理由>` in both places.

## Which reference to read

- Every gate: read [references/concrete-questions.md](references/concrete-questions.md) first. It
  defines what a valid question is.
- Explain-back, re-explain after `决策变更：<项>`, or `评审纠偏：<来源>`:
  [references/explain-back.md](references/explain-back.md).
- Simulated flight, or re-fly after review changed covered behavior:
  [references/simulated-flight.md](references/simulated-flight.md).

## Where the stage skills call this skill

- `writing-plans` Explain-Back Gate → explain-back.
- `executing-plans`: a §0 decision change, or reclassification to high-risk → explain-back for the
  affected items.
- `pr-ready` Pre-PR Gates step 1 → simulated flight.

The stage skills own the checks that a gate ran: `executing-plans` will not start without a current
`确认记录`, and `pr-ready` blocks a PR without a passing record. This skill owns how the gate runs.

## Boundaries

- A plan confirmation, an approval, or a recitation of the agent's explanation is not understanding.
  Do not accept them in place of a passing answer.
- Do not put the answer in the question.
- The agent never drafts or suggests sign-off wording for an accepted residual risk. Only the
  responsible human writes it.
- These gates add requirements. They never waive tests, review, compatibility, or rollout rules.
