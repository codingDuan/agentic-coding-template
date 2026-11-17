# Plan Document Reviewer Prompt Template

Use this template when dispatching a plan document reviewer subagent.

**Purpose:** Verify the plan is complete, matches the spec, and has proper task decomposition and progressive disclosure structure.

**Dispatch after:** The complete plan (main document + all sub-task documents) is written.

```
Task tool (general-purpose):
  description: "Review plan document"
  prompt: |
    You are a plan document reviewer. Verify this plan is complete and ready for implementation.

    **Main plan:** [MAIN_PLAN_FILE_PATH]
    **Sub-task documents:** [LIST_SUB_TASK_FILES]
    **Spec for reference:** [SPEC_FILE_PATH]

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Decision quality | Does §2 identify consequential decisions, rejected alternatives, risks, and surprising scope boundaries? Are behavior changes and semantic drift (RULES §2.1) explicit? |
    | Completeness | TODOs, placeholders, incomplete tasks, missing steps |
    | Spec Alignment | Plan covers spec requirements, no major scope creep |
    | Task Decomposition | Tasks have clear boundaries, steps are actionable |
    | Buildability | Could an engineer follow this plan without getting stuck? |
    | Progressive Disclosure | Main doc is concise (architecture + index + 上线), sub-tasks are self-contained with full details |
    | Status Tracking | Sub-task headers have status fields (待开始/进行中/已完成) |
    | Post-Completion Sections | Sub-tasks have "实际改动" and "踩坑记录" sections reserved |
    | 图 | Flowchart / sequence diagram / state machine present, or an explicit reason each missing one is N/A. Silence is a defect. |
    | 三端兼容 | Changed API/schema/auth/payment/subscription/permission contracts have the every client in RULES.md §3 plus Worker·Internal·MCP matrix filled in |
    | 上线步骤 | Read `docs/agents/release-dimensions.md`: are all eight dimensions present, untouched ones marked "无" rather than omitted, plus 发布顺序 and 回滚? |
    | Worker/MCP 判据 | If the diff touches backend modules, does the plan show it actually checked whether Worker and MCP import the changed modules? When they import backend modules directly rather than calling them over HTTP, so "only backend changed" is not evidence they are unaffected. |
    | 验证 | Does the 验证 section include `make test-critical-scope` (and `make test-critical` for runtime paths) plus the path-scoped tests from `docs/09-test-guide.md`? |

    ## Calibration

    **Only flag issues that would cause real problems during implementation.**
    An implementer building the wrong thing or getting stuck is an issue.
    Minor wording, stylistic preferences, and "nice to have" suggestions are not.

    Approve unless there are serious gaps — missing requirements from the spec,
    contradictory steps, placeholder content, or tasks so vague they can't be acted on.

    ## Output Format

    ## Plan Review

    **Status:** Approved | Issues Found

    **Issues (if any):**
    - [Task X, Step Y]: [specific issue] - [why it matters for implementation]

    **Recommendations (advisory, do not block approval):**
    - [suggestions for improvement]
```

**Reviewer returns:** Status, Issues (if any), Recommendations
