# Cookbook: attachment invisible

For a wheel, door, part or rack item that is attached and simulates but does not render: the proxy frame contract, the class name rule to check first, which proxy base class a slot needs, and why one rack cannot align rifles and tools.

Vanilla facts cite the file on `P:\`. The measurements on SUB_BRZ, LFQuad3 and the GunRacks mod come from the author's projects and from that third-party mod; they are not yet checked on `P:\`. A binary `.p3d` has no lines to cite, so facts measured on the vanilla sedan model name the file only.

## Check first: the `Proxy` class name against the file name

Do this before measuring any frame. It is a text check on `config.cpp`, it takes seconds and it has no false positives. For each proxy class in `CfgNonAIVehicles`, the class name must equal `Proxy` plus the base name of its `model` file, compared without case:

```
class_name.lower() == "proxy" + basename(model).lower()
```

Vanilla follows it: `ProxySedanWheel` has the model `sedanWheel.p3d` (`P:\DZ\vehicles\wheeled\config.cpp:23969-23971`), `ProxySedanWheel_destroyed` has `sedanWheel_destroyed.p3d` (`P:\DZ\vehicles\wheeled\config.cpp:23981-23983`) and `ProxyTruck_01_Wheel_ruined` has `Truck_01_Wheel_ruined.p3d` (`P:\DZ\vehicles\wheeled\config.cpp:23921-23923`).

Breaking the rule has two measured results:

- **A client crash on the damage swap.** On SUB_BRZ the file `sub_brz_wheel_ruined.p3d` needs the class `ProxySUB_BRZ_Wheel_ruined`. A class named `_destroyed` over a file named `_ruined` correlated with a native client crash when the wheel swapped to its damaged model (SUB_BRZ defect B5; not the allowlist check of the same number).
- **Silent, total non-render.** Added 2026-09-09. On LFQuad3 the attachment proxies were for inventory slots (`Shoulder`, `Melee`, `Back`), not wheels. All three drew nothing: no item, no placeholder, no line in the RPT. Six recipes tested in game touched the slot property, the `hide` animation, `initPhase`, the proxy index and the LOD; none touched the class name. Measured with the checker of the GunRacks mod: that mod conformed 18 of 18, LFQuad3 0 of 4; after the rename it was 3 of 3 and the items draw, verified in game. This failure mode costs far more because it leaves nothing to investigate: no error, no log, nothing to search for. Skipping the text check cost six in-game cycles.

## The attachment renders from the shell's proxy frame

SUB_BRZ defect B1, session s37.

The engine instances the attached item's model on the proxy of the visual LOD being drawn, oriented by that proxy's frame. An identity frame hides the piece while the simulation stays intact. py3d's `add_proxy(rotation=None)` writes an identity frame: the attached wheel renders rotated about 90 degrees and tucked inside the arch. It is invisible from outside and a raycast at the hub hits nothing, while attach, simulation and damage all work. That is the exact "attached but invisible" signature.

The contract, measured against the civiliansedan control (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`: 5 wheel proxies in every visual LOD 1, 2, 3, 4 and 6, plus View Geometry and Fire Geometry):

1. The attachment proxy exists in every visual LOD of the shell, not only the finest.
2. Each proxy carries the lateral frame of its side: for x greater than 0 `((1,0,0),(0,0,-1),(0,1,0))`, mirrored for x less than 0. Doors carry the uniform measured door frame `((-1,0,0),(0,0,1),(0,1,0))`.
3. The proxy point flags are 63, like the control. The identity-frame proxies also had flags 0.
4. The `CfgNonAIVehicles` class name matches the proxy file base name without case: the check at the top of this file.

Mechanical gate: `derive_proxy_frame` of every visual attachment proxy equals the expected frame, with a negative fixture (the identity frame must fail).

"Attached but invisible" is not a missing item LOD 0.0 (refuted in game in s37), and it is not a bone or companion issue when the anchors and companions match. After the class name check, measure the frames. Root cause analysis: `<vehicle-import>\work\s37_b1_rca\B1_RCA_findings.md`.

**Status.** The fix was verified offline (measured twice) on 2026-07-18, and its in-game gate was closed on 2026-08-24: the attached part renders in its place. The proxy frame correction is therefore verified in game, not only offline.

## The frame per side belongs to its control

Added 2026-08-22.

The constant in point 2 (for x greater than 0 `((1,0,0),(0,0,-1),(0,1,0))`, mirrored for x less than 0) is not universal. It was measured on `civiliansedan_mlod` and holds for geometry derived from that control. The rip import history of the vehicles pack says the same: copy the vanilla frame, not the frame of the "kt" mod, whose mirror differs because its wheel geometry differs. The structural parity topic gives the general rule: the frame depends on e1 and e2 and on the orientation of the base model. (`rip-import.md` and `vehicle-structural-parity.md` in the source pack.)

The practical consequence, and where time is lost: measuring these literals against a control from another family yields "inverted" with nothing broken. It happened. A note in the ledger (SP-156) recorded the constant as measured backwards after comparing it against a Landrover. Before believing the constant is wrong:

1. Measure the frame of your own control, the one that renders, with `derive_proxy_frame`.
2. Compare against that, not against these literals.
3. If your control has a different geometry, a difference is expected and is not a bug.

The mechanical fixture that goes with the invariant requires only that the identity frame fails. A fixture that swaps the sides and requires a failure is still pending; it is what would turn "inverted" into an automatic red instead of a discussion.

## `ProxyVehiclePart` and `ProxyAttachment` are not interchangeable

From the same LFQuad3 session, measured in game. `ProxyVehiclePart` is the vanilla base of the wheel and door proxies; it inherits `ProxyAttachment` and sets `simulation="ProxyInventory"` (`P:\DZ\vehicles\wheeled\config.cpp:23901-23904`). It draws the model of the proxy class: on a rack that showed as a gray placeholder rifle. `ProxyAttachment` places the attached entity there. For a wheel, whose proxy model is the wheel, `ProxyVehiclePart` is correct. For an inventory slot that must show whatever is attached to it, it is the bug.

## A rack shared by rifles and tools does not align both

Added 2026-09-13.

An attachment proxy draws the item in the local frame of the item's model, with the origin at the proxy point. The vanilla models that fit the `Shoulder` and `Melee` slots (`Slot_Shoulder` and `Slot_Melee`, `P:\scripts\config.cpp:20-26`) do not share a long axis. Census of 120 parts on LFQuad3: 84 of 87 weapons in `CfgWeapons` have it along X; the 3 bows (`Archery_Base`) and the 33 tools in `CfgVehicles` have it along Y. A rack placed for rifles leaves a shovel, pickaxe or axe crossed by 90 degrees, and a viewer that draws each model in its own frame already shows it. It is not an engine or viewer bug; it is geometry.

Two solutions, both measured in game:

- **Two proxies on the same slot**, one per family and each on its own bone, with script hiding the proxy of the family that is not attached (`IsWeapon`, `P:\scripts\3_game\entities\object.c:630`; `Archery_Base` counts as a tool). It draws the tool in the correct plane. On LFQuad3 it was dropped for looks.
- **A rack for weapons only.** Reject in `CanReceiveAttachment` (`P:\scripts\3_game\entities\entityai.c:1472`) whatever is not `IsWeapon()` or is `Archery_Base`. No dedicated slot is needed; a dedicated slot would force a patch of `Rifle_Base` for every weapon on the server.

Census trap: most vanilla weapon configs open `class cfgWeapons` in lower case (`P:\DZ\weapons\archery\bow_pvc\config.cpp:22`). A parser that compares the root name with case sees zero weapons and returns "zero exceptions". Require positive controls (three known rifles along X) before trusting the result.
