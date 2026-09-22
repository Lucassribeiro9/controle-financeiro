from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/execute-issue"


def test_execute_issue_bundle_has_required_files():
    required = {
        "SKILL.md",
        "agents/openai.yaml",
        "references/execution-protocol.md",
        "references/capability-resolution.md",
        "references/deviation-policy.md",
        "references/publication-policy.md",
        "references/execution-plan.schema.json",
        "references/execution-evidence.schema.json",
        "references/project-manifest.schema.json",
        "references/capability-registry.schema.json",
        "references/default-capabilities.yaml",
        "scripts/validate_execution_plan.py",
        "scripts/merge_capability_registry.py",
    }
    existing = {str(p.relative_to(SKILL)) for p in SKILL.rglob("*") if p.is_file()}
    assert required.issubset(existing)


def test_execute_issue_revalidates_execution_plan_references():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "structured references" in skill
    assert "local deviation" in skill
    assert "material deviation" in skill
