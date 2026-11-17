#!/usr/bin/env bash
# Initialize a repository created from this template.
# Usage: bash bootstrap.sh --name "My Project" --slug my-project --repo owner/my-project [--with-personal] [--skip-plugins]
set -euo pipefail
cd "$(dirname "$0")"

name="" slug="" repo="" with_personal=0 skip_plugins=0
while [ $# -gt 0 ]; do
  case "$1" in
    --name) name="$2"; shift 2 ;;
    --slug) slug="$2"; shift 2 ;;
    --repo) repo="$2"; shift 2 ;;
    --with-personal) with_personal=1; shift ;;
    --skip-plugins) skip_plugins=1; shift ;;
    -h|--help) sed -n 2,3p "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$name" ] || read -r -p "Project name (e.g. My Project): " name
[ -n "$slug" ] || read -r -p "Project slug (e.g. my-project): " slug
[ -n "$repo" ] || read -r -p "GitHub repo (owner/name): " repo

echo "== 1/4 Fill core placeholders"
files=$(git ls-files 2>/dev/null || find . -type f -not -path './.git/*')
for f in $files; do
  case "$f" in bootstrap.sh|*.png|*.jpg) continue ;; esac
  [ -f "$f" ] || continue
  if grep -q '{{PROJECT_NAME}}\|{{PROJECT_SLUG}}\|{{GITHUB_REPO}}' "$f"; then
    NAME="$name" SLUG="$slug" REPO="$repo" python3 - "$f" <<'PY'
import os, sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
for k, v in (("{{PROJECT_NAME}}", os.environ["NAME"]), ("{{PROJECT_SLUG}}", os.environ["SLUG"]), ("{{GITHUB_REPO}}", os.environ["REPO"])):
    t = t.replace(k, v)
p.write_text(t)
PY
    echo "  filled $f"
  fi
done

echo "== 2/4 Install project skills into .claude/skills and .codex/skills"
bash scripts/install-skills.sh

echo "== 3/4 Third-party plugins (plugins.txt)"
if [ "$skip_plugins" -eq 1 ]; then
  echo "  skipped (--skip-plugins)"
elif ! command -v claude >/dev/null 2>&1; then
  echo "  claude CLI not found; install these manually:"
  grep -v '^#' plugins.txt | awk -F'\t' 'NF>=2 {print "    claude plugin marketplace add " $1 " && claude plugin install " $2 "   # " $3}'
else
  grep -v '^#' plugins.txt | while IFS=$'\t' read -r source plugin need why; do
    [ -n "$plugin" ] || continue
    echo "  [$need] $plugin"
    claude plugin marketplace add "$source" >/dev/null 2>&1 || true
    if ! claude plugin install "$plugin" </dev/null; then
      echo "    install failed; run manually: claude plugin install $plugin" >&2
      [ "$need" = required ] && echo "    (required by project skills — see docs/agents/skill-dependencies.md)" >&2
    fi
  done
fi

echo "== 4/4 Personal layer"
if [ "$with_personal" -eq 1 ]; then
  bash personal/install-personal.sh
else
  echo "  skipped (pass --with-personal to install the owner-only gates and hook)"
fi

echo
echo "Remaining placeholders to fill by hand:"
grep -rn --exclude-dir=.git --exclude-dir=.claude --exclude-dir=.codex --exclude=bootstrap.sh '{{[A-Z_]*}}' . | cut -c1-120 || echo "  none"
echo
echo "Done. Start a new Claude Code / Codex session so the skills load."
