# Two DayZ persistence facts every audit assumes

Two engine properties that any DayZ mod with saved data inherits: there is no rename or move for files, and the base class writes a varying number of values into the save stream. Open this in step 1; both are found with a search, not by reading the happy path.

## The two facts

Both were read on 1.29.0.163451 and again on `P:\` (game storage version 144). They are engine properties, not project quirks, so any DayZ mod that persists data inherits them.

- **DayZ exposes no rename and no move, so "temp -> verify -> replace" is NOT atomic.** The file primitives stop at `FileExist`, `OpenFile`, `ReadFile`, `CloseFile`, `FPrint`, `FGets`, `MakeDirectory`, `DeleteFile` and `CopyFile` (`P:\scripts\1_core\proto\ensystem.c:397-531`); a grep for `Rename|MoveFile` over `1_core` returns zero. The real replace is `DeleteFile(dest)` followed by `CopyFile(tmp, dest)`, leaving a window in which the destination does not exist. Audit consequence: back up BEFORE that window, verify AFTER the copy, and delete the `.tmp` only once the post-copy verify passes. Treat any code or comment claiming an atomic replace as a finding, not as documentation.

- **`EntityAI.OnStoreSave` writes a runtime-dependent NUMBER of fields.** With an energy component it writes eight, without it none (`P:\scripts\3_game\entities\entityai.c:2917-2948`). Reading by fixed offset after `super.OnStoreLoad` therefore desynchronises only for the configurations that lack the component -- it will pass every test written against the configuration that has it. Audit consequence: any subclass that reads after `super` must read sequentially and check each read's return; a fixed offset is a latent defect even when the current tests are green.

Both belong in the Step 1 mechanical sweep, because both are grep-able and neither is deducible by reading the happy path.

**And the entry-point instance they combine into**, found by this skill's own mechanical check 3 on a save simulator: the normal save path deleted a destination that failed its post-copy verify, while the recovery path left the corrupt bytes in place as the live file. Same invariant, two entry points, one of them silently weaker -- the same shape as VULN-009 in the case study. When a codebase has a `save` and a `recover`, diff their verify branches line by line; do not assume the recovery path inherited the discipline.
