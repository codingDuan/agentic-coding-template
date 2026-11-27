#!/usr/bin/env bash
# 测试个人包 docs/agents/personal-control 的 hooks/require-local-review.sh 与 scripts/mark-review-passed.sh。
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
pkg="$repo_root/docs/agents/personal-control"
hook="$pkg/hooks/require-local-review.sh"
mark="$pkg/scripts/mark-review-passed.sh"
work=$(mktemp -d)
trap 'rm -rf "$work" "${work}-sibling"' EXIT

git -C "$work" init -q
git -C "$work" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m one
export PERSONAL_CONTROL_REPO="$work"

run_hook() {
  local cmd=$1 dir=${2:-$work}
  jq -n --arg c "$cmd" --arg d "$dir" '{tool_input: {command: $c}, cwd: $d}' | bash "$hook" 2>/dev/null
}

expect() {
  local want=$1 cmd=$2 label=$3 dir=${4:-$work} got=0
  run_hook "$cmd" "$dir" || got=$?
  if [[ "$got" != "$want" ]]; then
    echo "FAIL $label: expected exit $want, got $got" >&2
    exit 1
  fi
}

expect 0 "gh pr list" "other commands pass"
expect 2 "gh pr create --fill" "blocked without record"

# 只管配置的仓库：仓库外和同前缀的兄弟目录放行，仓库子目录照拦
mkdir -p "$work/sub" "${work}-sibling"
expect 0 "gh pr create --fill" "outside the configured repo passes" "$(dirname "$work")"
expect 0 "gh pr create --fill" "sibling dir with the same prefix passes" "${work}-sibling"
expect 2 "gh pr create --fill" "subdirectory of the repo is still gated" "$work/sub"

# 没配置仓库路径时 fail closed
got=0
jq -n --arg d "$work" '{tool_input: {command: "gh pr create --fill"}, cwd: $d}' \
  | env -u PERSONAL_CONTROL_REPO bash "$hook" 2>/dev/null || got=$?
[[ "$got" == 2 ]] || { echo "FAIL unconfigured repo path: expected exit 2, got $got" >&2; exit 1; }

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
multiline_body=$'gh pr create --title "t" --body "$(cat <<\'EOF\'\n| a | b |\n|---|---|\nline; two\nEOF\n)" --head other'
expect 2 "$multiline_body" "multi-line quoted body does not hide --head"
expect 2 "gh pr create --title 'it\"s' --head other --body \"b\"" "double quote inside single quotes does not hide --head"

# 没有 jq 时 fail closed：PATH 里只放钩子需要的其他命令
nojq="$work/nojq-bin"
mkdir -p "$nojq"
for c in bash cat git; do ln -s "$(command -v "$c")" "$nojq/$c"; done
input=$(jq -n --arg d "$work" '{tool_input: {command: "gh pr create --fill"}, cwd: $d}')
got=0; printf '%s' "$input" | (cd "$work" && PATH="$nojq" bash "$hook" 2>/dev/null) || got=$?
[[ "$got" == 2 ]] || { echo "FAIL missing jq: expected exit 2, got $got" >&2; exit 1; }
got=0; printf '%s' "$input" | (cd / && PATH="$nojq" bash "$hook" 2>/dev/null) || got=$?
[[ "$got" == 0 ]] || { echo "FAIL missing jq outside the repo: expected exit 0, got $got" >&2; exit 1; }
got=0; printf '%s' '{"tool_input":{"command":"ls"}}' | PATH="$nojq" bash "$hook" 2>/dev/null || got=$?
[[ "$got" == 0 ]] || { echo "FAIL missing jq: other commands should pass, got $got" >&2; exit 1; }

# 复制安装用的占位符在仓库版里保持原样，hook 的默认值就是它
grep -q 'PERSONAL_CONTROL_REPO:-<REPO_PATH>' "$hook" \
  || { echo "FAIL hook default must stay the <REPO_PATH> placeholder in the repository copy" >&2; exit 1; }

git -C "$work" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m two
expect 2 "gh pr create --fill" "blocked after a new commit"

# 有未提交的已跟踪改动时拒绝记录
echo a > "$work/f" && git -C "$work" add f
if (cd "$work" && bash "$mark" >/dev/null 2>&1); then
  echo "FAIL mark should refuse a dirty worktree" >&2
  exit 1
fi

echo "require-local-review: ok"
