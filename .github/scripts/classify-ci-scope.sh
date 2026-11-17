#!/usr/bin/env bash
# 变更路径分类的唯一来源（RULES.md §8）。stdin：NUL 分隔的路径。
#   默认：输出 docs_only（true/false）；全部路径都是 doc 时为 true；空输入 fail closed。
#   --paths：逐行输出 "<class>\t<path>"，make test-critical-scope 据此判断是否需要 make test-critical。
# 类别：doc（文档）、skill（skills/**）、client（客户端代码，目录按项目改写下面的 case 行）、runtime（其他一切，含新目录）。
set -euo pipefail

classify() {
  case "$1" in
    docs/*|README.md|CLAUDE.md|AGENTS.md|REVIEW.md|RULES.md|CONTEXT.md|CHANGELOG.md|LICENSE) echo doc ;;
    skills/*) echo skill ;;
    apps/web/*|apps/mobile/*|apps/miniprogram/*) echo client ;;  # 按项目的客户端目录改写
    *) echo runtime ;;
  esac
}

mode=${1:-}
case "$mode" in
  ''|--paths) ;;
  *) echo "usage: classify-ci-scope.sh [--paths] < NUL-separated paths" >&2; exit 2 ;;
esac

docs_only=true
changed_count=0
while IFS= read -r -d '' path; do
  changed_count=$((changed_count + 1))
  class=$(classify "$path")
  [[ "$class" == doc ]] || docs_only=false
  if [[ "$mode" == --paths ]]; then
    printf '%s\t%s\n' "$class" "$path"
  fi
done

if [[ "$mode" == --paths ]]; then
  exit 0
fi
test "$changed_count" -gt 0
printf '%s\n' "$docs_only"
