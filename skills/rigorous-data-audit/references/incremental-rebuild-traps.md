# Atomic-to-phased conversion traps

Three defect classes that appear when a rebuild or recount that used to run in one call is spread over several ticks while other code keeps changing the same live structures. Open this in step 1 whenever a correctness-critical synchronous rebuild or recount becomes multi-tick or incremental over shared live structures.

The case behind it is the source author's LFPowerGrid mod (third-party; measured there, not checkable on `P:\`). The `CLAIM-...` id is the source pack's claim label, kept only for tracing.

## The three defect classes

Rule `CLAIM-R21-RDA-INCREMENTAL-REBUILD`: enumerate the following three defect classes before approving the conversion.

1. **Lost update through a non-gateable mutator.** Classify every concurrent mutator as gateable (for example an RPC handler) or non-gateable (for example an engine lifecycle hook). A non-gateable mutator touching a partially rebuilt live structure requires either retaining the synchronous rebuild or shadow-building and atomically swapping. A gate that postpones an entity death or deletion lifecycle is not a valid fix.
2. **Non-idempotent retry.** If a batch can throw before its cursor commits and its per-item effect is a raw increment, retry re-applies the completed prefix. Commit per item, make the effect a set, or re-clear before retry.
3. **Stuck-flag blast radius.** Grep every consumer of the in-progress flag. A stuck flag can freeze unrelated synchronization or maintenance paths, not only the phased job.

In DayZ terms, the engine lifecycle hooks of point 1 are the `EntityAI` events such as `EEInit` (`P:\scripts\3_game\entities\entityai.c:905`), `EEDelete` (`entityai.c:946`) and `EEKilled` (`entityai.c:1104`): the engine calls them when the entity is created, deleted or killed, and script cannot make the engine wait.

## Iteration stability

Also audit iteration stability. A phased job that keeps a cursor into a live map can skip or repeat keys when concurrent deletion shifts enumeration. A key snapshot plus per-key lookup avoids that cursor drift; a shadow structure plus atomic swap is stronger when the rebuilt index itself is authoritative.

## Severity

Do not misclassify this automatically as on-disk data loss. Session-only maps that self-heal after restart are correctness corruption or degradation with an explicit recovery horizon; persisted structures can raise the severity.

## Evidence

The LFPowerGrid case produced all three defects after an atomic reverse-index rebuild was converted into batches of 16 owners. The accepted correction restored the critical index rebuild to a synchronous atomic operation and kept phased work only over a key snapshot.

The source pack recorded the case in its lessons log, in the LFPowerGrid bug ledger and in a session note of 2026-07-23 on the implementation gates; those private files are not part of this repo.
