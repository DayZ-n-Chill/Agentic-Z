# What a dayz-mcp reply proves

Which dayz-mcp verb replies mislead (`world_spawn`, `wait_for`, `logs_since`, `inventory_give`, `telemetry_read`, `object_delete`, `player_respawn`, `key_press`, `entities_query`, `player_teleport`, `object_anim`), and the check to read instead.

The verbs belong to the third-party dayz-mcp tool. Their behaviour was measured in game with it and is not checked on `P:\`; `MCPBridge.c` lines are dayz-mcp's own source and `<dayz-mcp>` is your checkout. Vanilla facts (spawn flags, inventory calls) cite the vanilla file.

## Read the effect, never the reply

`ok` does not mean success, and the replies use at least four different shapes. The same verb with the same reply shape can do opposite things:

| Call | Reply | Effect |
|---|---|---|
| `object_delete(999999999)` | `ok:1, deleted:0` | Deleted nothing |
| `object_delete(<real id>)` | `ok:1, deleted:1` | Deleted it |

| What you want to know | Do not look at | Look at |
|---|---|---|
| Did it place the object where asked? | `ok` | `surface_query(x,z).y` against the `pos_real` of `world_spawn` |
| Did it delete anything? | `ok` | `deleted` |
| Did the player respawn? | `ok`, `requested` | `query_player_state.pos` before and after |
| Was the wait satisfied? | `ok` | `satisfied` |

## Six traps that cost a run each

Five of these give a verdict that blames the mod when the mod has no fault. In one test series on a mod device they produced six failed runs with no real mod failure. Check them before you write the first probe.

1. `dayz_test_run` does not load `@DayZ_MCP` by default and answers `succeeded` anyway. Both processes start, the game works and the bridge stays silent. The symptoms (`server_poll_stale`, `client_not_polling`, `ready.reason=no_run`) point at the bridge or the key, not at the mod list. Pass `extra_mods=["@DayZ_MCP"]` and confirm in the server log that the define `DayZ_MCP` shows in all four script modules, or look for `[MCP-POC]` lines.
2. `logs_since` does not accept its own `marker`. It returns the marker as a dict `{path: [offsets]}` and its parameter wants a string, so a Pydantic `ValidationError` follows, and reading the log in steps is impossible. Read the whole log at the end of the sequence and match the responses in order, checking each against a field of the event itself (a type, an id). If two probes share that field, mark `ambiguous_alignment` instead of guessing.
3. `wait_for(log_matches)` cannot wait for your own response. With the default `lookback_lines=200`, a line from the previous probe satisfies the pattern at once. With `lookback_lines=0` it has timed out with the line already in the client log, returning a line from another flow in `observed`. Use it as a convenience wait; the verdict comes from `logs_since`.
4. The player's inventory is not reset between runs. The second run finds what the first left, nothing fits, and handing out items fails silently (`create_failed`, or 0 units given). To chain runs: `dayz_test_stop`, back up and delete `<mission>\storage_1\players.db`, and relaunch (about 3 minutes). `clean=true` does not do this: it forces a build and passes `-clear` to AddonBuilder, which rebuilds the PBO and breaks the byte-for-byte identity an A/B test needs. Balance or state the mod saves in the server profile survives the deletion.
5. `inventory_give` returns `create_failed` both when the class does not exist and when the item does not fit, and the two cannot be told apart. Before you blame the inventory, check that the class exists: search the mission's `types.xml` and try a vanilla control item (`Apple` works). Do not assume the class names in a mod's config exist; they can point at a mod that is not loaded, and then the whole feature looks broken without being broken.
6. Read the client log before you believe a verdict. Many mod events are written by the client, not the server. In one series the automatic verdict said FAIL or INCONCLUSIVE six times in a row while the client log showed every operation working. The dangerous failure of a test is not "measures nothing" but "measures wrong and blames the mod", and that ends up in project notes. Before you record a FAIL, open the client log; `/dayz-logwatch --dir <client profile folder> --since 5` reads it with triage.

## `world_spawn`

- `ok=1` does not prove the object stays where you asked. `IsSpawnReady` (`MCPBridge.c:2729` to `:2753`) takes the object's actual position, searches for objects there and is satisfied when it finds the object itself. That always passes for a live object, even while physics throws it away: it does not compare against the requested position, measure drift or ask for stability between ticks. A vehicle spawned at a town with `ok=1` ended 40 km below the map. After any spawn that matters, confirm with `object_inspect` or `entities_query` that the distance to the requested position is as expected, and read again a few seconds later to rule out drift. A check that looks only at `ok` is invalid.
- The vector is in engine order `[x, y_up, z_north]` (`MCPBridge.c:1638`, `Vector(x,y,z)`), but the bridge's connect log prints the player position as `<x, z_north, y_up>`. Passing the log triplet as it is spawns the object about 6 km up: `IsSpawnReady` (2.0 m radius) is never satisfied, the job times out with `found=0`, and the engine deletes the object (`NETWORK (E): Will delete object ... outside world coords`). Convert `<x,z,y>` to `[x,y,z]` before every `world_spawn` and `camera_set`. After a spawn timeout, search the RPT for `outside world coords` before you retry; it tells bad coordinates from a slow spawn. A `scene_raycast` to the terrain gives the real `y_up`.
- `y=0` snaps to the ground. `ValidateSpawnArgs` makes `flags = ECE_PLACE_ON_SURFACE` the default for `flags=0`, and `IsAllowedSpawnFlags` asks for that bit in every accepted combination but one, `ECE_CREATEPHYSICS|ECE_TRACE`. `pos=[7500,0,7500]` gave `pos_real y=313.14` in four measurements. In vanilla `ECE_PLACE_ON_SURFACE` is 1060, the sum of `ECE_CREATEPHYSICS`, `ECE_UPDATEPATHGRAPH` and `ECE_TRACE` (`P:\scripts\3_game\ce\centraleconomy.c:38`).
- A spawn next to the player can land inside a building. Cast three or four `scene_raycast` rays to find clear ground before you choose the position.
- An object spawned with `flags=0` is saved by the server and outlives its run. Create test objects with `flags=8389668`, which is `ECE_PLACE_ON_SURFACE` (1060) plus `ECE_NOPERSISTENCY_WORLD` (8388608, `centraleconomy.c:31`). See `vehicle-smoke.md`, "Driving bench: leftover cars, the wrong car and old traces".
- A timeout leaves the command running: the spawn can still happen after you lost the `object_id`. Before you retry, check with `telemetry_read(mode="object_at")` for that type at the spawn position. `telemetry.found` 0 means none of that type is inside the radius at that moment (the command can still land later), and two or more inside the radius fail with `ambiguous_fixture` (`MCPBridge.c:3031` to `:3045`). Do not spawn again blindly.
- `rotation` changes how the object is posed (`collision-probes.md`, "Posing a test object square to the world").

## `wait_for`

- The player spawn pattern must not assume a gender. The example `Create entity type 'SurvivorM_` from the verb's own description fails silently with a female character: a 300 s timeout with the player already in the world and `Create entity type 'SurvivorF_Helga'` in the RPT. Use `Create entity type 'Survivor`.
- A response that lands about 200 ms after its trigger is always missed with a "from now" cursor. Pass `lookback_lines=200` for that case and accept trap 3 above: an older line can satisfy it.
- `wait_for(log_matches)` reads log files and does not cross the bridge; `wait_for(players_at_least)` does (`run-lifecycle.md`).

## `inventory_give`: one call is not one unit

`inventory_give(classname)` uses `CreateInInventory`. The vanilla `CreateInInventory` returns null whenever `FindFirstFreeLocationForNewEntity` finds no place (`P:\scripts\3_game\systems\inventory\inventory.c:876`), which is why trap 5 cannot tell a missing class from an item that does not fit. A stackable item is created with its default quantity, which can be a full stack. Never turn the number of calls into units or a value. After handing items out, measure each item's real `quantity` with an entity inspection or the total the mod exposes, and set every threshold for cost, leftover and cleanup from that measurement.

## `telemetry_read(mode="object_at")` reads any class

The bridge matches the type by exact `GetType()` inside the radius (`<dayz-mcp>/addon/scripts/5_Mission/MCPBridge.c:3007` to `:3051`), and the loopback only checks that `type` is a non-empty string (`<dayz-mcp>/tools/dayz_mcp/loopback.py:1349` to `:1358`). It answered `telemetry.found=1` with `pos`, `orientation`, `health01` and `declared_slots` for two custom character classes (`health01` 0 and 0.7525) and the vanilla `ZmbM_SoldierNormal` (0); the reply's top-level `found` stays 0. `inventory_attach` returned the same block for `SurvivorM_Francis`. It reads only the fields the bridge fills, not a mod's script members or sync variables.

`telemetry_read` is not hardened yet: it does not certify large JSONL traces or extreme ranges.

## `object_delete`

Always read `deleted`; `deleted:0` means nothing was removed. Some vanilla vehicles resist `object_delete`, and then the user removes them by hand with an admin tool.

## `player_respawn` works only from the death screen

Kill the player with outside damage: `world_spawn` a live infected with `flags=3108` next to it (a fall does not work with a panel open). Wait for the capture to go through its three stages (normal, desaturated with blood while unconscious, fully black when dead), then `player_respawn()` starts the vanilla sequence ("Spawning in 8 s"); the position jumped about 1,878 m. No client window is needed. The value 3108 is `ECE_PLACE_ON_SURFACE` plus `ECE_INITAI` (2048, `P:\scripts\3_game\ce\centraleconomy.c:18`).

On a living player it returns exactly the same `ok:1, requested:1` and does nothing; the position stays identical. Only the position tells the two cases apart.

## `key_press` sends a key code to the mission, not system input

`key_press(dik=1)` returns `delivered:1` and does not open the vanilla menu (`ui_tree` answers `no_menu`). That is not a failure: its description says "a mission callback, not OS input", and the vanilla menu does not hang off `OnKeyPress` (the mission hook is `P:\scripts\5_mission\mission\missiongameplay.c:742`). It works for mod UIs that do hang off that hook. Do not use it in place of the Escape key and do not call the verb broken from that test. It has no key-up and no hold, so it cannot finish a continuous action (`actions-ui-and-inventory.md`).

## `entities_query`, `surface_query` and unverified coordinates

- `entities_query` is reliable only with a player inside the area. Far from any player it answers 0 or its cap of 128 and shows no error. `surface_query` is reliable everywhere, since terrain is static. For a corridor, use three spheres of radius 65 with `count_total` as the truncation sign, and check the distance of the last row (results come nearest first).
- Check for cover before any teleport to unverified coordinates. A `scene_raycast` in `geom` mode from y+30 down to y-5 must hit within 0.05 m of the surface at both the player point and the vehicle point. It finds roofs, tree crowns and water (it hits the water surface above the seabed, with a negative y).

## Verbs added in bridge version 9

The version check needs the matching daemon and PBO pair.

- `object_anim` and `object_inspect` accept the `object_id` that `world_spawn` returned and resolve it in the bridge's registry. That works whatever the position, including test objects owned by the client whose server copy sits at the spawn point.
- `player_teleport` refuses a surface landing whose column is covered (`clearance_blocked`); pass `skip_clearance_check=true` for interiors.
- `entities_query` returns `nearest_player_m` and `reliability` (`player_in_bubble` or `remote_unverified`).
- An `object_anim` write is applied (`SetAnimationPhaseNow`, vanilla `P:\scripts\3_game\entities\entity.c:22`), but the `phase` in its own reply can lag one tick: phase 0, write 1.0, reply 0.0, next read 0.599. Confirm with a later read.
- The clearance probe is cast with `ignore='player'`, yet a survivor standing in the column still gave dy=1.671 and got a good site refused. Before you read `clearance_blocked` as a roof, check that no survivor stands in the column.

## `exec_enforce`

It does not run on the headless diag server; dayz-mcp records that as an engine limit, like `MakeScreenshot` in `captures.md`. Do not rely on it for verification logic; use a mission driver (`actions-ui-and-inventory.md`, "A mission driver for logic that has no verb").
