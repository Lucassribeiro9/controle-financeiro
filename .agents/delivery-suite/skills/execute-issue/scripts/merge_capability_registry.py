from copy import deepcopy


def merge_registry(default, local):
    merged = deepcopy(default)
    capabilities = merged.setdefault("capabilities", {})
    for name, override in (local.get("overrides") or {}).items():
        if name not in capabilities:
            raise ValueError(f"unknown capability override: {name}")
        baseline = capabilities[name]
        if "required_behavior" in override:
            required = set(baseline.get("required_behavior", []))
            proposed = set(override.get("required_behavior", []))
            if not required.issubset(proposed):
                raise ValueError(f"cannot weaken required_behavior for {name}")
        baseline.update({k: deepcopy(v) for k, v in override.items()})
    for name, definition in (local.get("custom_capabilities") or {}).items():
        if name in capabilities:
            raise ValueError(f"custom capability already exists: {name}")
        capabilities[name] = deepcopy(definition)
    return merged
