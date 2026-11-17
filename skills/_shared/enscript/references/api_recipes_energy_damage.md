# Reference: recipes, the energy manager and the damage pipeline

Quick facts on three vanilla systems that mods often extend: crafting recipes (`RecipeBase` and `PluginRecipesManager`), `ComponentEnergyManager`, and how damage reaches an entity. Every line cited as `P:\...:N` was opened on `P:\`; anything marked "reported" was measured in game and not re-run here. More depth on the same systems is in `skills/enforce-script-reference/references/vanilla-deep-dive.md`.

## Recipes

| Fact | Source |
|---|---|
| A recipe has exactly two ingredients: `MAX_NUMBER_OF_INGREDIENTS = 2`. It can make up to ten results (`MAXIMUM_RESULTS = 10`, `:2`). | `P:\scripts\4_world\classes\recipes\recipebase.c:1` |
| Ingredients are added with `InsertIngredient(index, classname)`. There is no `AddIngredient`. | `P:\scripts\4_world\classes\recipes\recipebase.c:159` |
| Recipes are registered in `RegisterRecipies()` (vanilla's spelling, with `ies`). | `P:\scripts\4_world\classes\recipes\recipes\pluginrecipesmanagerbase.c:14` |
| The base `CanDo()` returns false when either ingredient has attachments. | `P:\scripts\4_world\classes\recipes\recipebase.c:551-560` |
| `m_ResultToInventory`: `-1` puts the result in the player's inventory. The body of the branch for values of 0 and up (swap with an ingredient) is commented out, so it does nothing. | `P:\scripts\4_world\classes\recipes\recipebase.c:232-251` |
| Since 1.30 the result no longer takes the ingredient's health through `TransferItemProperties`: the recipe passes `false` for the health argument. | `P:\scripts\4_world\classes\recipes\recipebase.c:353` |
| `GetRecipeClassName(int recipe_id)` is new in 1.30. | `P:\scripts\4_world\plugins\pluginbase\pluginrecipesmanager.c:84` |

A mod registers its recipe from a modded manager:

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

A recipe whose ingredient is a weapon or another item with attachments must override `CanDo()`. Reported: in such an override, copy `ingredients[0]` and `ingredients[1]` to locals first and do not call `super.CanDo`; after that call the array read back held the same item in both slots and the craft cancelled itself.

## ComponentEnergyManager

All in `P:\scripts\3_game\tools\component\componentenergymanager.c`:

| Fact | Source |
|---|---|
| A device has at most four sockets: `MAX_SOCKETS_COUNT = 4`. | `P:\scripts\3_game\tools\component\componentenergymanager.c:73` |
| `energyStorageMax` is optional. With only `energyAtSpawn` in config, that value is also the maximum. | `P:\scripts\3_game\tools\component\componentenergymanager.c:228-229` |
| The energy chain is walked upwards through the sources, with a safety limit of 500 steps (`cycle_limit`). | `P:\scripts\3_game\tools\component\componentenergymanager.c:800` |
| With no `compatiblePlugTypes` in config, a socket accepts every plug. | `P:\scripts\3_game\tools\component\componentenergymanager.c:994` |

The events to override are empty methods on `EntityAI`: `OnWorkStart()`, `OnWork(float consumed_energy)`, `OnWorkStop()` and `OnSwitchOn()` (`P:\scripts\3_game\entities\entityai.c:3428`, `:3431`, `:3434`, `:3437`). Reported: the switch events fire on both sides, while the work events fire on the server and in single player only, so what clients must see goes through a synced variable and `SetSynchDirty()` (`../patterns/netsync.md`).

## Damage

| Fact | Source |
|---|---|
| `ProcessDirectDamage(damageType, source, componentName, ammoName, modelPos, damageCoef = 1.0, flags = 0)`: `componentName` is the name of the damage zone, not of a model component. `damageCoef` multiplies the damage of the `CfgAmmo` class named by `ammoName`. | `P:\scripts\3_game\entities\object.c:1138` |
| A vehicle hit is one such call: `RegisterTransportHit` passes the ammo `"TransportHit"` with the hit speed in m/s as the coefficient (`m_TransportHitVelocity.Length()`). | `P:\scripts\3_game\entities\entityai.c:4134-4153` |
| `EEHitBy` runs on the server. `EEHitByRemote` is called only on the client that caused the hit. | `P:\scripts\3_game\entities\entityai.c:1143`, `:1153` |
| Damage in a radius is `DamageSystem.ExplosionDamage(source, directHitObject, ammoType, pos, damageType)`. There is no `ProcessIndirectDamage` in script. | `P:\scripts\3_game\damagesystem.c:25` |
| `GetProtectionLevel(type, ...)` covers four environmental hazard types only (`DEF_BIOLOGICAL`, `DEF_CHEMICAL`, `DEF_DUST_PARTICLE_BREATH`, `DEF_DUST_PARTICLE_EYES`, `P:\scripts\3_game\constants.c:547-550`). Ballistic protection of clothing is config and engine work with no script call. | `P:\scripts\4_world\entities\itembase.c:4073` |

`DecreaseHealth` changes health directly and skips this pipeline, so no `EEHitBy`, hit animation or bleeding follows it (reported; the call is in `api_player.md`, "Health"). Disease agents are not config classes: there is no `CfgAgents`, and each agent is a script class registered with `RegisterAgent` in `PluginTransmissionAgents` (`P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:22`). The vehicle hit flow line by line is in the `dayz-physics-engine` skill, `references/damage-and-transporthit.md`.
