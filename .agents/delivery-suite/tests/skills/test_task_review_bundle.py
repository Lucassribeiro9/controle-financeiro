from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/task-review"


def test_task_review_bundle_has_required_files():
    required = {
        "SKILL.md",
        "agents/openai.yaml",
        "references/review-protocol.md",
        "references/workspace-policy.md",
        "references/output-contract.md",
        "references/execution-plan.schema.json",
        "references/project-manifest.schema.json",
        "scripts/validate_execution_plan.py",
    }
    existing = {str(p.relative_to(SKILL)) for p in SKILL.rglob("*") if p.is_file()}
    assert required.issubset(existing)


def test_task_review_emits_execution_plan_1_1_references():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    output = (SKILL / "references/output-contract.md").read_text(encoding="utf-8")
    protocol = (SKILL / "references/review-protocol.md").read_text(encoding="utf-8")

    assert "schema version 1.1" in skill
    assert "structured references" in skill
    assert 'schema_version: "1.1"' in output
    assert "references:" in output
    assert "Execution Plan `references`" in protocol
