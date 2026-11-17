# Personal PR-ready gate

## Local review loop (every plan, before `gh pr create`)

After implementation and verification, and before creating a PR:

1. Run the repository `code-review-request` skill against `origin/main...HEAD`, then handle
   the report with `code-review-response`.
2. If any finding is blocking (🔴), fix it, rerun the affected verification, commit, and start a
   new review round. Repeat until one round reports no blocking finding for the current HEAD.
3. Record each round in the plan's actual-change section and the PR description: round number,
   reviewed commit, findings, and the treatment of each. Non-blocking findings that are not fixed
   need a reason.
4. When the round for the current HEAD has no blocking finding, run
   `bash ~/.agents/skills/personal-control/scripts/mark-review-passed.sh`. It records HEAD as
   reviewed. Never run it before the review finishes or when a blocking finding remains.
5. Only then create the PR. Any later commit invalidates the record, so changes after review need a
   new round before updating or creating the PR.

Claude Code enforces step 5 with a `PreToolUse` hook (`~/.claude/hooks/require-local-review.sh`)
that blocks `gh pr create` unless the record matches HEAD. Codex has no hook; follow the steps
manually.

## High-risk simulated flight

For a high-risk plan, run this gate after implementation and verification but before creating or
handing off the PR. Low-risk plans record `## 个人模拟飞行` as not applicable with the reason.

## Simulated flight

Before summarizing the implementation to the owner:

1. Ask the owner to describe in at most three sentences where input enters, which object is the
   source of truth, and what is written.
2. Pose one or two concrete injected faults drawn from §0 `必须人理解`, such as a duplicate callback,
   a worker dying between writes, an old client calling a changed contract, or overlapping scheduler
   runs. Ask what happens and which layer stops it.
3. Check each answer against current code and tests. A pass requires both a correct final answer and
   a passing test that covers the behavior.
4. If the answer is wrong, explain actual behavior and use a different scenario testing the same
   mechanism. If code is wrong or coverage is absent, fix it and rerun full verification.
5. Record the owner's answer, actual behavior, covering test, result, and current commit under
   `## 个人模拟飞行`, in one round table:

   ```markdown
   核对 commit：`<sha>`，日期 YYYY-MM-DD，触发：首次 | 评审后复飞

   | 轮次 | 题 | owner 回答要点 | 实际行为 | 覆盖测试 | 结果 |
   |---|---|---|---|---|---|
   | 1 | 数据流 | … | … | — | ❌ |
   | 2 | 数据流′ <新场景> | … | … | `test_…` | ✅ |
   | 1 | 故障 A | … | … | `test_…` | ✅ |

   结论：数据流 2 轮、故障 A 1 轮，全部通过。
   ```

   Use the same row, prime, and `结果` rules as the planning gate's `确认记录`. A recitation of
   Claude's explanation is recorded with `结果` `不计`, and its round still counts.

Do not create or hand off the PR until the data-flow exercise and injected faults pass. If the owner
chooses to carry an unmastered or untested risk, only the owner may write the explicit sign-off in
that section; reproduce that sign-off verbatim under the PR description's `残余风险`. Never draft or suggest sign-off wording
on the owner's behalf.

If later review changes behavior covered by a flight exercise, rerun the affected exercise against
the new code and update the recorded revision before updating the PR.
