# Classification viewer

How to review and change which parts of a ripped car are kept, dropped or movable without opening Blender: what the viewer needs, the steps per car, and the data the GLB must carry.

The viewer is `classify-viewer\index.html` in the scripts folder of `/dayz-model-tools` (`skills/dayz-model-tools/scripts/`), a Three.js r128 page over a GLB export of the car's classification scene. It only advises and collects changes; the `.blend` file stays the source of truth, and a headless script applies the changes to it, never a hand edit. It runs in Blender and a browser and needs neither `P:\` nor DayZ Tools; nothing in it is a fact about the game.

## Three.js is not shipped

The page loads three files from a `lib\` folder next to `index.html`: `three.min.js`, `GLTFLoader.js` and `OrbitControls.js`, all from Three.js r128 (about 726 KB). They are not in this repo. Take them from version 0.128.0 of the `three` npm package: `build/three.min.js`, `examples/js/loaders/GLTFLoader.js` and `examples/js/controls/OrbitControls.js`.

Use the UMD files, not the ES module ones. `index.html` loads them with `<script src=...>`, and the `importmap` that module builds need fails from `file://` in many Chrome versions.

## Steps per car

1. Export the GLB; this does not change the `.blend`:

   ```cmd
   blender --background --python-exit-code 1 --python "skills\dayz-model-tools\scripts\export_car_glb.py" -- --blend <car.blend> --out <dir>\car.glb
   ```

   The script prints `GLB_DONE mode=full bytes=<n>` when done. If this Blender version refuses the full option set, the line reads `GLB_DONE mode=minimal (<error>) bytes=<n>` and the export fell back to the exporter's default options with extras on, so materials are included.
2. Copy `index.html` and `lib\` next to `car.glb`, or write the GLB into the viewer folder.
3. Serve the folder over http; the page cannot fetch the GLB from `file://`. Any static server works, such as `py -m http.server <port> --directory <dir>`.
4. The user clicks a part and sets it to INCLUDE, MOVABLE or EXCLUDE; EXCLUDE asks for a reason. The changes live in `window.DZ_DELTAS` as `{stem: {from, to, reason}}`. Read them with a browser script tool, or the user presses "Copy changes (JSON)".
5. Apply the changes to the `.blend` headless: move the objects whose `source_id` equals the stem or starts with `stem__obj`, and update `dz_exclude_reason` and `dz_responsible`. Check the result, then carry on with export and the import checks.

The page title and heading still carry the name of the first car it was used on; edit both lines of `index.html` for another car.

## Data the GLB must carry

The page reads these node extras from `userData`:

| Extra | Meaning | Set by |
|---|---|---|
| `source_id` | Stable part id; sub-objects are `stem__objNN`. Nodes without it are ignored. | A custom property already on the object in the `.blend` |
| `dz_coll` | `DZ_INCLUDE`, `DZ_EXCLUDE` or `DZ_MOVABLE`, from the object's collection | `export_car_glb.py`, in memory only |
| `dz_reason` | The exclusion reason, copied from `dz_exclude_reason` | `export_car_glb.py`, in memory only |
| `dz_review` | Marks a part for review; the list shows a star | A custom property already on the object |
| `dz_movable_group` | The part's movable group, shown in brackets | A custom property already on the object |

Parts with no mesh appear as "(no geometry)". The export unhides every collection, and the full export writes no materials; the page gives each part its own material so it can tint it by class.

Tested on one car: 128 parts in a 24.7 MB GLB, with the changes read back intact and no console errors.
