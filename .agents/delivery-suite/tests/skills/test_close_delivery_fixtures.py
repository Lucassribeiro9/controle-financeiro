from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_close_delivery_fixtures_have_named_cases():
    case = yaml.safe_load((ROOT / "evals/close-delivery/safety-scenarios.yaml").read_text(encoding="utf-8"))
    assert case["name"]
    names = {item["name"] for item in case["cases"]}
    assert names >= {
        "pr-not-merged", "merge-absent-from-base", "dirty-worktree",
        "unpublished-local-commits", "ambiguous-target", "other-pr-reuses-head",
        "remote-already-absent", "worktree-already-removed", "verified-squash-needs-force-delete",
    }
