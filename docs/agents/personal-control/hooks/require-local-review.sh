#!/usr/bin/env bash
# PreToolUse(Bash)：在目标仓库里 gh pr create 之前，当前 HEAD 必须已记录本地 review 通过。
# 个人 hook：注册在用户级 ~/.claude/settings.json，只对本机 owner 生效（Codex 无钩子，按 pr-ready-gate 手动执行）。
# 记录由本 skill 的 scripts/mark-review-passed.sh 写入 git 目录，不进提交。
# 检查的是会话工作目录的 HEAD，所以 --head / -H 指定别的分支时直接拦截。

# 复制后把 <REPO_PATH> 换成仓库的绝对路径（或者设置环境变量 PERSONAL_CONTROL_REPO）。
# 匹配仓库目录及其子目录，所以 <REPO_PATH>/.worktrees/* 也在范围内；同前缀的兄弟目录不算。
repo_prefix="${PERSONAL_CONTROL_REPO:-<REPO_PATH>}"

input="$(cat)"
case "$input" in
  *"gh pr create"*) ;;
  *) exit 0 ;;
esac
if [ "$repo_prefix" = "<REPO_PATH>" ]; then
  echo "require-local-review 钩子还没配置仓库路径：把脚本里的 <REPO_PATH> 换成仓库绝对路径，或设置 PERSONAL_CONTROL_REPO。" >&2
  exit 2
fi
if ! command -v jq >/dev/null 2>&1; then
  # 没有 jq 无法解析输入：用 hook 进程的工作目录判断范围，范围内 fail closed，而不是静默放行。
  case "$PWD" in
    "$repo_prefix"|"$repo_prefix"/*)
      echo "require-local-review 钩子需要 jq（例如 brew install jq），安装后再创建 PR。" >&2
      exit 2 ;;
  esac
  exit 0
fi
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"
case "$cwd" in
  "$repo_prefix"|"$repo_prefix"/*) ;;
  *) exit 0 ;;
esac
case "$command" in
  *"gh pr create"*) ;;
  *) exit 0 ;;
esac
# 先把多行合成一行（heredoc 正文常跨行），再一次性从左到右去掉 "..." 与 '...'，
# 先出现的引号优先，所以单引号里的 " 不会和后面的 " 配对吞掉 --head。
# 然后只看 gh pr create 这一段子命令的参数（到 && ; | 为止），避免同一行其他命令里的文字误伤。
# -[A-Za-z]*H 同时覆盖 -H、-Hbranch 和合写的短参数（如 -dH）。这是启发式解析，不是完整的 shell 解析。
unquoted="$(printf '%s' "$command" | tr '\n' ' ' | sed -E "s/\"[^\"]*\"|'[^']*'//g")"
args="${unquoted#*gh pr create}"
args="${args%%&&*}"; args="${args%%;*}"; args="${args%%|*}"
if [[ "$args" =~ (^|[[:space:]])(--head([=[:space:]]|$)|-[A-Za-z]*H) ]]; then
  echo "钩子只核对当前工作区的 HEAD：请在该分支自己的 worktree 里运行 gh pr create，不要用 --head/-H。" >&2
  exit 2
fi
cd "$cwd" 2>/dev/null || exit 0
git rev-parse --show-toplevel >/dev/null 2>&1 || exit 0
head="$(git rev-parse HEAD 2>/dev/null)" || exit 0
marker="$(git rev-parse --git-path agentic-review-passed 2>/dev/null)"
if [ -f "$marker" ] && [ "$(cat "$marker")" = "$head" ]; then
  exit 0
fi
echo "当前 HEAD ($head) 没有本地 review 通过记录。先按 personal-control 的 pr-ready-gate「本地评审循环」跑 review，无 🔴 后运行它的 scripts/mark-review-passed.sh，再创建 PR。" >&2
exit 2
