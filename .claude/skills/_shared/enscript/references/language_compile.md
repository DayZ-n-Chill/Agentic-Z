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
