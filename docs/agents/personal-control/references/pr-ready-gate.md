# Personal PR-ready gate

Run these after implementation and verification, before `gh pr create` or handing off the PR,
**in this order**: simulated flight first, local review loop last. The review must cover every
commit, including the plan commit that records the flight. The final review record never needs a
commit, so the loop terminates.

PRs created by CI workflows (for example the `pr-lessons` rolling `lessons/pending` PR) are exempt:
a human reviews them at merge.

## 1. Simulated flight (high-risk plans)

For a plan classified high-risk against `docs/agents/high-risk.md`, run the simulated flight below,
record it under `## 个人模拟飞行`, and commit the record. Non-high-risk plans record
`不适用：<理由>` there.

The flight checks whether the owner knows how the **implemented** code behaves under faults. It
checks against current code and tests, not against the plan. Run it before summarizing the
implementation to the owner, and follow the planning gate's
[Concrete questions](planning-gate.md#concrete-questions) rules for every question.

1. Data flow: give one concrete trigger with real input values and the starting state that matters.
   Then ask the owner to trace that case through the implemented code in four short numbered steps:
   ① 哪个函数/任务先收到它; ② 读了哪张表的哪一行, 关键字段当时是什么值;
   ③ 写了哪张表的哪些字段, 写成什么值; ④ 调用方或用户最后得到什么, 比如状态码、字段值或推送内容.
   Use the trigger from §0 `必须人理解` that has the most risk. Do not ask the owner to describe the
   flow in general.
2. Pose one or two injected faults drawn from §0 `必须人理解` on top of the same case. Examples are a
   duplicate callback, a worker dying between writes, an old client calling a changed contract, or
   overlapping scheduler runs. Name the exact moment, such as "③ 写完 `orders.status` 后、写
   `subscriptions` 前 worker 被杀". Ask for the resulting row values and which function or
   constraint stops the problem.
   The data-flow steps ①–④ and a fault question's resulting row values use `[简答]`. Only "which
   function or constraint stops it" may use `[单选]` with a reason. One fault question is one row and
   one question; it is ✅ only when the row values and the stopper are both right, and the covering
   test rule still applies. When the stopper uses `[单选]`, tag the row `[简答+单选]`; it counts as
   a `[简答]` row. Use the planning gate's
   [Question formats](planning-gate.md#question-formats) for tags and grading.
3. Check each answer against current code and tests. A pass requires both a correct final answer and
   a passing test that covers the behavior.
4. If the answer is wrong, explain actual behavior and re-ask with one variable changed in the same
   case, so the new question tests the same mechanism. If code is wrong or coverage is absent, fix it
   and rerun full verification.
5. Record the owner's answer, actual behavior, covering test, result, and current commit under
   `## 个人模拟飞行`, in one round table:

   ```markdown
   核对 commit：`<sha>`，日期 YYYY-MM-DD，触发：首次 | 评审后复飞

   | 轮次 | 题 | owner 回答要点 | 实际行为 | 覆盖测试 | 结果 |
   |---|---|---|---|---|---|
   | 1 | [简答] 数据流 回调 PAY20261120001 首次到达 | … | … | — | ❌ |
   | 2 | [简答] 数据流′ 同单但订阅已过期 | … | … | `test_…` | ✅ |
   | 1 | [简答+单选] 故障 A 写完 orders.status 后 worker 被杀 | … | … | `test_…` | ✅ |

   结论：数据流 2 轮、故障 A 1 轮，全部通过。
   ```

   Use the same row, prime, and `结果` rules as the planning gate's `确认记录`. A recitation of
   Claude's explanation is recorded with `结果` `不计`, and its round still counts.

Do not create or hand off the PR until the data-flow exercise and injected faults pass. Code or
tests changed because of the flight go back through full verification and plan sync before the
review loop.

If the owner chooses to carry an unmastered or untested risk, only the owner may write the explicit
sign-off in `## 个人模拟飞行`; reproduce that sign-off verbatim under the PR description's
`残余风险`. Never draft or suggest sign-off wording on the owner's behalf.

## 2. Local review loop (every PR)

1. Run the repository `code-review-request` skill against `origin/main...HEAD`, then handle the
   report with `code-review-response`.
2. If any finding is blocking (🔴), fix it, rerun the affected verification, and record that round
   (round number, reviewed commit, findings, treatment) in the plan's `### 本地评审记录` subsection,
   placed immediately before `## 个人模拟飞行` (when a plan applies), **in the same commit as the
   fix**. If the fix
   changes behavior covered by a flight exercise, re-fly that exercise against the fix commit
   (trigger `评审后复飞`) and commit the updated `## 个人模拟飞行` record separately: a record cannot
   name the commit that contains it. Then start a new round. Repeat until one round reports no 🔴
   for the current HEAD.
3. The final round (no 🔴) is recorded **only in the PR description**, never in a tracked file:
   committing it would change HEAD and invalidate the record. The PR description lists every round:
   round number, reviewed commit, findings, and the treatment of each. An unfixed non-blocking
   finding needs a reason. For a high-risk plan, the PR's 验证结果 also gives the simulated-flight
   conclusion and its verified commit.
4. When the round for the current HEAD has no 🔴, run this skill's
   `scripts/mark-review-passed.sh` from the repository worktree. It records HEAD as reviewed. Never
   run it before the review finishes or while a 🔴 remains.
5. Only then create the PR, from the branch's own worktree and without `--head`. Any later commit
   invalidates the record: changes after review need a new round before creating or updating the
   PR.

Claude Code enforces step 5 with this skill's `hooks/require-local-review.sh`, registered as a
user-level `PreToolUse` hook (see the package README). It applies only inside `<REPO_PATH>`, blocks
`gh pr create` unless the record matches the HEAD of the session's working directory, blocks
`--head` / `-H`, and blocks when `jq` is missing. It does not gate `git push` to an already open PR;
updating a PR relies on step 5 being followed. Codex has no hook; follow the steps manually.
