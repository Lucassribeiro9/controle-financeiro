import json
from pathlib import Path
from jsonschema import Draft202012Validator
from scripts.validate_execution_plan import validate_execution_plan

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/integration/fixtures/happy-path"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_happy_path_contract_chain_is_compatible():
    plan = load(FIX / "execution-plan.json")
    evidence = load(FIX / "execution-evidence.json")
    plan_schema = load(ROOT / "contracts/execution-plan.schema.json")
    evidence_schema = load(ROOT / "contracts/execution-evidence.schema.json")
    assert list(Draft202012Validator(plan_schema).iter_errors(plan)) == []
    assert validate_execution_plan(plan) == []
    assert list(Draft202012Validator(evidence_schema).iter_errors(evidence)) == []
    assert evidence["plan_id"] == plan["execution_plan"]["plan_id"]
    assert evidence["plan_revision"] == plan["execution_plan"]["revision"]
    assert evidence["publication"]["branch"] == plan["workspace"]["branch"]["suggested_name"]
