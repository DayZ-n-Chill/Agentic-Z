# Characters

Covers the survivor classes, the body parts and head each one is built from, and how a new character reaches the character list. It also covers what every survivor inherits from `SurvivorBase` (the animation and ragdoll binding, the skinning yield, the surrender state), how infected differ as wearers, and where the work for a new body is described.

## Class tree

| Class | Parent | What it sets | Where |
|---|---|---|---|
| `SurvivorBase` | `Man` | Shared player config, including `InventoryEquipment` `playerSlots[]` | `P:\DZ\characters\data\config.cpp:122` |
| `SurvivorMale_Base` | `SurvivorBase` | `scope=0`, `woman=0`, `clothingType="male"`, default empty body parts, `faceType` | `:9138` |
| `SurvivorFemale_Base` | `SurvivorBase` | `scope=0`, `woman=1`, `clothingType="female"` | `:9192` |
| `SurvivorM_Mirek` | `SurvivorMale_Base` | `scope=2`, its own head and body parts | `:9234` |
| `SurvivorF_Eva` | `SurvivorFemale_Base` | `scope=2`, its own head and body parts | `:10234` |

All of these are in addon `DZ_Characters` (`P:\DZ\characters\data\config.cpp:3`).

## What one character is made of

`SurvivorM_Mirek` (`P:\DZ\characters\data\config.cpp:9234`) names five parts and a few textures:

| Key | Value on Mirek | The class it names |
|---|---|---|
| `emptyHead` | `MaleAdamHead` | `cfgVehicles` `MaleAdamHead: Head_Default` with the head model `m_adam.p3d` (`P:\DZ\characters\heads\config.cpp:2232`) |
| `emptyBody` | `MaleAdamTorso` | `MaleAdamTorso: MaleTorso_Base` (`P:\DZ\characters\tops\config.cpp:46`) |
| `emptyLegs` | `MaleAdamLegs` | `MaleAdamLegs: MaleLegs_Base` (`P:\DZ\characters\pants\config.cpp:50`) |
| `emptyFeet` | `MaleAdamFeet` | `MaleAdamFeet: MaleFeet_Base` (`P:\DZ\characters\shoes\config.cpp:45`) |
| `emptyGloves` | `MaleAdamHands` | `MaleAdamHands: MaleHands_Base` (`P:\DZ\characters\gloves\config.cpp:43`) |
| `faceType` | `MaleAdamHead` | `CfgFaces` entry (`P:\DZ\characters\heads\config.cpp:20`) and `CfgHeads` entry (`:4976`) |

It also sets `decayedTexture`, `BloodyHands` materials, `Lifespan` `Beard` textures and `Wounds` materials, all under `dz\characters\heads\data\m_adam\`.

The body parts are what shows when a slot is empty. `MaleTorso_Base` takes the `Body` slot and has one hidden selection, `personality`, which each character fills with its own skin texture and material (`P:\DZ\characters\tops\config.cpp:28`, and `MaleAdamTorso` at `:46`). That skin is what clothing copies into its own `personality` selection (see `color-variants.md`).

## How a character reaches the list

The game builds the list of playable characters when it starts. `DayZGame` walks every `CfgVehicles` class and keeps those with `scope` 2 that inherit `SurvivorBase` (`P:\scripts\3_game\dayzgame.c:1098` to `:1117`). So a new character is a new `scope=2` class under `SurvivorMale_Base` or `SurvivorFemale_Base`.

`cfgCharacterCreation` (`P:\DZ\data\config.cpp:2230`) holds the vanilla name lists (`personalityMale[]`, `personalityFemale[]`) and the starting clothes for each slot (`top[]`, `bottom[]` and the rest). `DefaultCharacterCreationMethods` reads the starting clothes by slot (`P:\scripts\3_game\gameplay.c:1149` and `:1183`). Adding a starting shirt means adding its class to `top[]`. Redeclare the whole array with `=` and keep the vanilla entries, the same safe form the Tier 2 `inventorySlot` rule uses (`skills/_shared/conventions/config.md`).

## Scope of a new character

A character with a new face needs a new head model and textures, which is art work for the Object Builder and asset specialists. A character that reuses a vanilla head with new skin textures needs only config: a new `SurvivorM_` or `SurvivorF_` class plus body part classes that inherit the vanilla `_Base` parts and set their own `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]`. Say which kind the request is before starting, because the first is several times the work.

A third kind is a whole new body: a custom survivor, human NPC or infected mesh. That is a rigging project, several times the work of a new head again. The mesh has to be weighted to the vanilla bone names in the vanilla bind pose: the workflow is in `body-rigging.md` and the export in `body-export.md`, why a body deforms under animation in `canonical-bind.md`, and the texture bake in `body-uv-bake.md`. The infected class side is in `skills/_shared/ai/custom-infected.md`. Vanilla has no human AI to drive an NPC (`skills/_shared/ai/patrols-and-guards.md`).

## What every survivor inherits from `SurvivorBase`

### Animation and ragdoll binding

`SurvivorBase` carries the block that binds a survivor to the player animation system, `class enfAnimSys` (`P:\DZ\characters\data\config.cpp:153`):

| Key | Value | Line |
|---|---|---|
| `meshObject` | `dz\characters\bodies\player_testing.xob` | `P:\DZ\characters\data\config.cpp:155` |
| `graphName` | `dz\anims\workspaces\player\player_main\player_main.agr` | `P:\DZ\characters\data\config.cpp:156` |
| `defaultInstance` | `dz\anims\workspaces\player\player_main\player_main.asi` | `P:\DZ\characters\data\config.cpp:157` |
| `skeletonName` | `player_testing.xob` | `P:\DZ\characters\data\config.cpp:158` |
| `ragdoll` | `DZ/characters/bodies/human.ragdoll` | `P:\DZ\characters\data\config.cpp:160` |

A new `SurvivorM_` or `SurvivorF_` class inherits the block and needs none of it redeclared. A mod that replaces the block for a custom body keeps the `ragdoll` line or points it at its own file. The ragdoll is data since 1.30: `P:\DZ\characters\bodies\human.ragdoll` holds eleven `RagdollBone` blocks with a mass and capsule each, from `pelvis` (mass 17, `P:\DZ\characters\bodies\human.ragdoll:5`) down to the legs. The format and the mass table are in `ragdoll.md`.

The bone list behind `player_testing.xob` has 172 bones and starts at `P:\DZ\anims\cfg\skeletons.anim.xml:110`.

### Skinning yield

`class Skinning` on `SurvivorBase` (`P:\DZ\characters\data\config.cpp:167`) sets what a skinned human body gives:

| Class | `item` | `count` | Line |
|---|---|---|---|
| `Steaks` | `HumanSteakMeat` | 10 | `P:\DZ\characters\data\config.cpp:169` |
| `Guts` | `Guts` | 1 | `P:\DZ\characters\data\config.cpp:175` |
| `Bones` | `Bone` | 2 | `P:\DZ\characters\data\config.cpp:181` |

`BloodInfectionSettings` (`P:\DZ\characters\data\config.cpp:187`) adds a `Salmonella` chance of 0.4. There is no `Lard` class in 1.30. 1.29 had one (1.29, not on `P:\`, so that part is not checked here). A recipe that expects `Lard` from a human body no longer gets it.

### Surrender state

Since 1.30 the surrender state is a flag on the player, not an item in the hands.

- `IsSurrendered()` is declared on `Man` (`P:\scripts\3_game\entities\man.c:67`).
- `SetSurrenderState(bool newState)` is on `PlayerBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:2116`).
- `ForceSurrenderState` on `EmoteManager` is marked obsolete in favour of `SetSurrenderState` (`P:\scripts\4_world\classes\emotemanager.c:1255`).

Clothing or item script that needs to know whether its wearer has surrendered asks `IsSurrendered()`.

## Infected as wearers

Infected are not survivors: `ZombieBase` inherits `DayZInfected` (`P:\DZ\characters\zombies\config.cpp:24`). Two differences matter for wearables.

- They take four attachment slots only: `Vest`, `Back`, `Headgear` and `Eyewear` (`attachments[]` at `P:\DZ\characters\zombies\config.cpp:64`).
- They bind to a shorter bone list, `hermit_newbindpose.xob` with 95 bones against the player's 172, and it has no face bones, so headgear weighted to face bones can stretch on an infected. The bone lists and the untested `skeletonName` override are in `canonical-bind.md`, "Survivors and infected bind to different skeletons".

Since 1.30 there are female military infected (`ZmbF_SoldierNormal_Base` at `P:\DZ\characters\zombies\config.cpp:11119`) next to the male ones. Their behaviour is in `skills/_shared/ai/custom-infected.md`.

## The skeleton name inside character and clothing models

Vanilla survivor bodies, infected bodies and worn clothing are all compiled with the skeleton name `DayzTemporarySkeleton`; the counts, the four unused models that carry `ofp2_manskeleton`, and what goes wrong with the other name are in `worn-models.md`, "Skeleton".

## Sandstorm protection on the wearer (1.30)

Two protection types decide whether worn gear shields its wearer from sandstorm dust: `DEF_DUST_PARTICLE_BREATH` and `DEF_DUST_PARTICLE_EYES` (`P:\scripts\3_game\constants.c:549` and `:550`). The dust agents they block are `SILICOSIS = 512` and `EYES_IRRITATION = 1024` in `eAgents` (`P:\scripts\3_game\enums\eagents.c:14` and `:15`). `PluginTransmissionAgents` reads the first type from the mask category for silicosis and the second from eyewear, mask and night vision for eye irritation (`AGT_AIRBOURNE_SOLID` at `P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:414`, the two cases at `:420` to `:433`), through `GetProtectionLevelCachedEquipment` (`:577`). A mod mask or goggles without these keys in its `Protection` class gives no sandstorm protection. Head gear also cuts the sun's heat: `HeadGearProtectionAgainstSun()` reads the heat isolation of the item in the `HEADGEAR` slot (`P:\scripts\4_world\classes\environment\environment.c:2037`). The protection keys themselves are in `protection-and-insulation.md`.
