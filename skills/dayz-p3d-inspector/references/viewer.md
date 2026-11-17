# The inspector viewer

What the HTML page written by `p3d_inspector_viewer.py` shows, how the user works in it, and the design choices that must not be undone when the script is changed.

Tool behaviour, not game facts. The point names it colours are the vanilla ones in `_shared/models/memory-points.md`, for example `ce_center`, which vanilla script reads at `P:\scripts\3_game\entities\object.c:1363`.

## Layers

Each layer has a toggle in the toolbar. The seven wireframe LOD layers start off.

| Layer | Shows |
|---|---|
| Visual | the model, flat shaded, no textures |
| Geometry | green wireframe of the collision LOD |
| Fire Geo | red wireframe of the bullet collision LOD |
| View Geo | blue wireframe of the sight and action cursor LOD |
| LandContact | yellow-green wireframe of the ground contact points |
| Roadway | cyan wireframe of the walkable surfaces |
| Paths | magenta wireframe of the AI paths |
| HitPoints | orange wireframe of the hit points |
| Memory Pts | a coloured sphere at each memory point |
| Axes | purple arrows along the animation axes |
| Bounds | the bounding box (cyan) and the `box_placing` box (orange) |
| Labels | floating names on memory points and axes |
| Grid | a reference grid |
| Wireframe | a wireframe over the visual mesh |
| Export Recipe | opens a box holding the edited Recipe JSON |

## Memory point colours

| Category | Colour | Points |
|---|---|---|
| Center | cyan | `pos center`, `ce_center` |
| Interaction | red | `actionPos` and other action points |
| Axis | purple | the two end points of an animation axis |
| Placing | orange | `box_placing_min`, `box_placing_max` |
| Port | deep orange | `port_*`, `cable_*` (electrical port points of power grid mods; third-party mod names, not vanilla) |
| Proxy | gray | proxy attachment points |
| Other | light gray | everything else |

## Side panels

- **Points**: every memory point with live coordinates; click one to fly the camera to it.
- **LODs**: each LOD with its point and face counts and its selections.
- **Selections**: every named selection in every LOD.
- **Paths**: the texture and material paths the model names, with a warning on `P:\` paths. It is a hint only; `/dayz-p3d-audit` does the real path check.

## Working in it

| Action | How |
|---|---|
| Orbit | drag with the left button on empty space |
| Pan | drag with the right button |
| Zoom | mouse wheel |
| Select a point | click its sphere; a panel shows its coordinates |
| Move a point | click its sphere and drag; it moves in the plane facing the camera |
| Snap to the grid | hold Shift while dragging |
| Grid size | press `1` for 1 cm, `2` for 5 cm |
| Focus | click a point in the Points panel |
| Export | press Export Recipe, then Select All and Ctrl+C in the box. The text holds `meta`, `memory_points`, `axes` and `bbox` only; copy `memory_points` and `axes` into the extracted Recipe before building |

While a point is dragged the page updates, live: the sphere, its label, the axis line and arrow when the point is an axis end, the placing box when it is `box_placing_min` or `box_placing_max`, the coordinates in the side panel and the info panel, and the Recipe held in memory. A floating readout shows X, Y and Z, and the snap size while Shift is held.

## Design choices to keep

- **Three.js 0.185.1, loaded as ES modules through an importmap from jsDelivr.** The script does not write the scene setup itself: the importmap, the imports (OrbitControls), the renderer, camera, controls, grid, resize handling and render loop come from `viewer_core.py`, the scaffold the 3D viewer tool and `/dayz-proxy-align` also use. The script looks for it in the tool folder `scripts/tools/dayz-3d-viewer` first, then in the shared skills folder `_shared`, and refuses a copy with another contract or Three.js version. Change the Three.js version there, never in this script.
- **If the page shows no canvas when opened from disk.** An earlier version of this viewer (Three.js 0.160.0 as ES modules) failed that way in Chrome on Windows: the browser blocked the module request from a `file://` page (`net::ERR_BLOCKED_BY_ORB`) and the whole script stopped without a word. That version was replaced for a time by r0.147.0 loaded with plain `<script>` tags, the last release that ships non-module files, and the script has since moved to the shared scaffold. Not checked in a browser here: if the fault shows again, serve the folder (`python -m http.server`) and open the page over `http://localhost`.
- **Labels are HTML elements** placed with `Vector3.project()`, not a CSS2DRenderer.
- **Bounding boxes are hand-built line segments**, not a Box3Helper.
- **Every material is a MeshStandardMaterial**, so a selected object can glow (emissive).
- **Buffers use `BufferAttribute` with an explicit `Float32Array`.**
- **Dragging.** Hovering a sphere turns orbit control off before the button goes down, so the press starts a drag instead of an orbit; moving off the sphere turns it back on. The drag begins after the pointer has moved more than 5 pixels, on a plane through the point that faces the camera, and ends on release.
- **Export uses a text box**, because the clipboard API is blocked for a page opened from disk.

## Measuring visibility: sample the area, not the centroid

To decide whether a selection can be seen from outside, cast rays from random points spread over each face (about 3,000 per LOD) and report the share of free area. One ray from the centroid lies. Measured on a heater model: centroid rays reported 48 of 48 faces blocked in all six directions, while area sampling showed 84 to 86 % free, because every face was a long thin triangle whose centroid sat behind a 1 to 2 mm wire. The false reading nearly led to rebuilding the model's glowing grid when the fault was in the config.
