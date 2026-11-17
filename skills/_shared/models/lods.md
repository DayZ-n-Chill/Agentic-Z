# LODs

Which LODs a DayZ model carries, the order they sit in, how the visual LODs are numbered, and the rules for the three collision LODs.

A LOD's resolution value is its type. The values for Visual, Geometry, GeoPhys, Memory, LandContact, Roadway, Paths, HitPoints, View Geometry and Fire Geometry are in the Tier 2 table in `_shared/conventions/assets.md`. Use those numbers, never the Arma 3 ones.

## What vanilla carries

A scan of every `.p3d` under `P:\DZ\` read the LOD list at the start of each file. These counts are from the 7,929 models whose list has at least one special LOD.

| LOD (Object Builder name) | Resolution | Models | Example |
|---|---|---|---|
| Visual | `0` to `999` | 7,883 | every model |
| Geometry | `1.0e+13` | 7,830 | `P:\DZ\gear\camping\wooden_case.p3d` |
| View Geometry | `6.0e+15` | 4,765 | `P:\DZ\gear\books\book_kniga.p3d` |
| Fire Geometry | `7.0e+15` | 4,759 | `P:\DZ\gear\books\book_kniga.p3d` |
| Memory | `1.0e+15` | 4,587 | `P:\DZ\gear\camping\wooden_case.p3d` |
| Roadway | `3.0e+15` | 3,119 | `P:\DZ\structures\Residential\HouseBlocks\houseblock_3f_corner1.p3d`, `P:\DZ\gear\camping\fence.p3d` |
| LandContact | `2.0e+15` | 980 | `P:\DZ\gear\camping\wooden_case.p3d` |
| Paths | `4.0e+15` | 260 | `P:\DZ\structures\specific\churches\chapel.p3d` |
| Hit points | `5.0e+15` | 201 | `P:\DZ\vehicles\wheeled\transitbus\transitbus.p3d` |
| GeoPhys (PhysX geometry) | `4.0e+13` | 8 | `P:\DZ\structures\furniture\beds\pillow_grey.p3d`, `P:\DZ\structures\furniture\beds\stretcher_green.p3d` |
| Buoyancy geometry | `2.0e+13` | 1 | `P:\DZ\vehicles\water\boat_01\boat_01.p3d` |

No vanilla model has a ShadowVolume LOD (`10000` to `19999`). Do not add one unless the user asks. When one is asked for, make it slightly smaller than the visual LOD, or the object looks fully shaded; that is format knowledge no vanilla model shows.

Roadway, Paths and Hit points are Bohemia format LODs that script never names: Roadway is the surface characters walk on (vanilla buildings, ruins, rocks and the base building fence carry it), Paths holds the walking routes inside buildings, and Hit points belongs to vehicles and wrecks. A new item never needs them. A walkable building or structure follows the closest vanilla model of the same kind.

What those building LODs hold, read from vanilla: the Paths LOD of `P:\DZ\structures\industrial\garages\garage_small.p3d` stores the points `pos1`, `pos2`, `in1`, `in2`, `actionbegin1` and `actionend1`, and the climbable ladder props carry a Roadway LOD besides their climb points (`P:\DZ\structures\residential\misc\ladder.p3d` and `ladder_half.p3d` beside it), while the decorative `P:\DZ\structures\furniture\various\ladder_a_wood.p3d` has only Geometry and View Geometry. The names and what each is for are in `building-selections.md`.

## Reading the LOD list of a vanilla model

Every model under `P:\DZ\` is binarized (all 8,256 start with the `ODOL` signature). The file opens with that signature, the format version in bytes 4 to 7, the LOD count, then one resolution value per LOD, which is where the counts above come from. Of the 8,256 models, 8,253 are version 56 (for example `P:\DZ\gear\camping\wooden_case.p3d`) and three are still version 54 (`P:\DZ\vehicles\wheeled\offroad_02\proxy\offroad_02_body.p3d` and two wreck proxies under `P:\DZ\structures\wrecks\vehicles\proxy\`). A reader written for one version fails on another, so read the version before choosing a reader; what changed between 54 and 56 is in `dayz-model-pipeline/references/dayz-1-30-model-pipeline.md`.

Tool knowledge, not a vanilla fact: the py3d in `scripts/tools/py3d` classifies a LOD with `classify_lod_resolution`, which accepts a value within 5 % of the canonical one.

## Order

LODs sit in rising resolution order: the visual LODs first, then each special LOD by its value. No vanilla header is out of that order. Object Builder keeps this order when it saves, so the user picks a LOD's type by setting its resolution, never by moving it.

## Visual LODs

- Numbering starts at `1` in most vanilla models and at `0` in the rest (gear: 375 start at `1`, 132 at `0`; structures: 1,607 at `1`, 934 at `0`). Either works. The audit checks the lowest one as LOD0.
- Most vanilla gear has three to five visual LODs (four is the most common, 260 of 519 gear models with a visual LOD). Each next LOD is a simpler mesh of the same object.
- Every visual LOD carries the same named selections: hidden selections (`camoGround` on the wooden case, `P:\DZ\gear\camping\config.cpp:10180`), bones for moving parts and proxies. A selection missing from a lower LOD makes that part vanish or stop moving at a distance.
- The values only have to rise. Some generators space them `0`, `1`, `4`, `8`; vanilla mostly counts `1`, `2`, `3`, `4`. Both load.
- A part that sits inside another, such as liquid in a tray, is rebuilt from each LOD's own simplified container. Built once from the full detail container, it pokes through the simpler walls of the lower LODs. Seen on a mod model, not checked on `P:\` (`dayz-model-pipeline/references/critical-rules.md`, rule 21).

## Common LOD sets

The special LOD sets vanilla uses most, from the same scan.

| Kind | Special LODs | Vanilla example |
|---|---|---|
| Handheld item | Geometry, Memory, View Geometry, Fire Geometry | `P:\DZ\gear\books\book_kniga.p3d` (250 gear models) |
| Gear that also has contact points | the four above plus LandContact | `P:\DZ\gear\camping\wooden_case.p3d`, `canvas.p3d` (185 gear models) |
| Base building part | Geometry, Memory, LandContact, Roadway, View Geometry, Fire Geometry | `P:\DZ\gear\camping\fence.p3d` |
| Building with interiors | Geometry, Memory, Roadway, View Geometry, Fire Geometry, often Paths | `houseblock_3f_corner1.p3d`, `chapel.p3d` |

A mod model always has a visual LOD, Geometry and Memory; `/dayz-p3d-audit` reports a missing one as CRITICAL and a missing View Geometry or Fire Geometry as a NOTE (`dayz-p3d-audit/references/p3d-killers.md` section 4). Some vanilla props have no Memory LOD, but follow the audit for mod models.

## Geometry

The physics body: what players bump into, what items rest on, and where the mass lives.

- Build it from simple closed convex parts. Each part is a named selection `Component01`, `Component02` and so on, with a capital C (`p3d-killers.md` sections 2, 8 and 9). Binarize stores them lower case (`component01` in `wooden_case.p3d`).
- Mass is the sum of the point masses on the Geometry LOD. The audit prints it (`check_geometry_mass` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`). It is not the config `weight`; see `_shared/physics/mass-and-weight.md`.
- Give every face a penetration material, or bullets and footsteps find no surface (`p3d-killers.md` section 10). The wooden case uses `dz\data\data\penetration\wood_desk.rvmat` (string in `wooden_case.p3d`).
- Give walls and floors real thickness. A thin face lets fast bodies pass through (`_shared/physics/drop-and-throw.md`).
- Only this LOD carries mass. Seen on a vehicle mod, not checked on `P:\`: a mass entry on any other LOD, even one where every point mass is `0.0`, makes Binarize bake a centre of mass of zero, and the object spawns underground and is thrown out (`dayz-model-pipeline/references/py3d-assembly-rules.md`).
- A building needs far fewer parts here than in Fire Geometry. Counting the `componentNN` names stored per collision LOD: `P:\DZ\structures\industrial\farms\barn_wood1.p3d` has 564 in one LOD and 73 and 49 in the other two, and `P:\DZ\structures\industrial\garages\garage_small.p3d` has 25, 20 and 16.
- In the MLOD source each face of a component is wound so its cross product points into the component. Measured in game on mod models, not checked on `P:\` (`dayz-p3d-audit/references/p3d-killers.md` section 1, and `dayz-model-pipeline/references/axes-and-winding.md` for the Blender side).

## Fire Geometry

What bullets hit. Same rules as Geometry: closed convex components, named the same way, with penetration materials. Damage zones in `config.cpp` list selection names in `componentNames[]` (`MediumTent` zone `Body`, `P:\DZ\gear\camping\config.cpp:242`), so those names must exist in this LOD. A model can stop players and still let bullets through, so it needs its own check. Thickness counts here too: glass built too thick stops bullets (format knowledge, not shown by a vanilla file).

The penetration materials are vanilla files under `P:\DZ\data\data\penetration\`, a `.rvmat` and nearly always a `.bisurf` of the same name: `metalplate`, `wood`, `wood_desk`, `glass`, `concrete`, `plastic`, `rubber`, `cloth` and about forty more. Write the path as `dz\data\data\penetration\<name>.rvmat`. Arma guides name `CA\Data\Penetration\metal_plate.rvmat`; the DayZ folder is the one above, and it holds no `metal_plate.rvmat`.

## View Geometry

What the action cursor and view checks hit. Without it the player gets no action prompt on the object (`p3d-killers.md` section 4). A building door is found from its View Geometry component (`P:\scripts\3_game\entities\building.c:27` to `:28`), so each door needs its own convex component plus a named selection named after the door here; see `doors.md`.

Two more things read this LOD:

- **Attachment proxies, since 1.30.** A dedicated server reads the position of an inventory attachment proxy from the View Geometry LOD when the proxy is not in the last visual LOD, instead of returning the parent's center. Put a copy of the proxy triangle and its selection here as well as in the visual LODs (`proxies.md`). The fallback is engine code that no script names, so it is not checked on `P:\`.
- **Liquid actions on a well.** The wash, drink and fill actions ask for the View Geometry components of a selection named `liquid_source` (`P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:180`). The selection is optional: see `building-selections.md`.

To prove which LOD a fault is in, probe it from script as `_shared/physics/collision-lods.md` shows.

## Limits (not checked on `P:\`)

Vanilla models are binarized and already inside every limit, so none of these can be read from `P:\`. They are Bohemia format knowledge or measurements on third-party mods; the full accounts are in `dayz-model-pipeline/references/lods-and-geometry.md`.

| Limit | Value | What happens past it |
|---|---|---|
| Vertex normals in one LOD | 32,768 | The game crashes or the LOD is not drawn |
| The drawn LOD0 of a host with its proxies resolved, each proxy counted once per copy | about 32,768 normals and 65,536 vertices | The same, while each part's own `.p3d` looks fine. `/dayz-p3d-audit` prints a model's LOD0 vertex budget |
| LODs in one model, all types together | under about 30 | Binarize can crash |
| Roadway LOD | every face points up; at most about 36 m from the model's origin; at most 255 points when it holds animated parts; no overlap with the Geometry LOD | Characters fall through, a long bridge needs several models, characters wobble |
| Components in one collision LOD | the name allows up to `Component2048`; one large building failed in Binarize far below that | Binarize writes no file and prints no reason. Measured on that building: 28,124 faces and 31.5 million (named selections × points) per collision LOD passed, 32,766 faces and 33.9 million failed |

Three working rules follow from those limits:

- Two LODs must never share a resolution value, and a script that adds LODs must check that the LOD is not there already: run twice, it duplicates them.
- Reduce a visual LOD with Decimate in collapse mode. Planar dissolve does not reduce a curved surface: on one vehicle body it gave more triangles than the LOD above it once the result was triangulated. To keep a grille or a badge intact, protect it with a vertex group.
- When a building's collision goes past what Binarize accepts, move pieces into a second, collision only model placed at the same transform. Do not merge or decimate the pieces to fit.
