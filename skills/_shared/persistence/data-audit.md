# Data loss audit

The check run before a release so no saved data is lost or misread, and the report format that reaches the server lead.

## When to run it

Run it on every release that touches a class with `OnStoreSave` or `OnStoreLoad`, a base building `Construction` config, or a saved JSON file. Compare the release candidate with the last released version (its git tag or the last PBO's source). A first release is audited too; its upgrade checks are simply empty.

## Steps

1. **Find every saving class.** Grep the mod's scripts for `OnStoreSave`, `OnStoreLoad`, `AfterStoreLoad` and `EEOnAfterLoad`. Grep the configs for `class Construction`. Grep for `JsonFileLoader` and `FileSerializer`. If the mod uses Community Framework's ModStorage, also grep for `CF_OnStoreSave` and `CF_OnStoreLoad` (third-party hooks, not checked on `P:\`).
2. **List the writes and the reads.** For each class, number every `ctx.Write` in `OnStoreSave` and every `ctx.Read` in `OnStoreLoad`, with the value's type and the version that added it.
3. **Check the pairs.** Every row must pass all of these:
   * `super.OnStoreSave(ctx)` is the first line of the save, and the load returns `false` when `super.OnStoreLoad` does.
   * The mod's own version is the first value written and the first read.
   * Same number of values, same types, same order.
   * Every `Read` checks its return.
   * A write inside an `if` is matched by a read behind a saved flag, not behind a condition that may differ at load time. Vanilla writes a `bool` first and the optional value after it (`P:\scripts\4_world\entities\itembase.c:3194` to `:3210`, read at `:3107` to `:3122`).
4. **Check the upgrade path.** For every version that was ever released, walk the load as if that version wrote the record: every field added later is skipped with a default, every field removed later is still read and thrown away, and no branch returns `false` for an old version.
5. **Check modded vanilla classes.** Any `modded class` of a vanilla type that writes values is a risk on a server that already has saves, and again if the mod is ever removed (see `versioning-and-migration.md`, "Adding saved fields to a vanilla class"). Flag it in the report.
6. **Check base building IDs.** Every part `id` is unique within its object, between 1 and 93, and unchanged from the last release (see `base-building.md`).
7. **Check links.** Entities linked by persistent ID are looked up only in `EEOnAfterLoad` (`P:\scripts\3_game\entities\entityai.c:1381`); vanilla's comment on `GetEntityByPersitentID` says "This function is available only in this event!" (`:1393`).
8. **Check files.** Each saved JSON or binary file has a version field and a load path for every older version; files are written only on the server.
9. **Record test evidence.** Note whether both paths were tested: a fresh object, and an object saved by the last release then loaded by this one. Say plainly when a path was not tested.
10. **Count the inventory twice.** A list of saving classes built by one search is closed with a second, independent count before anyone reviews it: also grep for `ctx.Read` and `ctx.Write` themselves, and for helper methods that take the context from another class. A table built by one search can list far fewer files than actually contain `ctx.Read` or `ctx.Write`, and miss a whole family of helper hooks. Reviewers treat the table they are handed as complete.
11. **Check no reader counts values past `super`.** The base class data has no fixed width: `EntityAI` writes eight energy values or none (`P:\scripts\3_game\entities\entityai.c:2917` to `:2948`), and construction data may come before them (`save-load-contract.md`, "The base class data has no fixed width"). A load that skips a fixed number of values instead of calling `super.OnStoreLoad` is a finding even when every current test passes.
12. **Check the whole `super` chain, in both directions.** For each saving class, open every class between it and the vanilla base and confirm each override of `OnStoreSave`, `OnStoreLoad`, `AfterStoreLoad` and `EEOnAfterLoad` calls `super`; one missing link breaks every class below it. For a `modded class` on a vanilla base, also list the vanilla classes that inherit from that base and override the method without calling `super`: the modded code never runs for them.
13. **Check the class still exists and will stay in the world.** Compare class name, parent, `scope` and the `CfgPatches` `units[]` entry with the last release, in the config of the built PBO (`versioning-and-migration.md`, "The class must still exist"). Confirm every class that persists has a `types.xml` entry with an explicit lifetime (`save-load-contract.md`, "Saved is not the same as kept: lifetime").
14. **Check file replacement.** No code or comment may claim an atomic save. A replace is `DeleteFile` then `CopyFile` (`P:\scripts\1_core\proto\ensystem.c:528` and `:531`): confirm a backup is made before the delete, the copy is read back and checked, and the temp file is removed only after that check. Where the code has a save path and a recovery path, compare their checks line by line; the typical fault is a recovery path that keeps a destination the save path would have deleted as corrupt.
15. **Check every written file has its cleanup.** For each marker or sidecar file the mod writes, confirm three sites remove or handle it: the success path, the reset or delete of its owner, and the scan at boot that meets a marker with no owner. The only vanilla delete is `DeleteFile` (`P:\scripts\1_core\proto\ensystem.c:528`), so a search for it lists every cleanup site. A file missing from the reset is how an admin reset of a virtual storage mod leaves a slot blocked.
16. **Check state that must survive a restart is on disk.** A flag held only in a member variable is gone after a restart or a mission reload. The vanilla `Mission` class offers `OnMissionStart` and `OnMissionFinish` (`P:\scripts\3_game\gameplay.c:701` and `:702`); a hook such as `OnMissionLoaded` is not on `P:\` and comes from a framework, so a flag set in one hook and read in another holds only if no path reaches the reader without the writer. Where one fact lives in memory and in a file, every operation and every reset must change both.
17. **Check a registry entry leaves only by its own id.** Where the mod keeps its own list of placed entities, an entity with no id must never remove an entry, and the nearest entity is not proof of identity: `GetObjectsAtPosition3D` returns the objects in a sphere and promises no order (`P:\scripts\3_game\global\game.c:930`). List every path that deletes an entity (pickup, refused placement, admin delete, mission shutdown) and confirm each one.

Rules for the evidence itself:

* A finding quotes the code it is about, with `path:line`. A description without the quoted lines is a guess, and the next reader cannot check it.
* Before acting on a list of findings, open the file for each one and confirm it says what the finding claims. In an audit run by several agents with no such check, many of the findings can turn out to be invented.
* A check that reports "nothing to fix" counts only with proof it looked at something: a count above zero, or a planted example it found. A test object younger than the default lifetime, or a storage copy that loaded no items, proves nothing.
* A tolerant parser, a redundant guard or a branch that accepts two formats is robustness, not a defect.

## When to run the deep audit

The steps above are the release check for a normal mod. When a bug would lose player progression on a live server (storage mods, virtual containers, banking, anything with its own files, queues or recovery after a crash), run the full procedure in `deep-audit.md`: mechanical checks first (file name helpers, cleanup of every written marker, every entry point, flags against their files, state transitions), then eight review angles, then a check of every finding against the real file by a reader with fresh context, a cross-actor pass, fixes, a second pass and four tests in game. The report below is still what reaches the server lead.

## Report format

Put this, unchanged, at the end of your report to the script lead; the orchestrator passes it to the server lead before the test build. Keep one section per saving class.

```markdown
# Data audit: <ModName> <new version> (from <last released version>)

Verdict: PASS | FAIL
Server action: none | wipe needed for <classes> | do not roll back after this version

## <ClassName> (scripts/4_World/<path>.c)

Save version: <old> to <new>

| # | Value | Type | Since | Written at | Read at | Result |
|---|---|---|---|---|---|---|
| 1 | save version | int | 1 | :41 | :52 | ok |
| 2 | m_MyMod_Owner | string | 1 | :42 | :56 | ok |
| 3 | m_MyMod_Opens | int | 2 | :43 | :60 | ok, default 0 before v2 |

Upgrade paths checked: v1 to v2
Findings: none

## Base building IDs

| Object | Part | id | Last release id | Result |
|---|---|---|---|---|

## Files

| Path | Version field | Older versions handled | Result |
|---|---|---|---|

## Risks for the server owner

- <modded vanilla class with saved values, rollback warning, or "none">

## Not tested

- <each path that was not run in game, or "none">
```

A FAIL names the class, the row and the fix, and goes back to the persistence specialist through the script lead. A PASS reaches the server lead through the orchestrator; the server lead keeps it with the release notes and passes any server action to the user.
