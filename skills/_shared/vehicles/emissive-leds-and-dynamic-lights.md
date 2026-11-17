# Emissive LEDs, material swaps and dynamic lights

How to make an LED change colour and glow (a hidden selection, one `.rvmat` per state with `emmisive[]`, a swap from script) and how to make it also light the scene (a `PointLightBase` on a memory point).

> Status: a citation written with its full `P:\` path was opened on the vanilla data. The `emmisive[]` magnitudes recommended for a custom LED, the `SuperExt` row and the statement about Bohemia's DayZ-Samples materials are not yet checked on `P:\`. A vehicle's headlights, brake and reverse lights do not use this pattern since DayZ 1.30: they are `VehicleLightBase` entities registered on the lights component (`dayz-1-30-vehicles.md`, section 1), and the light material paths and hidden selection order of a car are in `lights.md`. The dashboard backlight swap (`dashboardMatOn` and `dashboardMatOff`) is in `materials-and-selections.md`.

## Vanilla anchors checked on `P:\`

- `SetObjectTexture` is declared at `P:\scripts\3_game\entities\entityai.c:2881`.
- `SetObjectMaterial` is declared at `P:\scripts\3_game\entities\entityai.c:2884`.
- `CreateLight` is a static method of `ScriptedLightBase`: `P:\scripts\4_world\entities\scriptedlightbase.c:227`.
- `AttachOnMemoryPoint` is declared at `P:\scripts\4_world\entities\scriptedlightbase.c:165`.
- `PointLightBase` extends `ScriptedLightBase`: `P:\scripts\4_world\entities\scriptedlightbase\pointlightbase.c:1`.
- A vanilla material spells the property `emmisive[]`: `P:\DZ\vehicles\wheeled\offroadhatchback\data\engine_niva.rvmat:4`.
- The same vanilla material uses `PixelShaderID="Super"`: `P:\DZ\vehicles\wheeled\offroadhatchback\data\engine_niva.rvmat:7`.
- Vanilla has an LED material of its own, and it glows with `emmisive[]={10,0.5,...}` on the `Super` shader: `P:\DZ\gear\tools\data\remotedetonator_led.rvmat:4` and `PixelShaderID="Super"` at `P:\DZ\gear\tools\data\remotedetonator_led.rvmat:7`.
- That LED material fills its first stages with procedural textures, for example the flat `NOHQ` normal `#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)`: `P:\DZ\gear\tools\data\remotedetonator_led.rvmat:11`.
- The `Normal` pixel shader with the `Basic` vertex shader also exists in vanilla, on the muzzle flash material: `PixelShaderID="Normal"` at `P:\DZ\data\data\zasleh.rvmat:11`.
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

`emmisive[]` is processed by the standard pixel-lighting pipeline regardless
of which shader runs. There is no "emissive-only" shader. Any shader that
runs the lighting formula (Super, Normal, Multi, Glass, NonTL, SuperExt,
NormalMap*, …) consumes the material's `emmisive[]` array. So the shader
choice is about **what texture stages you want**, not whether emission works.
Vanilla shows both ends: the remote detonator LED glows on `Super` with
seven stages, and the muzzle flash glows on `Normal`/`Basic` (see the anchors
above).

### Use the Super 7-stage pattern

Props and clothing in Bohemia's DayZ-Samples materials use `Super`/`Super`
with 7 stages, and the vanilla LED material does the same. There is no
separate emissive LED template: the template for any prop, including an LED,
is the Super 7-stage structure.

| Pattern | Shader | Stages | Recommendation |
|---------|--------|--------|----------------|
| **Super 7-stage** | `Super` + `Super` | **7 (NOHQ, DT, MC, AS, SMDI, fresnel, env)** | **Use this.** Even for a solid-color LED. |
| SuperExt Stage8-emissive | `SuperExt` + `SuperExt` | 8 stages, Stage8 = emissive map | Skip unless you author an emissive `.paa` mask and can test it in game. No material under `P:\DZ` uses `SuperExt`. |
| Normal/Basic minimal | `Normal` + `Basic` | 0 | The engine accepts it and vanilla uses it for the muzzle flash. Do not use it for a prop; migrate old files to the Super 7-stage pattern. |

### LED template — copy this

Fully procedural, no external `.paa` needed apart from the vanilla
environment map. Keep every stage.

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

### Two claims about shaders that are wrong

1. **"`Super` with procedural stages silently kills emission."** Wrong.
   The vanilla LED material is `Super` with procedural stages and
   `emmisive[]` of 10 on its peak channel
   (`P:\DZ\gear\tools\data\remotedetonator_led.rvmat:4`).
2. **"`Normal`/`Basic` with no stages is the reliable default."** Wrong
   for a prop. It works, because the engine still accepts the older
   shaders, but props use the Super 7-stage structure. A mod that carries
   `Normal`/`Basic` LED materials can be migrated by script: every stage
   present, the DT and SMDI colours matching `diffuse[]` and `specular[]`,
   the spelling correct.

Before generalising about a material structure, open a vanilla `.rvmat` of
the same kind on `P:\`. Accepted by the engine is not the same as what
vanilla does.

### If your LED renders black — debug order

1. **`emmisive[]` spelling.** Must be `emmisive` (two m's, no trailing s).
   Every vanilla material that sets it under `P:\DZ` spells it that way
   and none spells it `emissive[]`.
2. **`emmisive[]` magnitude.** For visible glow, peak channel ≥ 5. A
   subtle red-hot surface uses about `{0.85, 0.12, 0.02, 1}`; LEDs
   typically use `{60, 8, 8, 1}` or `{8, 60, 8, 1}` for a pronounced
   glow. Values < 1 look "dark-red/dark-green tinted matte," not lit.
3. **Power / sync state actually reaching the client.** Log the synced
   variable before blaming the material. A material that looks "black"
   because its entity never received the powered state is a networking
   bug, not a material bug.
4. **Selection index matches `hiddenSelections[]` position.** Off-by-one
   applies the rvmat to the wrong selection.
5. **Only then** suspect the file. If a Super material with procedural
   stages is not lighting on one model, the cause is a defect in that
   file (a malformed stage, a missing map-type hint, a UV problem on the
   target face), not the pattern.

### Spelling quirk — `emmisive`, not `emissive`

The property name is `emmisive[]` (two m's, no trailing s), a legacy
spelling kept for backward compatibility. `emissive[]` is silently
ignored (not yet checked on `P:\`; what is checked is that no vanilla
material uses that spelling).

### Legacy pattern to recognise — Normal/Basic with no stages

**Do not use this for new work.** It is here so you recognise it in
older mods. When you find it on a prop, migrate it to the Super 7-stage
template above.

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

### Textured emissive (when you have authored textures)

Same `Super` shader with all 7 stages, with the procedural placeholders
replaced by your `.paa` files where you have them. A stage you have no
texture for keeps its procedural placeholder from the template above.

```cpp
emmisive[] = {1, 1, 1, 1};           // modulates the texture
PixelShaderID  = "Super";
VertexShaderID = "Super";
class Stage1 { texture = "MyMod\data\led_nohq.paa"; … };   // normal map
class Stage2 { texture = "MyMod\data\led_co.paa"; … };     // diffuse
class Stage3 { texture = "MyMod\data\led_mc.paa"; … };     // macro
// … stages 4-7 as in the template
```

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

**RVMATs do not illuminate the environment.**
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

Turn the light off in `EEDelete` so you don't leak lights when the
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

- The 3D viewer (`scripts/tools/dayz-3d-viewer/`) — previews emissive RVMATs; its
  RVMAT reader takes the `emmisive` key.
- The dayz-ui-development skill — if the LED state is user-driven from a menu.
- The enforce-script-reference skill — SyncVars + OnVariablesSynchronized for state
  propagation.
