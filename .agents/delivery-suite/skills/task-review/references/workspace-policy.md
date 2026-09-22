# Workspace Policy

For every executable issue, branch is `required`.

Worktree defaults to `recommended`. Escalate worktree to `required` when any relevant factor exists:

- behavior change with TDD;
- frontend + backend in the same delivery;
- migration;
- multiple subsystems;
- many files with meaningful collision risk;
- parallel execution;
- target branch already checked out in another workspace.

Return explicit rationale:

```yaml
workspace:
  branch:
    decision: required
    base_branch: main
    suggested_name: feat/484-card-limits
  worktree:
    decision: required
    suggested_name: 484-card-limits
    suggested_path: ../worktrees/484-card-limits
    reuse_existing: true
    reason: behavior_change_with_tdd
    factors:
      - behavior_change
      - tdd
```

Task Review only decides and suggests. The executor creates or reuses the workspace after approval.
