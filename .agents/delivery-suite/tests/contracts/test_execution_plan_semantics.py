from copy import deepcopy
import json
from pathlib import Path
from scripts.validate_execution_plan import validate_execution_plan

ROOT = Path(__file__).resolve().parents[2]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


BASE = load_json(ROOT / "tests/fixtures/execution-plan/minimal-valid.json")


def test_executable_issue_requires_required_branch():
    plan = deepcopy(BASE)
    plan["workspace"]["branch"]["decision"] = "recommended"
    assert "execution.allowed=true requires workspace.branch.decision=required" in validate_execution_plan(plan)


def test_required_tdd_requires_tdd_capability():
    plan = deepcopy(BASE)
    plan["testing"] = {"tdd": {"decision": "required"}}
    assert "testing.tdd=required requires capability tdd" in validate_execution_plan(plan)


def test_unknown_stage_dependency_is_rejected():
    plan = deepcopy(BASE)
    plan["stages"][0]["depends_on"] = ["missing"]
    assert "stage prepare_workspace depends on unknown stage missing" in validate_execution_plan(plan)


def test_duplicate_stage_ids_are_rejected():
    plan = deepcopy(BASE)
    plan["stages"] = [
        {"id": "a", "type": "implementation", "decision": "required", "depends_on": []},
        {"id": "a", "type": "validation", "decision": "required", "depends_on": []}
    ]
    assert "stage ids must be unique" in validate_execution_plan(plan)


def test_cycle_is_rejected():
    plan = deepcopy(BASE)
    plan["stages"] = [
        {"id": "a", "type": "implementation", "decision": "required", "depends_on": ["b"]},
        {"id": "b", "type": "validation", "decision": "required", "depends_on": ["a"]}
    ]
    assert "stage dependency graph contains a cycle" in validate_execution_plan(plan)


def test_approved_revision_must_match_plan_revision():
    plan = deepcopy(BASE)
    plan["approval"]["approved_revision"] = 2
    assert "approved_revision must equal execution_plan.revision" in validate_execution_plan(plan)
