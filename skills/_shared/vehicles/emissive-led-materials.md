# Emissive LED materials

How to write the `.rvmat` for each LED state so it glows: which shader and stages to use, how strong `emmisive[]` must be, and what to check when an LED renders black.

The selection, the script swap and the scene light are in `emissive-leds-and-dynamic-lights.md`.

## Glow is a material value, not a shader

The `emmisive[]` array is read by the normal lighting formula whatever shader runs; there is no emission-only shader. Any lit shader (`Super`, `Normal`, `Multi`, `Glass`, `NonTL`, `SuperExt`, the `NormalMap` family) uses it. The shader choice decides which texture stages you get, not whether emission works.

Vanilla shows both ends. The remote detonator LED glows with `emmisive[]={10,0.5,...}` on `PixelShaderID="Super"` with procedural stages (`P:\DZ\gear\tools\data\remotedetonator_led.rvmat:4` and `:7`). The muzzle flash glows on `PixelShaderID="Normal"` with the `Basic` vertex shader (`P:\DZ\data\data\zasleh.rvmat:11`).

## Which pattern to use

| Pattern | Shaders | Stages | Use |
|---|---|---|---|
| Super with seven stages | `Super`, `Super` | NOHQ, DT, MC, AS, SMDI, fresnel, env | Use this, even for a plain coloured LED. |
| `SuperExt` with an emissive map in Stage 8 | `SuperExt`, `SuperExt` | Eight | Skip unless you author an emissive `.paa` mask and test it in game. No material under `P:\DZ` uses `SuperExt`. |
| Normal and Basic with no stages | `Normal`, `Basic` | None | The engine accepts it and vanilla uses it for the muzzle flash. Do not use it for a prop. |

The vanilla LED material uses the seven-stage Super layout, and so do prop and clothing materials generally; there is no separate LED template. That `Super` with procedural stages still glows is shown by the vanilla LED (`remotedetonator_led.rvmat:4`, peak channel 10). The claim that Bohemia's sample materials all use this layout is not checked on `P:\`.

## LED template

Fully procedural; the only file it needs is the vanilla environment map `P:\DZ\data\data\env_land_co.paa`. The flat normal in Stage 1 is the one the vanilla LED uses (`remotedetonator_led.rvmat:11`). Keep every stage.

```cpp
ambient[]       = {0.02, 0.15, 0.02, 1};
diffuse[]       = {0.05, 0.65, 0.05, 1};  // LED colour, 0 to 1
forcedDiffuse[] = {0.05, 0.65, 0.05, 1};
emmisive[]      = {8, 60, 8, 1};          // glow; peak channel 5 or more
specular[]      = {0.05, 0.45, 0.05, 1};
specularPower   = 20;
PixelShaderID   = "Super";
VertexShaderID  = "Super";
class Stage1    // NOHQ, flat normal
{
    texture = "#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage2    // DT, same RGB as diffuse
{
    texture = "#(argb,8,8,3)color(0.05,0.65,0.05,1,DT)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage3    // MC, no macro
{
    texture = "#(argb,8,8,3)color(0,0,0,0,MC)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage4    // AS, no occlusion
{
    texture = "#(argb,8,8,3)color(1,1,1,1,AS)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,0}; pos[]={0,0,0}; };
};
class Stage5    // SMDI, same RGB as specular
{
    texture = "#(argb,8,8,3)color(0.05,0.45,0.05,1,SMDI)";
    uvSource = "tex";
    class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,1}; };
};
class Stage6    // fresnel
{
    texture = "#(ai,64,64,1)fresnel(1.53,2.44)";
    uvSource = "none";
};
class Stage7    // environment reflection
{
    texture = "dz\data\data\env_land_co.paa";
    uvSource = "none";
};
```

For another colour, change `diffuse[]`, `forcedDiffuse[]`, `emmisive[]`, `specular[]` and the Stage 2 and Stage 5 colours together. For the off state set `emmisive[] = {0,0,0,1}`, dim the diffuse, and keep all seven stages.

With authored textures, keep the same shader and stages and put your `.paa` files in the stages you have (for example `led_nohq.paa` in Stage 1, `led_co.paa` in Stage 2, `led_mc.paa` in Stage 3), keeping the procedural placeholder in any stage you have no texture for. Set `emmisive[] = {1, 1, 1, 1}` so it scales the texture.

## Strength

- Peak channel 5 or more for visible glow. Pronounced LEDs use about `{60, 8, 8, 1}` or `{8, 60, 8, 1}`.
- Below 1 the LED looks like dark tinted matte, not lit. A faint red-hot surface uses about `{0.85, 0.12, 0.02, 1}`.
- At 50 or more the centre burns out to white with the colour around it, the classic lit LED look. Small indicators stay between 5 and 15.

These values are a starting point for a custom LED and are not checked on `P:\`.

## Spelling

Vanilla spells the key `emmisive`, two m's (`P:\DZ\vehicles\wheeled\offroadhatchback\data\engine_niva.rvmat:4`, a material on `PixelShaderID="Super"` at `:7`); keep that spelling. Every vanilla material under `P:\DZ` that sets it spells it that way and none uses `emissive[]`. That the engine ignores `emissive[]` is not checked on `P:\`.

## An LED that renders black

Check in this order:

1. The key is `emmisive`, not `emissive`.
2. The peak channel is 5 or more.
3. The power or sync state reaches the client. Log the synced variable before blaming the material; an entity that never received the powered state is a networking bug.
4. The selection index matches its position in `hiddenSelections[]`.
5. Only then suspect the file itself: a malformed stage, a missing map type suffix, or a UV problem on the target face.

## Older mods

Older mods often carry LED materials on `Normal` and `Basic` with no stages:

```cpp
// led_green.rvmat, the old pattern
emmisive[]      = {8, 60, 8, 1};
PixelShaderID   = "Normal";
VertexShaderID  = "Basic";
// no Stage classes
```

It works, but move such a prop to the seven-stage template: every stage present, the Stage 2 and Stage 5 colours matching `diffuse[]` and `specular[]`, and the key spelled `emmisive`. Before generalising about a material layout, open a vanilla `.rvmat` of the same kind on `P:\`; that the engine accepts a layout does not make it what vanilla does.
