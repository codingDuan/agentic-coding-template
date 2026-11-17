# Skill 外部依赖：superpowers

仓库 `skills/` 里的项目 skill 引用了 [superpowers](https://github.com/obra/superpowers) 插件的若干 skill。
没装插件时，这些引用会失效：项目 skill 自身的规则仍然有效，但被委托出去的那一段流程不会执行。

## 被引用的 skill

| superpowers skill | 引用方 | 用途 |
|---|---|---|
| `subagent-driven-development` | `writing-plans`、`executing-plans` | 计划的推荐执行方式：每个任务一个新子代理 |
| `verification-before-completion` | `executing-plans` Step 4 | 宣布完成前必须有新鲜的验证证据 |
| `finishing-a-development-branch` | `executing-plans` | 实现完成后的合并 / PR 收尾 |
| `using-git-worktrees` | `executing-plans` | 开工前建隔离工作区 |

新增引用时同步更新本表。

## 同名 skill：项目版与插件版不是一回事

superpowers 自带 `writing-plans` 和 `executing-plans`，与本仓库的同名 skill **内容不同**：
项目版承载了 `RULES.md` 合规检查、计划目录规范、上线八维度、`make test-critical` 等项目规则，
插件版没有。

- **Claude Code**：插件 skill 带命名空间（`superpowers:executing-plans`），与项目的
  `executing-plans` 同时出现在列表里，**不会互相覆盖**。引用哪一个，完全取决于写的是哪个名字。
- **Codex**：superpowers 以 `~/.agents/skills/superpowers/` 方式安装，skill 名不带前缀，
  与 `.codex/skills/` 里的项目版**同名**。两者冲突时加载哪一个未经验证。

因此项目 skill 之间互相引用时**一律写裸名**（`executing-plans`），
只有确实要用插件版能力时才写 `superpowers:` 前缀。

## 安装

第三方插件统一登记在仓库根目录 `plugins.txt`，`bash bootstrap.sh` 会按清单安装；新增依赖时同时更新 `plugins.txt` 和本文。


- Claude Code：`/plugin install superpowers@claude-plugins-official`
- Codex：按 superpowers 仓库 README 的 Codex 安装说明（克隆到 `~/.codex/superpowers`，
  并把 `skills/` 链接到 `~/.agents/skills/superpowers`）
