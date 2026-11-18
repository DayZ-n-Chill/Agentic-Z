# Pass and fail by mod type

What scene to set before capturing, and what counts as PASS or FAIL for a static object, an item or weapon, and a vehicle checked through dayz-mcp.

The verbs belong to the third-party dayz-mcp tool; their behaviour was measured in game with it and is not checked on `P:\`. Vanilla facts cite the vanilla file.

## Set the scene so captures compare

- `world_time_set` to noon. All five arguments (`year`, `month`, `day`, `hour=12`, `minute=0`) are required, like the vanilla `SetDate` it wraps (`P:\scripts\3_game\global\world.c:46`).
- `world_weather_set(overcast=1.0)`. Overcast gives diffuse light and removes the glint of direct sun that burns weapons and materials to white and hides detail.
- Do not use `time_multiplier=0` while animations are pending: it freezes the simulation.
- Place the object next to the player, not next to the camera, because the streamed world follows the player (`captures.md`, "The streamed world follows the player, not the camera").

## Every check starts from the spawn

`world_spawn(type=<classname>, pos=[x,y,z])` passes when it returns `ok` with no `unknown_type` or `spawn_failed`. Keep the real `pos` for later steps, then confirm the object is where you asked: `ok` alone proves nothing about position (`verb-gotchas.md`, section "`world_spawn`").

## Static object, container or building

| Check | How | PASS | FAIL means |
|---|---|---|---|
| Load | The spawn above | `ok` | The class does not resolve: the mod is not mounted (mod paths must be absolute, `../windows-launch-cycle.md`) or its `CfgPatches` does not register. `/dayz-lint <ModName>` finds the second kind before a boot. |
| Visible, textured, winding | Orbit at least four poses (front, side, back, overhead) with `camera_set` and `capture_screenshot`; inspect each PNG | Visible, no solid magenta, white or black, plausible proportions, no inverted faces or holes | A hole seen from one side that is solid from the other is inverted winding. If the vanilla terrain and sky are flat in the same frame, the client did not load textures and the frame says nothing (`captures.md`, "Frames that say nothing about the model"). |
| Collision | `scene_raycast` in `geom`, `view` and `fire`, with the full set of rays and its two controls (`collision-probes.md`); for a building, walls, corners and floor | Rays that should hit return `hit=true` with the object's `object_type` or `object_class` | The View Geometry or Fire Geometry LOD is missing or not resolved. |
| Placement | `telemetry_read(mode="object_at", type=<classname>, pos=<spawn_pos>, radius=2)` | `found=true`, `pos` close to the spawn, a sensible `orientation`; not buried or floating, `pos.y` agreeing with the captures | Buried or floating. |

Doors are not covered here; what can be driven on a door is in `actions-ui-and-inventory.md`, section "Doors".

## Item or weapon

- Load, visible, textured and winding as above. Look hardest at proportions against a real-world reference and at the geometry after import (orientation, winding), where generated and imported meshes tend to fail.
- `telemetry_read(mode="object_at")` gives `attachment_count` and `health01`. It passes when the object is found with healthy values.
- Collision as for a static object. Picking the item up, by hand or with `action_use`, does not test its collision (`collision-probes.md`, "Picking an item up proves nothing about its collision").
- A raised or aimed pose needs the raise forced inside a mod, on the client (`captures.md`, "Capturing a raised weapon").

## Vehicle placement and structure

- Load, visible, collision and telemetry as above. `vehicle_enter(pos)` returning `seated=true` confirms the seat. `telemetry_read` gives `engine_on_server`, `wheel_count` and `fuel_fraction`.
- `vehicle_enter` only seats the player. Driving uses the owner-side verbs `vehicle_get_in_client`, `engine_set`, `vehicle_control` and `vehicle_telemetry` (`vehicle-smoke.md` and `vehicle-acceptance.md`).
- A bare spawn has no wheels and shows the brakes and hubs. That is not misalignment (`vehicle-smoke.md`, "A bare spawn shows the undercarriage").

## The report

Write a table of criterion, PASS, FAIL or INFO, and evidence. Attach the PNG captures and the telemetry and raycast JSON, give one overall verdict, and add a "manual test" section listing what was not covered (doors, shooting and so on).

Each capture costs about 25,000 tokens at 240 to 320 pixels. Batch the orbit captures, never ask for a higher resolution, and do not open a PNG again except to check one concrete thing.

When a person is watching and the render is ambiguous, their eye outranks the capture. On a car with a flaky grab, the user's reading was the reliable call on winding and proxy alignment, and caught a proxy misalignment on faint renders that were about to be signed as PASS.
