# Attachment proxies that draw nothing

Why a wheel, door, part or rack item can be attached and simulate yet not render: the proxy class name rule, the proxy frame the item is drawn in, which proxy base class a slot needs, and why one rack cannot hold rifles and tools in line.

Facts measured on test vehicles and on a third-party gun rack mod are marked as such; they are not checked on `P:\`. A binarized `.p3d` has no lines to cite, so facts read from the vanilla sedan model name the file only.

## Check the proxy class name first

This is a text check on `config.cpp` that takes seconds and has no false positives, so do it before measuring any frame. For each proxy class in `CfgNonAIVehicles`, the class name must equal `Proxy` plus the base name of its `model` file, compared without case:

```python
class_name.lower() == "proxy" + basename(model).lower()
```

Most vanilla proxies follow it: `ProxySedanWheel` uses `sedanWheel.p3d` (`P:\DZ\vehicles\wheeled\config.cpp:23969` to `:23971`), `ProxySedanWheel_destroyed` uses `sedanWheel_destroyed.p3d` (`:23981` to `:23983`) and `ProxyTruck_01_Wheel_ruined` uses `Truck_01_Wheel_ruined.p3d` (`:23921` to `:23923`). A few do not (`ProxyHatchback_02_Wheel_destroyed` draws `Hatchback_02_ruined.p3d`, `:24187` to `:24189`), but in a mod keep the names matched.

Breaking the rule has two results, both measured in game on test vehicles:

- A client crash on the damage swap. A wheel file named `_ruined.p3d` needs a class ending `_ruined`; a class named `_destroyed` over a `_ruined` file went with a native client crash when the wheel swapped to its damaged model.
- Nothing drawn at all. Attachment proxies for the `Shoulder`, `Melee` and `Back` slots drew no item, no placeholder and no line in the RPT. Changing the slot, the `hide` animation, `initPhase`, the proxy index and the LOD did nothing; renaming the classes to match their files made every item draw. A third-party gun rack mod passes the same check on all 18 of its proxies. Because this case leaves no error to search for, run the text check before anything else.

## The item draws in the shell's proxy frame

The engine draws the attached item on the proxy of the visual LOD being drawn, turned by that proxy's frame. An identity frame hides the item while simulation, attach and damage keep working: the wheel draws turned about 90 degrees and tucked inside the arch, invisible from outside, and a ray at the hub hits nothing. That is the "attached but invisible" signature. py3d's `add_proxy(rotation=None)` writes exactly this identity frame (**tool knowledge**).

The vanilla sedan (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`) has its 5 wheel proxies in every visual LOD (1, 2, 3, 4 and 6) and in View Geometry and Fire Geometry (**model knowledge**). Match it:

1. Put the attachment proxy in every visual LOD of the shell, not only the finest.
2. Give each proxy the frame of its side. On the sedan a wheel with x greater than 0 has `((1,0,0),(0,0,-1),(0,1,0))`, mirrored for x less than 0; doors share `((-1,0,0),(0,0,1),(0,1,0))`.
3. Set the proxy point flags to 63, as the sedan does. Identity frame proxies written by a tool also tend to carry flags 0.
4. Keep the class name rule above.

An automatic check can compare each visual attachment proxy's frame against the expected one; make it fail on an identity frame, and prove that it does. A missing item LOD 0.0 is not the cause, and neither are bones or companion items when anchors and companions already match. With the fix applied, the attached part draws in its place, measured in game on a test car.

## Measure the frame on your own reference car

The side frames in point 2 hold for the vanilla sedan and for geometry derived from it. They are not universal: the frame depends on the two axes of the base model and on its orientation (`vehicle-structural-parity.md`). A third-party wheel mod's frame can be mirrored relative to the sedan because its wheel geometry differs, so copy the vanilla frame (`rip-import.md`).

Measuring these literals against a reference car of another shape reads as "inverted" with nothing broken. Before deciding the frame is wrong:

1. Measure the frame of your own reference car, the one that draws, with `derive_proxy_frame`.
2. Compare against that, not against the literals here.
3. Expect a difference when the reference has other geometry.

A check that swaps the sides and expects a failure does not exist yet; with it, an inverted frame would show as a failure instead of a discussion.

## `ProxyVehiclePart` and `ProxyAttachment` are not interchangeable

`ProxyVehiclePart` is the vanilla base of the wheel and door proxies: it inherits `ProxyAttachment` and sets `simulation="ProxyInventory"` (`P:\DZ\vehicles\wheeled\config.cpp:23901` to `:23904`). It draws the model of the proxy class itself, which on a rack shows as a grey placeholder rifle (measured in game). `ProxyAttachment` places the attached entity there instead. For a wheel, whose proxy model is the wheel, use `ProxyVehiclePart`; for an inventory slot that must show whatever is attached, use `ProxyAttachment`.

## A rack for rifles and tools cannot line up both

An attachment proxy draws the item in the item model's own frame, with the origin at the proxy point. The vanilla models that fit `Slot_Shoulder` and `Slot_Melee` (`P:\scripts\config.cpp:20` to `:26`) do not share a long axis. A count of 120 vanilla items finds 84 of 87 weapons in `CfgWeapons` long along X, and the 3 bows (`Archery_Base`) and 33 tools in `CfgVehicles` long along Y. A rack placed for rifles shows a shovel, pickaxe or axe crossed by 90 degrees. That is geometry, not an engine bug.

Two fixes, both measured in game on a test vehicle:

- Two proxies on the same slot, one per family and each on its own bone, with script hiding the proxy of the family not attached (`IsWeapon`, `P:\scripts\3_game\entities\object.c:630`; count `Archery_Base` as a tool).
- A rack for weapons only. In `CanReceiveAttachment` (`P:\scripts\3_game\entities\entityai.c:1472`) reject anything that is not `IsWeapon()`, and reject `Archery_Base`. No new slot is needed; a new slot would mean patching `Rifle_Base` for every weapon on the server.

When you count items yourself, note that most vanilla weapon configs open `class cfgWeapons` in lower case (`P:\DZ\weapons\archery\bow_pvc\config.cpp:22`). A parser that compares the root name with case finds zero weapons and reports no exceptions. Check that three known rifles come out along X before trusting the count.
