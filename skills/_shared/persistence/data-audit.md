# Data loss audit

The check run before a release so no saved data is lost or misread, and the report format that reaches the server lead.

## When to run it

Run it on every release that touches a class with `OnStoreSave` or `OnStoreLoad`, a base building `Construction` config, or a saved JSON file. Compare the release candidate with the last released version (its git tag or the last PBO's source). A first release is audited too; its upgrade checks are simply empty.

## Steps

1. **Find every saving class.** Grep the mod's scripts for `OnStoreSave`, `OnStoreLoad`, `AfterStoreLoad` and `EEOnAfterLoad`. Grep the configs for `class Construction`. Grep for `JsonFileLoader` and `FileSerializer`.
2. **List the writes and the reads.** For each class, number every `ctx.Write` in `OnStoreSave` and every `ctx.Read` in `OnStoreLoad`, with the value's type and the version that added it.
3. **Check the pairs.** Every row must pass all of these:
   * `super.OnStoreSave(ctx)` is the first line of the save, and the load returns `false` when `super.OnStoreLoad` does.
   * The mod's own version is the first value written and the first read.
   * Same number of values, same types, same order.
   * Every `Read` checks its return.
   * A write inside an `if` is matched by a read behind a saved flag, not behind a condition that may differ at load time. Vanilla writes a `bool` first and the optional value after it (`P:\scripts\4_world\entities\itembase.c:3194` to `:3206`, read at `:3103` to `:3121`).
4. **Check the upgrade path.** For every version that was ever released, walk the load as if that version wrote the record: every field added later is skipped with a default, every field removed later is still read and thrown away, and no branch returns `false` for an old version.
5. **Check modded vanilla classes.** Any `modded class` of a vanilla type that writes values is a risk on a server that already has saves, and again if the mod is ever removed (see `versioning-and-migration.md`, "Adding saved fields to a vanilla class"). Flag it in the report.
6. **Check base building IDs.** Every part `id` is unique within its object, between 1 and 93, and unchanged from the last release (see `base-building.md`).
7. **Check links.** Entities linked by persistent ID are looked up only in `EEOnAfterLoad` (`P:\scripts\3_game\entities\entityai.c:1393`).
8. **Check files.** Each saved JSON or binary file has a version field and a load path for every older version; files are written only on the server.
9. **Record test evidence.** Note whether both paths were tested: a fresh object, and an object saved by the last release then loaded by this one. Say plainly when a path was not tested.

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
