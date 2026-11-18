#!/usr/bin/env python3
"""Deterministic structure, link, ledger, and scope checks for docs/plans."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

# 领域清单的唯一来源是 docs/plans/README.md 的「领域入口」表：每个领域一行
# `[<slug>](./<slug>/README.md)`。不在脚本里写死，模板换项目时只改 README。
DOMAIN_LINK_RE = re.compile(r"\]\(\./([a-z0-9][a-z0-9-]*)/README\.md\)")
IGNORED_DIRS = {
    ".git",
    ".worktrees",
    ".codex",
    ".claude",
    ".superpowers",
    "node_modules",
}
ARCHIVE = "_archive"
DECISIONS = {
    "keep-active",
    "keep-observing",
    "move-history",
    "merge-delete",
    "authority-delete",
    "covered-delete",
    "keep-unknown",
}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
REPO_PATH_RE = re.compile(r"(?<![\w/])docs/plans/[^\s`)'\"]+")
# 本脚本自身含 docs/plans 正则字面量，其测试夹具会构造不存在的 docs/plans
# 路径；两者都是自指，扫描时必须跳过。
DOC_REF_SKIP_PREFIXES = ("skills/organizing-plans/scripts/",)
# 其他 skill 脚本的测试夹具同样会构造不存在的 docs/plans 路径（如 governance/sample）。
SKILL_TESTS_RE = re.compile(r"^skills/[^/]+/scripts/tests/")
# 源码注释里路径多为裸写，后面常紧跟中文，而中文不带空格——REPO_PATH_RE 靠空格
# 断尾会把整段中文吞进路径（`xxx.md。两个策略`）。这里按字符集断尾，只认路径
# 合法字符，再剥掉尾部的 `.`（句点结尾的英文句子）。字符集含 `*`：注释里的
# `24-*.md` 是通配描述，截成 `24-` 会被当成具体文件误报；带上 `*` 后由
# resolve_target 按通配跳过。
DOC_REF_RE = re.compile(r"(?<![\w/])docs/plans/[A-Za-z0-9._/*-]+")
# 长路径在 docstring / 注释里常被折成两行：`docs/plans/<domain>/<topic>/` 行尾断开，
# 下一行（去掉缩进和 `#` `//` `*` 注释前缀后）才是文件名。单行匹配只拿到存在的目录
# 前缀而放行，删掉文件后引用悄悄失效。续行片段必须含 `.` `-` `/` 之一才拼接，
# 避免把目录引用后面的普通英文注释（`# and more`）拼成不存在的路径。
WRAPPED_DOC_REF_RE = re.compile(
    r"((?<![\w/])docs/plans/[A-Za-z0-9._/-]*/)[ \t]*\r?\n[ \t]*(?:#+|//+|\*|--)?[ \t]*"
    r"(?=[A-Za-z0-9._-]*[./-])"
)


def issue(code: str, path: str, detail: str) -> str:
    return f"{code}\t{path}\t{detail}"


def command(repo: Path, *args: str) -> list[str]:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.splitlines()


def tracked_plan_paths(repo: Path, base_ref: str | None) -> set[str]:
    if base_ref:
        return set(
            command(repo, "ls-tree", "-r", "--name-only", base_ref, "docs/plans")
        )
    return set(command(repo, "ls-files", "docs/plans"))


def strip_fenced(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def resolve_target(path: Path, target: str, repo: Path) -> Path | None:
    target = target.strip().split("#", 1)[0].split("?", 1)[0]
    if not target or target.startswith(
        ("http://", "https://", "mailto:", "#")
    ):
        return None
    # Documentation examples and shell globs describe paths; they are not links
    # that the audit should resolve as concrete files.
    if any(char in target for char in "*?{}") or "..." in target or "<" in target:
        return None
    if target in {
        "url",
        "YYYY-MM-DD-<feature>-task1-<name>.md",
        "YYYY-MM-DD-<feature>-task2-<name>.md",
    }:
        return None
    if target.startswith("/"):
        return repo / target.lstrip("/")
    if target.startswith(("docs/", "apps/", "libs/", "skills/")):
        return repo / target
    if target.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
        return None
    return (path.parent / target).resolve()


def load_domains(index: Path) -> set[str]:
    return set(DOMAIN_LINK_RE.findall(index.read_text(encoding="utf-8")))


def check_structure(repo: Path) -> list[str]:
    plans = repo / "docs/plans"
    problems: list[str] = []
    if not plans.is_dir():
        return [issue("MISSING_PLANS", "docs/plans", "directory does not exist")]
    index = plans / "README.md"
    if not index.is_file():
        return [issue("MISSING_README", "docs/plans", "README.md with the domain table missing")]
    domains = load_domains(index)
    if not domains:
        return [
            issue(
                "NO_DOMAINS",
                "docs/plans/README.md",
                "领域入口 table has no `[slug](./slug/README.md)` rows",
            )
        ]
    # 根层允许存放日期型计划文件：入口口径以 RULES.md 和 writing-plans skill 为准，
    # 本脚本只校验领域目录结构，不拦根层文件。
    for child in plans.iterdir():
        if child.is_dir() and child.name not in domains | {ARCHIVE}:
            problems.append(
                issue(
                    "UNKNOWN_DOMAIN",
                    str(child.relative_to(repo)),
                    "directory is not a registered business domain",
                )
            )
    for domain in sorted(domains):
        domain_dir = plans / domain
        if not domain_dir.is_dir():
            problems.append(
                issue(
                    "MISSING_DOMAIN",
                    str(domain_dir.relative_to(repo)),
                    "domain directory missing",
                )
            )
            continue
        if not (domain_dir / "README.md").is_file():
            problems.append(
                issue(
                    "MISSING_README",
                    str(domain_dir.relative_to(repo)),
                    "domain README.md missing",
                )
            )
        for topic in domain_dir.iterdir():
            if not topic.is_dir():
                continue
            if not (topic / "README.md").is_file():
                problems.append(
                    issue(
                        "MISSING_README",
                        str(topic.relative_to(repo)),
                        "topic README.md missing",
                    )
                )
    archive = plans / ARCHIVE
    if archive.is_dir():
        for domain in archive.iterdir():
            if not domain.is_dir():
                continue
            for topic in domain.iterdir():
                if topic.is_dir() and not (topic / "README.md").is_file():
                    problems.append(
                        issue(
                            "MISSING_README",
                            str(topic.relative_to(repo)),
                            "archive topic README.md missing",
                        )
                    )
    return problems


def check_links(repo: Path) -> list[str]:
    problems: list[str] = []
    for path in repo.rglob("*.md"):
        if any(part in IGNORED_DIRS for part in path.relative_to(repo).parts):
            continue
        text = strip_fenced(path.read_text(encoding="utf-8"))
        targets = list(LINK_RE.findall(text)) + REPO_PATH_RE.findall(text)
        for raw_target in targets:
            target_path = resolve_target(path, raw_target, repo)
            if target_path is not None and not target_path.exists():
                code = (
                    "BROKEN_REPO_PATH"
                    if raw_target.startswith("docs/plans/")
                    else "BROKEN_LINK"
                )
                problems.append(
                    issue(
                        code,
                        str(path.relative_to(repo)),
                        f"target does not exist: {raw_target}",
                    )
                )
    return problems


def check_doc_refs(repo: Path) -> list[str]:
    """非 Markdown 文件里的 docs/plans 引用必须可达。

    check_links 只覆盖 Markdown。源码注释、测试 docstring、CI workflow 和 dev
    脚本里的文档指针同样会被文档移动/删除搞坏，但它们不参与任何构建：类型检查、
    lint、CI 全都不会红，失效只在有人真的去点那个路径时才暴露。历史上这个缺口
    已经让引用悄悄烂掉四次（5ff7cf60 / 83fddcc3 / 349ebc46 / ff41a2e5），
    所以整理计划文档时必须由脚本兜底，而不是靠整理者记得排查。
    """
    problems: list[str] = []
    for rel in command(repo, "ls-files"):
        if (
            rel.endswith(".md")
            or rel.startswith(DOC_REF_SKIP_PREFIXES)
            or SKILL_TESTS_RE.match(rel)
        ):
            continue
        if any(part in IGNORED_DIRS for part in Path(rel).parts):
            continue
        path = repo / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        text = WRAPPED_DOC_REF_RE.sub(r"\1", text)
        for raw_target in DOC_REF_RE.findall(text):
            target = raw_target.rstrip(".")
            target_path = resolve_target(path, target, repo)
            if target_path is not None and not target_path.exists():
                problems.append(
                    issue("DANGLING_DOC_REF", rel, f"target does not exist: {target}")
                )
    return problems


def check_ledger(repo: Path, ledger_path: Path, base_ref: str | None) -> list[str]:
    problems: list[str] = []
    try:
        with ledger_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    except (OSError, csv.Error) as exc:
        return [issue("LEDGER_FORMAT", str(ledger_path), str(exc))]
    required = {
        "source_path",
        "domain",
        "topic",
        "decision",
        "evidence",
        "target_or_authority",
    }
    if not rows or not required.issubset(rows[0]):
        return [
            issue(
                "LEDGER_FORMAT",
                str(ledger_path),
                f"required columns: {sorted(required)}",
            )
        ]
    sources = [row["source_path"] for row in rows]
    for source in sources:
        if not source.startswith("docs/plans/"):
            problems.append(
                issue("LEDGER_SCOPE", source, "source_path must be under docs/plans")
            )
    for duplicate in sorted(
        {source for source in sources if sources.count(source) > 1}
    ):
        problems.append(
            issue("LEDGER_DUPLICATE", duplicate, "source_path appears more than once")
        )
    for row in rows:
        if row["decision"] not in DECISIONS:
            problems.append(
                issue("LEDGER_DECISION", row["source_path"], row["decision"])
            )
    expected = tracked_plan_paths(repo, base_ref)
    actual = set(sources)
    for missing in sorted(expected - actual):
        problems.append(
            issue("LEDGER_MISSING", missing, "tracked baseline path has no disposition")
        )
    for extra in sorted(actual - expected):
        problems.append(issue("LEDGER_EXTRA", extra, "path is not tracked at base-ref"))
    return problems


def check_scope(repo: Path, base_ref: str) -> list[str]:
    allowed = (
        "docs/plans/",
        "docs/api-contract/",
        "docs/agents/",
        "skills/organizing-plans/",
    )
    changed = command(repo, "diff", "--name-only", f"{base_ref}..HEAD")
    problems = []
    for path in changed:
        # Link maintenance may touch Markdown outside docs/plans; runtime code
        # and unrelated skill sources must still be rejected.
        if path.endswith(".md"):
            continue
        if not path.startswith(allowed):
            problems.append(
                issue(
                    "OUT_OF_SCOPE",
                    path,
                    "committed change is outside documentation/skill scope",
                )
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--base-ref")
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    try:
        problems = check_structure(repo) + check_links(repo) + check_doc_refs(repo)
        if args.ledger:
            problems += check_ledger(repo, args.ledger.resolve(), args.base_ref)
        if args.base_ref:
            problems += check_scope(repo, args.base_ref)
    except RuntimeError as exc:
        print(issue("GIT_ERROR", str(repo), str(exc)))
        return 2
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
