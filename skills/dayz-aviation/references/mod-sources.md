# Where the helicopter mod sources are

Which Workshop helicopter mods can be read as plain script, which PBO holds the flight code, and which are a dead end. Open it before planning research on "how does another helicopter mod do this".

Third-party mod behaviour, not vanilla, and not yet checked on `P:\` (these are Workshop mods). The sizes and file counts were read on 2026-08-05 from each mod's PBO header and by extracting with a PBO extraction tool; a mod update can change them. `<DayZ>` below is the DayZ client install folder; subscribed Workshop mods sit under `<DayZ>\!Workshop\`.

| Mod | PBO with the scripts | Content | Verdict |
|---|---|---|---|
| **RFFS** | `addons\RFFSHeli_Core.pbo` in the RFFS mod folder | 53 `.c` files, packing method 0 (uncompressed). The core is `scripts\4_World\RFFSHeli_Core.c` at 88,559 bytes. Also `modded_Inputs.xml`, `GUI\RFFSHelicopterGUI.layout` and `scripts\5_Mission\GUI\headsUpDisplay.c`. | Extract directly; no special tooling needed. |
| **Expansion** | `@DayZ-Expansion-Vehicles\addons\vehicles_scripts.pbo` | 192 `.c` files, 974 KB. Largest: `ExpansionVehicleHelicopter.c` (116,933 bytes), `CarScript.c` (97,932 bytes), `ExpansionHelicopterScript.c` (40,671 bytes), `ExpansionPhysicsState.c`, `ExpansionInterpolatedInput.c`, `ExpansionHelicopterHud.c`. | The flight code is in `vehicles_scripts.pbo`, not in `vehicles_air_gyro.pbo` or `vehicles_air_hatchbird.pbo` (those hold models and sounds). |
| **Arma 2 Helicopters Remastered** | `@Arma 2 Helicopters Remastered\addons\Scripts.pbo` (137 KB of a mod of about 700 MB) | 24 `.c` files, including 13 `EXT_*.c` files, one flight parameter file per airframe (`EXT_UH60M.c`, `EXT_MH6.c`, `EXT_AH64D.c`, `EXT_Mi24.c` and more), plus `ExpansionHelicopterScript.c`. | The cheapest source of tuned numbers per aircraft; it derives from Expansion. It is not among the mods analysed in the other files here, so add it when comparing feel or rate constants. |
| **AnimatedDynamicHelicopters** | `DynamicHelicopters.pbo` (334 MB, one PBO) | Built to defeat extraction: 358,128 index entries, 25,169 decoy `.c` files with Windows reserved device names (`LPT1.{GUID}`, `COM1`, `NUL`, `PRN`), zero width characters in paths, `Cprs` compression. | Do not spend time on it; extracting it can also litter the file system. |
| `HelicopterSIB_Hommade_LF` | `HelicopterSIB_Hommade_LF.pbo` | One `.c` file of 1,177 bytes. This is not the SIB helicopter source. | Dead end. The SIB scripts that were read are described in `helicopter-sib.md` (Workshop `3485438937`). |

## Two traps

1. **A mod named after a helicopter mod is not its source.** `HelicopterSIB_Hommade_LF` looks like the SIB source by name; it is a 1 KB stub. Count the `.c` files before planning around a source.
2. **Read the PBO index before extracting.** A 40 line reader over the PBO header (a zero terminated name plus five 4 byte fields per entry, `<4sIIII>` in Python `struct` notation) gives the `.c` count and the packing method in under a second. That is enough to spot both an obfuscated mod and an empty one without unpacking 300 MB. Packing method `0` means the scripts are plain text inside the PBO; `Cprs` means compressed.

## Check the notes first

Before commissioning research on how other helicopter mods do something, read `helicopter-rffs.md`, `helicopter-mh6.md`, `helicopter-sib.md` and `helicopter-expansion.md`: the four are already analysed there with `file:line`, including how each one syncs in multiplayer. The work that is really missing is almost never "what does mod X do"; it is "how does our code differ from it".

Reading another mod's scripts is for learning the pattern. Write the mod's own code, and respect each mod's licence: a mod that ships obfuscated or under a no-derivatives licence is not a source to copy from.
