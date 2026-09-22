#!/usr/bin/env python3
import argparse
from pathlib import Path

RESOURCE_MAP = {
    "contracts/execution-plan.schema.json": [
        "skills/task-review/references/execution-plan.schema.json",
        "skills/execute-issue/references/execution-plan.schema.json",
        "skills/draft-pr/references/execution-plan.schema.json",
    ],
    "contracts/execution-evidence.schema.json": [
        "skills/execute-issue/references/execution-evidence.schema.json",
        "skills/draft-pr/references/execution-evidence.schema.json",
    ],
    "contracts/findings.schema.json": [
        "skills/draft-pr/references/findings.schema.json",
    ],
    "contracts/project-manifest.schema.json": [
        "skills/task-review/references/project-manifest.schema.json",
        "skills/execute-issue/references/project-manifest.schema.json",
    ],
    "contracts/capability-registry.schema.json": [
        "skills/execute-issue/references/capability-registry.schema.json",
    ],
    "shared/default-capabilities.yaml": [
        "skills/execute-issue/references/default-capabilities.yaml",
    ],
}


def sync_resources(root: Path, check: bool = False, resource_map=None) -> list[str]:
    resource_map = RESOURCE_MAP if resource_map is None else resource_map
    stale = []
    for source_rel, destinations in resource_map.items():
        source = root / source_rel
        source_bytes = source.read_bytes()
        for destination_rel in destinations:
            destination = root / destination_rel
            if destination.exists() and destination.read_bytes() == source_bytes:
                continue
            if check:
                stale.append(destination_rel)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_bytes)
    return stale


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    stale = sync_resources(root, check=args.check)
    if stale:
        for path in stale:
            print(path)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
