# PR Lifecycle

Lookup by head branch and behave idempotently:

```text
no PR          -> passing audit creates Draft PR
existing draft -> re-audit current HEAD; update title/body/checklist if needed
ready          -> never demote; report current lifecycle
merged         -> do not reuse or reopen; block normal draft flow
closed         -> do not reuse or reopen silently; block normal draft flow
```

Provider order: GitHub MCP/API preferred, authenticated `gh` fallback. If no remote write provider exists, return `github_write_provider_unavailable`.

After PR creation/update, CI may be `passed|pending|failed|unavailable`. Pending leaves the PR draft. Failed leaves it draft and emits a finding. Never mark ready automatically.

The PR body should derive from the real state and include summary, scope, acceptance coverage, major changes, tests/validation, docs/spec changes, relevant deviations/risks, and `Closes #<issue>` for the intended delivery issue.
