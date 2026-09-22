# Commit, Publication, and Evidence Policy

## Commits

- Detect and follow repository commit conventions.
- `1 commit = 1 coherent logical change`; never require one commit per stage.
- Implementation and its tests may share a commit.
- Validation-only stages do not require their own commit.
- RED state does not require a separate commit unless repository convention says so.
- Do not mix independent changes.

## Publication

Keep commits local while execution is incomplete. Push once after all required stages/gates and final validations pass. Do not force-push by default. Push failure returns blocked publication and prevents `execution.status: completed`.

```yaml
publication:
  commits_created: 3
  branch: feat/484-card-limits
  remote: origin
  pushed: true
  head: abc123
```

## Execution Evidence

Return structured evidence in conversation/context, not local run files:

```yaml
execution_evidence:
  schema_version: "1.0"
  plan_id: issue-484
  plan_revision: 1
  stages:
    - id: implement_behavior
      status: completed
      evidence:
        files: [cards/selectors.py]
        tests: [tests/cards/test_selectors.py]
  capability_resolution:
    - capability: tdd
      status: resolved
      provider: {type: skill, name: tdd}
  deviations:
    - type: local
      description: Reused existing selector helper.
  publication:
    branch: feat/484-card-limits
    remote: origin
    pushed: true
    head: abc123
  completion:
    required_stages_completed: true
    blocking_gates_passed: true
```
