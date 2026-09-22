# Worktree Cleanup

Inspect the delivery worktree with `git status --porcelain`.

If output is non-empty, preserve all local changes. Do not stash, reset, clean, or force-remove. Return partial progress: base/merge/issue verification may remain completed, while worktree and local branch removal stay blocked.

If clean and merge proof is valid:

```bash
git worktree remove <path>
git worktree prune
```

Prune only stale worktree metadata. Worktree removal must occur before local branch deletion.
