# Placement, `autocenter`, and the knee-height bug

Where `autocenter=0` belongs on a placed item and on a vehicle, why adding it to every LOD of one placed item made it float at knee height, and the LOD resolution bands to use when reading or writing LOD properties.

> Status: a field note measured on one third-party mod item (LFPG_PressurePad, April 2026) and on debinarized copies of the vanilla CivilianSedan and of a quad bike mod. Those measurements were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. Skills of other parts of this import are named without a path (dayz-p3d-inspector, enforce-script-reference).

## Vanilla anchors checked on `P:\`

- Vehicles: `ProxyVehiclePart` at `P:\DZ\vehicles\wheeled\config.cpp:23901` sets `autocenter=0` four lines down, and that is the only `autocenter` line in the file. `CivilianSedan` (`P:\DZ\vehicles\wheeled\config.cpp:5113`) has none, which matches the SCOPE note below: a vanilla car carries the property in the model and on its part proxy classes, not on the car's config class.
- Placed gear: in `P:\DZ\gear\camping\config.cpp` the only two `autocenter` lines sit in proxy classes under `CfgNonAIVehicles`: `ProxyPart` (`P:\DZ\gear\camping\config.cpp:13387`) and `Proxycable_reel` (`P:\DZ\gear\camping\config.cpp:13548`). No item class under `CfgVehicles` there sets it.
- A byte scan of the 82 binarized models in `P:\DZ\gear\camping\` finds the property name `autocenter` in 78 of them (for example `P:\DZ\gear\camping\wooden_case.p3d`), and in `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` and `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanwheel.p3d`. The scan shows that vanilla keeps the property in the model; it cannot tell which LOD holds it or its value.

## Where this note disagrees with the rest of the repo

For placed items this note says the config class is authoritative and a LOD-level `autocenter=0` is a bug. `skills/_shared/models/named-properties.md` says the opposite: a placed object carries the named property on the Geometry LOD as well as the config line, and `check_autocenter_prop` in `skills/dayz-p3d-audit/scripts/audit_p3d.py` reports a Geometry LOD that lacks the property when the config sets it. Vanilla on `P:\` sides with the model-side property (anchors above), so follow `named-properties.md` when building a new placed object.

Keep this note for what it measured. On that one item the property sat on the Geometry and LandContact LODs together with the config line, the hologram and the placed object were about 0.4 m too high, and removing the two LOD properties fixed it. When a placed item floats at knee height, test that removal first. The explanation under "Why adding it to LODs breaks things" is the author's reading and is not checked on `P:\`.

## What the note says

A short but important reference: where `autocenter=0` actually belongs, and
why the "add it everywhere to be safe" advice is wrong and actively breaks
DayZ placements.

## Short answer

`autocenter=0` goes on the **config.cpp** class, not on any `.p3d` LOD — for
**Inventory_Base placeable items**; vehicles are the exception (see SCOPE below).

SCOPE (corrected s20 2026-07-02): this rule is for **Inventory_Base placeable items** (verified on
LFPG_PressurePad). **VEHICLES AND PROXY MODELS ARE THE EXCEPTION**: vanilla working vehicles carry
`autocenter=0` as a named property ON the Geometry LOD (CivilianSedan MLOD res=1e13 props
`{autocenter:0, class:vehicle}`, measured via py3d; QuadBike likewise), and the CivilianSedan config class
has NO config-level autocenter. For vehicles follow `vehicle-structural-parity.md`; never run
`strip_bad_autocenter` on a vehicle `.p3d`.

```cpp
class LFPG_PressurePad : Inventory_Base
{
    scope = 2;
    model = "\LFPowerGrid\data\pressure_pad\pressure_pad.p3d";
    autocenter = 0;   // <- THIS is the right place
    // ...
};
```

Do NOT duplicate `autocenter=0` onto the Geometry LOD, LandContact LOD,
Memory LOD, View Geometry LOD, or Fire Geometry LOD properties. The config
flag is authoritative.

## Why adding it to LODs breaks things

Verified on `LFPG_PressurePad` in April 2026:

- The `.p3d` had `autocenter=0` added to LOD 3 (Geometry, res 1 × 10¹³) and
  LOD 5 (LandContact, res 2 × 10¹⁵) by a previous pipeline/editor.
- In-game symptom: the placement hologram appeared floating ~0.4 m above
  ground (knee height), and the final placed object stayed at the same
  height. Both server-side and client-side.
- Removing just those two LOD-level `autocenter=0` properties restored
  correct ground placement immediately. No code changes needed.

The engine's ground-contact calculation uses the Geometry/LandContact
position to figure out where the "bottom" of the object is. When the
config's `autocenter=0` already freezes the model origin, re-asserting it
on the LOD effectively double-applies the offset and the engine places the
object with an extra shift on top of the visual origin.

## LOD resolution bands (DayZ)

For reference when reading/writing LOD properties (the same values as the table in `skills/_shared/conventions/assets.md`, which adds GeoPhys at 4 × 10¹³):

| Type | Resolution |
|---|---|
| Visual 0, 1, 2… | 0, 1, 2, … |
| Shadow volume | 10 000 |
| Geometry (collision) | 1 × 10¹³ |
| Memory | 1 × 10¹⁵ |
| LandContact | 2 × 10¹⁵ |
| Roadway | 3 × 10¹⁵ |
| Paths | 4 × 10¹⁵ |
| HitPoints | 5 × 10¹⁵ |
| View Geometry | 6 × 10¹⁵ |
| Fire Geometry | 7 × 10¹⁵ |

Older skill notes listed GeoPhys at 2 × 10¹³, FireGeo at 3 × 10¹³, ViewGeo
at 7 × 10¹³. Those values are wrong for modern DayZ and cause LandContact,
ViewGeo, and FireGeo to all be misclassified as "memory".

## Audit / fix snippet

```python
import py3d

def strip_bad_autocenter(p3d_path, out_path=None):
    """Remove `autocenter=0` from collision/landcontact LODs only.

    Returns list of (lod_index, lod_type) tuples that were changed.
    """
    with open(p3d_path, "rb") as f:
        p = py3d.P3D(); p.read(f)

    changed = []
    for i, lod in enumerate(p.lods):
        res = lod.resolution
        # Everything except Visual (res < 1000) and Shadow (10000)
        is_non_visual = res >= 10000 and res != 10000
        # More specifically: Geometry, LandContact, Memory, View, Fire
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

## When config-level `autocenter=0` is appropriate

- **Always** for `Inventory_Base` items that are placeable on the ground
  (the vast majority of deployable kits and their placed devices).
- **Always** when you authored the model with the origin at the intended
  ground-contact point rather than at the geometric center.
- Skip it only if you know the engine's auto-centering gives you what you
  want (uncommon — usually only for small handheld items where the exact
  "sit on ground" pose doesn't matter).

## When someone might legitimately add LOD-level `autocenter=0`

Rare. The one case is a model where the LOD's geometry centroid is far
from the origin and you explicitly don't want the engine to recompute
the LOD's own center. In practice, for DayZ mod kits you should assume
"LOD-level autocenter is a bug" until proven otherwise.

## See also

- `/dayz-p3d-audit`: the author's copy of `audit_p3d.py` warned when `autocenter=0` was found on a
  non-visual LOD. This repo's `skills/dayz-p3d-audit/scripts/audit_p3d.py` does the reverse (see the
  disagreement section above): it reports a Geometry LOD without the property when the config sets it.
- The dayz-p3d-inspector skill: `p3d_inspector_build.py` does NOT auto-add
  `autocenter`; Recipe JSON `properties` is authoritative.
- The enforce-script-reference skill: config.cpp conventions for placeable items.
- `vehicle-structural-parity.md` and `rip-geometry-and-winding.md` ("`autocenter=0`: corrected scope"): the vehicle side of this rule.
