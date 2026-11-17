#!/usr/bin/env bash
# Install the owner-only layer: personal-control skill + require-local-review hook.
# Never asks other contributors to do this. Re-run with --force to overwrite.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
force=0; [ "${1:-}" = "--force" ] && force=1

skill_dst="$HOME/.agents/skills/personal-control"
hook_dst="$HOME/.claude/hooks/require-local-review.sh"

if [ -e "$skill_dst" ] && [ "$force" -ne 1 ]; then
  echo "exists: $skill_dst (use --force to overwrite)"
else
  mkdir -p "$(dirname "$skill_dst")"; rm -rf "$skill_dst"; cp -R "$here/skills/personal-control" "$skill_dst"
  echo "installed $skill_dst"
fi
mkdir -p "$HOME/.claude/skills"
[ -L "$HOME/.claude/skills/personal-control" ] || ln -s "$skill_dst" "$HOME/.claude/skills/personal-control"

if [ -e "$hook_dst" ] && [ "$force" -ne 1 ]; then
  echo "exists: $hook_dst (use --force to overwrite)"
else
  mkdir -p "$(dirname "$hook_dst")"; cp "$here/hooks/require-local-review.sh" "$hook_dst"; chmod +x "$hook_dst"
  echo "installed $hook_dst"
fi

cat <<'MSG'

Two manual steps (not automated on purpose — they edit your global config):

1) Register the hook in ~/.claude/settings.json under "hooks":
   "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
     "command": "bash ~/.claude/hooks/require-local-review.sh",
     "if": "Bash(gh pr create*)", "timeout": 10}]}]
   The hook only acts in repositories that contain a .agentic-workflow file.

2) Opt projects into the personal gates in ~/.claude/CLAUDE.md, e.g.:
   When working under /path/to/project, always load and apply `personal-control` together with
   the repository's `writing-plans`, `executing-plans`, and `pr-ready` skills.
   Do not require partners or other contributors to pass its personal gates.
MSG
