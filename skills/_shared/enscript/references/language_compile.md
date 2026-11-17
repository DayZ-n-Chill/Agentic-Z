# Reference: modded classes, attributes and the preprocessor

How a mod changes vanilla classes, the attributes vanilla defines, and the compile time defines the engine sets. Facts cite the vanilla file on `P:\scripts\` they were checked against (game storage version 144, `P:\scripts\3_game\global\game.c:5`).

## Script layers

Vanilla scripts sit in five folders, compiled in this order: `1_core`, `2_gamelib`, `3_game`, `4_world`, `5_mission` (`P:\scripts\`). Code in one layer can use types from its own layer and the layers below, never above. A mod uses the same folder names for its own modules; the layout and config rules are in `_shared/conventions/scripts.md`.

## `modded class`

`modded class Foo` changes the existing class `Foo` in place, so every `Foo` the game creates gets the change. Vanilla shows the form itself:

```c
modded class ParticleList
{
	static const int MODDED_PARTICLE = RegisterParticle( "mod_folder/" , "my_modded_particle");
}
```

Source: `P:\scripts\3_game\particles\particlelist.c:5` (an example inside a comment). A real vanilla use is `modded class PluginDiagMenu` (`P:\scripts\4_world\plugins\pluginbase\plugindiagmenu\plugindiagmenumodding.c:21`), which also sits inside `#ifdef DIAG_DEVELOPER` (`:10`).

Rules (details and the traps are in `patterns/modded_class.md`):

1. No `extends` clause on a modded class.
2. Mark replaced methods `override` and call `super.Method(...)` unless you mean to drop vanilla behaviour, as vanilla's own overrides do (`P:\scripts\3_game\entities\entityai.c:3507`, `:3509`).
3. Prefix new fields and methods with your mod tag so two mods modding the same class do not collide (`_shared/enscript-style.md`).
4. Mod the most specific script class, the one the game actually creates, in the lowest layer that has the types you need.

## Attributes

An attribute is a class; the square brackets before a declaration call its constructor. `Obsolete` is `class Obsolete: Managed` with a `string` constructor (`P:\scripts\1_core\proto\enscript.c:359`).

| Attribute | Effect | Source |
|---|---|---|
| `[Obsolete("Use X instead")]` | A compile time warning wherever the method is used; the call still runs. Vanilla tags methods and classes this way with the version (`[Obsolete("1.30: No replacement")]`). | `P:\scripts\1_core\proto\enscript.c:344`, `P:\scripts\3_game\entities\entityai.c:74` |
| `[NonSerialized()]` | The serializer skips this field. | `P:\scripts\1_core\proto\serializer.c:7`, `:16`, `P:\scripts\3_game\client\syncplayer.c:7` |
| `[Attribute("default", "widget", "description", "range")]` | Exposes a field to the Workbench editor. | `P:\scripts\1_core\proto\enentity.c:825`, `P:\scripts\2_gamelib\entities\rendertarget.c:13` |
| `[WorkbenchPluginAttribute(...)]`, `[ButtonAttribute(...)]` | Workbench plugins and their buttons. | `P:\scripts\1_core\workbenchapi.c:137`, `:117`, `P:\scripts\editor\plugins\dayztools.c:46` |
| `[Test("Suite")]`, `[Step(...)]` | The script testing framework. | `P:\scripts\2_gamelib\tests\testingframework.c:96`, `:125`, `:30` |

`JsonSerializer` derives from `Serializer` (`P:\scripts\3_game\gameplay.c:49`) and `JsonFileLoader` uses it (`P:\scripts\3_game\tools\jsonfileloader.c:5`). Test that a `[NonSerialized()]` field stays out of your JSON before you rely on it.

Use `[Obsolete]` in a framework mod instead of deleting a method other mods may call (`_shared/enscript-style.md`).

## Preprocessor

Vanilla script uses `#ifdef`, `#ifndef`, `#else` and `#endif`. It has no `#include` and no `#if` expression. File local debug switches are left as commented `//#define NAME` lines at the top of a file (`P:\scripts\4_world\classes\codelockcomponent.c:1`).

```c
#ifndef SERVER
	// client only cases
#endif
```

The defines come from the engine. `P:\scripts\1_core\defines.c` lists them for documentation only ("All defines in this file are added from C++ side", `:1`).

| Define | Set when | Source (`1_core\defines.c`) |
|---|---|---|
| `SERVER` | A dedicated server. Only defined when `IsDedicatedServer()` is true, and preferred over that call when possible. | `:106`, `:112` to `:115` |
| `NO_GUI`, `NO_GUI_INGAME` | Server builds. Wrap any code that names GUI types. | `:27` to `:34` |
| `DIAG`, `DEVELOPER`, `DIAG_DEVELOPER` | Diag builds, internal builds, and either one. | `:75` to `:92` |
| `RELEASE` | Retail builds. A build is always `DEVELOPER` or `RELEASE`. | `:80` to `:87` |
| `BUILD_EXPERIMENTAL` | Experimental builds. | `:95` to `:97` |
| `DAYZ_X_XX` | The game version, such as `DAYZ_1_16`. | `:12` to `:14` |
| `ENABLE_LOGGING` | The `-doScriptLogs=1` launch parameter. | `:37` to `:39` |
| `PLATFORM_WINDOWS`, `PLATFORM_LINUX`, `PLATFORM_CONSOLE` | The platform. | `:148` to `:161` |
| `WORKBENCH`, `BULDOZER` | Compiling in Workbench, or the land editor. | `:17` to `:24` |

What follows for mod code:

- `SERVER` is not defined in single player or offline mode, so code inside `#ifdef SERVER` does not exist there. Use `#ifdef SERVER` only for code that must never ship in the client build; use `GetGame().IsServer()` for authority work that must also run offline (`_shared/conventions/scripts.md`).
- Vanilla guards client only RPC cases with `#ifndef SERVER` and GUI code with `#ifndef NO_GUI` together (`P:\scripts\3_game\dayzgame.c:3157`, `:3158`).
- Most vanilla debug code sits behind `#ifdef DIAG_DEVELOPER`, so it is missing from retail. Code you need in retail must not depend on it.
- `PluginDeveloper` is one such case: it is registered through `RegisterPluginDiag`, whose body sits inside `#ifdef DIAG_DEVELOPER` (`P:\scripts\4_world\plugins\pluginmanager.c:65`, `:249` to `:254`), so `GetPlugin(PluginDeveloper)` is `null` on a retail server and a teleport or give built on it does nothing there. The retail substitutes (`SetPosition`, moving the vehicle of a seated player, `CreateInInventory`) are in `skills/enforce-script-reference/references/pitfalls-advanced.md`.
- `DEVELOPER` and `DIAG_DEVELOPER` are different defines. Reported by the knowledge pack, not checked on `P:\` (the defines come from the engine): DayZDiag defines `DIAG_DEVELOPER` but not `DEVELOPER`, so a mod that calls a symbol which exists only under `#ifdef DEVELOPER` stops its whole PBO compiling there. Read the `defines:` line of `script_*.log` on the server and on the client before you rely on a define.
- A define that another mod must see has to come from that mod's `CfgMods` class, not from a `#define` in one of its script files. Reported by the knowledge pack, not checked on `P:\`: since 1.26 a mod's `CfgMods` class name and the names in its `defines[]` array are defined for every mod's scripts, while a `#define X` written in a script file is seen only inside that mod. An `#ifdef` in your mod on a name the other mod only `#define`s in script compiles to nothing, so a `modded class` inside it is silently lost.

## Symbols that are in the source but not in the build

A correct `path:line` does not prove a symbol can be called. Check three things before you call or mod a vanilla symbol:

- **Its define is active.** `PerformAction` on `ActionManagerClient` sits inside `#ifdef BOT` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:796` to `:802`), and no vanilla script defines `BOT`, so the method does not exist in any build. The public entry point is `PerformActionStart` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804`). In the same way `GetConsoleToolbarText` exists only under `#ifdef PLATFORM_CONSOLE` (`P:\scripts\5_mission\gui\inventorynew\inventory.c:1307`); the knowledge pack reports that overriding it on PC gives `no function to override in base class` and a client that hangs on the loading screen.
- **Its class is not commented out.** The whole of `actionfishing.c` is one block comment that opens with `/*class ActionFishingCB` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionfishing.c:1`); the live class is `ActionFishingNew` (`P:\scripts\4_world\classes\useractionscomponent\actionconstructor.c:246`). A `modded class` on the dead name fails with `Unknown type` (reported).
- **A `proto native` is linked.** Reported, not checked on `P:\`: `GetFPS` is declared in `proto.c` yet every call threw `Function 'GetFPS' not linked` in DayZDiag 1.29. Call a `proto native` once from a test script before you build on it.

## Compiler traps

Reported by the knowledge pack from compiles on DayZDiag and retail servers; the compiler is native, so only the vanilla examples were checked on `P:\`. The measurements and error texts are in `skills/enforce-script-reference/references/compiler-traps.md` and `skills/enforce-script-reference/references/hard-rules.md`.

| Trap | What the compiler says | What to write |
|---|---|---|
| A local has method scope, not block scope: the same name declared in two `case` or `if` blocks of one method | `Multiple declaration of variable 'X'` on DayZDiag; retail may let it pass | One declaration at the top of the method, or a different name per block |
| A statement split over lines: a `+` string chain, an `&&` condition or a call's argument list continued on the next line | `Missing ';' at the end of line`, `Expected ')'`, then `Syntax error` on later lines | Keep the statement on one line, or build it in several one line statements |
| `%` with a `float` in the expression | `Unknown operator '%'` | Compute the modulo into an `int` first. Every vanilla use has integer operands, such as `new_index % count` (`P:\scripts\1_core\proto\enscript.c:652`) |
| A keyword used as a variable name: `out`, `owned`, `ref`, `autoptr`, `notnull`, `local`, `event` | `Broken expression (missing ';'?)` on the declaration | Rename it. `owned` is a modifier, as in `proto native owned string GetWorldFile()` (`P:\scripts\2_gamelib\gamelib.c:57`) |
| A method named exactly like a vanilla class, called as a bare statement: a helper `FoodStage(3);` beside `class FoodStage` (`P:\scripts\4_world\classes\foodstage\foodstage.c:22`) | `Types X and Y are unrelated` | Rename the method |
| A plain `const` class member read from a `static` method | Fatal on a retail server | Declare it `static const` |
| `ref` on a method parameter | `Method argument can't be strong reference` on DayZDiag; retail lets it pass | Drop the outer `ref`: `array<ref X> p` |
| A `protected` field read through a parameter from a class in another module | `Variable 'm_X' is protected` | Make the field public when a method body moves to another class |
| `Print(...)` at file level, outside any function | `Syntax error`, then `Can't compile "<Module>" script module!` | Put it in a function |
| A name that starts with a keyword followed by a digit: `out0`, `ref1`, `new2`, `auto3`, `inout4` | `Expected ',' or ')', not a '0'`, then `Unexpected scope` and `Syntax error` | Rename it (`dst0`). The lexer reads the keyword and then the number |
| A variable named like a type: `Widget map = ...` (also `set`, `array`, `vector`, `string`, `Class`) | `Variable name 'map' already used as type name`, then decoy errors on the lines after it | Rename it; fix the first error of the block and ignore the rest |
| One line that joins 18 or more terms with `+` and holds a string literal (17 compiled, 18 failed on DayZDiag 1.30.164289) | `Formula too complex`, then `Incompatible parameter` on the same line | Build the string in steps: `s = s + part;` |
| A method with a 17th parameter (measured on a 1.30.164289 server) | `Maximum arguments count 16 exceeded in method 'X'` | Pass one object that carries the values |
| A `switch` in which every case, `default` included, returns | A missing return is reported for the method | Move the last `return` out of the `switch`, after it |
| `a & b == b` | Nothing: it compiles as `a & (b == b)`, as in C | Write `(a & b) == b` |
| `text.Replace(a, b).Replace(c, d)` | The second call is made on an `int`: `Replace` changes the string and returns a count (`P:\scripts\1_core\proto\enstring.c:156`) | One `Replace` per statement, on a local copy |

The measurements behind the last seven rows are in `skills/enforce-script-reference/references/pitfalls-advanced.md`.

Two things that do compile, against a common belief: C style casts, as in `(float)random_int / (float)max_range` (`P:\scripts\1_core\proto\enmath.c:110`), and a `string` plus a `bool`.

Only the game compiles Enforce Script. `CfgConvert`, AddonBuilder ("Build Successful" means the PBO was packed) and a linter check form. A script module is proven to compile when a server or client boots with it, which is what `/dayz-gate` does.
