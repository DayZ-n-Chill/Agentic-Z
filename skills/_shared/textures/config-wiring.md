# Textures and materials in config

How `config.cpp` connects an item to its textures and materials: hidden selection textures, hidden selection materials, health level materials on a model with more than one material, and the light material pairs of a vehicle.

The asset worker writes the `.paa` and `.rvmat` files. The config entries belong to whoever owns the item's class; `rvmat-stages.md`, "Damage and destruct materials", says who. Blocks with `MyMod` paths are shapes to adapt, not vanilla text.

## A new color only: `hiddenSelectionsTextures[]`

When only the color changes and the surface responds the same way, swap the texture:

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

- Check that the selection name exists in the model and matches the config before you use it.
- An empty string hides a selection on purpose; see `runtime-material-swaps.md`. One texture per color is covered for clothing in `_shared/wearables/references/color-variants.md` and for vehicles in `vehicle-materials.md`.

## A new surface: `hiddenSelectionsMaterials[]`

When the material itself changes (highlight, relief, glow, glass or a damage look), swap the material too. The vanilla AKM sets both arrays, one entry per hidden selection, textures first (`P:\DZ\weapons\firearms\akm\config.cpp:208` to `:217`):

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

The same shape for a mod item:

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

The arrays match the model's selections by position. Never add a material path for a selection that does not exist.

## Health levels on a model with several materials

The single material case, three materials and which level gets which, is in `rvmat-stages.md`. When the model carries several materials, every level lists one path per material, always in the same order. The AKM lists the body and the grip at each level (`P:\DZ\weapons\firearms\akm\config.cpp:301` to `:347`):

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

- Keep the same stage layout in the pristine, damage and destruct materials.
- Put a damage or destruct macro texture in Stage3 (`rvmat-cookbook.md`, "Damage and destruct Stage3").
- Keep the Stage1 normal map and the Stage5 `_smdi` unless the damage should change them too.
- Check that the class tree gives the asset a `DamageSystem`.

## Vehicle light material pairs

Vehicles name an on and an off material for each lit part. The vanilla `Sedan_02` sets `dashboardMatOn`, `dashboardMatOff`, `frontReflectorMatOn` and `frontReflectorMatOff` (`P:\DZ\vehicles\wheeled\config.cpp:14045` to `:14048`):

```cpp
dashboardMatOn="dz\vehicles\wheeled\sedan_02\data\sedan_02_int2e.rvmat";
dashboardMatOff="dz\vehicles\wheeled\sedan_02\data\sedan_02_int2.rvmat";
frontReflectorMatOn="dz\vehicles\wheeled\sedan_02\data\sedan_02_chrome_e.rvmat";
frontReflectorMatOff="dz\vehicles\wheeled\sedan_02\data\sedan_02_chrome.rvmat";
```

- These are vehicle keys; don't expect them to work on another class.
- Start from the nearest vanilla vehicle family.
- Keep each on and off path together and check every path against the packed files.

Script reads each key by name and writes the material with `SetObjectMaterial` to a fixed index of `hiddenSelections[]`, not to a selection found by name; a key that is missing or empty is skipped (`P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c:77` to `:79`). On a `CarScript` the indexes are constants, `SELECTION_ID_FRONT_LIGHT_L` onwards (`P:\scripts\4_world\entities\vehicles\carscript.c:174` to `:182`), so the first nine names in `hiddenSelections[]` must be the light parts in this order, as the offroad hatchback lists them (`P:\DZ\vehicles\wheeled\config.cpp:1274` to `:1282`):

| Index | Selection on `OffroadHatchback` | Keys |
|---|---|---|
| 0 and 1 | `light_left`, `light_right` | `frontReflectorMatOn`, `frontReflectorMatOff` |
| 2 and 3 | `light_brake_1_2`, `light_brake_2_2` | `brakeReflectorMatOn`, `brakeReflectorMatOff` |
| 4 and 5 | `light_reverse_1_2`, `light_reverse_2_2` | `ReverseReflectorMatOn`, `ReverseReflectorMatOff` |
| 6 and 7 | `light_1_2`, `light_2_2` | `TailReflectorMatOn`, `TailReflectorMatOff` |
| 8 | `light_dashboard` | `dashboardMatOn`, `dashboardMatOff` |

The hatchback sets all ten keys (`config.cpp:1336` to `:1345`). A `MotorbikeScript` registers four indexes with `RegisterSelection` instead: 0 front, 1 brake, 2 tail and 3 dashboard (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:114` to `:122`). A car whose light selections sit elsewhere in the list gets its lit material painted on whatever part holds those indexes. `UpdateLights` runs the swap on every machine, not only on the server (`carscript.c:1853` to `:1859`).

## Swaps from script

Prefer a swap in config. When the change has to come from script, read `runtime-material-swaps.md` first: it lists the calls, their two index spaces, what health levels do to a material set from script, and what happens on worn clothing.
