# Placement and `autocenter`

Where vanilla keeps `autocenter=0` on placed items and on vehicles, which rule to follow for each, and the one case where the property on two LODs made a placed item float at knee height.

## Where vanilla keeps it

- Vehicles: the part proxy class `ProxyVehiclePart` sets `autocenter=0` (`P:\DZ\vehicles\wheeled\config.cpp:23901` to `:23905`), and that is the only `autocenter` line in the file. `CivilianSedan` (`config.cpp:5113`) has none, so a vanilla car carries the property in its model and on its part proxy classes, not on the car's config class.
- Placed gear: in `P:\DZ\gear\camping\config.cpp` the only two `autocenter` lines sit in proxy classes under `CfgNonAIVehicles`, `ProxyPart` (`:13387`) and `Proxycable_reel` (`:13548`). No item class under `CfgVehicles` there sets it.
- A byte scan of the 82 binarized models in `P:\DZ\gear\camping\` finds the name `autocenter` in 78 of them (for example `P:\DZ\gear\camping\wooden_case.p3d`), and also in `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` and `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanwheel.p3d`. The scan shows vanilla keeps the property in the model; it cannot show which LOD holds it or its value.

## Which rule to follow

| Object | Rule |
|---|---|
| A new placed object | Follow `_shared/models/named-properties.md`: the named property `autocenter` = `0` goes on the Geometry LOD together with the config line. `/dayz-p3d-audit` (`check_autocenter_prop` in `skills/dayz-p3d-audit/scripts/audit_p3d.py`) reports a Geometry LOD without the property when the config sets it. |
| A vehicle or a proxy model | The property is a named property on the Geometry LOD. An unbinarized copy of the `CivilianSedan` carries `{autocenter:0, class:vehicle}` on its resolution 1e13 LOD (read with py3d; the copy on `P:\` is binarized), and its config class has no `autocenter` line. Follow `vehicle-structural-parity.md`; `rip-geometry-and-winding.md` covers the host model and its sub-models. Never run the strip snippet below on a vehicle `.p3d`. |

## A placed item that floats at knee height

One measured case goes against the first rule, so test for it when a placed item floats. Measured in game on one mod item, a pressure pad on `Inventory_Base`:

- The config class set `autocenter = 0;`.
- The `.p3d` also had `autocenter=0` on the Geometry LOD (resolution 1e13) and on the LandContact LOD (2e15).
- The placement hologram floated about 0.4 m above the ground, and the placed object stayed at that height on the server and the client.
- Removing only those two LOD properties put it back on the ground, with no code change.

The cause is not established and not checked on `P:\`. One reading: the ground contact takes the bottom of the object from the Geometry and LandContact LODs, and the property there applied an offset a second time on top of the config line. Vanilla models carry the property without floating, so do not turn this into a rule that a LOD property is a bug. When a placed item floats at knee height, test this removal first.

## LOD resolutions used here

The full table is in `_shared/conventions/assets.md`. This file uses Geometry 1e13, Memory 1e15, LandContact 2e15, View Geometry 6e15, Fire Geometry 7e15, Shadow volume 10000, and visual LODs below 1000. A classifier that puts Fire Geometry at 3e13 or View Geometry at 7e13 is wrong for DayZ, and reports LandContact, View Geometry and Fire Geometry as unknown.

## Strip the property to test the floating case

Write the result to a copy, test it in game, and keep the original; for a new placed object the property on the Geometry LOD stays the rule.

```python
import py3d

def strip_bad_autocenter(p3d_path, out_path=None):
    """Remove autocenter=0 from the Geometry, Memory, LandContact,
    View Geometry and Fire Geometry LODs. Never run it on a vehicle or proxy model."""
    with open(p3d_path, "rb") as f:
        p = py3d.P3D(); p.read(f)

    changed = []
    for i, lod in enumerate(p.lods):
        res = lod.resolution
        is_collision = (
            abs(res - 1e13) < 1e12 or    # Geometry
            abs(res - 1e15) < 1e14 or    # Memory
            abs(res - 2e15) < 1e14 or    # LandContact
            abs(res - 6e15) < 1e14 or    # View Geometry
            abs(res - 7e15) < 1e14       # Fire Geometry
        )
        if is_collision and lod.properties.get("autocenter") == "0":
            del lod.properties["autocenter"]
            changed.append((i, f"res={res:.0g}"))

    if changed:
        with open(out_path or p3d_path, "wb") as f:
            p.write(f)
    return changed
```

## Related tools

- `skills/dayz-model-tools/scripts/p3d_inspector_build.py` writes the `properties` of the recipe JSON and adds `autocenter` = `0` to a Geometry LOD whose recipe has none.
- `config.cpp` conventions for placeable items are in the Enforce Script pack, `skills/_shared/enscript/`.
