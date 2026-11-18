# Playbooks: pass and fail criteria by mod type

The scene to set before capturing, and what counts as PASS or FAIL for a static object, an item or weapon, and a vehicle.

The verbs are dayz-mcp's and their behaviour is third-party, measured in game sessions with that tool and not yet checked on `P:\`. Vanilla facts cite the vanilla file.

## Scene conditions, so captures can be compared

- `world_time_set` to noon. All five arguments (`year`, `month`, `day`, `hour=12`, `minute=0`) are required, like the vanilla `SetDate` call it wraps (`P:\scripts\3_game\global\world.c:46`).
- `world_weather_set(overcast=1.0)`. An overcast sky gives diffuse light: it removes the specular glint of direct sun that burns weapons and materials to white and hides detail (found on a rifle project, 2026-06-17).
- Do not use `time_multiplier=0` while animations are pending: it freezes the simulation.
- Place the object next to the player, not next to the camera: the streamed world follows the player (`captures.md`, "The bubble follows the player").

## Every playbook starts from the spawn

`world_spawn(type=<classname>, pos=[x,y,z])` passes if it returns `ok` with no `unknown_type` or `spawn_failed`. Save the real `pos` for the later steps, then confirm the object is where you asked (`verb-gotchas.md`, "`world_spawn`": `ok` alone proves nothing about position).

## Static object, container or building

- **Load.** The spawn passes (above). A failure means the class does not resolve: the mod is not mounted (mod paths must be absolute for the engine to mount them, see the `dayz-launch-test` skill), or its `CfgPatches` does not register. `/dayz-lint <ModName>` finds the second kind before a boot.
- **Visible, textured, winding.** Orbit the camera through at least four poses (front, side, back, overhead) with `camera_set` and `capture_screenshot`, and inspect each PNG. PASS means the object is visible, has no missing textures (no solid magenta, white or black), has plausible proportions, and shows no inverted faces or holes. A hole or missing face from one angle that is solid from the opposite angle is inverted winding. Before failing a model on its textures, look at the vanilla terrain and sky in the same frame: if they are flat too, the client did not load its textures and the frame says nothing about the model (`captures.md`, "Frames that say nothing about the model").
- **Collision.** `scene_raycast` in each of the `geom`, `view` and `fire` modes, with the ray battery and its two controls. The method is in `collision-probes.md`. For a building, cast at several points (walls, corners, floor). PASS means the rays that should hit return `hit=true` with the object's `object_type` or `object_class`. No hit where there should be one means the View Geometry or Fire Geometry LOD is missing or not resolved.
- **Placement.** `telemetry_read(mode="object_at", type=<classname>, pos=<spawn_pos>, radius=2)` returns `found=true`, a `pos` close to the spawn and a sensible `orientation`. PASS means not buried and not floating; cross-check `pos.y` with the captures.
- **Doors are not covered** by this playbook. What can and cannot be driven on a door is in `actions-ui-and-inventory.md`, "Doors".

## Item or weapon

- Load, visible, textured and winding as above, with the emphasis on proportions against a real-world reference and on the geometry after import (orientation, winding), which is where generated and imported meshes tend to fail.
- `telemetry_read(mode="object_at")` gives `attachment_count` and `health01`. Telemetry passes when the object is found with healthy values.
- Collision as for a static object: the ray battery with its two controls. Picking the item up, by hand or with `action_use`, does not test its collision (`collision-probes.md`, "Picking an item up proves nothing about its collision").
- A raised or aimed weapon pose needs the raise forced inside a mod, on the client (`captures.md`, "Capturing a raised weapon").

## Vehicle (placement and structure)

- Load, visible, collision and telemetry as above. `vehicle_enter(pos)` returning `seated=true` confirms the seat. `telemetry_read` gives `engine_on_server`, `wheel_count` and `fuel_fraction`.
- `vehicle_enter` only seats the player. Driving is the acceptance ladder, with the owner-side verbs `vehicle_get_in_client`, `engine_set`, `vehicle_control` and `vehicle_telemetry` (`vehicle-smoke.md` and `acceptance-ladder.md`).
- A bare spawn has no wheels and shows the brakes and hubs; that is not misalignment (`vehicle-smoke.md`, "A bare spawn exposes the undercarriage").

## The report

Write a criteria table (criterion, PASS, FAIL or INFO, evidence), attach the PNG captures and the telemetry and raycast JSON as evidence, give one overall verdict, and add a "manual test" section listing what was not covered (doors, shooting and so on).

Context cost: each capture costs about 25,000 tokens at 240 to 320 pixels. Batch the orbit captures and do not read a PNG again except to check one concrete thing; images fill the context quickly. Treat 25,000 tokens per image as a hard budget and do not ask for a higher resolution.

If a human is in the loop and the render is ambiguous, their eye outranks the capture: on one car project the grab was flaky and the user's reading was the reliable diagnosis of winding and proxy alignment. In one case (2026-06-24) the agent was about to sign a PASS on faint renders and the user's eye caught a proxy misalignment the captures could not resolve, which made it a correct FAIL.
