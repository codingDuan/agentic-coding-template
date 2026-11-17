---
name: prod-deploy
description: Use when deploying to staging or production, publishing the current commit or a release, checking release status, or rolling an environment back through the approved release workflow.
---

# Staging and production release (skeleton)

> Template note: fill the `{{...}}` placeholders and the "Project specifics" section after the
> project's release tooling exists. Keep the authorization and evidence rules as they are.

This skill coordinates an authorized release; it does not expand that authorization. Announce the
skill before acting. Read `CLAUDE.md`, `RULES.md`, the current implementation plan under
`docs/plans/`, and `docs/agents/release-dimensions.md` before touching any environment.

## Authorization

- Production releases need an explicit request from the owner in this conversation. Approval for
  one release does not carry over to the next.
- Staging is not production. A green staging deploy is not evidence for production behavior that
  depends on production data, credentials, or traffic.
- Never edit `.env` or server configuration as part of a release. Tell the owner what must change.

## Workflow

1. **Identify the release.** The exact commit or release id, the PRs it contains, and the plan(s)
   they belong to.
2. **Classify components.** From the diff, decide which components must be rebuilt or restarted.
   Use `docs/agents/release-dimensions.md`; do not decide by intuition. If release tooling or
   deploy scripts changed, assume every backend component restarts.
3. **Pre-deploy checks.** Run every pre-deploy check the plan lists (config preconditions,
   read-only counts that post-deploy checks compare against).
4. **Deploy** with `{{DEPLOY_COMMAND}}` in the order the plan's 发布顺序 gives.
5. **Verify.** Run the plan's post-deploy checks; read migration logs; confirm the deployed version
   with `{{DEPLOY_STATUS_COMMAND}}`. Report only what the evidence shows.
6. **Rollback** with `{{ROLLBACK_COMMAND}}` when a check fails. State the data effect: code rolls
   back, written data usually does not.

## Project specifics

| Item | Value |
|---|---|
| Release id format | `{{RELEASE_ID_FORMAT}}` |
| Build / prepare | `{{PREPARE_COMMAND}}` |
| Deploy | `{{DEPLOY_COMMAND}}` |
| Status | `{{DEPLOY_STATUS_COMMAND}}` |
| Rollback | `{{ROLLBACK_COMMAND}}` |
| Migration logs | `{{MIGRATION_LOG_LOCATION}}` |

## Report

Release id, components restarted, migrations run with their log lines, post-deploy check results,
and anything skipped with the reason.
