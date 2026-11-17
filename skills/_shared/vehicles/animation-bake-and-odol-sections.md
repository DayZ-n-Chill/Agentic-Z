# Animation bake and ODOL sections

Proving offline that a `model.cfg` animation and a new piece of geometry survived binarization: skeleton bones, `sections[]`, the ODOL section flags, PAA encoding and translation offsets.

> Status: field notes measured on third-party mods, each named in its entry (SUB_BRZ, SUB_WRXSTI, MercedesAMGLF, LFQuad, LFQuad2, LFQuad3, Arma2Quad, LFHeli). Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the `carscript.c` numbers matched this repo's `P:\` (a 1.30 build), the `transport.c` numbers sat 3 to 9 lines lower than written, and the `DZ\vehicles\wheeled\config.cpp` numbers differed. Tags such as SP-205 or LL-244 are the notes' own lesson numbers. Paths such as `<vehicle-import>\...` or `SUB_BRZ_dev\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" all mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number.

## Vanilla anchors checked on `P:\`

- `SetAnimationPhaseNow` sets a phase and applies it at once (`P:\scripts\3_game\entities\entity.c:22`); on a source whose animation was dropped at build time it does nothing and reports nothing.
- Vanilla ships no loose `model.cfg` next to its vehicle models (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` has none beside it), so the bake has to be read from the binarized model.

## Animations only bake for selections that are skeleton bones (added 2026-08-19, SUB_BRZ)

**Animations only bake for selections that are skeletonBones (invariant, added 2026-08-19, SUB_BRZ grey-screen root cause):**
AddonBuilder silently DROPS every model.cfg animation whose `selection` is not declared in the
model's `CfgSkeletons` `skeletonBones[]`: the build exits 0, the anim classes stay in the source
model.cfg, the AnimationSources stay in config.cpp, and `SetAnimationPhaseNow` on their sources
becomes a silent no-op. Measured differential (SUB_BRZ): `gps_marker` was a bone → its 4 anims
baked into the ODOL; the 28 `nav_w*` windows were in CfgModels `sections[]` but NOT bones → all
28 `type=hide` anims dropped, so the untextured bank could never be hidden and rendered as an
opaque grey panel 0.5–1.85 mm in front of the real screen — a grey that reads as "my texture
apply fails" while the apply is actually landing fine behind it. Two rules: (1) every animated
selection — hide anims included — must be listed in skeletonBones[]; being in `sections[]` is
NOT enough. (2) Verify the bake OFFLINE before deploying: extract the PBO and string-scan the
binarized .p3d for the animation SOURCE names, which are plaintext in the ODOL (e.g.
`re.findall(rb'nav_w\d\d_h', odol)` must yield all 28 distinct names). Zero hits = the animation
does not exist at runtime, whatever model.cfg says. Debugging corollary: the engine grey
fallback is per-SECTION (`texture_index=-1`); when a screen shows uniform grey, check for
coplanar untextured geometry IN FRONT of the selection being textured before blaming the
texture path or the apply call.

## Verify new geometry by its ODOL section, not by strings (added 2026-08-19, SUB_BRZ)

**Verify new geometry by its ODOL SECTION, not by strings (invariant, added 2026-08-19, SUB_BRZ marker hunt):**
Geometry added to a MLOD by tooling can be present in every string table of the binarized
p3d — selection name, material, texture — and still never render, because whether the
engine draws a section is decided by fields the strings do not show. Measured on the
SUB_BRZ dash marker across seven builds:

| Section `special` | Meaning | Renders? |
|---|---|---|
| `0x0002C000` | hidden-selection + opaque pass | yes (all working textured sections) |
| `0x0002C100` | hidden-selection + alpha pass | alpha-dependent, unreliable for tiny quads |
| `0x0000C000` | no hidden-selection bits | **never** |

Two authoring rules follow. (1) A bone-skinned textured selection must ALSO be listed in
`CfgModels.sections[]`, or binarize emits `is_sectional=0 / sections=[]` and there is no
draw call for the bone — being a `skeletonBones` entry is necessary but not sufficient.
(2) The face texture must be a real `.paa` FILE: a procedural `#(argb,...)` face texture
on new geometry produces `0x0000C000`. Procedurals are fine in rvmat stages, not as the
face texture of a section you need drawn.

Gate before every deploy that adds geometry: extract the PBO and parse the ODOL section
table, asserting `is_sectional==1`, non-empty `sections`, and the `0x20000` bit. The LOD
address table is found by chaining (`lod_end[i] == lod_start[i-1]`, max end ≈ file size);
a naive scan for the first plausible table hits a false positive. Reference implementation:
`<vehicle-import>\work\navscreen_planb\gate_sections.py` (built on an external ODOL→MLOD converter's
`odol_reader`). String-only scans pass while the geometry is undrawable — that gate cost
five wasted in-game cycles before it existed.

In this repo the gate is `skills/dayz-vehicles/scripts/gate_odol_sections.py`: name the selections
with `--selection` and it fails any that is not sectional, owns no section or lacks the `0x20000`
bit. `skills/dayz-vehicles/scripts/check_odol_bone_refs.py` next to it prints the skeleton bone of
each vertex of a section, for the case where the section is drawable but its bone is hidden by an
animation. Both need the same external ODOL parser; `skills/dayz-vehicles/SKILL.md` says how to
point at it.

## PAA files: always encode with ImageToPAA (added 2026-08-19)

**PAA files: always encode with ImageToPAA (added 2026-08-19):**
A hand-rolled PAA whose mip chain runs below 4 px is invalid DXT. The failure mode depends
on the pass: an 8x8 DXT1 `_co` renders as the engine grey fallback, while a `_ca` with
2x2/1x1 mips renders as nothing at all on an alpha section. Encode every texture with
`DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe` from a >=64 px source and let it build the mips.

## Recycle existing faces instead of authoring new ones (added 2026-08-21, SUB_BRZ)

**Recycle existing faces instead of authoring new ones (invariant, added 2026-08-21, SUB_BRZ marker):**
On an imported/ripped vehicle model, faces ADDED by tooling can be perfectly formed and still
never render, while every modification of pre-existing faces shows up reliably. Measured over
ten builds on SUB_BRZ: a static witness quad — no bone, no animation, bright file texture,
section `0x0002C000`, winding/flags/normals identical to neighbouring faces that render, and
nothing occluding it — stayed invisible in-game; a bank-window quad that already existed was
shrunk, retextured and re-UV'd in the same file and rendered immediately. When a model needs a
new visible element, look for geometry already in it that can be repurposed (an unused overlay
quad, a hidden variant, a duplicate panel): you inherit its section, its bone and its proof of
rendering. Reserve authored geometry for models you build from scratch, and if you must add
faces to an imported model, prove one renders before building anything on top of it.

## Translation offsets: make the memory axis exactly 1 m (added 2026-08-21)

**Translation offsets: make the memory axis exactly 1 m and the ambiguity disappears (added 2026-08-21):**
For `type="translation"` in model.cfg, `offset0`/`offset1` are documented inconsistently: they
behave as metres in some sources and as a fraction of the axis vector in others, and picking
wrong is silent — the selection simply moves somewhere off the model, which reads exactly like
"my geometry does not render". SUB_BRZ lost six build cycles to a marker translated with
`offset1 = 1.0` against a 169 mm axis: under the metre reading each phase step threw it half a
metre out of the cabin. Author the memory axis **1.0 m long** in the travel direction and set
`offset1` to the travel in metres (0.169 for 169 mm of sweep). Both readings then produce the
same displacement, so the question never has to be answered. When a hidden/animated selection
is invisible, disconnect its animations and rebuild before blaming geometry or materials — a
detached control build is one cycle and it splits the two causes cleanly.
