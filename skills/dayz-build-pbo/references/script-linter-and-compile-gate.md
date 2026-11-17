# Script linter and compile gate

How to use the offline script validator before packing, what its result does and does not prove, and the boot
check that shows a deployed mod's script modules really compile.

Not yet checked on `P:\` except where a vanilla file is cited: the validator figures and the project cases
below are measurements on mod projects, not vanilla data.

`/dayz-lint` is the gate `/dayz-build-pbo` runs. It checks the mod's setup first, then runs the code rules of
the script validator in `scripts/tools/dayz-script-validator/` as its second stage, without
`--external-scripts`, so a code error already stops every build. The notes below apply whenever the validator
runs, alone or behind `/dayz-lint`.

## Running the validator

Run it on its own only when you need what the build does not do: pass `--external-scripts` for a mod that
depends on another mod (through `/dayz-lint <ModName> --external-scripts <folder>`), or compare the result
before and after a change.

```
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Covers Enforce `.c`, `.layout`, `config.cpp`, `inputs.xml`, and `.rvmat`, and outputs JSON. The path is
**relative to the root of this repo**, not of your mod: from a mod folder give the full path of your
checkout, or the command dies with `No such file or directory` and reads as "not installed".

- The report keys are **`errors` and `warnings` at root**, not `findings`.
- ⚠ **`status` is `WARN` even if `errors` is 0**, and the exit code is `0 PASS / 1 FAIL / 2 WARN`:
  a clean tree with warnings exits with **2**. Gate on `len(errors)`, never on `status` nor on
  the wrapper exit.
- **Compare against a base** (the base commit in a worktree): the delta is what attributes a new
  error to your change; an absolute number does not.
- **It is not a compiler.** Enforce only compiles upon loading the world. It does catch dangling
  references after a deletion, which is what a symbol grep misses. Measured 2026-09-08 on a mod of
  271 files: about 60 s; removing 8 left them at 263, with 0 errors on both sides.
- ⚠ **And it has a blind spot that costs a startup: it does not see an undeclared member.** Detail,
  measured case, and the sweep that does catch it, in
  `dayz-test-ingame/references/windows-launch-cycle.md`, Step 0.

The heuristic checks in `pre-build-checks.md` (check 7) are the fallback when the validator is not
available, and a useful second pass when it is.

## Advanced: Scripting Validation

Enforce Script supports `++`/`--` and `foreach (Type t : collection)`: vanilla uses them (`foreach` at `P:\scripts\3_game\tools\cameratools.c:14`, `last_index++` at `P:\scripts\3_game\tools\tools.c:200`),
so a validator must NOT flag them. Ternary (`x ? a : b`) is different:
no vanilla script on `P:\scripts` uses it and it does not compile
(`skills/_shared/enscript/patterns/language_workarounds.md`, "No Ternary Operator"), so write `if`/`else`. The array caveat:

```enforce_script
// Arrays: no '+=' concatenation operator. Add elements with Insert()/InsertAll():
selections.Insert("newSelection");    // append one
selections.InsertAll(otherArray);     // append many

// Supported and idiomatic (do NOT flag):
i++;  --i;                            // increment / decrement
foreach (string s : selections) { }   // foreach over a collection
```

For the authoritative Enforce Script rule set, see the `enforce-script-reference` skill.

---

## Offline script linter (pre-PBO)

**Blocking gate — run before packing, not after.**

```
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

Exit `0` PASS / `1` FAIL / `2` WARN. **Do not build a PBO on exit 1**: the errors it catches (`Unknown type`, local redeclaration, override of an absent method, `delete`, item declared under the wrong `CfgXxx`) only surface when the script module compiles at boot, so packing first turns a one-second check into a full in-game cycle. Add `python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>` when the mod ships UI.

Green here means the module should COMPILE and the asset should LOAD. It says nothing about engine behaviour — see `dayz-mod-workflow`, section 8 "Offline gates: structure is not behaviour", for the full contract and the known coverage limits.

### The linter scans the WHOLE addon_root and blames the mod for all of it

It walks `<addon_root>` recursively and every finding is reported as the mod's,
whatever subtree it came from. If anything that is not your shippable source
lives under that root — a read-only copy of vanilla for reference, a `_source_*`
rip, a `_recovered` tree, a copy of a dependency, an isolated build scratch — its
findings land in your numbers.

Measured: mounting five vanilla files under an addon root for a delegate to read
added **19 errors and 23 warnings** that belonged to Bohemia, not to the mod, and
turned a clean tree into exit `1`. Vanilla legitimately uses `delete`,
`ProcessDirectDamage` aliases and patterns this ruleset forbids for mods, so the
errors are correct — they are just not yours.

Both failure directions cost a cycle, and the second is the dangerous one:

- **Inflated**: a clean mod reads FAIL, and the natural next move is to "fix"
  code you must not touch. Editing a reference tree to make a gate go green
  neutralises the instrument instead of passing it.
- **Masked**: if the *baseline* of a before/after comparison was taken with the
  contamination present, a real new finding can hide inside the noise. This is
  the one that ships a defect.

Rule: **attribute by path before believing any count.** Split findings into the
mod's own source and everything else, compare only the mod's set against the
mod's baseline, and quote both numbers when reporting. Never reduce a delta to
the process exit code: the code is computed over the whole root, so it is red
whenever any foreign subtree is dirty, and it cannot distinguish "my change
broke something" from "the reference copy was always like that".

Corollary for delegation: if you mount reference sources inside the workspace so
a worker can read them, say in the brief that their findings are not the
worker's and are not to be fixed. Without that line, a diligent worker will try
to clean them.

Two more traps around the same instrument:

- More than one snapshot of the validator can be installed, and their rulesets
  differ — two copies reproduced identical *warning* sets while disagreeing on
  errors. Pin one path for baseline and delta, or the comparison is meaningless.
- Do not capture its JSON with a PowerShell `>` redirect: PS 5.1 prepends a
  UTF-8 BOM and `json.load` rejects the file. Read stdout via `subprocess`, or
  decode `utf-8-sig`.

### A deployed PBO with the right version does not prove it compiles

Offline-green plus a correct deploy is still not a compile. Measured 2026-08-29: a mod
was rebuilt and deployed with the source bumped v9 to v10, the deployed PBO byte-scanned
clean (version string present, all new verbs present, negative control against the previous
build), and the server still died with `Can't compile "Mission" script module!`.

Cause: a **partial sync between the repo addon tree and the `P:\<Mod>` build tree**. The
feature was two files -- a field in one, its consumer in the other. The sync copied the file
that declares the field (dropping it, because that feature is deliberately unpublished) but
not the file that reads it, leaving an orphaned consumer:

    P:\<Mod>\scripts\5_Mission\Bridge.c:1340   if (a.dest == "hands" || a.hands)   <- consumer
    <Mod>_dev\addon\...\Messages.c            string hands;  ABSENT               <- field

Enforce fails the WHOLE module on one unresolved symbol, so the log also shows errors from
unrelated mods loaded in the same run. The FIRST error names the real culprit; the rest are
collateral. Do not debug the second error first.

**Gate after any deploy:** boot the server with ONLY that mod and grep the fresh script log
for its module line. Cheap, decisive, and it isolates the mod from co-loaded ones:

    Module: Mission; loaded 217x files; 508x classes

Zero `Can't compile` / `Can't find variable` / `Failed to load mission scripts` is the pass.
Read the log from THIS boot: a stale `script_*.log` from an earlier day carries a green
module line and answers the question with old data.

**Diff the trees before packing** whenever a mod keeps a `_dev` repo tree beside a
`P:\<Mod>` build tree: `diff -rq` over the addon subtree. One line of drift there is
invisible to every byte-level PBO check, because the PBO faithfully contains the broken
source.

**And do not use mtime as the freshness signal.** `shutil.copy2`, `robocopy` and `xcopy`
preserve the source timestamp by design, so a file that was synced into the build tree one
minute ago can carry a timestamp from days earlier. Measured 2026-08-29: a source file fixed
and copied into `P:` at 03:51 still reported an mtime of 24-Aug 18:29, identical to its
origin, while its content and its byte size both proved the edit had landed.

That breaks the obvious build-debt check. Comparing a deployed PBO's mtime against the newest
source in the build tree can report NO DEBT while a freshly-synced source sits under a stale
PBO, because the sync handed the source an old timestamp. Adjudicate build debt by CONTENT:
sha256 the deployed PBO against a rebuild, or compare per-file hashes of the packed entries
against the tree. Treat mtime as a hint that orders events, never as the fact that decides
whether an artifact is current.
