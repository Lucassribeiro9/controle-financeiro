def evaluate_cleanup_safety(state):
    merge_proven = bool(
        state.get("pr_merged")
        and state.get("merge_commit_present_in_base")
        and state.get("head_branch_matches_pr")
    )
    worktree_safe = bool(merge_proven and state.get("worktree_clean"))
    local_safe = bool(
        worktree_safe
        and state.get("worktree_removed")
        and not state.get("local_branch_has_unpublished_commits")
    )
    remote_safe = bool(local_safe and not state.get("other_open_pr_uses_head"))
    return {
        "remove_worktree": worktree_safe,
        "delete_local_branch": local_safe,
        "delete_remote_branch": remote_safe,
        "destructive_cleanup_allowed": merge_proven,
    }
