# Vanilla deep dive: recipes, energy, actions, damage, player sync

Quick facts on five vanilla systems: recipes and crafting (`PluginRecipesManager`), `ComponentEnergyManager`, the action system, the damage pipeline, and player internals and sync. Every line cited as `P:\...:N` below was opened on `P:\` (1.30, game storage version 144).

### Recipes / crafting (PluginRecipesManager)
- `MAX_NUMBER_OF_INGREDIENTS = 2` (`P:\scripts\4_world\classes\recipes\recipebase.c:1`): recipes are physically limited to 2
  ingredients; `MAXIMUM_RESULTS = 10` (`:2`).
- Real API: `InsertIngredient(index, classname)` (`P:\scripts\4_world\classes\recipes\recipebase.c:159`). **`AddIngredient` does not exist** (no hit under `P:\scripts\`).
- The official typo is `RegisterRecipies()` (double i), declared at `P:\scripts\4_world\classes\recipes\recipes\pluginrecipesmanagerbase.c:14`. Mod pattern seen in production:
  `modded class PluginRecipesManagerBase { override void RegisterRecipies() { super.RegisterRecipies(); RegisterRecipe(new MyRecipe); } }`.
- Base `CanDo()` rejects ingredients with attachments (`P:\scripts\4_world\classes\recipes\recipebase.c:551-560`), so an override is required for recipes with
  weapons/items with attachments. An override copies `ingredients[0]` and `[1]` to locals first
  and does not call `super.CanDo`: measured in game, the array read back after that call held the
  same item in both slots and the craft cancelled itself (override rule 42 in `hard-rules.md`).
- `m_ResultToInventory`: only `-1` (to inventory) works; the body of the swap branch `>= 0` is commented out in `SpawnItems` (the `m_ResultToInventory` branches, `P:\scripts\4_world\classes\recipes\recipebase.c:232-251`). `SetIsCacheable` does not exist.
- (through 1.29: `TransferItemProperties` on a result with `m_ResultReplacesIngredient` could overwrite health from `m_ResultInheritsHealth`). (since 1.30: `TransferItemProperties(ingr, res, true, true, false, false)` is called, so `transfer_health = false`: `P:\scripts\4_world\classes\recipes\recipebase.c:353`. The signature of `TransferItemProperties` is at `P:\scripts\4_world\static\miscgameplayfunctions.c:269`. New: `PluginRecipesManager.GetRecipeClassName(int recipe_id)` at `P:\scripts\4_world\plugins\pluginbase\pluginrecipesmanager.c:84`.)

### ComponentEnergyManager (quick facts)
- `MAX_SOCKETS_COUNT = 4` hardcoded (`P:\scripts\3_game\tools\component\componentenergymanager.c:73`).
- `energyStorageMax` is optional: if you only define `energyAtSpawn`, that value acts as maximum (`P:\scripts\3_game\tools\component\componentenergymanager.c:228-229`).
- The energy chain is recursive: `ConsumeEnergy()`/`CanWork()` traverse sources upwards
  (safety limit: `cycle_limit = 500`, `P:\scripts\3_game\tools\component\componentenergymanager.c:800`).
- `OnSwitchOn/Off` fires on both sides; `OnWorkStart/OnWork/OnWorkStop` server/SP only, so real
  synchronization goes through `SetSynchDirty`. The empty hooks to override are on `EntityAI`: `OnWorkStart` at `P:\scripts\3_game\entities\entityai.c:3428`, `OnWork` `:3431`, `OnWorkStop` `:3434`, `OnSwitchOn` `:3437`.
- `compatiblePlugTypes` absent in config => the socket accepts all plugs (`P:\scripts\3_game\tools\component\componentenergymanager.c:994`).

### Action system (additions)
- `AddAction(typename)` in `SetActions()` registers **one shared instance per action class**
  (`ActionManagerBase.GetAction`), filed under its input type, so many actions share one input type
  (`P:\scripts\4_world\entities\itembase.c:255-290`) — there are no per-instance actions nor dynamic
  runtime registration.
- `CCTCursor` measures from the hit-pos of the `ObjIntersectView` raycast (requires View Geometry LOD);
  `CCTObject` measures from target's `GetPosition()`. If an action does not appear and the model lacks
  ViewGeo, check the LOD first (`skills/_shared/physics/collision-lods.md`).
- (through 1.29: CCT distance from hit-pos / `GetPosition()`, often via Head bone). (since 1.30: `CCTCursor` and `CCTCursorInherited` also measure from `MiscGameplayFunctions.GetPlayerHeadPosition`, which is stance height, not the Head bone: the `distanceHead` test at `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctcursor.c:35-36`, `fromPlayerHead` at `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctcursorinherited.c:28-32`, and `GetPlayerHeadPosition` itself at `P:\scripts\4_world\static\miscgameplayfunctions.c:776`. New `CCTLiquid` (constructor at `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:37`) replaces vanilla use of `CCTWaterSurfaceEx` in fill/drink/wash. `Can()` of a custom CCT does not change signature.)

### Damage pipeline (quick facts)
- `ProcessDirectDamage(damageType, source, componentName, ammoName, modelPos, damageCoef, flags)`
  (`P:\scripts\3_game\entities\object.c:1138`): `componentName` is the name of the **DamageZone**, not the model component.
- `damageCoef` multiplies the base damage of CfgAmmo. In vanilla `RegisterTransportHit`, the coef is the hit speed in m/s (`m_TransportHitVelocity.Length()`,
  `P:\scripts\3_game\entities\entityai.c:4134-4153`).
- `EEHitBy` is server-only; `EEHitByRemote` runs on the client that hit (`P:\scripts\3_game\entities\entityai.c:1143`, `:1153`). `DecreaseHealth` bypasses
  the pipeline (no EEHitBy/animation/bleeding).
- `ProcessIndirectDamage` does not exist in script (no hit under `P:\scripts\`); radius damage =
  `DamageSystem.ExplosionDamage(source, null, ammo, pos, DamageType.EXPLOSION)` (`P:\scripts\3_game\damagesystem.c:25`).
- `GetProtectionLevel` (`P:\scripts\4_world\entities\itembase.c:4073`) covers only `DEF_BIOLOGICAL`, `DEF_CHEMICAL`, `DEF_DUST_PARTICLE_BREATH` and `DEF_DUST_PARTICLE_EYES` (hazmat and dust; the constants are at `P:\scripts\3_game\constants.c:547-550`). Ballistic absorption of
  clothing is C++/config, with no script API.
- Full TransportHit flow line by line: `skills/_shared/physics/contact.md` (when and how hard the hit lands) and `skills/_shared/physics/damage-pipeline.md` (from `ProcessDirectDamage` on).

### Player internals — sync (quick facts)
- Stamina syncs via **SyncJuncture** (`SJ_STAMINA`), not via `SetSynchDirty`
  (`SyncStamina`, `P:\scripts\4_world\classes\staminahandler.c:831-839`). `EStaminaModifiers.PUSH_CAR` (`P:\scripts\3_game\enums\estaminamodifiers.c:13`) and `EStaminaConsumers.PUSH` (`P:\scripts\3_game\enums\estaminaconsumers.c:12`) already exist; use `DepleteStaminaEx` (`P:\scripts\4_world\classes\staminahandler.c:1144`) for custom costs.
- `eModifierSyncIDs`: on `P:\` nine bits are used, `0x1` to `0x100` (`MODIFIER_SYNC_PARTICLE_EYES` is `0x80`, `MODIFIER_SYNC_HEAT_STROKE` is `0x100`), so `0x200..0x80000000` are free for custom synchronized modifiers (enum `eModifierSyncIDs`, `P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:2-12`; at most 32 synced modifiers). An older game version used only seven bits, so older mods took `0x80` or `0x100`: both are taken now, do not use them.
- `PlayerStatsPCO` uses positional indices: a custom stat via `modded PlayerStatsPCO_current`
  needs index > 11 or it corrupts serialization: 1.30 added `THERMAL_BIAS` = 11 to `EPlayerStats_v130`
  (enum `EPlayerStats_v130`, `P:\scripts\4_world\classes\playerstats\playerstatspco.c:312-326`, `EPlayerStats_current` at `:356`), so a stat at 11, valid on 1.29
  (where the last index was 10), collides with it.
- Custom modifiers: `ModifiersManager` `Init()` hardcodes the list (`P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:90`), so the pattern is
  `modded class ModifiersManager`. `CfgAgents` does not exist (no hit under `P:\scripts\`): agents are script classes registered
  in `PluginTransmissionAgents` with `RegisterAgent` (`P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:22`).
