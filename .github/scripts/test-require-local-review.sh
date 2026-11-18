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
expect 2 "gh pr create --fill --head other" "blocks --head even when HEAD is recorded"
expect 2 "gh pr create -H other --fill" "blocks -H even when HEAD is recorded"
expect 2 "gh pr create -Hother --fill" "blocks attached -H form"
expect 2 "gh pr create --head=other" "blocks --head= form"
expect 0 "gh pr create --fill && echo --head -H" "flags in a later subcommand are ignored"
expect 2 "gh pr create --title \"a; b\" --head other" "separator inside quotes does not hide --head"
expect 2 "gh pr create --title 'x && y' -H other" "single-quoted separator does not hide -H"
expect 2 "echo 'gh pr create' && gh pr create --head other" "quoted earlier mention does not hide --head"
expect 2 "gh pr create -dH other" "combined short flags with H are blocked"
expect 0 "gh pr create --fill --body \"see -H and --head\"" "flag text inside quotes is ignored"

# 没有 jq 时 fail closed：PATH 里只放钩子需要的其他命令
nojq="$work/nojq-bin"
mkdir -p "$nojq"
for c in bash cat git; do ln -s "$(command -v "$c")" "$nojq/$c"; done
input=$(jq -n --arg d "$work" '{tool_input: {command: "gh pr create --fill"}, cwd: $d}')
got=0; printf '%s' "$input" | PATH="$nojq" bash "$hook" 2>/dev/null || got=$?
[[ "$got" == 2 ]] || { echo "FAIL missing jq: expected exit 2, got $got" >&2; exit 1; }
got=0; printf '%s' '{"tool_input":{"command":"ls"}}' | PATH="$nojq" bash "$hook" 2>/dev/null || got=$?
[[ "$got" == 0 ]] || { echo "FAIL missing jq: other commands should pass, got $got" >&2; exit 1; }

# 钩子确实在项目设置里注册，且指向存在的脚本
settings="$repo_root/.claude/settings.json"
jq -e '.hooks.PreToolUse[] | select(.matcher == "Bash") | .hooks[]
  | select(.command == "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/require-local-review.sh")
  | select(.if == "Bash(gh pr create*)")' "$settings" >/dev/null \
  || { echo "FAIL hook command or if-filter not registered as expected in .claude/settings.json" >&2; exit 1; }

git -C "$work" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m two
expect 2 "gh pr create --fill" "blocked after a new commit"

# 有未提交的已跟踪改动时拒绝记录
echo a > "$work/f" && git -C "$work" add f
if (cd "$work" && bash "$mark" >/dev/null 2>&1); then
  echo "FAIL mark should refuse a dirty worktree" >&2
  exit 1
fi

echo "require-local-review: ok"
