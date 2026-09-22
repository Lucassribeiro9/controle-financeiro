from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/close-delivery"


def test_close_delivery_bundle_contains_safety_prohibitions():
    text = "\n".join(p.read_text(encoding="utf-8") for p in SKILL.rglob("*.md"))
    required = [
        "stash", "reset --hard", "git clean", "force-remove",
        "merge or rebase automatically", "Never close the issue manually",
        "git branch -D",
    ]
    for phrase in required:
        assert phrase in text
