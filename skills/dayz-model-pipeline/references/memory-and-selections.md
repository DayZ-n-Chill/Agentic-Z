# Memory points and named selections

Which memory points and named selections a generated model needs, how to create them, how proxy selections make an attachment show, and the memory point convention of the LF_PowerGrid mod's electrical ports.

What is checked and what is not: lines that cite `P:\` were opened and confirmed against vanilla. The Object Builder and Blender steps are tool knowledge. The proxy findings marked SP are the source author's measurements on his own mods (LF_PowerGrid, LFQuad, LFSecure, GunRacks), and the port convention is LF_PowerGrid's own; none of that can be checked on `P:\`. The vanilla side of each topic is in the model pack: `_shared/models/memory-points.md`, `selections.md`, `building-selections.md`, `proxies.md` and `proxy-frames.md`.

Evidence labels: `[CHANGELOG]` is stated by the official 1.30 changelog only. Codes such as SP-081 are the source author's ticket numbers.

## Memory points (Memory LOD)

Memory points are **single vertices** in the Memory LOD. They are not faces or edges, just isolated points in 3D space with a name (a vertex group, which is a named selection).

### How to create memory points

In Object Builder:

- Switch to the Memory LOD.
- Create single vertices at the positions wanted.
- Assign them to named selections.

In Blender (for automation):

- Create Empty objects or single vertex meshes at the required positions.
- Assign them to vertex groups with the correct names.
- The Arma 3 Object Builder addon exports them to the Memory LOD.

Workaround for outside tools that have no plugin:

- Create a triangle and put one or two of its vertices where the points are needed.
- Import it into Object Builder.
- Delete the extra vertex or vertices of the triangle.

With py3d the points are written directly: `py3d-direct-generation.md`, "Memory LOD Pattern".

### Common memory point types

#### Animation axes

Two vertices define a line (an axis) around which a selection rotates or along which it moves.

| Points | Purpose | Example |
|---|---|---|
| `door1_axis` (2 points) | Rotation axis for `door1` | Two points on the hinge line |
| `lever_axis` (2 points) | Rotation axis for a lever | Two points at the pivot |
| `switch_axis` (2 points) | Rotation axis for a switch | Two points at the toggle point |
| `slide_axis` (2 points) | Translation axis for sliding parts | Two points that set the slide direction |

The axis is the line between the two vertices. Rotation happens around this line, translation along it. These names are examples for a mod's own object: the name is free, because the animation class in `model.cfg` names its own `axis`. Vanilla building doors use the plural, `doors1_axis` (`_shared/models/building-selections.md`); a vanilla item example is `lid_axis` in `P:\DZ\gear\camping\wooden_case.p3d`.

Placement rules:

- For a door hinge: both points on the vertical edge where the hinge is, one at the top and one at the bottom.
- For a lever pivot: both points at the pivot, separated along the pivot axis.
- The order of the two points decides the direction of rotation (right hand rule).

#### Interaction points

Single vertices where the player's action widget appears.

| Point | Purpose |
|---|---|
| `actionPos` | Where the interaction prompt appears |
| `doorX_action` | Action point for door X |
| `soundPos` or `doorX_soundPos` | Where door and interaction sounds play |

`actionPos` and `soundPos` are names the mod's own script or config reads; no vanilla script under `P:\scripts\` looks up a point called `actionPos`. Vanilla building doors use one point for both jobs: `soundPos` in `class Doors` names the door's `_action` point (`soundPos="doorsTwin1_action"`, `P:\DZ\structures\residential\config.cpp:7363`).

#### Central economy points

| Point | Purpose |
|---|---|
| `ce_center` | The object's center. The source describes it as the center for loot placement; vanilla script reads it as the center for actions, vicinity and the code lock (`P:\scripts\3_game\entities\object.c:1363`, `_shared/models/memory-points.md`) |
| `ce_radius` | A single point; its distance from `ce_center` sets the radius |

#### Bounding override

If animated parts move outside the default bounding sphere (common with doors):

- Create a named selection in the Memory LOD that covers the full area the object occupies when animated.
- Reference it in `config.cpp`: `bounding = "selection_name";`.
- Without it, the raycast for actions may fail at certain angles.

Not checked on `P:\`: `bounding` is a real config key, but vanilla gear sets it to `"BSphere"` (`P:\DZ\gear\camping\config.cpp:44`), and no vanilla file read here gives it a memory selection name (`config-and-packing.md`).

#### Weapon points (for reference)

| Point | Purpose |
|---|---|
| `usti hlavne` | Muzzle end of the barrel (`P:\scripts\4_world\static\miscgameplayfunctions.c:728`) |
| `konec hlavne` | The other end of the barrel, at the breech (`P:\scripts\4_world\static\miscgameplayfunctions.c:729`) |
| `eye` | Iron sight eye position, named by `memoryPointCamera` (`P:\DZ\weapons\firearms\AKM\config.cpp:169`) |
| `nabojnicestart`, `nabojniceend` | Ejection port: where a spent casing and chamber smoke start, and their direction (`overridePoint="Nabojnicestart"`, `P:\DZ\weapons\firearms\AKM\config.cpp:236`). The source called them the magazine well |
| `recoil` | Recoil application point (source's list; no vanilla script read here looks it up) |
| `optics` | Optics attachment point (source's list; not checked on `P:\`) |

The full weapon table, with every vanilla reader, is `_shared/weapons/model-selections.md`.

### Memory points can be animated

Memory LOD selections can be animated through `model.cfg` like those of any other LOD. This is useful to move an interaction point with an animated part.

---

## Named selections

Named selections are vertex groups that identify parts of the model by name. They serve different purposes in different LODs (`_shared/models/selections.md` has the table of who reads each kind).

### Where a named selection must be present

For an animated part (for example a lever):

| LOD | Required? | Why |
|---|---|---|
| Resolution LODs | Yes | So the visual mesh animates |
| Geometry LOD | Yes | So collision follows the animation |
| Fire Geometry LOD | Yes | So bullet interaction follows the animation |
| View Geometry LOD | Yes | So occlusion and the action cursor follow the animation |
| Memory LOD | Yes | For the axis points and bone definitions |
| Shadow volume | Optional | Shadows follow the animation (recommended when the model has one) |

**The selection must have the same name in every LOD where it appears.** Matching ignores letter case (the barrel model stores `lid` and its config says `class Lid`, `P:\DZ\gear\containers\config.cpp:101`), but spell a name the way the config or script that uses it does.

A collision LOD needs the selection only where the collision should move with the part; a static collision box under a moving lever does not need it.

### Selection naming conventions

| Pattern | Purpose |
|---|---|
| `door1`, `door2` | Animated door selections on a mod's own object (vanilla buildings: `doors1`, `doors2`, see below) |
| `lever`, `switch` | Animated mechanical parts |
| `Component01`, `Component02` | Geometry, Fire Geometry and View Geometry components |
| `camo` | Texture swap selection (for `hiddenSelections`) |
| `zbytek` | "Remainder": everything not in another selection |
| `liquid_source` | Since 1.30: View Geometry component for the liquid actions of a well or pump, `LIQUID_SOURCE_SELECTION` (`P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:180`). See `dayz-1-30-model-pipeline.md` |

### Doors and ladders: the scheme vanilla buildings use

Read on 2026-07-06 from nine vanilla models converted back to MLOD (`garage_small`, `barn_wood1`, `farm_cowsheda` and six ladders), and checked again on `P:\` for the model pack. It refines the tables above, which use the singular `door1`:

- **Doors.** The selection is `doorsN`, plural, in every vanilla building read (`doors1`, `doors2` ...), not `door1`. In the Memory LOD: `doorsN_axis` (the rotation axis) and `doorsN_action` (the action point). Twin doors are `doorstwinN` with `twinN_action`. The `doorsN` selection goes in every LOD that matters (visual, Geometry, Memory, View Geometry, Fire Geometry, Hit points). Named properties of the Geometry LOD: `class=house`, `map=building`, `damage=no`.
- **Ladders**, two schemes: (a) a climbable **loose prop** (`ladder.p3d`) has Memory points `start` and `end` (or `start1` and `end1`) and a Roadway LOD underneath; (b) a ladder **built into a building** (lighthouse, watchtower, silo) has `ladderN` (the base, and a View Geometry component) with Memory points `ladderN_bottom_front`, `ladderN_top_front`, `ladderN_middle_X` (with `_align`, for floors in between), `ladderN_con`, `ladderN_con_dir` and `ladderN_dir`, plus a Roadway. The wiki's `ladderN_*` names are right for the building case.
- **Paths LOD (AI).** `posXX` (stop vertices, usable by `buildingpos`), `inXX` (entry) and `actionbeginN` with `actionendN`.

The full account, with the vanilla files each name was read from and the table of LOD resolution values, is `_shared/models/building-selections.md` and `_shared/models/lods.md`.

### In Blender

Named selections are vertex groups in Blender.

- Create vertex groups with the correct names.
- Assign vertices to them with weight 1.0.
- The Arma 3 Object Builder addon exports vertex groups as named selections.
- A vertex can belong to several selections (for example to both `Component01` and `lever`).

### Selections of LF_PowerGrid objects

Names the LF_PowerGrid mod uses on its devices (third-party convention):

- `cable_attach_point`: where cables connect
- `status_indicator`: an LED or indicator that changes with the power state
- `switch_handle`: the interactive switch part
- `panel_door`: an openable panel cover

---

## Proxy selections (attachment rendering)

Proxy selections tell the engine where to draw attached items (for example a `CarBattery` sitting in the cradle of a battery adapter). Without proxies the attachment exists in the inventory but is invisible on the 3D model.

- **SP-081.** Binarize does not compose the proxied sub models into the parent's ODOL; composition can only be observed in game. An offline "composition canary" (binarize, then convert back through an outside ODOL to MLOD converter) only verifies survival, meaning the sub model's own selections and the proxy's frame and anchor. It does not verify the posed result, which takes a raycast or a capture in game. Origin: 2026-07-21.

### Naming convention

```
proxy:<addon path>\<proxy model>.NNN
```

- `<addon path>\<proxy model>` is the path of a minimal proxy `.p3d`. Write it without the `.p3d` extension. The source writes the extension (`proxy:addon_path\proxy_model.p3d.NNN`), and LF_PowerGrid's own name, `proxy:LFPowerGrid\data\battery_adapter\LFPG_BatterySlot.p3d.001`, is spelled that way. Vanilla stores both spellings, almost always the one without: 147 of 17,891 proxy names under `P:\DZ\` keep `.p3d`. A separate in-game report from a vehicle mod found a name with `.p3d` silently absent (`_shared/models/proxies.md`), so the form without it is the one to write, and a proxy that does not show is first checked for this. The py3d fork enforces it: `LOD.add_proxy` raises "proxy path must omit the .p3d suffix".
- `.NNN` is a three digit index. The source starts it at `001`; vanilla also uses `000` (`P:\DZ\gear\camping\fence.p3d` uses both). The index does not pick an entry of the class's `inventorySlot[]`: vanilla `P:\DZ\gear\camping\territory_flag.p3d` stores `proxy:\dz\gear\consumables\stone.001` for the stones of the flag pole, which is the second slot of `ProxyStone` (`P:\DZ\gear\consumables\config.cpp:4573`, slots `Stones` and `Material_FPole_Stones`). Vanilla ties the proxies of a class with several slots to their slots through the selection each slot's `CfgSlots` entry names (`selection="Material_FPole_Stones"`, `P:\scripts\config.cpp:2496`).
- The class of the LF_PowerGrid example is `ProxyLFPG_BatterySlot` (`config-and-packing.md`: the class name is `Proxy` plus the model's file name).

### Where proxy selections must exist

| LOD | Required? | Why |
|---|---|---|
| Resolution LODs | **Yes** | The engine reads the proxy face position from the visual LODs |
| Geometry LOD | No | The proxy face is not a collision surface |
| Fire Geometry LOD | No for an item attachment, **yes for a vehicle wheel or suspension slot** (SP-012, below) | The proxy face is not a ballistic surface, but a wheel slot is seated through this LOD |
| Memory LOD | No | The proxy position comes from the face, not from memory points |
| View Geometry LOD | **Yes on a dedicated server, since 1.30** | Until 1.29, if the proxy was missing from the last visual LOD the server could report the parent's origin. Since 1.30 `[CHANGELOG]` the server uses the View Geometry LOD for the position of an inventory attachment proxy |

**SP-012: wheel and suspension slot proxies (vehicles).** The "No" for Fire Geometry applies to item attachment proxies only (a battery, a headlight torch and so on). For vehicle wheel and suspension slot proxies it is wrong: on four vanilla cars (civiliansedan, hatchback_02, offroadhatchback, offroad_02) the wheel proxies appear in the Resolution LODs and in the Fire Geometry LOD, at the same positions. On `P:\`, `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` has 6 visual LODs and stores each wheel proxy 7 times (`_shared/models/proxies.md`). A caveat on cause: adding the wheel proxies to Fire Geometry was required for parity, but it did not by itself fix LFQuad's "wheels never simulate". Do not present their absence as the single cause of that bug; the gate for wheel simulation is the wiring between `CfgSlots.selection` and the Fire Geometry selection (`critical-rules.md` rule 20; check SP-017 in `dayz-p3d-audit/references/vehicle-checks.md`).

Since 1.30 `[CHANGELOG]`: duplicate the proxy triangles of item attachments in **View Geometry** as well as in the Resolution LODs, so that a dedicated server does not fall back to the parent's origin. Detail: `dayz-1-30-model-pipeline.md`.

### What a proxy selection contains

- **One tiny triangle** (3 vertices) placed where the attachment should appear.
- The triangle sets the attachment's position and orientation. The source describes it by vertex order (vertex 0 the origin, vertex 1 forward, vertex 2 up). The frame is in fact read from the triangle's shape: the corner with the widest angle is the position and the other two give the axes, so a triangle with two equal angles is ambiguous (`_shared/models/proxy-frames.md`). The py3d fork's `LOD.add_proxy` writes an unambiguous triangle.
- The face has an **empty texture and material** (`""`).
- All 3 vertices and the face have weight 1 in the selection.

### The complete proxy system (three required parts)

For an attachment to show, all three parts must be present:

1. **The proxy face and selection in the parent `.p3d`**, in all visual LODs (and in View Geometry since 1.30).
2. **The proxy `.p3d` file**, a minimal model at the path the selection names.
3. **A `CfgNonAIVehicles` class** in `config.cpp` that maps the `inventorySlot` to the proxy model.

With any one of the three missing, the attachment is attached in the inventory and invisible.

### A proxy carrier with no mesh: an invisible `Inventory_Base` can hold and draw attachments (SP-LFS-6, measured 2026-09-10)

An entity whose visual LOD contains only proxy triangles (py3d `LOD.add_proxy`, all inside a selection declared as a bone in `CfgSkeletons`, the pattern of the GunRacks mod), plus Memory, View Geometry and Fire Geometry box LODs and no Geometry LOD:

- draws the attached item at the proxy, shows in the vicinity panel and accepts drag in and out (the `LFS_Armory_Probe` entity of the LFSecure mod, version 3, checked in game by its author), and persists with its attachments across restarts without a `types.xml` entry;
- needs `autocenter = 0` in its `CfgVehicles` class: without it the engine recenters the model (memory points and the bounding center shift);
- still collides with the player: its bounding volume blocks movement even with no Geometry, no View Geometry and no Fire Geometry (four variants measured). Design proxies and cursor boxes inside geometry that already blocks, or prototype without a physics body before accepting the placement;
- must be verified with both an instance loaded from storage and one created at runtime: attachments created in `EEInit` or in the creation tick never reach clients (SP-LFS-3 in the Enforce Script reference skill).

### Vanilla attachment model paths

Vanilla item models often used in proxy systems:

| Item | Model path |
|---|---|
| `CarBattery` | `DZ\vehicles\parts\battery_car.p3d` (`P:\DZ\vehicles\parts\config.cpp:152`) |
| `TruckBattery` | `DZ\vehicles\parts\battery_truck.p3d` (`P:\DZ\vehicles\parts\config.cpp:24`) |

For proxy rendering you do not reference the vanilla model directly in the proxy selection name. You create your own proxy `.p3d` and link the vanilla attachment slots to it through `CfgNonAIVehicles`. The engine then draws the attached item's own model at the proxy position.

See `py3d-direct-generation.md` for code that creates proxy faces and proxy `.p3d` files, and `config-and-packing.md` for the `CfgNonAIVehicles` class.

### LF_PowerGrid electrical port convention (Memory LOD)

Third-party convention, from the LF_PowerGrid mod. Its devices connect to each other with cables that the framework resolves by name. The device script calls `LFPG_AddPort("input_1", ...)` and `LFPG_AddPort("output_1", ...)` in its constructor, and the framework looks up memory points with the matching prefixed names at runtime.

Required memory point names per port:

| Memory point | Script port name | Purpose |
|---|---|---|
| `port_input_N` | `input_N` | Anchor point where an incoming cable attaches |
| `port_output_N` | `output_N` | Anchor point for an outgoing cable |
| `port_input_N_dir` | (paired) | Direction: the line from `port_input_N` to `port_input_N_dir` sets how the cable exits |
| `port_output_N_dir` | (paired) | The same for the output |

`N` is a small integer, counted from 0 (`port_input_0`) on older items (switch_v1, sprinkler) and from 1 (`port_input_1`) on newer ones (ceiling_light, wall_lamp). **Match the indexing the script's `LFPG_AddPort` calls use.** With mismatched names the cable cannot attach.

Other memory points LF_PowerGrid devices commonly set:

| Memory point | Required? | Purpose |
|---|---|---|
| `light` | If the device emits light | Origin of the point light (also the target of `CreateLightAtObjMemoryPoint`, `P:\scripts\4_world\entities\scriptedlightbase.c:215`) |
| `light_emit` | Optional | Paired visual anchor for the emissive selection (a convention seen in the mod's `ceiling_light.p3d`) |
| `ce_center` | Yes | Geometric center of the object |
| `ce_radius` | Yes | A single point whose distance from `ce_center` sets the radius |
| `boundingbox_min`, `boundingbox_max` | Yes | Tight box corners used to frame the inventory preview (`P:\scripts\3_game\gameplay.c:293`) and by some collision logic |
| `invview` | Optional | Camera anchor for the inventory preview (offset forward from the model) |

Example: the port layout of a wall mounted device (Z+ is the back, the wall side; cables exit through the wall):

```python
port_input_1      = (+0.0, cy + 0.04, z_back)        # upper port
port_input_1_dir  = (+0.0, cy + 0.04, z_back + 0.03) # 3 cm behind the wall
port_output_1     = (+0.0, cy - 0.04, z_back)        # lower port
port_output_1_dir = (+0.0, cy - 0.04, z_back + 0.03)
```

Inspect the Memory LOD of a sibling device with the `dayz-p3d-inspector` skill before designing your own: placement relative to the visible mesh is what makes cables look attached instead of floating, and it varies by device.
