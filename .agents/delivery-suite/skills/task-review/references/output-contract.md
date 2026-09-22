# Output Contract

Return two sections in this order.

## Review Report

Use these headings when applicable:

1. Request understood
2. In scope
3. Out of scope
4. Project context and sources
5. PRD/spec relationship
6. Classification
7. Decisions and assumptions
8. Risks and dependencies
9. Probable affected areas
10. Acceptance evidence and validations
11. Executability and next action
12. Manifest/context drift
13. Derived issue proposals

Explain reasoning here. Keep implementation instructions at technical-intent level, not line-by-line micromanagement.

## Execution Plan

Emit YAML. Example:

```yaml
execution_plan:
  schema_version: "1.1"
  plan_id: issue-484
  revision: 1

issue:
  id: 484
  executable: true

classification:
  primary: behavior
  concerns: [backend, documentation]
  executable_unit: true

execution:
  allowed: true

workspace:
  branch:
    decision: required
    base_branch: main
    suggested_name: feat/484-card-limits
  worktree:
    decision: required
    reuse_existing: true
    suggested_name: 484-card-limits
    suggested_path: ../worktrees/484-card-limits
    reason: behavior_change_with_tdd
    factors: [behavior_change, tdd]

requirements:
  spec:
    decision: not_needed
  prd:
    decision: not_needed

testing:
  tdd:
    decision: required

documentation:
  readme:
    decision: recommended
    action: update

capabilities:
  standard:
    domain: [backend]
    technology: [python, django]
    methodology: [tdd]
    artifacts: [readme-maintenance]
    validation: [unit-testing, regression-testing]
  custom: []

references:
  specs:
    - path: docs/specs/example.md
      role: behavior_contract
      required: true
  code:
    - path: cards/selectors.py
      role: implementation_context
      required: false

assumptions:
  - statement: Existing card selector conventions remain canonical.
    confidence: high
    blocking: false

stages:
  - id: prepare_workspace
    type: workspace
    decision: required
    depends_on: []
  - id: implement_behavior
    type: implementation
    decision: required
    depends_on: [prepare_workspace]
    capabilities: [backend, django, tdd]
    objective: Calculate card limits dynamically without persistence.
    expected_areas: [cards/selectors.py, tests/cards/]
    constraints: [do_not_persist_computed_limits]
    acceptance_evidence: [selector_tests]
  - id: regression
    type: validation
    decision: required
    blocking: true
    depends_on: [implement_behavior]
    capability: regression-testing

approval:
  required: true
  status: pending

next_action:
  type: await_approval

derived_issues: []
```

Use only abstract capabilities. Do not name a Skill as a required provider.
