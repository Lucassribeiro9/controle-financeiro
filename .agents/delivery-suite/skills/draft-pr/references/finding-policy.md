# Finding Policy

Severity answers whether the finding blocks progress. Classification answers who has authority to resolve it.

```text
informational + local  -> report, do not block
warning + local        -> report, do not block
blocking + local       -> block and return_to execute
blocking + material    -> block and return_to re_review
```

A local finding is resolvable inside the approved plan. A material finding changes scope, public contract, security posture, migration requirements, subsystem structure, or another approved plan boundary.

Never auto-fix a material finding. `draft-pr` is read-only for versioned content.
