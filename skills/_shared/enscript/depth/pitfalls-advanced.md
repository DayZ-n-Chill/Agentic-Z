# Compiler pitfalls

Which code the Enforce compiler mishandles or rejects with a confusing message, how to read the script log when a module fails, and the scoping traps. Runtime crashes are in `runtime-pitfalls.md`; modded class and define traps in `modded-class-and-defines.md`; boot-time traps in `compiler-traps.md`.

## Comparisons and control flow

- Reported, not checked on `P:\`: `1 < int.MIN` and `1 < -2147483647` both return true. Guard comparisons against `int.MIN` and `int.MAX` explicitly.
- Reported, not checked on `P:\`: a `switch` whose `default` returns still gets "not all paths return a value". Drop the `default` and put its `return` after the `switch`.
- Reported, not checked on `P:\`: bitwise operators bind looser than comparisons, as in C, so `a & b == b` means `a & (b == b)`. Write `(a & b) == b`.
- `if (!list[i])` on an `array<int>` compiles. Vanilla writes `if (!animSourceBehaviorInvetrtedOverrides[i])` (`P:\scripts\4_world\classes\basebuilding\constructionpart.c:549`, array declared at `:541`; again at `:572`, `:595`, `:647`).

## Errors that point at the wrong place

- Reported, not checked on `P:\`: when a referenced class does not exist, often because an addon is missing, the error names the last file parsed at its end, not the file with the problem. If a correct-looking file fails, check that every class it uses comes from a loaded addon.
- `Expected ',' or ')', not a '0'`, followed by `Unexpected scope` and `Syntax error`, on a signature: the lexer splits a name that starts with a keyword followed by a digit. `out vector out0` reads as `out`, `vector`, `out`, `0`. The prefixes are `out`, `ref`, `new`, `auto` and `inout`, and no vanilla script under `P:\scripts` has such a name. Rename to `dst0`, `res0` or `val0` (measured in a mod compile). The `owned` row in `review-and-troubleshooting.md` covers a keyword used as a whole name.
- A variable named like a type does not compile: `Widget map = root.FindAnyWidget("mapWidget")` gives `Variable name 'map' already used as type name`, and the module dies. Later lines report decoys such as `Trying to modify write protected variable '(null)'` and `Undefined function 'map.GetFlags'`; the first line is the cause. The same goes for `set`, `array`, `vector`, `string` and `Class`. The client boots, never enters and closes on its own; only the server's `script_*.log` says why (measured in game).

## `%` beside a float

Measured in game on DayZ 1.30 in a mod's `4_World`: `float x = (cell % 103) * 150 + 150 * 0.5;` and `float x = (cell % SIDE) * STEP + STEP * 0.5;` (`static const float STEP`, `static const int SIDE`) each stopped the module with `Unknown operator '%'`, then `Can't compile "World" script module!`. Putting the `%` in an `int` local first compiled and ran:

```c
int col = cell % SIDE;
float x = col * STEP;
x = x + STEP * 0.5;
```

Both failing lines hold the literal `0.5`, so whether a `static const float` alone triggers it is not isolated. A mission `init.c` has also reported `Unknown operator ''` for the second form. The rule is in `hard-rules.md`, section "Syntax"; the validator reports it as `ES-MODULO-FLOAT-CONTEXT`.

## Long expressions

Measured in game on DayZ 1.30: one line alternating string literals with an `int` and a float's `ToString()` compiled with 17 terms and failed with 18 and 20: `Formula too complex`, then `Incompatible parameter 'i0'` on the same line, then `Can't compile "World" script module!`. The `Incompatible parameter` is a cascade, not a second bug. A JSON-like expression of about 30 operands also failed in a mod. Other operand types are not measured.

Build long strings one assignment at a time (`s = s + part;`), and move vector or matrix indexing and call results into typed locals before formatting them. The validator warns from 18 terms joined by `+` in a statement with a string literal (`ES-FORMULA-TOO-COMPLEX`); a line over 400 characters is a useful lint signal but not a language limit. The game compile is the gate.

## Recurring compile failures

The compiler can stop at the first of these and show the next only after a rebuild, so fix and recompile every view until all are clean.

| Failure | Fix |
|---|---|
| Opaque file handles treated as integers. `FileHandle` and `FindFileHandle` are `int[]` aliases (`P:\scripts\1_core\proto\ensystem.c:390`, `:503`) | Declare the type without `= 0`, test `if (!handle)` and track the open state yourself |
| Searching a folder | `FindFile(pattern, out name, out attr, flags)`, `FindNextFile(handle, out name, out attr)`, then `CloseFindFile(handle)` (`ensystem.c:520` to `:522`) |
| Reading a whole file with `ReadFile(FileHandle, void, int)` (`:425`) | `OpenFile` (`:417`) with `READ`, repeated `FGets`, then `CloseFile`, as vanilla does (`P:\scripts\5_mission\gui\controlsxbox.c:293` to `:305`) |
| `ScriptRPC.WriteString` | There is none: `ScriptRPC` adds only `Reset` and `Send` (`P:\scripts\3_game\gameplay.c:104` to `:118`) to a `Serializer` with generic `Write` and `Read` (`P:\scripts\1_core\proto\serializer.c:57` and `:58`). A member that keeps the RPC needs `ref` |
| `.Replace().Replace()` | `string.Replace` changes the string in place and returns an `int` (`P:\scripts\1_core\proto\enstring.c:156`); call it once per statement on a local |
| `Multiple declaration` | Locals have method scope; rename per branch or declare once. Separate `#ifdef` and `#else` views may reuse a name, since only one exists at a time |
| `Unmatched brackets detected!` | It can come from `()` or `[]` as well as `{}`. An offline checker must balance all three after stripping strings and comments, and still cannot replace the game compile |

## Scope

The same name in sibling blocks fails, and so does a loop variable that repeats an outer name:

```c
int i = 5;
for (int i = 0; i < 12; i++) { }   // multiple declaration
```

Declare the variable once before the `if`, or use another name (`j`). More in `compiler-traps.md`, section "Locals have method scope".

## Empty `#ifdef` blocks

A block holding only a comment compiles. Measured in game on DayZ 1.30 diag in a mod's `4_World`: such a block at file scope, in a class body and in a method body, under `DIAG_DEVELOPER` and under a macro nobody defines, compiled and ran on server and client. Vanilla ships one: `#ifdef DIAG_DEVELOPER` around one commented line (`P:\scripts\4_world\classes\environment\environment.c:1` to `:3`). Unverified: a block with nothing inside, a retail build, DayZ 1.29. The validator still warns (`ES-EMPTY-IFDEF`); remove a block that holds no code.

## Printing and reading the log

```c
Print(myInt);
PrintFormat("Device %1 at %2 has load %3", typeName, pos.ToString(), load.ToString());
Error("Something failed");
ErrorEx("Failed to load config", ErrorExSeverity.WARNING);
```

The script console in Workbench or an admin tool runs a snippet such as `Print(GetGame().GetTime());` at runtime.

| Log line | Meaning |
|---|---|
| `SCRIPT (E): ...` | A script error, usually a null reference; not fatal |
| `Segmentation fault` | A fatal crash: array bounds, a dead pointer, a shader |
| `Illegal write at ...` | Heap corruption, usually from timer or allocation churn |
| `Multiple declaration of 'X'` | A name declared twice in one method |
| `Variable name 'X' already used as type name` | A variable named like a type; later lines are decoys (measured) |
| `Unknown operator '%'` | `%` beside a float (measured) |
| `Formula too complex` | 18 or more terms on one line (measured) |
| `'X' not found` | Missing class or method: an addon or a typo |
| `Scripted variables corrupted upon "X"` | `OnStoreLoad` reads in a different order than the save |
| `Cannot create object of type 'X'` | The class is missing from `config.cpp` or has the wrong parent |

Rows not marked measured are reported; logs are not on `P:\`. Also reported: a `crash_<date>_<time>.log` holds script exceptions, while a hard memory fault writes a separate dump, so check both.
