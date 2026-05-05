---
name: dayz-p3d-audit
description: >
  Audit and fix DayZ .p3d model files for collision, action targeting, physics, animation,
  path, and structural issues. Runs py3d-based validation against known-working reference
  patterns. Also validates config.cpp and .rvmat files for path and property issues.
  Use this skill whenever: a DayZ mod object has no collision, actions don't appear,
  the player walks through placed objects, CCTObject raycasts miss, Geometry LOD seems
  ignored, a model was exported from Blender and doesn't work in-game, textures are
  missing, animations don't play, or the user says "review the p3d", "check the model",
  "audit collision", "why no actions", "flag/object has no collision", "audit the mod",
  "check paths", "validate the model". Also trigger when debugging any placed
  Inventory_Base item. This is the GO-TO skill for P3D and mod structure debugging.
---

# DayZ P3D Audit — Complete Model & Mod Validator

Validates .p3d model files, config.cpp, model.cfg, and .rvmat materials against
DayZ engine requirements. Built from production debugging where models rendered
correctly but had zero collision, missing animations, or broken textures.

## Preflight gate

Per the L2 rule (`.claude/skills/_shared/dayz-conventions.md`), every DayZ skill that does work gates on `/dayz-preflight` first. The audit reads `.p3d` files which can live anywhere, but the moment you point it at `P:\` paths or a built mod, an unmounted P-drive silently produces wrong results. Run `/dayz-preflight` before this skill.

## Quick Start

```bash
python <skill-path>/scripts/audit_p3d.py path/to/model.p3d [more.p3d ...]
```

For full mod audit including config and materials, also check sections below manually.

---

## PART 1: The 10 Silent P3D Killers

These produce ZERO engine errors but break functionality completely.

### 1. Inverted Face Winding (CRITICAL — Most Common from Blender)

Geometry LOD faces have normals pointing INWARD. Raycasts from outside pass through
without detecting collision — no collision, no action targeting, no physics.

**Root cause**: Blender Z-up → DayZ Y-up axis conversion flips triangle winding on
collision LODs while leaving the Visual LOD correct. The model looks perfect but is
physically invisible.

**Detection**: Cross-product of edge vectors must point AWAY from mesh center.

**Fix**: Swap `vertices[1]` and `vertices[2]` of each inverted face.

**Why Visual LOD isn't affected**: Visual and Geometry LODs have independent face data.
The renderer draws both sides; collision only detects the "front" face.

### 2. Component Selection Case Sensitivity (CRITICAL)

Geometry LOD component MUST be `Component01` (uppercase C). The engine string-matches
exactly. `component01`, `COMPONENT01`, or any variation silently fails — engine finds
zero components and ignores ALL collision geometry.

**Verified against**: a placed-device mod production placed-object models
all use `Component01`.

### 3. Missing `autocenter=0` LOD Property (CRITICAL for Inventory_Base)

For items with `autocenter=0` in config.cpp, the Geometry LOD MUST ALSO carry
`autocenter=0` as a named property. Config property controls the visual mesh;
LOD property controls the collision mesh. Without both, collision is displaced.

**Where**: Named property on Geometry (1e13), GeoPhys (2e13), FireGeo (3e13) LODs.
In py3d: `lod.properties['autocenter'] = '0'`

### 4. Missing Memory LOD or Geometry LOD (CRITICAL)

A P3D without a Memory LOD (res ~1e15) will have no animation, no bounding data, and
potentially crash the engine. A P3D without a Geometry LOD (res ~1e13) will have zero
collision and zero action targeting.

**Required LODs for any interactive DayZ object:**
- LOD 0: Visual (res=0.0) — rendering
- Memory (res ~1e15) — animation axes, bounding, interaction points
- Geometry (res ~1e13) — collision and cursor raycasting

**Recommended additional LODs:**
- GeoPhys (res ~2e13) — physics collision (player walking, vehicles)
- FireGeo (res ~3e13) — ballistic damage zones

### 5. Missing `pos center` Memory Point

Without `pos center`, the engine calculates bounding center from vertex distribution.
For tall/asymmetric objects (flagpoles where most vertices are in cloth at top), the
calculated center is far from the base — breaking the action targeting pre-filter.

**Fix**: Add `pos center` at `(0.0, 0.0, 0.0)` in Memory LOD for `autocenter=0` items.

### 6. Missing Animation Selections & Axes

If model.cfg defines an animation (like `flag_mast`), the P3D MUST have:
- **Visual LOD**: Named selection matching the animation selection name (e.g. `flag_mast`)
  covering all vertices/faces that should animate
- **Memory LOD**: Named selection matching the axis name (e.g. `flag_mast_axis`) with
  EXACTLY 2 points defining the animation axis (start and end of translation/rotation)

If either is missing, the animation silently does nothing.

### 7. Missing `box_placing_min` / `box_placing_max` Memory Points

For deployable objects using the hologram placement system, the Memory LOD needs:
- `box_placing_min` — single point at the minimum corner of the placement bounding box
- `box_placing_max` — single point at the maximum corner

Without these, the hologram collision check may malfunction (permanently block placement
or never detect terrain collision).

**Note (empirical, vanilla 1.x)**: This memory-point pair is a *fallback*. Vanilla
`hologram.c::GetProjectionCollisionBox` first calls `m_Projection.GetCollisionBox(min_max)`,
which returns the bbox derived from the Geometry LOD; only if that fails does it fall
back to `box_placing_*`. Vanilla deployables (`55galdrum`, `wooden_case`, `sea_chest`,
`MilitaryCrate` from a6_base_storage) ship `boundingbox_min/max` as Memory LOD selection
names — NOT `box_placing_*` — and rely on the Geometry LOD bbox. So this rule fires only
for items without a proper Geometry LOD or with broken `GetCollisionBox()` data.

### 8. Incomplete Component01 Coverage

`Component01` must include ALL vertices AND ALL faces of the Geometry LOD with weight=1.
Partial coverage means partial collision — some faces won't register raycasts.

### 9. Non-Watertight Collision Mesh

The Geometry LOD mesh must be closed (watertight) — every edge shared by exactly 2 faces.
Open meshes (with boundary edges/holes) cause unreliable collision where raycasts can
pass through gaps.

### 10. Missing Surface/Material Assignment on Collision LODs (CRITICAL)

Every face in the collision LODs (Geometry / GeoPhys / FireGeometry / ViewGeometry /
HitPoints) MUST have a `material` assigned, pointing to a penetration `.rvmat` that in
turn references a `.bisurf` file. Without this assignment, the engine raycasts hit the
geometry but cannot resolve a surface to consult — bullets pass through, footstep sound
is missing, and action cursor may not register.

Vanilla items always ship this — verifiable via `strings <p3d> | grep penetration`:

| Vanilla object   | Penetration material assigned             |
|------------------|-------------------------------------------|
| `55galdrum`      | `dz\data\data\penetration\metalplate.rvmat` + `metalPlate.bisurf` |
| `wooden_case`    | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `sea_chest`      | `dz\data\data\penetration\wood_desk.rvmat` + `wood_desk.bisurf` |
| `MilitaryCrate` (a6_base_storage) | `dz\data\data\penetration\plastic.rvmat` + `plastic.bisurf` |

Detection (py3d):
```python
for lod in p.lods:
    if lod.resolution in collision_lod_ranges:
        for face in lod.faces:
            assert (face.material or '') != '', f"face missing material in {lod_label}"
```

Fix: in Object Builder OR programmatically via py3d, set `face.material =
"dz\\data\\data\\penetration\\<surface>.rvmat"` for every face in every collision LOD
and write back. Visual LOD keeps its complex multi-stage `.rvmat` (e.g. `wooden_case.rvmat`)
unchanged — the penetration `.rvmat` is a SEPARATE simpler material used only by
collision LODs. Symptoms persist after binarization (ODOL preserves the empty
material), so this can be missed until in-game ballistic test.

---

## PART 2: Config.cpp Validation

### Baked-in P:\ Drive Paths (CRITICAL)

Absolute paths like `P:\DZ\gear\consumables\data\rag_co.paa` only exist on the
developer's machine. These MUST be converted to game-relative paths:

```cpp
// WRONG — breaks on any other machine:
hiddenSelectionsTextures[] = {"P:\DZ\gear\consumables\data\rag_co.paa"};

// CORRECT — works everywhere:
hiddenSelectionsTextures[] = {"DZ\gear\consumables\data\rag_co.paa"};
```

**Where to check**: `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`,
and any texture/material path in config.cpp.

**Exception**: Paths starting with `P:\` are valid ONLY during development on a
workbench with P: drive mounted. They must be stripped for distribution/PBO packing.

### Required Properties for Placed Objects

```cpp
class MyPlacedObject: Inventory_Base
{
    autocenter = 0;        // MANDATORY — prevents visual mesh burial
    model = "\ModName\data\model.p3d";  // Backslash prefix = addon root
    // For kits (handheld items): do NOT set autocenter=0
};
```

### AnimationSources Must Match model.cfg

If model.cfg defines animation `flag_mast` with `source = "flag_mast"`, config.cpp
MUST have a matching AnimationSources entry:

```cpp
class AnimationSources
{
    class flag_mast
    {
        source = "user";    // "user" = script-controlled
        animPeriod = 0.5;
        initPhase = 1;      // 0=up, 1=down for vanilla flag convention
    };
};
```

### hiddenSelections Must Match P3D

Every entry in `hiddenSelections[]` MUST have a matching named selection in the
Visual LOD of the P3D. Missing selections silently fail (no texture swap occurs).

---

## PART 3: Material (.rvmat) Validation

### P:\ Drive Paths in .rvmat Files

Same rule as config.cpp — `P:\` paths break on distribution:

```
// WRONG:
texture="P:\dz\gear\camping\data\flag_generic_nohq.paa";

// CORRECT (vanilla reference):
texture="dz\gear\camping\data\flag_generic_nohq.paa";
```

### Required Texture Stages

Standard DayZ .rvmat needs at minimum:
- Stage 0: Diffuse color texture (`_co.paa`)
- Stage 1: Normal map (`_nohq.paa`)
- Stage 2: Specular/detail map (`_smdi.paa`)

Missing stages produce engine warnings but don't crash.

---

## PART 4: Diagnostic Decision Tree

```
1. Can you SEE the object in-game?
   NO  → Check model path in config.cpp (backslash prefix, case)
   YES ↓

2. Is the object buried/floating?
   BURIED → Missing autocenter=0 in config.cpp AND/OR LOD property
   FLOATING → autocenter=0 on a kit class (only placed objects need it)
   CORRECT ↓

3. Does floating text (item name) appear near it?
   NO  → Entity not spawned. Check CreateObjectEx, server logs
   YES ↓

4. Do debug Print() in ActionCondition appear in script log?
   YES → ActionCondition rejecting. Read prints to find which check fails
   NO  ↓ (P3D Geometry LOD issue — engine can't raycast)

5. Run audit_p3d.py and check:
   a. Face winding outward?      → If inward: swap verts[1]/verts[2]
   b. Component01 uppercase C?   → If wrong case: rename
   c. autocenter=0 LOD property? → If missing: add
   d. pos center in Memory?      → If missing: add at (0,0,0)
   e. Component01 covers all?    → If partial: extend selection
   f. Mesh watertight?           → If open: close gaps
   g. Geometry LOD exists?       → If missing: create one

6. Animations not playing?
   → Check flag_mast selection in Visual LOD
   → Check flag_mast_axis (2 points) in Memory LOD
   → Check AnimationSources in config.cpp matches model.cfg

7. Textures missing/white?
   → Check P:\ paths in config.cpp hiddenSelectionsTextures
   → Check P:\ paths in .rvmat files
   → Verify .paa files exist at referenced paths
```

---

## PART 5: Common Blender Export Pitfalls

1. **Z-up → Y-up flips collision winding but not visual** — always verify Geometry LOD
   normals independently from Visual LOD
2. **Blender Geometry LOD may inherit `class=house`** from Object Builder templates
3. **py3d read-write cycles** preserve validity but change file size (~800 bytes per
   property change). This is normal.
4. **Addon Builder binarizes MLOD → ODOL** — all MLOD issues persist into builds
5. **Named selections are case-sensitive** in MLOD format. `Component01` ≠ `component01`
6. **Memory LOD must have zero faces** — only single-vertex points. Faces in Memory LOD
   may confuse the engine.
7. **Animation axis points must be in the SAME named selection** — both points of
   `flag_mast_axis` must be in one selection, not split across two.

---

## PART 6: Script-Side Gotchas

These aren't P3D issues but commonly co-occur during debugging:

- `IsTakeable()` MUST return `true` for `ActionManagerClient` to include the entity
  in the action targeting pipeline. Use `CanPutInCargo()=false` +
  `CanPutIntoHands()=false` + `RemoveAction(ActionTakeItem)` for non-pickup items.
- `SetFullyRaised()` in group creation → flags start at progress=1.0 → only
  `LowerFlag` appears initially, not `RaiseFlag` (checks `< 1.0`).
- SyncVar timing vs RPC cache timing can deadlock ActionConditions.
- `autocenter=0` on FlagKit (handheld) causes it to float when dropped — only set
  on placed objects, not kits.

---



---

## WINDING DIAGNOSTICS — Deep Methodology

Movido desde `DayZ Projects/CLAUDE.md` production-verified. Es el detalle de validación
de winding aprendido en producción con a production crate mod y a vanilla-overriding lamp mod. Complementa la
sección 1 ("Inverted Face Winding") con metodología de validación, trampas y
checklist completo de importación.

### Cómo NO verificar — heurísticas que engañan

⚠️ **Check centroid-based (`cross(e1, e2) · (face_centroid - LOD_centroid) > 0`):**
- Es **right-handed** (convención Three.js / OpenGL). DayZ es **left-handed**. Un modelo CORRECTO post-flip aparecerá como "winding inward" en ese check pero con normales declaradas outward — no es incoherencia, es el signo opuesto del cross product entre sistemas.
- Asume **geometría convexa** (compara contra el centroide del LOD). Para cajas huecas con paredes gruesas, caras interiores correctas se marcan como "invertidas".
- **Conclusión: NO SIRVE para validar winding DayZ absoluto.** El skill `dayz-p3d-audit` lo tuvo durante meses y producía hasta 100% de falsos positivos en modelos correctos. Solo vale para consistencia relativa antes/después de la MISMA operación, o comparado contra un vanilla de referencia.

⚠️ **Comparar `face.vertices[i].normal` con la cross product directamente NO funciona.** Las normales del pool `lod.facenormals` son per-vertex-corner suavizadas (smoothing groups): en faces planas coinciden con la flat normal; en faces suavizadas no. Para usarlas como referencia de "intent" hay que **promediar las normales de los 3-4 corners de UNA face** y compararlo con `cross(e1, e2)`. Ver Check A en `audit_p3d.py`.

⚠️ **Asumir que `lod.facenormals[i]` es el normal de `lod.faces[i]`.** Falso. `lod.facenormals` es un POOL global (tamaño = `num_facenormals` del header MLOD, **independiente** de `len(lod.faces)`); cada Vertex apunta a él vía `normal_index`. Confundirlos lleva a checks que nunca corren (length mismatch) o checks que comparan cosas incorrectas.

### Cómo SÍ verificar

1. **Check A — winding-vs-normal-promediada por face (DIAGNÓSTICO).** Para cada face, calcular `n_winding = normalize(cross(v1-v0, v2-v0))` y compararlo con el promedio normalizado de `face.vertices[i].normal` sobre los corners. El % de faces con `dot < -0.5` indica el estado de handedness:
   - **~100% UNIFORM_FLIPPED** → estado ESPERADO en DayZ (left-handed) tras export desde Blender (right-handed Z-up). El cambio de handedness invierte el cross product. **Verificado empíricamente con a production crate mod production-verified in-game: render/balas/cursor/colisión todo OK.** No action needed. → severity NOTE.
   - **~0% UNIFORM_NON_FLIPPED** → o no hay handedness transform o las normales se re-alinearon post-transform. Verificar in-game. → severity NOTE.
   - **5-95% MIXED** → bug real, render/colisión inconsistente entre faces. → severity CRITICAL.
   Coordinate-system-agnostic.

2. **Check B — topología edge-pair (LA MÁS FIABLE).** Dos caras manifold que comparten una edge deben recorrerla en direcciones opuestas. Si `face1` recorre `(A→B)` y `face2` también recorre `(A→B)` ⇒ una de las dos está flipped. Coordinate-system-agnostic. Independiente de la intención del modelador. **Mejor herramienta para detectar winding mixto post-flip.**

3. **Check C — comparación vs vanilla.** Matchear faces entre el target y un vanilla equivalente (ej. `DZ/gear/camping/wooden_case.p3d`) por proximidad de centroides, comparar winding-derived normals. Solo aplicable cuando hay un equivalente vanilla cercano en geometría.

4. **Test in-game directo.** Rebuild PBO → servidor de test → inspeccionar visual + collision + actions + ballistic. Es el último filtro y el único 100% definitivo. Cuando todo lo anterior diga "OK", igualmente probar in-game.

### Trampas conocidas (lessons learned)
- **`flip_winding.py` aplicado dos veces** vuelve al estado original (idempotente módulo 2). Si no recuerdas si lo aplicaste, mira si hay backup `.p3d.bak_v4_pre_winding_flip` — si existe, ya se aplicó al menos una vez.
- **`renegate_normals.py` es DEPRECATED** y basado en un malentendido. Si se aplicó, las normales del pool están negadas erróneamente; revertir negando otra vez. Ver "Scripts reutilizables".
- **a production crate mod tiene winding mixto en Visual LOD** (38.6% bad edges en Check B, production-verified) pero **DayZ lo tolera en render** (verificado in-game: visual / balas / cursor / colisión OK). Los collision LODs (Geometry/LandContact/ViewGeo/FireGeo) son internamente consistentes. **El skill marca esto como CRITICAL en Check B**, lo cual está bien como señal preventiva, aunque el motor lo aguante en este caso particular. No re-flipar este modelo a menos que aparezca un síntoma in-game concreto.
- **`face.flags |= 0x20000` (`NoBackfaceCulling`)** elude el problema en Visual LOD pero NO en collision LODs. Si lo usas en Visual, **sigue siendo obligatorio** arreglar el winding en Geometry/GeoPhys/FireGeo/ViewGeo.
- **`make_double_sided.py` complica Check B:** introduce edges no-manifold (3+ faces compartiendo edge), lo cual es correcto pero el check debe tratarlo como NOTE, no como CRITICAL.

### Checklist al importar un modelo nuevo de Blender
1. Abrir el .p3d con Object Builder o py3d. Listar LODs y resoluciones; confirmar que existen los requeridos (Visual=0, Geometry=1e13, Memory=1e15) y los recomendados (LandContact=2e15, ViewGeo=6e15, FireGeo=7e15) si el objeto interactúa con balas/cursor.
2. Aplicar `flip_winding.py`. Comprobar que crea backup `.bak_v4_pre_winding_flip`.
3. Correr Check A + Check B en TODOS los LODs (no solo Visual).
4. Si Check B reporta bad edges: identificar qué faces y o bien re-flipar selectivamente, o re-exportar desde Blender con configuración correcta. NO declarar el modelo "ready" con winding mixto.
5. Si todo limpio: rebuild PBO + test in-game (visual desde fuera, balas, acciones, walking through).
6. Solo después de pasar in-game, considerar el modelo "good".


## Bundled Script

`scripts/audit_p3d.py` performs all checks from Parts 1-3. Run on any MLOD .p3d file.
Install py3d: `pip install git+https://github.com/KoffeinFlummi/py3d.git`
