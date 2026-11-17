# Config wiring and damage materials

How textures and materials are connected in `config.cpp`: hidden selection textures and materials, health level materials, and the vehicle light material pairs. The asset worker writes the files; the config entries belong to the worker who owns the item's class.

How to read it: a `P:\` citation was checked on the vanilla files. Blocks with `MyMod` paths are shapes to adapt, not vanilla text.

## Texture only: hidden selection textures

Use `hiddenSelectionsTextures[]` when only the color changes and the surface response stays the same.

```cpp
hiddenSelections[]=
{
	"camo"
};
hiddenSelectionsTextures[]=
{
	"MyMod\data\asset_co.paa"
};
```

- Check the selection name in the model and in the config before using it.
- Some selections show no geometry until a texture is assigned. One project's notes name `camoGround` as such a trap (a report, not checked on `P:\`). An empty string hides a selection on purpose: `_shared/textures/runtime-material-swaps.md`.

## Material swap through config

Use `hiddenSelectionsMaterials[]` when the material itself changes: specular, normal, emissive, glass or a damage look. The vanilla AKM sets both arrays, one entry per hidden selection, `hiddenSelectionsTextures[]` then `hiddenSelectionsMaterials[]` (`P:\DZ\weapons\firearms\akm\config.cpp:208-217`):

```cpp
hiddenSelectionsTextures[]=
{
	"dz\weapons\firearms\AKM\data\akm_co.paa",
	"dz\weapons\firearms\AKM\data\akm_co.paa"
};
hiddenSelectionsMaterials[]=
{
	"dz\weapons\firearms\AKM\data\AKM.rvmat",
	"dz\weapons\firearms\AKM\data\AKM_grip.rvmat"
};
```

The shape for a mod item:

```cpp
hiddenSelections[]=
{
	"camo"
};
hiddenSelectionsTextures[]=
{
	"MyMod\data\asset_co.paa"
};
hiddenSelectionsMaterials[]=
{
	"MyMod\data\asset.rvmat"
};
```

The arrays line up with the model's selections by position. Do not add a material path for a selection that does not exist.

## Damage and destruct health levels

`healthLevels[]` binds the normal, damaged and ruined materials. Each level lists one material per material the model uses. The vanilla AKM lists two per level, the body and the grip (`P:\DZ\weapons\firearms\akm\config.cpp:301-347`):

```cpp
healthLevels[]=
{
	{ 1, { "DZ\weapons\firearms\AKM\data\AKM.rvmat", "DZ\weapons\firearms\AKM\data\AKM_grip.rvmat" } },
	{ 0.69999999, { "DZ\weapons\firearms\AKM\data\AKM.rvmat", "DZ\weapons\firearms\AKM\data\AKM_grip.rvmat" } },
	{ 0.5, { "DZ\weapons\firearms\AKM\data\AKM_damage.rvmat", "DZ\weapons\firearms\AKM\data\AKM_grip_damage.rvmat" } },
	{ 0.30000001, { "DZ\weapons\firearms\AKM\data\AKM_damage.rvmat", "DZ\weapons\firearms\AKM\data\AKM_grip_damage.rvmat" } },
	{ 0, { "DZ\weapons\firearms\AKM\data\AKM_destruct.rvmat", "DZ\weapons\firearms\AKM\data\AKM_grip_destruct.rvmat" } }
};
```

For a mod asset:

- Keep the stage layout of the normal, damage and destruct materials the same.
- Change Stage3 to a damage or destruct macro texture (`rvmat-cookbook.md`, "Damage and destruct Stage3").
- Keep the Stage1 normal and the Stage5 `_smdi` unless the damage should change those maps too.
- Check that the class tree gives the asset a `DamageSystem`.
- The engine applies these materials when a health threshold is crossed, and that wipes a material a script set: `_shared/textures/runtime-material-swaps.md`.

## Vehicle light material pairs

Vehicles name on and off material pairs in config. The vanilla sedan sets `dashboardMatOn`, `dashboardMatOff`, `frontReflectorMatOn` and `frontReflectorMatOff` (`P:\DZ\vehicles\wheeled\config.cpp:14045-14048`):

```cpp
dashboardMatOn="dz\vehicles\wheeled\sedan_02\data\sedan_02_int2e.rvmat";
dashboardMatOff="dz\vehicles\wheeled\sedan_02\data\sedan_02_int2.rvmat";
frontReflectorMatOn="dz\vehicles\wheeled\sedan_02\data\sedan_02_chrome_e.rvmat";
frontReflectorMatOff="dz\vehicles\wheeled\sedan_02\data\sedan_02_chrome.rvmat";
```

When adapting:

- These keys are vehicle keys. Do not assume they work on another class.
- Clone the nearest vehicle family.
- Keep each on and off path as a pair and check every path against the packed files.

## Swaps from script

Prefer a config driven swap. When the behaviour has to come from script, read `_shared/textures/runtime-material-swaps.md` first: it lists the calls, the two index spaces, and what was measured on worn clothing. Check the call and the side (client or server) in the vanilla scripts before writing the code.
