from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]


def test_each_skill_zip_is_independent_and_small():
    for name in ["task-review", "execute-issue", "draft-pr", "close-delivery"]:
        path = ROOT / "dist" / name / "skill.zip"
        assert path.stat().st_size <= 25 * 1024 * 1024
        with ZipFile(path) as zf:
            names = set(zf.namelist())
            assert any(n.endswith("SKILL.md") for n in names)
            assert any(n.endswith("agents/openai.yaml") for n in names)
            assert not any("../" in n for n in names)
            assert not any("__pycache__" in n or n.endswith(".pyc") for n in names)
            roots = {n.split("/", 1)[0] for n in names if "/" in n}
            assert roots == {name}
