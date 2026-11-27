---
name: personal-control
description: Personal control profile for the owner of this machine. Use in <REPO_PATH> whenever writing-plans, executing-plans, or pr-ready is used, so Claude Code and Codex apply the same decision-card, explain-back, local-review, and simulated-flight gates without imposing them on other contributors.
---

# Personal Control

This skill is a personal overlay on the repository's shared workflow. Always follow the repository
skill first, then add only the gate for the current stage:

- Planning with `writing-plans`: read [references/planning-gate.md](references/planning-gate.md).
- Implementation with `executing-plans`: read [references/execution-gate.md](references/execution-gate.md).
- PR preparation or update with `pr-ready`: read
  [references/pr-ready-gate.md](references/pr-ready-gate.md).

Apply this profile only when working in `<REPO_PATH>` for the owner of this machine. Never ask a
partner, reviewer, or other contributor to complete these personal exercises. The repository's
tests, review, compatibility, and rollout requirements remain mandatory; this profile can add gates
but cannot waive shared requirements.

`docs/agents/high-risk.md` in the repository is the only definition of a high-risk change. This
profile reads it and does not keep its own list.

The repository's `pr-lessons` remains the single post-merge learning mechanism. Do not create a
separate personal lessons workflow.
