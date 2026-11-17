from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "pr_lessons.py"
_spec = importlib.util.spec_from_file_location("pr_lessons", SCRIPT)
pl = importlib.util.module_from_spec(_spec)
sys.modules["pr_lessons"] = pl
_spec.loader.exec_module(pl)


def pr(number, title, files, body="", merged="2026-10-16T10:00:00Z"):
    return {
        "number": number,
        "title": title,
        "body": body,
        "mergedAt": merged,
        "files": files,
    }


class WatermarkTest(unittest.TestCase):
    def test_parse(self):
        text = "<!-- reviewed-through: 340c00cd (2026-10-16) -->\n# x\n"
        self.assertEqual(pl.parse_watermark(text), "340c00cd")

    def test_parse_missing(self):
        self.assertIsNone(pl.parse_watermark("# lessons\n"))

    def test_set_replaces_existing_and_keeps_blank_line(self):
        text = "<!-- reviewed-through: 340c00cd (2026-10-16) -->\n\n# x\n"
        out = pl.set_watermark(text, "abcdef12", "2026-10-17")
        self.assertEqual(
            out, "<!-- reviewed-through: abcdef12 (2026-10-17) -->\n\n# x\n"
        )

    def test_set_inserts_when_missing(self):
        out = pl.set_watermark("# x\n", "abcdef12", "2026-10-17")
        self.assertTrue(
            out.startswith("<!-- reviewed-through: abcdef12 (2026-10-17) -->\n# x")
        )

    def test_set_rejects_non_sha(self):
        with self.assertRaises(ValueError):
            pl.set_watermark("# x\n", "main", "2026-10-17")


class PrNumbersTest(unittest.TestCase):
    def test_squash_and_merge_styles(self):
        lines = [
            "aaa\tdocs(skills): plan confirmation (#368)",
            "bbb\tMerge pull request #283 from owner/fix/x",
            "ccc\tchore: direct commit without pr",
        ]
        self.assertEqual(pl.pr_numbers_from_log(lines), [368, 283])

    def test_keeps_log_order_and_dedupes(self):
        lines = ["a\tfix: x (#10)", "b\tfix: y (#9)", 'c\tRevert "fix: x (#10)" (#11)']
        self.assertEqual(pl.pr_numbers_from_log(lines), [10, 9, 11])


class ClassifyTest(unittest.TestCase):
    PAY = "apps/api/app_api/services/payment_service.py"

    def test_high_risk_fix_without_plan_is_candidate(self):
        flags = pl.classify(pr(1, "fix(pay): 回调幂等", [self.PAY]), [])
        self.assertIn("high_risk_no_plan", flags)
        self.assertTrue(pl.is_candidate(flags))

    def test_high_risk_with_plan_link_is_candidate(self):
        p = pr(1, "feat: x", [self.PAY], body="关联 docs/plans/commerce/x/README.md")
        flags = pl.classify(p, [])
        self.assertEqual(flags, ["high_risk"])
        self.assertTrue(pl.is_candidate(flags))

    def test_high_risk_with_plan_file_in_diff_is_candidate(self):
        p = pr(1, "feat: x", [self.PAY, "docs/plans/commerce/x/01-design.md"])
        flags = pl.classify(p, [])
        self.assertEqual(flags, ["high_risk"])
        self.assertTrue(pl.is_candidate(flags))

    def test_migration_and_beat_are_high_risk(self):
        self.assertTrue(
            pl.touches_high_risk(
                ["apps/api/app_api/db/migrations/versions/0120_x.py"]
            )
        )
        self.assertTrue(
            pl.touches_high_risk(["apps/worker/app_worker/celery_app.py"])
        )
        self.assertFalse(
            pl.touches_high_risk(["apps/web/src/App.tsx", "docs/03-data-model.md"])
        )

    def test_high_risk_beyond_services(self):
        # Codex review #371：只匹配 services/ 会漏掉路由、模型、集成和三端支付页
        for path in (
            "apps/api/app_api/routers/public/payment.py",
            "apps/api/app_api/models/payment.py",
            "apps/api/app_api/integrations/virtual_payment.py",
            "apps/api/app_api/security.py",
            "apps/agent/app_mcp/app_mcp/oauth_provider.py",
            "apps/web/src/components/QRPaymentContent.tsx",
            "apps/miniprogram/src/utils/subscriptionAction.ts",
            "apps/worker/app_worker/tasks/schedule.py",
        ):
            self.assertTrue(pl.touches_high_risk([path]), path)

    def test_high_risk_ignores_tests_and_lookalikes(self):
        for path in (
            "apps/api/tests/test_payment_service.py",
            "apps/web/src/components/QRPaymentContent.test.tsx",
            "apps/miniprogram/e2e/payment.spec.ts",
            "apps/web/src/components/Border.tsx",
            "docs/plans/commerce/payment/README.md",
        ):
            self.assertFalse(pl.touches_high_risk([path]), path)

    def test_runtime_markdown_counts_as_code_for_overlap(self):
        # Codex review #371：content/books 等运行时 Markdown 不是工程文档
        book = "apps/api/app_api/content/books/quant-intro/ch01.md"
        recent = [pr(5, "feat: 书稿", [book], merged="2026-10-10T00:00:00Z")]
        p = pr(6, "fix: 书稿错字", [book])
        self.assertIn("fix_of_recent", pl.classify(p, recent))

    def test_fix_overlapping_recent_code_file(self):
        recent = [
            pr(
                5,
                "feat: crm",
                ["apps/api/app_api/services/crm.py"],
                merged="2026-10-10T00:00:00Z",
            )
        ]
        p = pr(6, "fix(crm): 口径", ["apps/api/app_api/services/crm.py"])
        self.assertIn("fix_of_recent", pl.classify(p, recent))

    def test_fix_overlapping_only_docs_is_not_fix_of_recent(self):
        recent = [
            pr(5, "feat: crm", ["docs/03-data-model.md"], merged="2026-10-10T00:00:00Z")
        ]
        p = pr(6, "fix: typo", ["docs/03-data-model.md"])
        self.assertNotIn("fix_of_recent", pl.classify(p, recent))

    def test_fix_referencing_recent_pr_number(self):
        recent = [pr(5, "feat: crm", ["a.py"], merged="2026-10-10T00:00:00Z")]
        p = pr(6, "fix: follow-up of #5", ["b.py"])
        self.assertIn("fix_of_recent", pl.classify(p, recent))

    def test_recent_older_than_window_is_ignored(self):
        recent = [pr(5, "feat", ["a.py"], merged="2026-09-01T00:00:00Z")]
        p = pr(6, "fix: x", ["a.py"])
        self.assertNotIn("fix_of_recent", pl.classify(p, recent))

    def test_non_fix_title_never_fix_of_recent(self):
        recent = [pr(5, "feat", ["a.py"], merged="2026-10-10T00:00:00Z")]
        self.assertEqual(pl.classify(pr(6, "feat: more", ["a.py"]), recent), [])

    def test_revert_and_signoff(self):
        self.assertIn("revert", pl.classify(pr(7, 'Revert "feat: x"', ["a.py"]), []))
        p = pr(8, "feat: y", ["a.py"], body="签字放行：xxx 无测试覆盖，接受风险")
        self.assertIn("signoff_or_ci_skipped", pl.classify(p, []))
        p = pr(9, "feat: y", ["a.py"], body="origin CI 未启动（账单）")
        self.assertIn("signoff_or_ci_skipped", pl.classify(p, []))

    def test_signoff_template_and_table_header_are_not_signoff(self):
        # #368 定义签字机制的正文：表头和带 <item> 的模板都不是真签字
        body = (
            "| 关卡 | 时机 | 可否签字放行 |\n"
            "签字有两种：`签字放行：未掌握 <item>，接受风险（理由）`、`签字放行：<item> 无测试覆盖`。\n"
        )
        self.assertEqual(
            pl.classify(
                pr(10, "docs(skills): x", ["skills/a/SKILL.md"], body=body), []
            ),
            [],
        )


class RelatedTest(unittest.TestCase):
    def test_refs_and_overlap_within_window(self):
        recent = [
            pr(5, "feat", ["a.py"], merged="2026-10-10T00:00:00Z"),
            pr(4, "feat", ["c.py"], merged="2026-10-11T00:00:00Z"),
        ]
        p = pr(6, "fix: 修 #3 的遗留", ["a.py"])
        self.assertEqual(pl.related_prs(p, recent), [3, 5])

    def test_revert_ref_older_than_window_is_kept(self):
        p = pr(7, 'Revert "feat: x (#2)"', ["a.py"])
        self.assertEqual(pl.related_prs(p, []), [2])


class TruncateTest(unittest.TestCase):
    def test_short_diff_unchanged(self):
        self.assertEqual(pl.truncate_diff("abc", limit=10), "abc")

    def test_long_diff_truncated_with_marker(self):
        out = pl.truncate_diff("中" * 10, limit=7)  # 每个汉字 3 字节，不能切出半个字符
        self.assertTrue(out.startswith("中中"))
        self.assertIn("diff 已截断：原始 30 字节", out)


class TooLargeDiffTest(unittest.TestCase):
    """实跑发现：#334（+32133 行）的 gh pr diff 返回 HTTP 406 too_large。确定性失败若按瞬时错误
    处理，会让每天的运行都中止、水位永不前移，所以要退回逐文件 patch。"""

    def test_detects_too_large(self):
        stderr = (
            "could not find pull request diff: HTTP 406: Sorry, the diff exceeded the maximum "
            "number of lines (20000) (https://api.github.com/repos/x/y/pulls/334)\n"
            "PullRequest.diff too_large\n"
        )
        self.assertTrue(pl.is_diff_too_large(stderr))
        self.assertFalse(pl.is_diff_too_large("HTTP 403: API rate limit exceeded"))

    def test_diff_from_files_marks_partial_and_missing_patches(self):
        files = [
            {"filename": "a.py", "status": "modified", "patch": "@@ -1 +1 @@\n-x\n+y"},
            {"filename": "big.json", "status": "added"},  # GitHub 对超大文件不给 patch
        ]
        out = pl.diff_from_files(files)
        self.assertTrue(out.startswith("[GitHub 拒绝返回完整 diff"))
        self.assertIn("diff --git a/a.py b/a.py\n@@ -1 +1 @@\n-x\n+y", out)
        self.assertIn("diff --git a/big.json b/big.json\n[added，GitHub 未提供 patch]", out)


class LeakTest(unittest.TestCase):
    def test_detects_by_name_only(self):
        secrets = {
            "LESSONS_GH_TOKEN": "ghp_abcdefghijkl",
            "DEEPSEEK_API_KEY": "sk-zzzzzzzzzz",
        }
        text = "+ 我的 token 是 ghp_abcdefghijkl\n"
        self.assertEqual(pl.leaked_secrets(text, secrets), ["LESSONS_GH_TOKEN"])

    def test_ignores_empty_and_short_values(self):
        self.assertEqual(
            pl.leaked_secrets("abc 1234567", {"A": "", "B": "1234567"}), []
        )


class CheckPathsTest(unittest.TestCase):
    def test_daily_only_lessons(self):
        self.assertEqual(pl.forbidden_paths(["docs/agents/lessons.md"], "daily"), [])
        self.assertEqual(pl.forbidden_paths(["RULES.md"], "daily"), ["RULES.md"])

    def test_weekly_allows_promotion_targets(self):
        ok = [
            "docs/agents/lessons.md",
            "RULES.md",
            "docs/03-data-model.md",
            "apps/api/README.md",
            "libs/app_core/app_core/readme.md",
            "skills/writing-plans/SKILL.md",
        ]
        self.assertEqual(pl.forbidden_paths(ok, "weekly"), [])

    def test_weekly_rejects_code_and_workflow_and_plans(self):
        bad = [
            "apps/api/app_api/services/payment_service.py",
            ".github/workflows/daily-pr-lessons.yml",
            "docs/plans/governance/README.md",
            "CLAUDE.md",
        ]
        self.assertEqual(pl.forbidden_paths(bad, "weekly"), bad)


class CollectTest(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True
        ).stdout

    def init_repo(self, root, *subjects):
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.email", "t@t")
        self.git(root, "config", "user.name", "t")
        self.git(root, "commit", "-q", "--allow-empty", "-m", "base")
        base = self.git(root, "rev-parse", "HEAD").strip()
        for s in subjects:
            self.git(root, "commit", "-q", "--allow-empty", "-m", s)
        return base, self.git(root, "rev-parse", "HEAD").strip()

    def test_collect_writes_context_for_candidates_and_related(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            ctx = Path(tmp) / "context"
            base, head = self.init_repo(
                root, "fix(pay): 回调幂等，修 #1 (#2)", "docs: x (#3)"
            )
            fake = {
                1: pr(
                    1,
                    "feat(pay): 回调",
                    ["apps/api/app_api/services/payment_service.py"],
                    merged="2026-10-10T00:00:00Z",
                ),
                2: pr(
                    2,
                    "fix(pay): 回调幂等，修 #1",
                    ["apps/api/app_api/services/payment_service.py"],
                ),
                3: pr(3, "docs: x", ["docs/x.md"]),
            }
            out = pl.collect_prs(
                base,
                "HEAD",
                fetch_pr=lambda n: fake[n],
                fetch_recent=lambda since: [fake[1]],
                fetch_diff=lambda n: f"diff for {n}\n",
                context_dir=ctx,
                cwd=root,
            )
            self.assertEqual((out["base"], out["head"]), (base, head))
            self.assertEqual([p["number"] for p in out["prs"]], [2, 3])
            first, second = out["prs"]
            self.assertEqual(
                first["flags"], ["fix_of_recent", "high_risk", "high_risk_no_plan"]
            )
            self.assertEqual(first["related"], [1])
            self.assertEqual(
                first["context"], ["pr-1.diff", "pr-1.json", "pr-2.diff", "pr-2.json"]
            )
            self.assertEqual(
                json.loads((ctx / "pr-2.json").read_text())["title"],
                "fix(pay): 回调幂等，修 #1",
            )
            self.assertEqual((ctx / "pr-1.diff").read_text(), "diff for 1\n")
            self.assertFalse(second["candidate"])
            self.assertNotIn("context", second)
            self.assertFalse((ctx / "pr-3.json").exists())  # 非候选不下载

    def test_collect_empty_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_repo(root)
            out = pl.collect_prs(
                "HEAD", "HEAD", fetch_pr=None, fetch_recent=None, cwd=root
            )
            self.assertEqual(out["prs"], [])

    def test_collect_without_context_dir_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, _ = self.init_repo(root, "revert: x (#4)")
            out = pl.collect_prs(
                base,
                "HEAD",
                fetch_pr=lambda n: pr(4, 'Revert "feat: y (#1)"', ["a.py"]),
                fetch_recent=lambda since: [],
                cwd=root,
            )
            self.assertTrue(out["prs"][0]["candidate"])
            self.assertEqual(out["prs"][0]["context"], [])

    def test_related_issue_ref_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            base, _ = self.init_repo(root, "revert: x (#4)")
            fake = {4: pr(4, 'Revert "feat: y"', ["a.py"], body="Closes #9")}
            out = pl.collect_prs(
                base,
                "HEAD",
                fetch_pr=lambda n: fake[n],  # #9 是 issue，KeyError 模拟 gh pr view 失败
                fetch_recent=lambda since: [],
                fetch_diff=lambda n: "d\n",
                context_dir=Path(tmp) / "context",
                is_pull_request=lambda n: False,
                cwd=root,
            )
            item = out["prs"][0]
            self.assertEqual(item["related"], [9])
            self.assertEqual(item["related_missing"], [9])
            self.assertEqual(item["context"], ["pr-4.diff", "pr-4.json"])

    def test_related_pr_transient_failure_aborts(self):
        # Codex review #371：限流 / 网络失败不能被当成「是 issue」吞掉，否则水位前移后永不重试
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            base, _ = self.init_repo(root, "revert: x (#4)")
            fake = {4: pr(4, 'Revert "feat: y (#1)"', ["a.py"])}

            def flaky_diff(n):
                if n == 1:
                    raise RuntimeError("HTTP 403: API rate limit exceeded")
                return "d\n"

            with self.assertRaises(RuntimeError):
                pl.collect_prs(
                    base,
                    "HEAD",
                    fetch_pr=lambda n: fake.get(n) or pr(n, "feat: y", ["a.py"]),
                    fetch_recent=lambda since: [],
                    fetch_diff=flaky_diff,
                    context_dir=Path(tmp) / "context",
                    is_pull_request=lambda n: True,
                    cwd=root,
                )

    def test_related_failure_without_pr_check_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            base, _ = self.init_repo(root, "revert: x (#4)")
            fake = {4: pr(4, 'Revert "feat: y"', ["a.py"], body="Closes #9")}
            with self.assertRaises(KeyError):
                pl.collect_prs(
                    base,
                    "HEAD",
                    fetch_pr=lambda n: fake[n],
                    fetch_recent=lambda since: [],
                    fetch_diff=lambda n: "d\n",
                    context_dir=Path(tmp) / "context",
                    cwd=root,
                )

    def test_prs_resolved_through_commit_association(self):
        # Codex review #371：rebase-merge / 改过标题的 squash 不带 (#N)，要靠 GitHub 的提交↔PR 关联
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, _ = self.init_repo(
                root, "feat: step one", "feat: step two", "docs: tidy (#8)", "chore: x"
            )
            shas = self.git(
                root, "log", "--reverse", "--format=%H", f"{base}..HEAD"
            ).split()
            assoc = {shas[0]: [7], shas[1]: [7], shas[2]: [], shas[3]: []}
            fake = {
                7: pr(7, "feat: rebased", ["a.py"]),
                8: pr(8, "docs: tidy", ["docs/x.md"]),
            }
            out = pl.collect_prs(
                base,
                "HEAD",
                fetch_pr=lambda n: fake[n],
                fetch_recent=lambda since: [],
                fetch_commit_prs=lambda sha: assoc[sha],
                cwd=root,
            )
            self.assertEqual([p["number"] for p in out["prs"]], [7, 8])
            self.assertEqual(out["unassociated_commits"], [shas[3]])


class WorkspaceSyncTest(unittest.TestCase):
    """Codex review #371 P1：模型在没有 .git 的隔离副本里改文件，由可信脚本比对后拷回。"""

    def make_tree(self, root: Path) -> None:
        (root / "docs/agents").mkdir(parents=True)
        (root / "docs/agents/lessons.md").write_text("old\n")
        (root / "RULES.md").write_text("rules\n")
        (root / "CLAUDE.md").write_text("claude\n")
        (root / "AGENTS.md").symlink_to("CLAUDE.md")  # 仓库里真实存在的被跟踪符号链接

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.pristine, self.ws, self.repo = base / "p", base / "ws", base / "repo"
        for d in (self.pristine, self.ws, self.repo):
            d.mkdir()
            self.make_tree(d)
        (self.ws / "_io").mkdir()
        (self.ws / "_io/commit-msg.txt").write_text("lessons: 10-17 复盘\n")
        self.msg_out = base / "msg.txt"

    def tearDown(self):
        self.tmp.cleanup()

    def sync(self, mode="daily"):
        return pl.sync_back(
            self.pristine,
            self.ws,
            self.repo,
            mode,
            ignore="_io",
            commit_msg_out=self.msg_out,
        )

    def test_allowed_change_is_copied_back(self):
        (self.ws / "docs/agents/lessons.md").write_text("new\n")
        self.assertEqual(self.sync(), 0)
        self.assertEqual((self.repo / "docs/agents/lessons.md").read_text(), "new\n")
        self.assertEqual(self.msg_out.read_text(), "lessons: 10-17 复盘\n")

    def test_unchanged_tracked_symlink_is_fine(self):
        self.assertEqual(
            pl.workspace_changes(self.pristine, self.ws, "_io"), ([], [], [])
        )

    def test_git_hook_in_workspace_is_rejected_and_nothing_copied(self):
        (self.ws / "docs/agents/lessons.md").write_text("new\n")
        (self.ws / ".git/hooks").mkdir(parents=True)
        (self.ws / ".git/hooks/pre-commit").write_text("curl evil\n")
        self.assertEqual(self.sync(), 1)
        self.assertEqual((self.repo / "docs/agents/lessons.md").read_text(), "old\n")
        self.assertFalse((self.repo / ".git/hooks/pre-commit").exists())

    def test_new_or_retargeted_symlink_is_invalid(self):
        (self.ws / "docs/agents/leak.md").symlink_to("/proc/self/environ")
        (self.ws / "AGENTS.md").unlink()
        (self.ws / "AGENTS.md").symlink_to("RULES.md")
        _, _, invalid = pl.workspace_changes(self.pristine, self.ws, "_io")
        self.assertEqual(invalid, ["AGENTS.md", "docs/agents/leak.md"])
        self.assertEqual(self.sync(), 1)

    def test_deletion_is_rejected(self):
        (self.ws / "RULES.md").unlink()
        self.assertEqual(
            pl.workspace_changes(self.pristine, self.ws, "_io")[1], ["RULES.md"]
        )
        self.assertEqual(self.sync("weekly"), 1)

    def test_daily_rejects_rules_but_weekly_allows(self):
        (self.ws / "RULES.md").write_text("rules + 新条款\n")
        self.assertEqual(self.sync("daily"), 1)
        self.assertEqual((self.repo / "RULES.md").read_text(), "rules\n")
        self.assertEqual(self.sync("weekly"), 0)
        self.assertEqual((self.repo / "RULES.md").read_text(), "rules + 新条款\n")

    def test_symlinked_commit_message_is_not_copied(self):
        msg = self.ws / "_io/commit-msg.txt"
        msg.unlink()
        msg.symlink_to("/proc/self/environ")
        self.assertEqual(self.sync(), 0)
        self.assertFalse(self.msg_out.exists())


class ExtraFileLeakTest(unittest.TestCase):
    def test_commit_message_is_scanned(self):
        # Codex review #371 P1：模型写的 commit message 也会进 git 历史
        with tempfile.TemporaryDirectory() as tmp:
            msg = Path(tmp) / "msg.txt"
            msg.write_text("lessons: token ghp_abcdefghijkl\n")
            text = pl.read_extra_files([msg, Path(tmp) / "missing.txt"])
            self.assertEqual(
                pl.leaked_secrets(text, {"LESSONS_GH_TOKEN": "ghp_abcdefghijkl"}),
                ["LESSONS_GH_TOKEN"],
            )


if __name__ == "__main__":
    unittest.main()
