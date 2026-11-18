# Compiler traps

Which code makes the Enforce compiler give a misleading error, or none until the script module compiles at boot, and which offline checks look green while nothing has compiled.

## Locals have method scope

A local variable lives for the whole method, not its block, like `var` in old JavaScript. Declare the same name in two `case` blocks, or any two blocks, of one method and the diag compiler stops with `SCRIPT (E): Multiple declaration of variable 'X'`, then `Can't compile "World" script module!`, and the server does not start. Reported: retail may let it pass, so it hides when only retail is tested, the same split as `ref` on a parameter in `hard-rules.md`.

Use a different name per block (`cgVel`, `cgVelRec`) or declare it once at the top of the method.

## Retired classes inside block comments

`modded class X` on a vanilla class that sits inside `/* */` gives `Unknown type X`, and the module dies at boot. A text search still finds the class, because its text is there.

The usual case is fishing: the whole of `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfishing.c` is one block comment, opening at `:1` with `/*class ActionFishingCB : ActionContinuousBaseCB` and closing at `:52`. The live class is `ActionFishingNew` in `actionfishingnew.c` in the same folder, the one `RegisterActions` inserts (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:246`).

Before `modded class X`, read the head of the file that declares X. The symbol index built by the script validator under `scripts/tools/dayz-script-validator/` records commented out classes and answers this in one query.

## Methods under an inactive `#ifdef`

If vanilla declares a method only inside `#ifdef PLATFORM_CONSOLE`, or any define that is off in the PC build, overriding it gives `no function to override in base class` and the client hangs on the loading screen with no useful RPT line. Example: `P:\scripts\5_mission\gui\inventorynew\inventory.c:1307` is `#ifdef PLATFORM_CONSOLE` and `:1308` declares `protected string GetConsoleToolbarText(int mask)`, so `override string GetConsoleToolbarText(...)` freezes the load on PC.

Same family as the `DEVELOPER` against `DIAG_DEVELOPER` trap in `modded-class-and-defines.md` and the `#ifdef BOT` case in `hard-rules.md`: before overriding, check whether the declaration sits under a define, not only whether it exists.

## `TextWidget` has no `GetText()`

`class TextWidget extends Widget` (`P:\scripts\1_core\proto\enwidgets.c:189`) declares `SetText`, `GetTextSize` (`:210`) and `GetTextProportion` (`:214`), but no `GetText`; nor do `MultilineTextWidget` (`:219`) and `RichTextWidget` (`:224`). `GetText` exists in three classes, with two signatures:

| Class | Source | Signature |
|---|---|---|
| `MultilineEditBoxWidget extends TextWidget` | `enwidgets.c:318` | `proto void GetText(out string text)` |
| `EditBoxWidget extends UIWidget` | `enwidgets.c:349` | `proto string GetText()` |
| `ButtonWidget extends UIWidget` | `enwidgets.c:389` | `proto void GetText(out string text)` |

Moving a read from an `EditBoxWidget` to a `ButtonWidget` changes how it must be called.

## A method named like a vanilla class

Identifiers are case sensitive. Name a method exactly like a vanilla class and call it as a bare statement, `Name(args);`, and the compiler binds `Name` to the type: `Types X and Y are unrelated`. `class FoodStage` is declared at `P:\scripts\4_world\classes\foodstage\foodstage.c:22`, so a helper `void FoodStage(int n)` called as `FoodStage(3);` fails. Used inside an expression (`x = FoodStage(3);`) it binds to the method and compiles. Rename the method (`FoodStageInfo`).

## A new action needs registration

A class that `extends ActionBase` never reaches the player on its own. Registration goes through `void RegisterActions(TTypenameArray actions)` (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:27`, called from `:6`).

- To change an existing action, use `modded` on its class. `extends` does nothing here, because the engine creates the vanilla name.
- To add an action, write the class, insert it from a `modded ActionConstructor` in `RegisterActions`, and `AddAction` it in the item's `SetActions()`. In DayZ 1.30 also register the replacement when vanilla dropped the old class: `ActionFillBottleBase` is `[Obsolete]` and missing from `RegisterActions`; the live class is `ActionObtainLiquidBase` (`actionconstructor.c:156`). More in `dayz-1-30-enforce-script.md`.
- Info only actions use `InitInfoData` and return false from `CanBeStarted()`. The liquid target condition is `CCTLiquid`. Animation overrides live on `EntityAI.m_EntityActionOverrides`.

`modded` on a `*Base` class changes every descendant at once: right for a blanket change, wrong for one new item.

## C style casts and `string + bool` both compile

Vanilla compiles, so one live use settles it. C style casts:

```c
a = (int)h << 24;                                          // P:\scripts\1_core\proto\proto.c:312, h is float (:310)
float rand_float = (float)random_int / (float)max_range;   // P:\scripts\1_core\proto\enmath.c:110
ctx.Write((int)GetIsFrozen());                             // P:\scripts\3_game\entities\entityai.c:3206
int row= (int)Math.Floor( x / ITEMS_IN_ROW );              // P:\scripts\5_mission\gui\inventorynew\inherited\vicinityslotscontainer.c:262
```

`Math.Floor` returns `float` (`P:\scripts\1_core\proto\enmath.c:427`), so it is not the conversion itself. `ToInt()` belongs to `class string` (`P:\scripts\1_core\proto\enstring.c:20`), and `class float` has only `ToString` (`P:\scripts\1_core\proto\enconvert.c:109` to `:116`).

A `bool` call concatenated to a string, outside any `#ifdef`:

```c
text += "Disabled: " + GetIsSimulationDisabled() + "\n";   // P:\scripts\3_game\entities\entityai.c:3300
```

`GetIsSimulationDisabled` returns `bool` (`P:\scripts\3_game\entities\entity.c:6`). `bool.ToString()` exists too (`enconvert.c:1` to `:8`, returning `"true"` or `"false"`); there is no `BoolToString` helper. The script validator no longer has rules against either form.

Unverified until a compile shows it: what `"x" + someBool` prints, whether the literal `"x" + true` compiles (vanilla never writes it), and whether `(int)(-1.7)` truncates toward zero.

## A newline ends the statement

The parser ends a statement at the line break, so a string chain or a condition split over two lines breaks with errors that point elsewhere.

```c
return "type=" + top.GetType()
    + " wet=" + top.GetWet().ToString();      // Missing ';' at the end of line
```

Every continuation line reports `Missing ';' at the end of line`, plus a `Syntax error`, which looks like a quoting problem. A split condition gives `Expected ')', not a '...'`, then `Invalid statement ')'`, `Unexpected scope` and `Syntax error` (measured in game). Build the string one statement at a time and keep every condition on one line:

```c
string desc = "type=" + top.GetType();
desc = desc + " wet=" + top.GetWet().ToString();
```

When a whole file avoids a handy construct, such as multi-line conditions in thousands of lines, assume first that the construct does not compile.

## Keywords and file level statements

- `out` is reserved (it marks out parameters, as in `GetPlayers(out array<Man> players)`, `P:\scripts\3_game\global\game.c:945`). A local named `out` gives `Broken expression (missing ';'?)` with no hint that the name is the problem. The `owned` row in `review-and-troubleshooting.md` lists the other keywords that do this.
- `Print(...)` at file level is not valid Enforce: `Syntax error` and `Can't compile "<Module>" script module!`.

## Moving a method body between modules

`protected` reaches only the declaring class and its descendants. A body moved into `5_Mission`, as in a facade and implementation split, reaches state through parameters (`dev.m_Field`), and that compiles only if the field is public. Measured in game: a tree with no linter errors and a clean binarize still failed the first boot with `Variable 'm_DeviceId' is protected`, then `Can't compile "Mission" script module!`.

When a body moves across modules, the move includes the visibility of every field it touches. The validator check `ES-PROTECTED-CROSS-MODULE` looks for this across the tree (see the README under `scripts/tools/dayz-script-validator/`); whether it catches a receiver reached through a parameter is unverified, so boot the server too.

## Only a boot proves compilation

These checks prove form, not compilation:

| Check | What it proves |
|---|---|
| `CfgConvert -test` | The `config.cpp` parses; no Enforce is compiled |
| An offline linter or text search | Form |
| AddonBuilder `Build Successful` | The PBO was packed |
| A search of the packed PBO | The text travelled |
| Server startup | Compilation |

All four of the first can pass while the server reports `Can't compile "World" script module!`. A boot fails in about 20 seconds, which makes it the cheapest real check before a long test run. In this repo that boot is `/dayz-gate`.
