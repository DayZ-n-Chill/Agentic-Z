# Spawning and placing test objects

How to create a test object so it lands where you meant, does not outlive the run, and is posed so its faces can be read: the spawn flags, the coordinate order, the placement flags, what an inventory create really makes, and how to kill, respawn and provoke the player.

Flag values cite `P:\scripts\3_game\ce\centraleconomy.c`. The behaviour around them was measured in game on DayZ 1.29 and 1.30 and is not checked on `P:\`.

## Spawn flags

Objects are created with `CreateObjectEx(string type, vector pos, int iFlags, int iRotation = RF_DEFAULT)` (`P:\scripts\3_game\global\game.c:703`).

| Value | Flags | Source | Use |
|---|---|---|---|
| 1060 | `ECE_PLACE_ON_SURFACE`, the sum of `ECE_CREATEPHYSICS` (1024), `ECE_UPDATEPATHGRAPH` (32) and `ECE_TRACE` (4) | `centraleconomy.c:38`; `:17`, `:13`, `:10` | Puts the object on the ground below the given point. A `y` of 0 lands on the terrain: `pos=[7500,0,7500]` gave `y=313.14` in four measurements. |
| 8388608 | `ECE_NOPERSISTENCY_WORLD`, "do not save this object in world" | `centraleconomy.c:31` | Add it to every test object. |
| 8389668 | `ECE_PLACE_ON_SURFACE` plus `ECE_NOPERSISTENCY_WORLD` | | The default for test objects and test cars. |
| 3108 | `ECE_PLACE_ON_SURFACE` plus `ECE_INITAI` (2048) | `centraleconomy.c:18` | A living infected. |
| 8391716 | 3108 plus `ECE_NOPERSISTENCY_WORLD` | | A living infected that is not saved. |

An object created without `ECE_NOPERSISTENCY_WORLD` is saved by the server and comes back in every later run. A test car whose run died before it was deleted came back in each new run, where nothing held its id any more; the next seat command then found that leftover car 2 m away instead of the new one. Rotating `storage_1` also clears piled-up test entities (`build-and-storage-traps.md`).

## Coordinates

- `vector` is in engine order `[x, y_up, z_north]`. Some logs print positions as `<x, z_north, y_up>`; passing such a triplet unchanged puts the object about 6 km up, where the engine deletes it with `NETWORK (E): Will delete object ... outside world coords` in the RPT. After a spawn that never shows, search the RPT for that line before you retry; it tells bad coordinates from a slow spawn.
- A spawn next to the player can land inside a building. Cast a few rays down to find clear ground first (`raycasts-and-collision.md`).
- A spawn that reports success does not prove the object stays there: physics can throw it away, and a vehicle spawned at a town ended 40 km below the map. Read the position again a few seconds later, against the requested one.
- Before a teleport to coordinates nobody checked, cast a ray from y+30 down to y-5 at both the player's point and the object's point; it must hit within 0.05 m of the terrain height. The ray finds roofs, tree crowns and water (it hits the water surface, above the seabed).
- Network bubble: a search for objects near a point is reliable only with a player near that point. Far from any player it can return nothing, with no error. Terrain height reads are reliable everywhere, since terrain is static.
- The streamed world follows the player, not a free camera (`screenshots-and-cameras.md`). Spawn next to the player.

## Placement flags and posing a test object

The fourth argument of `CreateObjectEx` is a placement flag, not a heading.

- `RF_DEFAULT` (512, "use default placement setuped on object in config", `centraleconomy.c:66`) turned an `Inventory_Base` test box about 10 degrees: a side face reading moved 0.22 m across 1.2 m of the face.
- 64 spawned the same box with its faces on the world axes, on flat concrete. Vanilla gives 64 two names, `RF_IGNORE` ("object will spawn as model was created", `centraleconomy.c:57`) and `RF_RANDOMROT` (`:63`). The result agrees with the first comment and does not settle how the engine reads the value.
- No flag sets a heading, and a spawned car takes the slope of the ground at its point. Choose the site, not the direction.
- Check the pose before you trust face coordinates. Two parallel rays at one height on a vertical face catch a turn but not a tilt, so also read bullet ray normals on two faces that are not parallel, such as a side and the top (`raycasts-and-collision.md`). Allow for the ground: statics read up to 0.31 degrees off the axis, items the same as the ground under them.

### An item can come out with its sides swapped

One source model held two 2 m boxes, A in `Component01` and B in `Component02`, along x. Spawned with 8389668 and rotation 64, as `HouseNoDestruct` the west box was A, as modelled; as `Inventory_Base` (`item_large`) the boxes had swapped sides, as a half turn about Y leaves them. Memory points are read in model space (`GetMemoryPointPos`, `P:\scripts\3_game\entities\object.c:452`), so they do not show the pose. Give a test object sides a ray can tell apart (one component per side, read from the hit's component, or a collider on one side only), put parts off centre in z as well to tell a half turn from a mirror, and probe along z too. Not measured: whether the swap is fixed or random, other flags, other base classes and the cause.

## Inventory creates are not units

`CreateInInventory` returns null whenever `FindFirstFreeLocationForNewEntity` finds no place (`P:\scripts\3_game\systems\inventory\inventory.c:876`), so a missing class and an item that does not fit look the same. Before you blame the inventory, check that the class exists in the mission's `types.xml` and try a vanilla control item such as `Apple`. A stackable item is created with its default quantity, which can be a full stack, so never turn the number of creates into units; read each item's real quantity.

The player's inventory is saved with the character, so the next run finds what the last one left, and creates fail because nothing fits. To start clean, stop the server, back up and delete `<mission>\storage_1\players.db`, and relaunch. Balance or state the mod saves in the server profile survives that.

## Killing, respawning and provoking the player

- Respawn works only from the death screen. Kill the player with outside damage: spawn a living infected (3108) next to them; a fall does not work with a panel open. The screen goes normal, then desaturated with blood while unconscious, then black when dead; the vanilla respawn then counts down ("Spawning in 8 s") and the player appears elsewhere. A respawn request on a living player does nothing, so compare positions.
- An infected attacks only once it notices the player. One spawned behind a still player walked away; one spawned 2.4 m in front attacked after a short jog of 1.2 s, again and again.
- God mode does not hide the player from AI in the diag build: `m_CanBeTargetedDebug` starts true under `#ifdef DIAG_DEVELOPER` (`P:\scripts\4_world\entities\manbase\playerbase.c:408`).
- Infected spawned without `ECE_INITAI` did not stay healthy: with 8389668, three idled in place, but about 12 minutes later two read health 0 and lay on the ground and the third read 0.75. One observation with no control. Capture static infected early and read their health again before a late capture.
- The player spawn line in the RPT is `Create entity type 'SurvivorM_...'` or `'SurvivorF_...'`. Wait for `Create entity type 'Survivor`, which matches both; a pattern with `SurvivorM_` waits forever on a female character.

## Comparing worn items

A second garment cannot go into a taken slot, and a teleport upward leaves the player hanging with no fall (`raycasts-and-collision.md`, "Standing on top"). To compare two garments, put the second on a survivor spawned as an object (`SurvivorM_<name>`): its attachment slots accept clothing, it stands facing north, and it cannot hold an item in `Hands`, so read its sides from its facing.
