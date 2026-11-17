# Animation bake and ODOL sections

Proving offline that a `model.cfg` animation and a new piece of geometry survived binarization: skeleton bones, `sections[]`, the ODOL section flags, PAA encoding and translation offsets.

> Status: field notes. The build and in-game results below were measured on a mod test car (SUB_BRZ, a sedan with a dashboard map screen) and are mod behaviour, not vanilla; they were not repeated for this file. A citation written with its full `P:\` path was opened on the vanilla data of this repo (a 1.30 build). "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- `SetAnimationPhaseNow` sets a phase and applies it at once (`P:\scripts\3_game\entities\entity.c:22`); on a source whose animation was dropped at build time it does nothing and reports nothing.
- Vanilla ships no loose `model.cfg` next to its vehicle models (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` has none beside it), so the bake has to be read from the binarized model.

## Animations only bake for selections that are skeleton bones

Measured 2026-08-19 on SUB_BRZ; this was the root cause of a grey dashboard screen.

AddonBuilder silently DROPS every model.cfg animation whose `selection` is not declared in the
model's `CfgSkeletons` `skeletonBones[]`: the build exits 0, the anim classes stay in the source
model.cfg, the AnimationSources stay in config.cpp, and `SetAnimationPhaseNow` on their sources
becomes a silent no-op. Measured differential: `gps_marker` was a bone, so its 4 anims
baked into the ODOL; the 28 `nav_w*` windows were in CfgModels `sections[]` but NOT bones, so all
28 `type=hide` anims dropped, the untextured bank could never be hidden, and it rendered as an
opaque grey panel 0.5 to 1.85 mm in front of the real screen. That grey reads as "my texture
apply fails" while the apply is actually landing fine behind it. Two rules: (1) every animated
selection, hide anims included, must be listed in skeletonBones[]; being in `sections[]` is
NOT enough. (2) Verify the bake OFFLINE before deploying: extract the PBO and string-scan the
binarized .p3d for the animation SOURCE names, which are plaintext in the ODOL (e.g.
`re.findall(rb'nav_w\d\d_h', odol)` must yield all 28 distinct names). Zero hits = the animation
does not exist at runtime, whatever model.cfg says. Debugging corollary: the engine grey
fallback is per-SECTION (`texture_index=-1`); when a screen shows uniform grey, check for
coplanar untextured geometry IN FRONT of the selection being textured before blaming the
texture path or the apply call.

## Verify new geometry by its ODOL section, not by strings

Measured 2026-08-19 on the SUB_BRZ dash marker, across seven builds.

Geometry added to a MLOD by tooling can be present in every string table of the binarized
p3d (selection name, material, texture) and still never render, because whether the
engine draws a section is decided by fields the strings do not show:

| Section `special` | Meaning | Renders? |
|---|---|---|
| `0x0002C000` | hidden-selection + opaque pass | yes (all working textured sections) |
| `0x0002C100` | hidden-selection + alpha pass | alpha-dependent, unreliable for tiny quads |
| `0x0000C000` | no hidden-selection bits | **never** |

Two authoring rules follow. (1) A bone-skinned textured selection must ALSO be listed in
`CfgModels.sections[]`, or binarize emits `is_sectional=0 / sections=[]` and there is no
draw call for the bone: being a `skeletonBones` entry is necessary but not sufficient.
(2) The face texture must be a real `.paa` FILE: a procedural `#(argb,...)` face texture
on new geometry produces `0x0000C000`. Procedurals are fine in rvmat stages, not as the
face texture of a section you need drawn.

Gate before every deploy that adds geometry: extract the PBO and parse the ODOL section
table, asserting `is_sectional==1`, non-empty `sections`, and the `0x20000` bit. The LOD
address table is found by chaining (`lod_end[i] == lod_start[i-1]`, max end ≈ file size);
a naive scan for the first plausible table hits a false positive. String-only scans pass
while the geometry is undrawable: five in-game cycles were wasted before this gate existed.

The gate is `skills/dayz-vehicles/scripts/gate_odol_sections.py`: name the selections
with `--selection` and it fails any that is not sectional, owns no section or lacks the `0x20000`
bit. `skills/dayz-vehicles/scripts/check_odol_bone_refs.py` next to it prints the skeleton bone of
each vertex of a section, for the case where the section is drawable but its bone is hidden by an
animation. Both need the same external ODOL parser; `skills/dayz-vehicles/SKILL.md` says how to
point at it.

## PAA files: always encode with ImageToPAA

A hand-rolled PAA whose mip chain runs below 4 px is invalid DXT. The failure mode depends
on the pass: an 8x8 DXT1 `_co` renders as the engine grey fallback, while a `_ca` with
2x2/1x1 mips renders as nothing at all on an alpha section. Encode every texture with
`DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe` from a >=64 px source and let it build the mips.

## Recycle existing faces instead of authoring new ones

Measured 2026-08-21 on SUB_BRZ, over ten builds.

On a ripped vehicle model, faces ADDED by tooling can be perfectly formed and still
never render, while every modification of pre-existing faces shows up reliably. A static
witness quad (no bone, no animation, bright file texture,
section `0x0002C000`, winding/flags/normals identical to neighbouring faces that render, and
nothing occluding it) stayed invisible in-game; a bank-window quad that already existed was
shrunk, retextured and re-UV'd in the same file and rendered immediately. When a model needs a
new visible element, look for geometry already in it that can be repurposed (an unused overlay
quad, a hidden variant, a duplicate panel): you inherit its section, its bone and its proof of
rendering. Reserve authored geometry for models you build from scratch, and if you must add
faces to a ripped model, prove one renders before building anything on top of it.

## Translation offsets: make the memory axis exactly 1 m

For `type="translation"` in model.cfg, `offset0`/`offset1` are documented inconsistently, as metres in some
places and as a fraction of the axis vector in others, and picking
wrong is silent: the selection simply moves somewhere off the model, which reads exactly like
"my geometry does not render". SUB_BRZ lost six build cycles (2026-08-21) to a marker translated with
`offset1 = 1.0` against a 169 mm axis: under the metre reading each phase step threw it half a
metre out of the cabin. Author the memory axis **1.0 m long** in the travel direction and set
`offset1` to the travel in metres (0.169 for 169 mm of sweep). Both readings then produce the
same displacement, so the question never has to be answered. When a hidden/animated selection
is invisible, disconnect its animations and rebuild before blaming geometry or materials: a
detached control build is one cycle and it splits the two causes cleanly.
