from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "audit_plans.py"


class AuditPlansTest(unittest.TestCase):
    def git(self, root: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    def run_audit(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        # check_doc_refs 通过 git ls-files 枚举被跟踪文件，因此夹具必须是真实
        # 仓库，且测试写入的文件要在运行前入库。
        self.git(root, "add", "-A")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(root), "--check", *extra],
            text=True,
            capture_output=True,
        )

    def valid_fixture(self) -> Path:
        root = Path(tempfile.mkdtemp())
        self.git(root, "init", "-q")
        self.git(root, "config", "user.email", "audit@test.local")
        self.git(root, "config", "user.name", "audit")
        (root / "docs/plans/strategy/sample").mkdir(parents=True)
        (root / "docs/plans/README.md").write_text("# Plans\n")
        for domain in {
            "agent-platform",
            "clients",
            "commerce",
            "content",
            "governance",
            "growth",
            "market-insight",
            "notifications",
            "strategy",
            "strategy-deployment",
            "trading",
        }:
            domain_dir = root / "docs/plans" / domain
            domain_dir.mkdir(parents=True, exist_ok=True)
            (domain_dir / "README.md").write_text(f"# {domain}\n")
        (root / "docs/plans/strategy/sample/README.md").write_text("# Sample\n")
        return root

    def test_allows_root_level_dated_plan_file(self) -> None:
        root = self.valid_fixture()
        (root / "docs/plans/2026-01-01-old.md").write_text("old\n")
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 0)

    def test_reports_dangling_doc_ref_from_source_file(self) -> None:
        root = self.valid_fixture()
        (root / "apps").mkdir()
        (root / "apps/service.py").write_text(
            '"""设计文档：docs/plans/strategy/gone/01-design.md。"""\n'
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("DANGLING_DOC_REF", result.stdout)

    def test_accepts_source_doc_ref_followed_by_chinese_text(self) -> None:
        # 中文不带空格，靠空格断尾的正则会把整段中文吞进路径而误报。
        root = self.valid_fixture()
        (root / "apps").mkdir()
        (root / "apps/service.py").write_text(
            "# 详见 docs/plans/strategy/sample/README.md。两个入口都在这里。\n"
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_reports_dangling_doc_ref_wrapped_across_docstring_lines(self) -> None:
        # 长路径在 docstring 里折行后，单行匹配只拿到存在的目录前缀而放行；
        # 2026-09-18 lifecycle/08-task-rollout.md 险些因此被删而无人察觉。
        root = self.valid_fixture()
        (root / "scripts").mkdir()
        (root / "scripts/check.py").write_text(
            '"""另外重跑 `docs/plans/strategy/\n    gone-rollout.md` 的两条查询。"""\n'
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("docs/plans/strategy/gone-rollout.md", result.stdout)

    def test_reports_dangling_doc_ref_wrapped_across_comment_lines(self) -> None:
        root = self.valid_fixture()
        (root / "apps").mkdir()
        (root / "apps/service.py").write_text(
            "# 见 docs/plans/strategy/\n#   gone/01-design.md\n"
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("docs/plans/strategy/gone/01-design.md", result.stdout)

    def test_accepts_wrapped_doc_ref_to_existing_file(self) -> None:
        root = self.valid_fixture()
        (root / "apps").mkdir()
        (root / "apps/service.py").write_text(
            "// 见 docs/plans/strategy/\n//   sample/README.md\n"
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_does_not_join_prose_after_directory_ref(self) -> None:
        # 目录引用后面换行接普通英文注释，不能被拼成一个不存在的路径。
        root = self.valid_fixture()
        (root / "apps").mkdir()
        (root / "apps/service.py").write_text(
            "# plans live under docs/plans/strategy/\n# and more notes here\n"
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_accepts_glob_doc_ref_in_source_file(self) -> None:
        # `24-*.md` 是通配描述，不是具体文件；正则若不认 `*` 会截成 `24-` 误报。
        root = self.valid_fixture()
        (root / "apps").mkdir()
        (root / "apps/service.py").write_text(
            "# 取消后无法重新复刻（见 docs/plans/strategy/sample/24-*.md）。\n"
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_requires_readme_for_each_domain_and_topic(self) -> None:
        root = self.valid_fixture()
        (root / "docs/plans/strategy/sample/README.md").unlink()
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING_README", result.stdout)

    def test_reports_missing_relative_markdown_target(self) -> None:
        root = self.valid_fixture()
        (root / "docs/plans/strategy/sample/README.md").write_text(
            "[missing](./gone.md)\n"
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("BROKEN_LINK", result.stdout)

    def test_reports_missing_repo_absolute_plan_target(self) -> None:
        root = self.valid_fixture()
        (root / "docs/plans/strategy/sample/README.md").write_text(
            "See `docs/plans/strategy/missing.md`.\n"
        )
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("BROKEN_REPO_PATH", result.stdout)

    def test_requires_exactly_one_ledger_row_per_baseline_plan(self) -> None:
        root = self.valid_fixture()
        tracked = root / "docs/plans/strategy/sample/design.md"
        tracked.write_text("design\n")
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Audit Test",
                "-c",
                "user.email=audit@example.com",
                "commit",
                "-m",
                "fixture",
            ],
            cwd=root,
            check=True,
            capture_output=True,
        )
        ledger = root / "disposition.tsv"
        ledger.write_text(
            "source_path\tdomain\ttopic\tdecision\tevidence\ttarget_or_authority\n"
            "docs/plans/strategy/sample/design.md\tstrategy\tsample\tbad\te\tt\n"
        )
        result = self.run_audit(root, "--ledger", str(ledger))
        self.assertEqual(result.returncode, 1)
        self.assertIn("LEDGER_DECISION", result.stdout)

    def test_accepts_valid_progressive_disclosure_fixture(self) -> None:
        root = self.valid_fixture()
        result = self.run_audit(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
