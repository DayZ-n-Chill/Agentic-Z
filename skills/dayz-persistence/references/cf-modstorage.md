# CF ModStorage contract

How Community Framework (CF) stores one framed block per mod inside an entity's save, what version it hands the mod, and what it does not solve. Open this when a mod saves data on an entity it does not own, or the data must survive the mod being removed and added back.

Third-party content: every `CF_ROOT/...` citation points into the Community Framework scripts (`CF_ROOT` is CF's script root), not into vanilla. Community Framework is not unpacked on `P:\`, so these lines are not yet checked on `P:\`; confirm them in the CF version you build against. The vanilla side of the chain is `EntityAI.OnStoreSave` and `OnStoreLoad` (`P:\scripts\3_game\entities\entityai.c:2910` and `:2978`).

## Scope

Use CF ModStorage when a mod stores data on an entity it does not own, or when that data must survive the mod being removed, the entity being saved again, and the mod later being reinstalled. This contract assumes Community Framework is a dependency. It is not a universal replacement for the vanilla entity stream or for administrator-facing sidecar files.

CF exposes the entity hooks `CF_OnStoreSave` and `CF_OnStoreLoad` at `CF_ROOT/Entities/ItemBase.c:42-44,84-87`.

## Framing

`CF_ModStorageObject.OnStoreSave` writes this outer frame:

1. `CF_ModStorage.VERSION` for the framework data format.
2. The count of mod streams with data.
3. One framed stream for each mod.

The writer and framing are at `CF_ROOT/ModStorage/CF_ModStorageObject.c:46,62,64-71`; the current framework constant is `CF_ModStorage.VERSION = 5` at `CF_ROOT/ModStorage/CF_ModStorage.c:9`.

The outer framework version is not the payload version of every mod. Each mod owns its stream contents and compatibility decisions.

## Version unit: the mod

A mod's version chain is:

`CfgMods storageVersion` -> `ModStructure.GetStorageVersion()` -> `CF_ModStorage.m_Version` -> `CF_ModStorage.GetVersion()`.

The config value is loaded and wired at `CF_ROOT/Mods/ModStructure.c:61-63,307`; CF assigns it to the storage object at `CF_ROOT/ModStorage/CF_ModStorage.c:274`; consumers read it through `GetVersion()` at `CF_ROOT/ModStorage/CF_ModStorage.c:41-44`.

Use that value to branch the mod payload's reader. Do not use the DayZ build as the only mod-format version: two mod releases can write different payloads on the same DayZ build.

## The three compatibility cuts

| Cut | Reader behavior |
|---|---|
| DayZ game version `< 116` | Return success without consuming a CF payload. |
| DayZ game version `116..140` | The current framework-header branch is not entered; no current framed mod records are consumed. |
| DayZ game version `>= 141`, then CF data version `< 2` | Read the framework version, return success before the mod count, and expose no mod records. |

The first cut is implemented at `CF_ROOT/ModStorage/CF_ModStorageObject.c:90-93`. The framework-version cut is at `CF_ROOT/ModStorage/CF_ModStorageObject.c:121-124`. The threshold constants `116`, `141`, and `2` are declared at `CF_ROOT/ModStorage/CF_ModStorage.c:11,12,14`.

Malformed framed reads are not compatibility cuts. A failed framework read emits `FormatError` and returns `false` (`CF_ROOT/ModStorage/CF_ModStorageObject.c:109-113,127-131`). If fewer mod streams are read than the declared count, the load returns `false` (`CF_ROOT/ModStorage/CF_ModStorageObject.c:149-150`). Do not apply staged mod state after either failure.

## Uninstall and reinstall guarantee

CF retains each mod's framed bytes independently from whether that mod is currently loaded. When a known block belongs to an unloaded mod, CF writes the stored bytes back unchanged (`CF_ROOT/ModStorage/CF_ModStorageObject.c:73-77`). Therefore this cycle preserves the block byte for byte:

1. Save with mods A, B, and C loaded.
2. Load without B.
3. Save again while B remains absent.
4. Reinstall B and load the new save.

B cannot consume its payload while absent, but its block remains in the outer frame and becomes available after reinstall. This byte-preserving re-emission is CF ModStorage's differential property.

## What CF does not solve

CF provides framing, mod-specific version delivery, and unloaded-block preservation. The mod still owns all of these obligations:

- Define the payload's field order, types, and independent migrations.
- Classify legacy, known, future, truncated, and rollback inputs.
- Stage payload reads and reject partial state on any failure.
- Back up before automatically rewriting migrated data.
- Rate-limit diagnostics for future or malformed data.
- Provide administrator inspection or repair outside the game when required.
- Provide recoverable sidecar replacement; CF supplies no rename, backup, or atomic file transaction.

CF also cannot preserve a vanilla subclass's unframed appended bytes after that subclass disappears. That guarantee exists only for data written through CF's own per-mod framing.

## Verification checklist

- The outer framework version, mod count, and every stream are read completely.
- The mod payload branches on its `storageVersion` or its own header, not only on the DayZ build.
- Game-build and framework-data compatibility cuts are distinct.
- Failed or partial outer reads return `false` and commit no staged state.
- An unloaded middle mod's raw block is identical after save/load/save.
- Reinstalling the mod exposes the same mod version and payload bytes.
- Payload migration, rollback, and corruption handling are declared separately.
