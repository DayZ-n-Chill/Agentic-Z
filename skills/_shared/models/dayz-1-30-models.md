# DayZ 1.30 changes for models

What DayZ 1.30 changed for meshes, proxies, houses, wells, the model cache and the binarized model format, and what to check when you bring a 1.29 model forward. The LOD table, the py3d assembly path, the winding rules (`axes-and-winding.md`) and the artist return checks (`artist-returns.md`) are unchanged.

Some of these changes are stated only by the official 1.30 changelog (modding section) and show in no vanilla file; each one says so. The script lines are from the 1.30 scripts on `P:\scripts\`.

## What breaks for a 1.29 model or config

| Change | What to do | Section |
|---|---|---|
| An attachment proxy only in the visual LODs can be read at the parent's origin on a dedicated server | Add the proxy to View Geometry too | "Attachment proxies and View Geometry" |
| A custom well with `liquid_source` on some View Geometry components takes the liquid actions only there | Decide which part should take them | "`liquid_source` on a well" |
| Duplicate members inside one config class fail Binarize | Fix them before `/dayz-build-pbo` | |
| Mod models binarize as ODOL v56 | Update any ODOL reader you own | "Binarized models are ODOL v56" |
| Static houses that never need a tick | Consider `disableSimulation` | "`disableSimulation` on houses" |
| A loop on unbinarized `.p3d` files | Launch with `-cacheP3D=1` | "The `-cacheP3D` option" |
| Custom character or infected graphs | `.agf` through Workbench, not `model.cfg` | "Animation graphs" |

## Attachment proxies and View Geometry

Before 1.30, when the proxy triangle was missing from the last visual LOD, a dedicated server could report an inventory attachment at the parent's origin. Since 1.30 the server falls back to the View Geometry LOD. The changelog says: "Getting the position of an inventory attachment proxy on the server will now use the view geometry LOD to prevent getting the center of the parent object if the proxy was not defined in the final lod". This is stated only by the changelog; it is engine code, and no script names it, so do not invent an API for it.

Put the proxy triangle and its `proxy:...NNN` selection in View Geometry (`6.0e+15`) as well as in every visual LOD where it should show. View Geometry is the server's fallback, not a replacement for the visual proxies (`proxies.md`).

## The `-cacheP3D` option

Since 1.30, `-cacheP3D=0/1` writes `.p3dcache` files next to `.p3d` files so later launches of the game or Buldozer load unbinarized models faster (changelog only; no `.p3dcache` ships with the game). Use it on DayZDiag and Buldozer loops over MLOD models not yet packed by Addon Builder. The cache files sit beside the `.p3d` and never go into a release PBO. Launching is `/dayz-launch-test`.

## `disableSimulation` on houses

Since 1.30, house based entities take a `disableSimulation` config parameter that stops needless ticking on client and server (the changelog states what it does). The Takistan houses and props set it on the `Land_` class, next to `model`: `Land_House_1M2: HouseNoDestruct` (`P:\DZ\structures_takistan\Residential\config.cpp:1297`) and the well `Land_WaterWell_Brick: HouseDestructible` (`P:\DZ\structures_takistan\Props\config.cpp:22`). No vanilla config outside `P:\DZ\structures_takistan\` sets it (30 classes there). The script side is on `Entity` (`P:\scripts\3_game\entities\entity.c:1` to `:6`):

```c
class Entity extends ObjectTyped
{
	proto native void DisableSimulation(bool disable);

	//! Returns whether simulation is disabled
	proto native bool GetIsSimulationDisabled();
```

Prefer the config parameter, `disableSimulation=1;`, on static `House` classes that never need a tick, as the Takistan classes do; call `DisableSimulation(true)` only to switch it at run time.

## `liquid_source` on a well

The liquid actions on a well object (not a pond surface) look for the View Geometry components in a selection named `liquid_source`, through `UAMisc.LIQUID_SOURCE_SELECTION` (`P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:180`, in the `UAMisc` class at `:175` to `:181`, beside `FLAG_STEP_INCREMENT = 0.2` and `CONSUMPTION_SLOWDOWN_COEF_HOT = 5.0`). The callers, all in `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\`:

| Action | Line |
|---|---|
| Wash hands | `actionwashhandswell.c:38` |
| Drink | `actiondrinkwellcontinuous.c:54` |
| Wash head | `actionwashheadwell.c:38` |
| Fill bottle | `actionfillbottlebase.c:62` |
| Wet clothing | `actionwetclothinginhandswell.c:30` |

The selection narrows the action; it is not required. `CCTLiquid` (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:1`) accepts any component of a well when the model has no such selection. `GetActionComponentsForSelectionName` fills the list of selection components, and the aimed component is checked only when that list is not empty (`cctliquid.c:89` to `:92`). `ActionWashHandsWell` refuses only when the list is not empty and the aimed component is not in it (`actionwashhandswell.c:39`). A scan of the 10,626 `.p3d` files under `P:\DZ\` finds the name in three Takistan models, all with a `Well` script class: the brick well `P:\DZ\structures_takistan\Props\misc\waterwell_brick.p3d` (`Land_WaterWell_Brick : Well`, `P:\scripts\4_world\entities\building\land_waterwell_brick.c:1`) and the two cistern truck wrecks `wreck_truck01_aban1_cistern.p3d` and `wreck_truck01_aban2_cistern.p3d` under `P:\DZ\structures_takistan\Wrecks\wheeled\` (`P:\scripts\4_world\entities\building\wrecks\wreck_truck01_aban1_cistern.c:1`). Every other vanilla well uses the fallback.

Give a custom well or pump `liquid_source` on the View Geometry components of the spout when only that part should take wash, drink and fill, as the cistern wrecks do; leave it out and the whole well takes them. `CCTLiquid` reads the selection only when `IsWell()` is true, that is when `GetWaterSourceObjectType()` returns `EWaterSourceObjectType.WELL` (`P:\scripts\3_game\entities\object.c:664` to `:667`). Extending `Well` gives that and adds the well actions (`P:\scripts\4_world\entities\building\well.c:1`, `:8` to `:11` and `:23` to `:30`). A memory point of that name does nothing. Pond and sea surfaces go through `CCTLiquid` without it. The selection list of a well is in `building-selections.md`.

## Vegetation step sounds per object

1.30 adds `StaticObjectType`, which loads optional per object vegetation step sounds from `CfgNonAIVehicles <name> VegetationSounds` (`P:\scripts\3_game\entities\staticobjecttype.c:1` to `:15`):

```c
protected void LoadCustomStepSounds()
{
	string pathBase = "CfgNonAIVehicles " + GetName() + " VegetationSounds";
	if (!g_Game.ConfigIsExisting(pathBase))
		return;
```

The Takistan cactus bushes use it. From `P:\DZ\plants_takistan\config.cpp:14` to `:28`:

```cpp
class CfgNonAIVehicles
{
	class BushHard;
	class BushHard_b_OpuntiaFicusIndica_1s: BushHard
	{
		class VegetationSounds
		{
			class bush_walkErc
			{
				soundSet="cactus_walkErc_SoundSet";
				animEventIds[]={1,2,23,24,51,52};
			};
```

The class names and `animEventIds` match the survivor's generic set, its `VegetationSounds` class (`P:\DZ\characters\data\config.cpp:348`). The player looks up the plant's own sound for the step event first and falls back to the survivor's set when the plant has none (`P:\scripts\4_world\entities\dayzplayerimplement.c:3405` to `:3415`), so a mod plant only lists the events it wants to change. The sound sets are audio work for `dayz-audio-fx-specialist`.

## Animation graphs

Since 1.30, player and infected animation graph files use the Enfusion config format (`.agr` to `.agf`), the 250 bone global limit is gone, and `skeletons.anim.xml` is unused except its `lod` attribute (the changelog states the bone limit and the `.xml` change). On `P:\` the graph sheets now come as Enfusion `AnimSrcGraphFile` files (`P:\DZ\anims\workspaces\infected\infected_main\combat.agf`), with the old `$AnimGraph` sheets of the same name still beside them; the main graph keeps its `.agr` name, as an `AnimSrcGraph` file, and config still points at it (`graphname`, `P:\DZ\characters\zombies\config.cpp:74`). None of this touches object animation in `model.cfg` (`CfgSkeletons`, `CfgModels`; `_shared/animation/device-model-cfg.md`). Never convert an object's `model.cfg` to `.agf`. Character and infected graphs are in `_shared/animation/rtm-and-character-animation.md`.

## Unpacked mods

Since 1.30, `-mod` may point at a plain folder, configs are read unpacked, and each mod gets a named filesystem (changelog only). Changing `config.cpp` no longer always needs Addon Builder, unbinarized `.p3d` files still gain from `-cacheP3D`, and a Workshop release still ships a PBO.

## Binarized models are ODOL v56

With DayZ Tools for 1.30, Binarize writes mod models as ODOL v56, the version of the 1.30 vanilla models; earlier DayZ Tools wrote v55. The version is in bytes 4 to 7 of the file. Of the 10,626 vanilla models under `P:\DZ\`, 10,623 are v56 (for example `P:\DZ\gear\camping\wooden_case.p3d`) and three are still v54: `P:\DZ\vehicles\wheeled\offroad_02\proxy\offroad_02_body.p3d` and the two `wreck_offroad02_medic_tk_proxy` models under `P:\DZ\structures\wrecks\vehicles\proxy\`.

Read the version from the header before you open a model with an ODOL reader: a v54 reader fails on vanilla v56 with `ValueError: subsection not found`, and a v55 reader fails on your own v56 models.

What changed in the bytes, from comparing binarized files (not something one vanilla file shows):

- One MLOD binarized before and after the tools update: the first 205 bytes match except the version; v56 has 4 more zero bytes inside a run of zeros in the model info (34 instead of 30); the 8 LOD start and end offsets after it are 4 higher; nothing else differs.
- Where the 4 bytes sit: in 488 vanilla 1.30 models compared with their v54 files from an earlier game version, v56 has 4 zero bytes right after the float an ODOL reader reads as `ht_min`, before `ht_max`. In the pair above that float is the 1.0 at bytes 201 to 204, so the new bytes are 205 to 208. Five of the 488 have non zero floats there, which fixes the place. With the bytes removed, 471 match their v54 file past the skeleton up to one byte near the end of the model info; the other 17 already differ before `ht_min`. What the field holds is not known.
- Exact LOD ends do not prove the place: read after `shadow_buffer_source` instead, the 4 bytes still end every LOD exactly in 489 of 500 vanilla models but give different model info for 92 of them. The other 11, all animated (tents, locks, a spotlight, garden plots, `pepper_plant`), fail wherever the 4 bytes are read while their v54 files parse, so v56 changes something more in them that is not identified.
