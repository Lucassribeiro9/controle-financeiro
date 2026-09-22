from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/draft-pr"


def test_draft_pr_bundle_has_required_files():
    required = {
        "SKILL.md",
        "agents/openai.yaml",
        "references/audit-protocol.md",
        "references/finding-policy.md",
        "references/pr-lifecycle.md",
        "references/execution-plan.schema.json",
        "references/execution-evidence.schema.json",
        "references/findings.schema.json",
    }
    existing = {str(p.relative_to(SKILL)) for p in SKILL.rglob("*") if p.is_file()}
    assert required.issubset(existing)


def test_draft_pr_audits_execution_plan_references():
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "structured references" in skill
