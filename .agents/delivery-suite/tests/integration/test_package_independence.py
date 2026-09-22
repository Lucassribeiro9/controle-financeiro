from pathlib import Path
from scripts.sync_shared_resources import sync_resources

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ["task-review", "execute-issue", "draft-pr", "close-delivery"]


def test_shared_resources_are_fresh():
    assert sync_resources(ROOT, check=True) == []


def test_skills_do_not_reference_external_sibling_sources():
    forbidden = ["delivery-suite/contracts/", "delivery-suite/shared/"]
    sibling_paths = [f"skills/{name}/" for name in SKILLS]
    for skill_name in SKILLS:
        skill = ROOT / "skills" / skill_name
        for path in skill.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert "../.." not in text, path
            for token in forbidden:
                assert token not in text, path
            for sibling in sibling_paths:
                if sibling != f"skills/{skill_name}/":
                    assert sibling not in text, path
