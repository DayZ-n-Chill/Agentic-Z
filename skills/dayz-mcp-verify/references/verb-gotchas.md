# Verb gotchas: what each dayz-mcp reply does and does not prove

Per-verb traps of the dayz-mcp bridge (`world_spawn`, `wait_for`, `logs_since`, `inventory_give`, `telemetry_read`, `object_delete`, `player_respawn`, `key_press`, `entities_query`, `player_teleport`, `object_anim`), each with the check that replaces the misleading reply.

The verb behaviour is third-party: measured in game sessions with dayz-mcp, not yet checked on `P:\`. Vanilla facts (spawn flags, inventory calls) cite the vanilla file. File and line numbers such as `MCPBridge.c:2729` are lines of dayz-mcp's own source at the time of the measurement.

## The oracle is the effect, never the reply (SP-351, added 2026-08-29)

`ok` does not mean success, and at least four different encodings coexist. Measured in game on 2026-08-29, same tool, same reply shape, opposite effect:

```
object_delete(999999999) -> ok:1, deleted:0     <- deleted nothing
object_delete(<real id>) -> ok:1, deleted:1     <- deleted it
```

One oracle per verb:

| What you want to know | Do not look at | Look at |
|---|---|---|
| Did it place the object where asked? | `ok` | `surface_query(x,z).y` against the `pos_real` of `world_spawn` |
| Did it delete anything? | `ok` | `deleted` |
| Did the player respawn? | `ok`, `requested` | `query_player_state.pos` before and after |
| Was the wait satisfied? | `ok` | `satisfied` |

## Six traps that cost one run each (added 2026-08-18)

Verified in game on 2026-08-18 during a test battery on an ATM device. Each cost at least one run, and five of the six produce a verdict that accuses the mod when the mod has no fault (6 runs, 0 real mod failures). Check them before writing the first probe.

1. **`dayz_test_run` does not load `@DayZ_MCP` by default, and answers `succeeded` anyway.** Both processes start, the game works, and the bridge stays silent. The symptom you get (`server_poll_stale`, `client_not_polling`, `ready.reason=no_run`) points at the bridge or the key, not at the mod set, so the time is lost in the wrong place. Gate: pass `extra_mods=["@DayZ_MCP"]` and confirm in the server log that the define `DayZ_MCP` appears in all four script modules, or look for `[MCP-POC]` lines.
2. **`logs_since` does not accept its own `marker`.** It returns the marker as a dict `{path: [offsets]}` and its parameter wants a string: a Pydantic `ValidationError`. Incremental draining is impossible. Workaround: read the whole log at the end of the sequence and assign the responses in order, checking the alignment with a field of the event itself (a type, an id). If two probes share that field, mark `ambiguous_alignment` instead of guessing.
3. **`wait_for(log_matches)` does not work for waiting on your own response.** With the default `lookback_lines=200`, a line from the previous probe satisfies the pattern at once. With `lookback_lines=0` it has been seen timing out with the line already in the client log, returning a line from another flow in `observed`. Use it as an opportunistic wait; the verdict comes from polling `logs_since`.
4. **The player's inventory is not reset between runs.** The second run finds what the first left, nothing fits any more and the provisioning fails silently (`create_failed`, or a gift of 0 units). To chain runs: `dayz_test_stop`, delete `<mission>\storage_1\players.db` after backing it up, and relaunch (about 3 minutes). `clean=true` does not do this: it forces a build and passes `-clear` to AddonBuilder, so it rebuilds the PBO and breaks binary identity, which an A/B test cannot afford. Balance or state that the mod saves in the server profile survives the deletion.
5. **`inventory_give` returns `create_failed` both when the class does not exist and when the item does not fit.** The two cannot be told apart. Before blaming the inventory, check that the class exists: search the mission's `types.xml` and try a vanilla control item (`Apple` works). Do not assume the class names in the mod's config exist: they can point at a mod that is not loaded, in which case the count of that exact class is 0 forever and the whole feature looks broken without being broken.
6. **Do not believe a verdict without reading the client log.** Many mod events are written by the client, not the server. In the battery behind this list the automatic verdict said FAIL or INCONCLUSIVE six times in a row while the client log showed the operations running correctly. The dangerous failure of a test cell is not "does not measure", it is "measures badly and accuses the mod", and that travels into project documents. If a verdict says FAIL, open the client log before recording it. `/dayz-logwatch --dir <client profile folder> --since 5` reads it with triage.

## `world_spawn`

- **`ok=1` does not prove the object stays where you asked** (added 2026-08-21). `IsSpawnReady` (`MCPBridge.c:2729-2753`) takes the object's actual position, searches for objects there, and is satisfied when it finds the object itself. An object is always where it is: the gate is a tautology and passes for any live object, even while physics is throwing it away. It does not compare against the requested position, does not measure drift and does not ask for stability between ticks. Real case: a spawn at a town with `ok=1` and a vehicle that ended at Y = -40 km. This is different from the inverted coordinates below, which time out: this one gives a false pass. Rule: after any `world_spawn` that matters, confirm with `object_inspect` or `entities_query` that the distance to the requested position is as expected, and read again a few seconds later to rule out drift. A playbook verdict that looks only at `ok` is invalid.
- **The vector is in engine order `[x, y_up, z_north]`** (`MCPBridge.c:1638`, `Vector(x,y,z)`), but the bridge's connect log prints the player position as `<x, z_north, y_up>` (SP-060, verified live 2026-07-11). Passing the log triplet as it is spawns the object about 6 km up: `IsSpawnReady` (2.0 m radius) is never satisfied, the job times out with `found=0`, and the engine deletes the orphan (`NETWORK (E): Will delete object ... outside world coords`). That cost three timeouts in a row. Convert `<x,z,y>` to `[x,y,z]` before every `world_spawn` and `camera_set`; after a spawn timeout search the RPT for `outside world coords` before retrying (it tells bad coordinates from a slow spawn). A `scene_raycast` to the terrain gives the real `y_up`.
- **`y=0` snaps to the ground.** `ValidateSpawnArgs` sets `flags = ECE_PLACE_ON_SURFACE` as the default for `flags=0`, and `IsAllowedSpawnFlags` asks for that bit in every accepted combination but one, `ECE_CREATEPHYSICS|ECE_TRACE`. Measured four times: `pos=[7500,0,7500]` gave `pos_real y=313.14`. In vanilla, `ECE_PLACE_ON_SURFACE` is 1060, the sum of `ECE_CREATEPHYSICS`, `ECE_UPDATEPATHGRAPH` and `ECE_TRACE` (`P:\scripts\3_game\ce\centraleconomy.c:38`).
- **A spawn next to the player can land inside a building.** Probe three or four `scene_raycast` rays to find clear terrain before choosing the position.
- **An object spawned with `flags=0` is persisted by the server and outlives its run.** Create test fixtures with `flags=8389668`, which is `ECE_PLACE_ON_SURFACE` (1060) plus `ECE_NOPERSISTENCY_WORLD` (8388608, `P:\scripts\3_game\ce\centraleconomy.c:31`). See `vehicle-smoke.md`, "Driving bench".
- **A timeout leaves a zombie command** (SP-152): the spawn can still run after you lost the `object_id`. Before retrying, reconcile the effect with `telemetry_read(mode="object_at")` for that type at the spawn position: `telemetry.found` 0 means none of that type is inside the radius when the read runs (the zombie command can still run later), and two or more of that type inside the radius fail with `ambiguous_fixture` (`MCPBridge.c:3031-3045`; not exercised on a zombie spawn). Do not duplicate the spawn blindly. Corrected 2026-10-03: an earlier version said "if the `object_at` cap prevents it, use logs plus user inspection"; there is no such cap.
- **`rotation`** changes how the object is posed; see `collision-probes.md`, "Axis-aligned fixtures".

## `wait_for`

- **The player spawn pattern must not assume a gender.** The example `Create entity type 'SurvivorM_`, suggested by the description of `wait_for` itself, fails silently with a female character: a 300 s timeout with the player already in the world and `Create entity type 'SurvivorF_Helga'` in the RPT. Use `Create entity type 'Survivor`.
- **A response that lands about 200 ms after its trigger is always lost with a "from now" cursor** (BUG-086: 2 of 2 timeouts with the line already in the log). For that case pass `lookback_lines=200`, and accept trap 3 above: an older line can satisfy it.
- `wait_for(log_matches)` reads log files and does not cross the bridge; `wait_for(players_at_least)` does (see `run-lifecycle.md`).

## `inventory_give`: one call is not one unit (SP-300, added 2026-08-31)

`inventory_give(classname)` uses `CreateInInventory`. The vanilla `CreateInInventory` returns null whenever `FindFirstFreeLocationForNewEntity` finds no place (`P:\scripts\3_game\systems\inventory\inventory.c:876`), which is why trap 5 above cannot tell a missing class from an item that does not fit. A stackable item is created with its default quantity, which can be the full stack. Never turn the number of calls into units or into a nominal value. After provisioning, measure the item's real `quantity` with an entity inspection or with the aggregate the mod exposes, and calibrate every threshold for cost, leftover and cleanup against that measurement.

## `telemetry_read(mode="object_at")` reads any class (SP-152, corrected 2026-10-03)

The bridge matches the type by exact `GetType()` inside the radius (`<dayz-mcp>/addon/scripts/5_Mission/MCPBridge.c:3007-3051`), and the loopback only checks that `type` is a non-empty string (`<dayz-mcp>/tools/dayz_mcp/loopback.py:1349-1358`). [EXACT][CLAIM-MCPV-OBJECT-AT-ANY-TYPE] On 2026-10-02 (DayZDiag 1.29.163709, run `1c289781`) it answered `telemetry.found=1` with `pos`, `orientation`, `health01` and `declared_slots` (the reply's top-level `found` stays 0) for three types: a custom character class (`health01` 0), the vanilla `ZmbM_SoldierNormal` (0) and a second custom character class (0.7525). `inventory_attach` returned the same telemetry block for `SurvivorM_Francis`. It reads only the fields the bridge fills, not a mod's script members or sync variables.

Corrected 2026-10-03: this entry used to say that on the frozen platform `telemetry_read(mode="object_at")` only accepted one hard-coded vehicle class, with the limit in the Python loopback, and that for other classes the diagnosis had to be planned with server logs and user tests. The oldest copy of the tools on disk (2026-07-25) has that class check only in the loopback's `vehicle_prepare_fixture` branch, whose arguments also carry `mode="object_at"`, and its `telemetry_read` took any non-empty `type`; which verb returned the `bad_args` behind the old entry on 2026-08-02 is not recorded. The tools' 2026-08-16 release has no such check.

`telemetry_read` is exposed as it is (BUG-010, BUG-011, BUG-012, hardening pending): it does not certify large JSONL fixtures or extreme ranges.

## `object_delete`

Always read `deleted`. `deleted:0` means nothing was cleaned up. Some vanilla vehicles resist `object_delete`; if that happens, the cleanup is manual, by the user with an admin tool.

## `player_respawn` works without a client window, and only from the death screen

Verified 2026-08-29 (run `02524f97`): kill the player with external damage (a `world_spawn` of a live infected with `flags=3108` next to it; falling does not work with a panel open), wait for the capture to go through its three phases (normal, desaturated with blood for unconscious, fully black for dead) and then `player_respawn()` starts the vanilla sequence ("Spawning in 8 s"). Measured: the position jumped about 1,878 m. The flag value 3108 is `ECE_PLACE_ON_SURFACE` plus `ECE_INITAI` (2048, `P:\scripts\3_game\ce\centraleconomy.c:18`).

Trap: on a living player it returns exactly the same (`ok:1, requested:1`) and does nothing; the position is byte-identical. The reply does not tell the two cases apart; the position does.

## `key_press` delivers a key code to the mission, it is not operating system input

`key_press(dik=1)` returns `delivered:1` and does not open the vanilla menu (`ui_tree` answers `no_menu`). That is not a failure: its description says "a mission callback, not OS input", and the vanilla menu does not hang from `OnKeyPress` (the mission hook is `P:\scripts\5_mission\mission\missiongameplay.c:742`). It works for mod UIs that do hang from there. Do not use it as a substitute for the system Escape key, and do not call the verb broken from that test. By its own description it is also no key-up and no hold, so it cannot finish a continuous action (`actions-ui-and-inventory.md`).

## `entities_query`, `surface_query` and unverified coordinates (added 2026-08-24)

- **`entities_query` is reliable only with a player inside the area.** Far from any player it answers 0 or the cap of 128 (two modes) and shows no error. `surface_query` is reliable everywhere (static terrain). For a corridor, use three spheres of radius 65 with `count_total` as the truncation indicator, and check the distance of the last row (results come nearest first).
- **Canopy gate before any teleport to unverified coordinates.** A `scene_raycast` in `geom` mode from y+30 to y-5 must hit within 0.05 m of the surface at both the player point and the vehicle point. It detects roofs, tree crowns and water (it hits the surface sheet above the seabed, with a negative y).

## Bridge v9 (dayz-mcp commit `d73da6c`, added 2026-08-24)

The version gate needs the matching daemon and PBO pair.

- `object_anim` and `object_inspect` accept `object_id` (the one `world_spawn` returned) and resolve it against the bridge's registry. That is independent of position and reaches client-authoritative fixtures whose replica sits at the spawn point.
- `player_teleport` rejects surface landings whose column is covered (`clearance_blocked`); pass `skip_clearance_check=true` for interiors.
- `entities_query` returns `nearest_player_m` and `reliability` (`player_in_bubble` or `remote_unverified`).
- Measured caveat: an `object_anim` write is applied (`SetAnimationPhaseNow`, vanilla `P:\scripts\3_game\entities\entity.c:22`), but the `phase` in the reply itself can lag one tick (0, write 1.0, reply 0.0, next read 0.599). Confirm with a later read, not with the reply.
- The clearance probe is cast with `ignore='player'`, and a survivor standing in the column still gave dy=1.671 and got the point rejected. A good site (x 4300) was demoted by mistake this way: before reading a `clearance_blocked` as a roof, check that no survivor stands in the column.

## `exec_enforce`

It does not execute on the headless diag server. dayz-mcp records that as an engine limitation (its GATE4B-LIM), like `MakeScreenshot` in `captures.md`. Do not rely on it to run arbitrary verification logic; use a mission driver (`actions-ui-and-inventory.md`, "A mission driver for logic that has no verb").
