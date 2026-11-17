#!/usr/bin/env bash
# PreToolUse(Bash)：在启用了 agentic workflow 的仓库里，gh pr create 前必须已对当前 HEAD 记录本地 review 通过。
# 「启用」= 仓库根目录存在 .agentic-workflow 标记文件（模板自带）。
# 记录由 personal-control/scripts/mark-review-passed.sh 写入。
input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"
case "$command" in
  *"gh pr create"*) ;;
  *) exit 0 ;;
esac
cd "$cwd" 2>/dev/null || exit 0
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -f "$root/.agentic-workflow" ] || exit 0
head="$(git rev-parse HEAD 2>/dev/null)" || exit 0
marker="$(git rev-parse --git-path agentic-review-passed 2>/dev/null)"
if [ -f "$marker" ] && [ "$(cat "$marker")" = "$head" ]; then
  exit 0
fi
echo "当前 HEAD ($head) 没有本地 review 通过记录。先按 personal-control 的 pr-ready-gate「Local review loop」跑 review，无阻塞项后运行 mark-review-passed.sh，再创建 PR。" >&2
exit 2
