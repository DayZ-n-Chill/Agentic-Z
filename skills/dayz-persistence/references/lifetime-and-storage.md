# Lifetime, `types.xml` and storage copies

Why placed objects vanish after a restart even when their save code is right: the central economy lifetime of a class with no `types.xml` entry, what adding the entry late does, and what a copied storage folder needs before it loads. Open this when objects disappear after a restart, before a persistence test, or when counting what a storage copy holds.

The measurements were made in game with a test mod and cannot be checked on `P:\`; the vanilla script lines cited are from `P:\` (game storage version 144).

## A storage copy without the economy's anchor files loads nothing

Measured in game on DayZDiag 1.29.163709; engine behaviour, not checkable on `P:\`.

A copy of `storage_1` carrying only `animals.bin`, `building.*` and `dynamic_*` (without `types.*`, `events.*`, `vehicles.*`, `zombies.bin`) loads NOTHING: the RPT reports every file `ver:0 stamp:0, valid:NO`, even files that are present, and ends with `[CE][Hive] :: Empty storage folder, reinitializing ...`; zero items restored, zero mod load lines. The `dynamic_000.bin` header bytes match a working world's, so it is not corruption: the CE files anchor the stamp that validates the rest. Control on the same machine, full world: `dynamic_000.bin ... valid:yes` and `Restoring file ... 812 items.`

Rules: (1) before censusing a storage copy, check that `data/` brings `types.bin` and `events.bin` with their generations besides the `dynamic_*`; (2) a boot census counts only if the RPT shows `Restoring file ... N items` with N > 0, without that signal a zero count of load lines is vacuous, not "zero"; (3) do not count entities by grepping class names in the `.bin` files, the byte-grep returns 0 even in a world that contains them.

## A class with no `types.xml` entry lives 30 to 60 minutes of server time

Measured in game on DayZDiag 1.29.163709 with a test mod; the script API lines are from `P:\`.

The central economy keeps a lifetime, in seconds, on every entity it persists: `GetLifetime`/`SetLifetime` read and set what remains, `GetLifetimeMax`/`SetLifetimeMax` the maximum (`P:\scripts\3_game\entities\entityai.c:3377-3386`), and `GetEconomyProfile` returns the class's economy profile (`entityai.c:888`). A probe in the test mod logged them for classes that have no entry in any `types.xml`:

- the profile's lifetime and `GetLifetimeMax()` are both 1800;
- a new entity starts above that: 1857.19 and 2883.18 (six creations, with and without an entry, started at 1.03 to 1.98 times `lifeMax`);
- the lifetime falls in real time with a player 10 m away (49 s in 49 s): being near does not pause it;
- a restart saves and restores what remains (1808.19 before, 1783.69 after), and server downtime does not count;
- in `EEInit` of a restored entity `GetLifetime()` is 0: the stored value is not loaded yet;
- restored entities whose lifetime had run out are deleted during startup, before any player connects: four `delete ... life=-1 lifeMax=1800` lines come before the first `EOnClientPrepare`.

So an object placed from a class without an entry runs out 30 to 60 minutes of server time after it is created, and the next restart deletes it. While the server runs, the economy's cleanup is expected to delete it once no player is within `CleanupAvoidance` (100 m in the mission's `db/globals.xml`); this probe did not measure that. A persistence test with objects younger than that proves nothing. Not shown: that 1800 is a fixed engine value, and a dedicated server.

Adding the entry (lifetime 3888000) to a world that already holds such objects:

- new entities start at 5.02e6 and 6.68e6;
- existing ones take the new `lifeMax` but keep what remained of their short lifetime (created at 2059.67 and 2124.49 without the entry, 2008.97 and 2073.79 after the restart with it);
- restored entities that had run out are deleted at startup anyway;
- removing the entry from the XML after it has loaded changes nothing: new entities still start at 4.63e6 and 7.72e6, and that run restores the types from the storage's `types.bin`.

Rule: ship every class that a player places, or that otherwise persists in the world, in the mod's own `types.xml` with an explicit lifetime (3888000 for placed structures, as vanilla gives `Fence` and `Watchtower` in Chernarus' `db/types.xml`), and check the file mechanically against the public classes of `config.cpp`. A server that installs the file late keeps its existing objects on the short lifetime: tell admins to dismantle them and place them again after the restart. A territory flag might also rescue them: its refresh calls `GetCEApi().RadiusLifetimeReset` (`P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:168` and `:207`), documented as a reset "to default value from DB within radius" (`P:\scripts\3_game\ce\centraleconomy.c:562-569`), which with the entry is 3888000. Read in the code, not measured.

An entry with `nominal` above 0 and no `category`, `usage` or `value` tags still spawns as loot. On a fresh storage (`Empty storage folder, reinitializing`) with `log_ce_lootspawn` on, the economy placed 202 of the mod's objects (kits, items and generators) across the map in its first pass. The RPT's `Adding <class> at [x,z]` lines also record what a script creates: nine more lines were the test scene. Tags restrict where an entry spawns; they are not needed for it to spawn.
