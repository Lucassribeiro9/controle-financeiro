#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def _all_capabilities(plan):
    standard = plan.get("capabilities", {}).get("standard", {})
    values = {cap for group in standard.values() for cap in (group or [])}
    values.update(plan.get("capabilities", {}).get("custom", []) or [])
    return values


def _has_cycle(stages):
    graph = {s["id"]: s.get("depends_on", []) for s in stages if s.get("id") is not None}
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(dep in graph and visit(dep) for dep in graph[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def validate_execution_plan(plan):
    errors = []
    if plan.get("execution", {}).get("allowed") is True and plan.get("workspace", {}).get("branch", {}).get("decision") != "required":
        errors.append("execution.allowed=true requires workspace.branch.decision=required")

    if plan.get("testing", {}).get("tdd", {}).get("decision") == "required" and "tdd" not in _all_capabilities(plan):
        errors.append("testing.tdd=required requires capability tdd")

    stages = plan.get("stages", [])
    ids = [s.get("id") for s in stages]
    if len(ids) != len(set(ids)):
        errors.append("stage ids must be unique")
    known = set(ids)
    for stage in stages:
        for dep in stage.get("depends_on", []):
            if dep not in known:
                errors.append(f"stage {stage.get('id')} depends on unknown stage {dep}")
    if _has_cycle(stages):
        errors.append("stage dependency graph contains a cycle")

    approval = plan.get("approval", {})
    revision = plan.get("execution_plan", {}).get("revision")
    if approval.get("status") == "approved" and approval.get("approved_revision") != revision:
        errors.append("approved_revision must equal execution_plan.revision")
    return errors


def main(argv):
    if len(argv) != 2:
        print("usage: validate_execution_plan.py PLAN.json", file=sys.stderr)
        return 2
    plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    errors = validate_execution_plan(plan)
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
