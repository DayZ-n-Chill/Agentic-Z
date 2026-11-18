# dayz-script-validator rules

The rules that need more than the line in front of them: what each one
reports, the compile failure behind it, what it leaves unjudged and how it
was measured. Install, invocation, tests and the vanilla control are in
`README.md` next to this file.

## Checks that need more than one file

Most rules read a single file. The ones below read the tree:
`ES-PROTECTED-CROSS-MODULE` the addon's modules, `ES-EXTERNAL-CONSUMER-MISSING`
the addon and the `--external-scripts` roots, and the others the addon, those
roots and the vanilla tree:

- `ES-PROTECTED-CROSS-MODULE` compares modules against each other. Enforce
  enforces `protected` across script modules, so a `5_Mission` class reading a
  `4_World` class's protected member aborts the whole Mission module. Runs
  automatically.
- `ES-EXTERNAL-CONSUMER-MISSING` compares the addon against script that calls
  into it from outside -- a mission folder, another mod. Pass those roots
  explicitly; the check is inert without them:

```powershell
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root> `
    --external-scripts <mission_root> --external-scripts <other_mod_root>
```

Both only fire when the receiver's declared type resolves inside the addon.
That is deliberate: judging by member name alone produced 164 false positives
on a tree that compiles clean.

- `ES-UNDEFINED-CLASS-REF` (FAIL) flags a class-like name (first letter upper
  case) used where only a type fits -- `Name.Method(`, `Name.Cast(`,
  `new Name`, a template argument, a typed declaration at the start of a line
  -- when no `class`, `enum` or `typedef` of that name exists in the addon,
  in the vanilla scripts tree or in any `--external-scripts` root. The case
  behind it: a change to a mod deleted a `4_World` class that `5_Mission` still
  called, a guaranteed Mission compile failure the linter reported as WARN
  with 0 errors. The vanilla tree comes from `--vanilla-root`, then
  `DAYZ_VANILLA_ROOT`, then `P:\scripts`.

```powershell
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root> `
    --external-scripts <CF_root>
```

Pass each dependency's root, the folder that holds its `config.cpp`: the rule
reads that file's `CfgPatches` to know which `requiredAddons[]` entry the
root covers, so a root without it leaves the dependency uncovered.

It judges only when it can see every place the type could be declared, and
otherwise lists what it could not judge under `info.skipped_checks` (and as a
`SKIP` line in `--terse`) without changing the status:

| Situation | Result |
|---|---|
| no vanilla tree, or a folder that declares no `class Managed` | SKIP: every vanilla type would look undefined |
| `requiredAddons[]` names an addon that is not a vanilla patch and that no scanned root declares in `CfgPatches`, directly or as the dependency of a scanned dependency | SKIP with the unresolved names; pass that addon's root with `--external-scripts` to get verdicts |
| a `requiredAddons[]` entry that is not a string literal (a macro, a number) | SKIP: that dependency is unknown |
| no `config.cpp` in the tree lists any `requiredAddons[]` entry | SKIP: dependencies unknown |
| code under `#ifdef`/`#ifndef` of a macro that vanilla does not test and no scanned script `#define`s or `CfgMods defines[]` lists | not judged: usually another mod's flag |
| the `#ifndef` or `#else` branch of a macro that a scanned script `#define`s, or a scanned `CfgMods defines[]` lists, on a line the preprocessor always keeps (outside every block, or under an `#ifdef` of a macro the same file defines first) | not judged: that branch never compiles |

A mod that uses another mod's classes without listing it in `requiredAddons[]`
does get the FAIL; the message names both remedies. "Vanilla patch" means one
of the 211 `CfgPatches` names of `P:\DZ` (1.29.0.163451), the scripts tree and
the 1.30.164014 Exp data, listed in
`scripts/tools/dayz-script-validator/scripts/shared/vanilla_patches.py`. A
`DZ_` prefix is not enough: four mod patches under `P:\` use it too.

Measured with the first version of the rule: 33 003 references
judged on the vanilla tree with no finding; over 161 addon roots under `P:\`
it left 12 FAILs in 3 roots (one probable real bug, two source trees
that use a sibling mod they do not declare) and 32 SKIPs whose unresolved
names all belong to mods. Reading the vanilla tree adds about 0.9 s per
invocation (2.6 s against 1.7 s on a 23-file addon, four runs each). After
the fixes from two rounds of review, the
vanilla tree gave the same 33 003 references and no finding; the 161 roots
were not measured again.

- `ES-VARIABLE-NAMED-AS-TYPE` (FAIL): a variable, member or parameter whose
  name is a class, enum or typedef declared in the addon, the vanilla tree or
  an `--external-scripts` root. `bool Debug;` in a 4_World settings class
  made DayZDiag 1.29 refuse the module with `Variable name 'Debug' already
  used as type name`; a local `Widget map`
  failed the same way (`skills/_shared/enscript/depth/`,
  `pitfalls-advanced.md`). Only a member and a local are on record; a
  parameter, an enum and
  a typedef are judged the same way without a failure on record. The match
  is exact case, so a member `debug` passes: identifiers are case-sensitive
  and no case-only failure is on record. A name is judged against the types
  of its own module and the modules below it (a 4_World local may be named
  like a 5_Mission class). A file outside any `N_Module` folder may compile
  in any module, so it is judged only against the types of 1_Core and those
  of its own file; in a mod laid out without its module folders the rule
  had reported a member against a 5_Mission class (measured on mods).
  Positions are those of `ES-RESERVED-WORD-IDENTIFIER`;
  code that never compiles is not judged, and a type the addon or an external
  root declares only there is no type. Nor is a name judged against a type its
  own file declares only in another branch of the same `#ifdef` block, or only
  under the opposite test of a macro the file never `#define`s or `#undef`s
  (`#ifdef X` type, a later `#ifndef X` name): the two never compile together.
  Without a vanilla tree the addon's
  and the external roots' types are still judged, and the vanilla part is
  listed as SKIP in `info.skipped_checks` and in `--terse`.
- `ES-CAST-UNRELATED-TYPES` (FAIL): `X.Cast(y)` where neither X nor the
  declared type of `y` derives from the other. `Mission mission =
  GetGame().GetMission(); hud = IngameHud.Cast(mission);` made DayZDiag 1.29
  refuse the Mission module with `Types 'IngameHud' and 'Mission' are not
  related`. Judged only when everything is
  known: `y` is a plain name declared once, with a plain type, as a local
  still open at the cast or a parameter of the same function, or else as a
  member of the enclosing class itself (an inherited member is not looked
  up); both are classes, not a typedef, an enum, a template or a primitive;
  and the `extends` chain of both resolves in the addon, the vanilla tree or
  an `--external-scripts` root, through declarations that are not `modded`
  and agree on one parent (a header that a directive splits, `class D` /
  `#ifdef X` / `: B` / `#endif`, does not resolve). `Class` is related to
  everything. Anything else,
  a call's result included, is skipped without a SKIP line; without a
  vanilla tree that means every cast whose chain reaches a vanilla class.
- `ES-UNDECLARED-STATIC-MEMBER` (FAIL): `ClassName.Member` or
  `ClassName.Member(` where no declaration of the class names `Member`. A
  change deleted `ANIM_SWAP_ENABLED` and its sibling consts from its own class
  `FX_Constants` while seven call sites still read
  `FX_Constants.ANIM_SWAP_ENABLED`, and DayZ refused the World module on
  the first boot. Judged only for a class
  the addon owns end to end: declared in the addon, not modded and not a
  template there, declared nowhere (modded or not) in the vanilla tree or an
  `--external-scripts` root, with every ancestor the same through
  declarations that agree on one parent. A name counts as declared when it
  appears at the top level of the body of any addon declaration of the class
  or an ancestor, `modded class` and `#ifdef` branches included; the methods
  of `Class` (`Cast`, `CastTo`, `StaticType`, `StaticGetType`...) always
  count. A class whose
  chain reaches a vanilla or another mod's class is not judged, so it runs
  without a vanilla tree; a class-like name declared as a variable in the
  addon is not judged either.
- `ES-PROTECTED-METHOD-CROSS-CLASS` (WARN): `recv.Method(` where `Method`
  is `protected` or `private` in the declared type of `recv` (or the addon
  ancestor that declares it) and the calling class is neither that class nor
  derived from it. The shape comes from a mod: `PlayerBase.OnRPC`
  called `cmd.FX_OnServerState(...)`, protected in `FX_RideCommand`, in
  the same module. WARN because the refusal is measured for a protected
  field (`Variable '...' is protected`, `ES-PROTECTED-CROSS-MODULE`) and not
  for a method. The receiver's type is looked up as in
  `ES-CAST-UNRELATED-TYPES`; every class from it up to the one that declares
  the method must be the addon's own, and the first declaration found decides
  (any public declaration of that name in the addon clears it). A caller whose
  chain leaves the addon and the external roots counts as unrelated: a
  vanilla class cannot derive from an addon class. A caller or an ancestor
  whose header a directive splits is not read, and the call is skipped.
- `ES-PROTO-ARGUMENT-DOWNCAST` (FAIL or WARN): a name passed to a parameter
  of a `proto` method where the parameter's class derives from the class
  the name is declared as. `DayZPhysics.RaycastRV(from, to, pos, dir, comp,
  hits, hitEntity, m_Human, true, false, ObjIntersectGeom)`, with
  `hitEntity` an `IEntity` at the `Object` parameter 6, made DayZ
  1.30.164014 server refuse the World module with `Cannot convert 'IEntity'
  to 'Object' for argument '6' to method 'RaycastRV'` (the compiler
  counts arguments from 0). DayZDiag
  1.30.164289 refused that call again, and an `Object` passed to the
  `EntityAI` parameter 0 of `ItemPreviewWidget.SetItem`, the shape the rule
  had found in a mod, with `Cannot convert 'Object' to 'EntityAI' for
  argument '0' to method 'SetItem'` (a retail build is not
  measured for it). Those two pairs, an `IEntity` where an `Object` is
  taken and an `Object` where an `EntityAI` is, are FAIL; any other is
  WARN, because no refusal of it is measured. Judged only when everything is
  known: the call is in a method the validator reads (not one whose return
  type has template arguments, `array<T> F(`); the receiver is a class, or a
  name looked up as in `ES-CAST-UNRELATED-TYPES` or else as a member of
  another body of the enclosing class or of the nearest class up its chain
  that declares it; the first class up the receiver's chain that declares
  the method (a `modded class` included) declares it `proto` every time,
  with one parameter list, where a declaration whose `(` is on a line that
  never compiles does not count; the argument is a plain name looked up the
  same way; and the parameter is not `out` or `inout` and has a plain class
  type whose chain holds the argument's class above its own. `Class` is not
  judged as the argument's class. A member in a body of another file counts
  when that file's script module is not later than the call's (a later one
  is compiled after it), and leaves the name unknown when either file is
  under no `N_Module` folder. A declaration under `#if`, `#ifdef` or
  `#ifndef` leaves a name unknown unless it is in the call's file under
  blocks that are all around the call, and a method whose declaration has a
  line up to its `(` under such a block is unknown. A name that the method
  declares before the call only where that declaration is no longer open at
  the call (a `for` or `foreach` variable, for a call in the loop's body or
  after it, or a local of a block closed before the call) is unknown too,
  also where a member has that name; a call in that `for`'s own header, as
  in its condition, takes the variable's type. A call whose arguments hold
  `<`, `>` or a directive is skipped, and so is one with more arguments than
  parameters. Protos are read from the addon, the `--external-scripts` roots
  and the vanilla tree, so without a vanilla tree no vanilla proto is
  judged, with no SKIP line. Only a proto's refusal is measured: an argument
  of a script method and a down-cast in an assignment are not judged.
- `ES-UNDEFINED-BUILTIN-METHOD` (FAIL): a call to a method that the vanilla
  tree's class of a built-in type does not declare. `vector gU =
  gF.Cross(gR);`, with `gF` and `gR` vector locals, made a DayZ 1.30.164200
  server refuse the World module with `Undefined function 'vector.Cross'`:
  the 1.30.164014 Exp scripts declare
  `vector.Cross` (`1_Core/proto/EnConvert.c:239-246`), the 1.30.164200 ones
  do not, and the validator had passed the call against either tree. The
  built-in types are `bool`, `int`, `float`, `vector`, `string`, `typename`,
  `array`, `set` and `map`. Their members are the names at the top level of
  every declaration of that class in the vanilla tree, the addon and the
  `--external-scripts` roots (`modded` included, any `#ifdef` branch,
  comments and strings dropped), and every name written before a `(` from
  such a header to the next class header, plus those of `Class`; a type the
  vanilla tree does not declare is not judged. Judged: `T.Method(` with `T` one of
  them or a typedef of one (`TStringArray`), unless a variable of the file is
  named `T` (`Widget map`, which `ES-VARIABLE-NAMED-AS-TYPE` reports); and
  `name.Method(` where `name` is looked up as in `ES-CAST-UNRELATED-TYPES`
  (a declaration under an `#ifdef` that is not around the call leaves it
  unknown) and declared as one of them, a template of one (`array<string>
  names`) or a typedef of one. A typedef counts when its name has one
  target, no `[]` (`typedef int[] Physics` is a handle) and no class
  declaration anywhere (`ResourceName` is also `class ResourceName :
  string`). A call's result, a member access (`this.m_X.`), an index, a
  `for` or `foreach` variable inside its loop, a local of a block closed
  before the call, a name a later declarator declares (`vector a, x;`), a
  member declared in a parent class, `value` inside a `modded class vector`
  and a parameter whose template arguments the lookup reads across other
  parameters are not judged. Lines that never
  compile are not judged, nor lines that need a DayZ version macro defined:
  the engine defines one `DAYZ_<major>_<minor>` (`1_Core/defines.c:11-14`)
  and the tree does not say which, so `#ifdef DAYZ_1_29`, and the `#else` of
  `#ifndef DAYZ_1_29`, are left out, while the `#ifndef DAYZ_1_29` branch,
  the code of every later build, is judged. Without a usable vanilla tree
  the rule is a SKIP line. A verdict holds for the build the vanilla tree
  comes from: see `--game-root` below.

  Measured against the 1.30.164200 scripts: on the tree of
  the mod that failed, before its fix, the rule reports lines 1957 and 1959
  of one file and nothing else (390 calls judged), and nothing on the fixed
  tree (388 judged). Nothing on the vanilla tree itself (8 870 calls judged),
  and the vanilla control still matches its baseline; nothing either on the
  1.30.164014 Exp tree or a 1.29 tree, each against itself (8 878 and 8 059
  calls judged). Over 236 addon roots
  under `P:\` (2 019 files, 23 885 calls judged) it reports one call,
  `text.StartsWith(` on a string in an old copy of a bench mod: no tree
  declares `StartsWith` (1.29, 1.30.164014 and 1.30.164200), and the shipped
  copy of that mod uses `IndexOf` instead. Before two fixes the same pass
  gave 19 false positives: 18 where the lookup read `map<string, int> m` as
  an array, its `<...>` running from an earlier parameter's `<`, and one on
  `map.ClearFlags(` with a `Widget map` local. A later review
  built a third on a synthetic tree: a `(` that only one
  branch of an `#ifdef` opens hid every later member of `vector`, hence the
  names written before a `(`. It also listed the unjudged receivers above as
  missed calls; they stay unjudged. The rule takes about 1 s on
  that 11-file addon (about 2.5 s on the first call of a
  process) and about 6 s on the 3 056 files of the vanilla tree.

## Which build the vanilla tree is

The rules that read the vanilla tree judge the addon against that tree, not
against the game. A gate that read the 1.30.164014 Exp extract while the
game was 1.30.164200 passed `vector.Cross`, which only the extract declares.
`--game-root`, or `DAYZ_GAME_ROOT`, names
the DayZ install folder (or its `dta\scripts.pbo` itself), and the vanilla
tree is compared with that PBO, `.c` file by `.c` file, by content, with
names compared without case:

```powershell
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root> `
    --vanilla-root <tree> --game-root <DayZ install folder>
```

When they differ, `VANILLA-ROOT-BUILD-MISMATCH` (WARN) gives the counts
(files that differ, files the tree lacks, files only the tree has), the
first five names and the PBO header's `version`; `info.vanilla_build` holds
the counts either way, with `matches`. A folder carries no build number,
and the header's `version` or the exe's version only name a build, so the
comparison is by content. The PBO is read with the fail-closed reader of
`scripts/tools/dayz-vehicle-proxy-contract` (a compressed entry is refused;
without that folder the comparison is a SKIP line too): a PBO
that cannot be read, a folder without `dta\scripts.pbo` or a missing vanilla
tree gives a SKIP line, never a match. Without `--game-root` nothing is
compared. WARN exits 2, which a gate that accepts WARN lets through: a gate
that must stop on a stale tree has to fail on this rule itself.

Measured with the 1.30.164014 Exp extract against a 1.30.164200
game: it gives 111 `.c` files that differ and 14 that the tree lacks
(`1_Core/proto/EnConvert.c` first); `P:\scripts` and an extract of the same
`scripts.pbo` both match (3 056 files). The comparison takes about 1.7 s.

## Compile errors read from one file

These rules come from script modules that did not compile, each with its
log, or from a broken file the validator passed:

- `ES-RESERVED-WORD-IDENTIFIER` (FAIL): a variable, member or parameter named
  `sealed`, `local`, `owned` or `out`. These four failed as names in a real
  compile: `Expected name, not a keyword 'sealed'` on DayZDiag 1.29.163709,
  and `Broken expression (missing ';'?)` for the others (`local` on DayZDiag
  1.30.164014 Exp). Vanilla uses each only as a keyword. Other modifiers
  vanilla uses the same way (`notnull`, `inout`, `autoptr`, `event`...) are
  not listed until a failure is on record. A name counts after its type,
  on the same line or the next, as a later declarator (`int a = 1, out;`)
  and as a foreach variable; a later use of the variable is not reported
  again. Later declarators are found by counting brackets in the text as
  written, lines that never compile included, so one that follows brackets
  which differ between two branches of an `#ifdef`, or a bracket in a
  branch that never compiles, can go unseen.
- `ES-MODULO-FLOAT-CONTEXT` (FAIL): `%` inside an arithmetic expression that
  also holds a float literal, such as `(n % 4) * 0.7`. Both operands of `%`
  can be integers and it still fails with `Unknown operator '%'` (DayZDiag
  1.29 and DayZ 1.30 Exp); computing the `%` into an int local first
  compiles. The expression stops at a call's or an index's brackets, a
  comparison, an assignment, `;` and `,`, and one that holds a string
  literal anywhere is not judged (there `+` concatenates); quotes inside a
  comment are no string. That includes a string that is only the receiver
  of a method: `"cell".Length() + (n % 4) * 0.5` is not judged, because
  types are not tracked and another method could return a string. A float
  literal under an `(int)` cast, or in a parenthesised condition (only the
  results behind a `?` count), does not reach the expression. A float
  variable is not seen: only the literal case is caught.
- `ES-FORMULA-TOO-COMPLEX` (WARN): one statement that holds a string
  literal and joins 18 or more terms with binary `+`. On DayZDiag
  1.30.164289 a statement on one line alternating
  string literals with an `int` and a float's `ToString()`
  (`string s = "a" + i0 + " b" + f0.ToString() + ...`) compiled with 14
  and 17 terms and failed with 18 and 20: `Formula too complex` on its
  line, then `Incompatible parameter 'i0'` there as a cascade, and
  `Can't compile "World" script module!`. The limit is that pattern's:
  other operand types and a statement over several lines are not
  measured, so the rule warns. `++`, `+=` and a unary `+` join nothing.
  Every binary `+` of the statement counts, one inside parentheses or a
  call's arguments too, and whether the compiler counts those is not
  measured. A chain with no string literal adds numbers and is not
  judged. Build the string in steps (`s = s + part;`).
- `ES-UNBALANCED-BRACKETS` (FAIL): the first `(`, `[` or `{` never closed,
  or closed by another kind of bracket, and the first closer with nothing
  to close. `m_Objects.Clear();` sabotaged to `m_Objects.Clear(;` got PASS.
  Brackets are counted on the text without
  comments and strings; this is no parser, so a file it passes can still
  fail to compile. Each branch of an `#ifdef`/`#ifndef`/`#if` block starts
  from the brackets open before it, so a header written once per branch
  with one `{` after the block counts once. When the branches of a block
  end with different brackets open, or an `#ifdef` is never closed, the
  file is not judged. A file with an unterminated string or block comment
  is not judged either: the stripper's warning is the finding there.
- `ES-MODDED-ENGINE-CLASS` (FAIL): `modded class Transport`,
  `modded class DayZPlayerInventory` or `modded class Magazine`. DayZDiag
  1.29.163709 refused `Transport` with `Engine class 'Transport' cannot be
  modded.` and `Can't compile "Game" script module!`. DayZDiag 1.30.164200
  refused `DayZPlayerInventory` and `Magazine` in 4_World the same way, with
  `Can't compile "World" script module!`. Only these three classes are listed:
  another engine class goes in only after a compile refuses it. For vehicles,
  mod the script bases in 4_World instead, `CarScript` or `BoatScript`; for
  ammo piles, `Ammunition_Base`, which compiled modded in the same 1.30 build;
  `DayZPlayerInventory` has no script subclass, so hook the item side
  (`ItemBase.EEItemLocationChanged`) instead.
- `ES-MULTILINE-CONDITION-OPERATOR` (FAIL): a line inside the parentheses
  of an `if (` or `while (` that ends in `&&` or `||`, once per header.
  DayZ 1.30.164014 server refused `if ((t >= A && t < B) ||` followed by
  `(t >= C && t < D))` with `Invalid statement ')'` and `Syntax error` at the
  continuation. One measurement; FAIL since
  the vanilla control found nothing for it on 1.29.0.163451 and on
  1.30.164078 stable. The operator leading the next line is
  the same parser rule (`skills/_shared/enscript/depth/hard-rules.md`) and is not
  reported here; neither is a call's argument list over two lines.

Each finding is wrong wherever the code compiles, so code under another
mod's `#ifdef` is judged too. A branch that never compiles is not: `#if`
blocks, and the `#ifndef` or `#else` branch of a macro the same file
`#define`s first
(`scripts/tools/dayz-script-validator/scripts/shared/dead_branches.py`). An
expression is never
read through a branch that never compiles, nor from the branch that holds
the `%` into another branch of the same block. Blocks are not compared by
their macros: `#ifdef X` and a later `#ifndef X` count as unrelated, so
their lines can still meet in one expression. The terms of a statement
are counted outside every block and along one branch of nested blocks at
a time: two branches of one block, or two blocks side by side, are never
counted together.

Measured: nothing on vanilla 1.29.0.163451 (69 `%` judged) or
on vanilla 1.30.164014 Exp (94 `%`), and on the source that failed in game,
`vector local;`, the reserved-word rule fires on that line. Vanilla
compiles a statement with 14 `+`. A later vanilla control found
no `ES-FORMULA-TOO-COMPLEX` on vanilla 1.30.164289 (3057 files).
