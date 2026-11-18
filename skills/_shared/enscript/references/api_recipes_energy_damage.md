# Recipes, energy and damage

What a mod needs to extend three vanilla systems: crafting recipes (`RecipeBase` and `PluginRecipesManager`), the `ComponentEnergyManager`, and the path damage takes to reach an entity. Facts marked "measured in game" come from production mods and are not checked on `P:\`.

## Recipes

| Fact | Source |
|---|---|
| A recipe has exactly two ingredients, `MAX_NUMBER_OF_INGREDIENTS = 2`, and makes up to ten results, `MAXIMUM_RESULTS = 10` (`:2`) | `P:\scripts\4_world\classes\recipes\recipebase.c:1` |
| Ingredients are added with `InsertIngredient(index, classname)`. There is no `AddIngredient` and no `SetIsCacheable` anywhere under `P:\scripts` | `recipebase.c:159` |
| Recipes are registered in `RegisterRecipies()`. Vanilla spells it with `ies`; keep that spelling | `P:\scripts\4_world\classes\recipes\recipes\pluginrecipesmanagerbase.c:14` |
| The base `CanDo()` returns false when either ingredient has attachments | `recipebase.c:551` to `:560` |
| `m_ResultToInventory = -1` puts the result in the player's inventory. The branch for 0 and up (swap with an ingredient) has its body commented out, so it does nothing. Both branches are in `SpawnItems` (`recipebase.c:215`) | `recipebase.c:232` to `:251` |
| The result doesn't take the ingredient's health: `TransferItemProperties(ingr, res, true, true, false, false)` passes `false` for `transfer_health` (signature at `P:\scripts\4_world\static\miscgameplayfunctions.c:271`). Up to 1.29 it did, which could overwrite the health set by `m_ResultInheritsHealth` | `recipebase.c:353` |
| `PluginRecipesManager.GetRecipeClassName(int recipe_id)` is new in 1.30 | `P:\scripts\4_world\plugins\pluginbase\pluginrecipesmanager.c:84` |

Register a recipe from a modded manager:

```c
modded class PluginRecipesManagerBase
{
    override void RegisterRecipies()
    {
        super.RegisterRecipies();
        RegisterRecipe(new MyMod_Recipe);
    }
}
```

A recipe whose ingredient is a weapon or any item with attachments must override `CanDo()`. In that override, copy `ingredients[0]` and `ingredients[1]` to locals first and don't call `super.CanDo`. Measured in game: after that call the array read back held the same item in both slots, and the craft cancelled itself.

## The energy manager

| Fact | Source |
|---|---|
| A device has at most four sockets: `MAX_SOCKETS_COUNT = 4` | `P:\scripts\3_game\tools\component\componentenergymanager.c:73` |
| `energyStorageMax` is optional. With only `energyAtSpawn` in config, that value is also the maximum | `componentenergymanager.c:228` and `:229` |
| `ConsumeEnergy()` and `CanWork()` walk the chain of sources upwards, with a safety limit of 500 steps (`cycle_limit`) | `componentenergymanager.c:800` |
| With no `compatiblePlugTypes` in config, a socket accepts every plug | `componentenergymanager.c:994` |

The events to override are empty methods on `EntityAI`: `OnWorkStart()`, `OnWork(float consumed_energy)`, `OnWorkStop()`, `OnSwitchOn()` and `OnSwitchOff()` (`P:\scripts\3_game\entities\entityai.c:3428`, `:3431`, `:3434`, `:3437`, `:3440`). Measured in game: the switch events fire on both sides, while the work events fire only on the server and in single player. Anything clients must see goes through a synced variable and `SetSynchDirty()` (`../patterns/netsync.md`).

## Damage

| Fact | Source |
|---|---|
| `ProcessDirectDamage(damageType, source, componentName, ammoName, modelPos, damageCoef = 1.0, flags = 0)`: `componentName` is the damage zone, not a model component; the vanilla comment says "which 'DamageZone' was hit (NOT a component name, actually!)" (`:1128` to `:1137`). `damageCoef` multiplies the damage of the `CfgAmmo` class named by `ammoName` | `P:\scripts\3_game\entities\object.c:1138` |
| A vehicle hit is one such call: `RegisterTransportHit` passes the ammo `"TransportHit"` with the hit speed in m/s (`m_TransportHitVelocity.Length()`) as the coefficient | `P:\scripts\3_game\entities\entityai.c:4134` to `:4153` |
| `EEHitBy` runs on the server. `EEHitByRemote` runs only on the client that caused the hit | `entityai.c:1143` and `:1153` |
| Damage in a radius is `DamageSystem.ExplosionDamage(source, directHitObject, ammoTypeName, worldPos, damageType)`, for example `(source, null, ammo, pos, DamageType.EXPLOSION)`. There is no `ProcessIndirectDamage` in script | `P:\scripts\3_game\damagesystem.c:25` |
| `GetProtectionLevel(type, ...)` covers four hazard types only: `DEF_BIOLOGICAL`, `DEF_CHEMICAL`, `DEF_DUST_PARTICLE_BREATH`, `DEF_DUST_PARTICLE_EYES` (`P:\scripts\3_game\constants.c:547` to `:550`). Ballistic protection of clothing is config and engine work with no script call | `P:\scripts\4_world\entities\itembase.c:4077` |

`DecreaseHealth` changes health directly and skips this path, so no `EEHitBy`, hit animation or bleeding follows it (measured in game; the call is in `api_player.md`, section "Health").

Disease agents are not config classes. There is no `CfgAgents`; each agent is a script class registered with `RegisterAgent` in `PluginTransmissionAgents` (`P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:22`).

The vehicle hit, line by line, is in the physics pack: `_shared/physics/contact.md` (when and how hard the hit lands) and `_shared/physics/damage-pipeline.md` (from `ProcessDirectDamage` on). Actions and player sync are in `../depth/actions-and-player-sync.md`.
