# Classification viewer

How to review and change the session A classification of a ripped car without opening Blender: what the viewer needs, the steps per car and the data it expects in the GLB.

The viewer is `classify-viewer\index.html` in this skill's folder, a Three.js (r128 UMD) page over the GLB export of a session A scene. It is advisory and it captures deltas. Authority stays with the `.blend`, then `blender_export_asset_contract.py`, then the ledger entry. The deltas are applied to the `.blend` by a headless script (the `fix_roofvent` pattern of the import project), never by hand.

Nothing here is a fact about the vanilla game. The script runs inside Blender and the page runs in a browser; neither needs `P:\` or DayZ Tools. The viewer's behaviour was measured by the author and is not yet checked on `P:\`.

## Three.js is not shipped

The page loads three files from a `lib\` subfolder next to `index.html`: `three.min.js`, `GLTFLoader.js` and `OrbitControls.js`, all from Three.js r128 (UMD build, MIT licence, about 726 KB). They are not in this repo. Download them from <https://github.com/mrdoob/three.js/tree/r128/build> (`three.min.js`) and from `examples/js/loaders/GLTFLoader.js` and `examples/js/controls/OrbitControls.js` of the same tag.

Use the r128 UMD files, not the ESM ones. `index.html` loads them with `<script src=...>`, and the `importmap` that ESM builds need fails from `file://` in many Chrome versions.

## Steps per car

1. Export the GLB. This does not touch the `.blend`:

   ```cmd
   blender --background --python-exit-code 1 --python "<skill-dir>\export_car_glb.py" -- --blend <sessionA.blend> --out <dir>\car.glb
   ```

   The script prints `GLB_DONE mode=<full|minimal> bytes=<n>` when it finishes. `minimal` means this Blender version rejected the full option set and the export fell back to the GLB format with extras only.
2. Copy `index.html` and `lib\` next to `car.glb`, or write the GLB into the viewer folder.
3. Serve the folder over http. The page cannot fetch the GLB from `file://`. Any static server works, for example `python -m http.server <port> --directory <dir>`; in Claude Code that is an entry in `.claude\launch.json` started with `preview_start`.
4. The human clicks a part and sets it to INCLUDE, MOVABLE or EXCLUDE; EXCLUDE takes a reason. The changes live in `window.DZ_DELTAS` as `{stem: {from, to, reason}}`. The agent reads them with a browser JavaScript tool (`javascript_tool` in Claude Code), or the human presses "Copy changes (JSON)".
5. Apply the deltas to the `.blend` headless: move the objects whose `source_id` equals the stem or starts with `stem__obj`, and update `dz_exclude_reason` and `dz_responsible`. Check the result again, then follow the normal lane: export, `import-blender`, `check`.

The page title and heading still carry the name of the first car it was used on (`sub_wrxsti_04`); edit both lines of `index.html` for another car.

## Data the GLB must carry

Each node carries these extras, which the page reads from `userData`:

| Extra | Meaning | Who sets it |
|---|---|---|
| `source_id` | Stable part id; sub-objects are `stem__objNN`. Nodes without it are ignored. | A custom property already on the object in the session A `.blend`. |
| `dz_coll` | `DZ_INCLUDE`, `DZ_EXCLUDE` or `DZ_MOVABLE`, from the collection the object is in. | `export_car_glb.py`, in memory only. |
| `dz_reason` | The exclusion reason, copied from `dz_exclude_reason`. | `export_car_glb.py`, in memory only. |
| `dz_review` | Marks a part for review; the list shows a star. | A custom property already on the object. |
| `dz_movable_group` | The movable group of the part; the list shows it in brackets. | A custom property already on the object. |

Parts with no mesh (EMPTY placeholders) appear in the list as "(no geometry)". The export unhides every collection and writes no materials; the page gives each part its own material so it can tint it by class.

## First real use

sub_wrxsti_04 on 2026-08-06: 128 parts in a 24.7 MB GLB, verified with a round trip of the deltas and no console errors.
