# {{PROJECT_NAME}} Hard Rules

This file is the single source for project rules. `CLAUDE.md` includes it for development.
`REVIEW.md` tells reviewers to read this file. Do not merge when a rule violation occurs.

> Template note: rules 2–9 are stack-independent and come from production experience; keep them.
> Rule 1 is a slot for the project's own environment-parity hazards — rewrite it for your stack.
> When you add, remove, or renumber a rule, update the mapping table in `REVIEW.md` in the same change.

## 1. Keep Development and Production Equivalent

{{ENVIRONMENT_PARITY_RULE}}
<!--
Example (SQLite in dev/test, PostgreSQL in production):
- Use SQL and ORM forms that give the same result in both databases.
- SQLite does not enforce `VARCHAR(n)` length; add explicit length tests for fixed identifiers.
- Do not use a successful SQLite write as proof of a valid PostgreSQL write.
- For a grouped expression with a literal, reuse one expression object in SELECT and GROUP BY.
-->

## 2. Examine All Consumers of a Contract

Apply this rule when you change one of these items:

- An API response field
- A schema or ORM field
- A front-end component property
- A queue/worker message format
- A field type, default value, or null rule

Search for all consumers before you change the contract.
Update each consumer, or record that it does not use the contract. List this result in the PR description.

### 2.1 Examine Semantic Changes

Apply rule 2 when field names and types stay the same but their business definition changes:
a persistent status becomes temporary, an enum gets a new value, a default or time limit changes,
a sort rule changes, or a query result gets a different business definition.

Do not search only for the field name. Search for filters on each affected value
(`== "value"`, `.in_((...))`, `filter(status=...)`, `status === 'value'`).
For each filter, identify the business concept it represents.
If one value no longer represents that concept, use one named constant for the concept.
Do not write the value list in multiple consumers.

## 3. Keep Backend APIs Compatible with All Clients

The backend serves these clients: {{CLIENT_LIST}} <!-- e.g. Web, Mobile, Mini Program, MCP, Workers -->.

Apply this rule to path, method, request, response, field, auth, permission, payment, status,
error code, paging, sort, filter, schema, SDK, or API-wrapper changes.

Do not delete a published field or change its definition without a transition plan.
If possible, use an added field, a new endpoint, or versioned behavior.
Examine callers in every client. For a client with no caller, write that result in the PR description.
Do not write only "front end updated."

Add one backend API test for payment, subscription, permission, notification, or login changes.
If a change affects a UI flow, add an applicable E2E or smoke test. If automation is not possible, record the reason.
For an incompatible change, give the transition method and the removal date or condition.

## 4. Give the Treatment of Current Data

For each data-layer defect, give the treatment of records that already have the defect:

- Backfill the records with correct values.
- Keep the records and give the reason that this is safe.
- Give a cleanup or recalculation procedure.

Do not merge the change without one treatment.

### 4.1 Test Data Migrations with Data

Apply this section to backfills, data corrections, and projection rebuilds (not DDL-only migrations).
Make realistic records in the database. Run the real migration code on those records.
Make sure that the number and values of the output records are correct.
Include applicable dirty forms: `NULL`, empty strings, naive datetimes, JSON stored as text,
long strings, duplicate subjects.
In the PR result, write that the test database contained data.
Do not use an empty-database migration run as backfill proof.

## 5. Put Documents Only in Approved Locations

Put Markdown documents only in these locations:

- `docs/NN-*.md` — numbered core documents
- `docs/api-contract/**` — API contract details
- `docs/plans/**` — feature, defect, and refactor plans
- `docs/product-docs/**` — product requirements
- `docs/discuss/**` — draft discussions
- `docs/static/**` — document assets
- `docs/agents/**` — agent configuration
- `skills/**` — project skills
- Any `**/README.md`
- Root project documents: `README.md`, `CLAUDE.md`, `REVIEW.md`, `RULES.md`, `AGENTS.md`, `CHANGELOG.md`, `LICENSE`

Do not add other Markdown files at the repository root or in source directories.
Put a short, temporary analysis in code comments, the commit message, or the PR description.

## 6. Do Not Modify `.env`

Do not use an edit tool or a shell command to change `.env`. It can contain credentials.
To add a configuration example, modify `.env.example`.
Tell the user how to make a required `.env` change. Do not make the change for the user.

## 7. Keep Dependency Lock Files Complete

If a change edits a dependency manifest, also update its lock file with `{{LOCK_COMMAND}}`.
Do not merge a dependency change without the updated lock file.

## 8. Match Verification to the Change Risk

`make test-critical` runs the project's core tests. The `Makefile` is the single source for that list.
Before you merge, run `make test-critical-scope`. It lists each changed path and its class.
`.github/scripts/classify-ci-scope.sh` is the single source for path classes.
Exempt classes are documents, skills, and client code. Any other path requires `make test-critical`.

If the command reports `REQUIRED`, run `make test-critical` successfully on a clean worktree at a commit in the PR history.
A successful run stays valid while all later changes are exempt.
To reuse a run, run `make test-critical-scope SINCE=<run commit>` and get `NOT REQUIRED`.
In the PR verification result, add the scope output. When you reuse a run, also add the run commit and its result.

Client changes still need their client checks from `docs/09-test-guide.md`.
For payment, subscription, permission, notification, authentication, trade, or migration changes, add an API or integration test.
For each schema migration, keep one migration head and run the migration on a production-equivalent database.

## 9. Prevent Duplicate Facts and Unnecessary Design

Before architecture work, record the accepted business stories, roles, facts, operations, and non-goals.
Do not add a future life cycle that the owner did not approve.
Before you add persistent state, examine the current models, services, APIs, and operator interfaces.
For each business fact, select one source of truth and one stable identifier.
Do not add a second writable copy of the same fact, dual writes, shadow ledgers, or synchronization jobs without an approved need.
For each new table, role, status, key, service, or compatibility path, show the fact gap and the smallest rejected design.
