import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_minimal_execution_plan_matches_schema():
    schema = load_json(ROOT / "contracts/execution-plan.schema.json")
    plan = load_json(ROOT / "tests/fixtures/execution-plan/minimal-valid.json")
    errors = list(Draft202012Validator(schema).iter_errors(plan))
    assert errors == []


def test_execution_plan_1_1_accepts_structured_references():
    schema = load_json(ROOT / "contracts/execution-plan.schema.json")
    plan = load_json(ROOT / "tests/fixtures/execution-plan/minimal-valid.json")
    plan["execution_plan"]["schema_version"] = "1.1"
    plan["references"] = {
        "specs": [
            {
                "path": "docs/specs/example.md",
                "role": "behavior_contract",
                "required": True,
            }
        ],
        "code": [
            {
                "path": "app/services/example.py",
                "role": "implementation_context",
                "required": False,
            }
        ],
    }

    errors = list(Draft202012Validator(schema).iter_errors(plan))
    assert errors == []


def test_execution_plan_1_0_remains_backward_compatible():
    schema = load_json(ROOT / "contracts/execution-plan.schema.json")
    plan = load_json(ROOT / "tests/fixtures/execution-plan/minimal-valid.json")

    errors = list(Draft202012Validator(schema).iter_errors(plan))
    assert errors == []
