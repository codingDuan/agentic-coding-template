#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scope="$script_dir/test-critical-scope.sh"
tmp_root=$(mktemp -d)
trap 'rm -rf -- "$tmp_root"' EXIT

new_repo() {
  local repo="$tmp_root/$1"
  git init -q "$repo"
  git -C "$repo" config user.email scope@example.invalid
  git -C "$repo" config user.name scope-test
  mkdir -p "$repo/apps/api" "$repo/docs"
  printf 'x = 1\n' > "$repo/apps/api/a.py"
  printf 'a\n' > "$repo/docs/a.md"
  git -C "$repo" add -A
  git -C "$repo" commit -qm base
  printf '%s\n' "$repo"
}

# expect <repo> <exit code> <output fragment>
expect() {
  local repo=$1 code=$2 fragment=$3 base actual_code output
  base=$(git -C "$repo" rev-list --max-parents=0 HEAD)
  set +e
  output=$(cd "$repo" && bash "$scope" "$base" 2>&1)
  actual_code=$?
  set -e
  if [[ "$actual_code" != "$code" ]] || [[ "$output" != *"$fragment"* ]]; then
    printf 'repo %s: expected exit %s with "%s", got %s:\n%s\n' \
      "$repo" "$code" "$fragment" "$actual_code" "$output" >&2
    exit 1
  fi
}

commit_all() { git -C "$1" add -A && git -C "$1" commit -qm "$2"; }

# 只改 doc / skill / client：不需要
repo=$(new_repo exempt)
mkdir -p "$repo/apps/web/src" "$repo/skills/x"
printf 'b\n' > "$repo/docs/b.md"
printf 's\n' > "$repo/skills/x/SKILL.md"
printf 'export {};\n' > "$repo/apps/web/src/a.tsx"
commit_all "$repo" exempt
expect "$repo" 0 "NOT REQUIRED"
expect "$repo" 0 $'client  apps/web/src/a.tsx'

# 已提交的 runtime 改动：需要
repo=$(new_repo committed)
printf 'x = 2\n' > "$repo/apps/api/a.py"
commit_all "$repo" api
expect "$repo" 1 $'runtime apps/api/a.py'

# 未提交的 runtime 改动：需要
repo=$(new_repo uncommitted)
printf 'x = 3\n' > "$repo/apps/api/a.py"
expect "$repo" 1 "REQUIRED"

# 未跟踪的 runtime 文件：需要（git diff 看不到，靠 ls-files --others）
repo=$(new_repo untracked)
mkdir -p "$repo/libs"
printf 'y = 1\n' > "$repo/libs/new.py"
expect "$repo" 1 $'runtime libs/new.py'

# 把 runtime 文件挪进 docs/：源路径也要算
repo=$(new_repo rename)
git -C "$repo" mv apps/api/a.py docs/a.py
commit_all "$repo" move
expect "$repo" 1 $'runtime apps/api/a.py'

# 没有改动：不需要
repo=$(new_repo unchanged)
expect "$repo" 0 "NOT REQUIRED"

# 无法解析的 ref：退出码 2
repo=$(new_repo badref)
set +e
(cd "$repo" && bash "$scope" no-such-ref >/dev/null 2>&1)
code=$?
set -e
test "$code" = 2 || { echo "bad ref must exit 2, got $code" >&2; exit 1; }

# 沿用的 SINCE 不是 HEAD 的祖先（全绿后又回退了 runtime 提交）：不能放行，退出码 2
repo=$(new_repo descendant)
printf 'x = 4\n' > "$repo/apps/api/a.py"
commit_all "$repo" api
green=$(git -C "$repo" rev-parse HEAD)
git -C "$repo" reset -q --hard HEAD~1
set +e
(cd "$repo" && bash "$scope" "$green" >/dev/null 2>&1)
code=$?
set -e
test "$code" = 2 || { echo "non-ancestor SINCE must exit 2, got $code" >&2; exit 1; }

# 分类器失败：不能放行，退出码 2
repo=$(new_repo noclassifier)
lonely="$tmp_root/lonely"
mkdir -p "$lonely"
cp "$scope" "$lonely/test-critical-scope.sh"
base=$(git -C "$repo" rev-list --max-parents=0 HEAD)
set +e
(cd "$repo" && bash "$lonely/test-critical-scope.sh" "$base" >/dev/null 2>&1)
code=$?
set -e
test "$code" = 2 || { echo "classifier failure must exit 2, got $code" >&2; exit 1; }

# 在子目录里运行：仍然看到仓库根下的未跟踪文件
repo=$(new_repo subdir)
mkdir -p "$repo/libs"
printf 'y = 1\n' > "$repo/libs/new.py"
base=$(git -C "$repo" rev-list --max-parents=0 HEAD)
set +e
output=$(cd "$repo/docs" && bash "$scope" "$base" 2>&1)
code=$?
set -e
if [[ "$code" != 1 ]] || [[ "$output" != *"runtime libs/new.py"* ]]; then
  printf 'subdir run must see libs/new.py, got %s:\n%s\n' "$code" "$output" >&2
  exit 1
fi
