from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "check_plan_completion.py"


class CheckPlanCompletionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.git("init", "-q")
        self.git("config", "user.email", "plan-check@test.local")
        self.git("config", "user.name", "Plan Check")

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            text=True,
            capture_output=True,
        )

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def contract(self, assertions: list[dict[str, object]], **extra: object) -> str:
        payload: dict[str, object] = {"version": 1, "assertions": assertions}
        payload.update(extra)
        return (
            "```json plan-compliance/v1\n"
            + json.dumps(payload, ensure_ascii=False)
            + "\n```"
        )

    def plan(
        self,
        *,
        status: str = "进行中",
        contract: str | None = None,
        task_link: bool = True,
    ) -> str:
        verification = contract or "没有契约。"
        task = "- [Task 1](./02-task1.md)" if task_link else "无任务。"
        return f"""# Sample plan

> 状态：{status}

## 9. 验证

{verification}

## 13. 子任务详情

{task}
"""

    def task(
        self,
        *,
        status: str = "待开始",
        checked: bool = False,
        checkbox: str | None = None,
    ) -> str:
        mark = "x" if checked else " "
        step = checkbox or f"- [{mark}] **Step 1：do work**"
        return f"""# Task 1

> 状态：{status}

{step}
"""

    def run_check(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo-root",
                str(self.root),
                *args,
            ],
            text=True,
            capture_output=True,
        )

    def test_static_mode_checks_regex_and_does_not_execute_commands(self) -> None:
        marker = self.root / "command-ran"
        assertions = [
            {
                "id": "legacy-absent",
                "type": "forbid-regex",
                "paths": ["src/**/*.py"],
                "pattern": "legacy_fallback",
            },
            {
                "id": "classifier-present",
                "type": "require-regex",
                "paths": ["src/**/*.py"],
                "pattern": "classify_day",
            },
            {
                "id": "boundary-test",
                "type": "command",
                "argv": [
                    sys.executable,
                    "-c",
                    f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
                ],
            },
        ]
        self.write("src/service.py", "def classify_day():\n    return 'unknown'\n")
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=self.contract(assertions)),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS forbid-regex legacy-absent", result.stdout)
        self.assertIn("PASS require-regex classifier-present", result.stdout)
        self.assertIn("SKIP command boundary-test", result.stdout)
        self.assertFalse(marker.exists())

    def test_completed_plan_rejects_unchecked_task_step(self) -> None:
        self.write(
            "docs/plans/governance/sample/02-task1.md", self.task(status="✅ 已完成")
        )
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(status="已完成", contract=self.contract([], none_reason="none")),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("UNCHECKED_STEP", result.stdout)

    def test_completed_plan_rejects_all_markdown_unchecked_list_forms(self) -> None:
        for index, checkbox in enumerate(
            ("  - [ ] nested", "* [ ] star", "- [ ]\ttab")
        ):
            with self.subTest(checkbox=checkbox):
                task_path = "docs/plans/governance/sample/02-task1.md"
                plan_path = "docs/plans/governance/sample/01-design.md"
                self.write(task_path, self.task(status="已完成", checkbox=checkbox))
                self.write(
                    plan_path,
                    self.plan(
                        status="已完成", contract=self.contract([], none_reason="none")
                    ),
                )

                result = self.run_check("--plan", plan_path, "--static-only")

                self.assertEqual(result.returncode, 1, f"case={index}\n{result.stdout}")
                self.assertIn("UNCHECKED_STEP", result.stdout)

    def test_completed_plan_ignores_checkbox_examples_in_fenced_code(self) -> None:
        task = (
            self.task(status="已完成", checked=True)
            + "\n```markdown\n- [ ] example\n```\n"
        )
        self.write("docs/plans/governance/sample/02-task1.md", task)
        plan_path = "docs/plans/governance/sample/01-design.md"
        self.write(
            plan_path,
            self.plan(status="已完成", contract=self.contract([], none_reason="none")),
        )

        result = self.run_check("--plan", plan_path, "--static-only")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_long_fence_does_not_hide_unchecked_step_after_literal_short_fence(
        self,
    ) -> None:
        task = self.task(status="已完成", checked=True) + (
            "\n````markdown\n```\n- [ ] example inside code\n````\n- [ ] real unfinished step\n"
        )
        self.write("docs/plans/governance/sample/02-task1.md", task)
        plan_path = "docs/plans/governance/sample/01-design.md"
        self.write(
            plan_path,
            self.plan(status="已完成", contract=self.contract([], none_reason="none")),
        )

        result = self.run_check("--plan", plan_path, "--static-only")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("02-task1.md:11", result.stdout)
        self.assertNotIn("02-task1.md:9", result.stdout)

    def test_completed_plan_rejects_incomplete_task_status(self) -> None:
        self.write("docs/plans/governance/sample/02-task1.md", self.task(checked=True))
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(status="已完成", contract=self.contract([], none_reason="none")),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("TASK_STATUS", result.stdout)

    def test_forbid_regex_reports_file_and_line(self) -> None:
        self.write("src/service.py", "safe = True\nlegacy_fallback = True\n")
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        assertion = {
            "id": "legacy-absent",
            "type": "forbid-regex",
            "paths": ["src/**/*.py"],
            "pattern": "legacy_fallback",
        }
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=self.contract([assertion])),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("FORBIDDEN_MATCH", result.stdout)
        self.assertIn("src/service.py:2", result.stdout)

    def test_require_regex_reports_missing_pattern(self) -> None:
        self.write("src/service.py", "safe = True\n")
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        assertion = {
            "id": "classifier-present",
            "type": "require-regex",
            "paths": ["src/**/*.py"],
            "pattern": "classify_day",
        }
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=self.contract([assertion])),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("REQUIRED_MISSING", result.stdout)

    def test_regex_path_must_match_a_file(self) -> None:
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        assertion = {
            "id": "files-exist",
            "type": "require-regex",
            "paths": ["missing/**/*.py"],
            "pattern": "anything",
        }
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=self.contract([assertion])),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("PATH_NO_MATCH", result.stdout)

    def test_rejects_parent_path_and_invalid_regex(self) -> None:
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        assertions = [
            {
                "id": "outside",
                "type": "forbid-regex",
                "paths": ["../outside.py"],
                "pattern": "x",
            },
            {
                "id": "bad-regex",
                "type": "require-regex",
                "paths": ["src/*.py"],
                "pattern": "[",
            },
        ]
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=self.contract(assertions)),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("PATH_OUTSIDE_REPO", result.stdout)
        self.assertIn("INVALID_REGEX", result.stdout)

    def test_run_commands_propagates_failure(self) -> None:
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        assertion = {
            "id": "boundary-test",
            "type": "command",
            "argv": [sys.executable, "-c", "raise SystemExit(7)"],
        }
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=self.contract([assertion])),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--run-commands"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("COMMAND_FAILED", result.stdout)
        self.assertIn("exit=7", result.stdout)

    def test_new_plan_in_diff_requires_contract(self) -> None:
        self.write("README.md", "fixture\n")
        base = self.commit("base")
        self.write(
            "docs/plans/governance/sample/01-design.md", self.plan(contract=None)
        )
        head = self.commit("add plan")

        result = self.run_check(
            "--changed-from", base, "--changed-to", head, "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("CONTRACT_REQUIRED", result.stdout)

    def test_explicit_plan_requires_contract(self) -> None:
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=None),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--run-commands"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("CONTRACT_REQUIRED", result.stdout)

    def test_in_progress_status_annotation_is_not_complete(self) -> None:
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(
                status="进行中（Task 1–4 已完成；Task 5 待处理）",
                contract=self.contract([], none_reason="no deterministic assertion"),
            ),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("UNCHECKED_STEP", result.stdout)

    def test_annotated_in_progress_transition_requires_contract(self) -> None:
        plan_path = "docs/plans/governance/sample/01-design.md"
        self.write(
            plan_path,
            self.plan(
                status="进行中（Task 1–4 已完成；Task 5 待处理）",
                contract=None,
                task_link=False,
            ),
        )
        base = self.commit("annotated in progress")
        self.write(
            plan_path,
            self.plan(status="已完成", contract=None, task_link=False),
        )
        head = self.commit("complete")

        result = self.run_check(
            "--changed-from", base, "--changed-to", head, "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("CONTRACT_REQUIRED", result.stdout)

    def test_named_new_main_plan_without_task_heading_is_rejected(self) -> None:
        self.write("README.md", "fixture\n")
        base = self.commit("base")
        self.write(
            "docs/plans/governance/sample/01-sample-design.md",
            "# Sample plan\n\n"
            "> 状态：进行中\n\n"
            "## 9. 验证\n\n"
            + self.contract([], none_reason="no deterministic assertion")
            + "\n",
        )
        head = self.commit("add malformed main plan")

        result = self.run_check(
            "--changed-from", base, "--changed-to", head, "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("TASK_SECTION_REQUIRED", result.stdout)
        self.assertNotIn("plans=0", result.stdout)

    def test_completed_transition_in_diff_requires_contract(self) -> None:
        plan_path = "docs/plans/governance/sample/01-design.md"
        self.write(plan_path, self.plan(status="进行中", contract=None, task_link=False))
        base = self.commit("in progress")
        self.write(plan_path, self.plan(status="已完成", contract=None, task_link=False))
        head = self.commit("complete")

        result = self.run_check(
            "--changed-from", base, "--changed-to", head, "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("CONTRACT_REQUIRED", result.stdout)

    def test_unchanged_completed_status_grandfathers_missing_contract(self) -> None:
        plan_path = "docs/plans/governance/sample/01-design.md"
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        self.write(plan_path, self.plan(status="已完成", contract=None, task_link=True))
        base = self.commit("legacy completed plan")
        self.write(
            plan_path,
            self.plan(status="已完成", contract=None, task_link=True) + "\nMore notes.\n",
        )
        head = self.commit("edit legacy prose")

        result = self.run_check(
            "--changed-from", base, "--changed-to", head, "--static-only"
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SKIP legacy plan without contract", result.stdout)

    def test_diff_discovers_quoted_unicode_and_tab_plan_paths(self) -> None:
        self.write("README.md", "fixture\n")
        base = self.commit("base")
        for topic in ("中文", "tab\ttopic"):
            with self.subTest(topic=topic):
                plan_path = f"docs/plans/governance/{topic}/01-design.md"
                self.write(plan_path, self.plan(contract=None, task_link=False))
        head = self.commit("add quoted paths")

        result = self.run_check(
            "--changed-from", base, "--changed-to", head, "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("CONTRACT_REQUIRED"), 2, result.stdout)

    def test_contract_schema_rejects_bool_version_and_non_string_fields(self) -> None:
        invalid_payloads = (
            {"version": True, "assertions": [], "none_reason": "reason"},
            {"version": 1, "assertions": [], "none_reason": None},
            {"version": 1, "assertions": [{"id": "x", "type": [], "argv": ["true"]}]},
        )
        plan_path = "docs/plans/governance/sample/01-design.md"
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                contract = (
                    "```json plan-compliance/v1\n"
                    + json.dumps(payload, ensure_ascii=False)
                    + "\n```"
                )
                self.write(plan_path, self.plan(contract=contract, task_link=False))

                result = self.run_check("--plan", plan_path, "--static-only")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("CONTRACT_SCHEMA", result.stdout)
                self.assertNotIn("Traceback", result.stderr)

    def test_missing_command_is_reported_without_traceback(self) -> None:
        assertion = {
            "id": "missing-command",
            "type": "command",
            "argv": ["definitely-not-a-real-command"],
        }
        plan_path = "docs/plans/governance/sample/01-design.md"
        self.write(
            plan_path, self.plan(contract=self.contract([assertion]), task_link=False)
        )

        result = self.run_check("--plan", plan_path, "--run-commands")

        self.assertEqual(result.returncode, 1)
        self.assertIn("COMMAND_ERROR", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_successful_command_preserves_argv_and_side_effect(self) -> None:
        marker = self.root / "argv.json"
        assertion = {
            "id": "argv-command",
            "type": "command",
            "argv": [
                sys.executable,
                "-c",
                "import json, pathlib, sys; pathlib.Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))",
                str(marker),
                "a value",
                "literal;$HOME",
            ],
        }
        plan_path = "docs/plans/governance/sample/01-design.md"
        self.write(
            plan_path, self.plan(contract=self.contract([assertion]), task_link=False)
        )

        result = self.run_check("--plan", plan_path, "--run-commands")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(marker.read_text()), ["a value", "literal;$HOME"])

    def test_rejects_duplicate_ids_and_unknown_fields(self) -> None:
        self.write("docs/plans/governance/sample/02-task1.md", self.task())
        assertions = [
            {"id": "same", "type": "command", "argv": ["true"]},
            {"id": "same", "type": "command", "argv": ["true"], "mystery": 1},
        ]
        plan = self.write(
            "docs/plans/governance/sample/01-design.md",
            self.plan(contract=self.contract(assertions)),
        )

        result = self.run_check(
            "--plan", str(plan.relative_to(self.root)), "--static-only"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("DUPLICATE_ID", result.stdout)
        self.assertIn("CONTRACT_SCHEMA", result.stdout)


if __name__ == "__main__":
    unittest.main()
