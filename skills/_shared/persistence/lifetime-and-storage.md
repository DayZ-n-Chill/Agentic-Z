# Lifetime and storage copies

Why placed objects vanish after a restart even when their save code is right: the central economy lifetime, what a class with no `types.xml` entry gets, what adding the entry late does, and what a copied storage folder needs before it loads. Open this when objects disappear after a restart, before a persistence test, or when counting what a storage copy holds. The economy files themselves are described in `central-economy-files.md`.

## Saved is not the same as kept

The central economy keeps a lifetime in seconds on every entity it persists. `SetLifetime` and `GetLifetime` set and read what remains, `SetLifetimeMax` and `GetLifetimeMax` the maximum per instance, whose default comes from the economy database (`P:\scripts\3_game\entities\entityai.c:3377` to `:3386`). `GetEconomyProfile` returns the class's economy profile (`entityai.c:888`). A territory flag's refresh calls `RadiusLifetimeReset` (`P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:168` and `:207`), documented as a reset "to default value from DB within radius" (`P:\scripts\3_game\ce\centraleconomy.c:562` to `:570`).

So correct save code does not keep an object in the world. Every class a player places, or that otherwise persists, needs an entry with an explicit `lifetime` in the mod's own `types.xml`. Vanilla gives `Fence` and `Watchtower` 3888000 seconds, 45 days (`P:\DZ\worlds\chernarusplus\ce\db\types.xml:7774` for `Fence`). Check the file mechanically against the public classes of `config.cpp`. The `types.xml` work belongs to dayz-server-admin.

## A class with no entry lives 30 to 60 minutes of server time

Measured in game on DayZDiag 1.29.163709 with a test mod's placed objects; engine behaviour, not checkable on `P:\`. A probe logged the lifetime of classes that have no entry in any `types.xml`:

* The profile's lifetime and `GetLifetimeMax()` were both 1800.
* A new entity started above that: six creations, with and without an entry, started at 1.03 to 1.98 times the maximum (for example 1857.19 and 2883.18).
* The lifetime fell in real time with a player 10 m away (49 s in 49 s); being near does not pause it.
* A restart saved and restored what remained (1808.19 before, 1783.69 after); server downtime did not count.
* In `EEInit` of a restored entity `GetLifetime()` was 0: the stored value is not loaded yet at that point.
* Restored entities whose lifetime had run out were deleted during startup, before any player connected: four `delete ... life=-1 lifeMax=1800` lines came before the first `EOnClientPrepare`.

So an object placed from a class with no entry runs out 30 to 60 minutes of server time after it is created, and the next restart deletes it. While the server runs, the economy's cleanup is expected to delete it once no player is within `CleanupAvoidance` (100 m stock, `P:\DZ\worlds\chernarusplus\ce\db\globals.xml:4`); the probe did not measure that. A persistence test with objects younger than an hour proves nothing. Not shown: that 1800 is a fixed engine value, and the same on a dedicated server.

## Adding the entry late

Measured in the same way, with the entry added (lifetime 3888000) to a world that already held such objects:

* New entities started at 5.02e6 and 6.68e6.
* Existing ones took the new maximum but kept what remained of their short lifetime (2059.67 and 2124.49 before the entry, 2008.97 and 2073.79 after the restart with it).
* Restored entities that had run out were deleted at startup anyway.
* Removing the entry from the XML after it had loaded changed nothing: new entities still started at 4.63e6 and 7.72e6, because that run restored the types from the storage's `types.bin`.

Tell admins of a server that installs the entry late to dismantle and place such objects again after the restart. A territory flag's refresh might also rescue them through `RadiusLifetimeReset` (read in the code above, not measured).

## An entry needs no tags to spawn as loot

Measured in game on DayZDiag 1.29.163709: an entry with `nominal` above 0 and no `category`, `usage` or `value` tags still spawns as loot. On a fresh storage with `log_ce_lootspawn` on, the economy placed 202 of a mod's objects (kits, items, generators) across the map in its first pass. Tags restrict where an entry spawns; they are not needed for it to spawn. The RPT's `Adding <class> at [x,z]` lines also record what a script creates.

## A storage copy without the economy's own files loads nothing

Measured in game on DayZDiag 1.29.163709; engine behaviour, not checkable on `P:\`.

A copy of `storage_1` that carried only `animals.bin`, `building.*` and `dynamic_*`, without `types.*`, `events.*`, `vehicles.*` and `zombies.bin`, loaded nothing. The RPT reported every file `ver:0 stamp:0, valid:NO`, even the files that were there, and ended with `[CE][Hive] :: Empty storage folder, reinitializing ...`. The `dynamic_000.bin` header matched a working world's, so it was not damage: the economy's own files anchor the stamp that validates the rest. On the full world the same machine logged `dynamic_000.bin ... valid:yes` and `Restoring file ... 812 items.`

Rules:

1. Before counting what a storage copy holds, check that its `data` folder has `types.bin` and `events.bin` with their generations, besides the `dynamic_*` files.
2. A count at boot counts only if the RPT shows `Restoring file ... N items` with N above 0. Without that line a zero count of load lines means nothing.
3. Do not count entities by searching class names in the `.bin` files. That search returns 0 even in a world that holds them. Count them in game.

