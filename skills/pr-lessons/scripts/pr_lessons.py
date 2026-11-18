#!/usr/bin/env python3
"""每日 PR 复盘的确定性部分：水位、候选打标、上下文预下载、隔离副本拷回、改动与密钥检查。

判断「有没有教训」交给模型；本脚本只决定**哪些 PR 交给它、它读得到什么、它改的哪些文件能回到仓库**。
模型步骤拿不到任何 GitHub token，而且只在一份没有 .git 的隔离副本里干活（D5）：候选 PR 的正文、
评论和 diff 由 collect 预先写成文件；它改了什么由 sync-back 逐字节比对原始快照得出，白名单内的才拷回。
标记规则见 docs/plans/governance/daily-pr-lessons/01-design.md §2 筛选表。
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

LESSONS_PATH = "docs/agents/lessons.md"
RECENT_WINDOW = timedelta(days=14)
MAX_DIFF_BYTES = 200_000
MIN_SECRET_LEN = 8
COMMIT_MSG_NAME = "commit-msg.txt"
MAX_COMMIT_MSG_BYTES = 4096

WATERMARK_RE = re.compile(
    r"^<!--\s*reviewed-through:\s*([0-9a-f]{7,40})\b.*-->[ \t]*$", re.M
)
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
SQUASH_PR_RE = re.compile(r"\(#(\d+)\)\s*$")
MERGE_PR_RE = re.compile(r"^Merge pull request #(\d+)\b")
FIX_TITLE_RE = re.compile(r"^(fix|hotfix)\b", re.I)
REVERT_TITLE_RE = re.compile(r"^revert\b", re.I)
PR_REF_RE = re.compile(r"#(\d+)\b")
PLAN_RE = re.compile(r"docs/plans/")
# 真签字是「签字放行：<具体项>」；带 <item> 占位符的是 writing-plans 里的模板（如 #368 正文），不算
SIGNOFF_RE = re.compile(r"签字放行：(?!.*<item>)")
CI_SKIPPED_MARKER = "CI 未启动"

# 高风险路径规则（scopes / exclude_regex / keywords）只在 high-risk.json 里维护，按项目改写。
# 它和本脚本放在同一目录：workflow 把两者一起复制到可信区，脚本按自身位置找它。
# 缺文件或缺字段直接报错，绝不回落成「没有高风险路径」——那会让所有高风险 PR 静默漏掉复盘。
HIGH_RISK_CONFIG = Path(__file__).with_name("high-risk.json")
_high_risk_cache: tuple[tuple[str, ...], re.Pattern[str], tuple[str, ...]] | None = None


def load_high_risk(
    path: Path = HIGH_RISK_CONFIG,
) -> tuple[tuple[str, ...], re.Pattern[str], tuple[str, ...]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scopes = tuple(data["scopes"])
    keywords = tuple(k.lower() for k in data["keywords"])
    if not scopes or not keywords:
        raise ValueError(f"{path}: scopes 和 keywords 都不能为空")
    return scopes, re.compile(data["exclude_regex"]), keywords


def _high_risk_rules() -> tuple[tuple[str, ...], re.Pattern[str], tuple[str, ...]]:
    global _high_risk_cache
    if _high_risk_cache is None:
        _high_risk_cache = load_high_risk()
    return _high_risk_cache


# 工程文档 = docs/09-test-guide.md 里的非运行时路径；产品内容目录里的运行时 Markdown 算代码
DOC_PREFIXES = ("docs/", "skills/")
ROOT_META_DOCS = {
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "REVIEW.md",
    "RULES.md",
    "CONTEXT.md",
    "CHANGELOG.md",
    "LICENSE",
}

# 需要把「被修 / 被回滚的那个 PR」一起交给模型的标记
RELATED_FLAGS = {"fix_of_recent", "revert"}

ALLOWED_PATHS = {
    "daily": (LESSONS_PATH,),
    "weekly": (
        LESSONS_PATH,
        "RULES.md",
        "docs/agents/rules-evidence.md",
        "docs/[0-9][0-9]-*.md",
        "apps/*/README.md",
        "apps/*/readme.md",
        "libs/*/README.md",
        "libs/*/readme.md",
        "skills/*/SKILL.md",
    ),
}


def parse_watermark(text: str) -> str | None:
    m = WATERMARK_RE.search(text)
    return m.group(1) if m else None


def set_watermark(text: str, sha: str, date: str) -> str:
    if not SHA_RE.match(sha):
        raise ValueError(f"not a commit sha: {sha!r}")
    line = f"<!-- reviewed-through: {sha} ({date}) -->"
    if WATERMARK_RE.search(text):
        return WATERMARK_RE.sub(line, text, count=1)
    return f"{line}\n{text}"


def pr_numbers_from_log(lines: list[str]) -> list[int]:
    seen: list[int] = []
    for line in lines:
        subject = line.split("\t", 1)[-1]
        m = SQUASH_PR_RE.search(subject) or MERGE_PR_RE.match(subject)
        if m and int(m.group(1)) not in seen:
            seen.append(int(m.group(1)))
    return seen


def prs_in_range(
    lines: list[str], fetch_commit_prs: Callable[[str], list[int]]
) -> tuple[list[int], list[str]]:
    """以 GitHub 的提交↔PR 关联为准（rebase-merge、改过标题的 squash 都不带 (#N)），
    关联为空才退回解析标题；两者都没有的提交单独列出，不静默丢弃。"""
    numbers: list[int] = []
    unassociated: list[str] = []
    for line in lines:
        sha = line.split("\t", 1)[0]
        found = fetch_commit_prs(sha) or pr_numbers_from_log([line])
        if not found:
            unassociated.append(sha)
        for n in found:
            if n not in numbers:
                numbers.append(n)
    return numbers, unassociated


def _is_high_risk_path(path: str) -> bool:
    scopes, exclude_re, keywords = _high_risk_rules()
    if not path.startswith(scopes) or exclude_re.search(path):
        return False
    lowered = path.lower()
    return any(k in lowered for k in keywords)


def touches_high_risk(files: list[str]) -> bool:
    return any(_is_high_risk_path(f) for f in files)


def _is_doc(path: str) -> bool:
    return path.startswith(DOC_PREFIXES) or path in ROOT_META_DOCS


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _refs(pr: dict) -> set[int]:
    text = f"{pr['title']}\n{pr.get('body') or ''}"
    return {int(n) for n in PR_REF_RE.findall(text)} - {pr["number"]}


def _window(pr: dict, recent: list[dict]) -> list[dict]:
    merged = _parse_time(pr["mergedAt"])
    return [
        r
        for r in recent
        if r["number"] != pr["number"]
        and merged - RECENT_WINDOW <= _parse_time(r["mergedAt"]) < merged
    ]


def _overlapping(pr: dict, window: list[dict]) -> set[int]:
    code_files = {f for f in pr["files"] if not _is_doc(f)}
    return {r["number"] for r in window if code_files & set(r["files"])}


def classify(pr: dict, recent: list[dict]) -> list[str]:
    title, body, files = pr["title"], pr.get("body") or "", pr["files"]
    flags: list[str] = []
    if REVERT_TITLE_RE.match(title):
        flags.append("revert")
    if FIX_TITLE_RE.match(title):
        window = _window(pr, recent)
        refs = _refs(pr)
        if _overlapping(pr, window) or any(r["number"] in refs for r in window):
            flags.append("fix_of_recent")
    if touches_high_risk(files):
        flags.append("high_risk")
        if not PLAN_RE.search(body) and not any(
            f.startswith("docs/plans/") for f in files
        ):
            flags.append("high_risk_no_plan")
    if SIGNOFF_RE.search(body) or CI_SKIPPED_MARKER in body:
        flags.append("signoff_or_ci_skipped")
    return flags


def is_candidate(flags: list[str]) -> bool:
    # 每个分类标记都代表值得复盘的异常或高风险信号；是否有关联计划只用于报告区分，
    # 不能作为豁免，因为公共计划流程不保证执行个人的讲回或模拟飞行门槛。
    return bool(flags)


def related_prs(pr: dict, recent: list[dict]) -> list[int]:
    """引用到的 PR（不限时间，回滚的常是老 PR），加上 14 天内改到同一非文档文件的 PR。"""
    return sorted(_refs(pr) | _overlapping(pr, _window(pr, recent)))


def truncate_diff(text: str, limit: int = MAX_DIFF_BYTES) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= limit:
        return text
    kept = raw[:limit].decode("utf-8", errors="ignore")
    return f"{kept}\n[diff 已截断：原始 {len(raw)} 字节，只保留前 {limit} 字节]\n"


def leaked_secrets(text: str, secrets: dict[str, str]) -> list[str]:
    return sorted(
        name
        for name, value in secrets.items()
        if len(value) >= MIN_SECRET_LEN and value in text
    )


def forbidden_paths(paths: list[str], mode: str) -> list[str]:
    allowed = ALLOWED_PATHS[mode]
    return [p for p in paths if not any(fnmatch.fnmatch(p, pat) for pat in allowed)]


def _walk(root: Path, ignore: str) -> dict[str, Path]:
    """相对路径 → 路径。符号链接（指向文件或目录）作为叶子返回，不跟进；顶层的 ignore 目录跳过。"""
    out: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        if rel_dir == Path("."):
            dirnames[:] = [d for d in dirnames if d != ignore]
        real_dirs = []
        for d in dirnames:
            path = Path(dirpath) / d
            if path.is_symlink():
                out[(rel_dir / d).as_posix()] = path
            else:
                real_dirs.append(d)
        dirnames[:] = real_dirs
        for f in filenames:
            out[(rel_dir / f).as_posix()] = Path(dirpath) / f
    return out


def workspace_changes(
    pristine: Path, workspace: Path, ignore: str
) -> tuple[list[str], list[str], list[str]]:
    """返回 (改动或新增, 删除, 非法)。非法 = 新增或改过指向的符号链接、非普通文件。
    与原始快照一模一样的符号链接（如被跟踪的 AGENTS.md → CLAUDE.md）不算改动。"""
    ws, orig = _walk(workspace, ignore), _walk(pristine, ignore)
    changed: list[str] = []
    invalid: list[str] = []
    for rel, path in ws.items():
        before = orig.get(rel)
        if path.is_symlink():
            same = (
                before is not None
                and before.is_symlink()
                and os.readlink(before) == os.readlink(path)
            )
            if not same:
                invalid.append(rel)
            continue
        if not path.is_file():
            invalid.append(rel)
            continue
        if (
            before is None
            or before.is_symlink()
            or before.read_bytes() != path.read_bytes()
        ):
            changed.append(rel)
    deleted = [rel for rel in orig if rel not in ws]
    return sorted(changed), sorted(deleted), sorted(invalid)


def sync_back(
    pristine: Path,
    workspace: Path,
    repo: Path,
    mode: str,
    ignore: str = "_io",
    commit_msg_out: Path | None = None,
) -> int:
    """比对隔离副本与原始快照，全部合规才把改动拷回真实仓库；任何一项违规都不拷。"""
    changed, deleted, invalid = workspace_changes(pristine, workspace, ignore)
    errors = (
        [f"符号链接或特殊文件：{p}" for p in invalid]
        + [f"删除了文件：{p}" for p in deleted]
        + [f"越界改动（{mode} 模式不允许）：{p}" for p in forbidden_paths(changed, mode)]
    )
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    for rel in changed:
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(workspace / rel, dst)
        print(f"拷回：{rel}")
    if commit_msg_out is not None:
        io_dir = workspace / ignore
        msg = io_dir / COMMIT_MSG_NAME
        if (
            not io_dir.is_symlink()
            and not msg.is_symlink()
            and msg.is_file()
            and msg.stat().st_size <= MAX_COMMIT_MSG_BYTES
        ):
            shutil.copyfile(msg, commit_msg_out)
    return 0


def read_extra_files(paths: list[Path]) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8", errors="ignore") for p in paths if p.is_file()
    )


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(
        cmd, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def _write_context(
    context_dir: Path,
    number: int,
    view: dict,
    fetch_diff: Callable[[int], str],
) -> list[str]:
    context_dir.mkdir(parents=True, exist_ok=True)
    (context_dir / f"pr-{number}.json").write_text(
        json.dumps(view, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (context_dir / f"pr-{number}.diff").write_text(
        truncate_diff(fetch_diff(number)), encoding="utf-8"
    )
    return [f"pr-{number}.diff", f"pr-{number}.json"]


def collect_prs(
    base: str,
    ref: str,
    fetch_pr: Callable[[int], dict] | None,
    fetch_recent: Callable[[str], list[dict]] | None,
    fetch_diff: Callable[[int], str] | None = None,
    context_dir: Path | None = None,
    fetch_commit_prs: Callable[[str], list[int]] | None = None,
    is_pull_request: Callable[[int], bool] | None = None,
    cwd: Path | None = None,
) -> dict:
    log = _run(
        [
            "git",
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%s",
            f"{base}..{ref}",
        ],
        cwd,
    )
    head = _run(["git", "rev-parse", ref], cwd).strip()
    base_sha = _run(["git", "rev-parse", base], cwd).strip()
    lines = [line for line in log.splitlines() if line]
    if fetch_commit_prs is None:
        numbers, unassociated = pr_numbers_from_log(lines), []
    else:
        numbers, unassociated = prs_in_range(lines, fetch_commit_prs)
    out: dict = {
        "base": base_sha,
        "head": head,
        "prs": [],
        "unassociated_commits": unassociated,
    }
    if not numbers:
        return out
    prs = [fetch_pr(n) for n in numbers]
    earliest = min(_parse_time(p["mergedAt"]) for p in prs) - RECENT_WINDOW
    recent = fetch_recent(earliest.date().isoformat())
    by_number = {p["number"]: p for p in prs}
    for p in prs:
        flags = classify(p, recent)
        item = {
            "number": p["number"],
            "title": p["title"],
            "mergedAt": p["mergedAt"],
            "url": p.get("url"),
            "flags": flags,
            "candidate": is_candidate(flags),
        }
        if item["candidate"]:
            item["files"] = p["files"]
            item["related"] = (
                related_prs(p, recent) if RELATED_FLAGS & set(flags) else []
            )
            written: set[str] = set()
            if context_dir is not None:
                for n in [p["number"], *item["related"]]:
                    try:
                        view = by_number.get(n) or fetch_pr(n)
                        written.update(_write_context(context_dir, n, view, fetch_diff))
                    except Exception:
                        # 引用的 #N 常常是 issue（如 "Closes #369"），gh pr view 会失败。只有确认
                        # 「不是 PR」才跳过；限流、网络、写盘失败都让整次失败，水位不前移，下次重试。
                        if n == p["number"] or is_pull_request is None:
                            raise
                        if is_pull_request(n):
                            raise
                        item.setdefault("related_missing", []).append(n)
            item["context"] = sorted(written)
        out["prs"].append(item)
    return out


def _gh_fetch_pr(repo: str) -> Callable[[int], dict]:
    def fetch(number: int) -> dict:
        raw = json.loads(
            _run(
                [
                    "gh",
                    "pr",
                    "view",
                    str(number),
                    "-R",
                    repo,
                    "--json",
                    "number,title,body,mergedAt,files,url,comments",
                ]
            )
        )
        raw["files"] = [f["path"] for f in raw.get("files") or []]
        raw["mergedAt"] = raw.get("mergedAt") or ""
        return raw

    return fetch


def _gh_fetch_recent(repo: str) -> Callable[[str], list[dict]]:
    def fetch(since: str) -> list[dict]:
        raw = json.loads(
            _run(
                [
                    "gh",
                    "pr",
                    "list",
                    "-R",
                    repo,
                    "--state",
                    "merged",
                    "--base",
                    "main",
                    "--search",
                    f"merged:>={since}",
                    "--limit",
                    "200",
                    "--json",
                    "number,mergedAt,files",
                ]
            )
        )
        for r in raw:
            r["files"] = [f["path"] for f in r.get("files") or []]
        return raw

    return fetch


def is_diff_too_large(stderr: str) -> bool:
    return "HTTP 406" in stderr and "too_large" in stderr


def diff_from_files(files: list[dict]) -> str:
    parts = ["[GitHub 拒绝返回完整 diff（超过 20000 行），以下为逐文件 patch，可能不全]"]
    for f in files:
        name = f["filename"]
        patch = f.get("patch") or f"[{f.get('status', '')}，GitHub 未提供 patch]"
        parts.append(f"diff --git a/{name} b/{name}\n{patch}")
    return "\n".join(parts) + "\n"


def _gh_fetch_diff(repo: str) -> Callable[[int], str]:
    def fetch(number: int) -> str:
        try:
            return _run(["gh", "pr", "diff", str(number), "-R", repo])
        except subprocess.CalledProcessError as exc:
            # 超大 PR 的 diff 是确定性拒绝，不是瞬时错误；按瞬时错误中止会让流水线永久卡住
            if not is_diff_too_large(exc.stderr or ""):
                raise
        pages = json.loads(
            _run(
                [
                    "gh",
                    "api",
                    "--paginate",
                    "--slurp",
                    f"repos/{repo}/pulls/{number}/files?per_page=100",
                ]
            )
        )
        return diff_from_files([f for page in pages for f in page])

    return fetch


def _gh_fetch_commit_prs(repo: str) -> Callable[[str], list[int]]:
    def fetch(sha: str) -> list[int]:
        raw = json.loads(_run(["gh", "api", f"repos/{repo}/commits/{sha}/pulls"]))
        return [
            p["number"]
            for p in raw
            if p.get("merged_at") and (p.get("base") or {}).get("ref") == "main"
        ]

    return fetch


def _gh_is_pull_request(repo: str) -> Callable[[int], bool]:
    def check(number: int) -> bool:
        try:
            raw = json.loads(_run(["gh", "api", f"repos/{repo}/issues/{number}"]))
        except subprocess.CalledProcessError as exc:
            if "HTTP 404" in (exc.stderr or ""):
                return False  # 号不存在，也不是 PR
            raise
        return "pull_request" in raw

    return check


def _untracked() -> list[str]:
    out = _run(["git", "ls-files", "--others", "--exclude-standard"])
    return [p for p in out.splitlines() if p]


def _changed_paths(base: str) -> list[str]:
    tracked = _run(["git", "diff", "--name-only", base]).splitlines()
    return sorted({p for p in tracked + _untracked() if p})


def _changed_text(base: str) -> str:
    parts = [_run(["git", "diff", base])]
    for p in _untracked():
        parts.append(Path(p).read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect")
    c.add_argument("--lessons", default=LESSONS_PATH)
    c.add_argument("--since", help="覆盖水位（backfill 用）")
    c.add_argument("--ref", default="origin/main")
    c.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), required=not os.environ.get("GITHUB_REPOSITORY"))
    c.add_argument("--context-dir", type=Path, help="把候选 PR 及关联 PR 的正文、评论、diff 写到这里")

    w = sub.add_parser("set-watermark")
    w.add_argument("--lessons", default=LESSONS_PATH)
    w.add_argument("--sha", required=True)
    w.add_argument("--date", required=True)

    d = sub.add_parser("check-diff")
    d.add_argument("--base", required=True)
    d.add_argument("--mode", choices=sorted(ALLOWED_PATHS), required=True)

    s = sub.add_parser("check-secrets")
    s.add_argument("--base", required=True)
    s.add_argument("--env", action="append", required=True, help="要扫描其原值的环境变量名，可重复")
    s.add_argument(
        "--extra-file",
        action="append",
        type=Path,
        default=[],
        help="同样要扫描的仓库外文件（如 commit message），可重复",
    )

    b = sub.add_parser("sync-back")
    b.add_argument("--pristine", type=Path, required=True)
    b.add_argument("--workspace", type=Path, required=True)
    b.add_argument("--repo", type=Path, default=Path("."))
    b.add_argument("--mode", choices=sorted(ALLOWED_PATHS), required=True)
    b.add_argument("--ignore", default="_io")
    b.add_argument("--commit-msg-out", type=Path)

    args = parser.parse_args(argv)

    if args.cmd == "collect":
        base = args.since or parse_watermark(
            Path(args.lessons).read_text(encoding="utf-8")
        )
        if not base:
            print(f"{args.lessons} 缺 reviewed-through 水位，用 --since 指定", file=sys.stderr)
            return 2
        out = collect_prs(
            base,
            args.ref,
            _gh_fetch_pr(args.repo),
            _gh_fetch_recent(args.repo),
            fetch_diff=_gh_fetch_diff(args.repo),
            context_dir=args.context_dir,
            fetch_commit_prs=_gh_fetch_commit_prs(args.repo),
            is_pull_request=_gh_is_pull_request(args.repo),
        )
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    if args.cmd == "set-watermark":
        path = Path(args.lessons)
        if not path.exists():
            print(f"{path} 不存在", file=sys.stderr)
            return 2
        path.write_text(
            set_watermark(path.read_text(encoding="utf-8"), args.sha, args.date),
            encoding="utf-8",
        )
        return 0

    if args.cmd == "check-secrets":
        secrets = {name: os.environ.get(name, "") for name in args.env}
        text = _changed_text(args.base) + "\n" + read_extra_files(args.extra_file)
        leaked = leaked_secrets(text, secrets)
        for name in leaked:
            print(f"改动里出现了密钥原值：{name}（不打印值）", file=sys.stderr)
        return 1 if leaked else 0

    if args.cmd == "sync-back":
        return sync_back(
            args.pristine,
            args.workspace,
            args.repo,
            args.mode,
            ignore=args.ignore,
            commit_msg_out=args.commit_msg_out,
        )

    bad = forbidden_paths(_changed_paths(args.base), args.mode)
    for p in bad:
        print(f"越界改动（{args.mode} 模式不允许）：{p}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
