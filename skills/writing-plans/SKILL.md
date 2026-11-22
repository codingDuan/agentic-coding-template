---
name: writing-plans
description: Use when creating or updating a technical plan before code changes, especially for multi-step features, migrations, API changes, payment/subscription/permission/notification/scheduler work, or any change that needs docs/plans design coverage.
---

# Writing Plans

## Overview

A plan has **two readers with different needs**, and each layer is written for one of them:

| Reader | Reads | Budget | Layer |
|---|---|---|---|
| Human who confirms the plan | Main document | concise | Decisions, rejected alternatives, risks, compatibility, rollout |
| Executor (agent or engineer) | Everything, especially sub-task documents | unlimited | Full code, exact commands, expected output |

The main document must be concise enough for review while still making decisions, risks,
compatibility, verification, and rollout explicit. Its §0 decision card is what the human explains
back before a high-risk plan is implemented (see Explain-Back Gate).

For the executor layer: assume the engineer has zero context for our codebase and questionable taste. Document everything they need: which files to touch for each task, code, testing, docs to check, how to verify. Give them the whole thing as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits. Assume a skilled developer who knows almost nothing about our toolset or problem domain, and who does not know good test design well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

## Required Project Context

Before writing or updating a plan, read:

1. `RULES.md`
2. `docs/plans/README.md`
3. The relevant existing product/API/data-model docs listed under Sources in `CLAUDE.md`
4. Any existing plan directory for the same feature
5. `docs/agents/lessons.md` — lessons from recently merged PRs; a plan touching an area with a lesson must show how it avoids repeating it

Do not start from a generic template if a feature-specific plan already exists. Extend the existing plan and preserve its structure unless there is a clear reason to split it.

## Save Location

Plans are organized by **domain → topic**, following `docs/plans/README.md`:

1. Pick the domain from the 领域入口 table in `docs/plans/README.md` (e.g. `billing`, `auth`, `notifications`, ...).
2. Inside it, find an existing topic directory for this feature. **If one exists, extend it** — add the next numbered files and update its README — instead of starting a parallel plan.
3. Only when no topic fits, create `docs/plans/<domain>/<topic>/README.md` and link it from the domain README.

Inside a topic directory, files are numbered in creation order, e.g.
`01-<name>-design.md` (main document), `02-<name>-implementation.md`, `03-task1-<name>.md`, ...
Directory names use the
domain and topic, never a date; dates live in the document metadata.

User-provided locations override these defaults only if they still satisfy `RULES.md`.

## Progressive Disclosure Document Structure

Plans MUST follow a **main document + sub-task documents** structure.

**The split rule:** the main document holds everything that is true of the change *as a whole* — decisions, background, architecture, diagrams, cross-client impact, rollout. Sub-task documents hold everything an engineer needs to execute *one task*. An engineer reading only a sub-task document must be able to finish it; an engineer reading only the main document must understand the shape of the change and what ships.

### Main Document

```markdown
# [Feature Name]

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans (this repo's, not
> superpowers:executing-plans) — its plan gate and completion steps apply to every execution mode;
> superpowers:subagent-driven-development (recommended) may replace only its task-execution step.
> Steps use checkbox (`- [ ]`) syntax for tracking.

> 创建时间: YYYY-MM-DD
> 状态: 进行中 | 已完成
> 分支: <branch-name>
> 风险等级: 高风险（<命中 docs/agents/high-risk.md 的哪一条>） | 非高风险（<理由>）

## 0. 决策卡

### 关键决策
| 编号 | 决策 | 选择 | 否决的方案 | 选错的代价 |
|---|---|---|---|---|
| D1 | … | … | … | … |

### 掌控分级
| 必须人理解 | 交给验证兜底 |
|---|---|
| [数据模型、钱、权限、不可逆操作、对外契约、状态机] | [其他项，每项写明具体的可执行检查：测试名、契约、不变量、类型检查或告警] |

### 可能让你意外的地方
[行为变化、语义漂移、推迟的范围、迫使设计成这样的约束]

### 确认记录
[高风险计划：讲回轮次表，见 control-gates 的 references/explain-back.md。非高风险：`不适用：<理由>`]

## 1. 问题背景 / 目标
[Why this change is needed, what problem it solves, explicit non-goals]

## 2. 解决策略 / 设计原则
[Key decisions and rejected alternatives, high-level approach, project constraints,
compatibility expectations, compliance boundaries, risks and surprises]

## 3. 流程图
[Mermaid flowchart — see Diagram Requirements]

## 4. 时序图
[Mermaid sequence diagram — see Diagram Requirements]

## 5. 状态机
[Mermaid state diagram — see Diagram Requirements]

## 6. 数据流
[Inputs, persisted objects, status transitions, outputs]

## 7. API / Schema / UI 影响
[Changed contracts and compatibility strategy, plus the all-client
compatibility matrix — see Compatibility Matrix]

## 8. 子任务及依赖关系

```
Task 1: [Name] → 无依赖
Task 2: [Name] → 无依赖
Task 3: [Name] → 依赖 Task 1, 2
```

## 9. 验证
[Minimum sufficient tests based on changed paths and risk; exact commands]

### 完成对账

| 计划约束 | 实现证据 | 边界测试 / 命令 | 最终结果 |
|---|---|---|---|
| [One row per consequential requirement or non-goal] | 待实施 | [Exact command] | 待执行 |

### 机械验收契约

```json plan-compliance/v1
{
  "version": 1,
  "assertions": [],
  "none_reason": "Explain why this plan has no deterministic absence, presence, or command assertion"
}
```

## 10. 上线步骤与回滚
[Eight-dimension table + 发布顺序 + rollback — see Rollout Requirements]

## 11. 实际改动清单（完成后回填）
| 文件 | 改动 |
|------|------|
| `path/to/file` | 描述 |

## 12. 踩坑记录（完成后回填）
| 问题 | 根因 | 解决方案 |
|------|------|----------|

## 模拟飞行
[高风险计划：实现与验证后由 pr-ready 回填。非高风险：`不适用：<理由>`]

## 13. 子任务详情
- [Task 1: 短名称](03-task1-<name>.md)
- [Task 2: 短名称](04-task2-<name>.md)
```

Sections 3–5 and 10 are **required** for migrations, payments, subscriptions,
permissions, scheduler, notifications, and high-risk UI funnels. If one is
genuinely not applicable, write the reason explicitly. **Silence is a plan defect.**

§0 is required for every plan; keep it to 3–5 consequential decisions. Classify the plan's risk
level against `docs/agents/high-risk.md` in the header. `## 模拟飞行` is an unnumbered section that
stays immediately before `## 13. 子任务详情` so the shared numbering (and the completion checker's
`## 13.` heading) is unchanged; it is the only place the simulated-flight record lives.

### Sub-Task Documents

Each sub-task has its own file with full implementation detail:

```markdown
# Task N: [Task Name]

> 状态: 待开始 | 进行中 | ✅ 已完成
> 依赖: Task X, Task Y
> 文件: `path/to/file.py`, `path/to/other.py`

## 计划改动
[What was planned — full code, exact commands, expected output]

## 实际改动（完成后回填）
[What was actually done — may differ from plan due to discoveries]

## 验证
[How to verify this task is correct — exact command and expected output]
```

### Key Rules

1. **Main document = decisions + index + architecture + 上线**: no per-task implementation details
2. **Sub-task documents = everything an engineer needs**: full code, exact commands, expected output
3. **Status tracking**: `待开始 | 进行中 | ✅ 已完成` in sub-task headers
4. **Post-completion update**: after implementation, fill in "实际改动" and "踩坑记录" to reflect reality

### Completion Reconciliation and Mechanical Contract

Every new main plan must include both §9 blocks from the template:

1. **完成对账** maps each consequential requirement and non-goal to implementation evidence and an
   exact boundary command. It is the semantic review surface; the executor fills the final result.
2. **`plan-compliance/v1`** declares only deterministic checks. Run
   `python skills/executing-plans/scripts/check_plan_completion.py --help` for the CLI contract.

Use these assertion shapes:

```json
{"id":"old-fallback-absent","type":"forbid-regex","paths":["src/**/*.py"],"pattern":"source_date\\s*=="}
{"id":"shared-classifier-present","type":"require-regex","paths":["src/**/*.py"],"pattern":"classify_trading_day"}
{"id":"materialization-boundary","type":"command","argv":["python","-m","pytest","tests/test_timeline.py::test_unknown_day","-q"]}
```

When a requirement says **remove**, **forbid**, **must not infer**, **only source of truth**, or
**fail closed**, add an absence/presence assertion whenever repository files can express it. A green
helper test does not replace the command for the caller or materialization boundary named by the
plan. Commands are argv arrays, not shell strings.

If no deterministic assertion applies, keep `assertions: []` and replace `none_reason` with a
specific reason. Omitting the contract is not the same as having no mechanical assertion.

## Diagram Requirements

Use Mermaid unless the user asks otherwise.

Flowchart must answer: "How does the user, admin, or scheduled task move from entry to result?"

Sequence diagram must answer: "Which system calls which other system, in what order, and where is state committed?"

State machine must answer: "What is the single source of truth for business state, and what action drives each transition?"

Pay special attention to stateful domains. Typical ones (replace with the project's list):

- Payment order fulfillment, refund, renewal, cancellation
- Subscription, entitlement, and quota bookkeeping
- Permission and masking
- Notification event and delivery status
- Worker run lifecycle and scheduler fan-out
- {{PROJECT_STATEFUL_DOMAINS}}

## Compatibility Matrix

For API, schema, auth, payment, subscription, permission, notification, or status-flow changes, include a matrix in the main document:

| Caller | Impact | Required change | Verification |
|---|---|---|---|
| Web | affected / not affected | files or reason | test command |
| Mobile | affected / not affected | files or reason | test command or N/A reason |
| <other client in RULES.md §3> | affected / not affected | files or reason | test command or N/A reason |
| Worker/Internal/MCP | affected / not affected | files or reason | test command |

Never write only "frontend updated" when the backend contract serves multiple clients.

## Rollout Requirements

The main document's 上线步骤 section must enumerate all eight dimensions —
**read `docs/agents/release-dimensions.md` and follow it**. It is the single source of truth
shared with `executing-plans` and `pr-ready`; do not restate the dimensions here.

Two things a plan must add on top of that file: the 发布顺序 across dimensions with reasons,
and per-batch rollback with **data impact** (code rolls back, written data usually does not).

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in — follow the patterns already in the codebase rather than unilaterally restructuring.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

Additionally, tasks must be executable and verifiable:

- Identify exact files or directories to inspect or modify.
- Include failing-test-first steps when behavior changes.
- Include expected command outputs for verification steps.
- Keep unrelated refactors out of the plan.
- Mark data migration, rollback, and compatibility work as **first-class tasks, not footnotes**.

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:

- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases" — give exact behavior and error code
- "Write tests for the above" without actual test code, scope, and command
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task
- A state list without transition actions
- A flow or sequence described only in prose when a diagram is required

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

1. **Spec coverage:** skim each requirement in the spec. Can you point to a task that implements it, or an explicit non-goal? List any gaps.
2. **Diagrams:** does the main document have flowchart, sequence diagram, and state machine — or an explicit reason each missing one is N/A?
3. **Three-client compatibility:** do changed contracts have the matrix filled in, including Worker/Internal/MCP?
4. **上线步骤:** are all eight dimensions from `docs/agents/release-dimensions.md` present, with untouched ones marked "无" rather than omitted? Did you actually run the Worker/MCP import greps?
5. **Test commands:** does the 验证 section include `make test-critical-scope` (and `make test-critical` when the change touches runtime paths), plus the path-scoped tests from `docs/09-test-guide.md`?
6. **Type consistency:** do types, signatures, and property names in later tasks match earlier ones? `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.
7. **Progressive disclosure:** is the main document free of per-task implementation detail? Are sub-task documents self-contained?
8. **Placeholder scan:** search for the patterns in "No Placeholders" and fix them.
9. **Decision quality:** §0 lists 3–5 consequential decisions with the rejected alternative and the
   cost of being wrong; every `交给验证兜底` item names a concrete executable check; §2 expands the
   choices, risks, and surprising scope boundaries clearly enough for review.
10. **Completion contract:** §9 has one reconciliation row per consequential requirement/non-goal,
    and a valid `plan-compliance/v1` block. Removal/prohibition constraints have absence evidence;
    helper tests do not stand in for named caller-boundary commands. Run the checker in static mode.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Explain-Back Gate

For a **high-risk** plan, after self-review and before implementation, **REQUIRED SUB-SKILL:** use
`control-gates` to run the explain-back with the human partner who drives the change, and record it
in §0 `确认记录`. A plan confirmation alone does not pass this gate.
For other plans, write `不适用：<理由>` in `确认记录` and `## 模拟飞行`.

## Execution Handoff

After the plan is saved, present its path and a concise summary of decisions, risks, non-goals,
verification, and rollout. Ask the user to confirm the plan before implementation (for a high-risk
plan, the Explain-Back Gate must also pass), then offer the execution choice:

**"Plan confirmed and saved to `docs/plans/<domain>/<topic>/<file>.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?"**

**Either way, REQUIRED SUB-SKILL: executing-plans** (this repo's, not `superpowers:executing-plans` — that one has none of the project gates). It owns the plan gate, completion verification, and doc sync. The choice only decides who executes the tasks:

- **Subagent-Driven:** executing-plans Step 3 is carried out with superpowers:subagent-driven-development (fresh subagent per task + two-stage review); all other steps still run.
- **Inline Execution:** executing-plans runs end to end in this session.
