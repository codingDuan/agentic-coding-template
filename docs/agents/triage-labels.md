# Triage 标签

技能用五个 canonical triage 角色说话。按本仓库实际存在的标签填写映射；没有对应标签的角色降级为评论。

| Canonical 角色 | 本仓库对应 | 怎么做 |
|---|---|---|
| `ready-for-agent` | `{{LABEL_READY}}` | 仅当 issue 已完整到可无人值守执行时使用 |
| `wontfix` | `wontfix` | 可用 |
| `needs-triage` / `needs-info` / `ready-for-human` | 无对应标签 | 不打标，把原因写进 issue 评论 |

## 硬性约束

1. **打标前先确认标签存在**：`gh label list --json name --jq '.[].name'`。
   `gh issue edit --add-label` 遇到不存在的标签会**整条命令失败**，不是跳过。
2. **不要创建新标签。** 标签体系是人的工作流，不是 agent 的暂存空间。
3. **无标签是正常状态**，不要为了「补全 triage」批量给存量 issue 打标。

本文件的价值在于描述现实：一份声称角色可用、实际标签不存在的映射表比没有映射表更糟。
