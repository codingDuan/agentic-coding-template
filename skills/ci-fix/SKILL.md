---
name: ci-fix
description: Use when debugging or fixing failing CI checks, local test failures, compliance wording failures, Playwright failures, TypeScript failures, pytest failures, migrations, or pre-commit errors.
---

# CI Fix

## Overview

Use this skill when a CI or local verification command fails. The goal is to reproduce the failure,
find the root cause, make the smallest correct fix, and run the minimum sufficient verification for
the touched area.

Announce at start: "I'm using the ci-fix skill to reproduce and fix the failing check."

## Required Reads

Read:

1. `RULES.md`
2. `docs/09-test-guide.md`
3. The failing command output
4. Relevant test file(s)
5. Relevant source file(s)

If the failure touches a planned feature, read the related `docs/plans/**` docs and keep diagrams in
sync when state flow or cross-system order changes.

## Process

1. **Reproduce exactly**: run the failing command from the same working directory when feasible.
2. **Minimize**: if the failing suite is large, isolate the smallest failing test or check.
3. **Inspect before editing**: read the test, source, and local helpers around the failure.
4. **Classify root cause**:
   - product bug
   - test bug or brittle assertion
   - docs/compliance wording violation
   - environment or port conflict
   - fixture/order dependency
   - unrelated existing failure
5. **Fix narrowly**: change the smallest set of files that addresses the root cause.
6. **Verify locally**:
   - rerun the isolated failing command
   - run affected-area tests from `docs/09-test-guide.md` §3
   - run `git diff --check`
7. **Escalate verification** for high-risk paths as defined in `docs/agents/high-risk.md`.

## Common Commands

Web changes:

```bash
cd {{WEB_DIR}}
npm test
npx tsc -b
npm run test:compliance
```

Targeted Playwright:

```bash
cd {{WEB_DIR}}
npx playwright test tests/<file>.spec.ts -g "<test name>"
```

API changes:

```bash
make test-api
```

Worker changes:

```bash
make test-worker
```

Core changes:

```bash
make test-core
```

Full backend matrix:

```bash
make test
```

## Reproducing PostgreSQL Gate Failures Locally

**A failing `Test API PostgreSQL gates` job is reproducible on this machine. Do not report
"can't reproduce locally" without walking these steps** — `docker info` failing only means the
daemon is down, not that Docker is absent. Docker Desktop is installed but normally not running.

Check in order; only move on when the previous step fails. Do not jump to a conclusion:

```bash
docker info >/dev/null 2>&1 && echo "daemon ready"   # 1. daemon running?
ls -d /Applications/Docker.app                       # 2. installed but stopped?
open -a Docker                                       # 3. start it, ~30-60s
until docker info >/dev/null 2>&1; do sleep 3; done   #    poll, don't guess at the wait
```

Start a database matching CI's version and credentials. **Use port 55432**, not 5432, which may
already be taken locally:

```bash
docker run -d --name {{PROJECT_SLUG}}-pg-test \
  -e POSTGRES_DB=app_test -e POSTGRES_USER=app_test -e POSTGRES_PASSWORD=app_test \
  -p 55432:5432 postgres:16
until docker exec {{PROJECT_SLUG}}-pg-test pg_isready -U app_test -d app_test >/dev/null 2>&1; do sleep 2; done
```

Run exactly what CI runs — the gate discovers its files by glob, so run the same glob rather
than naming files (a hand-typed subset is how a gate silently stops covering something):

```bash
W=$PWD
PYTHONPATH="$W/{{BACKEND_DIR}}" \
{{TEST_DB_URL_ENV}}="postgresql+psycopg://app_test:app_test@127.0.0.1:55432/app_test" \
{{REQUIRE_TEST_DB_ENV}}=1 \
  python -m pytest {{BACKEND_DIR}}/tests/*_postgres.py -q
```

Tear down with `docker rm -f -v {{PROJECT_SLUG}}-pg-test`. The container is disposable — never keep one
around accumulating state between runs.

**`-v` is not optional.** The `postgres` image declares `/var/lib/postgresql/data` as a volume,
so every `docker run` above creates an anonymous ~500MB–1GB data volume. Plain `docker rm -f`
removes the container but leaves that volume behind, unreferenced. On 2026-10-14 this had piled
up to 106 orphaned anonymous volumes (~37GB), filled the Docker VM disk, and the next
`docker run` failed in `initdb` with `No space left on device`. Check for leftovers with
`docker volume ls -qf dangling=true`.

**Why this is worth the trouble**: the failure classes RULES §1 lists (`GroupingError`,
`StringDataRightTruncation`, `FILTER (WHERE ...)`, migration replay collisions) **all pass
silently on SQLite**. Without a real PostgreSQL, "green locally" carries zero information about
them.

**Reproduce before fixing.** Before the fix you should see the exact error CI reported, word for
word; after it, watch that same command go green. Skipping reproduction means using CI as a
debugger at three minutes per round trip.

## Compliance Wording Failures

When `npm run test:compliance` fails:

1. Read `{{COMPLIANCE_CHECK_SCRIPT}}`.
2. Replace high-risk investment-action wording with platform-safe wording.
3. Preserve product meaning while avoiding advisory/trading instruction language.
4. Rerun `npm run test:compliance`.
5. If wording policy changed, update the relevant product/compliance doc.

## Playwright Failures

For Playwright:

1. Read the error context and screenshot if available.
2. Check whether the failure is a real UX regression, overlay/interception, stale fixture, or brittle locator.
3. Prefer user-facing role/name locators.
4. If changing tests, make assertions more semantically precise, not looser.
5. Rerun the specific test, then the affected file or suite.

## Reporting

Final report must include:

- Root cause
- Files changed
- Commands run and results
- Any unrelated failures or untracked files left untouched

Do not claim a CI issue is fixed until the relevant command has passed locally or you clearly state
why it could not be run.
