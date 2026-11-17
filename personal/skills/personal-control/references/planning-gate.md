# Personal planning gate

After the shared `writing-plans` skill has produced the main plan and task documents, add a compact
`## 0. 决策卡` to the main plan before asking for confirmation.

It contains:

1. `关键决策`: 3–5 consequential choices, each with the rejected alternative and cost of being wrong.
2. `掌控分级`: `必须人理解` for data models, money, permissions, irreversible operations,
   external contracts, and state machines; `交给验证兜底` for other items, each naming a concrete
   executable check.
3. `可能让你意外的地方`: behavior changes, semantic drift, deferred scope, or constraints that
   forced the design.
4. `确认记录`: initially empty.

Also insert an unnumbered `## 个人模拟飞行` section immediately before the shared
`## 13. 子任务详情` section. Keep the shared section number unchanged. This stable heading is the
only location for the personal simulated-flight record; low-risk plans write `不适用` with a reason.

## Explain-back

Before implementation:

1. Point the owner to §0 and the exact sections referenced by its decisions and `必须人理解` items.
   Offer Plannotator if available; chat is sufficient otherwise.
2. Ask the owner to explain each decision and `必须人理解` item in their own words: what was chosen,
   why, and what breaks if it is wrong. Do not quote the answer in the question.
3. If an answer is incomplete, explain the mismatch and ask a different question about the same
   mechanism. Do not accept a sign-off in place of understanding at this stage.
4. Record the result in `确认记录` using the round table below, including any changed plan sections
   and re-asked items.

### `确认记录` format

Every explain-back, including a later re-explain after a decision change, appends rows to one table.
Do not write the record as prose or bullets.

```markdown
| 日期 | 触发 | 轮次 | 题 | owner 回答要点 | 结果 | 处理 |
|---|---|---|---|---|---|---|
| 2026-10-27 | 首次 | 1 | D2 拦截条件 | … | ✅ | — |
| 2026-10-27 | 首次 | 1 | D3 泄露面 | … | ❌ | 解释凭证与裸地址区别，换问法 |
| 2026-10-27 | 首次 | 2 | D3′ 转发 play_url 的后果 | … | ✅ | — |
| 2026-10-28 | 决策变更：D3 | 1 | D3 鉴权边界 | … | ✅ | 改 §10 第 4 项 |

结论：首次 2 轮通过；决策变更 1 轮通过。可以开始实施。
```

- `触发` is `首次`, `决策变更：<item>`, or `评审纠偏：<source>`. Round numbers restart at 1 for each
  trigger.
- One row per question per round. A re-asked question keeps its ID with a prime (`D3′`, `D3″`) and
  names the new angle.
- `结果` is `✅`, `❌`, or `⚠️` (conclusion right, mechanism wrong; counts as not passed).
- `处理` names the explanation given, the changed plan section, or `—`.
- End each trigger with a `结论` line that states the number of rounds to pass.

Implementation starts only after the current §0 is explained correctly. If a consequential decision
changes later, the previous answer does not cover it: update the plan and repeat this gate only for
the changed items.
