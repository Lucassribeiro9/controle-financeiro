# Branch Cleanup

## Local branch

Try:

```bash
git branch -d <branch>
```

Allow:

```bash
git branch -D <branch>
```

only when all are true: PR proven merged, merge commit present in updated base, PR head matches branch, worktree clean and removed, audited/published branch head corresponds to the delivery, and no unpublished local commits exist. `-D` is never a generic fallback for any deletion error.

## Remote branch

Check whether `origin/<branch>` exists. If absent, no-op. If present, require safe local cleanup and proof that no other active PR uses the same head branch, then run:

```bash
git push origin --delete <branch>
```

## Issue

Verify the merged PR contains the intended closing reference and inspect issue state. If a merged PR with `Closes #<issue>` leaves the issue open, emit warning `expected_auto_close_did_not_occur`. Never close the issue manually.

All steps are idempotent: already-absent worktree/branches and already-closed issue are valid states.
