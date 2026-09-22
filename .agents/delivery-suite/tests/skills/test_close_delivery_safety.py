import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "skills/close-delivery/scripts/evaluate_cleanup_safety.py"
spec = importlib.util.spec_from_file_location("close_delivery_safety", HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
evaluate_cleanup_safety = module.evaluate_cleanup_safety

BASE = {
    "pr_merged": True,
    "merge_commit_present_in_base": True,
    "head_branch_matches_pr": True,
    "worktree_clean": True,
    "worktree_removed": True,
    "local_branch_has_unpublished_commits": False,
    "other_open_pr_uses_head": False,
}


def test_dirty_worktree_blocks_worktree_and_local_branch_removal():
    state = {**BASE, "worktree_clean": False, "worktree_removed": False}
    result = evaluate_cleanup_safety(state)
    assert result["remove_worktree"] is False
    assert result["delete_local_branch"] is False


def test_unverified_merge_blocks_all_destructive_cleanup():
    state = {**BASE, "pr_merged": False}
    result = evaluate_cleanup_safety(state)
    assert not any(result[k] for k in ["remove_worktree", "delete_local_branch", "delete_remote_branch"])


def test_remote_delete_requires_no_other_open_pr():
    state = {**BASE, "other_open_pr_uses_head": True}
    result = evaluate_cleanup_safety(state)
    assert result["delete_remote_branch"] is False
