# Script validator and compile check

How to run the offline script validator before packing, what a green result proves and what it does not, and the boot check that shows a deployed mod's script modules really compile.

The validator figures and the cases below were measured on mod projects, not read from vanilla data; the lines that cite `P:\` are the exceptions.

`/dayz-lint` is the gate `/dayz-build-pbo` runs. It checks the mod's setup first, then runs the code rules of the script validator in `scripts/tools/dayz-script-validator/` as its second stage, without `--external-scripts`, so a code error already stops every build. Everything below applies whenever the validator runs, alone or behind `/dayz-lint`.

## Running the validator

Run it alone only when you need what the build does not do: `--external-scripts` for a mod that depends on another mod (through `/dayz-lint <ModName> --external-scripts <folder>`), or a comparison before and after a change.

```bat
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

The validator covers Enforce Script `.c`, `.layout`, `config.cpp`, `inputs.xml` and `.rvmat`, and prints JSON. The path is relative to the root of this repo, not of your mod: from a mod folder give the full path of your checkout, or the command dies with `No such file or directory` and reads as "not installed". Add `ui_reconcile.py` when the mod ships UI; it checks `FindAnyWidget` and `FindWidget` names against the real widgets in the `.layout` files and `#STR_` keys against the stringtable, two faults that compile and show only when the menu opens. It takes under a second on a whole addon, so run it on every pass.

How to read the result:

- The report keys are `errors` and `warnings` at the root, not `findings`.
- `status` is `WARN` even when `errors` is 0, and the exit code is 0 for pass, 1 for fail and 2 for warnings, so a clean tree with warnings exits 2. Gate on `len(errors)`, never on `status` or the exit code.
- Compare against a base, the base commit in a worktree. The difference attributes a new error to your change; an absolute count does not.
- Never pack on exit 1. What it catches (`Unknown type`, a local declared twice, an override of a missing method, `delete`) otherwise shows only when the module compiles at boot, which turns an offline check of about a minute into a full game cycle. Fix the error, or justify it in writing in the handoff with the rule id and the reason. Read every warning.
- Capture the JSON through `subprocess` or decode it as `utf-8-sig`. A PowerShell 5.1 `>` redirect adds a UTF-8 BOM and `json.load` rejects the file.
- Pin one installed copy of the validator for the base and the comparison. Copies differ: two of them gave the same warnings and different errors.

It is not a compiler; Enforce Script compiles only when the world loads. It does catch references left dangling after a deletion, which a symbol grep misses: on a mod of 271 files it took about 60 seconds, and removing 8 files left 263 with 0 errors on both sides. It does not see an undeclared member; the case and the sweep that catches it are in `skills/dayz-launch-test/references/windows-launch-cycle.md`, "Run the offline linter first". The fallback checks for when the validator is not available are in `stringtable-and-script-checks.md`.

## What Enforce Script accepts

Enforce Script supports `++`, `--` and `foreach (Type t : collection)`, and vanilla uses them (`foreach` at `P:\scripts\3_game\tools\cameratools.c:14`, `last_index++` at `P:\scripts\3_game\tools\tools.c:200`), so a validator must not flag them. The ternary `x ? a : b` is different: no vanilla script under `P:\scripts` uses it and it does not compile (`skills/_shared/enscript/patterns/language_workarounds.md`, "No Ternary Operator"), so write `if` and `else`. Arrays have no `+=`:

```c
selections.Insert("newSelection");    // append one
selections.InsertAll(otherArray);     // append many

i++;  --i;                            // supported, do not flag
foreach (string s : selections) { }   // supported, do not flag
```

The full rule set is in the Enforce Script pack (`skills/_shared/enscript/depth/`).

## Offline gates: structure is not behaviour

A passing offline gate does not let you say "done" when it checks structure and the goal is engine behaviour.

| Gate | What it checks | What it proves |
|---|---|---|
| Structural (offline, repeatable) | Class name equals file name, paths exist, topology, winding and UVs, selection sums, braces, the APIs cited (the mini-audit in `skills/dayz-scope-mod/references/implementation-protocol.md`), a skeleton or bind compared with vanilla | The module should compile and the asset should load |
| Behavioural (engine running, or Buldozer) | Deformation under animation, visible render and winding, mass, centre of mass and collision, getting in, the proxy convention the engine applies, elbow and wrist IK | How it behaves; nothing offline can show this |

The behavioural gate stays mandatory on its own (`/dayz-gate ingame`, `behavior` and `visual`).

The validator's tables in `scripts/tools/dayz-script-validator/scripts/shared/vanilla_reference.py` are small on purpose and cover only some rules. When a vanilla scripts tree is found (`--vanilla-root`, then `DAYZ_VANILLA_ROOT`, then `P:\scripts`), the validator also reads it for `ES-UNDEFINED-CLASS-REF`, `ES-UNDEFINED-BUILTIN-METHOD` and the 1.30 `RegisterConstructionSyncVariables` hook; without one those rules are reported as skipped, not as findings. Rules that rest on the small tables miss things by design, so green is not proof that a fault is absent.

Before iterating on an offline number, ask whether it follows the behaviour you want or is a proxy the engine ignores. For a proxy with no shown link, run one behavioural test before polishing it further, and stop if it does not follow. Two cases:

- A deform test in Blender cut edge stretch from 34 times to 6 to 9 times over about 12 offline iterations with no change in game, because the engine skins against the real `OFP2_ManSkeleton` from `model.cfg`, not the FBX armature.
- A vehicle proxy frame derived as identity passed offline twice; the engine applied another convention and the body proxy came out rotated about 90 degrees.

## The validator blames the mod for everything under the root

It walks `<addon_root>` recursively and reports every finding as the mod's. Anything else under that root (a read-only copy of vanilla, an extracted source, a recovered tree, a copy of a dependency, build scratch) lands in your numbers. Five vanilla files placed under an addon root for a worker to read added 19 errors and 23 warnings and turned a clean tree into exit 1. Vanilla rightly uses `delete`, `ProcessDirectDamage` aliases and patterns this rule set forbids for mods, so the errors are correct; they are just not yours.

- **Inflated:** a clean mod reads as failing, and the next move is to "fix" code you must not touch. Editing a reference tree to turn a gate green breaks the gate instead of passing it.
- **Masked:** if the base of a before and after comparison was taken with the foreign files present, a real new finding hides in the noise. This is the one that ships a defect.

Sort findings by path before believing any count: split the mod's own source from everything else, compare only the mod's set with the mod's base, and quote both numbers. Never reduce the difference to the exit code, which covers the whole root. When you place reference sources in the workspace for a worker to read, say in the brief that their findings are not the worker's to fix.

## Both sides must compile

A server compile pass does not cover the whole build. Code under `#ifndef SERVER` (vanilla has such blocks, for example `P:\scripts\4_world\classes\constructionbase.c:151`) is left out of the server's compile and can still break the client's module. Before accepting a build, boot both server and client, read the script compile of each, and record a pass for each side. Wrapping a failing declaration in a side guard is no fix unless the side that still compiles it passes too. `/dayz-gate ingame` boots both and reads both sets of logs.

## A deployed PBO with the right version may still not compile

A clean offline result plus a correct deploy is still not a compile. One mod was rebuilt and deployed with its version raised, the deployed PBO scanned clean (the new version string and every new verb present, a negative control against the previous build), and the server still died with `Can't compile "Mission" script module!`.

The cause was a partial sync between the repo's addon tree and the `P:\<Mod>` build tree. The feature was two files, a field in one and its reader in the other. The sync copied the file that declares the field, dropping the field because that feature is deliberately unpublished, but not the file that reads it, which was left reading a field that no longer existed (`if (a.dest == "hands" || a.hands)` with no `string hands;` declared).

Enforce Script fails the whole module on one unresolved symbol, so the log also shows errors from unrelated mods loaded in the same run. The first error names the real culprit; debug that one first.

After any deploy, boot the server with only that mod and grep the fresh script log for its module line:

```text
Module: Mission; loaded 217x files; 508x classes
```

No `Can't compile`, `Can't find variable` or `Failed to load mission scripts` is the pass. Read the log from this boot; a `script_*.log` from an earlier day carries a green module line and old data.

Whenever a mod keeps a development tree beside a `P:\<Mod>` build tree, diff the two before packing (`diff -rq` over the addon folder). One line of drift there is invisible to every byte check on the PBO, because the PBO faithfully holds the broken source.

Never use the modified time to decide freshness. `shutil.copy2`, `robocopy` and `xcopy` keep the source timestamp by design, so a file synced into the build tree a minute ago can carry a time days old; one fixed file copied into `P:` kept its origin's timestamp while its content and size proved the edit had landed. Comparing a deployed PBO's time with the newest source can then report nothing to rebuild while new source sits under an old PBO. Decide by content: hash the deployed PBO against a rebuild, or compare per-entry hashes with the tree. The time only orders events.

## Script module capacity

Measured in game: the log line `SCRIPT : Module: World; ... used X/33554 kB` reports one shared arena of about 32 MiB for vanilla and every loaded mod. Source lines, file bytes and file counts do not model that capacity: comments can be free, while declarations, generic instantiations and compiled method bodies cost structure and bytecode.

There is no single "kB per class" figure. Generic specializations formed one group at 5.6 to 6.6 kB each, small shell classes took 0 to 1 kB, and two heavy classes took 139 kB. Size a reduction with engine readings of the same kind of class before and after. Count class declarations case sensitively, so a variable written `Class x` is not taken for a `class X` declaration.

When a module nears capacity, remove or parameterise repeated script declarations before shortening text. A public `config.cpp` class name does not need a script class of the same name; it binds to the nearest scripted ancestor. Keep the public config names and the `types.xml` entries while collapsing redundant script subclasses, then read the same module line again on both sides.
