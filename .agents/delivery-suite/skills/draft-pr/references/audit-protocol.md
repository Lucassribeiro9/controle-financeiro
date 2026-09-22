# Audit Protocol

Always verify independently:

- head branch and base branch;
- current branch HEAD;
- issue and approved Execution Plan revision;
- commit range and actual diff;
- changed files and scope;
- acceptance criteria;
- spec/docs/test decisions;
- recorded deviations;
- current CI/checks.

Execution Evidence is supplemental. If `execution_evidence.publication.head` differs from current HEAD, mark relevant evidence stale and revalidate risk-relevant checks.

Use risk-based validation: always inspect scope and acceptance. Re-run targeted critical checks when evidence is stale or missing. Same-HEAD CI/evidence may be reused only when it directly covers the requirement.

Preflight must pass before creating/updating a Draft PR.
