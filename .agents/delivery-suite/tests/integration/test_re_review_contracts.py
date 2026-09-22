import json
from pathlib import Path
from jsonschema import Draft202012Validator
from scripts.validate_execution_plan import validate_execution_plan

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests/integration/fixtures/re-review"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_material_discovery_requires_new_revision_and_stales_rev1_evidence():
    request = load("re-review-request.json")
    rev1_evidence = load("rev1-evidence.json")
    rev2_plan = load("rev2-plan.json")
    rev2_evidence = load("rev2-evidence.json")
    schema = json.loads((ROOT / "contracts/execution-plan.schema.json").read_text(encoding="utf-8"))
    assert request["deviation"]["type"] == "material"
    assert request["execution_paused"] is True
    assert rev1_evidence["plan_revision"] != rev2_plan["execution_plan"]["revision"]
    assert list(Draft202012Validator(schema).iter_errors(rev2_plan)) == []
    assert validate_execution_plan(rev2_plan) == []
    assert rev2_evidence["plan_revision"] == rev2_plan["execution_plan"]["revision"]
