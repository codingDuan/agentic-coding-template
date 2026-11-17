## 每日 PR 复盘（滚动 PR）

由 `{{LESSONS_WORKFLOW_REPO}}` 上的 `Daily PR Lessons` workflow 维护：每天 09:30 复盘前一天合入 main 的 PR，
每周一 10:30 做 fold。每次运行追加一个 commit，并 rebase 到最新的 main。

- **合并 = 确认**本 PR 里的全部教训和沉淀；main 上的水位随之前移。
- **关闭不合并 = 拒绝**；下一次运行会从 main 上的旧水位重新复盘这批 PR。
- 如果 diff 里有 `RULES.md`，那是 review 的 🔴 依据，请逐条确认后再合并。

机制见 `skills/pr-lessons/SKILL.md`，设计见 `docs/plans/governance/daily-pr-lessons/01-design.md`。
本 PR 只改文档，按 CLAUDE.md 测试约定属于非运行时路径，无需 `make test-critical`。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
