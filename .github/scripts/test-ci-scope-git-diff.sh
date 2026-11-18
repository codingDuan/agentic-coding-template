#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
classifier="$script_dir/classify-ci-scope.sh"
tmp_root=$(mktemp -d)
trap 'rm -rf -- "$tmp_root"' EXIT

assert_rename_scope() {
  local name=$1
  local expected=$2
  local source_path=$3
  local target_path=$4
  local repo="$tmp_root/$name"

  git init -q "$repo"
  git -C "$repo" config user.email ci-scope@example.invalid
  git -C "$repo" config user.name ci-scope-test
  mkdir -p "$repo/$(dirname -- "$source_path")"
  printf 'scope test\n' > "$repo/$source_path"
  git -C "$repo" add .
  git -C "$repo" commit -qm base
  base_sha=$(git -C "$repo" rev-parse HEAD)

  mkdir -p "$repo/$(dirname -- "$target_path")"
  mv "$repo/$source_path" "$repo/$target_path"
  git -C "$repo" add -A
  git -C "$repo" commit -qm rename
  head_sha=$(git -C "$repo" rev-parse HEAD)

  changed_files="$repo/changed-files"
  git -C "$repo" diff --no-renames --name-only -z "$base_sha" "$head_sha" > "$changed_files"
  actual=$(bash "$classifier" < "$changed_files")
  if [[ "$actual" != "$expected" ]]; then
    echo "expected scope $expected, got $actual for rename $source_path -> $target_path" >&2
    exit 1
  fi
}

assert_rename_scope runtime_to_docs false apps/api/runtime.md docs/runtime.md
assert_rename_scope docs_to_docs true docs/old.md docs/new.md
assert_rename_scope docs_to_runtime false docs/runtime.md apps/api/runtime.md
