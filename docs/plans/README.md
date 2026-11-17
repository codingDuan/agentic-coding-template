# 计划文档

> 计划文档按业务领域组织；当前事实以代码和编号核心文档为准。本目录只承载仍需设计、实施、上线观察或具有独立历史价值的材料。

## 领域入口

| 领域 | 入口 |
|---|---|
| {{DOMAIN_NAME}} | [{{domain-slug}}](./{{domain-slug}}/README.md) |

## 目录约定

```
docs/plans/
├── README.md                     # 本页：领域入口
└── <domain>/
    ├── README.md                 # 领域 README：列出主题
    └── <topic>/
        ├── README.md             # 主题入口：当前状态 + 阅读顺序
        ├── 01-<name>-design.md   # 主文档（决策、图、兼容性、上线）
        ├── 02-task1-<name>.md    # 子任务文档（完整代码、命令、预期输出）
        └── ...
```

## 阅读规则

1. 先读领域 README，再读主题 README；主题细节按需进入 design、implementation 和 task 文件。
2. 目录名使用业务领域和功能主题，不使用日期；日期、PR 和提交只保留在正文元数据中。
3. 已落地的长期事实必须进入 `docs/NN-*.md`、`docs/api-contract/**`、`docs/agents/**` 或模块 README；计划不复制第二份规范。
4. 同一主题只有一个当前入口。跨领域内容选择拥有核心业务状态的领域作为主入口，其他位置只链接。
5. `_archive/` 仅保留不可从当前代码还原的架构决策、不可逆迁移、上线/回滚手册或事故防复发约束；其余历史依赖 Git 追溯。

## 维护

整理流程与可重复检查见 `skills/organizing-plans`。新增计划时先选择领域和主题，再创建入口 README。
