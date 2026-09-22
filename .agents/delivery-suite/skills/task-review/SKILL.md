---
name: task-review
description: Review software-development issues before implementation and produce a human Review Report plus a versioned Execution Plan. Use when an issue, ticket, tracker, bug, feature, refactor, documentation task, or configuration change needs scope clarification, dependency analysis, workspace decisions, capabilities, acceptance evidence, or decomposition before execution.
---

# Task Review

Transform an issue and its verified project context into two outputs: a human Review Report and a machine-readable Execution Plan. Plan only; never implement or mutate Git/GitHub state.

## Workflow

1. Read issue, comments, parent/dependencies, and available project context.
2. Read `.agents/local/project-manifest.yaml` when present; otherwise enter discovery mode.
3. Validate only Manifest claims relevant to the issue against repository evidence.
4. Discover and preserve the stack already used by the project. Distinguish declared stack from observed stack and record drift instead of proposing a replacement stack.
5. Resolve applicable PRD/spec/document paths from the repository when declared paths are missing or stale. Never assume one fixed documentation layout.
6. Read applicable PRD/spec/code/conventions using the source precedence in `references/review-protocol.md`.
7. Classify the issue as executable or tracker/non-executable.
8. Resolve non-blocking uncertainty as explicit assumptions with confidence and `blocking: false`.
9. Use `grill-me` only when material ambiguity remains blocking after repository/source investigation.
10. Build the Review Report.
11. Build an Execution Plan using schema version 1.1, abstract capabilities, DAG stages, and structured references to the applicable PRD/spec/architecture/code sources.
12. Validate the plan against `references/execution-plan.schema.json` and `scripts/validate_execution_plan.py`.
13. Return the Review Report first and the Execution Plan second. Do not execute the plan.

Read `references/workspace-policy.md` when deciding branch/worktree. Read `references/output-contract.md` when formatting the final result. Read `references/review-protocol.md` for source precedence, stack/spec discovery, drift handling, trackers, and authority boundaries.

## Hard Boundaries

Do not edit code or documentation, create branches/worktrees, commit, push, open or update PRs, create GitHub issues, or mutate Project Manifest/Capability Registry. Proposed derived issues remain proposals only.
