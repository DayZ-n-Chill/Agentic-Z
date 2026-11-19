# Community Framework ModStorage

How Community Framework (CF) keeps one framed block per mod inside an entity's save, which version it hands each mod, and what it leaves to the mod. Open it when a mod saves data on an entity it does not own, or when the data must survive the mod being removed and added back.

CF is a third-party mod, so none of this is under `P:\scripts\`. The CF lines below are paths inside CF's own scripts PBO, `@CF\Addons\scripts.pbo`, checked against the framework's scripts, not vanilla. That PBO is not unpacked on `P:\`, so check them again in your copy of CF after a CF update. The vanilla end of the chain is `EntityAI.OnStoreSave` and `OnStoreLoad` (`P:\scripts\3_game\entities\entityai.c:2910` and `:2978`). The rest of the CF API (modules, RPCs, events) is in `_shared/enscript/integrations/community_framework.md`.

## The hooks

CF's modded `ItemBase` wraps the vanilla stream: its `OnStoreSave` and `OnStoreLoad` call `super` and then pass the stream to a `CF_ModStorageObject` (`4_World\CommunityFramework\Entities\ItemBase.c:3` to `:20`). A mod overrides the two empty hooks `CF_OnStoreSave(CF_ModStorageMap storage)` and `CF_OnStoreLoad(CF_ModStorageMap storage)` (`CommunityFramework\Entities\ItemBase.c:42` and `:84`), not `OnStoreSave`. The other entity bases in the same folder (`BuildingBase.c`, `CarScript.c`, `DayZPlayerImplement.c`, `ZombieBase.c` and more) carry the same pair.

`CF_ModStorageMap` is keyed by mod name: `Get(string)`, `Get(typename)`, `Contains(string)` and `Find(string, out CF_ModStorage)` (`3_Game\CommunityFramework\ModStorage\CF_ModStorageMap.c:5` to `:23`). `CF_ModStorage` reads and writes `bool`, `int`, `float`, `vector` and `string` (`3_Game\CommunityFramework\ModStorage\CF_ModStorage.c:61` to `:179`).

A mod's pair, with a field added in its version 2:

```c
modded class ItemBase
{
    override void CF_OnStoreSave(CF_ModStorageMap storage)
    {
        super.CF_OnStoreSave(storage);

        CF_ModStorage ctx = storage.Get("MyMod");
        ctx.Write(m_MyModCustomValue);
        ctx.Write(m_MyModTag);
        ctx.Write(m_MyModNewField);
    }

    override bool CF_OnStoreLoad(CF_ModStorageMap storage)
    {
        if (!super.CF_OnStoreLoad(storage))
            return false;

        // A save made before the mod was added has no block for it.
        if (!storage.Contains("MyMod"))
            return true;

        // Read into locals; apply nothing unless every read succeeds.
        CF_ModStorage ctx = storage.Get("MyMod");
        int customValue;
        string tag;
        int newField;
        if (!ctx.Read(customValue)) return false;
        if (!ctx.Read(tag))         return false;

        bool hasNewField = ctx.GetVersion() >= 2;
        if (hasNewField)
        {
            if (!ctx.Read(newField)) return false;
        }

        m_MyModCustomValue = customValue;
        m_MyModTag = tag;
        if (hasNewField)
            m_MyModNewField = newField;

        return true;
    }
}
```

A `false` from `CF_OnStoreLoad` does not fail the entity's load: CF logs a warning and returns `true` (`4_World\CommunityFramework\ModStorage\CF_ModStorageObject.c:161` to `:170`). So the mod must leave its own fields untouched on a failed read (`save-load-contract.md`, "When a read fails").

## The frame

`CF_ModStorageObject.OnStoreSave` writes, in order (`CF_ModStorageObject.c:46`, `:62`, `:64` to `:71`):

1. `CF_ModStorage.VERSION`, the framework's own format version, 5 (`CF_ModStorage.c:9`).
2. The number of mod blocks that hold data.
3. One framed block per mod.

The framework version is not the version of any mod's data. Each mod owns its block and its upgrade paths.

## The mod's version

The value comes from the mod's `CfgMods` `storageVersion`, through `ModStructure.GetStorageVersion()` (`3_Game\CommunityFramework\Mods\ModStructure.c:61` to `:63` and `:307`), into `CF_ModStorage.m_Version` (assigned at `CF_ModStorage.c:274`), and is read with `CF_ModStorage.GetVersion()` (`:41` to `:44`).

Branch the mod's reader on that value or on a version the mod writes into its own block, never on the game build alone: two mod releases can write different blocks on the same game build.

## Old saves CF reads as empty

| Case | What the reader does |
|---|---|
| Game storage version below 116 | returns success without reading any CF data |
| Game storage version 141 or higher, and CF's entity list does not hold this entity | returns success without reading, taking it that CF itself was just added; below 141 there is no entity list and the reader goes on |
| CF data version below 2 | reads the framework version and returns success before the mod count; no mod blocks |

Sources: `CF_ModStorageObject.c:90` to `:106` and `:121` to `:124`; the constants 116, 141 and 2 at `CF_ModStorage.c:11`, `:12` and `:14`.

A broken frame is a different case. A failed framework read logs a format error and returns `false` (`CF_ModStorageObject.c:109` to `:113` and `:127` to `:131`); a framework version above 5 or a mod count outside 0 to 256 returns `false` (`:136` to `:140`); and reading fewer blocks than the declared count returns `false` (`:147` to `:159`). Apply none of the mod's staged values after any of these.

## Removing and adding a mod back

CF keeps each mod's block whether or not that mod is loaded, and writes the block of an unloaded mod back unchanged (`CF_ModStorageObject.c:73` to `:77`). So this cycle keeps mod B's block byte for byte:

1. Save with mods A, B and C loaded.
2. Load without B.
3. Save again, B still absent.
4. Add B back and load.

B cannot read its data while it is absent, but its block stays in the frame and is there again when B returns. No other place to save gives this.

CF cannot keep values that a `modded class` appended to a vanilla stream outside its framing. Only data written through CF's own per mod block has this guarantee.

## What CF leaves to the mod

- The block's field order, types and upgrade paths.
- Sorting old, current, future, truncated and rolled back data (`migration-matrix.md`).
- Reading into locals and applying nothing on a failed read (`save-load-contract.md`, "When a read fails").
- A backup before rewriting migrated data.
- Rate limited log lines for future or broken data.
- Anything an admin must read or repair outside the game, and any file replacement (`sidecar-files.md`); CF gives no rename, backup or atomic file write.

## Checklist

- The framework version, the mod count and every block are read completely.
- The mod's reader branches on `storageVersion` or its own version, not only on the game build.
- The game version cases and the framework data cases are handled separately.
- A failed or short outer read returns `false` and applies no staged state.
- The block of a mod that is not loaded is identical after save, load and save.
- After the mod is added back, it sees the same version and the same bytes.
- Upgrade, rollback and damaged data are each handled on their own.
