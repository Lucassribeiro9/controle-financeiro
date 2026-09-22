# Execution Protocol

## Stage transitions

```text
pending -> ready      when all depends_on stages are completed
ready -> running      immediately before work begins
running -> completed  when objective and required evidence pass
running -> blocked    when an unmet prerequisite/capability/human dependency prevents progress
running -> failed     after execution and bounded repair cannot satisfy objective
recommended -> skipped only with explicit reason
required -> skipped   forbidden for successful completion
```

A required stage that is not completed prevents `execution.status: completed`.

## Recommended stages

Approval authorizes both required and recommended stages. Attempt every recommended stage. It may be skipped only with an objective reason such as `no_longer_applicable` or `superseded`; record the reason in evidence.

## Parallelism

Parallel execution requires all of:

- dependency independence;
- no overlapping files/modules;
- no shared critical state;
- no coupled contract mutation.

Force sequential execution for Git operations, migrations, same-unit TDD, shared APIs, generated files, or uncertainty about collision/state coupling. Independence is necessary, not sufficient.

## Workspace

Materialize the approved branch/worktree decision only after preflight. Reuse an existing matching workspace when safe. Verify branch-to-worktree association before mutation.
