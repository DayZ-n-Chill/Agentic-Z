# Characters

Covers the survivor classes, the body parts and head each one is built from, and how a new character reaches the character list.

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

`cfgCharacterCreation` (`P:\DZ\data\config.cpp:2230`) holds the vanilla name lists (`personalityMale[]`, `personalityFemale[]`) and the starting clothes for each slot (`top[]`, `bottom[]` and the rest). `DefaultCharacterCreationMethods` reads the starting clothes by slot (`P:\scripts\3_game\gameplay.c:1149` and `:1183`). Adding a starting shirt means adding its class to `top[]`. Redeclare the whole array with `=` and keep the vanilla entries, the same safe form the Tier 2 `inventorySlot` rule uses (`.claude/skills/_shared/conventions/config.md`).

## Scope of a new character

A character with a new face needs a new head model and textures, which is art work for the Object Builder and asset specialists. A character that reuses a vanilla head with new skin textures needs only config: a new `SurvivorM_` or `SurvivorF_` class plus body part classes that inherit the vanilla `_Base` parts and set their own `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]`. Say which kind the request is before starting, because the first is several times the work.
