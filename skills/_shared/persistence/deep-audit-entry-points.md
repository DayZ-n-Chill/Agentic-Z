# Entry point check

How to find the bug where the main path keeps a rule about saved data but another way in (a synchronous shortcut, an admin command, an early mission hook) skips it. This is the third mechanical check of `deep-audit.md`; run it for every rule the mod keeps about its saved data.

A reading review follows the main path, which is usually spread across ticks, and treats the shortcut as obviously the same. It rarely is.

The examples come from two storage mods, read in their code or measured in game, so they cannot be checked on `P:\`. The function names and `file:line` values in the tables are those mods' and only show the shape of each table. The vanilla hooks are cited where they are listed. The search lines are recipes for the agent's search tool.

## Examples

### The synchronous path leaves a marker

`Virtualize_Async` wrote a `.virtualizing` marker, did the work across ticks, then removed the marker. `VirtualizeSynchronous`, used during shutdown, wrote the marker but never removed it, because the shutdown path skipped the cleanup that runs on completion. The next boot saw the marker, decided the container had crashed mid store, and ran recovery on a container that was fully stored. Recovery merged duplicates.

### A kill switch held only in memory

`OnMissionStart` set the flag `m_ExternalVSDetected` in memory, and `OnMissionLoaded` read it to gate work. A second boot path, a server reload after an admin command, skipped `OnMissionStart` and went straight to `OnMissionLoaded`, so the flag was still false and the gate never fired. The fix saved the detection result on disk, where every entry point can read it.

### The gate runs after super

`EEItemAttached` called `super.EEItemAttached(item, slot)` first and then checked `IsVirtualized()`. Vanilla had already changed the cargo, so the state was left inconsistent.

### Removing a registry entry by distance

The second mod keeps the objects it placed in its own registry, `placed.json`, with class, position and id per entry. The main removal went by id: `EEDelete` called `UnregisterEntity`, which found the rock by its id. A rock with no id fell back to the nearest entry of the same class within 0.75 m, which was then saved out of the file. Two entry points delete a rock that never got an id: placement, which creates the rock, checks the site and deletes it when refused, and an admin who spawns one from the console and deletes it. Both removed the entry of a registered rock nearby, and that rock did not come back after the next restart.

The fix: removal needs a matching id, and an entity without one never touches the file. Measured in game: a console rock spawned 0.3 m (horizontally) from a registered one and then deleted left the file unchanged, and the registered rock came back after the restart.

The same audit found the shutdown side of this rule: a restore pass still queued in `CALL_CATEGORY_SYSTEM` after `OnMissionFinish` cleared the shutdown flag again, so the deletions during shutdown removed entries. `OnMissionFinish` now removes the pass before it sets the flag; the shutdown order in game is not confirmed. Both rules, and the restore that binds by id before position, are in `where-to-save.md` and in `load-and-restore.md`, section "A registry entry leaves by its id, never by proximity".

## List the entry points for each rule

For each rule the mod keeps, list every entry point that should keep it. Common rules and their entry points:

| Rule | Entry points |
|---|---|
| A container ends a store with no marker on disk | `Virtualize_Async` (main path, across ticks); `VirtualizeSynchronous` (shutdown); `Virtualize_FromAdminCommand` (`migrate-all`); `Virtualize_FromMigrationStub` (old saves, runs once) |
| Detecting another storage mod gates work on every boot | `OnMissionStart`; `OnMissionLoaded`; a server reload after an admin command; a world load after a crash recovery |
| A registry entry leaves only by its own id | `EEDelete` of a registered entity (pickup, dismantle, destruction); placement refused after the entity was created; an admin console spawn, then delete; `EEDelete` of every entity during shutdown; a restore pass still queued with `CallLater` when `OnMissionFinish` runs |

The vanilla `Mission` class declares `OnInit`, `OnMissionStart` (`P:\scripts\3_game\gameplay.c:701`), `OnMissionFinish` (`gameplay.c:702`) and `OnUpdate` (`gameplay.c:703`). A search of `P:\scripts` finds no `OnMissionLoaded`: that hook comes from a framework or from the mod (Community Framework modules have one; not checked on `P:\`). List the mission hooks the mod really overrides, vanilla and framework, as separate entry points.

For the rule that a gate runs before vanilla `super`, the entry points are the `EE` hooks and the store pair:

| Hook | Source |
|---|---|
| `EEInit` | `P:\scripts\3_game\entities\entityai.c:905` |
| `EEDelete` | `entityai.c:946` |
| `EEItemLocationChanged` | `entityai.c:976` |
| `EEKilled` | `entityai.c:1104` |
| `EEItemAttached`, `EEItemDetached` | `entityai.c:1159`, `:1199` |
| `EECargoIn`, `EECargoOut` | `entityai.c:1234`, `:1248` |
| `OnStoreSave`, `OnStoreLoad` | `entityai.c:2910`, `:2978` |

## Walk every entry point

Search for each entry point, open each match and check that the rule holds. Build the table:

| Rule | Entry point | File:Line | Kept? | Notes |
|---|---|---|---|---|
| Store ends without a marker | `Virtualize_Async` | persistence.c:340 | yes | removes `.virtualizing` on success |
| Store ends without a marker | `VirtualizeSynchronous` | persistence.c:480 | no | skips the cleanup branch |
| Store ends without a marker | `Virtualize_FromAdminCommand` | admin.c:120 | yes | calls the async path |
| Gate before super | `EEItemAttached` | events.c:88 | no | gate after super |
| Gate before super | `EECargoIn` | events.c:102 | yes | |

## Patterns to search

Synchronous shortcuts of a queued operation:

```text
Grep "Synchronous|_Sync\b|Force\w+|_Now\b|ImmediateMode" --type c --output_mode content -n true
```

For each hit, find the matching queued function and compare the two by hand. They should differ only in scheduling, not in the rules they keep.

Admin command handlers:

```text
Grep "OnAdminCommand|HandleAdmin|RegisterCommand|admin_|Cmd_" --type c --output_mode content -n true
```

For each handler, ask whether it bypasses the queue. If it does, it must take the same gates and clean up the same markers as the queue.

Mission entry points:

```text
Grep "OnMissionStart|OnMissionLoaded|OnMissionFinish|OnUpdate" --type c --output_mode content -n true
```

For state set in `OnMissionStart` and read in `OnMissionLoaded`, look for a path that reaches `OnMissionLoaded` without `OnMissionStart`: a server reload, a world reload, a mission script reload. If one exists, the state must be on disk, not in memory.

Order inside `EE` hooks:

```text
Grep "override\s+void\s+EE" --type c --output_mode content -n true
```

For each `EE` override that gates, read the body. The gate must run before `super` in every such hook. A hook that calls `super` first and gates afterwards is a finding, even when every hook does it the same way.

Distance used as identity:

```text
Grep "Closest|Nearest|GetObjectsAtPosition" --type c --output_mode content -n true
```

For each hit, ask whether it decides which registry entry an entity owns. If it does:

- a matching id must win;
- an entity without an id must not remove an entry;
- on restore, a candidate in the radius that does not carry the entry's id is not a match, and the first candidate is not always the nearest: `GetObjectsAtPosition3D` promises no order (`P:\scripts\3_game\global\game.c:930`; its comment says only that it returns all objects in the sphere);
- an empty radius does not prove the entry's entity is gone, so a restore that creates one there can make a second copy.

How a restore should bind and create is still open: no rule for it has held up in review (`where-to-save.md`, and the registry section of `load-and-restore.md`).

## Output

A findings table with three columns: the rule, the entry point that breaks it, and a sketch of the fix. Group by rule, so the user sees "this rule holds in 3 of 4 entry points". One broken entry point is enough for a finding. Rate it by what it does to player data, as with any finding: data loss possible, or recovery needed. The synchronous marker above needs recovery: it sends a complete container into recovery.

## Rules of thumb

- Fewer than four entry points for a rule usually means one was missed; look harder.
- "Synchronous", "Sync", "Force", "Immediate" or "Now" in a function name marks a shortcut. Suspect it.
- Admin commands almost always skip something. Audit each one on its own.
- Server reload and mission reload paths are easy to forget; when unsure which entry points exist, ask the user.

## Time

Allow 3 to 5 minutes per rule. A storage mod with about six rules of this shape takes about 30 minutes, which is cheap next to a data loss bug that ships.
