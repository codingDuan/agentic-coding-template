#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
classifier="$script_dir/classify-ci-scope.sh"
tmp_file=$(mktemp)
trap 'rm -f "$tmp_file"' EXIT

assert_scope() {
  local expected=$1
  shift
  printf '%s\0' "$@" > "$tmp_file"
  actual=$(bash "$classifier" < "$tmp_file")
  if [[ "$actual" != "$expected" ]]; then
    echo "expected scope $expected, got $actual for: $*" >&2
    exit 1
  fi
}

assert_scope true docs/09-test-guide.md docs/plans/governance/daily-pr-lessons/01-design.md
assert_scope true README.md CLAUDE.md REVIEW.md RULES.md CONTEXT.md CHANGELOG.md LICENSE
# 运行时 Markdown（应用读取的产品内容）不是文档
assert_scope false apps/api/content/chapter.md
assert_scope false apps/web/README.md
assert_scope false docs/09-test-guide.md apps/api/content/chapter.md

assert_paths() {
  local expected=$1
  shift
  printf '%s\0' "$@" > "$tmp_file"
  actual=$(bash "$classifier" --paths < "$tmp_file")
  if [[ "$actual" != "$expected" ]]; then
    printf 'expected:\n%s\ngot:\n%s\n' "$expected" "$actual" >&2
    exit 1
  fi
}

assert_paths $'doc\tdocs/a.md\ndoc\tAGENTS.md\nskill\tskills/x/SKILL.md' \
  docs/a.md AGENTS.md skills/x/SKILL.md
# 客户端目录随 classify-ci-scope.sh 的 client 行一起改写
assert_paths $'client\tapps/web/src/a.tsx\nclient\tapps/miniprogram/a.ts\nclient\tapps/mobile/a.json' \
  apps/web/src/a.tsx apps/miniprogram/a.ts apps/mobile/a.json
assert_paths $'runtime\tapps/api/a.py\nruntime\tMakefile\nruntime\tconfig/new/x.yaml\nruntime\tapps/webhooks/a.py\nruntime\tapps/api/content/c.md' \
  apps/api/a.py Makefile config/new/x.yaml apps/webhooks/a.py apps/api/content/c.md

# --paths 允许空输入（没有改动 = 不需要跑）；默认模式仍然 fail closed（见下）
: > "$tmp_file"
test -z "$(bash "$classifier" --paths < "$tmp_file")"

# 默认模式（CI docs_only）语义不变：skill 与 client 仍然不算 docs-only
assert_scope false skills/x/SKILL.md
assert_scope false apps/web/src/a.tsx

if bash "$classifier" --bogus < /dev/null 2>/dev/null; then
  echo "unknown option must fail" >&2
  exit 1
fi

: > "$tmp_file"
if bash "$classifier" < "$tmp_file"; then
  echo "empty input must fail closed" >&2
  exit 1
fi
