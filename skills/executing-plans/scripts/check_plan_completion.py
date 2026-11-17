#!/usr/bin/env python3
"""Validate plan completion structure and explicit acceptance contracts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

CONTRACT_RE = re.compile(
    r"```json plan-compliance/v1[ \t]*\r?\n(.*?)[ \t]*\r?\n```",
    re.DOTALL,
)
STATUS_RE = re.compile(r"^>\s*状态[：:]\s*(.+?)\s*$", re.MULTILINE)
COMPLETE_STATUS_RE = re.compile(r"^(?:✅\s*)?已完成(?:$|[^\w])")
TASK_LINK_RE = re.compile(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)")
UNCHECKED_RE = re.compile(r"^[ \t]*[-+*][ \t]+\[[ \t]\](?:[ \t]+|$)")
FENCE_OPEN_RE = re.compile(r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
FENCE_CLOSE_RE = re.compile(r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})[ \t]*$")
MAIN_TASK_HEADING_RE = re.compile(r"^## 13\. 子任务详情\s*$", re.MULTILINE)
MAIN_PLAN_NAME_RE = re.compile(r"^\d+(?:-[^/]+)*-(?:design|overview)\.md$")
ALLOWED_TOP_FIELDS = {"version", "assertions", "none_reason"}
ALLOWED_ASSERTION_FIELDS = {
    "forbid-regex": {"id", "type", "paths", "pattern"},
    "require-regex": {"id", "type", "paths", "pattern"},
    "command": {"id", "type", "argv"},
}


@dataclass(frozen=True)
class Problem:
    code: str
    path: str
    detail: str

    def render(self) -> str:
        return f"{self.code}\t{self.path}\t{self.detail}"


def plan_status(text: str) -> str:
    match = STATUS_RE.search(text)
    return match.group(1).strip() if match else ""


def is_complete(status: str) -> bool:
    return COMPLETE_STATUS_RE.match(status) is not None


def is_main_plan_candidate(rel_plan: str, text: str) -> bool:
    return (
        MAIN_TASK_HEADING_RE.search(text) is not None
        or MAIN_PLAN_NAME_RE.fullmatch(PurePosixPath(rel_plan).name) is not None
    )


def task_section(text: str) -> str:
    match = MAIN_TASK_HEADING_RE.search(text)
    if not match:
        return ""
    tail = text[match.end() :]
    next_heading = re.search(r"^## ", tail, re.MULTILINE)
    return tail[: next_heading.start()] if next_heading else tail


def parse_contract(
    text: str, rel_plan: str
) -> tuple[dict[str, Any] | None, list[Problem]]:
    matches = CONTRACT_RE.findall(text)
    if not matches:
        return None, []
    if len(matches) != 1:
        return None, [
            Problem("CONTRACT_SCHEMA", rel_plan, "expected exactly one v1 contract")
        ]
    try:
        payload = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [Problem("CONTRACT_JSON", rel_plan, str(exc))]
    if not isinstance(payload, dict):
        return None, [
            Problem("CONTRACT_SCHEMA", rel_plan, "contract must be an object")
        ]
    return payload, []


def validate_contract(payload: dict[str, Any], rel_plan: str) -> list[Problem]:
    problems: list[Problem] = []
    unknown_top = sorted(set(payload) - ALLOWED_TOP_FIELDS)
    if unknown_top:
        problems.append(
            Problem(
                "CONTRACT_SCHEMA", rel_plan, f"unknown contract fields: {unknown_top}"
            )
        )
    version = payload.get("version")
    if type(version) is not int or version != 1:
        problems.append(
            Problem("CONTRACT_SCHEMA", rel_plan, "version must be integer 1")
        )
    assertions = payload.get("assertions")
    if not isinstance(assertions, list):
        return problems + [
            Problem("CONTRACT_SCHEMA", rel_plan, "assertions must be an array")
        ]
    none_reason = payload.get("none_reason")
    if not assertions and (not isinstance(none_reason, str) or not none_reason.strip()):
        problems.append(
            Problem(
                "CONTRACT_SCHEMA",
                rel_plan,
                "empty assertions require a non-empty none_reason",
            )
        )
    seen: set[str] = set()
    for index, assertion in enumerate(assertions):
        where = f"assertions[{index}]"
        if not isinstance(assertion, dict):
            problems.append(
                Problem("CONTRACT_SCHEMA", rel_plan, f"{where} must be an object")
            )
            continue
        assertion_id = assertion.get("id")
        if not isinstance(assertion_id, str) or not assertion_id.strip():
            problems.append(
                Problem("CONTRACT_SCHEMA", rel_plan, f"{where}.id must be non-empty")
            )
        elif assertion_id in seen:
            problems.append(Problem("DUPLICATE_ID", rel_plan, assertion_id))
        else:
            seen.add(assertion_id)
        assertion_type = assertion.get("type")
        if not isinstance(assertion_type, str):
            problems.append(
                Problem("CONTRACT_SCHEMA", rel_plan, f"{where}.type must be a string")
            )
            continue
        allowed = ALLOWED_ASSERTION_FIELDS.get(assertion_type)
        if allowed is None:
            problems.append(
                Problem(
                    "CONTRACT_SCHEMA",
                    rel_plan,
                    f"{where}.type is unsupported: {assertion_type!r}",
                )
            )
            continue
        unknown = sorted(set(assertion) - allowed)
        if unknown:
            problems.append(
                Problem(
                    "CONTRACT_SCHEMA",
                    rel_plan,
                    f"{where} has unknown fields: {unknown}",
                )
            )
        if assertion_type in {"forbid-regex", "require-regex"}:
            paths = assertion.get("paths")
            pattern = assertion.get("pattern")
            if (
                not isinstance(paths, list)
                or not paths
                or not all(isinstance(item, str) and item for item in paths)
            ):
                problems.append(
                    Problem(
                        "CONTRACT_SCHEMA",
                        rel_plan,
                        f"{where}.paths must be non-empty strings",
                    )
                )
            if not isinstance(pattern, str) or not pattern:
                problems.append(
                    Problem(
                        "CONTRACT_SCHEMA",
                        rel_plan,
                        f"{where}.pattern must be non-empty",
                    )
                )
        if assertion_type == "command":
            argv = assertion.get("argv")
            if (
                not isinstance(argv, list)
                or not argv
                or not all(isinstance(item, str) and item for item in argv)
            ):
                problems.append(
                    Problem(
                        "CONTRACT_SCHEMA",
                        rel_plan,
                        f"{where}.argv must be non-empty strings",
                    )
                )
    return problems


def safe_glob(
    repo: Path, pattern: str, assertion_id: str
) -> tuple[list[Path], list[Problem]]:
    pure = PurePosixPath(pattern)
    if pure.is_absolute() or ".." in pure.parts:
        return [], [Problem("PATH_OUTSIDE_REPO", assertion_id, pattern)]
    files: list[Path] = []
    problems: list[Problem] = []
    for candidate in repo.glob(pattern):
        if not candidate.is_file():
            continue
        try:
            candidate.resolve().relative_to(repo.resolve())
        except ValueError:
            problems.append(Problem("PATH_OUTSIDE_REPO", assertion_id, pattern))
            continue
        files.append(candidate)
    if not files and not problems:
        problems.append(Problem("PATH_NO_MATCH", assertion_id, pattern))
    return sorted(set(files)), problems


def run_regex_assertion(
    repo: Path, assertion: dict[str, Any], rel_plan: str
) -> list[Problem]:
    assertion_id = str(assertion["id"])
    try:
        compiled = re.compile(str(assertion["pattern"]), re.MULTILINE)
    except re.error as exc:
        return [Problem("INVALID_REGEX", assertion_id, str(exc))]
    files: list[Path] = []
    problems: list[Problem] = []
    for pattern in assertion["paths"]:
        matched, path_problems = safe_glob(repo, pattern, assertion_id)
        files.extend(matched)
        problems.extend(path_problems)
    if problems:
        return problems
    matches: list[tuple[Path, re.Match[str]]] = []
    for path in sorted(set(files)):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(Problem("FILE_READ", str(path.relative_to(repo)), str(exc)))
            continue
        match = compiled.search(text)
        if match:
            matches.append((path, match))
    assertion_type = assertion["type"]
    if assertion_type == "forbid-regex" and matches:
        for path, match in matches:
            line = path.read_text(encoding="utf-8").count("\n", 0, match.start()) + 1
            problems.append(
                Problem(
                    "FORBIDDEN_MATCH",
                    f"{path.relative_to(repo)}:{line}",
                    assertion_id,
                )
            )
    elif assertion_type == "require-regex" and not matches:
        problems.append(Problem("REQUIRED_MISSING", rel_plan, assertion_id))
    if not problems:
        print(f"PASS {assertion_type} {assertion_id}")
    return problems


def check_tasks(repo: Path, plan: Path, text: str) -> list[Problem]:
    if not is_complete(plan_status(text)):
        return []
    problems: list[Problem] = []
    for target in TASK_LINK_RE.findall(task_section(text)):
        task_path = (plan.parent / target).resolve()
        try:
            rel_task = str(task_path.relative_to(repo.resolve()))
        except ValueError:
            problems.append(Problem("TASK_PATH", str(plan.relative_to(repo)), target))
            continue
        if not task_path.is_file():
            problems.append(
                Problem("TASK_MISSING", rel_task, "linked task does not exist")
            )
            continue
        task_text = task_path.read_text(encoding="utf-8")
        if not is_complete(plan_status(task_text)):
            problems.append(
                Problem("TASK_STATUS", rel_task, plan_status(task_text) or "missing")
            )
        fence: tuple[str, int] | None = None
        for line_number, line in enumerate(task_text.splitlines(), start=1):
            if fence is not None:
                close_match = FENCE_CLOSE_RE.match(line)
                if close_match:
                    marker = close_match.group("marker")
                    if marker[0] == fence[0] and len(marker) >= fence[1]:
                        fence = None
                continue
            open_match = FENCE_OPEN_RE.match(line)
            if open_match:
                marker = open_match.group("marker")
                info = open_match.group("info")
                if marker[0] != "`" or "`" not in info:
                    fence = (marker[0], len(marker))
                    continue
            if UNCHECKED_RE.match(line):
                problems.append(
                    Problem(
                        "UNCHECKED_STEP",
                        f"{rel_task}:{line_number}",
                        "task step is open",
                    )
                )
    return problems


def check_plan(
    repo: Path, rel_plan: str, mode: str, require_contract: bool
) -> list[Problem]:
    plan = (repo / rel_plan).resolve()
    try:
        plan.relative_to(repo.resolve())
    except ValueError:
        return [Problem("PLAN_PATH", rel_plan, "plan is outside repository")]
    if not plan.is_file():
        return [Problem("PLAN_MISSING", rel_plan, "plan does not exist")]
    text = plan.read_text(encoding="utf-8")
    payload, problems = parse_contract(text, rel_plan)
    if (require_contract or payload is not None) and not MAIN_TASK_HEADING_RE.search(
        text
    ):
        problems.append(
            Problem(
                "TASK_SECTION_REQUIRED",
                rel_plan,
                "main plan must contain '## 13. 子任务详情'",
            )
        )
    if payload is None:
        if require_contract:
            problems.append(
                Problem("CONTRACT_REQUIRED", rel_plan, "v1 contract is missing")
            )
        elif not problems:
            print(f"SKIP legacy plan without contract {rel_plan}")
        return problems
    problems.extend(check_tasks(repo, plan, text))
    schema_problems = validate_contract(payload, rel_plan)
    problems.extend(schema_problems)
    if schema_problems:
        return problems
    for assertion in payload["assertions"]:
        if assertion["type"] in {"forbid-regex", "require-regex"}:
            problems.extend(run_regex_assertion(repo, assertion, rel_plan))
            continue
        assertion_id = assertion["id"]
        if mode == "static":
            print(f"SKIP command {assertion_id} (static-only)")
            continue
        try:
            result = subprocess.run(assertion["argv"], cwd=repo, check=False)
        except OSError as exc:
            problems.append(Problem("COMMAND_ERROR", assertion_id, str(exc)))
            continue
        if result.returncode:
            problems.append(
                Problem("COMMAND_FAILED", assertion_id, f"exit={result.returncode}")
            )
        else:
            print(f"PASS command {assertion_id}")
    return problems


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def changed_plans(repo: Path, base: str, head: str) -> list[tuple[str, bool]]:
    output = git_output(
        repo,
        "diff",
        "--name-status",
        "-z",
        "--no-renames",
        base,
        head,
        "--",
        "docs/plans",
    )
    selected: list[tuple[str, bool]] = []
    records = output.split("\0")
    if records and records[-1] == "":
        records.pop()
    if len(records) % 2:
        raise RuntimeError("unexpected NUL-delimited git diff output")
    for index in range(0, len(records), 2):
        status, rel = records[index : index + 2]
        if status == "D" or not rel.endswith(".md"):
            continue
        current = git_output(repo, "show", f"{head}:{rel}")
        if not is_main_plan_candidate(rel, current):
            continue
        require_contract = status == "A"
        if status != "A":
            previous = git_output(repo, "show", f"{base}:{rel}")
            require_contract = not is_complete(plan_status(previous)) and is_complete(
                plan_status(current)
            )
        selected.append((rel, require_contract))
    return selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check plan completion and plan-compliance/v1 assertions."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--plan")
    source.add_argument("--changed-from")
    parser.add_argument("--changed-to")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--static-only", action="store_true")
    mode.add_argument("--run-commands", action="store_true")
    args = parser.parse_args()
    if args.changed_from and not args.changed_to:
        parser.error("--changed-from requires --changed-to")
    if args.changed_to and not args.changed_from:
        parser.error("--changed-to requires --changed-from")
    return args


def main() -> int:
    args = parse_args()
    repo = args.repo_root.resolve()
    mode = "run" if args.run_commands else "static"
    try:
        plans = (
            [(args.plan, True)]
            if args.plan
            else changed_plans(repo, args.changed_from, args.changed_to)
        )
    except RuntimeError as exc:
        print(Problem("GIT_ERROR", "docs/plans", str(exc)).render())
        return 1
    problems: list[Problem] = []
    for rel_plan, require_contract in plans:
        problems.extend(check_plan(repo, rel_plan, mode, require_contract))
    for problem in problems:
        print(problem.render())
    if problems:
        print(f"FAIL plan-compliance problems={len(problems)}")
        return 1
    print(f"PASS plan-compliance plans={len(plans)} mode={mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
