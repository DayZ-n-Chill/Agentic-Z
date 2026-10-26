# EnScript (Enforce Script) Style Guide

> **Source:** [TrueDolphin/references wiki](https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide). Mirrored here so DayZ agents/skills follow it offline.
>
> **Authority:** This is best-practice for EnScript across DayZ modding. When code in `workspace/` conflicts with this guide, this guide wins unless the user says otherwise.

Every script task follows this guide. It is split into focused files under `enscript-style/`, so open only the one your task needs:

| Task | File |
|---|---|
| Naming a class, method, member, constant or file | [`enscript-style/naming.md`](enscript-style/naming.md) |
| Laying out a class: braces, member order, access; writing comments | [`enscript-style/layout-and-comments.md`](enscript-style/layout-and-comments.md) |
| Picking a type, casting, `auto`, containers | [`enscript-style/types.md`](enscript-style/types.md) |
| `ref`, `autoptr`, `delete`, lifetime of objects | [`enscript-style/memory.md`](enscript-style/memory.md) |
| `if`, loops, `switch`, `#ifdef`, `#define`, server and client builds | [`enscript-style/control-flow-and-preprocessor.md`](enscript-style/control-flow-and-preprocessor.md) |
| `modded class`, `super`, singletons, getters, serialization, input, modules | [`enscript-style/modding-patterns.md`](enscript-style/modding-patterns.md) |
| Logging, tracing, null checks, guards, client and server checks | [`enscript-style/debugging-and-errors.md`](enscript-style/debugging-and-errors.md) |
| A review pass over finished code | [`enscript-style/best-practices.md`](enscript-style/best-practices.md) |

What each file holds:

| File | Sections |
|---|---|
| `enscript-style/naming.md` | Introduction, File Organization, Naming Conventions |
| `enscript-style/layout-and-comments.md` | Code Structure, Comments |
| `enscript-style/types.md` | Type System |
| `enscript-style/memory.md` | Memory Management |
| `enscript-style/control-flow-and-preprocessor.md` | Control Flow, Preprocessor Directives |
| `enscript-style/modding-patterns.md` | Modding Patterns, Global Variables and Singletons, Property Access, Serialization, Input Handling, Module System |
| `enscript-style/debugging-and-errors.md` | Debugging and Tracing, Error Handling |
| `enscript-style/best-practices.md` | Best Practices, Common Pitfalls and Issues, Engine traps & production pitfalls, Conclusion |

## Style, not facts

This guide is about how code is written. Facts about vanilla APIs live in the checked references under `_shared/enscript/references/` (each cites `P:\scripts\`, for example `GetGame()` returning `g_Game` at `P:\scripts\3_game\gameplay.c:636`). Where a style file and a reference file disagree on a fact, the reference file wins.

## Key takeaways

- PascalCase for classes and methods; `m_` for members, `s_` for statics; prefix everything you add with your mod tag.
- Always write `override` when overriding, and call `super` unless you mean to replace the behaviour.
- `modded class X` never has `: Parent`.
- `ref` on members and container element types only; never on parameters, return types or locals.
- Null check where you can handle the null; use `notnull` to pass the guarantee on.
- Use `IsDedicatedServer()` for side checks in init code.
