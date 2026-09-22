# Capability Resolution

Resolve capabilities only when their stage becomes ready:

```text
stage becomes ready
→ load only its required capabilities
→ merge default registry with local delta
→ examine preferred providers in order
→ select first actually available provider
→ if none: apply fallback native|block
→ record resolution in Execution Evidence
```

Use `scripts/merge_capability_registry.py` to enforce the default contract. A local override may change provider priority, add custom capabilities, or make fallback stricter, but may not remove or weaken default `required_behavior`.

Provider examples:

```yaml
capability_resolution:
  capability: tdd
  provider:
    type: skill
    name: tdd
  status: resolved
```

```yaml
capability_resolution:
  capability: spec-authoring
  status: blocked
  reason: no_provider_available
```

The registry resolves who/how; the Execution Plan remains provider-agnostic.
