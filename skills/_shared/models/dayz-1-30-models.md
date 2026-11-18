# DayZ 1.30: what changed for models

What game version 1.30 changes for meshes, proxies, houses, wells and the model cache. The LOD resolution table, the py3d assembly path, the winding rules (`axes-and-winding.md`) and the artist return preflight (`artist-returns.md`) hold unchanged. Each note says what held until 1.29 and what holds since 1.30.

How to read the evidence labels: `[EXACT]` is read from a vanilla file or measured, `[CHANGELOG]` is stated only by the official 1.30 experimental changelog (modding section), `[DESIGN]` is a rule this skill derives from the two, and `[UNVERIFIED]` could not be confirmed. Script line numbers are those of the vanilla scripts on `P:\scripts\` (stable 1.30), opened to confirm each one.

## What breaks for a 1.29 mesh or config

1. An attachment proxy that sits only in the Resolution LODs can be read at the parent's origin on a dedicated server.
2. A custom well with a `liquid_source` selection on only some View Geometry components takes the liquid actions only on those components (see below; with no such selection the whole well still works).
3. Duplicate members inside one config class now fail binarize. The build side of that is `/dayz-build-pbo`.

## Inventory attachment proxy position on a dedicated server

Until 1.29: if the proxy triangle was missing from the final visual LOD, a dedicated server could report the attachment at the parent origin (the mesh center). Since 1.30 `[CHANGELOG]`: the server falls back to the View Geometry LOD to read the inventory attachment proxy position.

The official changelog says:

> Fixed: Getting the position of an inventory attachment proxy on the server
> will now use the view geometry LOD to prevent getting the center of the
> parent object if the proxy was not defined in the final lod

`[DESIGN]` Duplicate the proxy triangle and its `proxy:...NNN` selection in the View Geometry LOD (`6.0e+15`), not only in the Resolution LODs. The visual LOD requirement stays (`_shared/models/proxies.md`); View Geometry is now the server side fallback, not a substitute for the visual proxies.

No Enforce Script call site names this LOD fallback: it is engine code. Do not invent an API for it.

## `-cacheP3D=0/1` and `.p3dcache` next to unbinarized meshes

Since 1.30 `[CHANGELOG]`:

> Added: '-cacheP3D=0/1' command line launch option, creates .p3dcache files
> next to .p3d files to allow for quicker subsequent launches of the
> Game/Buldozer when working with unbinarized assets

`[DESIGN]` Use it on DayZDiag and Buldozer loops that iterate over MLOD `.p3d` files (not yet binarized by Addon Builder). The cache files are siblings of the `.p3d`; they are not packed into a shipping PBO. No `.p3dcache` file ships in the vanilla data, so the flag is known from the changelog only.

The launch arguments belong to the in-game test step (`/dayz-launch-test`).

## `disableSimulation` on house based entities

Since 1.30 `[CHANGELOG]`:

> Added: 'disableSimulation' config parameter to house-based entities to
> eliminate unnecessary entity ticking impacting client/server performance

Script API on `Entity`, `[EXACT]`:

```
// P:\scripts\3_game\entities\entity.c:1-6
class Entity extends ObjectTyped
{
	proto native void DisableSimulation(bool disable);

	//! Returns whether simulation is disabled
	proto native bool GetIsSimulationDisabled();
```

`[UNVERIFIED]` No vanilla `config.cpp` was found with a `disableSimulation = 1;` line. The config key is engine side; the script natives are exact. Prefer the config parameter on static `House` classes that never need a tick, and call `DisableSimulation(true)` only when toggling at runtime.

## Selection `liquid_source` (wells)

Since 1.30 the liquid actions that target a well object (not a pond surface) look up the View Geometry components that belong to a selection named `liquid_source`:

```
// P:\scripts\4_world\classes\useractionscomponent\actions\actionconstants.c:175-181
class UAMisc
{
	const float FLAG_STEP_INCREMENT = 0.2; //0..1
	const float CONSUMPTION_SLOWDOWN_COEF_HOT = 5.0;
	
	const string LIQUID_SOURCE_SELECTION = "liquid_source";
};
```

Call sites, all asking for the View Geometry level with `UAMisc.LIQUID_SOURCE_SELECTION`: `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashhandswell.c:38`, `actiondrinkwellcontinuous.c:54`, `actionwashheadwell.c:38`, `actionfillbottlebase.c:62`, `actionwetclothinginhandswell.c:30` in the same folder, and `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:89`.

The selection narrows the action; it is not required. `CCTLiquid` accepts any component of a well when the model has no such selection, and only when it has one must the aimed component be in it (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:89` to `:94`: `componentIndices.Count() > 0` checks the aimed component, otherwise `isValidInteract = true`). `ActionWashHandsWell` rejects only when the list is not empty and the aimed component is missing from it (`actionwashhandswell.c:39`). No vanilla model under `P:\DZ\` stores the name `liquid_source` (scan of all 8,256 `.p3d` files), so vanilla wells run on the fallback.

`[DESIGN]` Give a custom well or pump a `liquid_source` named selection on the View Geometry components of the spout when only that part should take wash, drink and fill. Leave it out and the whole well takes them. A memory point is not what the actions read. Pond and sea surfaces go through `CCTLiquid` without this selection.

## `StaticObjectType` and `CfgNonAIVehicles` `VegetationSounds`

Since 1.30 there is a new type class that loads optional per object vegetation step sounds from config:

```
// P:\scripts\3_game\entities\staticobjecttype.c:1-15
class StaticObjectType : EntityType
{
	//may not contain every soundset info, defaults from DayZPlayerType used in that case
	protected ref map<int, ref SoundObjectBuilder> m_CustomVegetationSoundsMap; //<stepEventID, SoundObjectBuilder>
	
	void StaticObjectType()
	{
		LoadCustomStepSounds();
	}
	
	protected void LoadCustomStepSounds()
	{
		string pathBase = "CfgNonAIVehicles " + GetName() + " VegetationSounds";
		if (!g_Game.ConfigIsExisting(pathBase))
			return;
```

The vanilla player vegetation sounds live on the survivor class, not in `CfgNonAIVehicles`:

```
// P:\DZ\characters\data\config.cpp:348-354
		class VegetationSounds
		{
			class bush_walkErc
			{
				soundSet="bush_walkErc_SoundSet";
				animEventIds[]={1,2,23,24,51,52};
			};
```

`[UNVERIFIED]` The only vanilla `config.cpp` under `P:\DZ\` with a `class VegetationSounds` is that one, so no shipped bush or tree shows the `CfgNonAIVehicles` form. The loader path is exact. Writing the sound sets is audio work (`dayz-audio-fx-specialist`).

## Animation graphs `.agr` to Enfusion `.agf` (not `model.cfg`)

`_shared/animation/model-cfg-device-examples.md` covers `model.cfg` object animation (`CfgSkeletons` and `CfgModels`). It has nothing to do with `.agr` files, a 250 bone cap or `skeletons.anim.xml`: those belong to the player and infected animation graph.

Since 1.30 `[CHANGELOG]`: animation graph files use the Enfusion config format, the 250 global bone limit is removed, and most of `skeletons.anim.xml` is unused except its `lod` attribute.

The `model.cfg` contract of a generated object does not change. Do not convert an object's `model.cfg` to `.agf`. Character and infected graph ports are character animation work (`_shared/animation/rtm-and-character-animation.md`).

## Unpacked mods and the named filesystem

Since 1.30 `[CHANGELOG]`: `-mod` may point at a physical folder, RV configs are read unpacked, and each mod gets a named filesystem. Iterating on `config.cpp` no longer always needs Addon Builder. Unbinarized `.p3d` files still benefit from `-cacheP3D`. A Workshop release still packs a PBO. Launching is `/dayz-launch-test`.

## Models you binarize are ODOL v56 (DayZ Tools 1.30.164.078)

Until the DayZ Tools update of 2026-10-15, `binarize.exe` wrote mod models as ODOL v55. Since DayZ Tools Steam build 25460346 (installed 2026-10-15 21:47 UTC, `binarize.exe` 1.30.164.078) they come out as ODOL v56, the version of the 1.30 vanilla models.

Checked on `P:\`: the version sits in bytes 4 to 7 of the file, and of the 8,256 vanilla models under `P:\DZ\`, 8,253 are v56 (for example `P:\DZ\gear\camping\wooden_case.p3d`) and three are still v54: `P:\DZ\vehicles\wheeled\offroad_02\proxy\offroad_02_body.p3d` and the two `wreck_offroad02_medic_tk_proxy` models under `P:\DZ\structures\wrecks\vehicles\proxy\`. The two blocks below are byte comparisons of binarized files; they are not vanilla facts that a single file on `P:\` shows.

`[EXACT]` One MLOD binarized by Addon Builder before and after that update: the first 205 bytes are equal except the version (bytes 4 to 7); the v56 file has 4 more zero bytes inside a run of zeros in the model info (30 bytes in v55, 34 in v56); the 8 LOD start and end offsets after it are 4 higher; nothing else differs. A reader written for v55 fails on the v56 file.

`[EXACT]` Where the 4 bytes sit, which that pair cannot tell: in 488 vanilla 1.30 models, each compared byte by byte with the v54 file of the same model from an earlier game build, the v56 file has 4 zero bytes right after the float an ODOL reader reads as `ht_min`, before the one it reads as `ht_max`; with them removed, 471 match their v54 file past the skeleton, until the v56 file has one byte more where the reader ends the v54 model info (in 102 the difference shows one byte before that end, in 5 one byte after it), and the other 17 already differ before `ht_min`. In the pair above that float is the 1.0 at bytes 201 to 204, so the new bytes are 205 to 208. Five of the 488 have non zero floats there and fix the place; in the others a run of zeros would let it slide. What the field holds is not known. LOD ends that come out exact do not prove the place: read after `shadow_buffer_source` instead, the 4 bytes still end every LOD exactly in the same 489 of 500 vanilla models, but give different model info values for 92 of them. The other 11, all animated (tents, locks, a spotlight, garden plots, `pepper_plant`), fail wherever the 4 bytes are read while their v54 files parse, so v56 changes something more in them; what, is not identified.

Before reading a vanilla 1.30 model or one of your own with an ODOL reader, read the version from the header: a v54 reader fails on vanilla v56 with `ValueError: subsection not found`, and a v55 reader fails on your v56 models.

## Migration checklist (model and config)

- [ ] Inventory attachments: proxy triangle and `proxy:...NNN` selection in the visual LODs and in View Geometry.
- [ ] Custom well or pump: decide whether the whole well or only a `liquid_source` selection on View Geometry takes the liquid actions.
- [ ] Static houses with no tick: consider `disableSimulation` (config key `[CHANGELOG]`; script toggle `Entity.DisableSimulation`).
- [ ] Unbinarized mesh loop: `-cacheP3D=1` on DayZDiag and Buldozer.
- [ ] Duplicate members inside one config class now fail binarize: fix them before `/dayz-build-pbo`.
- [ ] Custom character or infected graphs: `.agf` through Workbench, not this pipeline and not `model.cfg`.
- [ ] Your own ODOL tooling (debinarizers, parity checks) must read v56 before it reads a model binarized by DayZ Tools 1.30.164.078. Later builds were not measured: read the version in bytes 4 to 7 of each model before choosing a reader.
