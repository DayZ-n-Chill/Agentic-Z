# Rip structural LODs and first spawn

How to build the body and structural LODs of a ripped car, why a rip body crashes the render until it is thinned, which faults block the first spawn and get-in, and the offline checks worth building before testing in game.

Measured on cars built from rips (`rip-import.md`), in game and offline, against the vanilla sedan and shipped third-party car mods. Offline checks passed on every one of these cars before the game rejected them; the in-game spawn is the real test.

## Body: a real shell plus proxy chunks

A dense rip body does not collapse cleanly to a game budget: edge collapse, even per part with boundaries kept, crumples the dense aero parts into a wreck. An all-proxy body with no base breaks `hiddenSelections` paint. Copy the shipped pattern instead. On converted copies (**model knowledge**), the sedan's LOD 0 is a real shell of about 14.6k faces with the paint selection, lights and damage zones, plus proxies for doors, hood, trunk, engine, wheels and crew; a shipped car mod's LOD 0 is a real shell of about 13.4k faces plus proxies, with one visual LOD.

- LOD 0 is a basic real shell from the clean stock parts (`body_a` and the lights), painted through `hiddenSelections` (`color`) and carrying the light selections (`light_left`, `light_right`, `light_brake_1_2`, `light_brake_2_2`, `light_reverse_1_2`, `light_reverse_2_2`, `light_dashboard`).
- Everything else is proxy chunks, each under 65535 resolved vertices: dense aero parts (flares, custom fenders, fog lights, bumpers, anything over about 8k vertices), other panels, glass, interior. Chunks are in car space, placed with the vanilla body chunk frame and paths without `.p3d` (`vehicle-proxies.md`).
- `hiddenSelections` does not reach proxy geometry, so painted chunks carry the paint in their own `.rvmat`. One fixed colour per car; colour swaps and damage materials on chunks are out.
- Keep each chunk's light selections small. Light selections of about 6594 faces each on the shell came with spawn lag and broken light paint.

A body chunk that renders about 2.5 m away from where it belongs, with a correct frame, was seen on a car built this way. Keep a real shell in LOD 0, keep chunks under the vertex ceiling, and settle placement before iterating.

## Thinning the body

A raw rip body is about 400k visual faces. Above roughly 315k the client crashes while drawing the car: lag at spawn, then a crash (one car loaded at 315k, another at 417k did not). Decimate the proxy chunks only, with a planar dissolve:

1. Per chunk, export vertices, faces, UVs and each face's material, texture and selection.
2. In Blender, `dissolve_limited` at 10 degrees with `delimit={MATERIAL,UV,SEAM,SHARP}`. It collapses the source's flat over-subdivision and keeps boundaries, curves, materials and UVs.
3. Triangulate, rebuild the `.p3d`, recompute smooth normals and rebuild the named selections from the stored slots.

One body went from 440k to 198k faces (77.7 to 39.7 MB) with its shape intact and its structural checks still passing. Leave the shell's visual LOD, the View Pilot LOD and the structural LODs alone. Planar dissolve only merges nearly flat faces, so it does not deform the car.

## What crashes the render

Neither fault shows in any offline check or Blender render; only the game crashes, 9 to 22 seconds after the car comes on screen, always at the same fault offset in an unknown module (the GPU driver; the module base moves each launch, the offset does not).

- Collapsed UVs. A visual LOD whose vertices all share one UV (for example a transplant that set every corner to `(0,0)`) gives zero UV derivatives, so mip selection takes `log2(0)`, gets NaN, and the GPU crashes when that surface is drawn. Every transplanted mesh must carry real UVs, and avoid seams with extreme jumps: a cylindrical `atan2` UV tiled N times can still crash at its seam. Count unique UVs per LOD; the sedan wheel's LOD 0 has 1203, not 1.
- Body weight, above.

When the client crashes on the car: rule out weight, then corrupt geometry (NaN, overflow, NaN UVs), then a damaged environment (a corrupt `storage_1` gives false load crashes; wipe it), then change one render input at a time: glass alpha, per-mesh materials, the wheel.

## The structural LODs

The builder adds structural LODs to the deployed visual shell without touching its body geometry, writing a new `.p3d`; deploying is a separate step that checks the file hash. py3d helpers: `LOD.set_memory_point(name, coords)`, two-point `*_axis` selections by hand, `LOD.add_proxy(path, index, origin, rotation)`, `LOD.set_total_mass(kg)`, and a box helper that winds each box outward from its own centre.

| LOD | Contents |
|---|---|
| Geometry 1e13 | Four or more convex closed `component0N` boxes following the body, wells cleared at the corners (chassis points at least `tire_radius + 0.07` from each wheel centre), four small hubs `wheel_X_Y_damper_land` (about 0.20 by 0.18 by 0.18), `seat_driver` and `seat_codriver`. Properties `autocenter=0` and `class=vehicle`. `set_total_mass(curb_mass)` on this LOD only; symmetric boxes put the centre at x 0. Hubs and seats are also `componentNN`. |
| Memory 1e15 | Per wheel `_axis` (2 points, lateral), `_damper`, `_damper_axis` (2 points, vertical), `_damper_land` (hub); front `_steering` and `_steering_axis`; `pos_driver`, `pos_codriver` with `_dir`; `seat_con_1_1`, `seat_con_2_1`; dials `mph`, `rpm`, `fuel_1`, `drivewheel` with axes; `refill`, not `fuelpoint`, since the engine reads the fuel position from `refill` (`P:\scripts\3_game\vehicles\transport.c:112`); `light_left`, `light_right` with `_dir`, `light_reverse`, `reflector_1_1`, `reflector_2_1`; `engine`, `drown_engine`; `ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max`, `invview`, `pos center`; `ptcexhaust_start`, `ptcexhaust_end`, `ptcenginepos`, `ptccoolantpos`. `light_left` is +x and `light_right` -x, as on the sedan. |
| View Geometry 6e15 | One occlusion `component01`, the two seat boxes (inward wound, `crew-get-in-geometry.md`), four wheel proxies (vanilla `sedanwheel`), crew proxies `crew_driver` (bone `crewdriver`) and `crew_cargo` (bone `crewcodriver`) from `P:\DZ\vehicles\wheeled\proxies\`, each with its bone selection. |
| Fire Geometry 7e15 | One box per damage zone, each tagged both `component0N` and `dmgzone_X`, plus wheel and crew proxies with bone selections. |
| Hitpoints 5e15 | One point per damage zone. Assert that the Hitpoints set, the Fire Geometry damage zones and config `componentNames[]` are the same set, and hand that list to the config author. |
| Shadow 1e4 | The shell shrunk about 2% about its centre, materials and UVs removed, or built from the rip's `__slod` parts. A shadow not smaller than the visual mesh shades the whole body. |
| View Pilot 1100 | The car's own cockpit (dash, gauges, steering wheel), not the seats; it counts toward the vertex ceiling (`view-pilot-and-first-person.md`). |

Assert after assembly that only Geometry carries mass; a stray `#Mass#` elsewhere spawns the car underground (`vehicle-geometry-and-mass.md`). `new Point()` and `add_proxy` points default to `mass=None`.

`validate()` findings that are expected on a vehicle:

- `ERR_AXIS_SELECTION_MISSING` for every Memory `*_axis` with no visual selection named like the axis without its `_axis` suffix. For wheels it is real: add each wheel proxy face to visual `wheel_X_Y` (spin), `wheel_X_Y_damper` (suspension) and, at the front, `wheel_X_1_steering`, or `model.cfg` animates nothing. For dials not built yet it is expected.
- `WARN_NOT_WATERTIGHT` (proxy triangles are open), `WARN_WINDING_MIXED` on multi-box collision (each box is consistent about its own centre while the warning uses the global centre; `_shared/models/generated-model-rules.md`, "The per component winding check"), `WARN_LOD_KIND_UNKNOWN` for 1100.

A parent `model.cfg` animates only its own selections; a proxy only moves with its anchor face. So the steering wheel (`drivewheel`) and gauge needles (`mph`, `rpm`, `fuel_1`) must live in the shell, not in a proxy chunk. If they were grouped into a chunk, move them into the shell first. A rip's gauge cluster is usually one mesh with no separate needles, so needles need face segmentation or new geometry (`gauge-needles.md`); place the dial memory points regardless.

## First spawn faults

On the first spawn the server RPT showed:

```text
PHYSICS (E): Action selection 'seat_driver'/'seat_codriver' was not found in view or fire geometry ... class Crew::Crew
PHYSICS (E): Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry
```

and nothing usable spawned. The fixes, in the order they were found:

| Fault | Fix | Read |
|---|---|---|
| Hubs and seats are islands outside every `componentNN` (0% overlap) | Tag each hub and seat box as a `componentNN` too | `vehicle-proxies.md`, "Hub and seat selections share faces with a component" |
| Body chunks turned about 90 degrees and scattered | Body chunk frame `R=((-1,0,0),(0,0,1),(0,1,0))` | `vehicle-proxies.md` |
| Texture on the inside, outside see-through | Keep the glTF vertex order; never "make outward" by centroid | `rip-geometry-and-winding.md` |
| Crew and wheel proxies not found | Bone selections next to each attachment proxy | `vehicle-proxies.md` |
| No get-in prompt, telemetry class `CarScript` | A thin script class | `crew-get-in-geometry.md` |
| Only the driver can get in | Inward wound seat cubes with point flags `0x0000003F` | `crew-get-in-geometry.md` |

These are not the cause and changed nothing: binarized against pack only (same errors either way, so a vehicle does not have to be ODOL to simulate); penetration materials on the collision faces (a real defect, since vanilla uses `dz\data\data\penetration\*.rvmat`, but a ballistics fault); the audit's LOD 0 vertex count of 96585 (face indices; the resolved count was 22143); a hub of 8 points instead of the sedan's 16; seats in Geometry.

A spawn with no wheels attached sits on its chassis, and empty arches look like holes.

## See-through checks on an untextured car

Judging winding by eye before texturing gives three false holes: untextured glass looks see-through (it needs a glass material), empty arches plus tall grass look like holes in the lower flank, and the checkerboard placeholder is opaque, not a hole. A panel that hides distant terrain at its own height is solid; real see-through shows only below the sill or inside the arches. A ray against the Geometry LOD that hits a closed hull supports solidity, but it tests Geometry, not the visual LOD.

A metric that agrees with the source glTF winding per chunk read 0.127 before a flip and 0.873 after, exact complements: it detects a global flip and cannot tell a solid chunk from a see-through one. Test any winding metric on a part known solid reading solid, not only on a broken part reading broken.

Rip chunks carry only material selections, so to flip one piece that shares a chunk with others, group faces into connected parts by shared points and pick the part by position (for example centroid `z < -0.6` and `y >= 0.85` gave 7 of 88 front parts). Flip by reversing each face's vertex order and leave the normal pool alone; it is global, indexed by `vertex.normal_index`.

## Offline checks worth building

- Split checks into universal (the engine contract any car meets: hub and seat components, crew proxies in View Geometry, wheel proxies) and car policy (damage zone list, chunk names). Only universal checks block every car.
- Run the universal checks on the converted sedan first; if it fails, the check is wrong (`vehicle-structural-parity.md`).
- Prove a check can fail: a synthetic good model passes and a broken one fails exactly the expected set, including missing `componentNN` tags.
- Prove the writer loses nothing: read, save and read with py3d and compare.
- Test the builder: rebuild the sedan's structural LODs from its own memory points and require a pass, then switch off the `componentNN` tagging and require a failure. This would have found the first spawn fault offline.
- Fit the transform from source and output point pairs, then fit four wrong transforms (a sign flip, `Y0` off by 0.1, a 1.05 scale, an axis swap) and require each to miss by far more than the tolerance; a residual of 0 from the same transform proves nothing.
- Read proxy paths in either form when checking, so a `.p3d` suffix is reported, not hidden.
- Resolution bands for classifying LODs: Geometry about 1e13, Memory 1e15, View Geometry 6e15, Fire Geometry 7e15, View Pilot 1100, Shadow 1e4, visual below 100. Classify proxies by path ending (`wheel.p3d`, crew names), not loose substrings. Check the target file exists before importing py3d, so a missing file reports cleanly.
- A Blender render with back-face culling shows the other side of each face from the game and does not resolve body chunks. Use it for presence, silhouette and proxy inventory only.

None of these are wired into `/dayz-build-pbo`. Close a step only when the sedan passes, the target passes the hard checks, the builder test passes and the renders were looked at.

## Building and launching

- The test launcher's pack-only switch alone ships the old PBO; add the build switch too (`-Build -PackOnly`). File patching does not load a new `worldScriptModule` `.c` or `.p3d` geometry from the work drive, so a script or geometry change that "did nothing" usually means the PBO was not rebuilt. Pack only keeps MLOD per-face materials, which binarize would drop.
- A diag server started from a process the agent owns dies when that process ends, mid CE load and with no RPT, while the client survives. Start server and client from a `.bat` with `start ""` so they run detached, and poll `Get-NetUDPEndpoint -LocalPort 2302` yourself. Two agent sessions testing in game on one machine kill each other's diag processes; test one at a time.
- Before basing a fix on a mod tree, read the build script for its source root and compare a file hash from that root with the matching file in the deployed PBO. A complete looking copy can be an older generation.
- Named selections survive a raw pack only build unchanged, measured offline with 170 selections, mixed case and names up to 63 characters, order and membership included. This does not cover binarized ODOL; repeat the check if the tools change.
