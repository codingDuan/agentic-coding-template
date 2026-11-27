# Personal execution gate

Add these checks to the shared `executing-plans` workflow.

## Before implementation

- Confirm the plan has §0, a `风险等级` line, and `## 个人模拟飞行`. If the plan predates this
  profile, run the planning gate before editing code.
- High-risk plan: confirm a current explain-back pass in `确认记录`. If it is missing, run the
  explain-back before editing code.
- Non-high-risk plan: confirm `确认记录` says `不适用：<理由>`.

## During implementation

- In a high-risk plan, a change to a §0 decision, risk boundary, or `掌控分级` item pauses
  implementation. Update the plan first, explain the changed item to the owner, ask it back from a
  different angle, and append the new rows to the `确认记录` round table (trigger
  `决策变更：<item>`) before continuing.
- In a non-high-risk plan, the same change updates §0 and gets the owner's confirmation, as the
  shared skill requires.
- A change that makes a non-high-risk plan high-risk: update `风险等级`, then run the full
  explain-back before continuing.
- Ordinary implementation detail that stays within the confirmed decision does not trigger a new
  explain-back.

## Verification reconciliation

For each `交给验证兜底` item, verify that the named test, contract, invariant, type check, or alert
exists and ran successfully. A missing check must be added, or the item moves to `必须人理解`. In a
high-risk plan, the reclassified item is explained back (trigger `决策变更：<item>`).

## Before PR preparation

Continue with the PR-ready gate: the simulated flight for a high-risk plan, then the local review
loop for every PR. Any code or test changed because of those gates sends the work back through full
verification and plan sync.
