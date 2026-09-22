---
name: close-delivery
description: Safely close the local and remote Git lifecycle after a human-merged pull request. Use after merge to resolve the unique delivery target, update the base branch with fast-forward only, prove merge state using GitHub plus local ancestry, verify issue auto-closure, and remove clean worktrees and branches without discarding local work.
---

# Close Delivery

Perform post-merge cleanup only after remote and local merge proof.

## Workflow

1. Resolve an issue number or PR number to exactly one merged PR and its head/base branches.
2. Discover repository root and worktrees, then operate from the primary/base worktree.
3. Fetch/prune and update the base branch with fast-forward only.
4. Obtain authoritative remote merge state and merge commit SHA from GitHub MCP/API, falling back to authenticated `gh`.
5. Verify the merge commit is present in the updated base with local Git ancestry.
6. Evaluate destructive safety with `scripts/evaluate_cleanup_safety.py`.
7. Apply worktree/local/remote branch cleanup only where allowed.
8. Verify issue auto-closure; do not manually close it.
9. Return `completed`, `partial`, or `blocked` with preserved unsafe state.

Read `references/merge-verification.md`, `references/worktree-cleanup.md`, and `references/branch-cleanup.md` before destructive actions.

## Forbidden Actions

Never auto-stash, run `reset --hard`, run destructive `git clean`, force-remove a dirty worktree, merge/rebase the base automatically, manually close the issue, or use `git branch -D` without verified Squash Merge safety predicates.
