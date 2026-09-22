# Merge Verification

Accept issue or PR input. Resolve to one unique merged PR with head branch, base branch, and merge commit SHA. Multiple plausible merged PRs produce `ambiguous_delivery_target` and no destructive cleanup.

Invocation may start from any worktree. Use `git rev-parse --show-toplevel` and `git worktree list --porcelain` to identify the primary/base worktree and delivery worktree. Perform base synchronization from the primary worktree.

Synchronize with:

```bash
git fetch --prune
git checkout <base>
git pull --ff-only
```

If fast-forward fails, block destructive cleanup. Never merge or rebase automatically.

Remote proof must come from GitHub MCP/API, or authenticated `gh` fallback, and include merged state, merge commit SHA, head branch, and base branch. Local Git alone is insufficient for destructive cleanup.

Then prove ancestry:

```bash
git merge-base --is-ancestor <merge_commit_sha> <base_branch>
```

Only success allows destructive cleanup predicates to be evaluated.
