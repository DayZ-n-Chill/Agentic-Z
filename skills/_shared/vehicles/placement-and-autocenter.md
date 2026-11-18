# Placement, `autocenter`, and the knee-height bug

Where `autocenter=0` sits on a vanilla placed item and on a vanilla vehicle, one measured case where the property on two LODs of a placed item made it float at knee height, and a snippet that strips the property to test for that case.

> Status: the knee-height case was measured in game on one placed mod item (a pressure pad on `Inventory_Base`), and the vehicle LOD properties on unbinarized copies of the vanilla CivilianSedan and of a quad bike mod; the mod results are third-party mod behaviour, not vanilla. A citation written with its full `P:\` path was opened on the vanilla data on `P:\`. Other skills are named by skill name, each a folder under `skills/` (dayz-model-tools); the Enforce Script pack is `skills/_shared/enscript/`.

## Vanilla anchors checked on `P:\`

- Vehicles: `ProxyVehiclePart` at `P:\DZ\vehicles\wheeled\config.cpp:23901` sets `autocenter=0` four lines down, and that is the only `autocenter` line in the file. `CivilianSedan` (`P:\DZ\vehicles\wheeled\config.cpp:5113`) has none: a vanilla car carries the property in the model and on its part proxy classes, not on the car's config class.
- Placed gear: in `P:\DZ\gear\camping\config.cpp` the only two `autocenter` lines sit in proxy classes under `CfgNonAIVehicles`: `ProxyPart` (`P:\DZ\gear\camping\config.cpp:13387`) and `Proxycable_reel` (`P:\DZ\gear\camping\config.cpp:13548`). No item class under `CfgVehicles` there sets it.
- A byte scan of the 82 binarized models in `P:\DZ\gear\camping\` finds the property name `autocenter` in 78 of them (for example `P:\DZ\gear\camping\wooden_case.p3d`), and in `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` and `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanwheel.p3d`. The scan shows that vanilla keeps the property in the model; it cannot tell which LOD holds it or its value.

## The rule to follow

- **A new placed object**: follow `skills/_shared/models/named-properties.md`. The named property `autocenter` = `0` goes on the Geometry LOD together with the config line, and `check_autocenter_prop` in `skills/dayz-p3d-audit/scripts/audit_p3d.py` reports a Geometry LOD that lacks the property when the config sets it. Vanilla on `P:\` keeps the property in the model (anchors above).
- **A vehicle or a proxy model**: the property is a named property on the Geometry LOD. The unbinarized CivilianSedan carries `{autocenter:0, class:vehicle}` on its resolution 1e13 LOD (read with py3d), a quad bike mod likewise, and the CivilianSedan config class has no `autocenter` line. Follow `vehicle-structural-parity.md`, and never run `strip_bad_autocenter` (below) on a vehicle `.p3d`. `rip-geometry-and-winding.md` ("`autocenter=0`: corrected scope by LOD, host, and submodel") covers the host and its sub-models.

## The measured case: a placed item floating at knee height

One measured case goes against the first rule, so test for it when a placed item floats:

- The item was a pressure pad on `Inventory_Base` with `autocenter = 0;` in its config class:
  ```cpp
  class MyMod_PressurePad : Inventory_Base
  {
      scope = 2;
      model = "\MyMod\data\pressure_pad\pressure_pad.p3d";
      autocenter = 0;
      // ...
  };
  ```
- Its `.p3d` also had `autocenter=0` on LOD 3 (Geometry, resolution 1 × 10¹³) and on LOD 5 (LandContact, resolution 2 × 10¹⁵), added by an earlier pipeline step.
- In game the placement hologram floated about 0.4 m above the ground (knee height), and the placed object stayed at that height, on the server and on the client.
- Removing only those two LOD properties restored ground placement at once, with no code change.

Why it happened is not established and is not checked on `P:\`. One reading: the ground contact calculation takes the bottom of the object from the Geometry and LandContact LODs, and the property on those LODs applied an offset a second time on top of the config line. Vanilla models carry the property in the model without floating, so do not turn this case into a rule that a LOD property is a bug. When a placed item floats at knee height, test that removal first.

## LOD resolutions used here

The resolution values of each LOD type are in the table in `skills/_shared/conventions/assets.md`. The ones this file uses: Geometry 1 × 10¹³, Memory 1 × 10¹⁵, LandContact 2 × 10¹⁵, View Geometry 6 × 10¹⁵, Fire Geometry 7 × 10¹⁵, Shadow volume 10 000, and Visual LODs below 1000. A classifier that puts Fire Geometry at 3 × 10¹³ or View Geometry at 7 × 10¹³ is wrong for DayZ and reports LandContact, View Geometry and Fire Geometry as unknown.

## Snippet: strip the property to test for the measured case

```python
import py3d

def strip_bad_autocenter(p3d_path, out_path=None):
    """Remove `autocenter=0` from the collision, memory and LandContact LODs.

    Returns list of (lod_index, lod_type) tuples that were changed.
    Never run it on a vehicle or proxy model.
    """
    with open(p3d_path, "rb") as f:
        p = py3d.P3D(); p.read(f)

    changed = []
    for i, lod in enumerate(p.lods):
        res = lod.resolution
        is_collision = (
            abs(res - 1e13) < 1e12 or    # Geometry
            abs(res - 1e15) < 1e14 or    # Memory
            abs(res - 2e15) < 1e14 or    # LandContact
            abs(res - 6e15) < 1e14 or    # ViewGeo
            abs(res - 7e15) < 1e14       # FireGeo
        )
        if is_collision and lod.properties.get("autocenter") == "0":
            del lod.properties["autocenter"]
            changed.append((i, f"res={res:.0g}"))

    if changed:
        with open(out_path or p3d_path, "wb") as f:
            p.write(f)
    return changed
```

Write the result to a copy (`out_path`), test it in game, and keep the original: for a new placed object the property on the Geometry LOD is the rule.

## See also

- `/dayz-p3d-audit`: `skills/dayz-p3d-audit/scripts/audit_p3d.py` reports a Geometry LOD without the property when the config sets `autocenter = 0`.
- The p3d inspector of the dayz-model-tools skill: `p3d_inspector_build.py` writes the `properties` of the Recipe JSON, and adds `autocenter` = `0` to a Geometry LOD whose recipe has none.
- the Enforce Script pack (`skills/_shared/enscript/depth/`): `config.cpp` conventions for placeable items.
- `vehicle-structural-parity.md` and `rip-geometry-and-winding.md` ("`autocenter=0`: corrected scope by LOD, host, and submodel"): the vehicle side of this rule.
