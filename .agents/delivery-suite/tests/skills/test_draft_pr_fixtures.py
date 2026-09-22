from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_draft_pr_fixtures_have_cases():
    paths = list((ROOT / "evals/draft-pr").glob("*.yaml"))
    assert paths
    for path in paths:
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert case["name"]
        assert case["cases"]
        for item in case["cases"]:
            assert item["expected"]
