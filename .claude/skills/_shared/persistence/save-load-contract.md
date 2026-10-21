# Save and load contract

How the object store saves an entity, what vanilla already writes for you, and the order the load hooks run in.

## Where it runs

Both hooks run on the server only. The engine calls `OnStoreSave` to collect an entity's data and `OnStoreLoad` when it reads it back (`P:\scripts\3_game\entities\entityai.c:2894` and `:2955`). Never call them yourself, and never send their data to clients; use net sync for that.

| Hook | Signature | Source |
|---|---|---|
| Save | `void OnStoreSave(ParamsWriteContext ctx)` | `P:\scripts\3_game\entities\entityai.c:2910` |
| Load | `bool OnStoreLoad(ParamsReadContext ctx, int version)` | `P:\scripts\3_game\entities\entityai.c:2978` |
| After this entity and its children loaded | `void AfterStoreLoad()` | `P:\scripts\3_game\entities\entityai.c:1419` |
| After load, for linked systems | `void EEOnAfterLoad()` | `P:\scripts\3_game\entities\entityai.c:1381` |
| A child could not be put back | `void OnBinLoadItemsDropped()` | `P:\scripts\3_game\entities\entityai.c:1424` |

`ParamsWriteContext` and `ParamsReadContext` are both `Serializer` (`P:\scripts\3_game\gameplay.c:15` and `:16`). `Write` and `Read` take any value and return `bool` (`P:\scripts\1_core\proto\serializer.c:57` and `:58`). Vanilla writes ints, floats, bools, strings and vectors this way; the player writes its ladder logout position as a vector (`P:\scripts\4_world\entities\manbase\playerbase.c:7384`).

## One stream per entity

Each entity has one stream of values with no names and no type tags. Every class in the chain calls `super` first, then appends its own values. Loading walks the same chain and must read the same values, of the same types, in the same order. The vanilla comment says it plainly: "format and order of reading must be the same as writing" (`P:\scripts\3_game\entities\entityai.c:2964`).

This means a subclass's data sits after its parent's data. If anything earlier in the chain reads one value too many or too few, every class after it reads the wrong bytes.

## What vanilla already saves

You do not write these yourself. They are written by the base classes your class inherits from.

| Data | Written by | Source |
|---|---|---|
| Construction component data | `EntityAI.OnStoreSave` | `P:\scripts\3_game\entities\entityai.c:2912` |
| Energy: amount, passive, switched on, plugged, and the energy source's persistent ID in four ints | `EntityAI.OnStoreSave` | `P:\scripts\3_game\entities\entityai.c:2917` to `:2948` |
| Variables mask and values (temperature in `EntityAI`; quantity, wetness, liquid type, color and cleanness in `ItemBase`) | `SaveVariables` and `WriteVarsToCTX` | `P:\scripts\3_game\entities\entityai.c:3160`; `P:\scripts\4_world\entities\itembase.c:2962` |
| Quick bar slot when a player carries it | `ItemBase.OnStoreSave` | `P:\scripts\4_world\entities\itembase.c:3190` |
| Disease agents | `ItemBase.OnStoreSave` calls `SaveAgents` | `P:\scripts\4_world\entities\itembase.c:3190` |
| Remote trigger pairing | `RemotelyActivatedItemBehaviour.OnStoreSave` from `ItemBase` | `P:\scripts\4_world\entities\itembase.c:3210` to `:3214` |

Attachments and cargo are stored by the engine as their own records, not in your stream. `AfterStoreLoad` runs "after all children loaded" (`P:\scripts\3_game\entities\entityai.c:1418`), and `OnBinLoadItemsDropped` fires when a child could not be put back into its parent and was dropped (`:1423`). So a safe's contents survive a restart without any script; only state the engine does not know about (a code, a timer, an owner) needs `OnStoreSave`.

## Load hook order

1. `OnStoreLoad` on the entity. Read your values here and store them in member variables. Do not look up other entities yet.
2. `AfterStoreLoad`, after this entity and all its children are loaded. Apply state that depends on loaded values or on children. `ItemBase` sets the loaded quantity here (`P:\scripts\4_world\entities\itembase.c:3218`), and `BaseBuildingBase` rebuilds its parts here (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:466`).
3. `EEOnAfterLoad`, for links between separate entities. `ItemBase` clears its damage reset flag here (`P:\scripts\4_world\entities\itembase.c:3234`), which shows vanilla expects it to run after `AfterStoreLoad`.

## Links to other entities

`GetPersistentID(out int b1, out int b2, out int b3, out int b4)` returns an ID that "stays the same even after server restart" (`P:\scripts\3_game\entities\entityai.c:3374`). To restore a link, save the four ints, keep them in `OnStoreLoad`, and look the entity up later with `GetGame().GetEntityByPersitentID(b1, b2, b3, b4)` (the vanilla name is spelled that way, `P:\scripts\3_game\global\game.c:1420`).

The lookup works only inside `EEOnAfterLoad`. The energy manager does exactly this: it stores the IDs during load because the lookup "cannot be called here" (`P:\scripts\3_game\entities\entityai.c:3041`) and calls it in `EEOnAfterLoad`, where "this function is available only in this event" (`:1393`).

## When a read fails

Check the return of every `Read` and return `false` when it fails. Vanilla returns `false` only when the stream is short or broken, for example `BaseBuildingBase` (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:432` to `:463`). Returning `false` means the engine could not load the record. What the engine then does with the object is not visible in script, so treat `false` as losing the object and test every load path on a copy of the server storage.

Do not return `false` to mean "this save has no value for my new field". That case is an upgrade path, covered in `versioning-and-migration.md`.

## Other saving hooks worth knowing

| Hook | Use | Source |
|---|---|---|
| `bool CanSaveItemInHands(EntityAI item_in_hands)` | Whether the item a player holds is saved with them. The stash returns `false`. | `P:\scripts\3_game\entities\entityai.c:1746`; `P:\scripts\4_world\entities\undergroundstash.c:36` |
| `void SetLifetime(float fLifeTime)` and `float GetLifetime()` | Set or read the remaining economy lifetime in seconds. Saved data does not keep an object whose lifetime the economy lets run out. | `P:\scripts\3_game\entities\entityai.c:3377` and `:3379` |
| `ECE_NOLIFETIME`, `ECE_NOPERSISTENCY_WORLD`, `ECE_DYNAMIC_PERSISTENCY` | Spawn flags for `CreateObjectEx` that skip lifetime, skip saving in the world, or turn saving on only once a player takes the object. | `P:\scripts\3_game\ce\centraleconomy.c:30`, `:31`, `:33`; used at `P:\scripts\3_game\dayzgame.c:3669` |

## Vanilla examples to read

| Class | What it shows | Source |
|---|---|---|
| `CombinationLock` | A field removed and a field added, both behind the game version | `P:\scripts\4_world\entities\itembase\combinationlock.c:128` and `:138` |
| `DigitalCodeLock` with `CodeLockComponent` | A helper object that saves its own fields inside the owner's stream | `P:\scripts\4_world\entities\itembase\codelock.c:484`; `P:\scripts\4_world\classes\codelockcomponent.c:257` |
| `TerritoryFlag` | A timer saved and checked after load | `P:\scripts\4_world\entities\itembase\basebuildingbase\totem.c:101` and `:111` |
| `PlayerBase` | Large chain of sub systems, each with its own save call, written only on a multiplayer server | `P:\scripts\4_world\entities\manbase\playerbase.c:7353` and `:7408` |
