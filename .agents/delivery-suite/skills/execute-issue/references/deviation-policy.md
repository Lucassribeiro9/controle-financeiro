# Deviation and Failure Policy

## Local deviation

May continue when the approved scope/behavior/public contract remain unchanged. Examples: predicted file moved, existing helper reused, extra test added, small internal refactor, equivalent test command discovered. Record evidence and continue.

## Material deviation

Pause and emit `re_review_request` for any scope/public-contract change, unplanned migration, new security risk, new blocking requirement, new subsystem, substantial unplanned capability, semantic PRD/spec change, or dependency-architecture change. `task-review` owns revision N+1; this Skill never edits an approved revision.

## Bounded repair

```text
max useful attempts: 2
useful attempt = diagnosis + hypothesis + change/repair + revalidation
unchanged rerun does not consume a useful attempt
material discovery bypasses repair and pauses for re-review
```

After two unsuccessful useful local attempts, mark the stage failed/blocked according to the failure. A local operational failure does not automatically imply re-review; a failure that reveals plan insufficiency does.
