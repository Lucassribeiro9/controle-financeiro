import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]

CASES = {
    "execution-evidence.schema.json": {"schema_version": "1.0", "plan_id": "issue-1", "plan_revision": 1, "stages": [], "deviations": [], "completion": {"required_stages_completed": True, "blocking_gates_passed": True}},
    "findings.schema.json": {"schema_version": "1.0", "findings": [{"id": "F-001", "severity": "blocking", "classification": "local", "type": "acceptance_gap", "description": "Missing coverage", "return_to": {"type": "execute"}}]},
    "project-manifest.schema.json": {"schema_version": "1.0", "project": {"name": "example"}, "repository": {"default_branch": "main"}},
    "capability-registry.schema.json": {"schema_version": "1.0", "extends": "default", "overrides": {}, "custom_capabilities": {}}
}


def test_shared_contracts_accept_minimal_instances():
    for name, instance in CASES.items():
        schema = json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))
        assert list(Draft202012Validator(schema).iter_errors(instance)) == []
