# Lifetime and storage copies

Why placed objects vanish after a restart even when their save code is right: the central economy lifetime, what a class with no `types.xml` entry gets, what adding the entry late does, and what a copied storage folder needs before it loads. The economy files themselves are in `central-economy-files.md`.

The measurements below were made in game on DayZ 1.29 with a test mod's placed objects. They are engine behaviour and not checkable on `P:\`.

## Saved is not the same as kept

The central economy keeps a lifetime in seconds on every entity it persists. `SetLifetime` and `GetLifetime` set and read what remains; `SetLifetimeMax` and `GetLifetimeMax` set and read the maximum per instance, whose default comes from the economy database (`P:\scripts\3_game\entities\entityai.c:3377` to `:3386`). `GetEconomyProfile` returns the class's economy profile (`entityai.c:888`). A territory flag's refresh calls `RadiusLifetimeReset` (`P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:168` and `:207`), which resets lifetimes "to default value from DB within radius" (`P:\scripts\3_game\ce\centraleconomy.c:562` to `:570`).

So correct save code does not keep an object in the world. Every class a player places, or that otherwise persists, needs an entry with an explicit `lifetime` in the mod's own `types.xml`. Vanilla gives `Fence` and `Watchtower` 3888000 seconds, 45 days (`P:\DZ\worlds\chernarusplus\ce\db\types.xml:7774` for `Fence`, `:25352` for `Watchtower`). Check the file mechanically against the public classes in `config.cpp`. The `types.xml` work belongs to `dayz-server-admin`.

## A class with no entry lives 30 to 60 minutes

A probe logged the lifetime of classes with no entry in any `types.xml`:

| Seen | Value |
|---|---|
| The profile's lifetime and `GetLifetimeMax()` | both 1800 |
| A new entity's starting lifetime, six creations with and without an entry | 1.03 to 1.98 times the maximum, for example 1857.19 and 2883.18 |
| Lifetime with a player 10 m away | fell in real time, 49 s in 49 s; being near does not pause it |
| Across a restart | saved and restored what remained, 1808.19 before and 1783.69 after; downtime does not count |
| `GetLifetime()` in `EEInit` of a restored entity | 0, because the stored value is not loaded yet |
| Restored entities whose lifetime ran out | deleted during startup before any player connected: four `delete ... life=-1 lifeMax=1800` lines before the first `EOnClientPrepare` |

So an object of a class with no entry runs out 30 to 60 minutes of server time after it is created, and the next restart deletes it. While the server runs, the economy's cleanup is expected to delete it once no player is within `CleanupAvoidance` (100 m stock, `P:\DZ\worlds\chernarusplus\ce\db\globals.xml:4`); the probe did not measure that. A persistence test with objects younger than an hour proves nothing. Not shown: that 1800 is a fixed engine value, and that it is the same on a dedicated server.

## Adding the entry late

Measured the same way, with an entry of lifetime 3888000 added to a world that already held such objects:

- New entities started at 5.02e6 and 6.68e6.
- Existing ones took the new maximum but kept what remained of their short lifetime: 2059.67 and 2124.49 before the entry, 2008.97 and 2073.79 after the restart with it.
- Restored entities that had run out were deleted at startup anyway.
- Removing the entry from the XML after it had loaded changed nothing: new entities still started at 4.63e6 and 7.72e6, because the server restored the types from the storage's `types.bin`.

Tell admins of a server that adds the entry late to dismantle and place such objects again after the restart. A territory flag's refresh might also rescue them through `RadiusLifetimeReset`; that is read in the code above, not measured.

## An entry needs no tags to spawn as loot

An entry with `nominal` above 0 and no `category`, `usage` or `value` tags still spawns as loot. On a fresh storage with `log_ce_lootspawn` on, the economy placed 202 of a mod's objects (kits, items, generators) across the map in its first pass. Tags limit where an entry spawns; they are not needed for it to spawn. The RPT's `Adding <class> at [x,z]` lines also record what a script creates.

## A storage copy without the economy's own files loads nothing

A copy of `storage_1` that held only `animals.bin`, `building.*` and `dynamic_*`, without `types.*`, `events.*`, `vehicles.*` and `zombies.bin`, loaded nothing. The RPT reported every file `ver:0 stamp:0, valid:NO`, even those present, and ended with `[CE][Hive] :: Empty storage folder, reinitializing ...`. The `dynamic_000.bin` header matched a working world's, so the file was not damaged: the economy's own files anchor the stamp that validates the rest. The full world on the same machine logged `dynamic_000.bin ... valid:yes` and `Restoring file ... 812 items.`

1. Before counting what a storage copy holds, check that its `data` folder has `types.bin` and `events.bin` with their generations, besides the `dynamic_*` files.
2. A count at boot counts only when the RPT shows `Restoring file ... N items` with N above 0. Without that line, zero load lines mean nothing.
3. Never count entities by searching the `.bin` files for class names. That search returns 0 even in a world that holds them. Count them in game.
