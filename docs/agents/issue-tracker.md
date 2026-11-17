# Issue tracker: GitHub

Issue 和 PRD 都是 `{{GITHUB_REPO}}` 的 GitHub issue，全部用 `gh` CLI 操作。

- 创建：`gh issue create --title "..." --body "..."`（多行 body 用 heredoc）
- 读取：`gh issue view <number> --comments`
- 列表：`gh issue list --state open --json number,title,body,labels,comments`
- 评论：`gh issue comment <number> --body "..."`
- 打标：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`（先读 `triage-labels.md`）
- 关闭：`gh issue close <number> --comment "..."`

如果仓库有多个 remote（例如上游 + 个人 fork），issue 在上游；`gh` 挑错时显式传 `--repo {{GITHUB_REPO}}`。

GitHub 的 issue 和 PR 共用一个编号空间，裸 `#42` 可能是任一种——先 `gh pr view 42`，
失败再回落 `gh issue view 42`。

技能里说「publish to the issue tracker」= 创建一个 GitHub issue；
说「fetch the relevant ticket」= `gh issue view <number> --comments`。
