---
name: personal-control
description: Personal control profile for the owner of this machine. Use in the owner's opted-in project directories (listed in the owner's global CLAUDE.md) whenever writing-plans, executing-plans, or pr-ready is used, so Codex Native and Claude Code apply the same explain-back and simulated-flight gates without imposing them on other contributors.
---

# Personal Control

This skill is a personal overlay on the repository's shared workflow. Always follow the repository
skill first, then add only the gate for the current stage:

- Planning with `writing-plans`: read [references/planning-gate.md](references/planning-gate.md).
- Implementation with `executing-plans`: read [references/execution-gate.md](references/execution-gate.md).
- PR preparation or update with `pr-ready`: read
  [references/pr-ready-gate.md](references/pr-ready-gate.md).

Apply this profile only in the project directories the owner opted into (listed in the owner's
global `~/.claude/CLAUDE.md`) for the owner of this machine. Never ask a partner, reviewer, or other contributor to complete these personal exercises.
The repository's tests, review, compatibility, and rollout requirements remain mandatory; this
profile can add gates but cannot waive shared requirements.

The repository's `pr-lessons` remains the single post-merge learning mechanism. Do not
create a separate personal lessons workflow.
