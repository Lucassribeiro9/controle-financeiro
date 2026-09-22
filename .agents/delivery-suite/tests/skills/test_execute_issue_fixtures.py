from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_execute_issue_fixtures_have_cases():
    paths = list((ROOT / "evals/execute-issue").glob("*.yaml"))
    assert paths
    for path in paths:
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert case["name"]
        assert case["cases"]
        for item in case["cases"]:
            assert item["expected"]
