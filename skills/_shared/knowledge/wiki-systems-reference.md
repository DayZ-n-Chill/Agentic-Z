# DayZ gameplay, environment and server configuration reference

Covers the configuration systems of a DayZ server and mission: contaminated areas, weather, underground darkness, wildlife spawners, stamina and temperature keys, surfaces and clutter, server launch parameters, the diag menu, object and gear spawners, and the DayZ Tools licence limits.

Status: not yet checked on `P:\`, except the lines listed under "Checked on `P:\`" at the end. These are mission-file and server-config facts; the script tree on `P:\` cannot confirm most of them. Treat each data point as a lead until it is confirmed against the vanilla mission files (`cfggameplay.json`, the XML files) or the server you run.

**Guardrail**: before stating an Enforce Script or config identifier from this note as fact, confirm it on `P:\` or in Bohemia's official documentation. Third-party mirrors and fan wikis are leads only; `public-wiki-harvest.md` says how far each kind of page can be trusted.

## Standing errata (corrected or downgraded): do not reintroduce

- **`CfgStamina` is NOT a vanilla class.** Stamina, temperature and wetness are configured via
  **`cfggameplay.json` keys** and `globals.xml` `WorldWetTempUpdate`, not via a `CfgStamina` class.
  The stamina script is `P:\scripts\4_world\classes\staminahandler.c`.
- `StaminaHandler`, the environment script (`P:\scripts\4_world\classes\environment\environment.c`),
  `m_HeatComfort` and `UniversalTemperatureSource` are real vanilla script APIs, but they are not part of
  Bohemia's published configuration documentation. Read them on `P:\scripts`, not from a description of them.
- `vonCodecQuality` range **0–30**: the `serverDZ.cfg` shipped with the Steam DayZ Server says `(values 0-30)`
  (read 2026-11-09 on 1.30.164200). Ranges of 0–10 or 0–20 quoted elsewhere are wrong for that build.

## 1. Environment and hazards

- **Contaminated areas — `cfgEffectArea.json`** (mission folder; static NOT persistent,
  added/removed between restarts WITHOUT wipe). Structure: `"Areas"[]` with `AreaName`, `Type`
  (`ContaminatedArea_Static`), `TriggerType` (`ContaminatedTrigger`), `Data` (`Pos[x,y,z]` — Y≠0 = floating
  gas; `Radius`, `PosHeight`, `NegHeight`, `InnerRingCount`, `InnerPartDist`, `OuterRingToggle`,
  `ParticleName` e.g. `contaminated_area_gas_bigass`), `PlayerData` (`PPERequesterType`
  `PPERequester_ContaminatedAreaTint`). Many `Data` accept `-1`=default. **v1.28**: helper
  `FillWithParticles(pos, areaRadius, outwardsBleed, partSize, partId)` + **clamp 1000 emitters/zone**.
  Empty `{ }` = disables. (Particles → skill `dayz-particles`.)
- **Weather — `cfgweather.xml`** (mission folder; **XML not JSON**, see `environment-and-infra.md`). Root
  `<weather reset="0" enable="1">`. Elements `<overcast>/<fog>/<rain>/<wind>/<storm>` with children
  `<current actual= time= duration=>`, `<limits min= max=>` (0..1), `<timelimits>`, `<changelimits>`.
  `<rain>` + `<thresholds min= max= end=>`; `<wind><maxspeed>` m/s; `<storm density= threshold= timeout=>`.
  Mirrors the `Weather` script API. 3 weather avenues: scripted state machine
  (`WorldData::WeatherOnBeforeChange` in `Enoch.c`), `MissionWeather(true)`+API, or XML.
  Reported limitation, not yet checked: with the file active, weather tends toward extremes;
  reliable mainly to DISABLE weather.
- **Underground darkness — `cfgundergroundtriggers.json`** ("eye accommodation" 0=dark,1=normal).
  Outer/Transitional/Inner triggers + Breadcrumbs (points with radius and weight by proximity). Trigger:
  `Position`, `Orientation`, `Size`, `EyeAccommodation`, `Breadcrumbs[]`, `InterpolationSpeed`. Diag
  (v1.20+): `Script > Underground Areas > Show Breadcrumbs / Disable Darkening`. Working reference file:
  the one in the vanilla `dayzOffline.enoch` mission.

## 2. Wildlife / animal AI
- Ambient animal spawner = CE dynamic event (`db/events.xml`, events starting with `Animal`/
  `Infected`; `<child type="Animal_VulpesVulpes"/>`, `<territory>`, `<zone>`). Toggleable.
- Footstep sounds: macros `ANIMAL_STEP_SOUNDTABLE(Bird,Walk)` in Surfaces config.
- Fishing: **no official modding documentation exists**; treat anything read elsewhere as unverified. Fish/bait items in CE
  (`cfgspawnabletypes.xml`).

## 3. Player systems
- **Stamina** (`cfggameplay.json` defaults; the script constants behind three of them are under "Checked on `P:\`"): `staminaMax=100.0`,
  `staminaWeightLimitThreshold=6000.0`, `staminaKgToStaminaPercentPenalty=1.75`, `staminaMinCap=5.0`;
  modifiers (float, default 1.0): `sprintStaminaModifierErc/Cro`, `sprintSwimmingStaminaModifier`,
  `sprintLadderStaminaModifier`, `meleeStaminaModifier`, `obstacleTraversalStaminaModifier`,
  `holdBreathStaminaModifier`; `staminaDepletionSpeed=10.0`; `allowStaminaAffectInertia` (bool).
- **Temp/wetness** (`cfggameplay.json` + `globals.xml`): `environmentMinTemps[12]`,
  `environmentMaxTemps[12]` (monthly arrays), `wetnessWeightModifiers[1.0,1.0,1.33,1.66,2.0]` (5
  states DRY..DRENCHED). `WorldWetTempUpdate` (globals.xml, master toggle). Enable:
  `enableCfgGameplayFile=1` in serverDZ.cfg.
- **VOIP** (serverDZ.cfg): `disableVoN` (0/1), `vonCodecQuality` (0–**30**).

## 4. Surfaces / clutter / projection (terrain authoring — low reuse)
- **CfgSurfaces** derives `DZ_SurfacesInt`/`DZ_SurfacesExt` (`DZ_Surfaces` addon). Params: `files`,
  `friction`, `restitution`, `soundEnviron` (hard_ground/metal/wood/concrete/tyre/water…), `soundHit`,
  `character` (→`CfgSurfaceCharacters`, terrain only), `footDamage`, `audibility`, `isDigable`,
  `isFertile`, `impact`, `deflection`. Roadway flattens clutter except `DZ\data\data\surfaces\clutter.rvmat`.
  (`isDigable`/`isFertile` are also in the `dayz-physics-engine` skill.)
- **Grass-clutter**: single-sided model res LODs; wind via rvmat `plantWind[]={speed,stiffness,
  smoothness,light}` (stiffness 0 = static). Config `class Clutter` in `CfgWorlds` (model/scaleMin/
  scaleMax/noSatColor) + `clutterGrid`/`clutterDist`. NOT previewable in Buldozer with grass shader.
- **Projection Layer** (directional snow/moss, Sakhal): Supershader/Multishader params
  `multiTopProjectionLayer`, `degAngleTopProjectionStart/End`, `multiTopProjectionBlend`,
  `multiTopProjectionLayerNormal`; alpha of a `_CA` masks.
  (→ skill `dayz-texture-pipeline` if touched.)

## 5. Server — launch params and config (see also `environment-and-infra.md`)
- Core: `-config=`, `-port=` (2302 UDP), `-profiles=`, `-mission=` (absolute), `-mod=` (client+server,
  `;`-sep, absolute), `-serverMod=` (server only).
- `steamQueryPort = 2305;` in serverDZ.cfg — fix for "server not visible in browser" (set the
  key explicitly; "game port +1" is a myth). Does not contradict "2302 is UDP" (that is the game port, another thing).
- **`-par=<file>`** — reads params from a file (one option/line; supports C++ comments/#define). Fix for
  Windows **8192-char command-line limit** when stacking many mods.
  Useful when a launch stacks many mods (for example `@CF;@Dabs;@VPP;@<Mod>_deps;@DayZ_MCP…` with absolute paths). `[TBD-verify]`:
  not yet checked, and not in the official parameter documentation → test a `.par` before relying on it.
- Diag/logging: `-doLogs`, `-adminLog`, `-netLog`, `-freezeCheck`, `-filePatching`, `-cpuCount=`
  (≤ logical cores), `-limitFPS=` (cap, max 200). `priority.txt` (SteamIDs `;`-sep, login queue).
- BattlEye: `BEServer_x64.cfg` next to `BEServer_x64.dll`; `-bePath`; `RConPassword`, `RestrictRCon 1`.
  With `-profiles=` and no `-bePath`, the retail DayZServer 1.30.164289 (Windows, 2026-11-10) used
  `<profiles>/BattlEye/` (only `BEServer_x64.cfg` and `BEServer_x64.dll` there), left no
  `beserver_x64_active_*.cfg` copy and took `RConPort` from that cfg on every start (moved from 27331 to
  27332 between two runs, RCon listened on 27332).
- Linux server: `./DayZServer` binary (SteamCMD app 223350; client 221100; DayZ Tools 830640); mods by
  workshop ID via symlinks; NOT as root; systemd unit. Unresolved: Bohemia documents a native Linux
  server binary, while some hosts run the Windows server under a compatibility layer; check which one
  your host uses.

## 6. Diag menu / spawners (DayZDiag_x64)
- Diag: Win+Alt (or Ctrl+Win, conflicts with Win11). Categories: Statistics (Script Profiler flags
  SPF_RECURSIVE/RESET/NONE, modules CORE/GAMELIB/GAME/WORLD/MISSION; `-profile` forces), Enfusion
  Renderer/World, DayZ render, Game (Weather, Free Camera, Vehicles, Combat DE*, **Central Economy**
  debug: Loot Spawn Edit, Force Save, Dynamic Events…), AI (NavMesh/Pathgraph), Sounds.
  Do not rely on a `-debugweather` launch parameter: it is unconfirmed.
- **Object Spawner** (`spawnerData.json`, mission folder; requires cfgGameplay): static objects
  (pos+orient) at startup. Missing class → "Object spawner failed to spawn" in RPT.
- **Spawning Gear** (`cfgGameplay.json` → `PlayerData.spawnGearPresetFiles`): server-side override of
  spawn; presets with `spawnWeight`, `characterTypes` (`SurvivorM_Mirek`), `attachmentSlotItemSets`,
  `discreteUnsortedItemSets`. Total override of `StartingEquipSetup()`.

## 7. DayZ Tools licence limits (guardrail)
Assets built with **DayZ Tools are non-commercial** (DayZ Tools EULA); reuse of Bohemia game
data falls under the "Arma & DayZ Only, Noncommercial" terms; content cannot be behind a paywall
(voluntary donations, free content). Relevant to work that uses source-game rips and AI-generated
assets. Read Bohemia's current EULA and monetization rules before publishing.

## Cross-ref
- `skills/_shared/models/building-selections.md` — doors, ladders and LODs (the modelling side, checked against vanilla).
- `environment-and-infra.md` — operational server infra (launch, ports, BattlEye, allowFilePatching).
- `stardz-dzconfig-distill.md` — Central Economy files and `types.xml` semantics.
- Skills: `enforce-script-reference` (config.cpp, vanilla stamina APIs), `dayz-particles`,
  `dayz-texture-pipeline`, `dayz-physics-engine`.

## Checked on `P:\`

Opened on 2026-11-17. A line here confirms only what it says.

- Errata: no `CfgStamina` occurs anywhere in `P:\scripts`. The defaults behind the stamina keys are constants: `STAMINA_MAX` = 100 at `P:\scripts\3_game\constants.c:749`, `STAMINA_WEIGHT_LIMIT_THRESHOLD` = 6000 at `P:\scripts\3_game\constants.c:746` and `STAMINA_KG_TO_STAMINAPERCENT_PENALTY` = 1.75 at `P:\scripts\3_game\constants.c:732`.
- Errata: `m_HeatComfort` is a member at `P:\scripts\4_world\classes\environment\environment.c:97`, and `class UniversalTemperatureSource` is at `P:\scripts\3_game\systems\universaltemperaturesource\universaltemperaturesource.c:66`.
- Section 1: contaminated areas load from `$mission:cfgeffectarea.json` (`P:\scripts\4_world\classes\contaminatedarea\contaminatedarealoader.c:4`).
- Section 1: `FillWithParticles(vector pos, float areaRadius, float outwardsBleed, float partSize, int partId)` is declared at `P:\scripts\4_world\classes\contaminatedarea\effectarea.c:335`.
- Section 1: underground triggers load from `$mission:cfgundergroundtriggers.json` (`P:\scripts\3_game\undergroundarealoader.c:105`).
- Section 1: `class Weather` is declared at `P:\scripts\3_game\weather.c:167`, and the Livonia weather state machine overrides `WeatherOnBeforeChange` at `P:\scripts\4_world\classes\worlds\enoch.c:138`.
- Section 3: `cfggameplay.json` is read only when `enableCfgGameplayFile` is set (`P:\scripts\3_game\cfggameplayhandler.c:53`).
- Section 6: `spawnGearPresetFiles` is a member of the gameplay JSON data at `P:\scripts\3_game\cfggameplaydatajson.c:91`.
