# personal-control：个人理解关卡

这是一个**个人 overlay**：只对自愿使用的人生效，不是团队流程。仓库里的 `writing-plans`、
`executing-plans`、`pr-ready` 是所有贡献者都要遵守的共享规则；本包在每个阶段之后**追加**一道个人关卡，
不改共享 skill，也不能豁免共享要求。

`scripts/install-skills.sh` 不会安装本目录。要用的人自己复制到个人 skill 目录（见下文「安装」）。

## 三道 gate

| 阶段 | 共享 skill | 个人 gate | 追加了什么 |
|---|---|---|---|
| 计划 | `writing-plans` | [`planning-gate`](references/planning-gate.md) | 主文档加 `风险等级` 和 §0 决策卡（关键决策、掌控分级、可能让你意外的地方、确认记录），§13 前加 `## 个人模拟飞行` 占位；高风险计划实施前讲回，按具体问法出题、按轮次表记录 |
| 实施 | `executing-plans` | [`execution-gate`](references/execution-gate.md) | 开工前检查讲回记录；关键决策变更时暂停，只对变更项重新讲回；逐项核对「交给验证兜底」的检查确实存在并跑绿 |
| PR | `pr-ready` | [`pr-ready-gate`](references/pr-ready-gate.md) | 高风险计划先做模拟飞行（数据流 + 注入故障，答对且有测试覆盖才算过）；然后每个 PR 跑本地评审循环直到没有 🔴，用脚本记下 HEAD，hook 拦住不匹配的 `gh pr create` |

「高风险」只按仓库的 [`docs/agents/high-risk.md`](../high-risk.md) 判定，本包不另写清单。讲回和模拟飞行
只对高风险计划做；非高风险计划在 `确认记录` 和 `## 个人模拟飞行` 里写 `不适用：<理由>`。§0 决策卡和
本地评审循环对每个计划和每个 PR 都适用。

几条设计约束：

- **gate 只加门槛，不豁免共享要求。** 测试、评审、兼容性、上线规则照常执行。
- **gate 不占共享计划的章节编号。** 个人模拟飞行用不带编号的固定标题插在 `## 13. 子任务详情` 前，
  所以共享 `writing-plans` 改模板时，`## 1.` 和 `## 13. 子任务详情` 这两个标题就是本包依赖的接口。
- **不要求别人通过你的关卡。** 合作者、评审者不做讲回和模拟飞行。
- 合并后的学习仍然只走仓库的 `pr-lessons`，本包不另建复盘流程。

## 安装

下面用 `<you>` 表示你的命名空间（例如名字缩写），`<REPO_PATH>` 表示仓库的绝对路径。

1. **复制到个人目录并改名**，避免和项目 skill 或别人的副本重名：

   ```bash
   cp -R <REPO_PATH>/docs/agents/personal-control ~/.agents/skills/<you>-personal-control
   ln -s ~/.agents/skills/<you>-personal-control ~/.claude/skills/<you>-personal-control
   ```

   Codex 读 `~/.agents/skills/`，Claude Code 读 `~/.claude/skills/`，软链让两边用同一份。

2. **替换占位符**：把副本里 `SKILL.md` 的 `name: personal-control` 改成 `<you>-personal-control`
   （要和目录名一致），再把 `SKILL.md`、`references/pr-ready-gate.md`、`hooks/require-local-review.sh`
   里的 `<REPO_PATH>` 换成仓库的绝对路径。

3. **在用户级指令里写加载规则**。这一步不能省：只靠 skill 的 description，模型经常不会在使用共享
   skill 时顺带加载 overlay。在 `~/.claude/CLAUDE.md`（Codex 写在 `~/.codex/AGENTS.md`）里加：

   ```markdown
   When working anywhere under `<REPO_PATH>`, always load and apply `<you>-personal-control`
   together with the repository's `writing-plans`, `executing-plans`, and `pr-ready` skills.
   The personal skill is an additive profile; repository rules remain in force.
   Do not require partners or other contributors to pass its personal gates.
   ```

4. **注册 hook**（只有 Claude Code 支持）。在 `~/.claude/settings.json` 的 `hooks` 里加：

   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash",
           "hooks": [
             {
               "type": "command",
               "command": "bash ~/.agents/skills/<you>-personal-control/hooks/require-local-review.sh",
               "if": "Bash(gh pr create*)",
               "timeout": 10
             }
           ]
         }
       ]
     }
   }
   ```

   hook 需要 `jq`。它只在 `<REPO_PATH>` 及其子目录（包括 `.worktrees/*`）里生效；没替换
   `<REPO_PATH>` 时，任何目录下的 `gh pr create` 都会被拦，并提示去配置。也可以不改脚本，
   改为设置环境变量 `PERSONAL_CONTROL_REPO=<REPO_PATH>`。

5. 新开一个会话，变更才会生效。

## 维护

- 建议把个人目录 `git init`，每个可用版本打一个 tag，方便回退和对比。
- 仓库版本的变更会写在这里。要同步时，拿副本和仓库版 diff，手工合并；注意别覆盖你替换过的占位符。
- `.github/scripts/test-require-local-review.sh` 用仓库版本测试 hook 和记录脚本，由 `make test-workflow` 运行。
