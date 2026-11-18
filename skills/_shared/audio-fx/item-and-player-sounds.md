# Item and player sounds: the vanilla handlers

Which sound systems vanilla already runs for items and players: the item sound handler that lets the server start a sound on every client, the player sound handlers, step sounds, player sound events and the step sounds of bushes. Use them before writing your own sync. Line numbers are from the 1.30 scripts on `P:\`; statements about 1.29 are not yet checked on `P:\`.

## Contents

- [Item sounds started by the server](#item-sounds-started-by-the-server)
- [The headless check in the sound handlers](#the-headless-check-in-the-sound-handlers)
- [Player sound handlers](#player-sound-handlers)
- [Step sounds](#step-sounds)
- [Player sound events: heavy breathing (1.30)](#player-sound-events-heavy-breathing-130)
- [Step sounds of bushes and other static objects (1.30)](#step-sounds-of-bushes-and-other-static-objects-130)

## Item sounds started by the server

`ItemSoundHandler` (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:23`) is the official way to start an item sound on the server and hear it on every client. Its header comment gives the steps (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:12`): add a sound ID, link the ID to a sound set in `InitItemSounds()`, then start it from the server.

### Pick an ID

IDs are plain numbers in `SoundConstants` (`P:\scripts\3_game\constants.c:423`), from `ITEM_PLACE = 1` to `ITEM_ARMY_FLASHLIGHT_TURN_OFF = 61`. The largest ID an item may use is `ITEM_SOUNDS_MAX = 63` (`P:\scripts\4_world\entities\itembase.c:116`). For your own sound, add a constant in a `modded class SoundConstants` with a free number up to 63, or reuse a vanilla ID your item does not use.

### Link the ID to a sound set

The vanilla barrel is the model (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:532`):

```c
override void InitItemSounds()
{
    super.InitItemSounds();

    ItemSoundHandler handler = GetItemSoundHandler();
    handler.AddSound(SoundConstants.ITEM_BARREL_OPEN, "MyMod_BarrelOpen_SoundSet");

    // A sound that loops until the server stops it
    SoundParameters params = new SoundParameters();
    params.m_Loop = true;
    handler.AddSound(SoundConstants.ITEM_DEPLOY_LOOP, "MyMod_DeployLoop_SoundSet", params);
}
```

- `AddSound(int sound, string soundset, SoundParameters params = null)` is at `P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:134`.
- `SoundParameters` has three fields: `m_FadeIn`, `m_FadeOut` and `m_Loop` (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:1`).
- The base `InitItemSounds()` already links the place, deploy and deploy loop IDs when the item overrides `GetPlaceSoundset()`, `GetDeploySoundset()` or `GetLoopDeploySoundset()` (`P:\scripts\4_world\entities\itembase.c:4420`). For those three sounds, overriding the getter is enough.

### Start and stop from the server

```c
StartItemSoundServer(SoundConstants.ITEM_BARREL_OPEN);     // one shot
StopItemSoundServer(SoundConstants.ITEM_DEPLOY_LOOP);      // stop a loop
```

Vanilla calls it from the action, on the server (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actionopenbarrel.c:36`).

### Attach and detach sounds from config

An item can play its own sound when it goes into a slot, or comes out of one, with no script. `InventoryItemType` reads two pairs of arrays from the item's class in `CfgVehicles`, `CfgWeapons`, `CfgMagazines` or `CfgAmmo`: `attachSoundSet[]` with `attachSoundSlot[]`, and `detachSoundSet[]` with `detachSoundSlot[]` (`P:\scripts\3_game\inventoryitemtype.c:37`, `:38`, `:92` and `:93`). Entry `i` of the sound set array plays for the slot named at entry `i` of the slot array. The two arrays must have the same length, or none of them is loaded (`:41`). The vanilla shelter fabric is the model (`P:\DZ\gear\camping\config.cpp:11494` to `:11501`):

```cpp
attachSoundSet[]={"Shelter_Site_Attach_Fabric_SoundSet"};
attachSoundSlot[]={"Material_Shelter_Fabric"};
```

The server starts these through the item sound handler: `OnWasAttached` calls `StartItemSoundServer(SoundConstants.ITEM_ATTACH, slot_id)` and `OnWasDetached` calls it with `ITEM_DETACH` (`P:\scripts\4_world\entities\itembase.c:1336` and `:1347`). On the client the handler looks up the sound set for that slot, and falls back to a set linked with `AddSound` for the same ID when the slot has none (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:94` to `:108`). `ITEM_ATTACH = 6` and `ITEM_DETACH = 7` are taken (`P:\scripts\3_game\constants.c:430` and `:431`), so never give your own sound one of those numbers. Override `CanPlayAttachSound()` or `CanPlayDetachSound()` to silence one item (`itembase.c:4857` and `:4862`).

### What happens on the way to the client (1.30)

- `StartItemSoundServer(int id, int slotId)` returns at once unless it runs on the server, then puts the sound in a queue and schedules one flush for the frame (`P:\scripts\4_world\entities\itembase.c:4440`).
- `FlushItemSoundQueue` sends every queued sound in one `RPC_ITEM_SOUND_PLAY` (`P:\scripts\4_world\entities\itembase.c:4480`).
- `StopItemSoundServer(int id)` sends one `RPC_ITEM_SOUND_STOP` (`P:\scripts\4_world\entities\itembase.c:4499` to `:4506`).
- On the client, `ItemBase.OnRPC` reads `RPC_ITEM_SOUND_PLAY` and calls `PlayItemSoundClient` for each entry (`P:\scripts\4_world\entities\itembase.c:2800`), and reads `RPC_ITEM_SOUND_STOP` and calls `StopItemSoundClient` (`P:\scripts\4_world\entities\itembase.c:2820`).
- `PlayItemSoundClient` plays the set at the item's position and sets autodestroy on it. It does nothing when that ID is already playing (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:56`).

So on 1.30 several sounds started in one frame all arrive. The handler's header comment still says to avoid starting two sounds at the same time because one variable carries them (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:20`); that comment describes the older path below.

### The older path (1.29, and legacy code on 1.30)

Up to 1.29 the server wrote the ID into a synced variable, `m_SoundSyncPlay` or `m_SoundSyncStop`, the client played it in `OnVariablesSynchronized`, and the variable was cleared about 100 ms later. Only one play and one stop could travel per sync (1.29, not yet checked on `P:\`).

1.30 keeps the variables, marked as deprecated but kept for older mods (`P:\scripts\4_world\entities\itembase.c:117`), and keeps the old path only for a class that asks for it:

- `LegacyItemSoundSync()` plays and stops from the two variables (`P:\scripts\4_world\entities\itembase.c:3297`). It runs only if your class calls it from its own `OnVariablesSynchronized`.
- `LegacyStopItemSoundServer(int id)` writes `m_SoundSyncStop` and clears it 100 ms later (`P:\scripts\4_world\entities\itembase.c:4487`).

A 1.29 mod that relied on `OnVariablesSynchronized` to play item sounds keeps working through the RPC path without changes, as long as it starts sounds with `StartItemSoundServer`.

### Impact sounds from config

The sound an item makes when it hits the ground comes from config too. `InitImpactSoundData` reads the item's `soundImpactType` key, `"default"` when it is missing, and loads the table `<soundImpactType>_Impact_LookupTable` (`P:\scripts\3_game\entities\inventoryitem.c:114` to `:122`). The tables are classes of `CfgImpactSoundTables` (`P:\DZ\sounds\hpp\config.cpp:506974`); vanilla has `default`, `gun`, `grenade`, `textile`, `wood`, `glass`, `plastic`, `metal`, `organic`, `backpack`, `bones`, `clock` and `pills`. The vanilla shelter fabric sets `soundImpactType="textile"` (`P:\DZ\gear\camping\config.cpp:11502`). Pick one of those names for a mod item. `PlayImpactSound` returns at once when no table was loaded (`inventoryitem.c:94`), so a name with no table most likely leaves the item silent (whether the lookup returns null for an unknown name is not checked on `P:\`). The item's config `weight` and the impact speed reach the sound set as the sound variables `weight` and `speed` (`inventoryitem.c:100` and `:101`). On a dedicated server the impact is sent to clients with the `m_WantPlayImpactSound` signal (`P:\scripts\4_world\entities\itembase.c:1134`).

### When the item sound handler does not fit

For a state that is not an item sound ID (a device that runs, an alarm that is armed), sync your own variable and play in `OnVariablesSynchronized`; see `sound-script.md`, "Starting a sound from the server".

## The headless check in the sound handlers

`Object.PlaySoundSet` still tests only `IsDedicatedServer()` in 1.30 (`P:\scripts\3_game\entities\object.c:1249`). The item and player sound handlers use the wider 1.30 check, `IsHeadlessOrDedicatedServer()`, which also skips headless clients:

- `StopItemSoundClient` (`P:\scripts\4_world\classes\soundhandlers\itemsoundhandler.c:121`).
- The client player sound manager, before it starts its distance check (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:105`).
- The registration of the player's step sound and attachment sound tables, with the vanilla comment "sounds are unnecessary on server" (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgsounds.c:335`).
- `SEffectManager.Cleanup`, which warns when sound data exists on that side (`P:\scripts\3_game\effectmanager.c:536`).

The check itself is `IsHeadlessOrDedicatedServer()` on the game (`P:\scripts\3_game\global\game.c:1136`). For new client side play and stop code of your own, use it. Do not assume `PlaySoundSet` moved to it: a headless client still passes the `PlaySoundSet` test.

## Player sound handlers

`PlayerSoundManagerBase` (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:20`) holds one handler per state in the `eSoundHandlers` enum: `STAMINA`, `HUNGER`, `INJURY` and `THIRST` (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:4`).

- `RegisterHandler(SoundHandlerBase handler)` adds one (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:33`) and `GetHandler(eSoundHandlers id)` returns it (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:39`).
- There is a server manager and a client manager. The client one registers the client handler of each state (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:95`).
- State sounds of other players are heard only within `SOUNDS_HEARING_DISTANCE = 50` meters (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:2`).
- The freezing handler is not live: the whole of `P:\scripts\4_world\classes\soundhandlers\freezingsoundhandler.c` is commented out (lines 1 to 58), and its enum entry and its registration are commented out too (`P:\scripts\4_world\classes\soundhandlers\playersoundmanager.c:99`). A mod cannot extend `FreezingSoundHandlerClient`.

## Step sounds

`DayZPlayerImplement.OnStepEvent` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3269`) handles each step:

- The sound part is compiled only for clients, inside `#ifndef SERVER`, and reads the step sound table of the player type with `GetStepSoundLookupTable()` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3328`).
- It plays through the player's own `PlaySound(SoundObject so, SoundObjectBuilder sob)`, which sets the position and calls `Play3D` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3254`).
- The noise part, which is what AI hears, is separate: `AddNoise(NoiseParams noisePar, float noiseMultiplier = 1.0)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3258`). See `noise-for-ai.md`.

Step and gesture sounds bound to animation events are played by the engine on each client; nothing has to be synced for them. The player handles its animation sound events in `OnSoundEvent(string pEventType, string pUserString, int pUserInt)` (`P:\scripts\4_world\entities\dayzplayerimplement.c:3484`), and an animal in `OnSoundEvent(int event_id, string event_user_string)`, registered as the animation event `"Sound"` (`P:\scripts\3_game\entities\dayzanimal.c:260`, `:298`). `ItemBase` has no `OnSoundEvent` to override: for an item, use the item sound handler above, `PlaySoundSet`, or an `AnimEvents` class in config. Config hooks for item animation events are in `effects-wiring.md`.

## Player sound events: heavy breathing (1.30)

1.30 adds the event ID `HEAVY_BREATHING` to `EPlayerSoundEventID` (`P:\scripts\4_world\classes\soundevents\playersoundevents\playersoundeventhandler.c:38`).

- Its class is `HeavyBreathEvent1`, which sets `m_SoundVoiceAnimEventClassID = 907` (`P:\scripts\4_world\classes\soundevents\playersoundevents\events\heavybreathevents.c:21` and `:26`).
- It is registered with `RegisterState(new HeavyBreathEvent1())` (`P:\scripts\4_world\classes\soundevents\playersoundevents\playersoundeventhandler.c:99`).
- Vanilla requests it from the silicosis modifier: `RequestSoundEventEx(EPlayerSoundEventID.HEAVY_BREATHING, true, EPlayerSoundEventParam.HIGHEST_PRIORITY)` (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\silicosis.c:105`).

A mod requests it the same way, with `RequestSoundEventEx` on the player (`P:\scripts\4_world\entities\manbase\playerbase.c:7768`).

### The destructor of a sound event

`SoundEventBase` stops its sound in the destructor only while the game object still exists: `if (g_Game) Stop();` (`P:\scripts\4_world\classes\soundevents\soundevents.c:12`).

Do not add a destructor of the 1.29 style to a subclass of `InfectedSoundEventBase` that calls `m_SoundSetCallback.Stop()` without that test. Such a destructor crashes the game on shutdown (not yet checked on `P:\`).

## Step sounds of bushes and other static objects (1.30)

A static object can bring its own step sounds for a player who walks through it. `StaticObjectType` reads them from config at `CfgNonAIVehicles <ClassName> VegetationSounds` (`P:\scripts\3_game\entities\staticobjecttype.c:13`):

- Each child class of `VegetationSounds` gives a `soundSet` and a list of `animEventIds[]`.
- `GetVegetationSoundBuilderFromEventID(int stepEventID)` returns the sound for one step event (`P:\scripts\3_game\entities\staticobjecttype.c:44`), and the player's step code asks for it (`P:\scripts\4_world\entities\dayzplayerimplement.c:3408`).
- The vanilla comment notes that the map may not hold every event; the defaults of the player type are used then (`P:\scripts\3_game\entities\staticobjecttype.c:3`).

The macro `CUSTOM_PLAYER_MOVEMENT_SOUNDSETS(walkErc, walkCro, runErc, sprintErc, scuffErc)` writes the whole `VegetationSounds` class from five sound set names (`P:\DZ\data\basicdefines.hpp:310`). Its five child classes and their animation event IDs:

| Class | Movement | `animEventIds[]` |
|---|---|---|
| `bush_walkErc` | Walking upright | 1, 2, 23, 24, 51, 52 |
| `bush_walkCro` | Walking crouched | 21, 22, 31, 32, 33, 34, 131 |
| `bush_runErc` | Running | 3, 4, 17, 101, 53, 54 |
| `bush_sprintErc` | Sprinting | 5, 6, 35, 36, 37, 38, 100, 110, 111 |
| `bush_scuffErc` | Scuffing | 7, 8 |

To give a custom bush its own sounds, add `VegetationSounds` to its `CfgNonAIVehicles` class, by hand or with the macro.

### A changelog entry that is not in script

The 1.30 changelog mentions a `SoundHitType` with a `GetSoundHitType()` getter. Neither name is in the script files on `P:\` (no file under `P:\scripts\` contains `SoundHitType`, and `P:\scripts\3_game\surfaceinfo.c` has no such getter). Do not call it.
