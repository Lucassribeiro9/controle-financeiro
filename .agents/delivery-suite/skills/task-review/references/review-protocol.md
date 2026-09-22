# Review Protocol

## Source precedence

Use the first applicable source as the higher authority when sources disagree:

1. PRD
2. applicable spec
3. issue + explicitly approved prior Task Review revision
4. project conventions and Manifest validated against repository evidence
5. specialized Skill guidance
6. general documentation/prompts

Do not treat a Project Manifest as infallible. It is an operational declaration that must be selectively validated against the repository for claims relevant to the current issue.

## Context discovery

### Existing stack

Never replace or redesign an already-defined project stack merely because a generic template expects something else. Discover the observed stack from repository evidence such as:

- `pyproject.toml`, `requirements*.txt`, `package.json`, lockfiles;
- framework configuration and application entrypoints;
- Dockerfile/Compose/container configuration;
- CI/CD workflows;
- repository documentation and Project Manifest;
- imports and code structure when configuration is insufficient.

Report both when useful:

```yaml
project_context:
  stack:
    declared: [python, django]
    observed: [python, django]
    confidence: high
```

If declared and observed stack differ, record evidence-backed drift. Do not block unless the contradiction makes planning unsafe.

### PRD/spec discovery

Do not assume PRD/spec/documentation live in one fixed directory. If a declared path is absent or stale:

1. Search repository filenames and content using issue identifiers, feature IDs, titles, domain terms, and links from nearby documentation.
2. Treat conventional directories such as `docs/`, `specs/`, `.specify/`, `.github/`, `documentation/`, or `architecture/` only as candidates.
3. Verify the content of a candidate before treating it as applicable.
4. If exactly one applicable source is established, use its actual path and record path drift.
5. If several plausible sources remain, resolve from issue links, PRD, scope, and history before asking the user.
6. Ask the user only when the remaining ambiguity is material and blocking.

If no spec exists, determine whether the issue actually needs one. Use `not_needed` when not required; otherwise mark spec `required` and route `next_action` to `generate_spec` or `task_review` as appropriate.

Path drift alone is not a blocker.
Record every source that downstream execution or audit needs in Execution Plan `references`. Use the actual repository path, a concise role, and whether the source is required. The `references` section is optional as a whole for backward compatibility, but schema version 1.1 should include it whenever applicable sources were discovered.


## Classification

Separate primary type from concerns. Examples of primary types include `behavior`, `documentation`, `configuration`, `tracker`, and `mixed`. Set `classification.executable_unit` explicitly.

Tracker issues remain non-executable even when they list technical subtasks. Use `execution.allowed: false` and propose decomposition when there is no single delivery unit.

## Ambiguity

Investigate before asking. Non-blocking uncertainty becomes an assumption:

```yaml
assumptions:
  - statement: Existing selector architecture remains canonical.
    confidence: high
    blocking: false
```

Use `grill-me` only for unresolved blocking ambiguity, one question at a time.

## Drift

Use `informational`, `warning`, or `blocking`. A blocking drift requires a contradiction that prevents a safe plan, such as an authoritative base branch or security rule conflict. Emit `manifest_suggestions` rather than modifying the Manifest.

## Authority boundaries

Never implement; edit code/docs; mutate Project Manifest/Capability Registry; create branch/worktree; commit; push; create/update PR; or create GitHub issues. `derived_issues` are proposals for a later issue-generation capability.
