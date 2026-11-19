# Rebuilds spread over several ticks

Which defects appear when a rebuild or recount that ran in one call is split over several ticks while other code keeps changing the same live structures. Check it in step 1 of `deep-audit.md` whenever a rebuild that correctness depends on becomes phased.

The case behind it is a third-party power grid mod; its behaviour was measured in that mod and is not checkable on `P:\`. A reverse index that was rebuilt in one call was changed to rebuild in batches of 16 owners, and all three defects below appeared. The accepted fix put the index rebuild back into one call and kept the phased work only over a snapshot of the keys.

## Three defects to rule out first

Rule out all three before approving the change.

1. **A lost update from code you cannot hold back.** Sort every other piece of code that changes the structure into what you can hold back (an RPC handler) and what you cannot (an engine lifecycle hook). When code you cannot hold back touches a half rebuilt structure, keep the rebuild in one call, or build a copy and swap it in at once. Holding back the death or deletion of an entity is not a valid fix.
2. **A retry that applies work twice.** When a batch can throw before its cursor is saved and each item adds to a counter, a retry adds the finished items again. Save the cursor per item, set the value instead of adding to it, or clear before the retry.
3. **A stuck "in progress" flag.** Find every reader of the flag. A flag left on can freeze sync or maintenance code that has nothing to do with the phased job.

The engine lifecycle hooks of point 1 are the `EntityAI` events such as `EEInit` (`P:\scripts\3_game\entities\entityai.c:905`), `EEDelete` (`entityai.c:946`) and `EEKilled` (`entityai.c:1104`). The engine calls them when an entity is created, deleted or killed, and script cannot make the engine wait.

## A cursor into a live map

A phased job that keeps a cursor into a live map can skip or repeat keys when another piece of code deletes entries during the walk. Taking a snapshot of the keys and looking each one up avoids that. When the rebuilt index is itself the truth, building a copy and swapping it in is safer still.

## Severity

This is not data loss on disk by default. A map that lives only for the session and heals after a restart is corruption or degraded behaviour until the next restart; a structure that is saved raises the severity.
