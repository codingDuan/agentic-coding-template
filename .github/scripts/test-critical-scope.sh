#!/usr/bin/env bash
# 判断 make test-critical 是否需要跑（RULES.md §8）。路径分类只认 classify-ci-scope.sh。
# 用法：test-critical-scope.sh [SINCE]
#   不传：对比 merge-base(origin/main, HEAD)，判断整个分支。
#   传 SINCE（上次全绿的提交）：SINCE 必须是 HEAD 的祖先，否则报错——它之后若有提交被回退，
#   当前树就没被测过，不能沿用。
# 范围：工作区对比基准提交，含未提交与未跟踪文件，重命名两端都算。
# 退出码：0 不需要，1 需要，2 参数、git 或分类器错误（任何错误都不给"不需要"）。
set -uo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if ! top=$(git rev-parse --show-toplevel 2>/dev/null); then
  echo "error: not inside a git repository" >&2
  exit 2
fi
# ls-files --others 只列当前目录以下，必须在仓库根执行
cd "$top" || exit 2

if [[ $# -ge 1 ]]; then
  since=$1
  if ! base=$(git rev-parse --verify --quiet "$since^{commit}"); then
    echo "error: cannot resolve '$since'" >&2
    exit 2
  fi
  if ! git merge-base --is-ancestor "$base" HEAD; then
    echo "error: '$since' is not an ancestor of HEAD; the current tree was not tested at that commit" >&2
    exit 2
  fi
else
  since=origin/main
  if ! base=$(git merge-base "$since" HEAD 2>/dev/null); then
    echo "error: cannot resolve merge-base of '$since' and HEAD" >&2
    exit 2
  fi
fi

paths_file=$(mktemp)
trap 'rm -f -- "$paths_file"' EXIT
# 未跟踪文件不在 git diff 里，必须单独列出
if ! { git diff --no-renames --name-only -z "$base" && git ls-files -z --others --exclude-standard; } > "$paths_file"; then
  echo "error: git failed while listing changed paths" >&2
  exit 2
fi

if ! classified=$(bash "$script_dir/classify-ci-scope.sh" --paths < "$paths_file"); then
  echo "error: classify-ci-scope.sh failed" >&2
  exit 2
fi
listing=$(printf '%s\n' "$classified" | sort -u)

short=${base:0:8}
echo "test-critical scope since $short ($since):"
total=0
runtime=0
while IFS=$'\t' read -r class path; do
  [[ -n "$class" ]] || continue
  total=$((total + 1))
  printf '  %-7s %s\n' "$class" "$path"
  [[ "$class" != runtime ]] || runtime=$((runtime + 1))
done <<< "$listing"

if [[ "$runtime" -gt 0 ]]; then
  echo "RESULT: REQUIRED — $runtime runtime path(s) changed since $short; run \`make test-critical\`"
  exit 1
fi
echo "RESULT: NOT REQUIRED — none of $total path(s) since $short is runtime; paste this output into the PR verification result"
exit 0
