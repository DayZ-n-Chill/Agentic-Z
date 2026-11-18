# Texture, LOD and wheel slot checks

What to check in a mod's assets before packing: every texture and material path resolves, each `.p3d` has the LODs and memory points it needs, and a vehicle's wheel slots point at selections that make the wheels simulate. The other pre-build checks are indexed in `pre-build-checks.md`.

## Texture and material paths

Collect every reference from three places: `config.cpp` (`hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]` and any quoted `.paa` or `.rvmat`), each `.rvmat` (the textures it names), and the `.p3d` face textures when py3d is available.

A reference is a root path that starts with a PBO prefix, not a path relative to the addon. Vanilla writes `"dz\gear\tools\data\alarmclock_blue_co.paa"` (`P:\DZ\gear\tools\config.cpp:85`); a mod with the prefix `mymod\myaddon` writes `"mymod\myaddon\data\body_co.paa"`. Resolve it from the `P:\` root, where the addon sits at `P:\<prefix>`.

| Check | Level |
|---|---|
| Every referenced `.paa` and `.rvmat` exists | Fail |
| Capitalisation matches the file on disk; paths are case sensitive on a Linux server | Warn |
| A `.png` or `.dds` is referenced; DayZ wants `.paa` | Warn |
| Each `.rvmat` names textures that exist in the addon or in vanilla data | Fail |
| Several selections share one texture: it has room for all their UVs | Manual |

Sample report lines:

```text
[FAIL] Texture not found: mymod\myaddon\data\textures\body_co.paa (config.cpp line 45, class Item_Shirt)
[WARN] PNG file: data\textures\logo.png (convert to PAA)
[WARN] Capitalisation: referenced as "Textures\Cloth_Co.paa", file is "textures\cloth_co.paa"
[PASS] All 12 texture references found
```

## LODs

Check this when the addon has `.p3d` files and py3d is available.

| Check | Rule |
|---|---|
| Resolution LOD | At least one (LOD 0.0); it is what the player sees. Required. |
| Geometry LOD | Present, for collision and physics. Required. |
| Memory LOD | Present, for named selections and memory points. Required. |
| Geometry mass | Every component has a mass above 0; the engine ignores a component with none. |
| Degenerate faces | No zero-area faces. |
| `ce_center` | Optional. It is the object's centre for actions and the vicinity list, not the centre of mass: `GetCenter` (`P:\scripts\3_game\entities\object.c:1361`) uses it when the point exists (`:1363`) and otherwise returns the object's position raised by 0.2 m (`:1371`); the action targets and the vicinity list name the point too (`P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:857`; `P:\scripts\5_mission\gui\inventorynew\vicinityitemmanager.c:11`). A byte scan finds it in 1,220 of the 10,626 vanilla models under `P:\DZ`. Add it when the model's middle is far from its origin, so actions aim at the item and not below it. Warn, never fail, when it is missing. |
| Collision points | None to check here: collision comes from the Geometry LOD, not from memory points. A byte scan of all 10,626 vanilla models under `P:\DZ` finds no `ce_geom` point. |
| Named selections | The same across LODs (a selection in LOD0 should exist in LOD2); warn on an unpaired name such as `Left_Arm` with no `Right_Arm`. |
| Vertex budget for a small item | LOD0 up to about 3,000 vertices, LOD1 40 to 60% of LOD0, the far LOD 10 to 20%. Warn above it; the Geometry LOD of a small item should also stay under 3,000. |

Sample report lines:

```text
[PASS] Resolution, Geometry and Memory LODs present
[PASS] Geometry LOD mass valid (all components above 0)
[WARN] Memory LOD has no ce_center point (GetCenter falls back to the object's position raised by 0.2 m)
[WARN] LOD0 has 4200 vertices (high for a small item)
```

## Wheel slots on a wheeled vehicle

For PhysX to seat a wheel (`WheelCountPresent() > 0`), the selection named by `CfgSlots > <wheel slot>.selection` in `config.cpp` must exist in the body's Fire Geometry LOD. A selection only in the visual LODs binds the slot for the inventory, but the wheel never simulates: `WheelCountPresent()` is 0, there is no traction and no spin, and the RPT says nothing. Treat it as a release blocker. Background: `skills/_shared/enscript/depth/vehicle-scripting.md` and `skills/_shared/models/generated-model-rules.md`, "The wheel slot selection in Fire Geometry".

The `dayz-p3d-audit` validator checks it. Run it before the build:

```bat
python "<skill-dir>\..\dayz-p3d-audit\scripts\audit_p3d.py" --scan-dir P:\<Mod>
```

`--scan-dir` finds the mod's `config.cpp` and checks every wheel slot's selection against the body's Fire Geometry.

| Output | Meaning |
|---|---|
| CRITICAL `Wheel-slot selection '<n>' (from CfgSlots) is missing from Fire Geometry LOD[<i>]` | The wheel will not simulate. Block the release, and add the Fire Geometry wheel proxy face to a selection named `<n>` with py3d, keeping its other selections, before packing. |
| NOTE `Wheel-slot check not run: ...` | The mapping could not be read; a config that reuses the vanilla wheel slots has no `CfgSlots` of its own. Check by hand. |

`audit_p3d.py` exits 1 on any CRITICAL, so adding `--scan-dir` to the pre-build gate keeps a vehicle with dead wheels from being packed. A wheeled body whose Geometry LOD lacks the named property `class=vehicle` is reported as CRITICAL too; that matches vanilla, but it is not what makes the wheels simulate.
