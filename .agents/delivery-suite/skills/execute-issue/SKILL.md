---
name: execute-issue
description: Execute an explicitly approved software-development Execution Plan. Use when an issue plan has already been reviewed and approved and the agent must prepare or reuse the workspace, resolve abstract capabilities, implement stages, test, handle bounded repairs and deviations, create semantic commits, push the branch, and return structured Execution Evidence without reinterpreting material scope.
---

# Execute Issue

Execute one explicitly approved Execution Plan revision. Do not reinterpret material scope.

## Preflight

1. Validate the Execution Plan with `references/execution-plan.schema.json` and `scripts/validate_execution_plan.py`. Accept 1.0 for backward compatibility and consume 1.1 structured references when present.
2. Require `execution.allowed == true`.
3. Require `approval.status == approved` and `approved_revision == execution_plan.revision`.
4. Never silently choose among multiple revisions.
5. Reject an older revision when a newer approved revision is supplied in context.
6. Discover, reuse, or create the approved branch/worktree.
7. Revalidate structured references before use: moved-but-equivalent paths are a local deviation; semantically invalid or obsolete sources are a material deviation that requires re-review.
8. Begin stage execution only after workspace verification.

## Runtime

Read `references/execution-protocol.md` for stage transitions and parallelism. Resolve each ready stage's abstract capabilities using `references/capability-resolution.md`. Read `references/deviation-policy.md` for local/material deviation and bounded repair. Read `references/publication-policy.md` before commit/push and when producing Execution Evidence.

## Completion

Successful completion requires all required stages completed, no blocking gate pending, every recommended stage attempted or explicitly skipped with reason, final validations passed, coherent commits created, and the branch published successfully. Return structured Execution Evidence; do not create `.agents/local/runs/`.
