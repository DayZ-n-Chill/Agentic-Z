# Three.js viewer pages

Which way to load Three.js in a generated viewer page, what a sandboxed chat frame allows, the fit editor pattern for placing memory points offline, the two defects that lose a user's placement, and how to test a page without a headless browser download. Open it before writing or changing any script that writes a viewer page.

Nothing here is a game fact, so nothing cites `P:\`. The numbers were measured on Three.js and Chrome 151 (no permissive flags), by HTTP probe and headless render, not in the game.

## Loading methods

| Loading method | Works from `file://` (double click) | Highest Three.js version |
|---|---|---|
| UMD `<script src=".../three.min.js">` | Yes | 0.160.1 |
| ES modules with an `importmap` pointing at an https CDN | Yes | 0.185.1 |
| ES modules with an `importmap` pointing at local copies of the module files | No (CORS) | Needs http |

- `build/three.min.js` (UMD) answers HTTP 200 up to 0.160.1 and 404 from 0.161.0. A page on UMD has no upgrade path.
- `examples/js/`, the non module OrbitControls and TransformControls, answers 200 at 0.147.0 and 404 from 0.148.0. That is why older viewers sit at 0.147: it is a hard limit, not a preference.
- ES modules with an importmap against the https CDN work from `file://` with no browser flags. What fails from `file://` is importing local module files, so never bundle a local copy of Three.js to make a page work offline.
- `three.module.js` is no longer one bundle. It re-exports from `three.core.js` (in 0.185.1, 650 KB plus 1.44 MB). Copying only the first gives a silent 404 and a blank page.
- From r160 to r185.1 nothing changed for the API these pages use (raw `BufferGeometry`, `MeshStandardMaterial`, `OrbitControls`, `Raycaster`, `shadowMap`, tone mapping): the same raycast distance, the same `outputColorSpace`, no page errors and no deprecation warnings. The one deprecation nearby is `PCFSoftShadowMap` (r182; use `PCFShadowMap`), which still works.

Write new pages with ES modules, an importmap and the CDN. Drop to UMD only for a measured reason, knowing it caps that page at 0.160.1.

The 3D viewer tool and the viewer scripts of `/dayz-model-tools` already work this way: both take their page scaffold from `viewer_core.py`, which pins Three.js 0.185.1 on jsDelivr. A generated page therefore needs a network to render.

## Pages inside a sandboxed frame

A chat artifact frame blocks `fetch()`, `XMLHttpRequest` and blob URLs from `URL.createObjectURL()`. Module imports from the CDN through the importmap still load, so Three.js itself works there. The embedded mode therefore bakes the geometry into the HTML as `Float32Array` data and the textures as `data:image/png;base64`, and builds the scene from raw `THREE.BufferGeometry` and `THREE.MeshStandardMaterial`, with no GLTFLoader, no fetch and no blob URLs. The web mode is the one that loads a separate `.glb` with `GLTFLoader.load()`.

## The fit editor pattern

Some memory points cannot be tuned in game: crew proxies, `pos_driver` and its `_dir` point, animation axes, cameras. They are baked into the model, so every change costs a rebuild. Set them offline first with a fit editor:

- A Three.js page that loads the first visual LOD of the `.p3d` files, with the geometry embedded as base64 (no fetch).
- One or more jointed mannequins at real scale, posed from the pelvis, each moved by sliders for X, Y, Z and yaw.
- Fixed reference markers, such as the handlebar grips and the get in points.
- A live readout of the coordinates that can be copied.

Several occupants at once, in different colours (driver and co-driver), let you fit them without overlap. The real seated pose comes from the animation; the mannequin is a geometric reference only.

Agentic-Z ships no fit editor script; the list above is the whole pattern. Such a page needs two parts: a builder that turns the `.p3d` into per material groups with a base64 loader, and the page logic for the mannequins, the sliders and the readout.

To check such a page when a headless browser does not fit on disk, parse the embedded JSON payload and run `node --check` on the inline script.

## Two defects that lose the user's placement

Both hit fit editors on a quad bike mod, and each threw away a full placement session. Build both checks before handing a fit editor to a user.

The copyable readout must be rebuilt on every change that matters, and only on those. In the failing page, the function that filled the text box ran at startup, on reset and on a mirror button, but not in the slider handler. The user placed everything, saw it look right on screen, copied the text box, and got the values from load time. Nothing warned them, and the placement was lost because it was never written anywhere. The page printed its timestamp inside that function too, so the stale text carried the time the page was opened and looked fresh. Check it both ways:

- Move a control from code, confirm the text changed and holds the new value, put the control back and confirm the text is identical to before.
- Change a control that must not alter the placement (which mesh is previewed, the camera) and confirm the readout stays the same. A page that rewrites the numbers when the mesh changes has the same bug the other way round.

`THREE.BoxHelper` comes apart from its mesh for two separate reasons that look the same:

- It works in world coordinates. Attached to a transformed holder, it gets that transform a second time. Add it to the scene, not to the holder.
- `update()` reads `object.matrixWorld`, which Three.js recalculates only during `render()`. Calling it right after moving the object uses the previous frame's matrix, so the box lags one step behind while dragging. Call `object.updateMatrixWorld(true)` before `helper.update()`, and send every move and rotation through one function so nothing skips it.

Fixing only the first leaves the page visibly broken.

One check catches both: take the corners the helper actually draws (its `position` attribute transformed by its own `matrixWorld`, so the check does not depend on its parent) and compare them with the mesh's world bounding box. Two negative controls are required: the old code path must give a deviation equal to the distance moved (0.55 m for a 0.55 m move), and attaching the helper to the holder a large one (1.13 m measured).

Expect a small remainder and leave it alone. `BoxHelper` draws the box around the transformed local box, not around the transformed vertices, so at rotations that are not multiples of 90 degrees it is looser than the mesh (5 to 16 mm measured across nine parts). Check that it encloses the mesh, never that it matches.

## Testing a page without Puppeteer

Puppeteer's Chromium download can fill a sandbox disk. Without it, serve the HTML with a static `http.server` and drive it with a browser preview tool. With a preview MCP server the calls are `preview_start`, then `preview_eval` for the page state, the data and the `THREE` objects, `preview_console_logs` at error level, and `preview_screenshot`. That shows the page renders, the console is clean and the state is right.

The screenshot can time out while the animation loop runs; reading the state with `preview_eval` is the reliable check.
