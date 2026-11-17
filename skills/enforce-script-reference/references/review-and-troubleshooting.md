# Review checklist and troubleshooting

What to scan for before handing over Enforce Script code, then a symptom table (error, cause, fix) for the failures the knowledge pack's projects hit most. Rule numbers refer to `hard-rules.md`. A line cited as `P:\...:N` was opened on `P:\`; rows that name a mod were measured in that mod and not re-run here.

## Review checklist

Before delivering any Enforce Script code, check:

- [ ] No ternary operators
- [ ] `foreach` runs over stored collections, not over a temporary a method returns
- [ ] All variables are declared before loops and conditions, and no local name is reused in sibling branches
- [ ] Every member field has the `m_` prefix
- [ ] `ref` on member fields that own their target; never on parameters, return types or typedefs, and never `new ref` (on a local it is valid and redundant)
- [ ] No `new` allocations inside repeated timer callbacks
- [ ] `GetGame()` is null checked in every destructor, and destructors do not call other engine globals unchecked
- [ ] Every `Cast()` result is null checked before use
- [ ] Every `ctx.Read()` return value is checked
- [ ] Synced variable writes are wrapped in `#ifdef SERVER` and followed by `SetSynchDirty()`
- [ ] `RegisterNetSyncVariable*` is called in the constructor, not in `EEInit`
- [ ] Reference cycles are broken in destructors
- [ ] `override` methods are contiguous: no custom methods between the overrides of a `ScriptedWidgetEventHandler`
- [ ] Periodic ticks are centralized (no repeating `CallLater` per instance)
- [ ] `IsDedicatedServer()` is used instead of `IsServer()` or `IsClient()` for side checks made during load
- [ ] Action tool checks use `IsKindOf()`, not `GetType() ==`
- [ ] Actions that need a tool in hand use `CCINonRuined`, not `CCINone`
- [ ] Server RPC handlers repeat the checks of the client action condition
- [ ] Entity identity is compared the right way: config class (`GetType()`, `IsKindOf`) against script class (`ClassName()`), see `api-patterns.md`
- [ ] Layout paths in `GetLayoutFile()` match `$PBOPREFIX$` exactly
- [ ] The construction of a `ScriptViewMenu` is guarded with a `GetLayoutRoot()` null check
- [ ] Placed objects have `RemoveAction(ActionTakeItem)` and `RemoveAction(ActionTakeItemToHands)`
- [ ] `inputs.xml` uses the `<modded_inputs>` root tag (not `<modinfo>`)
- [ ] `CfgMods` in `config.cpp` has the `inputs` entry (rule 37)
- [ ] No custom `<exclude>` includes `inventory` while a camera or sight is active (it suppresses the four `UAAim*` axes, rule 37b)
- [ ] Nothing in the exclude set reaches `aiming` through an include; `menu` does, through `inventory` (rule 37b)
- [ ] A sight or turret for a seated player mods `DayZPlayerCamera1stPersonVehicle` instead of giving up the pawn (rule 37d); if old code still gives it up, it rebuilds `StartCommand_Vehicle` and is known not to restore the camera (rule 37c)
- [ ] Overrides of a vanilla `inventorySlot`: use `=` when vanilla defines it as a string, `+=` only when vanilla defines it as an array
  - `+=` appends to the class's own current list, not to the parent's (measured 2026-09-10 with `ConfigGetTextArray` at the end of `OnMissionStart`: with the GunRacks mod re-listing `Shoulder`, `Melee` and the LFSecure mod adding `LFS_Gun_1..3`, `Rifle_Base` read `Shoulder,Melee,LFS_Gun_1..3,Shoulder,Melee,GunRack_Gun_1..6`; `Pot` patched by LFPowerGrid kept `CookingEquipment`). Add only the new values; the patches of two mods stack in load order. A class that redefines the array (70 of 139 `Edible_Base` descendants do) does not inherit a patch made on its base class: generate one patch per class with its exact parent (SP-LFS-4).

## Areas to verify per project

Common risk areas. They are places to check against `P:\scripts\`, not verified APIs in themselves:

- Entity identity: config type, script class name and inheritance check.
- Entity lifecycle: constructor, init, action registration, persistence save and load, sync callbacks, delete and destructor.
- Return values of object creation and inventory creation.
- The format of a config lookup path.
- Math and string helpers that are missing or differ between versions.
- Which target a server to client RPC is sent on.

Failure patterns that keep coming back:

- The UI or input stays locked because close or the destructor did not release focus or input state.
- A synced variable never reaches the client because it was registered too late.
- An RPC runs on the wrong side because the server and client split was read from the wrong helper.
- Entity creation fails silently because the object or the cast result was not checked.
- A config lookup fails because of the path format.
- A timer problem shows only after long server uptime.

## Troubleshooting: common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| **Segfault on shutdown** | `delete` on an object something else still references | Replace `delete x;` with `x = null;` and let reference counting free it |
| **"Illegal write to memory"** | Arrays or maps allocated inside a repeating `CallLater` callback | Move them to member fields and `Clear()` them each tick instead of `new` |
| **Null pointer after a `Cast`** | The result was used without a null check | Always `if (Cast(obj)) { ... }`; never assume a cast succeeds |
| **Dabs `ObservableCollection` not updating the UI** | The binding is set up but `NotifyPropertyChanged` is not called | Call `NotifyPropertyChanged("PropertyName")` when the data changes |
| **Reference cycle leak** | A collection holds a view and the view holds the controller | Break it in the destructor (`m_Controller = null;`) and `Clear()` the collection on close |
| **UI colour flashes when the hover ends** | The hover cache was not updated when the controls were disabled | Update the cache (`CacheColor(widget, newDisabledColor)`) in `SetControlsEnabled` |
| **Hover state stays after a drag** | `m_HoveredWidget` was not cleared when the drag started | Reset `m_HoveredWidget = null;` in `OnMouseButtonDown` |
| **Player stuck with input locked** | The input lock is not released in the destructor | Add the unlock to the `~ClassName()` destructor |
| **Synced variable does not reach the client** | `RegisterNetSyncVariable*` was called in `EEInit` instead of the constructor | Register in the constructor; `EEInit` is too late |
| **Layout child counts do not match** | Unbalanced braces or child blocks | Count `{` and `}` in the layout file; the two counts must be equal |
| **"Undefined variable" in an `if`/`else`** | The variable is declared in one branch and used in the sibling branch | Declare it before the condition: `string result; if (...) { result = "a"; } else { result = "b"; }` |
| **`CallLater` loses precision after 4.5 hours** | Reported as a 32 bit float overflow in the engine (not checkable on `P:\`, see rule 21) | Use one central manager with the `Timer` class, or resync after 4 hours |
| **`IsKindOf` returns false unexpectedly** | A config class name is compared with a script class name | Identify entities with `GetType()`: `if (entity.GetType() == "MyItem")`, not `if (entity.ClassName() == "MyItem")`; for the config against script parent case see `api-patterns.md` |
| **String concatenation compiles but prints nothing** | A rare case with very long concatenation chains | Split into several statements when there are more than 5 concatenations |
| **Null pointer in a `foreach` over a temporary** | `foreach` runs over the return of a method, a temporary | Store it in a local first: `TStringArray arr = GetItems(); foreach (string s : arr) { }` |
| **`CONFIG_NOT_FOUND` in the logs** | The config path is in the wrong format | Use `"CfgVehicles ClassName propertyName"`: separated by spaces, not dots |
| **RPC runs on the wrong side** | A synced variable is written outside `#ifdef SERVER` | Wrap the write and `SetSynchDirty();` in `#ifdef SERVER` ... `#endif` |
| **`CreateObjectEx` fails silently** | The return value or the entity cast is not checked | `EntityAI e = EntityAI.Cast(obj); if (!e) return;` before using it |
| **Member variables of a modded class are unstable** | Some entity classes may have trouble with added member variables | Safe for `DayZGame`. For `ItemBase` and `PlayerBase` use an external static map if unsure (rule 25) |
| **Widget colour stays black or invisible** | The widget is not in the scene tree, or a parent is hidden | Call `FindAnyWidget` from the root and check every parent is `Show(true)` |
| **`ScriptInvoker` crash on shutdown** | `Remove()` is called on a null invoker during cleanup | Null check first: `if (MyClass.Event_X) MyClass.Event_X.Remove(cb);` |
| **`Math.Clamp` not found** | An outdated reference; it exists (`P:\scripts\1_core\proto\enmath.c:531`) | Use `Math.Clamp(val, min, max)`. `Math.Min`, `Math.Max` and `Math.Sqrt` exist too |
| **`IndexOfFrom` not found** | An outdated reference; it exists (`P:\scripts\1_core\proto\enstring.c:271`) | Use `str.IndexOfFrom(startPos, searchStr)`. `LastIndexOf` (`:253`), `Hash` (`:223`) and `Replace` (`:156`) exist too |
| **A string copy changes with the original** | `ToLower` changes the string in place (`P:\scripts\1_core\proto\enstring.c:171`) | Copy first: `string lower = original + ""; lower.ToLower();` The `+ ""` forces a copy |
| **RPC collision with other mods** | Low RPC IDs | Use a high unique base (`START_RPC = 25416533`) and let the enum count up from it; see `networking.md` |
| **`GetScreenPos` marker shows behind the camera** | The `z` part is not checked | `GetGame().GetScreenPos(pos)[2] <= 0` means behind the camera: hide the widget |
| **Layout path crash and a ghost menu** | `GetLayoutFile()` returns a path that does not match `$PBOPREFIX$` | Use the exact prefix: if `$PBOPREFIX$` is `SimpleGroup`, return `"SimpleGroup/gui/layouts/file.layout"` |
| **A `ScriptViewMenu` blocks every other menu** | The layout failed but the singleton was set | Guard: `if (!dialog.GetLayoutRoot()) { s_Instance = null; dialog = null; return; }` |
| **Action does not appear while holding the tool** | `CCINone` is used with a tool in hand check | Change to `CCINonRuined` (rule 30) |
| **Action appears on the client but the server rejects it** | The client uses `IsKindOf()` and the server `GetType() !=` | Use the same check on both sides (`IsKindOf` preferred) |
| **Keybind does nothing** | Wrong `inputs.xml` format, or no reference in the config | `<modded_inputs>` root tag, the `inputs` entry in `CfgMods`, and a read such as `GetGame().GetInput().LocalPress()`; `skills/_shared/enscript/integrations/input_bindings.md` lists the three silent failures |
| **Attachment slot does not accept items** | The vanilla `inventorySlot` is a string and the mod uses `+=` | Bohemia ticket T148506: `+=` on a string `inventorySlot` fails silently; declare it again as `inventorySlot[] = {"vanilla_slot", "custom_slot"}` |
| **Item fits the slot but the quantity is limited** | The vanilla `varQuantityMax` is lower than needed | Override it in `config.cpp`: `class Stone: Inventory_Base { varQuantityMax = 16.0; }` |
| **A placed item can be picked up by dragging** | Only `IsTakeable()` is overridden | Also `RemoveAction(ActionTakeItem)` and `RemoveAction(ActionTakeItemToHands)` in `SetActions`, and `CanPutInCargo()` returning false |
| **`SetObjectTexture` has no effect** | `hiddenSelections` is not declared in the config, or the selection name does not match the P3D model | Check that `hiddenSelections[]` in the config matches the named selections in the P3D exactly (case sensitive). Read them back with `GetHiddenSelectionsTextures()`, which returns a `TStringArray` (`P:\scripts\3_game\hiddenselectionsdata.c:28`, override at `P:\scripts\3_game\entities\entityai.c:2796`); empty means no selections. There is no `GetObjectTextures()` (plural) in vanilla, and calling a method that does not exist fails the whole script at compile; see the `SetObjectTextureGlobal` row below |
| **`SetObjectTexture` changes the wrong part** | The wrong index | The index is the position in the `hiddenSelections[]` array (0 based), not the selection name. A barrel has 1 selection, at index 0 |
| **The texture path read back differs from the config** | The engine normalizes paths | The getter works per index: `proto native owned string GetObjectTexture(int index);` (`P:\scripts\3_game\entities\entityai.c:2882`; its material twin `GetObjectMaterial(int)` is at `:2885`). The config reads `"\dz\gear\..."` and the engine is said to return `"dz\gear\..."` with no leading backslash, so save and restore from the getter, not from a hard-coded config path. This normalization claim needs checking again: it was first written against `GetObjectTextures()`, which does not exist, so it cannot have come from that call |
| **A custom barrel or container lacks vanilla behaviour** | The script extends `ItemBase` instead of the vanilla script class | Extend `Barrel_ColorBase` (not `ItemBase`) for barrels. Always extend the vanilla script class that matches the config parent, and list the addon of the config parent in `requiredAddons` (for example `DZ_Gear_Containers`) |
| **A procedural texture is ignored** | The feature may not exist in DayZ | Read the RPT: "unknown procedural" means it was stripped; "class/extension not found" means the parser exists. `color()` is the most likely to work; test `text()`, `r2t()`, `ui()` and `extension()` first |
| **`SetObjectTextureGlobal` does not compile** | The method does not exist: no vanilla script under `P:\scripts\` declares or calls it | Do not call it; a call to a missing method fails the whole script at compile. Use `SetObjectTexture` and check the sync in multiplayer |
| **Diag server crash: `SCRIPT (E): "Method argument can't be strong reference"` then `Can't compile "World" script module!` (SP-047)** | The DayZDiag compiler rejects `ref` on a method parameter as fatal; the retail compiler lets it pass, so a mod tested only on retail can carry hidden cases that show only under diag | Drop the outer `ref` on the parameter: `ref array<ref X> p` becomes `array<ref X> p` (the inner `<ref X>` is legal). [VERIFIED in the LFPowerGrid mod 2026-06-18, `LFPG_DeviceInspector.c`] |
| **`SCRIPT (E): Broken expression (missing ';'?` on a clean variable declaration (SP-073)** | `owned` is an Enforce keyword (a reference modifier, as in `proto native owned string GetWorldFile()`, `P:\scripts\2_gamelib\gamelib.c:57`); declaring a variable with that name (`EntityAI owned;`) makes the parser fail on the declaration line with an error that never names the keyword. Same family: `out`, `ref`, `autoptr`, `notnull`, `local`, `event`, `reference`, `external`, `volatile` | Rename it (for example `EntityAI cached;`). When "Broken expression" points at an innocent declaration, suspect a keyword before missing punctuation. [VERIFIED in the LFPowerGrid mod 2026-07-20: `EntityAI owned;` in a mission `init.c` compiled once renamed `cached`] |
| **`CarScript` `OnPossess` and `OnUnPossess` never fire; `GetVelocity(this)` on a grounded owner returns the commanded velocity; the client's ghost pose stays after dismount (SP-280)** | (1) `P:\scripts\3_game\entities\pawn.c:224-232` declares `protected event void OnPossess()` and `OnUnPossess()`; a `protected override event` in a derived `CarScript` received no calls (0 log lines in 3 test runs with real get in and get out, on both sides), so it cannot be used as a hook for the possession change. (2) With a commanded force or velocity, `GetVelocity(this)` on a grounded owner returns the last commanded velocity (−1.96 m/s with the helicopter at rest; a contact probe read 0.0003), so do not decide "grounded" from velocity. (3) `Synchronize()` plus `ForceCorrection()` in `ForceUpdateLightsStart` (the start of get out, a server hook) does not correct the client's ghost pose on dismount: after giving up possession the client shows the creation transform (the X and Z of the spawn). | (1) Detect the possession change by polling `IsOwner()` in the owner tick (or by the owner tick going missing: 1.48 s without it before `OnDriverExit`). (2) Decide "grounded" from contact or altitude, not from `GetVelocity`. (3) Do not rely on `Synchronize()` or `ForceCorrection()` to correct the client pose on dismount; the client keeps the spawn transform. [MEASURED 2026-08-17 in the LFHeli mod, `LFHeli_Base.c`] |

## Most common fixes

1. **Crash on close?** Remove `delete`, check the destructors, clear the collections.
2. **Memory leak?** Break reference cycles in destructors; `Clear()` collections before close.
3. **UI not updating?** Call `NotifyPropertyChanged` when the data changes; check the binding syntax.
4. **Input stuck?** Unlock in the destructor; check `ChangeGameFocus` is balanced and `SetDisabled(false)` was called.
5. **Synced variable not syncing?** Move `RegisterNetSyncVariable*` to the constructor; check the `#ifdef SERVER` wrap.
