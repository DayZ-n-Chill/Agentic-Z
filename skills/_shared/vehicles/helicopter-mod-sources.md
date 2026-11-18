# Helicopter mod sources

Which Workshop helicopter mods can be read as plain script, which PBO holds their flight code, and which are dead ends. Open it before planning research on how another helicopter mod does something.

Vanilla ships no flyable helicopter: `HelicopterScript` (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:4`) has no subclass and no config class uses it (`helicopters.md`), so flight code to learn from lives in Workshop mods. The sizes and counts below were read from each mod's PBO header and by extracting it; a mod update can change them. Subscribed Workshop mods sit under `<DayZ>\!Workshop\`, where `<DayZ>` is the client install folder.

| Mod | PBO with the scripts | What is in it | Verdict |
|---|---|---|---|
| RFFS | `addons\RFFSHeli_Core.pbo` | 53 `.c` files, packing method 0 (uncompressed). The core is `scripts\4_World\RFFSHeli_Core.c` (88,559 bytes); also `modded_Inputs.xml`, `GUI\RFFSHelicopterGUI.layout` and `scripts\5_Mission\GUI\headsUpDisplay.c`. | Extract directly; no special tool needed. |
| Expansion | `@DayZ-Expansion-Vehicles\addons\vehicles_scripts.pbo` | 192 `.c` files, 974 KB. Largest: `ExpansionVehicleHelicopter.c` (116,933 bytes), `CarScript.c` (97,932), `ExpansionHelicopterScript.c` (40,671), then `ExpansionPhysicsState.c`, `ExpansionInterpolatedInput.c`, `ExpansionHelicopterHud.c`. | The flight code is here, not in `vehicles_air_gyro.pbo` or `vehicles_air_hatchbird.pbo`, which hold models and sounds. |
| Arma 2 Helicopters Remastered | `@Arma 2 Helicopters Remastered\addons\Scripts.pbo` (137 KB of a mod of about 700 MB) | 24 `.c` files, including 13 `EXT_*.c` files with one flight parameter set per airframe (`EXT_UH60M.c`, `EXT_MH6.c`, `EXT_AH64D.c`, `EXT_Mi24.c` and more), plus `ExpansionHelicopterScript.c`. | The cheapest source of tuned numbers per aircraft; derived from Expansion. Not analysed in the other helicopter files; add it when comparing feel or rate constants. |
| AnimatedDynamicHelicopters | `DynamicHelicopters.pbo` (334 MB, one PBO) | Built against extraction: 358,128 index entries, 25,169 decoy `.c` files with Windows reserved device names (`LPT1.{GUID}`, `COM1`, `NUL`, `PRN`), zero-width characters in paths, `Cprs` compression. | Skip it; extracting it can also litter the file system. |
| `HelicopterSIB_Hommade_LF` | `HelicopterSIB_Hommade_LF.pbo` | One `.c` file of 1,177 bytes. | Dead end; it is not the SIB source. The SIB scripts that were read are in `helicopter-sib.md` (Workshop `3485438937`). |

## Two traps

- A mod named after a helicopter mod is not its source. `HelicopterSIB_Hommade_LF` looks like the SIB source and is a 1 KB stub. Count the `.c` files before planning around a source.
- Read the PBO index before extracting. A short reader over the PBO header (a zero-terminated name plus five 4-byte fields per entry, `<4sIIII>` in Python `struct` notation) gives the `.c` count and the packing method in under a second, enough to spot an obfuscated or empty mod without unpacking 300 MB. Packing method `0` means plain text inside the PBO; `Cprs` means compressed.

## Read the existing notes first

Four mods are already analysed with file and line, including how each syncs in multiplayer: `helicopter-rffs.md`, `helicopter-mh6.md`, `helicopter-sib.md` and `helicopter-expansion.md`. What is usually missing is not what mod X does but how your own code differs from it.

Reading another mod's scripts is for learning the pattern. Write the mod's own code and respect each mod's licence: a mod shipped obfuscated or under a no-derivatives licence is not a source to copy from.
