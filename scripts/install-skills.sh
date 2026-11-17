#!/usr/bin/env bash
# -------------------------------------------------------
# 安装项目自定义 skill 到 .claude/skills/ 和 .codex/skills/ 目录
# 用法: bash scripts/install-skills.sh
# -------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
SKILLS_DSTS=(
    "$REPO_ROOT/.claude/skills"
    "$REPO_ROOT/.codex/skills"
)

if [ ! -d "$SKILLS_SRC" ]; then
    echo "ERROR: 找不到 skill 源目录: $SKILLS_SRC"
    exit 1
fi

for skills_dst in "${SKILLS_DSTS[@]}"; do
    mkdir -p "$skills_dst"

    case "$skills_dst" in
        */.claude/skills) platform_name="Claude Code" ;;
        */.codex/skills) platform_name="Codex" ;;
    esac

    echo "安装到 $platform_name ($skills_dst):"
    for skill_dir in "$SKILLS_SRC"/*/; do
        skill_name=$(basename "$skill_dir")
        dst="$skills_dst/$skill_name"

        if [ -d "$dst" ]; then
            echo "  更新 $skill_name"
            rm -rf "$dst"
        else
            echo "  安装 $skill_name"
        fi

        cp -r "$skill_dir" "$dst"
    done
    echo ""
done

echo "重启 Claude Code 和 Codex 会话后生效。"
