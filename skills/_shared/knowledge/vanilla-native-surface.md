# The vanilla `proto native` surface

Status: source reading of build `119356`. Checked on `P:\` on 2026-11-17: every cited declaration sits on the cited line of `P:\scripts`. The counts differ slightly there, so `P:\` is not the same script tree as build `119356`: counted with the same line-start rule, `P:\scripts` carries 2,789 `proto native` declarations (`1_core` 565, `2_gamelib` 103, `3_game` 1,955, `4_world` 166, `5_mission` 0), 52 of them `owned` and 25 `proto native static`. The numbers in the body are the source note's, for build `119356`. The `[EXACT][CLAIM-...]` tags are claim IDs in `scripts/dev/knowledge-pack/sources/claims.json`.

A `proto native` declaration is where Enforce Script ends and the engine begins: the script side states a name, a return type and a parameter list, and the native side supplies the body. The declaration is the whole contract, so it has to be read exactly.

This note maps that surface in the official DayZ scripts build `119356`: how many such declarations the build carries, where they concentrate, what `owned` does to the returned value and `static` to the call shape, and the exact shape of two representative calls. It is not a syntax lesson — the `enforce-script-reference` skill teaches how `proto native` is written — and it is not a runtime promise: every count and signature below is a statement about declarations in the build's scripts, verified against those scripts, and nothing here was exercised in a running game.

## What the build declares

Counting only declarations whose line begins with `proto native` (after optional whitespace), build `119356` carries 2,758 `proto native` declarations: 1,956 of them in `3_game`, 52 of them declared `owned`, and 25 of them declared `static` in the `proto native static` order. [EXACT][CLAIM-NATIVE-SURFACE-COUNTS]

The count is a count of declaration lines, not of callable APIs. A name declared in several classes, or declared more than once with different parameters, is counted once per line it is declared on, and a declaration inside a conditional-compilation block is counted like any other.

Per top-level directory, the same line-start count gives the following distribution, and the `3_game` concentration — 1,956 of 2,758, roughly seven in ten — is the headline. [EXACT][CLAIM-NATIVE-SURFACE-DISTRIBUTION]

| Top-level directory | `proto native` declarations |
|---|---:|
| `1_core` | 533 |
| `2_gamelib` | 103 |
| `3_game` | 1,956 |
| `4_world` | 166 |
| `5_mission` | 0 |
| **Total** | **2,758** |

Read the table as where engine services are exposed to script: the core engine interface sits in `1_core`, the game-level interface dominates in `3_game`, entity and world code in `4_world` adds a thinner layer, and `5_mission` declares none — every native the mission layer touches was declared further down. A modder hunting for whether a call exists should search `3_game` first and `1_core` second.

That concentration also tells a modder where *not* to look. A native is an engine entry point, and engine entry points are declared beside the engine and game interfaces, not beside mission presentation code; a fruitless search of `5_mission` is therefore expected, not a sign that the search string is wrong. Conversely, a name that surfaces only in `4_world` is an entity-layer service and should be called in that layer's terms, on an entity, not treated as a global utility.

The line-start rule is deliberate, and it defines what the numbers mean. Declarations written in the `static proto native` order — the modifier before `proto` — do not begin with `proto native` and are outside this count, however real they are. The 25 counted `static` declarations are the ones written `proto native static`. Counting a substring search instead of line-start declarations produces a different, larger number that does not reproduce this table.

## The modifiers

Two modifiers are easy to misread, and both are part of the declaration itself: `owned` is a variable modifier on the return value — `P:\scripts\1_core\proto\proto.c:14-16` defines it as the modifier for returning internal functions and tells the script VM that the returned string or array must not be released — while `static` marks a type-level call, made through the class name with no instance at all. `owned` does not make a function an instance method and does not change the parameter list; instance versus type-level is decided by `static` and by the enclosing class, not by `owned`. [EXACT][CLAIM-NATIVE-SURFACE-MODIFIERS]

`owned` — a return-value modifier, not a call shape. `GetObjectTexture` at `P:\scripts\3_game\entities\entityai.c:2882` is an instance call because it is declared inside `class EntityAI` without `static`, not because it is `owned`:

```c
proto native owned string GetObjectTexture(int index);

string texture = entity.GetObjectTexture(0);
```

The receiver is the object the method is called on, and it is not in the parameter list, so the call passes exactly the declared arguments. Do not add an explicit `this` (or the entity itself) as a first argument: the declaration lists one parameter, `int index`, so a call with two arguments matches no declared shape. Of the counted declarations, 52 carry `owned` in this position. `owned` also appears on `static` declarations: `P:\scripts\3_game\systems\inventory\inventoryslots.c:48` declares `static proto native owned string GetSlotName(int id)`, a type-level call whose return value is owned; because that line begins with `static`, it falls outside the line-start count above, so 52 counts `proto native ... owned` lines, not every owned return in the build. At global scope, `P:\scripts\1_core\proto\enscript.c:336` declares `proto owned string ThreadFunction(...)`, owned and neither an instance nor a static method.

`static` — a type-level call. The full declaration block of `class AudioSystem` (`P:\scripts\1_core\proto\enaudio.c:3-9`) is:

```c
typedef int[] AudioHandle;

class AudioSystem
{
	proto native static AudioHandle BankLoad(string path);
	proto native static AudioHandle ShaderLoad(string path);
	proto native static AudioHandle SoundPlay(AudioHandle bank, AudioHandle shader);
	proto native static void SoundDestroy(AudioHandle handle);
};
```

There is no instance to call through, so the call names the type: `AudioSystem.BankLoad(path)`. Of the counted declarations, 25 carry `static` in the `proto native static` position. Treating a `static` native as an instance method invents a call shape the build never declared; treating `owned` as a call shape does the same, because it qualifies the returned value, not the receiver.

## Two representative call shapes

**An array the native fills: `GetBoneMatrix`.** At `P:\scripts\1_core\proto\envisual.c:41` the build declares a free function (not a class method) that returns `bool` and fills a four-element `vector` array passed to it, so the caller declares `vector mat[4]`, passes that array, and reads the result out of it rather than receiving the matrix as the return value. [EXACT][CLAIM-NATIVE-SURFACE-BONE-MATRIX]

```c
proto native bool	GetBoneMatrix(notnull IEntity ent, int bone, vector mat[4]);

vector mat[4];
bool ok = GetBoneMatrix(ent, bone, mat);
```

The declared third parameter is exactly `vector mat[4]` — the source writes no `out` keyword, and the array is the shape that matters. Declare `vector mat[4]` and pass it; the native writes the four vectors. Do not pass a single `vector`: it is not the declared parameter type, and there is no overload at `P:\scripts\1_core\proto\envisual.c:41-42` that accepts one — the neighbouring `GetBoneLocalMatrix` takes the same `vector mat[4]`. The `bool` return is the only scalar result; the matrix itself arrives through the array.

**A static that returns a handle: `AudioSystem.BankLoad`.** Declared at `P:\scripts\1_core\proto\enaudio.c:5` inside `class AudioSystem` (`P:\scripts\1_core\proto\enaudio.c:3-9`), with `AudioHandle` defined at `P:\scripts\1_core\proto\enaudio.c:1` as `typedef int[] AudioHandle;`. The correct call is the type-level one, with exactly the declared argument:

```c
AudioHandle bank = AudioSystem.BankLoad(path);
```

No instance is created, no receiver is passed, and the returned value is the declared `AudioHandle`, to be handed back to the sibling declarations in the same block (for example `SoundPlay` and `SoundDestroy` at `P:\scripts\1_core\proto\enaudio.c:7-8`) rather than reinterpreted.

## What this changes

Before writing a native call, a modder can settle four things from the declaration alone: that the call exists in this build (search `3_game`, then `1_core`, using the counts above as the map); whether it is an instance call (no `static`, declared inside a class — receiver implicit, never an argument) or a type-level call (`static` — class name, no instance); the exact parameter list, including array shapes such as `vector mat[4]` that the caller must declare and the native fills; and the exact return type, including typedef'd handles such as `AudioHandle`. What the declaration cannot settle is whether the native behaves as hoped at runtime in a given context — that remains an in-game question, and this note does not answer it.

## How to reproduce

Against the build `119356` scripts (the `scripts/` root of that tree), with GNU `grep`:

```sh
grep -R -E '^[[:space:]]*proto[[:space:]]+native' --include='*.c' scripts | wc -l   # 2758
grep -R -E '^[[:space:]]*proto[[:space:]]+native' --include='*.c' scripts | grep -c ' owned'   # 52
grep -R -E '^[[:space:]]*proto[[:space:]]+native' --include='*.c' scripts | grep -c ' static'   # 25
for d in 1_core 2_gamelib 3_game 4_world 5_mission; do printf '%s ' "$d"; grep -R -E '^[[:space:]]*proto[[:space:]]+native' --include='*.c' "scripts/$d" | wc -l; done
# 1_core 533, 2_gamelib 103, 3_game 1956, 4_world 166, 5_mission 0
```

The cited declarations resolve at `P:\scripts\1_core\proto\envisual.c:41` (`GetBoneMatrix`), `P:\scripts\1_core\proto\enaudio.c:5` (`AudioSystem.BankLoad`, class at `:3-9`, typedef at `:1`), and `P:\scripts\3_game\entities\entityai.c:2882` (`GetObjectTexture`, inside `class EntityAI` at `:115`).

## Limits

This note describes build `119356` only; another build's surface must be recounted, not assumed. Its counts are declaration lines under the line-start rule stated above: they include declarations inside conditional-compilation blocks (for example the `proto native` declarations under `#ifdef ENF_DONE` at `P:\scripts\1_core\proto\enentity.c:774-780`) and they include overloads and same-name declarations in different classes, so 2,758 is not a count of distinct callable APIs and not a public API promise. The build's scripts are the authority for every signature quoted here; a declaration proves the shape was declared, not that a call succeeds at runtime, and no runtime verification was performed for this note. No code was copied from the vanilla scripts into this note beyond the short declarations quoted as evidence. [EXACT][CLAIM-NATIVE-SURFACE-LIMITS]
