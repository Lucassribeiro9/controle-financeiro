---
name: draft-pr
description: Independently audit a published implementation against its approved Execution Plan and create or update the matching Draft Pull Request. Use after execute-issue has pushed a branch and before human review, including re-audits after correction commits. This Skill is read-only for versioned content and may only write Draft PR metadata.
---

# Draft PR

Audit first, then create or update a Draft PR when the audit passes.

## Workflow

1. Read issue, approved Execution Plan revision, optional Execution Evidence, published branch, repository PR template, and conventions.
2. Verify branch, base, current HEAD, issue mapping, commits, diff, changed files, acceptance criteria, structured references from the approved Execution Plan, spec/docs/test decisions, deviations, and CI/checks.
3. Treat branch + HEAD + commits + diff as material truth. Treat Execution Evidence as supplemental and stale it whenever its recorded HEAD differs from current HEAD.
4. Classify findings with `severity` and `classification` using `references/finding-policy.md`.
5. Apply the PR lifecycle in `references/pr-lifecycle.md`.
6. If audit passes, create or update the Draft PR without asking for a second confirmation.
7. Never mutate versioned content.

Read `references/audit-protocol.md` for mandatory checks and risk-based validation.

## Hard Boundaries

Never edit tracked files, commit, push, force-push, mark a PR ready, merge, reopen a closed/merged PR silently, or manually close an issue.
