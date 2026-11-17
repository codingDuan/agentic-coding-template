# API 契约总览

> 模板骨架：通用约定写在这里，各模块细节放 `docs/api-contract/<module>.md`。
> 改契约前遵守 `RULES.md` §2、§3（排查全部消费方、对所有客户端兼容）。

## 通用约定

- 认证：{{AUTH_SCHEME}}
- 错误格式：{{ERROR_SHAPE}}
- 分页 / 排序：{{PAGING}}
- 版本与兼容：新增字段优先；删除或改语义必须给过渡方案与移除条件。

## 模块索引

| 模块 | 文档 |
|---|---|
| {{MODULE}} | `docs/api-contract/{{module}}.md` |
