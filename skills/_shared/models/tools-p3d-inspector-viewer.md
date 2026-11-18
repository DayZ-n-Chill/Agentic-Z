# Inspector page

What the HTML page from `p3d_inspector_viewer.py` shows, how to work in it, and which build choices must stay when the script changes. How to run the three inspector scripts is in `tools-p3d-inspector.md`.

This is tool behaviour, not game fact. Of the point names the page colours, only `ce_center`, `box_placing_min`, `box_placing_max` and the `_axis` names are vanilla (`memory-points.md`); vanilla script reads `ce_center` at `P:\scripts\3_game\entities\object.c:1363`. `pos center`, `actionPos`, `port_*` and `cable_*` are mod conventions.

## Layers

Each layer has a toolbar toggle. The seven wireframe LOD layers start hidden.

| Layer | Shows |
|---|---|
| Visual | The model, flat shaded, no textures |
| Geometry | Green wireframe of the collision LOD |
| Fire Geo | Red wireframe of the bullet collision LOD |
| View Geo | Blue wireframe of the sight and action cursor LOD |
| LandContact | Yellow green wireframe of the ground contact points |
| Roadway | Cyan wireframe of the walkable surfaces |
| Paths | Magenta wireframe of the AI paths |
| HitPoints | Orange wireframe of the hit points |
| Memory Pts | A coloured sphere at each memory point |
| Axes | Purple arrows along the animation axes |
| Bounds | The bounding box in cyan and the `box_placing` box in orange |
| Labels | Floating names on memory points and axes |
| Grid | A reference grid |
| Wireframe | A wireframe over the visual mesh |
| Export Recipe | Opens a box with the edited Recipe JSON |

## Point colours

| Kind | Colour | Points |
|---|---|---|
| Center | Cyan | `ce_center` (vanilla), `pos center` (mod convention) |
| Interaction | Red | `actionPos` (mod convention) and other action points |
| Axis | Purple | The two ends of an animation axis |
| Placing | Orange | `box_placing_min`, `box_placing_max` |
| Port | Deep orange | `port_*`, `cable_*`, the port points of power grid mods (not vanilla) |
| Proxy | Gray | Proxy attachment points |
| Other | Light gray | Everything else |

## Side panels

- Points: every memory point with live coordinates. Click one to fly the camera to it.
- LODs: each LOD with its point count, face count and selections.
- Selections: every named selection in every LOD.
- Paths: the texture and material paths the model names, with a warning on `P:\` paths. It is a hint only; `/dayz-p3d-audit` does the real path check.

## Working in the page

| Action | How |
|---|---|
| Orbit | Drag with the left button on empty space |
| Pan | Drag with the right button |
| Zoom | Mouse wheel |
| Select a point | Click its sphere; a panel shows its coordinates |
| Move a point | Click its sphere and drag; it moves in the plane facing the camera |
| Snap to the grid | Hold Shift while dragging |
| Grid size | `1` for 1 cm, `2` for 5 cm |
| Focus | Click a point in the Points panel |
| Export | Press Export Recipe, then Select All and Ctrl+C in the box |

The export holds `meta`, `memory_points`, `axes` and `bbox` only. Copy `memory_points` and `axes` into the extracted Recipe before building.

While a point is dragged, everything tied to it updates live: the sphere, its label, the axis line and arrow when it is an axis end, the placing box when it is `box_placing_min` or `box_placing_max`, both coordinate panels and the Recipe held in memory. A floating readout shows X, Y and Z, plus the snap size while Shift is held.

## Build choices to keep

- Three.js 0.185.1, loaded as ES modules through an importmap from jsDelivr. The scene setup (importmap, OrbitControls import, renderer, camera, controls, grid, resize handling, render loop) comes from `viewer_core.py`, the scaffold the 3D viewer and the proxy editor of `/dayz-model-tools` share. The script looks for it in `scripts/tools/dayz-3d-viewer` first, then in `_shared`, and refuses a copy with another contract or Three.js version. Change the Three.js version there, never in this script.
- If the page opened from disk shows no canvas, Chrome on Windows has blocked a module request from the `file://` page (`net::ERR_BLOCKED_BY_ORB`), which stops the script without a message. Serve the folder (`python -m http.server`) and open the page over `http://localhost`. Which loading methods work from `file://` is in `tools-threejs-viewers.md`.
- Labels are HTML elements placed with `Vector3.project()`, not a CSS2DRenderer.
- Bounding boxes are hand built line segments, not a Box3Helper.
- Every material is a MeshStandardMaterial, so a selected object can glow through its emissive colour.
- Buffers use `BufferAttribute` with an explicit `Float32Array`.
- Hovering a sphere turns orbit control off before the button goes down, so the press starts a drag instead of an orbit; moving off the sphere turns it back on. The drag starts once the pointer has moved more than 5 pixels, runs on a plane through the point that faces the camera, and ends on release.
- Export uses a text box, because the clipboard API is blocked for a page opened from disk.

## Testing visibility: sample the area, not the centroid

To decide whether a selection can be seen from outside, cast rays from random points spread over each face (about 3,000 per LOD) and report the share of free area. One ray from each centroid gives a false answer on thin faces. Measured on a heater model: centroid rays reported all 48 faces blocked in all six directions, while area sampling showed 84 to 86 % free, because every face was a long thin triangle whose centroid sat behind a 1 to 2 mm wire. That false reading points at the model when the fault is in the config.
