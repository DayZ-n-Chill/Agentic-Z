# Review and troubleshooting

What to check in Enforce Script before handing it over, and what a common error or symptom means, with its cause and fix. The rules behind the checks are in `hard-rules.md` and `action-and-input-rules.md`.

## Before handing code over

Language and memory:

- No ternary operators, and every statement on one line.
- `foreach` runs over a stored collection, never over a temporary a method returns.
- Variables are declared before loops and conditions; no local name repeats in sibling branches.
- Member fields carry `m_`.
- `ref` sits on owning member fields only: never on parameters, return types or typedefs, and never `new ref`.
- No `new` inside a repeated timer callback, and periodic ticks run from one manager, not a repeating `CallLater` per instance.
- Destructors null check `GetGame()` and every engine global, and break reference cycles.
- Every `Cast()` result and every `ctx.Read()` return is checked.

Networking:

- Synced variables are written inside `#ifdef SERVER` and followed by `SetSynchDirty()`, and registered in the constructor, not `EEInit`.
- Side checks during load use `IsDedicatedServer()`, not `IsServer()` or `IsClient()`.
- Server RPC handlers repeat the client action's checks.

Entities and actions:

- Identity uses the config class (`GetType()`, `IsKindOf`) where it matters, not the script class (`api-patterns.md`).
- Tool checks use `IsKindOf()`, and actions needing a tool use `CCINonRuined`.
- Placed objects remove `ActionTakeItem` and `ActionTakeItemToHands`.
- `override` methods of a `ScriptedWidgetEventHandler` sit together, with no custom methods between them.

UI and input:

- `GetLayoutFile()` paths match `$PBOPREFIX$`, and a `ScriptViewMenu` is checked with `GetLayoutRoot()` after construction.
- `inputs.xml` has the `<modded_inputs>` root, and `CfgMods` has its `inputs` entry.
- No exclude reaches `aiming` while a camera or sight is active, directly through `inventory` or through `menu`.
- A sight for a seated player mods `DayZPlayerCamera1stPersonVehicle` instead of giving up the pawn (`action-and-input-rules.md`).

Config:

- When overriding a vanilla `inventorySlot`, use `=` where vanilla defines a string and `+=` only where it defines an array. Measured in game with `ConfigGetTextArray`: `+=` appends to the class's own current list, not the parent's, and patches from several mods stack in load order, so add only the new values. A class that redefines the array does not inherit a patch on its base (70 of 139 `Edible_Base` descendants do), so write one patch per class with its exact parent.

Areas to check against `P:\scripts\` on every project: entity identity, the lifecycle order, the return of object and inventory creation, config path format, maths and string helpers that differ between versions, and which target a reply RPC uses.

## Errors and symptoms

| Symptom | Cause | Fix |
|---|---|---|
| Segfault on shutdown | `delete` on an object something else still holds | `x = null;` and let reference counting free it |
| "Illegal write to memory" | Arrays or maps allocated in a repeating `CallLater` | Member fields, `Clear()` each tick |
| Null pointer after a cast | The result was used unchecked | `if (Cast(obj)) { }` every time |
| Bound collection does not update the UI | `NotifyPropertyChanged` is never called | Call it when the data changes |
| Leak from a collection | The collection holds a view that holds the controller | Null the back reference in the destructor and `Clear()` on close |
| Colour flashes when hover ends | The hover cache was not updated on disable | `CacheColor(widget, disabledColor)` in `SetControlsEnabled` |
| Hover stays after a drag | `m_HoveredWidget` not cleared at drag start | Reset it in `OnMouseButtonDown` |
| Player stuck with input locked | The lock is not released in the destructor | Unlock in the destructor; balance `ChangeGameFocus`; call `SetDisabled(false)` |
| Synced variable never reaches the client | Registered in `EEInit` | Register in the constructor |
| RPC runs on the wrong side | A synced write outside `#ifdef SERVER` | Wrap the write and `SetSynchDirty()` |
| Layout child counts wrong | Unbalanced braces | Count `{` and `}` in the layout |
| "Undefined variable" in an `if` and `else` | Declared in one branch, used in the other | Declare before the condition |
| Null pointer in a `foreach` | Loop over a method's temporary return | Store it in a local first |
| `IsKindOf` false unexpectedly | Config name compared with a script name | Use `GetType()`; for a config parent that differs, see `api-patterns.md` |
| A long concatenation prints nothing (reported) | Very long chains | Split past about five concatenations |
| `CONFIG_NOT_FOUND` | Path written with dots | `"CfgVehicles ClassName propertyName"`, separated by spaces |
| `CreateObjectEx` fails silently | Return or cast unchecked | `EntityAI e = EntityAI.Cast(obj); if (!e) return;` |
| Modded class fields unstable on some entities (reported) | Added fields on entity classes | Safe on `DayZGame`; for `ItemBase` and `PlayerBase` a static map keyed by entity is the cautious choice |
| Widget colour black or invisible | The widget is outside the tree, or a parent is hidden | `FindAnyWidget` from the root; every parent `Show(true)` |
| `ScriptInvoker` crash on shutdown | `Remove()` on a null invoker | `if (MyClass.Event_X) MyClass.Event_X.Remove(cb);` |
| `Math.Clamp` not found | An old reference; it exists (`P:\scripts\1_core\proto\enmath.c:540`) | `Math.Clamp(val, min, max)`; `Min`, `Max` and `Sqrt` exist too |
| `IndexOfFrom` not found | An old reference; it exists (`P:\scripts\1_core\proto\enstring.c:271`) | `str.IndexOfFrom(startPos, searchStr)`; `LastIndexOf` (`:253`), `Hash` (`:223`) and `Replace` (`:156`) exist too |
| A string copy changes with the original | `ToLower` changes the string in place (`enstring.c:171`) | `string lower = original + ""; lower.ToLower();` |
| RPC collides with another mod | Low IDs | A high unique base such as `25416533`, counting up (`rpc-routing.md`) |
| Screen marker shows behind the camera | `z` not checked | Hide when `GetGame().GetScreenPos(pos)[2] <= 0` |
| Layout crash and a ghost menu | `GetLayoutFile()` does not match `$PBOPREFIX$` | Return `"MyMod/gui/layouts/file.layout"` for prefix `MyMod` |
| One `ScriptViewMenu` blocks all others | The layout failed but the singleton was set | `if (!dialog.GetLayoutRoot()) { s_Instance = null; return; }` |
| Action missing while the tool is held | `CCINone` plus a tool check | `CCINonRuined` |
| Action shows on the client, server rejects it | `IsKindOf()` on one side, `GetType() !=` on the other | The same check on both sides |
| Keybind does nothing | Wrong `inputs.xml` root, no `inputs` entry, or no read | See `../integrations/input_bindings.md` for the three silent failures |
| Slot refuses items | `+=` on a vanilla string `inventorySlot` (reported on the Bohemia tracker, T148506) | Redeclare `inventorySlot[] = {"vanilla_slot", "custom_slot"}` |
| Item fits the slot, quantity capped | Vanilla `varQuantityMax` too low | Override it: `class Stone: Inventory_Base { varQuantityMax = 16.0; };` |
| Placed item still drags | Only `IsTakeable()` overridden | Also remove the take actions and return false from `CanPutInCargo()` |
| `SetObjectTexture` has no effect | `hiddenSelections[]` missing, or names differ from the model (case sensitive) | Match them; read back with `GetHiddenSelectionsTextures()` (`P:\scripts\3_game\hiddenselectionsdata.c:28`, override at `P:\scripts\3_game\entities\entityai.c:2796`). There is no `GetObjectTextures()` |
| `SetObjectTexture` changes the wrong part | Wrong index | The index is the position in `hiddenSelections[]`, from 0 |
| Texture path read back differs from config | Reported: the engine drops the leading backslash | Read with `GetObjectTexture(int index)` (`entityai.c:2882`; `GetObjectMaterial(int)` at `:2885`) and restore from the getter |
| Custom barrel lacks vanilla behaviour | Script extends `ItemBase` | Extend `Barrel_ColorBase`, the script class matching the config parent, and require its addon (`DZ_Gear_Containers`) |
| A procedural texture is ignored | Unverified which kinds DayZ supports | Read the RPT: "unknown procedural" means stripped. `color()` is the safe one; test `text()`, `r2t()`, `ui()` and `extension()` first |
| `SetObjectTextureGlobal` does not compile | No vanilla script declares it | Use `SetObjectTexture` and check sync in multiplayer |
| Diag: `Method argument can't be strong reference`, then `Can't compile "World" script module!` | Diag rejects `ref` on a parameter; retail lets it pass | `ref array<ref X> p` becomes `array<ref X> p` (measured in a mod) |
| `owned` as a name: `Broken expression (missing ';'?` on a clean declaration | `owned` is a keyword (`proto native owned string GetWorldFile()`, `P:\scripts\2_gamelib\gamelib.c:57`). So are `out`, `ref`, `autoptr`, `notnull`, `local`, `event`, `reference`, `external` and `volatile` | Rename (`EntityAI cached;`); suspect a keyword before punctuation (measured in game) |

## Vehicle possession and pose

Measured in game in a helicopter mod:

- `Pawn` declares `protected event void OnPossess()` and `OnUnPossess()` (`P:\scripts\3_game\entities\pawn.c:223` to `:232`), but a `protected override event` in a `CarScript` received no calls on either side across real get in and get out. Detect a possession change by polling `IsOwner()` in the owner tick, or by the owner tick stopping (it stopped 1.48 s before `OnDriverExit`).
- With a commanded force or velocity, `GetVelocity(this)` on a grounded owner returns the last commanded velocity (-1.96 m/s at rest, where a contact probe read 0.0003). Decide "on the ground" from contact or altitude.
- `Synchronize()` with `ForceCorrection()` in `ForceUpdateLightsStart`, at the start of get out, does not fix the client's pose on dismount: the client shows the spawn transform. Do not rely on them for it.

## Quick fixes

| Problem | First thing to try |
|---|---|
| Crash on close | Remove `delete`, check destructors, clear collections |
| Leak | Break cycles in destructors; `Clear()` collections before close |
| UI not updating | `NotifyPropertyChanged` on change; check the binding |
| Input stuck | Unlock in the destructor; balance `ChangeGameFocus`; `SetDisabled(false)` |
| Synced variable not syncing | Register in the constructor; wrap writes in `#ifdef SERVER` |
