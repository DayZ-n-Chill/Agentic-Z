# Community Framework ModStorage

How Community Framework (CF) stores one framed block per mod inside an entity's save, which version number it hands the mod, and what it leaves to the mod. Open this when a mod saves data on an entity it does not own, or the data must survive the mod being removed and added back.

Third-party behaviour: every `CF_ROOT/...` line below points into the Community Framework scripts (`CF_ROOT` is CF's script root). CF is not unpacked on `P:\`, so none of these lines is checked there; confirm them in the CF version the mod builds against. The vanilla end of the chain is `EntityAI.OnStoreSave` and `OnStoreLoad` (`P:\scripts\3_game\entities\entityai.c:2910` and `:2978`). The CF API itself is described in `_shared/enscript/integrations/community_framework.md`.

## The hooks

CF gives an entity `CF_OnStoreSave` and `CF_OnStoreLoad` (`CF_ROOT/Entities/ItemBase.c:42-44` and `:84-87`). The mod writes and reads its own block there, not in `OnStoreSave`.

## The frame

`CF_ModStorageObject.OnStoreSave` writes, in order (`CF_ROOT/ModStorage/CF_ModStorageObject.c:46`, `:62`, `:64-71`):

1. `CF_ModStorage.VERSION`, the framework's own format version (5 at `CF_ROOT/ModStorage/CF_ModStorage.c:9`).
2. The number of mod blocks that hold data.
3. One framed block per mod.

The framework version is not the version of any mod's data. Each mod owns its block and its upgrade paths.

## The mod's version

The chain is `CfgMods` `storageVersion`, then `ModStructure.GetStorageVersion()`, then `CF_ModStorage.m_Version`, read with `CF_ModStorage.GetVersion()` (`CF_ROOT/Mods/ModStructure.c:61-63` and `:307`; assigned at `CF_ROOT/ModStorage/CF_ModStorage.c:274`; getter at `:41-44`).

Branch the mod's reader on that value or on a version the mod writes into its own block. Never on the game build alone: two mod releases can write different blocks on the same game build.

## The three compatibility cuts

| Cut | What the reader does |
|---|---|
| Game storage version below 116 | Returns success without reading any CF data |
| Game storage version 116 to 140 | Does not enter the framework branch; no framed mod blocks are read |
| Game storage version 141 or higher, CF data version below 2 | Reads the framework version and returns success before the mod count; no mod blocks |

Sources: `CF_ROOT/ModStorage/CF_ModStorageObject.c:90-93` and `:121-124`; the constants 116, 141 and 2 at `CF_ROOT/ModStorage/CF_ModStorage.c:11`, `:12`, `:14`.

A broken frame is not a compatibility cut. A failed framework read logs a format error and returns `false` (`CF_ModStorageObject.c:109-113`, `:127-131`), and reading fewer blocks than the declared count returns `false` (`:149-150`). Apply none of the mod's staged values after either failure.

## Uninstall and reinstall

CF keeps each mod's block whether or not that mod is loaded, and writes the block of an unloaded mod back unchanged (`CF_ModStorageObject.c:73-77`). So this cycle keeps mod B's block byte for byte:

1. Save with mods A, B and C loaded.
2. Load without B.
3. Save again, B still absent.
4. Add B back and load.

B cannot read its data while absent, but its block is still in the frame and is there again after B returns. This is the one property no other choice gives.

CF cannot keep values that a `modded class` appended to a vanilla stream outside its framing. Only data written through CF's own per-mod block has this guarantee.

## What CF leaves to the mod

* The block's field order, types and upgrade paths.
* Classifying old, current, future, truncated and rolled back data (`migration-matrix.md`).
* Reading into locals and applying nothing on a failed read (`save-load-contract.md`, "When a read fails").
* A backup before rewriting migrated data.
* Rate limited log lines for future or broken data.
* Anything an admin must read or repair outside the game, and any file replacement (`sidecar-files.md`); CF gives no rename, backup or atomic file write.

## Checklist

- The framework version, the mod count and every block are read completely.
- The mod's reader branches on `storageVersion` or its own version, not only on the game build.
- The game version cuts and the framework data cuts are handled as separate cases.
- A failed or short outer read returns `false` and applies no staged state.
- The block of a mod that is not loaded is identical after save, load and save.
- After the mod is added back, it sees the same version and the same bytes.
- Upgrade, rollback and damaged data are each declared on their own.
