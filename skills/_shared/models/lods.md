# LODs

Which LODs a DayZ model carries, the order they sit in, how the visual LODs are numbered, and the rules for the three collision LODs.

A LOD's resolution value is its type. The values for Visual, Geometry, Memory, LandContact, View Geometry and Fire Geometry are in the Tier 2 table in `_shared/conventions/assets.md`. Use those numbers, never the Arma 3 ones.

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

No vanilla model has a ShadowVolume LOD (`10000` to `19999`). Do not add one unless the user asks.

Roadway, Paths and Hit points are Bohemia format LODs that script never names: Roadway is the surface characters walk on (vanilla buildings, ruins, rocks and the base building fence carry it), Paths holds the walking routes inside buildings, and Hit points belongs to vehicles and wrecks. A new item never needs them. A walkable building or structure follows the closest vanilla model of the same kind.

## Order

LODs sit in rising resolution order: the visual LODs first, then each special LOD by its value. No vanilla header is out of that order. Object Builder keeps this order when it saves, so the user picks a LOD's type by setting its resolution, never by moving it.

## Visual LODs

- Numbering starts at `1` in most vanilla models and at `0` in the rest (gear: 375 start at `1`, 132 at `0`; structures: 1,607 at `1`, 934 at `0`). Either works. The audit checks the lowest one as LOD0.
- Most vanilla gear has three to five visual LODs (four is the most common, 260 of 519 gear models with a visual LOD). Each next LOD is a simpler mesh of the same object.
- Every visual LOD carries the same named selections: hidden selections (`camoGround` on the wooden case, `P:\DZ\gear\camping\config.cpp:10180`), bones for moving parts and proxies. A selection missing from a lower LOD makes that part vanish or stop moving at a distance.

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

## Fire Geometry

What bullets hit. Same rules as Geometry: closed convex components, named the same way, with penetration materials. Damage zones in `config.cpp` list selection names in `componentNames[]` (`MediumTent` zone `Body`, `P:\DZ\gear\camping\config.cpp:242`), so those names must exist in this LOD. A model can stop players and still let bullets through, so it needs its own check.

## View Geometry

What the action cursor and view checks hit. Without it the player gets no action prompt on the object (`p3d-killers.md` section 4). A building door is found from its View Geometry component (`P:\scripts\3_game\entities\building.c:27` to `:28`), so each door needs its own convex component plus a named selection named after the door here; see `doors.md`.

To prove which LOD a fault is in, probe it from script as `_shared/physics/collision-lods.md` shows.
