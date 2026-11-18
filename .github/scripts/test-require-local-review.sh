#!/usr/bin/env bash
# 测试 .claude/hooks/require-local-review.sh 与 skills/pr-ready/scripts/mark-review-passed.sh。
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
hook="$repo_root/.claude/hooks/require-local-review.sh"
mark="$repo_root/skills/pr-ready/scripts/mark-review-passed.sh"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

git -C "$work" init -q
git -C "$work" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m one

run_hook() {
  local cmd=$1
  jq -n --arg c "$cmd" --arg d "$work" '{tool_input: {command: $c}, cwd: $d}' | bash "$hook" 2>/dev/null
}

expect() {
  local want=$1 cmd=$2 label=$3 got=0
  run_hook "$cmd" || got=$?
  if [[ "$got" != "$want" ]]; then
    echo "FAIL $label: expected exit $want, got $got" >&2
    exit 1
  fi
}

expect 0 "gh pr list" "other commands pass"
expect 2 "gh pr create --fill" "blocked without record"

(cd "$work" && bash "$mark" >/dev/null)
expect 0 "gh pr create --fill" "passes when record matches HEAD"

git -C "$work" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m two
expect 2 "gh pr create --fill" "blocked after a new commit"

# 有未提交的已跟踪改动时拒绝记录
echo a > "$work/f" && git -C "$work" add f
if (cd "$work" && bash "$mark" >/dev/null 2>&1); then
  echo "FAIL mark should refuse a dirty worktree" >&2
  exit 1
fi

echo "require-local-review: ok"
