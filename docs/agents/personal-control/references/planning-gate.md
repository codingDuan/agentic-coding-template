# Personal planning gate

After the shared `writing-plans` skill has produced the main plan and task documents, add these to
the main plan before asking for confirmation.

In the header block, add a risk line classified against `docs/agents/high-risk.md`:

```markdown
> 风险等级: 高风险（<命中 docs/agents/high-risk.md 的哪一条>） | 非高风险（<理由>）
```

When unsure, classify as high-risk and give the reason in §0.

Then add a compact `## 0. 决策卡` before `## 1.`. It contains:

1. `关键决策`: 3–5 consequential choices, each with the rejected alternative and cost of being wrong.
2. `掌控分级`: `必须人理解` for data models, money, permissions, irreversible operations,
   external contracts, and state machines; `交给验证兜底` for other items, each naming a concrete
   executable check (test name, contract, invariant, type check, or alert).
3. `可能让你意外的地方`: behavior changes, semantic drift, deferred scope, or constraints that
   forced the design.
4. `确认记录`: initially empty. A non-high-risk plan writes `不适用：<理由>`.

```markdown
## 0. 决策卡

### 关键决策
| 编号 | 决策 | 选择 | 否决的方案 | 选错的代价 | 关联章节 |
|---|---|---|---|---|---|

### 掌控分级
| 必须人理解 | 关联章节 | 交给验证兜底 | 具体检查 |
|---|---|---|---|

### 可能让你意外的地方

### 确认记录
```

Each decision and each `必须人理解` item has a `关联章节` entry. The entry points to where the plan
explains the mechanism: a numbered subsection, a named diagram, or a Task, for example
`§4.2 时序图第 3 步、Task 2`. A summary section alone, such as `§2`, is not enough. The pointer
is too abstract if every row would have the same entry. Write the pointer before you ask for
confirmation. If no section explains the mechanism of an item, that is a plan defect: add the
section first.

Also insert an unnumbered `## 个人模拟飞行` section immediately before the shared
`## 13. 子任务详情` section. Keep the shared section number unchanged. This stable heading is the
only location for the personal simulated-flight record; non-high-risk plans write
`不适用：<理由>`. The PR-ready gate later adds a `### 本地评审记录` subsection immediately before it.

## Explain-back

Run the explain-back only for a high-risk plan. For other plans, `确认记录` stays
`不适用：<理由>`; the plan confirmation is enough.

Before implementing a high-risk plan:

1. Point the owner to §0 and to the `关联章节` of each decision and `必须人理解` item.
   Offer Plannotator if available; chat is sufficient otherwise.
2. Ask about each decision and `必须人理解` item with a concrete question (see
   [Concrete questions](#concrete-questions)). The owner must be able to answer what was chosen,
   why, and what breaks if it is wrong, but the question asks for a prediction about one case. Do not
   quote the answer in the question.
3. If an answer is incomplete, explain the mismatch and ask a different concrete case about the same
   mechanism. Do not accept a sign-off in place of understanding at this stage.
4. Record the result in `确认记录` using the round table below, including any changed plan sections
   and re-asked items.

Re-explain only the affected items when:

- a §0 decision, risk boundary, or `掌控分级` item changes during implementation (trigger
  `决策变更：<item>`, see the execution gate);
- a review shows that the owner misunderstands a mechanism (trigger `评审纠偏：<source>`).

### Concrete questions

These rules apply to the explain-back here and to the simulated flight in the PR-ready gate.
A question is too abstract if you could ask it about another plan without changing it. Questions
such as "解释 D2", "事实源是什么", "数据怎么流转", or "错了会怎样" are too abstract: a recitation
of Claude's explanation answers them, so they do not show understanding.

Each question contains three parts:

1. **Trigger**: one actor, one business action, and real input values, described the way the owner
   meets them: 用户 1001 在 15:01 打开产品 42 的信号页; 同一笔支付回调第二次到达; 每日调仓任务在
   15:30 和 15:31 各跑一次.
2. **State before**: the business facts that matter, written as values, for example
   「订阅有效，11-30 到期」. Leave out facts that do not matter.
3. **One prediction**: one observable outcome or one business decision. It can be what the user
   sees or receives, which state a business object ends in, which record becomes the source of
   truth, which component (migration, background job, API, page) acts first, or which business rule
   or guard stops the input.

Ask for a prediction ("之后 X 是什么状态"), not a description ("说说 X 怎么工作"). To test why a
choice was made, ask what the same input produces under the rejected alternative.

**Ask about logic, not code.** The owner cannot read all AI-written code, and the exercise tests
whether they understand the design, not whether they remember identifiers. Do not ask for function
names, field paths, column names, file locations, or exact error-code strings. Name business
objects, user-visible states, components, and rules in plain words; an enum value or status the
owner sees in a UI or a plan is fine. Claude still checks every answer key against the code and
tests, and the record's `实际行为` may cite code.

To re-ask, change one variable in the same case, such as an expired subscription, a repeated
callback, or an old client without the new field. That way the new answer tests the same mechanism.

Ask at most three numbered questions in one message. The simulated flight's four-step data-flow
trace counts as one question. In the record's `题` column, start with the format tag from
[Question formats](#question-formats), then write a short form of the case, such as
`[简答] D2 线索 L-88 成交后看板显示`.

| Abstract (too vague) | Code-level (do not ask) | Concrete |
|---|---|---|
| 解释 D2 为什么以跟进记录为事实源。 | 看板这一行读的是哪张表的哪个字段？ | 运营在侧边栏把线索 L-88 标为「已成交」，然后刷新收入看板。看板上这条线索显示成交了吗？如果用被否决的方案（看板读线索自身的状态），此刻显示什么？ |
| 说说支付回调的数据流。 | ① 哪个函数先收到；② 写了哪些字段。 | 订单 P-1 的支付回调首次到达，订单当时待支付。按顺序说：① 哪个环节先处理；② 它依据哪份事实判断，那份事实当时是什么状态；③ 处理完订单和订阅各是什么状态；④ 支付平台收到的是成功还是失败。 |
| 重复回调会怎样？ | 是哪个函数里的哪个 if 挡住的？ | 同一个回调 3 秒后又到了一次，此时订单已支付。用户会不会多出一份订阅？是哪条规则挡住的？ |

### Question formats

The format tests the answer. It does not set how hard the question is. A choice format checks
whether the owner can recognize an answer. The owner must produce the answer to show
understanding. The default format is therefore a short-answer prediction. Its answer is one state,
one outcome the user sees, one component, or one rule, so the owner does not type long text.

| 标签 | Format | Use it for | Requirements | Grading |
|---|---|---|---|---|
| `[简答]` | Short-answer prediction | The first explain-back round of each decision and `必须人理解` item; simulated-flight data flow and fault-question row values | Each part asks for one predicted state, user-visible outcome, component, or rule | ✅ / ⚠️ / ❌ |
| `[单选]` | Single choice plus a one-line reason | The rejected-alternative test, a path traced through a diagram, and the stopper of a simulated-flight fault question | 3–5 options. One option is `以上都不对` or `图上没有这条路径`. Distractors are outputs of the rejected alternative or nearby branches and states | Right option with a wrong reason is ⚠️ |
| `[判断]` | True/false plus a reason or a correction | A re-ask that changes one variable, and whether a state transition is legal | For "true", name the rule, guard, or transition that makes it true. For "false", give the correct state or path | Wrong judgment is ❌; right judgment with a wrong, missing, or generic reason or correction is ⚠️; right judgment with a concrete reason or correction is ✅ |
| `[多选]` | Select all that apply | Which events leave a state, and which rows exist at a failure moment | The exact set. The options include `都没有` | Any missing or extra option is ❌ |
| `[排序]` | Ordering | Sequence-diagram steps, especially callbacks that arrive out of order | 4–6 shuffled steps | Any step in the wrong place is ❌ |

Rules:

- **One ✅ row is not an item pass.** An item passes when, after its last ❌, ⚠️, or `不计` row,
  either one `[简答]`, `[排序]`, or `[判断]` row is ✅, or two ✅ rows use different formats and
  are variants of the same case with one variable changed. A single ✅ row of `[单选]` or `[多选]`
  does not pass the item.
- A `[判断]` row is ✅ only when the reason itself predicts the mechanism: it names the business
  rule, guard, state, or transition that decides the case (for "false", the correct state or path).
  This reason is what makes a single `[判断]` row enough. A bare "对/错", or a reason that only
  restates the question, is ⚠️, and the item does not pass on it.
- Options must not reveal the answer. The correct option must not be the only one with real names,
  the most specific one, or the longest one. Change the order of the options in each round.
- An escape option (`以上都不对`, `图上没有这条路径`, `都没有`) can be the correct answer when the
  code says so. Do not make it a permanent distractor, or the owner learns to ignore it.
- For a flowchart, a sequence diagram, or a state machine, ask the owner to trace one case through
  the diagram. Do not ask what the diagram shows. Prefer failure branches, edge branches, and cases
  with one protection removed, because a happy path can be recognized without understanding.
  Use the diagram's own nodes, steps, or states as options:
  - Flowchart: `[单选]` for which end node a given input reaches.
  - Sequence diagram: `[排序]` for the order of steps, and `[多选]` for which writes are persisted
    when step N fails.
  - State machine: `[单选]` for the next state after an event, `[判断]` for whether a transition is
    legal, and `[多选]` for which events leave a state.
- Check the answer key against the code, not only the diagram. If the diagram and the code
  disagree, the plan has a defect. Fix the plan before you grade the answer.
- If the owner chooses `图上没有这条路径` and the code shows that the path is real, the row is ✅.
  Record a plan defect in `处理` (explain-back) or `实际行为` (simulated flight). Add the missing
  branch to the diagram before you continue.

### `确认记录` format

Every explain-back, including a later re-explain after a decision change, appends rows to one table.
Do not write the record as prose or bullets.

```markdown
| 日期 | 触发 | 轮次 | 题 | owner 回答要点 | 结果 | 处理 |
|---|---|---|---|---|---|---|
| 2026-10-27 | 首次 | 1 | [简答] D2 未付费用户 1001 请求课程 7 第 3 节返回什么 | … | ✅ | — |
| 2026-10-27 | 首次 | 1 | [简答] D3 1001 把第 3 节响应里的 play_url 发给 1002，1002 10 分钟内打开结果 | … | ❌ | 解释签名凭证与裸地址的区别，同一案例改一个变量重问 |
| 2026-10-27 | 首次 | 2 | [判断] D3′ 同一案例但 1002 在 2 小时后打开（签名已过期），仍能播放 | … | ✅ | — |
| 2026-10-27 | 首次 | 2 | [简答] D3″ 同 D3′，但改由 1001 本人打开，返回什么 | … | ✅ | 单道判断不能让 D3 通过，补一道简答 |
| 2026-10-28 | 决策变更：D3 | 1 | [简答] D3 签名改绑 user_id 后，1002 10 分钟内打开 1001 的 play_url 被哪层拒 | … | ✅ | 改 §10 第 4 项 |

结论：首次 2 轮通过；决策变更 1 轮通过。可以开始实施。
```

- `触发` is `首次`, `决策变更：<item>`, or `评审纠偏：<source>`. Round numbers restart at 1 for each
  trigger.
- One row per question per round. `题` starts with the format tag. A re-asked question keeps its ID
  with a prime (`D3′`, `D3″`) and names the changed variable.
- `结果` is `✅`, `❌`, `⚠️` (conclusion right, mechanism wrong; counts as not passed), or `不计`
  (a recitation of Claude's explanation; the round counts and the row does not pass).
- A ✅ row is not an item pass; see the pass rule in [Question formats](#question-formats).
- `处理` names the explanation given, the changed plan section, or `—`.
- End each trigger with a `结论` line that states the number of rounds to pass.

Implementation of a high-risk plan starts only after the current §0 is explained correctly. If a
consequential decision changes later, the previous answer does not cover it: update the plan and
repeat this gate only for the changed items.
