# DayZ technical notes: models, physics, configs and loot

Covers py3d usage, LOD resolutions, winding and normals when porting from Blender, debris spawn offsets, double-sided faces, custom `Container_Base` requirements, dynamic item physics, magazine quantity, JSON schema migration, the optional LBmaster preset integration and a multi-tier loot cascade.

Status: every `P:\` citation below was opened and confirmed on 2026-11-17. The rest is not yet checked on `P:\`: in-game measurements name the mod they were measured on (Crate, Crate_Wooden, WallLamp, MercedesAMGLF and A6_MK47 are example mods whose source is not in this repo), and the LBmaster and DayZ Expansion facts are third-party mod behaviour, not vanilla. Checked versions of five topics already exist and win where they differ: `skills/_shared/py3d-mlod-notes.md`, `skills/_shared/conventions/assets.md` (LOD table), `skills/_shared/container-base.md`, `skills/_shared/enscript/patterns/physics_items.md` and `skills/_shared/enscript/patterns/json_config_migration.md`.

## py3d (MLOD reader)
- Constructor: `P3D(file)` — NOT `P3D.read(file)`.
- `lod.resolution` → float. Table in section "DayZ LODs".
- `lod.points[i].coords` → tuple `(x, y, z)`.
- `face.vertices[i].point.coords` → tuple `(x, y, z)`.
- `face.vertices[i].normal` → **direct tuple `(x, y, z)`**, NOT `.coords`. Confusing them results in silent fallback.
- `lod.facenormals` → **global pool of `(x, y, z)` tuples indexed by `vertex.normal_index`**, NOT a per-face array. Size = MLOD header `num_facenormals`, **independent** of `len(lod.faces)`. Each `Vertex` has `point_index` (→ `lod.points` pool) and `normal_index` (→ `lod.facenormals` pool). `face.vertices[i].normal` is a property resolving `all_normals[normal_index]`.
- `face.vertices[i].uv` → tuple `(u, v)`.
- `lod.selections['Name'].points` / `.faces` → named subsets.

## DayZ LODs — canonical resolutions

| LOD | resolution | Notes |
|---|---|---|
| Visual | `0.0`, `1.0`, `2.0`, ... | LOD0 = base |
| ShadowVolume | `10000`, `11000` | |
| Geometry | `1e13` | physical collision |
| Memory | `1e15` | named points |
| LandContact | `2e15` | |
| ViewGeometry | **`6e15`** | cursor/actions raycast; without this actions fail |
| FireGeometry | **`7e15`** | bullets/projectiles; without this bullets pass through |

FireGeo=`3e13` and ViewGeo=`7e13`, quoted by some online guides, are not DayZ LOD values; a tool that classifies LODs with them misreads a DayZ model. `skills/dayz-p3d-audit/scripts/audit_p3d.py` uses the values in the table above (see `skills/_shared/conventions/assets.md`).

Verification: the LOD list of `P:\DZ\gear\camping\wooden_case.p3d` → 9 LODs with Visual(1..4) + Geometry(`1e13`) + Memory(`1e15`) + LandContact(`2e15`) + ViewGeo(`6e15`) + FireGeo(`7e15`).

## Winding & normals (handedness Blender→DayZ) — CRITICAL TOPIC
It is the #1 cause of failures when porting models from Blender to DayZ. Subtle symptoms, misleading diagnostics. It was hit on the WallLamp and Crate_Wooden mods — read entirely before touching any imported model.

### Symptoms in game
- **The texture is only visible from INSIDE the object.** The object looks "empty" from outside (classic case, bad Visual LOD).
- **Bullets pass through the object** (bad winding in FireGeo + Geometry → raycast from outside finds no solid surface).
- **Actions do not appear** or cursor does not detect object (bad winding in ViewGeo or Geometry).
- **The player can walk through the object** (bad Geometry or GeoPhys).
- Sometimes only ONE of these symptoms: winding may be fine in Visual and bad in Geometry, or vice versa. **Verify each LOD separately.**

### Root cause
The winding decision follows the map, which is the same for Blender-authored geometry and for GLB/glTF geometry brought through Blender; a glTF read without Blender follows "GLB and glTF imports" (see `skills/dayz-model-pipeline/references/critical-rules.md`, Rule 12, and "GLB and glTF imports" in `axes-and-winding.md` of the same folder):
- **Blender-authored geometry**, via the reflection `x'=x, y'=z, z'=y` (det=-1): map vertices and normals in all LODs, keep the face order and negate the normals (`dayz-model-pipeline` Rule 12, measured in game 2026-10-01; the old det=+1 rotation `z'=-y` ships a mirrored model).
- **Geometry originating from GLB/glTF** (exported to spec, brought through Blender): the same map, the same face order, normals negated. **Never** reverse the faces after the det=-1 map: that rendered see-through in game (MercedesAMGLF, 2026-06-24), and A6_MK47 v12c rendered correctly with the order kept (2026-06-11).
Never assume: verify the result with `check_face_winding` (it must yield ~0% flipped, and it shows only that the face order and the normals agree) and check chirality on an asymmetric feature. *(Aligned 2026-10-03: the opening read "The winding decision depends on the asset source — Blender-authored or GLB/glTF; both maps below are det=-1 (Rule 12), with two cases:", the GLB/glTF case read "**Geometry originating from GLB/glTF**, via pure swap `(x,y,z)->(x,z,y)` (det=-1): **ALWAYS** invert vertex order of each face across each LOD, except proxy triangles, whose order encodes attachment frame." and this line read "Never assume which of the two cases applies: verify result with `check_face_winding`; must yield ~0% flipped.")*

Reversing faces does NOT touch the normals in the `lod.facenormals` pool — they keep pointing where they pointed before (for Blender-authored geometry, Rule 12 negates them explicitly). That is why the model *looks* correct when inspecting normals but fails in game: **what matters to the raycast/render engine is the winding, not the declared normal**.

### Canonical fix
For Blender authorship and for a GLB/glTF brought through Blender, follow `dayz-model-pipeline` Rule 12 (det=-1 reflection, face order kept, normals negated); the det=+1 rotation ships a mirrored model. A glTF read without Blender follows that skill's "GLB and glTF imports" (node transforms baked, mirrored instances reversed, its own det=-1 map). Reverse every face only to undo a reversal that hit every face, such as py3d `P3D.transform()` with a det<0 map (it reversed the proxy triangles too), and then negate every normal (Rule 12; `py3d.blender_to_dayz()` does both); faces that read outward only in part are fixed per face (`dayz-p3d-audit` killer #1). The whole-model reversal: *(Aligned 2026-10-03: this paragraph read "For Blender authorship, follow `dayz-model-pipeline` Rule 12 (det=-1 reflection, face order kept, normals negated); the det=+1 rotation ships a mirrored model. For a GLB/glTF source with det=-1 swap, invert vertex order with:")*
```python
import py3d
with open(p3d_path, 'rb') as f:
    p = py3d.P3D(f)
for lod in p.lods:                   # ALL LODs, not just Visual
    for face in lod.faces:
        face.vertices.reverse()       # inverts corner order in-place
with open(p3d_path, 'wb') as f:
    p.write(f)
```

Rules:
- When the whole-model reversal above is right, apply it to **all** LODs, proxy triangles included (`P3D.transform()` reversed them too): Visual + ShadowVolume + Geometry + LandContact + ViewGeometry + FireGeometry. Leaving one out produces inconsistencies between render and collision. *(Aligned 2026-10-03: this bullet opened "When Rule 12 requires inverting winding (GLB/glTF case, det=-1), apply to **all** LODs except proxy triangles:".)*
- `reverse()` operates in-place on the list of Vertex objects. **It does NOT touch the `lod.facenormals` pool** (it is global, indexed by `vertex.normal_index`) or `normal_index` — declared normals still point to the same pool location, which is correct.
- **DO NOT use the old "swap `vertices[1]` and `vertices[2]`"** — works only for tris. Quads and larger polys require `reverse()`.
- **UNIFORM application is essential.** If you skip some faces, the model ends up with mixed winding, which is WORSE than an inside-out flipped model: some areas show from outside, others from inside, unpredictable rendering. **Verify post-fix with Check B (edge-pair topology).**

No script for this reversal is in this repo; the loop above is the whole operation.

### Verification and gotchas — see `dayz-p3d-audit` skill

To verify winding (Check A diagnostic, Check B edge-pair topology, Check C
vs vanilla) and for the known traps (a whole-model flip applied twice undoes itself, Crate_Wooden
tolerated mixed winding, `face.flags |= 0x20000` did not give double-sided rendering in the Visual LOD)
→ see `skills/dayz-p3d-audit/references/winding-diagnostics.md`. The checklist for importing a
new Blender model is in `winding-methodology.md` in the same folder.

## Debris spawn offsets — from crate selection centroids, NOT debris bbox
**Rule:** spawn offset of each debris from the **centroid of the selection with that name inside Visual LOD0 of the main crate**. Do NOT use the bbox of the debris individual .p3d.

**Reason:** both bboxes may differ by several cm because Object Builder recenters when exporting/importing the individual .p3d, whereas the named selection in the intact crate maintains the original pose. Using the individual bbox produces embedded or height-misaligned offsets.

```python
with open(crate_main_p3d, 'rb') as f:
    model = py3d.P3D(f)
visual_lod = next(l for l in model.lods if l.resolution == 0.0)
sel = visual_lod.selections['plank_front']  # selection by name, not bbox
pts = [p.coords for p in sel.points]
centroid = (sum(p[0] for p in pts)/len(pts),
            sum(p[1] for p in pts)/len(pts),
            sum(p[2] for p in pts)/len(pts))
# centroid = spawn offset of the corresponding debris
```

## Single-sided vs double-sided faces
.p3d exported from Blender are single-sided by default (0 back-twin pairs, `face.flags = 0x0`). This is correct for parts only visible from the outside (sides, floor, corners of a closed crate).

**Exception:** planks at the **ends** (Front/Back) on an open crate are visible from outside (intact box) AND inside (gaps between planks once broken or when spawning detached) → require back-twin.

The fix is to duplicate each face of the Visual LOD with inverted vertex order and negated normal, and to extend the selections to include the twins (no script for this is in this repo). Do NOT touch Geo/Shadow/Memory (collision and shadow remain single-sided, as they should).

**Measured in-game:** setting `face.flags |= 0x20000` on single-sided faces of Visual LOD did not
achieve two-sided rendering: they remained transparent. The route that did work was duplicating
geometry (double-siding). The reason was measured offline: `binarize.exe` discards the MLOD per-face
`flags` field, so no face-flag value (`0x20000` or `0x00000020`) reaches the game
(`skills/dayz-p3d-audit/references/winding-diagnostics.md`, "Known traps").

## Custom `Container_Base`: non-obvious requirements
Inheriting from `Container_Base` is NOT enough by just declaring `scope = 2; model = ...;`. The resulting object takes no damage or bullets if config.cpp lacks:

1. `class Cargo { itemsCargoSize; openable; allowOwnedCargoManipulation; }` — some builds do not initialize the object as container without this.
2. `class GlobalArmor { class FragGrenade { ... } }` — without this the engine may not register projectile impacts.
3. `healthLevels[] = { {1.0, {"rvmat"}}, ... }` — modern format. **DO NOT** use `healthLevelValues[]` (legacy, silently breaks DamageSystem).

**Closed crates without player Cargo (Crate_Wooden case):** if loot spawns world-space via `EEKilled` and does not use Cargo, set `itemsCargoSize[] = {0, 0}`. Keep `class Cargo` empty because Container_Base needs it to initialize. If `{0,0}` yields RPT warning, plan B: inherit from `Inventory_Base` and remove entire `class Cargo` (not yet tested).

Reference: vanilla `WoodenCrate`, which opens at `P:\DZ\gear\camping\config.cpp:10157`.

## Dynamic item physics (`ThrowPhysically`)
**Symptom:** items spawned with `CreateObjectEx(name, pos, ECE_CREATEPHYSICS|ECE_UPDATEPATHGRAPH)` + `dBodyApplyImpulse(ent, impulse)` appear **frozen in mid-air** without falling.

**Cause:** for items with `simulation = "inventoryItem"` + `physLayer = "item"`, `ECE_CREATEPHYSICS` creates the **collision shape** but leaves the rigid body **static/kinematic**. `dBodyApplyImpulse` on a non-dynamic body is silently discarded. Dynamics + gravity + lifetime must be activated.

**Correct fix: `ThrowPhysically`** (signature at `P:\scripts\3_game\entities\inventoryitem.c:26`):
```
proto native void ThrowPhysically(DayZPlayer player, vector force, bool collideWithCharacters = true);
```
Internally does `CreateDynamicPhysics(ITEM_LARGE)` + `SetDynamicPhysicsLifeTime(...)` + applies force as impulse (inferred from behaviour; the native body is not in the scripts).

It is the vanilla pattern: vanilla calls `ThrowPhysically(null, force, false)` at `P:\scripts\4_world\static\miscgameplayfunctions.c:1321` and `:1345`. `P:\scripts\4_world\plugins\pluginbase\plugindeveloper.c:430` uses the other form, `ThrowPhysically(null, "0 0 0")`, which keeps `collideWithCharacters` at its default of true.

```enforce
ItemBase debrisEnt = ItemBase.Cast(spawned);
debrisEnt.ThrowPhysically(null, impulse, false);
```

**Related APIs verified in `P:\scripts`:**
- `P:\scripts\1_core\proto\enphysics.c:141` → `proto void dBodyApplyImpulse(notnull IEntity body, vector impulse);` — valid but ONLY on already dynamic body.
- `P:\scripts\1_core\proto\enphysics.c:64-69` → `dBodyActive`, `dBodyDynamic`, `dBodyIsDynamic`, `dBodyEnableGravity`.
- `P:\scripts\3_game\entities\object.c:456-458` → `CreateDynamicPhysics(int interactionLayers)`, `EnableDynamicCCD(bool)`, `SetDynamicPhysicsLifeTime(float)` — `Object` members, manually usable.
- `P:\scripts\3_game\global\dayzphysics.c:1-29` → enum `PhxInteractionLayers { NOCOLLISION, DEFAULT, BUILDING, CHARACTER, VEHICLE, DYNAMICITEM, DYNAMICITEM_NOCHAR, ROADWAY, ... }`. Vanilla uses `DYNAMICITEM` for inventory items.
- `P:\scripts\4_world\entities\itembase.c:4530` → `StopItemDynamicPhysics()` ⇒ `SetDynamicPhysicsLifeTime(0.01)`. Confirms that lifetime keeps dynamics alive.

**Manual pattern** (fine control without `ThrowPhysically`):
```enforce
obj.CreateDynamicPhysics(PhxInteractionLayers.DYNAMICITEM);
obj.EnableDynamicCCD(true);
obj.SetDynamicPhysicsLifeTime(20.0);  // without this the engine puts it to sleep
dBodyEnableGravity(obj, true);
dBodyApplyImpulse(obj, impulse);
```

## Quantity in magazines (`ServerSetAmmoCount`)
**Silent bug:** `ItemBase.SetQuantity(N)` on a Magazine (actual mags `Mag_*` and ammo piles `Ammo_*` — both extend `Magazine_Base`) does NOT fill internal ammo count. Admin requests `quantity=30` and mag spawns with 0 bullets.

**DWIM fix** for "quantity" in loot presets:
```enforce
if (node.quantity >= 0.0)
{
    Magazine mag = Magazine.Cast(ent);
    if (mag)
    {
        mag.ServerSetAmmoCount(node.quantity);
    }
    else
    {
        ItemBase ib = ItemBase.Cast(ent);
        if (ib)
            ib.SetQuantity(node.quantity);
    }
}
```
Cast to `Magazine` first (covers mags and ammo piles), then fall back to `ItemBase.SetQuantity` for normal stackables (Rag, PaperSheet, etc.).

**Verified signatures:**
- `P:\scripts\4_world\entities\itembase\magazine\magazine.c:70` → `proto native void ServerSetAmmoCount(int ammoCount);`
- `P:\scripts\3_game\entities\entityai.c:2227` → `bool SetQuantity(float value, bool destroy_config = true, bool destroy_forced = false, bool allow_client = false, bool clamp_to_stack_max = true);`

Vanilla names `ServerSetAmmoCount` on 29 lines of `P:\scripts` (counted 2026-11-17), for example `P:\scripts\4_world\entities\firearms\weapon_base.c:797`, `P:\scripts\4_world\classes\playergearspawn\cfgplayerspawnhandler.c:330` (and `:340`) and `P:\scripts\4_world\classes\recipes\recipebase.c:314` (and `:420`).

## Schema migration JSON — ExpansionSettingBase pattern
**Problem:** when a schema gains fields, an admin with an old JSON lacks them. If the constructor injects "didactic examples", on Load those examples remain intact → admin sees loot appearing out of nowhere, not knowing why.

**Canonical pattern** (the one DayZ Expansion uses in `OnLoad` of `ExpansionGarageSettings.c`; third-party mod behaviour, not vanilla):

1. `static const int SCHEMA_VERSION = N;` in config class. Bump N when adding fields.
2. **Minimal constructor:** numeric/scalar defaults only + `new array<T>` (empty so serializer does not receive null). `version = 0` as "not loaded yet" sentinel.
3. **Separate `Defaults()` method:** populates all fields with factory + examples. Idempotent (`Clear()` before `Insert()` in arrays).
4. **`LoadOrCreate` pattern:**
   - JSON does not exist → `cfg.Defaults(); SaveToDisk(cfg);`
   - JSON exists + load OK + `cfg.version < SCHEMA_VERSION` → `fresh = new Cfg; fresh.Defaults();`. Copy NEW fields via incremental migration (`if (cfg.version < 2) { ... }`, `if (cfg.version < 3) { ... }`). Then `cfg.version = SCHEMA_VERSION; SaveToDisk(cfg);`.
   - JSON exists + load FAILS → `cfg.Defaults()` ONLY in memory, do NOT overwrite file (admin may be editing with typo).

**Result:** server with old JSON performs transparent auto-upgrade → RPT shows `Migrating CrateConfig v1 -> v3` + JSON is resaved with new fields + didactic examples. Zero silent surprises.

## LBmaster preset integration: optional `#ifdef`
**Contract:** optional compile-time dependency. Do NOT add `LBmaster_Core` to `requiredAddons` of CfgPatches. Wrap ALL LB code in `#ifdef LBmaster_Core`. This way the mod compiles/runs on servers without LBmaster (with internal fallback) and uses LB when loaded.

**APIs read in the scripts of `LBmaster_Core`** (third-party mod behaviour, not vanilla; the line numbers belong to the version that was read and are not checked here):
- `LB_PresetBase.c:92` → `static void SpawnPresets(PlayerBase player, array<LB_PresetBase> presets, EntityAI parent, vector altPos = vector.Zero, float radius = 0.0)`
- `LB_PresetBase.c:138` → `void SpawnPreset(PlayerBase player, EntityAI parent, vector altPos = vector.Zero, float radius = 0.0)`
- `LB_PresetLoader.c:146` → `LB_PresetBase GetPreset(string name)` — null if not found.
- `LB_PresetLoader.c:189` → `array<LB_PresetBase> FindPresets(TStringArray arr)` — empty if nothing matches.
- `LBConfigLoader.c:6` → `static ref T1 Get;` — **static property, no parentheses**. Access: `LB_PresetLoader.Get.GetPreset(...)`, NOT `LB_PresetLoader.Get().GetPreset(...)`.

**Critical semantics:**
- `SpawnPreset` (instance, 1 preset) → enters directly into `minSpawnTries/maxSpawnTries` loop and **ignores the preset root chance** ⇒ guaranteed spawn.
- `SpawnPresets` (static, N presets) → **applies chance logic** (global weighted + individual) before spawning. With `individualChance = false` and chances < 1.0 it may spawn nothing.

## Loot resolution cascade — multi-tier pattern
For mods with multiple optional loot sources, recommended order in dispatcher:

1. **Tier 1 (most complex):** external system (LBmaster presets). Conditioned on admin toggle (`useLBPresets`). If framework not loaded or preset does not resolve → RPT warning + fallthrough to Tier 2.
2. **Tier 2 (medium):** native mod table with recursive nested attachments. If `lootTable.Count() == 0` → silent fallthrough to Tier 3.
3. **Tier 3 (simple):** flat list of classnames. Legacy. Empty → fallthrough to Tier 4.
4. **Tier 4:** no-op + RPT `All loot tiers empty -> crate broke without spawning any loot` (admin notices config is empty).

**Advantage:** admin moves up/down ladder depending on what they have on server. New mods do not break old JSONs (natural fallback). Admin without external framework still gets loot via Tier 2 or 3.
