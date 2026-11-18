#!/usr/bin/env bash
# PreToolUse(Bash)：gh pr create 之前，当前 HEAD 必须已记录本地 review 通过。
# 由仓库 .claude/settings.json 注册，团队成员 clone 后自动生效（Codex 无钩子，按 pr-ready 手动执行）。
# 记录由 skills/pr-ready/scripts/mark-review-passed.sh 写入 git 目录，不进提交。
# 检查的是会话工作目录的 HEAD，所以 --head / -H 指定别的分支时直接拦截。
input="$(cat)"
if ! command -v jq >/dev/null 2>&1; then
  # 没有 jq 无法解析输入：只要提到 gh pr create 就 fail closed，而不是静默放行。
  case "$input" in
    *"gh pr create"*)
      echo "require-local-review 钩子需要 jq（例如 brew install jq），安装后再创建 PR。" >&2
      exit 2 ;;
  esac
  exit 0
fi
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"
case "$command" in
  *"gh pr create"*) ;;
  *) exit 0 ;;
esac
case "$command" in
  *" --head"*|*" -H "*|*" -H="*)
    echo "钩子只核对当前工作区的 HEAD：请在该分支自己的 worktree 里运行 gh pr create，不要用 --head/-H。" >&2
    exit 2 ;;
esac
cd "$cwd" 2>/dev/null || exit 0
git rev-parse --show-toplevel >/dev/null 2>&1 || exit 0
head="$(git rev-parse HEAD 2>/dev/null)" || exit 0
marker="$(git rev-parse --git-path agentic-review-passed 2>/dev/null)"
if [ -f "$marker" ] && [ "$(cat "$marker")" = "$head" ]; then
  exit 0
fi
echo "当前 HEAD ($head) 没有本地 review 通过记录。先按 pr-ready 的「本地评审循环」跑 review，无 🔴 后运行 bash skills/pr-ready/scripts/mark-review-passed.sh，再创建 PR。" >&2
exit 2
