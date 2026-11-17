# Personal execution gate

Add these checks to the shared `executing-plans` workflow.

## Before implementation

- Confirm the plan has §0 and a current explain-back pass in `确认记录`.
- If the plan predates this profile or the record is missing, run the planning gate before editing code.

## During implementation

- A change to a §0 decision, risk boundary, or `掌控分级` item pauses implementation.
- Update the plan first, explain the changed item to the owner, ask it back from a different angle,
  and append the new rows to the `确认记录` round table (trigger `决策变更：<item>`) before continuing.
- Ordinary implementation detail that stays within the confirmed decision does not trigger a new
  explain-back.

## Verification reconciliation

For each `交给验证兜底` item, verify that the named test, contract, invariant, type check, or alert
exists and ran successfully. A missing check must be added, or the item moves to `必须人理解` and
the changed classification is explained back.

## Before PR preparation

For payment, subscription, permission, notification, scheduler, migration, trading execution, or
another stateful high-risk change, run the simulated flight defined in the PR-ready gate. Any code or
test changed because of the flight sends the work back through full verification and plan sync.
