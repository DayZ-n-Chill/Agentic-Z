# Selections and proxies when you author a model

Which LODs each named selection of a new model must sit in, how the three parts of a proxy make an attachment show, and the memory point names a power grid mod uses for its cable ports.

The vanilla side of each topic is in `memory-points.md`, `selections.md`, `building-selections.md`, `proxies.md` and `proxy-frames.md`; this file is the authoring checklist. Lines that cite `P:\` are checked there. The Object Builder and Blender steps are tool knowledge, the proxy findings marked as measured come from in game tests on mod items, and the port names are the power grid mod's own, not vanilla.

## Where a named selection must be

A named selection is a set of the points and faces of one LOD. Who reads each kind is in `selections.md`. For an animated part, such as a lever:

| LOD | Needed | Why |
|---|---|---|
| Resolution LODs | yes | The visible mesh moves |
| Geometry | yes | Collision follows the part |
| Fire Geometry | yes | Bullets hit the part where it is |
| View Geometry | yes | Sight blocking and the action cursor follow the part |
| Memory | yes | The axis points |
| Shadow volume | when the model has one | The shadow follows the part |

Give the selection the same name in every LOD it is in. Matching ignores letter case (the barrel model stores `lid` and its config says `class Lid`, `P:\DZ\gear\containers\config.cpp:101`), but spell a name the way the config or script that uses it does.

A collision LOD needs the selection only where its collision should move with the part. A fixed collision box under a moving lever does not.

## Common selection names

| Name | Use |
|---|---|
| `door1`, `door2` | A moving door on a mod's own object. Vanilla buildings use `doors1`, `doors2` (below) |
| `lever`, `switch` | Moving mechanical parts |
| `Component01`, `Component02` | Pieces of the Geometry, Fire Geometry and View Geometry LODs |
| `camo` | A texture swap, listed in `hiddenSelections[]` |
| `zbytek` | Czech for "the rest": everything in no other selection |
| `liquid_source` | Since 1.30, the View Geometry component that the liquid actions of a well or pump look for, `LIQUID_SOURCE_SELECTION` (`P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:180`); see `dayz-1-30-models.md` |

## Doors and ladders on a building

Vanilla buildings name their parts this way (read from vanilla models such as `garage_small`, `barn_wood1`, `farm_cowsheda` and six ladders converted back to MLOD; the full account with the file each name comes from is `building-selections.md`):

- Doors. The selection is `doorsN`, plural (`doors1`, `doors2`), not `door1`. The Memory LOD holds `doorsN_axis` (the hinge) and `doorsN_action` (the action point). Twin doors are `doorstwinN` with `twinN_action`. Put `doorsN` in every LOD that matters: visual, Geometry, Memory, View Geometry, Fire Geometry and Hit points. The Geometry LOD carries the named properties `class=house`, `map=building` and `damage=no`.
- A ladder that is a loose prop (`ladder.p3d`) has the Memory points `start` and `end` (or `start1` and `end1`) and a Roadway LOD under it.
- A ladder built into a building (lighthouse, watchtower, silo) has `ladderN` (its base, also a View Geometry component) and the Memory points `ladderN_bottom_front`, `ladderN_top_front`, `ladderN_middle_X` (with `_align`, for floors in between), `ladderN_con`, `ladderN_con_dir` and `ladderN_dir`, plus a Roadway.
- The Paths LOD for AI holds `posXX` (stop points, usable by `buildingpos`), `inXX` (entries) and `actionbeginN` with `actionendN`.

## In Blender

Named selections are vertex groups. Create each group with the exact name and assign its vertices with weight 1.0; the Arma 3 Object Builder add-on writes vertex groups as named selections. A vertex can sit in several groups, for example `Component01` and `lever`.

## Device selections of a power grid mod

Names one power grid mod uses on its devices (its own convention): `cable_attach_point` where cables connect, `status_indicator` for an LED that changes with the power state, `switch_handle` for the switch, and `panel_door` for an opening cover.

## Proxies: the three parts

A proxy tells the engine where to draw an attached item, for example a `CarBattery` in the cradle of a battery adapter. An attachment shows only when all three parts exist:

1. The proxy triangle and its selection in the parent `.p3d`, in every visual LOD, and since 1.30 in View Geometry as well.
2. The proxy `.p3d`, a minimal model at the path the selection names.
3. A `CfgNonAIVehicles` class in `config.cpp` that ties the `inventorySlot` to the proxy model (`proxy-attachment-config.md`).

With any one missing, the item is attached in the inventory and invisible on the model.

Binarize does not merge the proxied model into the parent. Binarizing and converting back through an outside ODOL to MLOD converter shows only that the proxy survived, with its frame and anchor; whether the attached model sits right shows only in game, with a ray cast or a capture.

## Proxy names

A proxy selection is named `proxy:<addon path>\<proxy model>.NNN`.

- Write the path without `.p3d`. Vanilla stores both spellings but almost always the one without: 147 of 17,891 proxy names under `P:\DZ\` keep `.p3d`. On a mod vehicle in game, a proxy whose name kept `.p3d` was silently absent (`proxies.md`), so check this first when a proxy does not show. The power grid mod's own name, `proxy:PowerMod\data\battery_adapter\PM_BatterySlot.p3d.001`, keeps it. py3d refuses it: `LOD.add_proxy` raises "proxy path must omit the .p3d suffix".
- `.NNN` is a three digit index. Vanilla starts at `001` or `000` (`P:\DZ\gear\camping\fence.p3d` uses both).
- The index does not pick an entry of `inventorySlot[]`. `P:\DZ\gear\camping\territory_flag.p3d` stores `proxy:\dz\gear\consumables\stone.001` for the stones of the flag pole, which is the second slot of `ProxyStone` (`P:\DZ\gear\consumables\config.cpp:4573`, slots `Stones` and `Material_FPole_Stones`). A class with several slots is tied to each through the selection that slot's `CfgSlots` entry names (`selection="Material_FPole_Stones"`, `P:\scripts\config.cpp:2496`).
- The config class is `Proxy` plus the model's file name: `ProxyPM_BatterySlot` for the power grid example (`proxy-attachment-config.md`).

## Which LODs hold the proxy

| LOD | Needed | Why |
|---|---|---|
| Resolution LODs | yes | The engine reads the proxy's position from the visual LODs |
| Geometry | no | The triangle is not a collision surface |
| Fire Geometry | no for an item attachment; yes for a vehicle wheel or suspension slot | A wheel slot is seated through this LOD (below) |
| Memory | no | The position comes from the triangle, not from memory points |
| View Geometry | yes since 1.30, for a dedicated server | Up to 1.29, a proxy missing from the last visual LOD could make the server report the parent's origin. Since 1.30 the server reads an inventory attachment's position from View Geometry (official 1.30 changelog; `dayz-1-30-models.md`) |

Wheel and suspension slots are the exception for Fire Geometry. On four vanilla cars (`civiliansedan`, `hatchback_02`, `offroadhatchback`, `offroad_02`) the wheel proxies sit in the resolution LODs and in Fire Geometry at the same positions; `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` stores each wheel proxy 7 times (`proxies.md`). Adding them to Fire Geometry was needed to match vanilla, but on a mod quad it did not by itself fix wheels that never simulated, so do not treat their absence as the only cause. What decides wheel simulation is the link between `CfgSlots.selection` and the Fire Geometry selection (`generated-model-rules.md`, "The wheel slot selection in Fire Geometry"; the wheel slot check in `dayz-p3d-audit/references/vehicle-checks.md`).

## What a proxy selection holds

- One tiny triangle (3 vertices) where the attachment should appear.
- The triangle sets position and facing by its shape, not its vertex order: the corner with the widest angle is the position and the other two give the axes, so a triangle with two equal angles is ambiguous (`proxy-frames.md`). py3d's `LOD.add_proxy` writes an unambiguous triangle.
- An empty texture and material (`""`) on the face.
- Weight 1 for all three vertices and the face.

## An entity made only of proxies

An entity whose visual LOD holds only proxy triangles (written with py3d `LOD.add_proxy`, all inside a selection declared as a bone in `CfgSkeletons`, as mod gun racks do), plus Memory, View Geometry and Fire Geometry box LODs and no Geometry LOD, was measured in game on a mod's test item:

- It draws the attached item at the proxy, shows in the vicinity panel, takes drag in and out, and keeps its attachments across restarts without a `types.xml` entry.
- It needs `autocenter = 0` in its `CfgVehicles` class; without it the engine recentres the model and the memory points and bounding centre shift.
- It still blocks the player: its bounding volume stops movement even with no Geometry, View Geometry or Fire Geometry (four variants tried). Put proxies and cursor boxes inside geometry that blocks anyway, or try the placement without a physics body before you accept it.
- Test it both as an instance loaded from storage and as one created at run time: attachments created in `EEInit` or in the creation tick never reach clients (`skills/_shared/enscript/depth/`).

## Vanilla attachment models

| Item | Model |
|---|---|
| `CarBattery` | `\dz\vehicles\parts\battery_car.p3d` (`P:\DZ\vehicles\parts\config.cpp:152`) |
| `TruckBattery` | `\dz\vehicles\parts\battery_truck.p3d` (`P:\DZ\vehicles\parts\config.cpp:24`) |

The proxy selection does not name the vanilla model. Make your own proxy `.p3d` and tie the vanilla slots to it through `CfgNonAIVehicles`; the engine then draws the attached item's own model at the proxy. Code that writes proxy triangles and proxy models is in `py3d-proxies.md`.

## Electrical port convention

A power grid mod's own convention, not vanilla. Its devices connect by cables that the framework finds by name: the device script calls `AddPort("input_1", ...)` and `AddPort("output_1", ...)` in its constructor, and the framework looks up memory points with matching prefixed names at run time.

| Memory point | Port name in script | Use |
|---|---|---|
| `port_input_N` | `input_N` | Where an incoming cable attaches |
| `port_output_N` | `output_N` | Where an outgoing cable attaches |
| `port_input_N_dir` | paired | The line from `port_input_N` to this point sets how the cable leaves |
| `port_output_N_dir` | paired | The same for the output |

`N` counts from 0 (`port_input_0`) on the mod's older devices (`switch_v1`, the sprinkler) and from 1 (`port_input_1`) on newer ones (`ceiling_light`, `wall_lamp`). Match the numbering of the script's `AddPort` calls; with names that do not match, the cable cannot attach.

Other memory points the mod's devices set:

| Memory point | Needed | Use |
|---|---|---|
| `light` | if the device gives light | Where the point light starts; also a target for `CreateLightAtObjMemoryPoint` (`P:\scripts\4_world\entities\scriptedlightbase.c:215`) |
| `light_emit` | optional | A visual anchor paired with the glowing selection, seen in the mod's `ceiling_light.p3d` |
| `ce_center` | yes | The object's centre |
| `ce_radius` | yes | One point whose distance from `ce_center` is the radius |
| `boundingbox_min`, `boundingbox_max` | yes | The box that frames the inventory preview (`P:\scripts\3_game\gameplay.c:293`) |
| `invview` | optional | The camera point of the inventory preview, forward of the model |

The ports of a wall mounted device, with Z+ as the back toward the wall so cables leave through it:

```python
port_input_1      = (+0.0, cy + 0.04, z_back)         # upper port
port_input_1_dir  = (+0.0, cy + 0.04, z_back + 0.03)  # 3 cm behind the wall
port_output_1     = (+0.0, cy - 0.04, z_back)         # lower port
port_output_1_dir = (+0.0, cy - 0.04, z_back + 0.03)
```

Before placing your own, open the Memory LOD of a similar device with the p3d inspector of `/dayz-model-tools` (`tools-p3d-inspector.md`): where the points sit against the visible mesh is what makes a cable look attached rather than floating, and it differs from device to device.
