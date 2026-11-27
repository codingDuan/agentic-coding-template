# {{PROJECT_NAME}} Agent Guide

## Purpose

{{PROJECT_PURPOSE}}
<!-- 用 2–4 句话说明：产品卖什么/解决什么、谁在用、本仓库负责哪一层（调度、API、前端…）。 -->

## Sources

Numbered files in `docs/` are core documents. Run `ls docs/` to see their subjects.

- API contracts: `docs/01-api-contract.md` and `docs/api-contract/`
- Tests: `docs/09-test-guide.md`
- Plans: `docs/plans/README.md`
- Post-merge lessons: `docs/agents/lessons.md`
- Reasons and incidents behind each rule: `docs/agents/rules-evidence.md`

Read the lessons before code changes.

## Mandatory Rules

`RULES.md` is the rule source for development and review.
Claude Code imports it here. Codex reads it through the mandatory `AGENTS.md` entry instruction.

@RULES.md

## Required Workflow

Run `git branch --show-current` before analysis. Use `main` as the baseline unless the user specifies another baseline.
Create a branch before the first file change.
A read-only task or an explicit user instruction can keep the current branch.
Continue the current feature branch for the same work. If the correct choice is not clear, create a branch.
Use `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, or `chore/<topic>`.

Before code changes, use `writing-plans` to create or extend the applicable plan in `docs/plans/`.
Get user confirmation before implementation. Then use the repository `executing-plans` skill.
Plan exceptions are single defects, typos, comments, formatting, dependency versions,
explicit direct-change requests, and temporary external scripts.
If a plan exception is not clear, ask the user.
Use edit tools for source changes. Do not use one-time scripts or complex shell commands to rewrite source files.

Before production diagnosis, search `git log --grep` and verify the deployed version first.
Use `pr-ready` before a PR.

## Evidence and Tests

Report only results that direct evidence supports.
Separate implementation, test, review, deployment, and production states.
`RULES.md` defines merge gates. `docs/09-test-guide.md` defines test selection and evidence.
The `Makefile` defines test targets and critical test files.

## Skills and Configuration

Skill sources are in `skills/`. Skill descriptions select task-specific skills.
After a skill change, run `bash scripts/install-skills.sh` and start a new session.

- Issues: `docs/agents/issue-tracker.md`
- Labels: `docs/agents/triage-labels.md`
- Releases: `docs/agents/release-dimensions.md`
- Terms: `docs/agents/domain.md`
- High-risk scope: `docs/agents/high-risk.md`
- Optional personal overlay (explain-back, simulated flight, local review loop; never required of other contributors): `docs/agents/personal-control/README.md`
- Skill dependencies: `docs/agents/skill-dependencies.md`
