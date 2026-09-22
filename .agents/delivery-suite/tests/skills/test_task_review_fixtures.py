from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_task_review_eval_fixtures_have_input_and_invariants():
    paths = list((ROOT / "evals/task-review").glob("*.yaml"))
    assert {p.name for p in paths} >= {
        "executable-issue.yaml",
        "tracker-issue.yaml",
        "missing-manifest.yaml",
        "blocking-ambiguity.yaml",
        "existing-stack.yaml",
        "spec-path-drift.yaml",
    }
    for path in paths:
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert case["name"]
        assert case["input"]
        assert case["expected"]["invariants"]
