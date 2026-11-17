# Post-build gates: is the PBO the one you meant to build?

Checks to run on a built or deployed PBO: its scripts and models are really inside, its entries match the
source, two builds are compared the right way, the mod's script modules load, and the gate you rely on can
fail.

Not checkable on `P:\`: unless a line cites a vanilla file, what follows is measured behaviour of AddonBuilder,
binarize and the game's loader, with the tool version named where it was recorded. Vanilla files on `P:\`
cannot confirm it.

## What `build.py` checks after every build

| Gate below | In `build.py` |
|---|---|
| Scripts and models are in the PBO | `check_pbo_contents`: every staged `.c` and `.p3d` that `include.lst` lets through must be an entry, or the build fails. Other missing files are a warning. |
| Derived manifest and extras check | Same function: the expected entries come from the staged source, never a hand-kept list; entries with no source file are a warning; `texHeaders.bin`, the prefix file and `config.bin` are allowed. |
| Header prefix | The PBO's `prefix` property must equal `<ModName>`. |
| 21-byte checksum trailer | `pbo_entries.py` checks it; a PBO without it gets a warning. |
| Fresh PBO, real result | The PBO must be newer than the build start, and `[ResultCode]` in AddonBuilder's log must be 0. |
| Stale `-temp` tree | The temp dir is removed before the build, and the build stops if it survives. |

Everything else in this file is manual: the negative control, per-entry comparison of two builds, the script
module name, the property gate, the model-path gate, and the checks on a deployed PBO.

## Post-build check — confirm the PBO actually contains your scripts (binarize drops `.c`)

`build.py` always passes `-include=include.lst`, which lists `*.c` and `*.csv`, so the two losses described in
this section do not happen in its builds, and its content check proves that per build. The section matters for
a hand-run AddonBuilder and for a PBO somebody else built.

AddonBuilder's default binarize mode does **not** copy `.c` script files — they aren't in its
binarize/copy include-list. A scripts-heavy or scripts-only addon built with a plain
`AddonBuilder src dst -clear` can pack to a **config-only PBO** (`config.bin` + the CfgMods
path strings, nothing else) while still printing `Build Successful`. In-game the mod *mounts*
(its CfgPatches name appears in the server `script.log` `defines:` list) but **no script runs**:
no modded class merges, no hook fires. Measured: a scripts mod packed to 662 bytes
under binarize; `-packonly` produced the correct 124 KB PBO with all its `.c`.

Pack mode by addon type:
- **Scripts-only** (no `.p3d`/`.paa`): build with `-packonly` (copies everything as-is;
  `config.cpp` stays text, which DayZ loads fine).

`.c` is not the only casualty of the include-list: **`.csv` is dropped too**. Measured
on a two-file addon: the binarizing pass produced a PBO with `config.bin` and
**no `stringtable.csv`**, while `-packonly` on the same source kept it. An addon whose only
job is to carry a stringtable therefore packs to something that mounts and translates
nothing. Same silent shape as the scripts case: `Build Successful`, mod mounts, feature
absent.
- **Mixed — models + scripts** (vehicles, items): you still need binarize for the `.p3d`, so
  `-packonly` is wrong. Confirm AddonBuilder's include-list copies `*.c`/`*.h`, or the scripts
  vanish silently — a CarScript vehicle would then load but never simulate.

### `-include` is not the final PBO manifest

AddonBuilder has two input paths. Its native binarization/discovery path handles `config.cpp`,
`.p3d`, and face-referenced `.rvmat`; these can enter the PBO even when their suffix is absent
from `-include`. The ordinary sync path carries `.c`, `.paa`, `.ogg`, `.layout`, and `.csv`;
with a fresh temp, an omitted suffix is silently dropped. So the rule "treat `-include` as an
exclusive filter" ("Further build rules" below) holds for the ordinary sync pass, not for the
final PBO contents.

Measured case: an `.rvmat` omitted from `include.lst` still entered and was binarized because
three `.p3d` files referenced it. This does not override binarized-build rule 2 in
`addonbuilder-rules.md` (rvmats referenced only from `config.cpp` do not enter the PBO):
an `.rvmat` referenced only by `config.cpp` may still be absent.

Do not add material suffixes to `include.lst` as a precaution and treat that as proof.
List, count, and name the built PBO entries. Compare ordinary payload against the source tree,
and check the complete config-referenced rvmat set separately. Presence in the list does not
prove that an entry was packed; absence from the list does not prove that a native input was
dropped.

Always verify after packing (cheap; catches it instantly):
```powershell
$txt = [System.IO.File]::ReadAllText($pbo, [System.Text.Encoding]::GetEncoding('ISO-8859-1'))
$txt.Contains('YourKnownClassName')   # must be True; also sanity-check the PBO byte size
```
Debugging heuristic — when "the mod loads but no script runs", grep the deployed PBO for a
known class string **before** chasing the script logic, the mission class, or server checks.

**Script-footprint caveat:** PBO byte shrink is NOT evidence of script-arena reduction. When the goal is script memory footprint, do not adjudicate capacity from source bytes, line counts, or PBO container size — the container size is a sanity/identity check, not a proxy for compiled memory. Measure control and candidate with DayZDiag under frozen stack/order/mission/config; report Game, World, Mission, and total separately, along with files/classes and hashes. Only the repeated engine delta sustains a causality or capacity claim.

### Post-build check — deployed-artifact reconciliation and exception-safe gates

- **Moving a project to another machine is a deployment boundary.** A copy of the sources does not bring Steam `!Workshop` or the server profiles. Before the first in-game test, inventory those external dependencies and profiles, extract a census of the deployed PBO entries, and compare each expected entry with the current compilable tree by content hash. Whole-PBO byte equality is not a substitute for per-entry comparison; rebuild and deploy on any unresolved divergence. Run source-sync steps only in a mode that cannot overwrite restored sources with stale assembly output. In PowerShell, `powershell -File x.ps1 -Array a,b` passes one string, so a gate fed that way fails without deploying; call the script with `&`.

### Content gate: derived manifest, extras check, and negative control

A content gate built on a hand-maintained closed file list goes stale in both directions
simultaneously: it names files that have since been deleted (killing the build at
startup) and omits files the PBO actually ships (a PASS then proves nothing about half
the payload). The correct construction:

- **Manifest = enumerate the source tree.** The expected file set is derived from what
  exists in the addon source directory at build time, not from a static list. A derived
  manifest cannot omit what is present.
- **Extras check on the PBO.** After packing, list the PBO entries and flag any file
  that is NOT in the derived manifest. This is what a closed list was actually buying:
  catching files that should not be there.
- **Exclude AddonBuilder-generated metadata from the extras check.** `$PBOPREFIX$.txt`
  and `texHeaders.bin` (the .paa index) are produced by AddonBuilder and have no source
  counterpart by design; they are expected in the PBO and must not trigger a flag.

**Negative control (mandatory).** A gate that only asserts presences cannot detect that
you failed to remove something you thought you removed. For every line or file the build
is supposed to have eliminated, the gate must assert that it is ABSENT from the PBO.
Presence-only checks pass even when stale content remains.

**Payload anchors go stale just like the manifest.** Before treating an absent anchor
(e.g. a `CreateAttachment("…")` call) as a regression you introduced: extract the
DEPLOYED PBO and check whether it contains the anchor. If it is absent from the deployed
PBO as well, the anchor is stale — there is no regression. Only an anchor present in the
deployed PBO but missing from your new build is a true regression.


### AddonBuilder non-determinism: byte identity is valid within a build, invalid between builds

Measured on two mods: with the same source MLOD and the same
`-include`, two AddonBuilder runs produce different `.p3d` bytes. The payload (vertices, normals,
UVs, named selections, textures, material set) hashes identically; only the ORDER of `faces`,
`sections`, and the material array changes. Of 10 byte-different entries in the first measurement,
8 were pure reordering and 2 were the real change.

**Within a build**, byte identity is valid and must be enforced: the binarized temp output must be
byte-exact against the PBO entry (both come from the same run). The non-determinism does not
invalidate that gate.

**Between builds**, comparing bytes or sizes gives false positives. A "only X should have changed"
gate against the deployed PBO will flag ~8 of 11 untouched entries. The correct between-builds gate
is an **unordered multiset** per LOD keyed on `(material, texture, vertex-index, lit_bit)`,
constructed by walking `sections` and mapping each face to its material. Vertex indices are
comparable because vertex order is stable (its hash matches across runs). Diagnose in three
steps: counts, then payload, then the canonical multiset.

**Mandatory self-check:** if the sections do not cover ALL faces of the LOD, the multiset is
incomplete and the gate must declare itself **VOID** rather than pass.

**Scripts are stable:** the non-determinism is in the ODOL binarization of `.p3d` only.
`.c` script entries are byte-stable between builds (measured: 1 of 147 `.c` entries changed size,
and it was exactly the file that was edited; all 50 `.p3d` sources were byte-identical between the
two trees). Therefore **comparing script entries between two PBOs IS a valid change detector** —
the "do not compare bytes between builds" rule applies to `.p3d` only; applying it to scripts
discards the cheapest gate available.

**SHA-pinned artifacts are irrepeatable.** If a qualification is pinned to a PBO SHA, rebuilding
"to regenerate it" produces a different hash from an identical tree and breaks the pin silently.
In a project with release or audit anchored to a hash, "do not rebuild the PBO" is a hard
invariant: the file is a unique artifact and must be backed up by hash.

- **Every expected difference needs a pinned base.** Audit gate code for `continue`, `pass`, `ok += 1` and allowlists. A file known to differ because a delta/merge is not yet promoted cannot receive an unconditional OK: store the `SHA-256` of the exact source base at derivation time in an `enforce-base.json`, mark the artifact `STALE` if that base moved, and force the merge to be rebuilt. Separately, a proximity check for words such as "retired" or "obsolete" answers an adjacent question; require the live identifier beside each retired reference.

### Compare the entries of two builds

After a rebuild, check that only the entries you meant to change differ:

```
python scripts/tools/dayz-pbo-diff/pbo_diff.py --old <old.pbo> --new <new.pbo> --out <diff.json>
```

It compares the SHA-256 of every entry's payload and the header properties; `differing` lists every
entry that changed or is on one side only. Read it with the non-determinism rule above: between two builds a
different `.p3d` entry proves nothing by itself, while a different script, config, material or
texture entry does (§"Binarize is not byte-deterministic" below). `--ignore-prefix <prefix>` drops
a prefix from `differing_not_ignored`, never from `differing`. A compressed entry is refused
(exit 1); see `scripts/tools/dayz-pbo-diff/README.md`.

### Two silent no-load causes to check before blaming the engine

Both produce the same symptom as the binarize/`.c` case above — the mod mounts, nothing
runs, the log is empty — and both are decidable offline in seconds. Check them before
spending an in-game session interpreting silence, and before concluding "this API does not
work" from a log line that was never going to exist.

**1. The script-module name selects the compile stage. A wrong name loads nothing.**
`CfgMods.<Mod>.defs` must map each source folder to its own stage: `3_Game` ->
`gameScriptModule`, `4_World` -> `worldScriptModule`, `5_Mission` -> `missionScriptModule`.
Declaring `4_World` files under `gameScriptModule` is accepted by the packer and produces no
warning, but the code never reaches the stage where its base classes exist. Measured:
a bench mod declared `files[]={"<Mod>/scripts/4_world"}` under `gameScriptModule`
and emitted nothing at all; two mods that load on the same machine
both use `worldScriptModule` for `4_World`. `/dayz-lint` reports the
mismatch as `script-module-layer`. The failure mode in game is silence rather than an error.

Match the **case** of the folder too, on disk and in `config.cpp`. Working mods ship
`4_World`/`5_Mission` capitalized; a lowercase tree packs lowercase paths into the PBO while
`config.cpp` asks for the capitalized ones, and Windows will not tell you.

```powershell
# Declared modules vs. what is actually on disk
$cfg = Get-Content "$mod\config.cpp" -Raw
[regex]::Matches($cfg,'class\s+(\w+ScriptModule)') | % { $_.Groups[1].Value }
[regex]::Matches($cfg,'"([^"]*scripts/[^"]+)"') | % {
  $p = Join-Path $mod ($_.Groups[1].Value -replace '^[^/]+/','' -replace '/','\')
  "{0} -> on disk: {1}" -f $_.Groups[1].Value, (Test-Path $p) }
```

**2. Every vanilla PBO ends in a 21-byte trailer; hand-rolled packers omit it.** The trailer
is one `0x00` separator followed by the SHA-1 of everything before it:

```
trailer == b"\x00" + sha1(data[:-21]).digest()
```

Measured on 6 vanilla PBOs (`ai`, `ai_bliss`, `animals`, `animals_bliss`,
`anims_anm_infected`, `anims_anm_player`), 6/6 match, 10 KB to 350 MB. AddonBuilder writes it (`pbo_entries.py` checks it on every `/dayz-build-pbo` build);
a custom Python/Node packer usually does not, because a PBO without it still parses correctly
with any reader you write yourself — the omission is invisible to a round-trip test, which
compares the packer against its own output.

Whether the engine *rejects* a PBO lacking the trailer is **not established**, and in the
measured case it was not the cause. Write it anyway: it is an idempotent append that removes
the variable instead of leaving it to be investigated later under time pressure.

```python
data = open(pbo, "rb").read()
if not (len(data) > 21 and data[-21] == 0
        and hashlib.sha1(data[:-21]).digest() == data[-20:]):
    open(pbo, "ab").write(b"\x00" + hashlib.sha1(data).digest())
```

**Gate ordering.** A build step that reports success without checking `$LASTEXITCODE` after
each AddonBuilder invocation, and a deploy step that accepts a PBO on `Test-Path` alone, will
both hand you a stale artifact and call it fresh. Check the return code after *every*
invocation — and for AddonBuilder, whose exit code is 0 even when the build fails
(`addonbuilder-rules.md`, binarized-build rule 1), read the rpt's `[ResultCode]` and check that the PBO exists and was rebuilt — and
print a `SHA-256` build-id at pack time that a boot sentinel inside the mod
can be checked against — otherwise an old PBO is indistinguishable from a new one that does
nothing.

---

## Build appendices

## Mandatory post-build PBO verification

The case behind this checklist: AddonBuilder reported "Build Successful" with a 613-byte PBO (its internal sync to temp copied 0 files, probably a collision with OneDrive); additionally the measured PBO was residue from a previous build, because AddonBuilder names the PBO after the source folder, not after `-prefix`.

Checklist after EACH build (exit 0 and "Build Successful" are NOT enough):
1. PBO size larger than a reasonable threshold (a script mod is around 15-30 KB; ~600 B = packed empty folder; a 2 KB PBO of a model mod means the model fell out).
2. Content: binary grep of expected strings (names of .c files, a RECENT code literal to detect residue): PowerShell `[Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($pbo)) -match "my_marker"`.
3. Name: PBO outputs as `<SourceFolderName>.pbo` — if you build from staging, the folder MUST be named exactly like the mod (e.g. `%TEMP%\<Mod>\`), or you will deploy and measure the wrong file.
4. Local staging (outside OneDrive) for build source: AddonBuilder sync against OneDrive paths can copy 0 files without reporting error.
5. PROPERTIES gate after `ExtractPbo` — SHA is not enough: a hash manifest compares the same file on both sides, so gives green even if packed `.p3d` were built BEFORE property entered generators. Measured case (a helicopter mod): `autocenter=0` was added to visual LOD of hull in both generators at 01:52/02:07, PBO was packed at 02:15 from previous `.p3d`, and manifest gave green; upon measuring the 48 extracted `.p3d`, the 8 sub-models had it and **the 40 hulls did not**. The gate must read the specific property **per LOD**, with expectations declared in table (property, expected value, reason, explicit exclusions — e.g. Memory LODs, having no geometry to recenter, are excluded). A gate only comparing hashes cannot turn red from this cause.
6. Model-count gate from the PBO ENTRY TABLE — size alone passes a model-less PBO: in a measured case, a build with exit 0 and "Build Successful" packed an 8.0 MB PBO with 132 entries and zero of ten `.p3d`, because the stage path carried the addon folder name higher up (`...\<Mod>_stage0\stage\<Mod>`); renaming only the stage's parent folder produced full PBOs again (21.5 MB, 140/140 entries, 10/10 ODOL). The `<4096 B` size gate misses it, and the "`-temp` must stay under the work drive" explanation (`addonbuilder-rules.md`, command-line rule 1) did not reproduce in four later builds with `-temp` outside the work drive (work drive mounted): re-measure before trusting either explanation of a tiny or model-less PBO. Count the `.p3d`/ODOL entries of the built PBO against the stage before trusting any build.

### Property-gate controls

The expectation table must also name controls that are expected not to change, such as the
control arm of an A/B build or a byte-frozen copy. A blanket "all LODs" requirement rejects
healthy controls and gets disabled; declare the expected value and reason for each control
instead.

## Model-path resolution gate — validate what the engine will resolve

The case behind it (a weapon mod): `model=` pointed at the PBO root while the
binarized p3d lived in `data\`; dirty-temp builds smuggled a raw MLOD into the
PBO root and the engine loaded that file for 11 versions, so every offline gate
validated a p3d the runtime never resolved.

Before declaring any build/deploy good:

1. Extract (or listFiles) the DEPLOYED PBO and read the compiled config.bin
   (classnames and paths survive rapification as plain strings).
2. For every `model=` — and every texture/rvmat path the config references —
   verify the path resolves to an entry INSIDE the PBO under its `$PREFIX$`,
   case-insensitive.
3. A second copy of the main `.p3d` at a non-referenced path (typically the
   PBO root) is NOT dead weight: it is the tell of a dirty AddonBuilder temp
   plus a mis-pointed `model=`. Fix the reference and rebuild with `-clear`.
4. Run this on the artifact the engine loads (the deployed PBO), never only on
   the source tree or the build temp.

---

## Further build rules

- **A compile error in a vanilla file may be a cascade.** Facing `quoted string not closed`, EOF or a line pointed out in vanilla, treat the file and line as a possible module cascade and inspect a BOM or a truncated file earlier in the module first. Diagnose and correct at byte level on the machine that holds the real files, not on a stale mount.
- **`-include` is an exclusive filter.** Treat it as one and always validate from an empty temp. Separate the `.p3d` sync from the step that binarizes them to ODOL; fail if entries are missing or the size shows an MLOD copied as-is.
- **A pin by sha256 or size breaks on its own going through git.** With `core.autocrlf=true` (default on Windows) `git add` normalizes to LF and `git checkout` rewrites with CRLF, so blob and working tree cease to match pinned values (measured: a text file of 1577 B pinned against 1548 B in the blob, and 8 failures on a Windows clone). Run the gate on a **freshly checked-out clone**, not on a copy exported with robocopy: the copy preserves the original bytes and passes on a tree that no one receives. Put a `.gitattributes` with `* text=auto eol=lf` in from the first commit, plus `-text` on whatever is compared byte by byte. It is the same axis as the AddonBuilder byte identity section above: before comparing hashes, make sure you compare the tree that gets published.
- **Trace a release to its whole source tree.** A release artifact is traced to its commit by the hash of its entire source tree, not of the touched files. Pre-release gate: commit or canonical source ↔ full build tree ↔ PBO. An incremental "verified" sync only verifies its own delta.

## A mod can have two PBOs, and the one your gate validates may not be the one the game loads

Measured on a vehicle mod, investigating why a freshness gate gave a reading
that did not add up:

| path | size | date | model inside |
|---|---:|---|---|
| `<Mod>\<Mod>.pbo` (in source tree) | 5.92 MB | 22-Jun | **binarized** `.p3d` (ODOL, 2,036,911 B) |
| `P:\Mods\@<Mod>\Addons\<Mod>.pbo` (the deployed one) | 17.22 MB | 21-Jun | **unbinarized MLOD** (10,914,580 B) |

Two builds via two different paths, with **73 entries, 5 `.c`, 36 `.paa` and 23 `.rvmat`
both** — meaning both complete, neither obviously broken. The visible difference is
size, and size is explained by binarization, not by anything missing.

**The one the game loads is the one in `Mods\@<Mod>\Addons\`, and it was the older of the two.**

Consequence for any packaging gate: **check all packages that
exist for that mod**, not one chosen by hand. The complementary way avoids having to
guess which pipeline is authoritative — if any of them does not carry what the model
requires, or is older than the sources, the verdict is red. A gate pointed only to the source
tree one can turn green on a deployment that never received the work.

Two instrumentation details that came out of the same place:

- **The presence of `.p3d` is checked by NAME, never by size**: one path
  binarizes it and the other does not, and the same model weighs 5.4x different in each package.
- A freshness gate traversing the source tree must exclude `*.pbo`, `*.bisign`,
  `*.bak*` and temp files. A backup is written **after** what it
  copies, so counting it as source leaves the gate red forever for a reason that
  has nothing to do with package being stale.

## "Build Successful" does not say it packaged your sources: the `-temp` tree can survive

Sister to the previous section. That one says you may be validating the wrong
PBO; this one, that you may be building the **correct PBO from the
wrong sources**. Measured on a large mod, after a week of
in-game measurements taken on a ghost package.

**The mechanism.** AddonBuilder receives `-temp=<dir>` and works there. It is common for the
project wrapper to clean it with `shutil.rmtree(temp, ignore_errors=True)`. That
flag swallows the failure: if anything locks the directory (explorer, an antivirus, an
open game), the old tree **survives**. AddonBuilder then regenerates only what
it produces itself —`config.bin` from your `config.cpp`, and `texHeaders.bin`—,
packs the `gui/`, `scripts/` and `data/` that were already there, and reports
**`Build Successful` with code 0**.

**The footprint that gives it away**, inside the `-temp` tree, is unmistakable:

| file | mtime |
|---|---|
| `config.bin`, `texHeaders.bin` | from one minute ago |
| `gui/`, `scripts/`, `data/` | from days or weeks ago |

In the measured case, the deployed package carried week-old sources while the source tree
was a week ahead: 14 different files, an entire missing `.layout`, ~8,500 B
less in a single view, and `config.cpp` not copied (replaced by regenerated
`config.bin`). Each "rebuild" moved the `.pbo` mtime and did not move its content.

**Two traps when checking it, both measured:**

- **Counting loose version mentions does not discriminate.** The old package gave 80
  occurrences of `"1.2.3"` and 1 of `"1.2.4"`, but those numbers mix comments,
  changelogs, and legacy migrations. What decides is the **exact literal** of the
  constant: `grep -c -a -F 'MYMOD_VERSION_STR = "1.2.4"'`. One against zero, without noise.
- **Larger is not more complete.** The correct package came out **8.4 MB smaller**
  than the ghost (99.6 MB against 108.0 MB), because the never-cleaned `-temp` tree
  had been accumulating debris from previous builds that got packed with everything else.
  A gate watching "that it does not shrink" would have blocked the good package.

**The check that does catch it** comes with mandatory positive control: choose a marker
that exists **only** in new sources and another that must exist in both. If the
second does not appear either, your grep is broken and the first result means nothing.

```bash
grep -c -a -F "<new marker>"      <path>/Addons/<Mod>.pbo   # must be >= 1
grep -c -a -F "<control marker>" <path>/Addons/<Mod>.pbo   # must be >= 1 always
```

**The fix in the wrapper** is four lines and is fail-closed: delete, **verify
that it was deleted**, and abort with own code if it survives. Never let an
`ignore_errors=True` decide for you what gets packed.

```python
shutil.rmtree(temp, ignore_errors=True)
if os.path.exists(temp):
    print("ABORT: temp dir survived removal: %s" % temp)
    raise SystemExit(4)
```

Verified with positive control: pointing `--temp` to a file (so `rmtree` fails and the
flag swallows it), guard aborts with `RC=4` without ever invoking AddonBuilder, and the
wrapper's `finally` block continues running — important if, as here, it puts configs
from other projects in quarantine while the build lasts.

### Cross-link: load order and thin lower layers

The `requiredAddons[]` dependency graph orders cross-mod compile within each script module layer (see `/dayz-mod-workflow`). Prefer not inventing 1_Core/2_GameLib content unless you truly need that surface; default shared data to 3_Game.

## Binarize is not byte-deterministic

Measured with AddonBuilder for DayZ 1.29 (staging outside `P:\`, `-temp` under `P:\`): two consecutive builds of the same assembled tree (a door and a room MLOD `.p3d`, byte-identical by sha256) produced different ODOL entries — door 339,554 vs 339,551 B, room 2,597,078 vs 2,598,395 B — while every script, config, rvmat, paa and csv entry hashed the same. Consequences for a release or A/B gate:

- **Per-entry PBO hashes are an identity gate for scripts, config, materials and textures only.** A changed `.p3d` entry between two builds proves nothing by itself.
- **A binarized model is accredited by the hash of its MLOD input plus the engine check** (render + raycast), never by ODOL bytes. Keep the MLOD hashes next to the PBO hash in the evidence.
- **Do not chase a byte diff in a `.p3d` entry** when the MLOD did not change; rebuild twice and compare before opening a debinarizer.
- When the doubt is already open (a test PBO whose ten `.p3d` all hash differently and whose body is ~33 KB smaller), close it by CONTENT: extract the ODOL from inside each PBO and compare what matters — baked animations, bones, face counts, dimensions — against the stage (measured identical there, `pbo_diff.py`: 127 entries equal, the 10 `.p3d` different). Size and hash differences between builds of the same stage are expected binarize noise, not evidence of a geometry change.

## A content gate string that the base build also contains cannot turn red

A gate that checks a required string is inside the packaged and deployed PBO is a good
gate: it catches a build that packaged an old version of the tree. It fails silently when
the chosen string **is not exclusive to the change**.

Measured case: to test a variant that enabled client
smoothing only with `ClientPresentMode == 1`, the gate required the string
`ClientPresentMode == 1` and passed. But the base build already contained that substring,
in a function that has nothing to do with the variant:

```c
// present since before the change
return m_Tuning.ClientPresentMode == 0 || m_Tuning.ClientPresentMode == 1;
```

Meaning that gate **would have passed just the same on the build without the variant**. It could not
turn red, and therefore proved nothing: throughout the entire run it seemed to verify that
the change had reached the PBO, and it only verified that the file was still there.

**How the string is chosen.** Make it unique to the change, not to the area of the change. A
new constant name (`REST_PROBE_ARM_MPS`) or a new log tag
(`[MYMOD-REST]`) are good: they do not exist before. An expression fragment on an
already-used field, no.

**And the check that closes it, taking one minute**: before trusting the gate,
**run it against the artifact WITHOUT the change and see that it FAILS**. A gate for which you have
only seen green is not calibrated; proving it can turn red is the half that
is almost never done. In the same run, two strings on new symbols did
discriminate and one on a pre-existing symbol did not, with the same command.
