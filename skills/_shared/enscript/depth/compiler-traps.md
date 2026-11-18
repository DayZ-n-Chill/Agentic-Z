# Compiler traps

Ways to break the Enforce compiler that give a misleading error, or none until the script module compiles at boot: method scope, dead vanilla symbols, names that collide with keywords or classes, statements split over lines, and offline checks that look green while nothing compiled. A line cited as `P:\...:N` was opened on `P:\`; the measured results were not re-run here.

## Locals have method scope, not block scope: the same local in two `case` blocks is a fatal compile error

Enforce gives local variables method scope, not block scope (like `var` in old JavaScript). Declaring the same variable in two `case` blocks, or any two blocks, of the same method gives `SCRIPT (E): Multiple declaration of variable 'X'`, then `Can't compile "World" script module!`, and the server does not start. The DayZDiag compiler rejects it; retail may let it pass, so it stays hidden when only retail is tested (the same split between diag and retail as `ref` on a parameter, memory rule 12 in `hard-rules.md`). Fix: use a different name per block (for example `cgVel` and `cgVelRec`) or declare it once at the top of the method. Example: `vector cgVel` declared in both the `FLIGHT` and the `EMERGENCY_RECOVERY` branch of one state machine step; the compile on the diag server caught it (`Multiple declaration of variable 'cgVel'`).

## Failures that only show when the module compiles at boot

Five failure modes that a text search of the vanilla tree does not catch and that only surface when the script module compiles at boot. Each was checked against the vanilla scripts on `P:\`.

### Defined is not alive: vanilla ships retired classes inside `/* */`

`modded class X` on a vanilla class that is commented out gives `Unknown type X`, and the script module dies at boot. A plain text search finds the class and says nothing, because its text is still there.

The standard case: the whole of `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfishing.c` is one block comment. It opens at `:1` with `/*class ActionFishingCB : ActionContinuousBaseCB` and closes at `:52`, after `class ActionFishing`. The live class is `ActionFishingNew` in `actionfishingnew.c` in the same folder, the one `RegisterActions` inserts (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:246`). Anyone modding "the fishing action" by name lands on the dead one.

Rule: before `modded class X`, confirm that X is not inside a block comment. Search for the declaration and read the head of the file. A symbol index that records commented out classes answers this in one query (the script validator under `scripts\tools\dayz-script-validator\` builds one); without an index, read the file.

### `TextWidget` has no `GetText()`, and the live signatures differ

`class TextWidget extends Widget` (`P:\scripts\1_core\proto\enwidgets.c:189`) declares `SetText`, `GetTextSize` (`:210`) and `GetTextProportion` (`:214`), but no `GetText`. Neither do its subclasses `MultilineTextWidget` (`:219`) and `RichTextWidget` (`:224`). A call to it does not compile, and reads like a typo.

`GetText` exists in exactly three places, and not with one signature:

| Class | Declared at | Signature |
|---|---|---|
| `MultilineEditBoxWidget extends TextWidget` (`:313`) | `P:\scripts\1_core\proto\enwidgets.c:318` | `proto void GetText(out string text)` |
| `EditBoxWidget extends UIWidget` (`:347`) | `P:\scripts\1_core\proto\enwidgets.c:349` | `proto string GetText()`, which returns the string |
| `ButtonWidget extends UIWidget` (`:381`) | `P:\scripts\1_core\proto\enwidgets.c:389` | `proto void GetText(out string text)` |

So moving a read from an `EditBoxWidget` to a `ButtonWidget` silently changes how it must be called. To show text use `TextWidget.SetText`; to read it back the widget must be one of the three above.

### Overriding a method that vanilla defines only under an inactive `#ifdef`

If vanilla declares a method inside `#ifdef PLATFORM_CONSOLE` (or any define that is not active in the PC release build), overriding it from a mod gives `no function to override in base class`, and the client hangs on the loading screen: no crash, no useful RPT line.

Verified case: `P:\scripts\5_mission\gui\inventorynew\inventory.c:1307` is `#ifdef PLATFORM_CONSOLE` and `:1308` is `protected string GetConsoleToolbarText(int mask)`. On a PC build that method does not exist, so `override string GetConsoleToolbarText(...)` freezes the load.

This is the same family as the `DEVELOPER` against `DIAG_DEVELOPER` trap in `pitfalls-advanced.md` and as the `#ifdef BOT` case at the top of `hard-rules.md`: before overriding, check whether the vanilla declaration sits under a define, not only whether it exists.

### A method named exactly like a vanilla class resolves to the type

Enforce identifiers are case sensitive. Declare a method whose name matches a vanilla class exactly, then call it as a bare statement `Name(args);`, and the compiler binds `Name` to the type (a cast or construction) instead of the method: `Types X and Y are unrelated`.

`FoodStage` is the real collision: `P:\scripts\4_world\classes\foodstage\foodstage.c:22` declares `class FoodStage`, so a helper `void FoodStage(int n)` called as `FoodStage(3);` fails. Using the result in an expression (`x = FoodStage(3);`, `FoodStage(3).Foo();`) binds to the method and compiles; it is the bare statement that breaks. Fix: rename the method (`FoodStageInfo`).

### A new action needs registration, not just a class

`extends ActionBase` alone is dead code: the action never reaches the player. Registration goes through `void RegisterActions(TTypenameArray actions)` at `P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:27`, called from `:6`.

Which tool for which job:

- **Change the behaviour of an existing action**: `modded` the action class. `extends` is useless here, because the engine and the mission create the vanilla name.
- **Add a new action**: `extends ActionBase`, plus a `modded ActionConstructor` that inserts it in `RegisterActions`, plus `AddAction` in the item's `SetActions()`. Until 1.29 those three were the whole contract. Since 1.30 they are still required but not always enough: register the replacement too when vanilla dropped the old class. `ActionFillBottleBase` is `[Obsolete]` and is not in `RegisterActions`; the live class is `ActionObtainLiquidBase` (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:156`). Info only actions use `InitInfoData` and return false from `CanBeStarted()` (the manager will not `ActionStart` them). The liquid target condition is `CCTLiquid`. Animation overrides live on `EntityAI.m_EntityActionOverrides`. Details: `dayz-1-30-enforce-script.md`.

How far it reaches: `modded` on a `*Base` class applies to every descendant at once. That is the right tool when a blanket change is the goal, and the wrong one when the goal is a single new item.

### Two common beliefs, both disproved by the vanilla tree

Two beliefs circulate: that Enforce has no C style casts, and that `string + bool` does not compile. A sweep of the whole vanilla tree disproved both. The tree ships and compiles, so one live counterexample settles it.

**C style casts exist and vanilla uses them.**

```c
a = (int)h << 24;                                   // P:\scripts\1_core\proto\proto.c:312, h is float (:310)
float rand_float = (float)random_int / (float)max_range;     // P:\scripts\1_core\proto\enmath.c:110
ctx.Write((int)GetIsFrozen());                      // P:\scripts\3_game\entities\entityai.c:3206
int row= (int)Math.Floor( x / ITEMS_IN_ROW );       // P:\scripts\5_mission\gui\inventorynew\inherited\vicinityslotscontainer.c:262
```

`Math.Floor` returns `float` (`P:\scripts\1_core\proto\enmath.c:427`), so it is not itself the conversion; its result is usually assigned to an `int` or wrapped in a cast. `ToInt()` is a member of `class string` (`P:\scripts\1_core\proto\enstring.c:20`), so it converts a string to an `int`, not a `float` to an `int`. `class float` (`P:\scripts\1_core\proto\enconvert.c:109-116`) has only `ToString`.

**`string + bool` compiles.** Vanilla concatenates calls that return `bool` into debug strings outside any `#ifdef`:

```c
text += "Disabled: " + GetIsSimulationDisabled() + "\n";   // P:\scripts\3_game\entities\entityai.c:3300
```

with `proto native bool GetIsSimulationDisabled();` at `P:\scripts\3_game\entities\entity.c:6`. If that did not compile, the game module would not load. `bool.ToString()` exists too (`P:\scripts\1_core\proto\enconvert.c:1-8`, it returns `"true"` or `"false"`), but it is an alternative, not a requirement. There is no `BoolToString` helper anywhere in the tree.

Consequence: both rules were removed from the script validator (`scripts\tools\dayz-script-validator\`), where their modules keep the evidence in their headers. `ES-C-STYLE-CAST` produced 73 findings over the 2805 files of the vanilla tree, every one a false positive by construction. `ES-STRING-PLUS-BOOL` found none, because it only looked for the literal form (`"x" + true`) and vanilla never writes that; the rule went anyway, because a rule whose stated reason is false teaches the falsehood.

Still open, and only a compile settles it: what `"x" + someBool` actually prints (`"true"` and `"false"`, or `"1"` and `"0"`), whether the literal form `"x" + true` compiles (vanilla never uses it), and whether `(int)(-1.7)` truncates toward zero or toward minus infinity.

## Three ways to break the compiler without a readable error

Each cost one diag server run, and none can be guessed by reading vanilla: the compiler points at the wrong line or invents a missing `;`.

**1. A string concatenation cannot be split over several lines.** The compiler ends the statement at the line break, so this does not compile:

```c
return "type=" + top.GetType()
    + " wet=" + top.GetWet().ToString();      // Missing ';' at the end of line
```

The error appears on every continuation line (`Missing ';' at the end of line` once per line, plus a `Syntax error`), which suggests a problem with quotes or parentheses. Build the string in a variable, one statement per line:

```c
string desc = "type=" + top.GetType();
desc = desc + " wet=" + top.GetWet().ToString();
```

**2. `out` is a reserved keyword** (it marks `out` parameters, as in `GetPlayers(out array<Man> players)`, `P:\scripts\3_game\global\game.c:945`). Using it as the name of a local variable gives `Broken expression (missing ';'?)`, which neither names the identifier nor hints that the name is the problem. The `owned` row in `review-and-troubleshooting.md` lists the other keywords with the same effect.

**3. `Print(...)` at file level is not valid Enforce**: `Syntax error` and `Can't compile "<Module>" script module!`. It matters more than it seems, because `CfgConvert -test` accepts a `config.cpp` and does not compile Enforce, so a set of probe scripts can pass every offline check and never have compiled at all. Measured on 2026-08-31 on three probes that had this defect: the offline checks were green and no probe had ever reached the compiler.

The rule to take from this: the only check that validates Enforce is booting a module. A green `CfgConvert -test`, a custom linter or a text search for an anchor prove form, not compilation.

## A newline also ends the statement inside a condition

This extends item 1 above, which shows the compiler ending the statement at a newline only for string concatenation. The rule belongs to the parser, not to the `+` operator, and someone who searches for the symptom under `if` would not look there.

Measured in game: a condition split over two lines

```c
if (m_RestProbeArmed && startVel.Length() < REST_PROBE_SPEED_MPS
    && m_RestProbeLines < REST_PROBE_MAX_LINES)
```

gives `Expected ')', not a 'REST_PROBE_SPEED_MPS'` plus `Missing ';' at the end of line`, followed by `Invalid statement ')'`, `Unexpected scope` and `Syntax error` on the next lines. The error points at a parenthesis and the defect is the newline.

A cheap and decisive signal before writing: count the conditions that already span lines in the file. In that file there were none in about 4,700 lines; every condition was on a single line, including those with six clauses. That uniformity was not style, it was the parser. When a whole file avoids a convenient construct, assume first that the construct does not compile.

### A fourth false check: "Build Successful" from AddonBuilder

The section above warns that `CfgConvert -test`, a custom linter and a text search prove form and not compilation. One more belongs on that list, and it sits inside the build pipeline, which makes it the most misleading: AddonBuilder packs, it does not compile Enforce. In that same run:

| Check | Verdict | What it proves |
|---|---|---|
| Offline linter on the addon | `WARN=6 ERROR=0`, identical to the base | Form |
| AddonBuilder | `exit=0`, `Build Successful` | That the PBO was packed |
| PBO content check | The new string is inside | That the text travelled |
| **Server startup** | **`Can't compile "World" script module!`** | **Compilation** |

The first three were green and the module did not compile. That cost the whole boot of a test batch: a server, and a shared machine other sessions were waiting for.

What follows in practice: when the test machine is a queued resource, server startup is not only the check, it is the cheapest check there is, because it fails in about 20 s. Spending 20 s on a boot before queueing a 30 minute batch is arithmetic, not caution. In this repo that boot is `/dayz-gate`.

## Moving a method body between modules: field visibility moves with it

[EXACT] Enforce `protected` reaches only the declaring class and its descendants. A body moved into `5_Mission` (a facade and implementation split) reaches device state through parameters (`dev.m_Field`), and that compiles only if the field is public, because the implementation class is not a descendant of the class that owns the state. Measured: a tree with 48 linter warnings and 0 errors and a passing isolated binarize still killed the first server boot with `Variable 'm_DeviceId' is protected`, then `Can't compile "Mission" script module!`. The fields were public on the branch where the bodies were written, and that visibility change did not travel with the bodies (measured in game, DayZDiag).

[DESIGN] When a body moves across modules, the move list includes the visibility of every field the body touches, not only the helpers it calls: resolve the type of every variable and require public before calling the tree good. The check is the engine, not the linter: on 2026-09-26 the offline linter in that project gave the identical verdict on the broken and the fixed tree, and review missed it because it read the branch where the field was public. The script validator has a check for this pattern over the whole tree, `ES-PROTECTED-CROSS-MODULE` (see the README under `scripts\tools\dayz-script-validator\`); run it, and still boot the server before calling such a move good. Whether that check catches a receiver reached through a parameter, as here, was not measured.
