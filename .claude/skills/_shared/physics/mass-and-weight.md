# Mass and weight

Covers the two separate numbers that make an object heavy, where each is set, how to read each one, and the config keys that change how an item is carried and thrown.

## Two numbers, two jobs

| Number | Set in | Unit | Used for |
|---|---|---|---|
| `weight` | `config.cpp` | grams | Inventory weight and the item's impact sound |
| Body mass | the model's Geometry LOD (**model knowledge**) | kilograms | The physics body: pushing, impulses, vehicle crash damage |

- `weight` is read as an integer: `m_ConfigWeight = ConfigGetInt("weight")` (`P:\scripts\3_game\entities\entityaitype.c:49`).
- It is in grams: vanilla names a 10 kg limit `OBJECT_OBSTRUCTION_WEIGHT = 10000; //in grams` (`P:\scripts\5_mission\gui\inventorynew\vicinityitemmanager.c:13`).
- The base value is `weight=1000` on `Inventory_Base` (`P:\DZ\data\config.cpp:3171`). `WoodenCrate` sets `weight=10000` (`P:\DZ\gear\camping\config.cpp:10174`).
- Inventory weight is the config weight times the wetness modifier (`P:\scripts\3_game\entities\entityai.c:3574`).
- `ItemBase.EOnContact` passes `m_ConfigWeight` into the impact sound (`P:\scripts\4_world\entities\itembase.c:1125` and `:1131`).
- Body mass is in kilograms. Vanilla car crash damage divides the contact impulse by `dBodyGetMass(this)` and says it "calculates damage as if the object's weight was 1000kg" (`P:\scripts\4_world\entities\vehicles\carscript.c:1292`).
- Code that needs the physical mass reads the body, not the config. The push action uses `dBodyGetMass(entity)` to size its impulse (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionpushobject.c:100`).

Changing `weight` in config does not change how the body moves, and changing the Geometry mass does not change the inventory weight. A fault report must say which of the two is wrong.

## Reading the mass

- **Mod MLOD model.** Run `/dayz-p3d-audit` on the model. In the Geometry LOD section it prints `NOTE: Geometry LOD mass: <value>`, or `NOTE: Geometry LOD has no mass` when no point carries a mass. The value is the sum of the per point masses stored in the LOD's `#Mass#` tag (**model knowledge**, read through py3d).
- **In game, any model.** On a diag session, read the live body with `dBodyGetMass(obj)` (`P:\scripts\1_core\proto\enphysics.c:122`) or `obj.GetPhysics().GetMass()` (`P:\scripts\1_core\physics\physics.c:69`; `GetPhysics()` at `P:\scripts\1_core\proto\enentity.c:562`). This is the only way to learn the mass of a vanilla model.
- `dBodySetMass(body, mass)` exists (`P:\scripts\1_core\proto\enphysics.c:123`), but the only vanilla caller is the scripted test body `ScriptModel` (`P:\scripts\2_gamelib\entities\scriptmodel.c:48`). Fix the mass on the model instead.

Compare the two numbers as a sanity check: a 10 kg crate should have about 10 on its Geometry LOD and `weight=10000` in config. This is a judgment for the reviewer, not an engine rule.

## Config keys that change physical handling

| Key | Values | Effect | Source |
|---|---|---|---|
| `simulation` | `"inventoryItem"` on every item | Makes the class an inventory item | `P:\DZ\data\config.cpp:3168` |
| `physLayer` | `"item_small"` (default) or `"item_large"` | Which item physics layer the body uses. Vanilla uses only these two values. The script enum has matching `ITEM_SMALL` and `ITEM_LARGE` layers (`P:\scripts\3_game\global\dayzphysics.c:37`, `:38`) | `P:\DZ\data\config.cpp:3169`; `MediumTent` sets `item_large` at `P:\DZ\gear\camping\config.cpp:76` |
| `itemBehaviour` | `0` heavy, `1` one handed, `2` two handed; unset is `-1` | `0` makes `IsHeavyBehaviour()` true, which blocks some actions in hands, such as drinking from a pond (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actiondrinkpondcontinuous.c:53`). Throwing is blocked by the hand profile instead; see `drop-and-throw.md` | `P:\scripts\4_world\entities\itembasetype.c:33`, read at `:103`; heavy test at `P:\scripts\4_world\entities\itembase.c:4326` |
| `soundImpactType` | a surface sound family such as `"wood"` | Picks the impact sound table; see `contact.md` | `P:\scripts\3_game\entities\inventoryitem.c:120`; `WoodenCrate` at `P:\DZ\gear\camping\config.cpp:10188` |

`WoodenCrate` is the vanilla reference for a crate: `weight=10000`, `itemBehaviour=0` (`P:\DZ\gear\camping\config.cpp:10174`, `:10176`), and it is registered with the heavy hand profile (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:854`), so a player drops it but can't throw it.
