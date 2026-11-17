# Building Three.js viewers for DayZ models

Which way to load Three.js in a generated viewer page, what a sandboxed chat frame allows, the "fit editor" pattern for placing memory points offline, the two defects that lose a user's placement, and how to test a viewer page without a headless browser download. Open it when writing or changing any script that emits a viewer page, not only this skill's.

Nothing here is a fact about the game, so nothing is cited to `P:\`. The measurements are the source author's, reported with the imported knowledge pack; each names its date and the mod it was made on.

## Three.js loading lanes

Measured on 2026-09-01 by HTTP probe and headless render (Chrome 151, no permissive flags). These are facts about the library, and they apply to every viewer a DayZ skill emits.

| Loading lane | Works from `file://` (double click) | Highest three version |
|---|---|---|
| UMD `<script src=".../three.min.js">` | yes | 0.160.0 |
| ESM with an `importmap` pointing at an https CDN | yes | 0.185.1 (the latest then) |
| ESM with an `importmap` pointing at local vendored files | no (CORS) | http only |

- `build/three.min.js` (UMD) answers HTTP 200 up to 0.160.0 and 404 from 0.161.0. A viewer on the UMD lane has no upgrade path: it is a dead branch, not just an old version.
- `examples/js/` (the non-module OrbitControls and TransformControls) answers 200 at 0.147.0 and 404 from 0.148.0. That is why legacy viewers sit at 0.147: a hard limit, not a preference.
- ESM with an importmap against the https CDN works from `file://` with no browser flags. Notes that say otherwise are wrong. What fails from `file://` is importing local module files. Do not vendor three to make a viewer work offline: vendored modules need http.
- `three.module.js` is no longer one bundle. It re-exports from `three.core.js` (in 0.185.1: 650 KB plus 1.44 MB). Vendoring only the first gives a silent 404 and a blank page.
- Going from r160 to r185.1 changed nothing for the API this tool uses (raw `BufferGeometry`, `MeshStandardMaterial`, `OrbitControls`, `Raycaster`, `shadowMap`, tone mapping): the same raycast distance, the same `outputColorSpace`, no page errors and no deprecation warnings. The one deprecation nearby is `PCFSoftShadowMap` (r182; use `PCFShadowMap`), which still works.

Emit new viewers on the ESM, importmap and CDN lane. Drop to UMD only for a measured reason, knowing it caps that viewer at 0.160.0 for good.

The viewer tool and `/dayz-proxy-align` are on that lane already: both take their page scaffold from `viewer_core.py`, which pins three 0.185.1 on jsDelivr. A generated page therefore needs a network to render.

## Embedded pages in a sandboxed frame

A chat artifact frame blocks every network request the page makes itself: `fetch()`, `XMLHttpRequest` and `URL.createObjectURL()`. The embedded mode therefore bakes the geometry into the HTML as `Float32Array` data and the textures as `data:image/png;base64`, and builds the scene from raw `THREE.BufferGeometry` and `THREE.MeshStandardMaterial`. It uses no GLTFLoader, no fetch and no blob URLs. The web mode is the one that loads a separate `.glb` with `GLTFLoader.load()`.

## The fit editor pattern

Some memory points cannot be tuned in game: crew proxies, `pos_driver` and its `_dir` point, animation axes, cameras. They are baked into the model, so every change costs a rebuild. Set them offline first with a "fit editor":

- A Three.js page that loads the first visual LOD of the `.p3d` files, with the geometry embedded as base64 (no fetch).
- One or more jointed mannequins at real scale, posed locally from the pelvis, each moved by sliders for X, Y, Z and yaw.
- Fixed reference markers, such as the handlebar grips and the get-in points.
- A live readout of the coordinates that can be copied.

Several occupants at once (driver and co-driver, in different colors) let you fit them without overlap. The real seated pose comes from the animation; the mannequin is a geometric reference only.

The source names two scripts as its reference implementation, `build_viewer3.py` (p3d to per-material groups and a base64 loader) and `build_viewer4.py` (the rider builder, the sliders and the readout). Neither came with the imported pack; the description above is what there is.

To check such a page when a headless browser will not fit on disk: parse the embedded JSON payload, and run `node --check` on the inline script.

## Two defects that lose the user's placement

Both hit the fit editor pattern, both were shipped, and each cost a whole placement session on the LFQuad3 mod (2026-09-08 and 09). Build both checks before handing a fit editor to a user.

**1. The copyable readout must be rebuilt on every change that matters, and only on those.**

The shipped defect: the function that fills the text box ran at startup, on reset and on a mirror button, but not in the slider handler. The user placed everything, saw it look right on screen, copied the text box, and got the values from load time. Nothing warned them, and the placement could not be recovered because it was never written anywhere. Worse, the timestamp was printed inside that function, so the stale text carried the time the page was opened and read as fresh.

Check it in both directions:

- Move a control from code, confirm the text changed and holds the new value, put the control back and confirm the text is identical to before.
- Change a control that must not alter the placement (which mesh is previewed, the camera) and confirm the readout stays the same. This direction is not optional: a viewer that rewrites the numbers when the mesh changes has the same bug with the sign reversed.

**2. `THREE.BoxHelper` comes apart from its mesh for two separate reasons that look the same.**

- It works in world coordinates. Attached to a transformed holder, it gets that transform a second time. It belongs in the scene.
- `update()` reads `object.matrixWorld`, which three recalculates only during `render()`. Calling it right after moving the object uses the matrix of the previous frame, so the box stays one step behind; the visible symptom is a box that lags while dragging. Call `object.updateMatrixWorld(true)` before `helper.update()`, and send every move and every rotation through one function so nothing can skip it.

Fixing only the first leaves the viewer visibly broken all the same, which is how it shipped the first time.

One check catches both: take the corners the helper actually draws (its `position` attribute transformed by its own `matrixWorld`, so the check does not depend on its parent) and compare them with the mesh's world bounding box. Two negative controls are required: the old code path must give a deviation equal to the distance moved (0.55 m measured for a 0.55 m move), and attaching the helper to the holder a large one (1.13 m measured).

Expect a remainder that is not zero, and do not chase it: `BoxHelper` draws the box around the transformed local box, not around the transformed vertices, so at rotations that are not multiples of 90 degrees it is legitimately looser than the mesh (5 to 16 mm measured across nine parts). Check that it encloses the mesh, never that it matches.

## Testing a viewer page without Puppeteer

Puppeteer's Chromium download can fill a sandbox disk. Without it: serve the HTML with a static `http.server` and drive it with a browser preview tool. The source used the preview MCP: `preview_start`, then `preview_eval` for the page state, the data and the `THREE` objects, `preview_console_logs` at error level, and `preview_screenshot`. That shows the page renders, the console is clean and the state is right, with no Chromium download.

The screenshot can time out while the animation loop runs; reading the state with `preview_eval` is the reliable check. First used on the LFQuad mod's wheel well tuner, 2026-06-01.
