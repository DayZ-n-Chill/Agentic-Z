# Animation bake and ODOL sections

How to prove offline that a `model.cfg` animation and a new piece of geometry survived binarization: skeleton bones, `sections[]`, the ODOL section flags, PAA encoding and translation offsets.

The build and in-game results here were measured on a test car with a dashboard map screen; they are mod behaviour, not vanilla. The ODOL scripts named below belong to `/dayz-p3d-audit`, which says how to point them at the external ODOL parser.

## What vanilla shows

- `SetAnimationPhaseNow` sets a phase and applies it at once (`P:\scripts\3_game\entities\entity.c:22`). On a source whose animation was dropped at build time it does nothing and reports nothing.
- Vanilla ships no loose `model.cfg` next to its vehicle models (none sits beside `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`), so the bake has to be read from the binarized model.

## Only skeleton bones get animated

AddonBuilder drops every `model.cfg` animation whose `selection` is not in the model's `CfgSkeletons` `skeletonBones[]`. The build still exits 0, the animation classes stay in the source `model.cfg`, the `AnimationSources` stay in `config.cpp`, and `SetAnimationPhaseNow` on their sources does nothing.

On the test car, `gps_marker` was a bone, so its four animations baked. The 28 `nav_w*` windows were in `CfgModels` `sections[]` but were not bones, so all 28 `type=hide` animations were dropped. The untextured bank could never be hidden, and it drew as an opaque grey panel 0.5 to 1.85 mm in front of the real screen. That grey looks like a failed texture apply while the apply is landing fine behind it.

- List every animated selection in `skeletonBones[]`, hide animations included. Being in `sections[]` is not enough.
- Check the bake before you deploy: extract the PBO and search the binarized `.p3d` for the animation source names, which are plain text in the ODOL. For the screen above, `re.findall(rb'nav_w\d\d_h', odol)` has to return all 28 names. No hits means the animation does not exist at runtime, whatever `model.cfg` says.
- The engine's grey fallback is per section (`texture_index=-1`). When a screen shows flat grey, look for coplanar untextured geometry in front of the selection before you blame the texture path or the apply call.

## Check new geometry by its ODOL section

Geometry a tool adds to an MLOD can appear in every string table of the binarized model (selection name, material, texture) and still never draw. Whether the engine draws a section is decided by fields the strings do not show:

| Section `special` | Meaning | Draws |
|---|---|---|
| `0x0002C000` | Hidden selection, opaque pass | Yes; every working textured section |
| `0x0002C100` | Hidden selection, alpha pass | Depends on alpha; unreliable for tiny quads |
| `0x0000C000` | No hidden selection bits | Never |

- A bone skinned textured selection must also be in `CfgModels` `sections[]`. Otherwise binarize writes `is_sectional=0` and `sections=[]`, and the bone gets no draw call. Being in `skeletonBones[]` is needed but not enough.
- Give the face a real `.paa` file. A procedural `#(argb,...)` face texture on new geometry produces `0x0000C000`. Procedurals are fine in `.rvmat` stages, not as the face texture of a section that has to draw.

Before every deploy that adds geometry, extract the PBO and parse the ODOL section table: `is_sectional==1`, `sections` not empty, and the `0x20000` bit set. Find the LOD address table by chaining (`lod_end[i] == lod_start[i-1]`, the largest end close to the file size); taking the first table that looks right gives a false match. A string search passes even when the geometry cannot draw.

`skills/dayz-p3d-audit/scripts/gate_odol_sections.py` runs that check: name the selections with `--selection` and it fails any that is not sectional, owns no section or lacks the `0x20000` bit. `check_odol_bone_refs.py` next to it prints the skeleton bone of each vertex in a section, for when the section can draw but an animation hides its bone.

## Encode every PAA with ImageToPAA

A hand made PAA whose mip chain goes below 4 px is invalid DXT. What you see depends on the pass: an 8x8 DXT1 `_co` draws as the engine's grey fallback, and a `_ca` with 2x2 and 1x1 mips draws nothing at all on an alpha section. Encode every texture with `DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe` from a source of 64 px or more, and let it build the mips.

## Reuse faces on a ripped model

On a ripped model, faces a tool adds can be well formed and still never draw, while changes to faces that already exist show up every time. On the test car, a static quad with no bone and no animation, a bright file texture, section `0x0002C000`, and winding, flags and normals matching faces that draw, stayed invisible with nothing in front of it. An existing bank window quad, shrunk, retextured and given new UVs in the same file, drew at once.

When a ripped model needs a new visible element, repurpose geometry it already has: an unused overlay quad, a hidden variant, a duplicate panel. You inherit its section, its bone and the fact that it draws. Keep new faces for models you build from scratch. If you must add faces to a ripped model, prove one draws before you build on it.

## Make a translation axis exactly 1 m

For `type="translation"` in `model.cfg`, `offset0` and `offset1` are described both as metres and as a fraction of the axis vector, and the wrong guess fails silently: the selection moves off the model, which looks like geometry that does not draw. A marker with `offset1 = 1.0` on a 169 mm axis, read as metres, moved half a metre out of the cabin on each phase step.

Draw the memory axis exactly 1.0 m long in the direction of travel, and set `offset1` to the travel in metres (`0.169` for 169 mm). Both readings then give the same movement.

When an animated or hidden selection is invisible, remove its animations and rebuild before you blame geometry or materials. That control build takes one cycle and separates the two causes.
