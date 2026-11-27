#!/usr/bin/env bash
# 记录当前 HEAD 已通过本地 review（无 🔴）。只在 pr-ready-gate「本地评审循环」结束且无阻塞项时，
# 在仓库 worktree 里运行。记录放在 git 目录内，不进提交；worktree 各有各的记录。
# hooks/require-local-review.sh 据此放行 gh pr create。
set -euo pipefail
marker="$(git rev-parse --git-path agentic-review-passed)"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "工作区有未提交的已跟踪改动；先提交再记录 review 结果。" >&2
  exit 1
fi
git rev-parse HEAD > "$marker"
echo "已记录本地 review 通过: $(cat "$marker")"
