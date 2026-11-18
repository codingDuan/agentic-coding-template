# Project Rule Evidence

This file holds the reasons, typical forms, and incident records behind `RULES.md`.
It does not contain normative rules: if this file and `RULES.md` disagree, `RULES.md` wins.

The template ships with incidents from the production project this workflow came from, with
business names removed. They show *why* each rule exists. Keep them until your own project has
its own incidents for the same rule, then add yours (the weekly lessons fold may also append here).

Entry format: **why** (the mechanism), **typical form** (what the defect looks like in a diff),
**incidents** (what happened, how it was found, what fixed it).

## Rule 1: Development and Production Equivalence

**Why.** Local tests pass on the development stack. Production runs a different database, driver,
or runtime. Any behavior the two stacks disagree on is untested until production.

**Typical form.** A query, constraint, or type that the development database accepts and the
production database rejects or reads differently.

**Incidents** (SQLite in development, PostgreSQL in production):

- *Grouped expression with a literal.* An admin dashboard query built two separate
  `func.coalesce(column, "legacy")` expressions, one for `SELECT` and one for `GROUP BY`.
  SQLAlchemy gave each literal its own bind parameter. PostgreSQL treated them as different
  expressions and raised `GroupingError: column ... must appear in the GROUP BY clause`; SQLite
  accepted the query. Every production request to the dashboard failed. A second query with the
  same form stayed hidden behind the first failure. Fix: reuse one expression object in both
  clauses; the regression test compiles the statement with the PostgreSQL dialect.
- *String length.* A seed wrote a 33-character value into a `VARCHAR(32)` column. SQLite does not
  enforce the length; PostgreSQL rejected the batch insert with `StringDataRightTruncation`.
  Fix: a shorter value plus a test that compares the value length with the model column length.
- *Unsupported function form.* `func.case` worked in one database and not the other; the fix was
  `sqlalchemy.case`.

## Rule 2: Contract Consumers

**Why.** API fields, schemas, ORM fields, component properties, and queue messages have consumers
outside the file being changed. A missed consumer often fails only in production, or only in a
client that ships later.

**Typical form.** A renamed or retyped field with no consumer list in the PR description.

## Rule 2.1: Semantic Changes

**Why.** A change can keep every name and type and still change what a value *means*. A search for
the field name finds the definition, not the filters that encode the old meaning.

**Typical form.** A status, enum value, default, or time limit changes meaning, and code elsewhere
still filters on `status == "value"` or `.in_((...))` with the old meaning.

**Incident.** A PR added expiry cleanup for unpaid orders: `pending` changed from a persistent
status to a temporary one (orders expired after 30 minutes). One PR produced four defects in
other consumers that filtered on `pending`: refund deduction cancelled the wrong orders, a
sales follow-up queue became empty, an "unpaid amount" field dropped to zero, and a category
report misclassified orders. Fix: one named constant for the business concept ("unsettled
orders") used by every consumer instead of repeated literal lists.

## Rule 3: Client Compatibility

**Why.** Several clients call the same backend. Mobile and mini-program clients ship on slower
release cycles than the backend, so old client versions keep calling new APIs for weeks.
Authentication, payment, and subscription changes carry the highest user risk.

**Typical form.** A PR that says "frontend updated" when only the web client was checked.

## Rule 4: Existing Data

**Why.** Fixing a write path does not fix the records it already wrote. Consumers keep reading the
bad records until a backfill runs or someone decides they are safe to keep.

**Typical form.** A data-layer fix with no backfill, retention reason, or cleanup procedure.

## Rule 4.1: Data Migrations Tested with Data

**Why.** An empty-database migration run proves the DDL executes. It never enters the backfill code
path, so it proves nothing about the data transformation.

**Incident.** A backfill migration read a datetime column through raw `sa.text()`. SQLite returned
a string; PostgreSQL with psycopg returned a `datetime`. The migration read `.tzinfo` without a
boundary conversion. Three test layers missed it:

1. The unit test passed ideal Python `datetime` objects straight into the merge function.
2. The upgrade and downgrade tests ran on an empty database, and a helper returned early on empty input.
3. The PostgreSQL gate produced the expected `datetime` type, so the string form never appeared.

In staging the migration raised `AttributeError: 'str' object has no attribute 'tzinfo'`, the
deploy script stopped with services down, and every staging endpoint returned 502. Fix: typed
result columns (`.columns(col=sa.DateTime())`) or normalization at the boundary, plus a test that
inserts realistic dirty rows and runs the real migration.

## Rule 5: Document Locations

**Why.** Scattered documents make the repository hard for people and agents to navigate, and
duplicate facts drift apart.

**Typical form.** `NOTES.md` or `bug-fix-summary.md` at the root, `services/payment-design.md` in a
source directory, or a new `docs/reports/` directory. The rule controls location, not document type.
Runtime Markdown that the application reads (for example product content) is application input,
not documentation.

## Rule 6: `.env`

**Why.** `.env` holds real local or production credentials. An automated edit can overwrite the
owner's settings or leak secrets into Git. Shell forms such as `sed -i`, `awk`, and `>` are edits too.

## Rule 7: Lock Files

**Why.** Deployment installs from the lock file, often without network access. A manifest change
without a lock update means the new package is absent at deploy time.

## Rule 8: Verification Matched to Risk

**Why.** Running the full critical suite after every documentation edit wastes time and trains people
to skip it; skipping it after a runtime change ships untested code. Path classes decide which.

**Notes.**

- Client code is exempt only because the critical tests do not read client source. Keep that true
  with a test if your backend ever reads client files.
- In the source project, one PR needed three review rounds that changed only web files after a
  green run; each round repeated a six-minute run that could not test those files. The `SINCE=`
  reuse exists for that case.
- Runtime Markdown does not meet the document exception.
- Unit tests do not cover the full boundary of payment, permission, notification, or migration
  changes; those need API or integration evidence.

## Rule 9: Duplicate Facts and Unnecessary Design

**Why.** Agents are good at producing complete-looking designs. Without an explicit record of what the
owner approved, a design grows tables, roles, and life cycles that duplicate facts other domains
already own.

**Incident.** The first design for a course-sales feature added a second partner qualification, a
course-specific attribution table, course-specific CRM projections with runtime writes, separate
redemption-code storage, external order records, and commission, settlement, and recovery life
cycles, plus legacy routes with dual writes and shadow reads. The accepted first release needed
none of them. The final design reused the shared users, channels, SKUs, codes, orders, and CRM
records, and a cleanup commit removed the duplicate runtime designs.
