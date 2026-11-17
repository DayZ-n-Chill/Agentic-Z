# Retracted claims ledger: DayZ modding beliefs once written as fact and later corrected

Tier 3 pack: a list of DayZ modding beliefs that were written down as fact, then measured or re-read and found wrong. Load it when a note, another agent or an older file states one of them, before acting on it. Each row gives the old claim, what holds now, and the evidence. The depth for each row lives in the skill named in the last column.

How to read the evidence column: a `P:\` path was opened for this file. "Measured" means an in-game or offline measurement on the build named; it is **not yet checked on `P:\`** and cannot be, because it is engine or tool behaviour. Third-party rows name the product and are that product's behaviour, not vanilla.

## Enforce Script and engine API

| Old claim | What holds | Evidence | Depth |
|---|---|---|---|
| An empty `#ifdef` block segfaults the compiler. | A block that holds only a comment compiles and runs, at file scope, in a class body and in a method body, with the macro defined or not. A block with nothing at all inside was not measured. | Measured on DayZDiag 1.30.164289, server and client. Vanilla ships such blocks; the two sites are cited in `engine-findings-from-pack-history.md` ("Which macros DayZDiag defines"). | `enforce-script-reference` |
| The last argument of `RegisterNetSyncVariableFloat` is a number of bits. | It is the number of digits after the decimal point (`precision`). | `P:\scripts\3_game\entities\entityai.c:2859-2861` | `enforce-script-reference` |
| A `scope = 1` class is "editor only" and cannot be spawned by script. | Script can create it. Vanilla spawns `LargeTentClutterCutter` that way. | `scope=1` at `P:\DZ\gear\camping\config.cpp:1454-1456`; the `CreateObjectEx` call with `LargeTentClutterCutter` at `P:\scripts\4_world\entities\itembase\tentbase\largetent.c:140` | `enforce-script-reference` |
| `EntityAI.OnStoreSave` writes nine energy fields. | It writes eight: four `m_EM` values and four energy-source blocks, on 1.29 as on 1.30. A stream simulator that writes nine misreads every later field. | `m_EM` writes at `P:\scripts\3_game\entities\entityai.c:2920-2947` | `dayz-persistence` |
| 1.30 removed `SurrenderDummyItem`. | The class is still declared, marked obsolete. 1.30 no longer puts it in the hands, and its profile is still registered so the child `.asi` is preloaded. | `P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1-2` | `dayz-animation-pipeline` |
| The comment "Old system for handling player death state" describes `PhysicsSetRagdoll`. | It sits on `PhysicsSetSimpleDeath`. | `P:\scripts\3_game\human.c:1448-1449` | `dayz-physics-engine` |
| The vanilla player graph's variable and command IDs are not exposed to script, so a `HumanCommandScript` cannot drive that graph. | Script gets the IDs by name through `GetAnimInterface`: `BindVariableFloat`, `BindCommand` and `BindTag`. Measured in game on 1.30.164014: the binds returned valid ids on server and owner client, and `PreAnim_CallCommand` took the graph into its jump-and-fall state machine. | `BindCommand` at `P:\scripts\3_game\human.c:310`, `BindVariableFloat` at `P:\scripts\3_game\human.c:313`, `BindTag` at `P:\scripts\3_game\human.c:318`, `GetAnimInterface` at `P:\scripts\3_game\human.c:1421` | `dayz-animation-pipeline` |
| The in-water check is `g_Game.GetWaterDepth(pos) <= 0`. | That holds where there is no water. In water the test is `> 0`. | `GetWaterDepth` at `P:\scripts\3_game\global\game.c:1198` | `enforce-script-reference` |
| `EnProfilerFlags` has `FUNCTION_TIMES`, `FUNCTION_COUNT`, `CLASS_TIMES` and `CLASS_COUNT`. | The flags are `NONE`, `RESET`, `RECURSIVE` and `ALL`. | `EnProfilerFlags` at `P:\scripts\1_core\proto\enprofiler.c:8-18` | `enforce-script-reference` |
| Damage type constants are spelled `DT_*`. | The enum is `DamageType`: `CLOSE_COMBAT`, `FIRE_ARM`, `EXPLOSION`, `STUN`, `CUSTOM`. | `DamageType` at `P:\scripts\3_game\damagesystem.c:10-17` | `enforce-script-reference` |
| A class that holds a `static ref` to itself stops its script module from compiling. | Retracted: it was measured on the wrong mod. Vanilla does exactly that and compiles. | `s_Instance` at `P:\scripts\5_mission\gui\inventorynew\vicinityitemmanager.c:20` | none: this file |
| A recipe's `CanDo` should call `super.CanDo` first. | Copy `ingredients[0]` and `[1]` to locals and do not call `super`. With `super` first, the server's `CanDo` returned false while every part of its condition read true. The mechanism is not established. Vanilla calls `super.CanDo` in 1 of its 218 recipe overrides (counted on `P:\`). | Measured on DayZDiag 1.29. The one vanilla call: `super.CanDo` at `P:\scripts\4_world\classes\recipes\recipes\craftlongtorch.c:61` | `enforce-script-reference` |
| `Fence.OpenFence()` checks the combination lock. | It does not. It only sets animation phases; the lock is checked by the callers through `IsLocked`. | `OpenFence` at `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:488`, `IsLocked` at `P:\scripts\4_world\entities\itembase\basebuildingbase\fence.c:127` | `dayz-basebuilding` |
| A `CallLater` re-queued from its own callback never fires again. | True only where it was measured, the client diag build of 1.29. On the retail DayZServer 1.30.164289 a `CALL_CATEGORY_SYSTEM` chain and a `CALL_CATEGORY_GAMEPLAY` chain both ran all six steps. | Measured | `enforce-script-reference` |
| Enforce Script has `do { } while`. | It does not. Write a `while` loop. | Measured (compile) | `enforce-script-reference` |
| A script cannot walk a client-controlled player. | It can: with the movement overrides set by the owner every tick and by the server in every `ConsumeMove` after `super`, the player walked about 1.52 m/s and owner and server ended at the same position. | Measured on DayZDiag 1.29 | `dayz-physics-engine` |
| A model with no View Geometry LOD gets no action. | At a camera pitch of -45 degrees or lower, targeting also takes the objects of a 30 degree, 3 m cone and scores them by distance to the cursor ray, with no hit on them needed. An item on the ground can still become a target, and the target condition of `ActionTakeItemToHands` checks only distance. So picking an item up is not a collision test. | Read in the 1.29 scripts; not yet checked on `P:\` | `dayz-physics-engine` |
| 1.30 added the `CanReachSeatFromDoors` call to the get-in condition. | 1.29 already called it. 1.30 adds `CanGetIn()` and a DiagMenu wrapper. | Read in both script trees; not yet checked on `P:\` | `dayz-vehicles` |
| To make a 1.30 battery car work, return `true` from `NeedElectricitySourceDevice()`. | `true` is already the default. The three electricity-source getters are what a custom battery car must override. | Read in the 1.30.164200 scripts; not yet checked on `P:\` | `dayz-vehicles` |
| Long log messages are cut around 255 characters. | Only by the 1.29 retail logger. Neither DayZDiag 1.30 nor the 1.30 retail server cuts. | Measured | `dayz-mod-workflow` |
| `ExpansionVehicleBase` is the base of Expansion vehicles. | Third-party, DayZ Expansion: `ExpansionVehicleBase` is an obsolete stub on `Transport`; current Expansion vehicles derive from `CarScript`. | Third-party mod behaviour, not vanilla: read in the DayZ Expansion scripts (commit `14fd692`) | `dayz-mod-dev` |

## Models, winding and collision

| Old claim | What holds | Evidence | Depth |
|---|---|---|---|
| Convert Blender to DayZ with the rotation `(x, z, -y)` (determinant +1), then reverse every face. | Blender is right-handed and DayZ left-handed. The map is the reflection `(x, y, z) -> (x, z, y)` (determinant -1), with the face order kept and the normals negated: `py3d.blender_to_dayz()`. The old recipe renders solid but **mirrored**, and no winding gate can see a mirror; only a chiral test model (a letter "F") shows it. | Measured in game on DayZDiag 1.29.163709 with one chiral model exported three ways; repeated on a character, a garment and an animation track. | `dayz-model-pipeline` |
| A GLB or glTF source needs every face reversed after the axis swap. | It does not. glTF front faces are counter-clockwise like Blender's, so after the determinant -1 map the winding is already right; the reversal renders inside-out. The old rule came from a build that shipped a stray raw MLOD at the PBO root, which the engine loaded instead. | Measured in game on two GLB-origin projects | `dayz-model-pipeline` |
| The collision selection must be spelled `Component01` with a capital C or the object silently loses all collision. | `Component01` and `component01` collide identically; binarize writes both as `component01`. The measured silent failure is a collision LOD with **no** `ComponentNN` selection at all, or a closed part left out of every component beside covered ones: it takes no ray and the player walks through, with no log line. | Measured in game on DayZDiag 1.29.163709 with byte-identical 2 m boxes, packed binarized and unbinarized, as an item and as a `HouseNoDestruct` | `dayz-p3d-audit` |
| Inverted collision winding lets the player walk through the object. | Outward-wound collision boxes took no Geometry, View or Fire LOD raycast, yet the physics-world ray hit them, they stopped a walking player about 0.36 m before the face, and a player stood on top. A walk does not diagnose winding either way. The raycast intersection modes are the ones in `ObjIntersect`. | Measured in game on DayZDiag 1.29.163709. `ObjIntersect` at `P:\scripts\3_game\constants.c:31-38` | `dayz-p3d-audit` |
| Fix an inverted face by swapping `vertices[1]` and `vertices[2]`. | That swap turns a quad into a crossed face. Reverse the whole vertex order (`face.vertices.reverse()`), and only on the faces that read outward. | Measured offline with py3d on synthetic boxes | `dayz-p3d-audit` |
| When a collision LOD's winding disagrees with the Visual LOD, reverse the collision LOD to match. | Never. The relative check also fires on healthy collision LODs under an inside-out Visual LOD. Decide per closed, convex component (every face must point inward) and reverse only the outward faces. | Measured offline; the paired in-game test is the one in the row above | `dayz-p3d-audit` |
| An inverted collision LOD hides behind a correct-looking model because the renderer draws both sides. | DayZ renders single-sided with backface culling. | Two independent in-game cases | `dayz-p3d-audit` |
| The MLOD face flag `0x20000` makes a face render two-sided. | Setting `0x20000` did nothing in game; double-siding the geometry works. Whether another "both sides" bit works (the Bohemia wiki names `0x00000020`) was never tested. | Measured in game | `dayz-vehicles` |
| A translation's `offset0`/`offset1` in `model.cfg` are metres, and the axis only gives direction. | That is true for rotations. For a translation the offsets count lengths of the axis: movement is offset times axis length. On a 1 m axis the offset reads in metres. | Read in binarized models; the engine behaviour is inferred, not measured | `dayz-model-pipeline` |
| A `CfgNonAIVehicles` proxy class can have any name. | A proxy class that is not `Proxy` plus the basename of its `model` draws nothing. Also, a slot added to a vanilla proxy class (`ProxyBattery_Car`) never drew the attachment; a `ProxyAttachment` class of the item's own, with its own proxy model, did. | Measured in game, one item | `dayz-model-pipeline` |
| In a staged build, "Material not loaded" messages are tolerable. | Binarize embeds a face material it cannot find **empty** in the ODOL (no shader, no stage texture, no surface) while the build says "Build Successful". Stage every cited file under the folder passed as `-addon`. | Measured over 11 builds | `dayz-build-pbo` |
| The binarize `-temp` folder must stay under `P:\`. | A habit, not a measured requirement: nine binarized builds with a local `-temp` worked. | Measured | `dayz-build-pbo` |
| The eleven masses of the vanilla `human.ragdoll` add up to 73.8 kg. | 73.9 kg. | Re-added from the file; not yet checked on `P:\` | `dayz-physics-engine` |

## UI

| Old claim | What holds | Evidence | Depth |
|---|---|---|---|
| `hexact`/`vexact 1` are physical screen pixels. | Exact units are 1/1080 of the screen height, on both axes. A 400-unit panel drew 400 px wide at 1920x1080 and at 2560x1080, and 267 px at 1280x720. | Measured in game | `dayz-ui-development` |
| A font with no size key ignores its widget box. | An unnumbered bitmap face, or an SDF face with no size key, follows its box. A numbered bitmap face keeps its pixel size. | Measured in game at 1080p and 720p | `dayz-ui-development` |
| 1.30 layout variants can only add widgets. | True only for hand-written, name-keyed files. A variant in the Workbench format (widgets matched by `Prefab` id) hides, recolours and adds vanilla widgets in place. | Measured on DayZDiag 1.30.164200 and 1.30.164289 | `dayz-ui-development` |

## Animation

| Old claim | What holds | Evidence | Depth |
|---|---|---|---|
| The 1.29 player and creature animation graphs are opaque binaries. | They are text `.agr` files in the `$AnimGraph 7` format. 1.30 changed the syntax, not text versus binary. | Read in the 1.29.0.163709 extraction; not yet checked on `P:\` | `dayz-animation-pipeline` |
| In 1.30 a mod can patch individual animation sub-graphs. | Unsupported. Adding a vehicle type still touches `Vehicles.agf`, `player_main.ast`, `player_main.asi` and, above 12 types, `player_main.agr`, all at vanilla paths, so only one graph mod can load. | Read in the 1.30 data files; not yet checked on `P:\` | `dayz-animation-pipeline` |
| `GetBoneIndexByName` returns -1 for a bone it cannot resolve. | It returned negative hash-like ids for `RightHand` and others, not -1. Test for a negative value. | Measured on DayZDiag 1.30.164014 | `dayz-animation-pipeline` |
| A stopped rider's head stays within 0.4 mm of the clip's pose. | In later first-person runs the stopped head moved by several centimetres between runs and between survivor classes. Log the eye position at every look. | Measured on DayZDiag 1.30.164200 | `dayz-animation-pipeline` |

## Testing, building and infrastructure

| Old claim | What holds | Evidence | Depth |
|---|---|---|---|
| DayZ Tools is Steam app 1042420. | DayZ Tools is app 830640 (DayZ is 221100). | Steam | `dayz-preflight` |
| `vonCodecQuality` has a ceiling below 30. | It goes up to 30, as the shipped `serverDZ.cfg` says. | Shipped config; not yet checked on `P:\` | `dayz-test-ingame` |
| `globals.xml` lives in the mission root. | It lives in the mission's `db/` folder. | Server mission files; not yet checked on `P:\` | `dayz-persistence` |
| The retail DayZServer never finishes loading the mission on a developer machine. | Not reproduced on 1.30.164289. | Measured | `dayz-test-ingame` |
| A `DSCheckSignatures` negative control made by flipping one byte of the PBO always fails. | It can pass. Change hashed content and recompute the trailer. Another build's PBO works as a control only when the two builds differ in an entry the signature covers; for a change that touches only models or textures, the `.c`-byte control is the one that can fail. | Measured | `dayz-test-ingame` |
| AddonBuilder's exit code tells you whether the build worked. | AddonBuilder exits 0 on a failed build (`[ResultCode]=1` in its log), and prints "Build Successful" for a PBO that lost every model. Accept a binarized build only when the PBO has one ODOL per `.p3d`. | Measured | `dayz-build-pbo` |
| `PrintWindow(PW_RENDERFULLCONTENT)` returns a black frame for the game window. | With the Windows session unlocked and the display on, it captures the scene. A locked session fails outright (`capture_backend_failed`). | Measured, more than 20 captures | `dayz-mcp-verify` |
| Restart Steam to fix a stale `ActiveProcess` pid. | Copy the live pid, from a shell outside any sandboxed app. A shell inside a sandboxed app sees a private registry copy. | Measured | `dayz-test-ingame` |
| A public web mirror of the script API is a usable reference. | Mirrors move and go stale: one that was in use now redirects elsewhere and its Doxygen pages return 404. Read `P:\scripts`. | Checked 2026-11 | `dayz-ui-development` |
| The Nasdara weapons (SCARL, Luger, LeeEnfield, MP18) have no model and no config class. | True on 1.30.164014 only. Since 1.30.164200 they ship in `weapons_nasdara.pbo`. | See `dayz-1-30-build-history.md` | `dayz-weapons` |

## How these got in, and the rule that keeps them out

Every row above was once written with confidence. The common causes:

- **A rule corrected at its source but not at its call sites.** The winding rule was fixed in one file and stayed wrong in six others. When a fact changes, grep every file that states it.
- **A symptom read as its cause.** "The player walks through" was assumed from missing raycasts; a walk test later showed physics still stopped the player.
- **One measurement generalised.** A door-proxy finding was written as a rule for wheels, whose frames are mirrored per side.
- **A test that cannot fail.** An in-game A/B that judges "which side renders" cannot see a mirrored model. Use a control that can show the defect.
- **A measurement on the wrong build or the wrong mod.** One run loaded a different registered mod, and the missing compile errors were read as a fix. Read the run's `-mod=` line before its verdict.
