# Proxies and detachable parts

How proxies sit on a car that works, which four config and model layers a detachable door, hood or trunk needs, what changes when a baked part becomes an attachment, and how to check binarized output without trusting its bytes. Actions for a seated player and get-in faults are in `seated-actions-and-get-in-faults.md`; hiding an attachment proxy from script is in `attachment-proxy-hiding.md`; the get-in condition chain and which anchor places the occupant are in `get-in-actions-and-proxy-pose.md`. Regenerating a dense body from glTF or FBX and splitting it into proxies to stay under the vertex limit, and the get-in radial and LOD set of a car whose body is proxies, are in `vehicle-structural-parity.md`.

The measurements come from mod vehicles, not vanilla ones: a working off-road car mod that ships unbinarized (the control), a helicopter on `CarScript`, two imported cars and a motorbike derived from `Motorbike_02_ColorBase`.

## How a working car places its proxies

The control ships unbinarized (MLOD version 257), so py3d reads it directly. Its LOD 0 has 18 proxies:

- No anchor sits at the origin. Each anchor is at the part's real position: a wheel at `[0.8746, 0.4513, -1.5638]`, the driver door at `[0.888, 0.6492, -0.8629]`, the trunk at `[0.0021, 1.1487, 2.5139]`.
- No proxy has an identity frame. The usual frame is `[[-1,0,0],[0,0,1],[0,1,0]]`; the other side mirrors it as `[[1,0,0],[0,0,-1],[0,1,0]]`; the spare wheel has its own rotation.
- Each sub-model is built in its own local space, origin at the attachment point. The distance from origin to bounding box centre is 0.000 m for the wheel and trunk, 0.726 m for the hood and 0.821 m for the driver door, which pivot on their hinges.

Rules that follow:

1. The proxy anchor is the part's position in the host's coordinates. An anchor at the origin is a defect.
2. A sub-model sits near its own origin, within about 1 m. One whose bounding box centre is 2 to 7 m away was built in host coordinates; that is the defect worth checking for.
3. The frame `[[-1,0,0],[0,0,1],[0,1,0]]` is the normal neutral, and working crew proxies carry it too. An exact identity frame never appears in a working model, and forcing it made placement worse in game on the helicopter.
4. A zero-size crew marker proxy (about 463 bytes) is unaffected by any frame because its geometry sits at the origin. Read the convention from a proxy that carries geometry.
5. Doors on a working vehicle are proxies with their own `.p3d` anchored at the hinge, not baked geometry moved by a bone. Consider that before designing doors driven by bones.

Check any rule like these against a model that works before trusting it: of three rules first written from the broken helicopter, two would have flagged every correct model. A check built on this section tests each proxy for an anchor at the origin, a sub-model built in host space, and agreement of normals and winding.

## The four layers of a detachable part

A door that "does not animate" with its script and model correct is usually missing a layer. Measured on the control:

1. `CfgSlots`. The slot's `selection` ties "the attachment is mounted" to "the proxy is drawn":

```cpp
class Slot_MyMod_Car_Driver_Door
{
    name = "MyMod_Car_Driver_Door";
    displayName = "...";
    selection = "doors_driver";   // the animation bone selection
    ghostIcon = "set:dayz_inventory image:doorfront";
};
```

2. `CfgNonAIVehicles`, the layer that gets missed. Without it the engine does not treat the host's `proxy:\...` as an attachment proxy. Vanilla declares `ProxyVehiclePart` with `scope=1`, `simulation="ProxyInventory"`, `autocenter=0`, `animated=0`, `shadow=1`, `reversed=0` (`P:\DZ\vehicles\wheeled\config.cpp:23901`), and `ProxySedanWheel` (`config.cpp:23969`) is a vanilla proxy class with a `model` and an `inventorySlot[]`. The control declares its own copy with `scope=2` and the same other values:

```cpp
class ProxyAttachment;
class ProxyVehiclePart: ProxyAttachment
{
    scope = 2; simulation = "ProxyInventory"; autocenter = 0; animated = 0; shadow = 1; reversed = 0;
};
class ProxyMyMod_Car_Driver_Door: ProxyVehiclePart
{
    model = "\MyMod\proxy\MyMod_Car_Driver_Door.p3d";
    inventorySlot = "MyMod_Car_Driver_Door";
};
```

   The control sets `autocenter=0` in three places: the sub-model's visual LOD, its Geometry LOD and this class.
3. The item class, `MyMod_Car_Driver_Door: CarDoor`, with `model`, `inventorySlot`, `hiddenSelections`, `weight`, `itemSize[]`, `physLayer` and a `DamageSystem`.
4. The vehicle: the slot name in `attachments[]`, and `class Doors` in its damage system.

The host's proxy triangle belongs to two selections. On the control's LOD 0, all three points of the driver door proxy are in `doors_driver` (the bone) and in the selection named after the slot. A proxy wired only to the bone animates but does not follow the attachment.

A detachable part is a physical item that can lie on the ground, so its `.p3d` needs real special LODs, not an empty Geometry. The control's driver door (points and faces): visual 463 and 754, Geometry 32 and 24, Memory 7 and 0, View Geometry 32 and 24, Fire Geometry 72 and 56, with `autocenter=0` on the visual and Geometry LODs. Budget those LODs before promising the feature.

For a custom slot, the slot name and the item's `inventorySlot` must match exactly, or the item never attaches and the proxy never draws. Appending with `inventorySlot[] += {...}` to a parent that uses the string form is a separate trap, covered in `_shared/conventions/config.md`. Rewriting a proxy triangle and the scope of `autocenter=0` are in `rip-geometry-and-winding.md`.

## When a baked part becomes an attachment

A vanilla car draws a door proxy only while the door is attached; that is the behaviour a baked door is converted to. Two things then look like a broken model and are not.

### The part is missing on every debug or admin spawn

`CreateObject`, admin tools and test tool spawns do not fill attachment slots, which is why a vanilla car spawned that way has no wheels. Fill them in `OnDebugSpawn()` (`P:\scripts\3_game\entities\entityai.c:3955`; `OnDebugSpawnEx(DebugSpawnParams params)` calls it at `entityai.c:3937` to `:3939`):

- One `CreateAttachment` per part, as a quad bike mod does:

```c
override void OnDebugSpawn()
{
    EntityAI entity;
    if (Class.CastTo(entity, this))
    {
        entity.GetInventory().CreateAttachment("CarBattery");
        entity.GetInventory().CreateAttachment("SparkPlug");
        entity.GetInventory().CreateAttachment("MyMod_Quad_Wheel_Front");
        // ...
    }
}
```

- One `CreateInInventory` per part, as the sedan does: `SpawnUniversalParts(); SpawnAdditionalItems(); FillUpCarFluids();` then one call per door and wheel (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:415` to `:436`).

The `EntityAI` version reads the type's `attachments[]`, scans `CfgVehicles`, `CfgMagazines` and `CfgWeapons` for a class whose `inventorySlot` matches, and calls `CreateInInventory` for it (`entityai.c:3955` to `:4009`). Calling `super.OnDebugSpawn()` therefore fills a vehicle from config with no code per model, which helps when one script base serves several models. The vanilla cars do not call `super`; they list their parts.

### `attachments[]` across an addon boundary

Within one config tree, `+=` can keep the parent's slots. When the parent comes from another, already compiled PBO, that list is not a safe basis: write the full list of vital and own slots in the child class. Check the effective list after a compile or config dump, not the presence of a `+=` token: battery, ignition, radiator, wheels and each declared door or part. Separately, check that each declared part appears in the `OnDebugSpawn` path.

## Proving a part was extracted from the shell

A shell can report only the proxy triangle under `door_1` and still keep the whole window, because the window belongs to a shared `glass` selection. For each visual LOD, count the shell faces inside the detached part's footprint by material, place the sub-model at its proxy anchor, and match face twins in model space. A matched shell face is a duplicate; an unmatched one is real shell. Take the distance tolerance from the dip in the measured two-peak distance histogram, not a round number. Checked offline only.

Removing the duplicate can expose an older sub-model placement error, so a more visible hole after cleanup is not proof of a regression. A zero difference between the sub-model and the volume it was built from proves where it came from, not how the engine draws it; the final placement check is in game.

## Binarized output is not byte-stable

Two runs of `binarize.exe -always` over the same source with the same flags produced shells of 2,886,719 and 2,763,097 bytes with different hashes, and interiors of 1,062,412 and 1,062,417 bytes. Two small rotor models came out identical, so the effect grows with model size. The two shells match in meaning: all 66 model info fields, and the same faces, selections and properties per LOD. Only encoding and compression order differ, and between builds the order of faces and sections changes too (`skills/dayz-build-pbo/references/post-build-gates.md`). On the motorbike, a rebuild from identical MLODs kept every count per LOD while the face arrays differed in every resolution LOD and the View Pilot, and the LOD 0 section of `dashboard` moved from index 175 to 204 between two builds.

So compare binarized models by meaning: counts per LOD, selections, properties, proxies, centres. Never compare bytes or section indices; between builds, key on the unordered set of sections. Comparing hashes stays valid for MLOD files the pipeline writes itself.
