# Emissive LEDs, material swaps and dynamic lights

How to make an LED change colour and glow (a hidden selection, one `.rvmat` per state with `emmisive[]`, a swap from script) and how to make it also light the scene (a `PointLightBase` on a memory point).

> Status: the `.rvmat` patterns and the audit of the DayZ-Samples repo were measured by the notes' author on a third-party mod (LFPG, LF PowerGrid) and are not yet checked on `P:\`. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. A vehicle's headlights, brake and reverse lights do not use this pattern since DayZ 1.30: they are `VehicleLightBase` entities registered on the lights component (`dayz-1-30-vehicles.md`, section 1), and the light material paths and hidden selection order of a car are in `lights.md`. The dashboard backlight swap (`dashboardMatOn` and `dashboardMatOff`) is in `materials-and-selections.md`.

## Vanilla anchors checked on `P:\`

- `SetObjectTexture` is declared at `P:\scripts\3_game\entities\entityai.c:2881`.
- `SetObjectMaterial` is declared at `P:\scripts\3_game\entities\entityai.c:2884`.
- `CreateLight` is a static method of `ScriptedLightBase`: `P:\scripts\4_world\entities\scriptedlightbase.c:227`.
- `AttachOnMemoryPoint` is declared at `P:\scripts\4_world\entities\scriptedlightbase.c:165`.
- `PointLightBase` extends `ScriptedLightBase`: `P:\scripts\4_world\entities\scriptedlightbase\pointlightbase.c:1`.
- A vanilla material spells the property `emmisive[]`: `P:\DZ\vehicles\wheeled\offroadhatchback\data\engine_niva.rvmat:4`.
- The same vanilla material uses `PixelShaderID="Super"`: `P:\DZ\vehicles\wheeled\offroadhatchback\data\engine_niva.rvmat:7`.
- The environment map of Stage 7 in the template below exists in vanilla: `P:\DZ\data\data\env_land_co.paa`.

## What this covers

Covers the full pipeline for LEDs that can change color, emit bloom (glow),
and optionally cast real light on the scene. DayZ runs a hybrid of Real
Virtuality (legacy) and Enfusion (new), so this touches three places at
once: the `.p3d` model, the `.rvmat` material + texture, and Enforce Script.

## 1. Prepare the model and config

For the engine to allow material swaps at runtime, the LED mesh must be a
**named Hidden Selection** on its own.

### In Object Builder (Oxygen 2)

Select the LED faces and assign them to a new Selection. Call it something
like `led_panel` (or `led_1`, `led_2`, … if you have multiple independent
LEDs).

### In `config.cpp`

Register that selection as hidden so scripts can target it by index:

```cpp
class YourCustomObject : ItemBase
{
    // Index 0 will map to "led_panel" in scripts
    hiddenSelections[] = {"led_panel"};

    // Default state (off)
    hiddenSelectionsTextures[] = {"YourMod\data\led_off_co.paa"};
    hiddenSelectionsMaterials[] = {"YourMod\data\led_off.rvmat"};
};
```

If you have multiple LEDs, add them in the same order to all three arrays
(`hiddenSelections`, `hiddenSelectionsTextures`, `hiddenSelectionsMaterials`).
Index is the array position.

## 2. Create the RVMATs and textures (bloom / glow effect)

To make something *visibly* glow, you need an emissive material. Create one
`.rvmat` per state/color (`led_red_on.rvmat`, `led_blue_on.rvmat`,
`led_off.rvmat`, …).

### Emissive is a MATERIAL property, not a shader feature

Key insight, verified against BI sources: `emmisive[]` is processed by
the standard pixel-lighting pipeline regardless of which shader runs.
There is no "emissive-only" shader. Any shader that runs the lighting
formula (Super, Normal, Multi, Glass, NonTL, SuperExt, NormalMap*, …)
consumes the material's `emmisive[]` array. So the shader choice is
about **what texture stages you want**, not whether emission works.

References consulted:
- BI-official [DayZ-Samples `gorka_normal.rvmat`](https://github.com/BohemiaInteractive/DayZ-Samples/blob/master/Test_ClothingRetexture/data/gorka_normal.rvmat) — canonical BI template.
- [dedmen Arma Shaders.yaml](https://gist.github.com/dedmen/90691e56c2dd77bc152ce0a48caf47ba) — authoritative shader ID table extracted from engine binaries.
- [zisb DayZ Emissive Tutorial](https://zi.sb/blog/Dayz_Emissive/) — DayZ-specific emissive guide.
- [armake issue #81](https://github.com/KoffeinFlummi/armake/issues/81) — confirms the `emmisive` spelling.

### Use the BI-canonical DayZ rvmat pattern. Period.

Authoritative finding after auditing **all 263 rvmats in BI's
DayZ-Samples** repo: **every single one** uses `Super`/`Super` + 7 stages
(for props/clothing) or a terrain-family shader (for terrain). **Zero**
BI DayZ rvmats use `Normal`/`Basic`. There is no DayZ-Samples emissive
LED template — BI's template for any prop, including LEDs, is the
Super 7-stage structure.

Therefore for a new rvmat in a DayZ mod:

| Pattern | Shader | Stages | BI-canonical DayZ? | Recommendation |
|---------|--------|--------|---------------------|----------------|
| **BI-canonical** | `Super` + `Super` | **7 (NOHQ, DT, MC, AS, SMDI, fresnel, env)** | ✅ Yes | **Use this.** Always. Even for a solid-color LED. |
| SuperExt Stage8-emissive | `SuperExt` + `SuperExt` | 8 stages, Stage8 = emissive map | ⚠ In engine shader table, not in DayZ-Samples | Skip unless authoring an emissive .paa mask and you have test coverage. |
| Normal/Basic minimal | `Normal` + `Basic` | 0 | ❌ Not in DayZ-Samples | Functional (engine accepts it) but non-canonical. Don't use. Migrate old files to BI-canonical. |

### BI-canonical LED template — copy this

Based on BI's [`gorka_normal_g.rvmat`](https://github.com/BohemiaInteractive/DayZ-Samples/blob/master/Test_ClothingRetexture/data/gorka_normal_g.rvmat)
(fully procedural, no external .paa needed), parameterized for an LED.
Every stage is mandatory — leaving any out means the rvmat is no longer
BI-canonical.

```cpp
ambient[]       = {0.02, 0.15, 0.02, 1};  // subtle ambient tint matching color
diffuse[]       = {0.05, 0.65, 0.05, 1};  // LED color (R,G,B = 0..1)
forcedDiffuse[] = {0.05, 0.65, 0.05, 1};  // usually same as diffuse for LEDs
emmisive[]      = {8, 60, 8, 1};          // GLOW intensity — ≥5 for visible bloom
specular[]      = {0.05, 0.45, 0.05, 1};  // spec tint (matches color)
specularPower   = 20;
PixelShaderID   = "Super";
VertexShaderID  = "Super";
class Stage1   // NOHQ — flat normal
{
    texture = "#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage2   // DT — diffuse/detail color (copy of diffuse RGB)
{
    texture = "#(argb,8,8,3)color(0.05,0.65,0.05,1,DT)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage3   // MC — no macro
{
    texture = "#(argb,8,8,3)color(0,0,0,0,MC)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage4   // AS — ambient shadow, full (no occlusion)
{
    texture = "#(argb,8,8,3)color(1,1,1,1,AS)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage5   // SMDI — specular (copy of specular RGB)
{
    texture = "#(argb,8,8,3)color(0.05,0.45,0.05,1,SMDI)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,1}; };
};
class Stage6   // Fresnel — standard glass-like
{
    texture = "#(ai,64,64,1)fresnel(1.53,2.44)";
    uvSource = "none";
};
class Stage7   // Environment reflection — vanilla DayZ path
{
    texture = "dz\data\data\env_land_co.paa";
    uvSource = "none";
};
```

For a red LED swap `diffuse[]` / `forcedDiffuse[]` / `emmisive[]` /
`specular[]` / Stage2 DT / Stage5 SMDI to red channels. For an **off**
state set `emmisive[] = {0,0,0,1}` and dim diffuse; keep all 7 stages.

### DO NOT fabricate claims about shader behavior without verifying against DayZ-Samples

Documented history of this file repeating mistakes (so they are not
repeated again):

1. **2026-04 (first)**: claimed `Super` + procedural stages "silently
   kills emission". **Wrong.** BI's own `gorka_normal.rvmat` uses exactly
   that pattern.
2. **2026-04 (second)**: recommended `Normal`/`Basic` + 0 stages as
   "the reliable default". **Wrong for DayZ.** Zero BI DayZ-Samples
   rvmats use that combo. It works (engine still accepts RV-era shaders)
   but it is not BI-canonical.
3. **Corrective action taken**: LFPG's 58 `Normal`/`Basic` files were
   migrated to the Super 7-stage template via a scripted audit. All 58
   pass structural verification (every stage present, DT/SMDI colors
   match diffuse/specular, spelling correct).

**Lesson: when advising on an Enfusion/DayZ rvmat structure, always
cross-check against an actual BI-authored DayZ-Samples rvmat before
generalizing. Engine-accepted ≠ BI-canonical.**

### If your LED renders black — debug order

1. **`emmisive[]` spelling.** Must be `emmisive` (two m's, no trailing s).
   `emissive[]` is ignored by the binarizer. Confirmed in every BI file
   and [armake issue #81](https://github.com/KoffeinFlummi/armake/issues/81).
2. **`emmisive[]` magnitude.** For visible glow, peak channel ≥ 5. The
   stove burner uses `{0.85, 0.12, 0.02, 1}` (subtle red hot); LEDs
   typically use `{60, 8, 8, 1}` or `{8, 60, 8, 1}` for a pronounced
   glow. Values < 1 look "dark-red/dark-green tinted matte," not lit.
3. **Power / sync state actually reaching the client.** Log the SyncVar
   before blaming rvmat. A material that looks "black" because its
   container entity never received `m_PoweredNet=true` is a networking
   bug, not a material bug.
4. **Selection index matches `hiddenSelections[]` position.** Off-by-one
   applies the rvmat to the wrong selection.
5. **Only then** consider swapping pattern. If B (Super+procedural)
   isn't lighting on a specific model, the issue is likely a
   file-specific defect (malformed Stage, missing map-type hint, UV
   problem on the target face) — not the pattern itself. Switching
   that one file to Pattern A sidesteps the risk surface without
   proving the pattern was at fault.

### Spelling quirk — `emmisive`, not `emissive`

The Bohemia property name is `emmisive[]` (two m's, no trailing s). This
is a legacy typo baked into Real Virtuality since OFP and preserved by
the binarizer for backward compatibility. `emissive[]` compiles but is
silently ignored. Verified in every BI-authored rvmat and the armake
binarizer source.

#### ⚠ Legacy reference only — Pattern A (Normal/Basic + 0 stages)

**Do not use this for new work.** Kept here only to recognize it in
older community mods. It's a valid engine shader combo inherited from
Real Virtuality, but NO BI DayZ-Samples rvmat uses it. When auditing
an older mod and you find this pattern, migrate it to the BI-canonical
Super 7-stage template above.

```cpp
// led_green.rvmat
ambient[]       = {0.02, 0.15, 0.02, 1};
diffuse[]       = {0.05, 0.65, 0.05, 1};
forcedDiffuse[] = {0.05, 0.65, 0.05, 1};
emmisive[]      = {8, 60, 8, 1};      // ← bloom intensity (green channel peaked)
specular[]      = {0.05, 0.45, 0.05, 1};
specularPower   = 20;
PixelShaderID   = "Normal";
VertexShaderID  = "Basic";
// NO class Stage1/Stage2/... — deliberately empty
```

Red variant: swap the RGB channels (`{60, 8, 8, 1}` for emissive, etc.).
Off variant: set `emmisive[] = {0, 0, 0, 1}` and dim diffuse.

#### Pattern B — Textured emissive (when you really have a texture)

> This subsection still says that procedural stages on the `Super` shader kill emission. The history
> above retracts that claim (item 1: BI's own `gorka_normal.rvmat` uses exactly that pattern), and the
> BI-canonical template above is the one to use. The text is kept as the notes had it.

`Super` shader with all 7 stages. Each stage must reference a **real** .paa
file, NOT a procedural `#(argb,8,8,3)color(...)` placeholder. Procedural
stages + Super shader is the trap that produces a black LED.

```cpp
emmisive[] = {1, 1, 1, 1};           // modulates texture; real brightness comes from _e.paa
PixelShaderID  = "Super";
VertexShaderID = "Super";
class Stage1 { texture = "MyMod\data\led_nohq.paa"; … };   // normal map
class Stage2 { texture = "MyMod\data\led_co.paa"; … };     // diffuse
class Stage3 { texture = "MyMod\data\led_mc.paa"; … };     // macro
// … stages 4-7 as vanilla
```

If you don't have authored .paa files for all slots, **use Pattern A**.
Don't fake them with `#(argb,8,8,3)color(...)` — the engine treats those
as invalid and silently kills emission on the Super shader path.

At very high `emmisive[]` values (≥50) the LED center goes white
(burnout) surrounded by the base color — classic LED-on look. For subtle
indicators stay in the 5–15 range.

## 3. Swap materials from Enforce Script

Once the mesh has the hidden selection and you have per-state RVMATs, the
in-game change is just `SetObjectTexture` + `SetObjectMaterial`. Call it
wherever your state changes (on var sync, on action, on tick, etc.). These
run both client and server in most code paths; if only the server mutates
state, make sure to sync it so every client re-applies the material in
`OnVariablesSynchronized`.

```c
class YourCustomObject extends ItemBase
{
    void SetLEDColor(string colorType)
    {
        // 0 == index of "led_panel" in hiddenSelections
        if (colorType == "RED")
        {
            SetObjectTexture(0, "YourMod/data/led_red_co.paa");
            SetObjectMaterial(0, "YourMod/data/led_red_on.rvmat");
        }
        else if (colorType == "BLUE")
        {
            SetObjectTexture(0, "YourMod/data/led_blue_co.paa");
            SetObjectMaterial(0, "YourMod/data/led_blue_on.rvmat");
        }
        else // off
        {
            SetObjectTexture(0, "YourMod/data/led_off_co.paa");
            SetObjectMaterial(0, "YourMod/data/led_off.rvmat");
        }
    }
}
```

## 4. CRITICAL — bloom ≠ real light

Modders run into this constantly: **RVMATs do not illuminate the environment.**
A high-`emmisive[]` material makes the LED glow on screen (bloom), but step
into a dark room and it won't light the walls or the player.

If you want the LED to also cast light:

- Instantiate a dynamic light from script (subclass `ScriptedLightBase` or
  `PointLightBase`).
- Attach it to a named memory point on the model so it stays glued to the LED
  as the object moves.

```c
PointLightBase m_LedLight;

void TurnOnRealLight(vector colorRGB)
{
    if (!m_LedLight)
    {
        m_LedLight = PointLightBase.Cast(
            ScriptedLightBase.CreateLight(PointLightBase, GetPosition())
        );
        // "led_memory_position" = memory point name in your .p3d
        m_LedLight.AttachOnMemoryPoint(this, "led_memory_position");
        m_LedLight.SetDiffuseColor(colorRGB[0], colorRGB[1], colorRGB[2]);
        m_LedLight.SetRadiusTo(2.0);   // metres
    }
}

void TurnOffRealLight()
{
    if (m_LedLight)
    {
        m_LedLight.FadeOut(0.2);
        m_LedLight = null;
    }
}
```

Clean up on `EEDelete` / `OnStoreSave` so you don't leak lights when the
object is removed.

## Action checklist

1. Split the LED faces into their own named selection in Object Builder.
2. Add that selection to `hiddenSelections[]` in config.cpp, with a default
   texture + RVMAT.
3. Author one RVMAT per desired state with `emmisive[]` > 1 for the "on"
   variants.
4. `SetObjectTexture` + `SetObjectMaterial` in Enforce Script to swap at
   runtime. Resync on client side after SyncVars.
5. Optional: spawn a `PointLightBase` attached to a memory point when you
   also need the LED to light up the scene.

## See also

- The 3D viewer (`scripts/tools/dayz-3d-viewer/`) — preview emissive RVMATs in Three.js (the notes say its
  RVMAT parser honors `emissive[]`; check which spelling it reads before relying on a preview).
- The dayz-ui-development skill — if the LED state is user-driven from a menu.
- The enforce-script-reference skill — SyncVars + OnVariablesSynchronized for state
  propagation.
