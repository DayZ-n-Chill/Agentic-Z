# Load failures, restore order and mod registries

What happens around a load that the save code alone does not show: an entity whose `OnStoreLoad` returns false, the order in which a mod's own structures and the game's stored entities come back, capturing live cargo over several ticks, and a registry a mod keeps of its world entities. Open it when designing a restore pass, a version rejection or a registry kept in a file of the mod's own.

The measurements were made in game with test mods and the code reviews on third-party mod code, so neither is checkable on `P:\`; the vanilla lines cited are.

## `OnStoreLoad` returning false keeps the entity

Measured in game on DayZ 1.29. When an entity's `OnStoreLoad` (`P:\scripts\3_game\entities\entityai.c:2978`) returns false, the engine does not delete it. The RPT prints `!!! Scripted variables corrupted upon "<class>"` with `Reason: [EntityAI::OnStoreLoad] :: [WARNING]`, and the entity stays in the world with its script variables at their defaults, apart from what the load assigned before it returned.

The test used three batteries whose load read their wires and then rejected the battery's own record as an old version. All three stayed, with their wires (the generator kept its four outputs and each lamp its input), and their stored energy started at 0; about 90 s later they read 116, 116 and 182, from charging. A save and load order mismatch prints the same RPT line (`_shared/enscript/depth/pitfalls-advanced.md`), so the line alone does not tell a deliberate rejection from a desync.

- A version rejection in `OnStoreLoad` loses the script state, not the entity. To remove the entity, delete it yourself. An audit that says "the entity is discarded" has to measure it.
- Not measured: the next save. The entity is still in the world, so expect it to be saved again with the state it holds, replacing the rejected record. Until that is measured, do not rely on `return false` to keep the original bytes, which the read only rejection in `migration-matrix.md` asks for.

## Build what stored entities rest on inside `OnMissionStart`

Measured in game on DayZ 1.29. Stored entities are created after `MissionServer.OnMissionStart` returns (`_shared/enscript/depth/api-patterns.md`).

A mod rebuilt its placed structures from its own file with a `CallLater` of 2 s from `OnMissionStart`, and each structure created its floor and platform parts 0.5 s after its own `EEInit`. A helicopter (a `CarScript` kept by the game's storage) parked on a lowered platform came back after an orderly restart before those parts existed. Its `EEInit` print, at the parked height (y 14.13), came before the parts line in the server script log, and it fell 6.9 m to the terrain and lay rolled -54.3°. With the restore called directly in `OnMissionStart` and the parts created in that call, the parts line came first after two orderly restarts, and the helicopter stayed where it was parked (0.010 and 0.014 mm from its parked height, level within 0.07°) and later rose with the platform. The 2 s pass stayed to bind what already exists and created nothing twice. The builds before and after also differed in other ways; what ties the fall to the timing is the order of the two log lines.

So a structure the mod rebuilds from its own file, when stored entities can rest on it (a floor, a platform, a hangar), is created synchronously in `OnMissionStart`, as long as nothing it needs comes from the game's storage, which loads later. A later pass only binds, and running it twice changes nothing. Not measured: a crash restart, stored entities other than this one vehicle, and freezing the vehicles until the structure exists.

## Capturing live cargo across ticks

Measured in game on DayZ 1.30. `GetItemCount()` is read once when the capture begins. A batched walk over `cargo.GetItem(i)` then loses items when the player removes one during the capture: the cargo closes the gap, the shifted item lands on an index already visited and never enters the snapshot, and a later `ClearPhantomItems` destroys it unsaved. The guard `i < GetItemCount()` hides the out of range access.

Walking live cargo across ticks needs either an abort that writes nothing when the count changes, or a capture by entity identity at one instant. A range guard that skips the hole loses data silently. Do not invent a smarter walk on a data path without an explicit decision; the minimum correct behaviour is to abort without writing to the world or the disk.

## A registry entry leaves by its id, never by distance

A mod that keeps its own registry of the world entities it placed (a JSON file with class, position and id per entry; `sidecar-files.md`) binds each entry to one entity. A review of one such mod's code, each finding checked against the code, found three ways to break that binding. The first was also checked in game on DayZ 1.29.

1. **Removing by distance deletes another entity's entry.** `EEDelete` called an unregister that looked the entity up by id and, failing that, took the nearest entry of the same class within 0.75 m and saved the file without it. Two paths create and then delete an entity that never got an id: a placement that creates the entity, checks the site and deletes it on refusal, and an entity an admin spawns from the console and deletes. Either way a registered neighbour of the same class inside the radius loses its entry and does not come back after the next restart.

   Remove an entry only on a matching id; an entity without one never touches the file, and an id two entries share identifies neither. When ids were assigned in memory but could not be saved, a deleted entity then comes back after a restart, which is better than deleting another entity's entry. In game, with that rule, a console entity created 0.3 m from a registered one horizontally (0.37 m apart, inside the radius) and then deleted left the registry byte for byte the same, and the registered entity came back after the restart. The original failure was read in the code, not reproduced.

2. **On restore only the id binds an entity to its entry.** `GetObjectsAtPosition3D` returns the objects in a sphere and promises no order (`P:\scripts\3_game\global\game.c:924` to `:930`). Taking the first unclaimed candidate of the class inside the radius can swap ids and states between two nearby entities of that class, and a second restore pass, 2 s after start to bind what the mission created, runs that code on every boot. The reviewed mod's fix takes the entity already bound to the entry's id, else the nearest one not yet claimed in the pass; it keeps the id in a script member, so no entity carries it across a restart.

   A position match proves nothing: an entity near the entry's position, or of its class, is not shown to be the entry's, and finding none there does not show the entry's entity is gone.

   No automatic restore rule has held up under review. Each rule tried was traced, through the reviewed mod's fixed code or the rule's own text, to an entry that takes the wrong entity or gets a second one:

   - **The wrong entity.** An entry left behind by an unregister whose save failed takes the nearest unclaimed entity of its class although that entity carries another entry's id, or an admin's console entity that carries no id. Of two loaded entities that carry one id, the second to load takes the binding.
   - **A second entity.** A rule that refuses every entity with another id creates again for an entry whose id was regenerated after a failed save (`I1` given to the entity in memory, the save fails, a later pass saves `I2`). A rule that reads an empty radius as absence creates while the entity sits outside the radius, under another class name or not yet loaded. A list of the restore's own creations, cleared when the mission ends, misses the previous mission's entities if they still live. A list of every live entity kept by the entities' own `EEInit` and `EEDelete` misses a creation in progress, which joins from its `EEInit` before it carries the id, so a pass started from that `EEInit` creates a second one. Reserving the entry during that creation does not stop a pass that reloads the registry and gets a copy of the entry without the reservation; where later passes do see the reservation, a creation that fails keeps the entry from ever getting its entity.

   These are traces, not observations: none was reproduced in game, and several need conditions not shown to occur in the reviewed mod (a pass started from an entity's `EEInit`, when it starts its passes only from `MissionServer`; two loaded entities with one id; entities that live through a mission change). Whether the engine persists that mod's placed entities is not established. No restore rule is given here; `where-to-save.md`, "Hard stops", says what a restore must not do.

3. **A queued restore pass can reopen saving at shutdown.** When the restore clears the shutdown flag (for a mission restart in the same process), a restore `CallLater` still waiting in `CALL_CATEGORY_SYSTEM`, which is processed "without any restrictions" (`game.c:1540`), clears it again after `OnMissionFinish`, and the shutdown's `EEDelete` calls then remove entries. Remove the pending passes with `ScriptCallQueue.Remove` (`P:\scripts\2_gamelib\tools.c:65`) before setting the flag. Read in the code; the shutdown order in game is not confirmed.

Every entry point that creates or deletes such an entity follows the first rule; the list of entry points to walk is in `deep-audit-entry-points.md`.
