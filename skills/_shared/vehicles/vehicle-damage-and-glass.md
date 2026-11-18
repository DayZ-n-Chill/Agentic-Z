# Car damage zones and glass

How a car's `DamageSystem` block is written in config, how breakable glass uses the same zones, what `RefTexsMats[]` and `"hidden"` do in a damage level, and a windscreen case that is still open.

The zone layout vanilla uses and the zone names script reads are in `damage.md`. Examples marked as third-party come from a four-wheel-drive car built from scratch ("the example 4x4") and the DayZ Expansion UAZ; they are not vanilla.

## The zone block

`class DamageSystem { class GlobalHealth { class Health { hitpoints; healthLevels[] } } class DamageZones { ... } }`. Each zone maps to a `dmgZone_*` selection through `componentNames[]` and `memoryPoints[]`, and can pass damage to other zones (`transferToZonesNames[]`, `transferToZonesCoefs[]`) or to attached items (`inventorySlots[]`, `inventorySlotsCoefs[]`). The example 4x4 uses Chassis, Front, Back, Roof, the four fenders, WindowFront, Engine, FuelTank and the two reflectors; door and window zones of doors live on the `CarDoor` items.

```cpp
class DamageSystem
{
    class GlobalHealth { class Health { hitpoints=2500; healthLevels[]={ {1.0,{}},{0.7,{}},{0.5,{}},{0.3,{}},{0.0,{}} }; }; };
    class DamageZones
    {
        class Chassis
        {
            class Health { hitpoints=2500; transferToGlobalCoef=0; };
            displayName="$STR_CfgVehicleDmg_Chassis0";
            memoryPoints[]={"dmgZone_chassis"}; componentNames[]={"dmgZone_chassis"};
            fatalInjuryCoef=-1; inventorySlots[]={};
        };
        class Front
        {
            class Health { hitpoints=2500; transferToGlobalCoef=0;
                healthLevels[]={ {1.0,{"MyMod\data\body.rvmat"}}, {0.7,{"MyMod\data\body.rvmat"}},
                                 {0.5,{"MyMod\data\body_damage.rvmat"}}, {0.3,{"MyMod\data\body_damage.rvmat"}},
                                 {0.0,{"MyMod\data\body_destruct.rvmat"}} }; };
            displayName="$STR_CfgVehicleDmg_Bumper0";
            transferToZonesNames[]={"Reflector_1_1","Reflector_2_1","Fender_1_1","Fender_2_1","Engine"};
            transferToZonesCoefs[]={0.1,0.1,0.1,0.1,0.15};
            memoryPoints[]={"dmgZone_front"}; componentNames[]={"dmgZone_front"};
            inventorySlots[]={"MyMod_Hood","CarRadiator","MyMod_Wheel_1_1","MyMod_Wheel_2_1"};
            inventorySlotsCoefs[]={0.3,0.25,0.1,0.1};
        };
    };
};
```

`healthLevels[]` has five thresholds (1.0, 0.7, 0.5, 0.3, 0.0), each giving the `.rvmat` list to show at that level; an empty `{}` changes nothing. Every `dmgZone_*` in `componentNames[]` must exist in the model as a Fire Geometry component and a Hitpoints selection, or there is no localized damage.

Script reads `componentNames[]` (`P:\scripts\3_game\damagesystem.c:63` to `:68`), not `memoryPoints[]`; vanilla's Chassis zone can leave `memoryPoints[]` out. Missing Memory `dmgzone_*` points are a parity matter, not a cause of collision jerks (`invariants-engine-fluids-and-handling.md`); keep the Fire Geometry selections and do not spend a game test adding the Memory half as a physics fix.

## `RefTexsMats[]`

A zone's `class Health` can declare `RefTexsMats[]`. Vanilla Motorbike_02 `Front` lists its body, glass and wheel materials, the same files as its 1.0 entry and in the same order (`P:\DZ\vehicles\singletrack\config.cpp:1719` to `:1724`), and its 0.0 entry is `{body_destruct, "hidden", wheel_destruct}` (`:1773`). Read from the config, each slot of an entry replaces the material in the same slot of the list.

Every motorbike zone that hides glass declares the list; Motorbike_01 `FuelTank` and Motorbike_02 `Engine` have none. In `P:\DZ\vehicles\wheeled\config.cpp` none of the 18 `Window*` zones with `"hidden"` declares it, and 14 of them hide with the whole entry `{0,"hidden"}`. How the engine matches materials to faces without the list is not established. A child zone that redefines `healthLevels[]` but not `RefTexsMats[]` keeps its parent's list through `class Health: Health`; what that does in game has not been isolated.

## Window glass

Breakable glass is not a separate system: it is the same zone and `healthLevels[]` swap as a body panel, on a zone named for the window. Configs agree on the shape (intact, intact, damage, destruct, `"hidden"`):

| Config | Zone | `hitpoints` | Last level |
|---|---|---|---|
| Example 4x4 (third-party) | `WindowFront`, body | 200 | `"hidden"` |
| DayZ Expansion UAZ (third-party) | `Window`, per door | 500 | `"hidden"` |
| DayZ Expansion UAZ (third-party) | `WindowFront`, body | 800 | `"hidden"` |
| Vanilla `OffroadHatchback` | `WindowFront` | `hitpoints=120` (`P:\DZ\vehicles\wheeled\config.cpp:2059`) | `"hidden"` (`:2095`) |

The UAZ door window reuses the vanilla Hatchback_02 glass materials, both present under `P:\DZ\vehicles\wheeled\hatchback_02\data\`, a fair shortcut when the vanilla crack look is acceptable:

```cpp
class Window
{
    class Health
    {
        hitpoints=500;
        healthLevels[]=
        {
            {1,   {"dz\vehicles\wheeled\hatchback_02\data\hatchback_02_windows.rvmat"}},
            {0.7, {"dz\vehicles\wheeled\hatchback_02\data\hatchback_02_windows.rvmat"}},
            {0.5, {"dz\vehicles\wheeled\hatchback_02\data\glass_i_damage.rvmat"}},
            {0.3, {"dz\vehicles\wheeled\hatchback_02\data\glass_i_damage.rvmat"}},
            {0,   "hidden"}
        };
    };
    fatalInjuryCoef=-1; transferToGlobalCoef=0;
    componentNames[]={"dmgZone_doorwindowLeft"};
};
```

Name zones in English with the `dmgZone_*` pattern (`dmgZone_windowFront`, `dmgZone_doorwindowLeft`). The old Czech glass names and their pipeline (a convex glass hull copied into Fire Geometry, one Hitpoints vertex per opening) come from older games and do not apply to DayZ's config zones.

Not established, so test before relying on it:

- The right `hitpoints`: values run from 120 to 800, so calibrate per vehicle.
- Which LOD the `dmgZone_window*` selection must sit in; convert the sedan and look (`vehicle-structural-parity.md`).
- Whether `"hidden"` at zero health also removes collision and fire blocking, or only the visual. Shoot through a broken window in game.
- That the swap and hiding work on glass at all; see the next section.

## A windscreen that never hid

Vanilla motorbikes put `"hidden"` in the glass slot of a zone with `RefTexsMats[]`: Motorbike_02 `Front`, `Reflector_1_1` and `FuelTank` (`P:\DZ\vehicles\singletrack\config.cpp:1703`, `:1864` and `:2160`, with `"hidden"` at `:1773`, `:1929` and `:2221`), and Motorbike_01 `Reflector_1_1` (`motorbike-damage-and-wheel-config.md`). In the binarized Motorbike_02 model that glass material sits on three LOD 0 sections, one per zone, with a procedural texture at 10% alpha; `motorbike_02_glass.rvmat` sets `renderFlags[] = {"NoZWrite"}` and the `Super` shaders (`P:\DZ\vehicles\singletrack\motorbike_02\data\motorbike_02_glass.rvmat:7` to `:12`). The Motorbike_02 windscreen is not one of them: it is the attachment `Motorbike_02_ShieldFront_ColorBase` (`proxy\Motorbike_02_windshield.p3d`), with its own `GlobalHealth` swap to windshield, damage and destruct materials and no `"hidden"`; its slot is in `Front`'s `inventorySlots[]` (`:1083` for the class, `:1788` for the slot).

One imported motorbike wired its windscreen like that body glass instead: `Front` declares `RefTexsMats[]` with the glass material in the same slot as every level, and `"hidden"` in that slot at 0.0. Its binarized LOD 0 has 390 sections (vanilla Motorbike_02 has 22); the windscreen is section 173, a procedural at 35% alpha, and the ninth of the 67 sections of `dmgzone_front`; the glass material is on 149 sections, 146 of them in `dmgzone_back`. With the zones taken down by the vanilla contact damage call (`process-gates.md`) and levels 2 and 4 logged on server and client, `Front`'s body panels took the damage and destruct materials and came back on repair, while the windscreen stayed drawn at level 4. Measured in game on DayZ 1.30 in four runs, the last with the crack material removed from the 0.5 and 0.3 entries. The cause is unknown.

- Ruled out: a missing file. `"hidden"` needs none, the glass material is on faces, and the test PBO held its marker material, so the config-only texture trap (`binarize-dropped-textures.md`) does not apply. Binarize's "Material not loaded" names the glass material, but also body materials that do swap.
- Weak evidence: at level 2 cracks and a red emissive marker never showed, but no part wore those materials from the start, and cracks on alpha-blended glass are faint. A vanilla Motorbike_02 cannot settle it, since its nearly clear glass looks the same hidden or not. The strong evidence is the windscreen still drawn at level 4.

Untested causes: a limit on section index or count (a cap at a zone's first 64 sections would still include its ninth, and 173 is under 256); a per-material section count; how transparent sections are handled (vanilla glass is also `NoZWrite` and `Super`, but no vanilla glass was seen hiding either); the shape itself, since vanilla puts body glass in zones of two to five sections, cars give glass its own zone, and the Motorbike_02 windscreen is an attachment. Section indices move between builds (`proxies-and-detachable-parts.md`), so read the index from the binarized model you test.

Cheapest first, one change per build against an unchanged control, each build counted against the budget in `method-and-gate-calibration.md`:

1. Offline, the face ownership count in `lights.md` for the windscreen section, against the model's hidden selections.
2. The windscreen in a zone of its own whose 0.0 entry is `{0,"hidden"}`.
3. The windscreen as an attachment, like `Motorbike_02_ShieldFront`.
4. The windscreen at a low section index with the same material and section count (check the binarized model first).
5. Its own material path (same content) with its own `RefTexsMats[]` slot.
6. `NoZWrite` alone against an opaque texture alone.
7. An opaque, unmistakable final material instead of `"hidden"`, next to a part that wears it from the start.

Until one of them changes the result, a glass zone that passes config and model checks is only configured, not known to work.
