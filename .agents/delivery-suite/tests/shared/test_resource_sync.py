from pathlib import Path
from scripts.sync_shared_resources import sync_resources


def test_sync_creates_missing_destination_and_check_detects_stale(tmp_path):
    root = tmp_path
    source = root / "contracts/execution-plan.schema.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"canonical")

    resource_map = {"contracts/execution-plan.schema.json": ["skills/task-review/references/execution-plan.schema.json"]}
    stale = sync_resources(root, check=False, resource_map=resource_map)
    assert stale == []

    destination = root / "skills/task-review/references/execution-plan.schema.json"
    assert destination.read_bytes() == b"canonical"

    destination.write_bytes(b"stale")
    stale = sync_resources(root, check=True, resource_map=resource_map)
    assert stale == ["skills/task-review/references/execution-plan.schema.json"]
    assert destination.read_bytes() == b"stale"
