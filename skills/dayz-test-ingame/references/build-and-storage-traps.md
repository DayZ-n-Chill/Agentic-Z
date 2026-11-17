# Build and storage traps that make a test run meaningless

Measured ways a build, deploy and test cycle goes green without testing the change: backups packed into the PBO, a locked PBO that is never replaced, a post-build check that only tests existence, `DSSignFile` signing the old PBO, and mission storage (`storage_1`) written by a different mod set, above all with or without Community Framework.

How the pieces map to this repo: the build step (`dayz-test.ps1 -Build`, `Invoke-Build`) is `/dayz-build-pbo`; launching server and client (`-Mode all`) is `/dayz-launch-test`; stopping is `/dayz-stop-test`; reading the logs is `/dayz-logwatch`; the pass or fail verdict is `/dayz-gate`. The mod source that the text calls `P:\<Mod>` is the junction to `workspace/<ModName>/`, and the profile folders it calls `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it. Tags such as `SP-078`, `LL-196` and `CLAIM-...` are the finding numbers of the knowledge pack this material came from; they are kept so that cross-references between files stay searchable. `DAYZ_INFRA.md` is that pack's infrastructure note (in this repo `skills/_shared/knowledge/environment-and-infra.md`); a tag like `[EXACT - DAYZ_INFRA.md §Section]` names the section of it that records the fact.

These are measured results and tool behaviour (AddonBuilder, FileBank, DSSignFile, DSCheckSignatures, Community Framework). They are not yet checked on `P:\`.

## Backups (.bak_*) in scripts/ inflate the PBO and break grep-verify (SP-065, added 2026-07-14)

`Invoke-Build -packonly` copies the mod tree AS-IS, so any `<file>.c.bak_*` left next to the `.c` (the OneDrive rule: back up before editing) gets packed into the PBO. It does not break the game (Enforce compiles only `*.c`, ignores `.bak_*`), but it (a) inflates the PBO and (b) breaks PBO verification by grep-of-the-blob - an old anchor reads as PRESENT because it lives in a `.bak`, not the active `.c`. Measured (LFHeli 2026-07-14): 827,593 bytes with 29 `.bak` inside vs 115,609 bytes after moving them out (7x bloat + stale code shipped).

Rule: in `Invoke-Build`, before packing, move/exclude `*.bak*` from `$src` (or warn if `Get-ChildItem $src -Recurse -Include *.bak*` is non-empty). When verifying a PBO by text, COUNT occurrences (`Cnt`) instead of `Contains` - a `.bak` copy makes `Contains` lie. Cross-project convention: never leave `.bak_` in the mod's `scripts/`; put them in `<Mod>_dev\_backups\`. Cross-ref `/dayz-build-pbo` (packaging). Origin: LFHeli feel-pass 2026-07-14 (cycle-16).

## Clean storage before any measurement boot - persisted entities re-fire EEInit (SP-062, added 2026-07-14)

Vehicles (and other persistent entities) saved in the mission's `storage_1` RE-RUN their `EEInit` on the next boot. Any logic ARMED there - a test `CallLater`, a JSON-driven spike/tuning mode, a countdown - re-fires on every persisted instance at once. Real case (LFHeli 2026-07-11): two helis from the day before re-armed their W0 spike at boot and flew off on their own after 60 s (two phantom CSV pairs contaminating the corpus, violating one-run-active-at-a-time; the user even saw them fly with no explanation).

Rule: before a boot meant for MEASUREMENT (cells, spikes, telemetry), the mission storage must be clean ALWAYS - rename `storage_1` -> `storage_1.bak_<date>_<reason>` (reversible), not only after a dirty kill. The current SOP only covers the dirty kill / stream-damage case (see the symptom table in `troubleshooting.md`). The rename also purges test entities accumulated from earlier sessions. Cross-ref `dayz-mcp-verify` (one-run-active protocol). Origin: LFHeli feel cells 2026-07-11 (storage renamed storage_1.bak_20260711_feelcells).

## Introducing CF on a mission with persistence written WITHOUT CF = hard server crash (added 2026-08-02)

If a project adds **Community Framework** (and with it Dabs/VPP) to a mission whose `storage_*` was
written in runs **without** CF, the server starts, loads the mission and **dies** upon reading
persistence. Exact signature (MercedesAMGLF 2026-08-02, server `crash_*.log`):

```
SCRIPT (E): Virtual Machine Exception
Reason: Failed to read modstorage for entity Type=Rangefinder, Position=<...>
Class: 'CF_ModStorageObject<ItemBase>'
  JM/CF/.../modstorage\cf_modstorageobject.c:142  Function OnStoreLoad_CF
  .../mpmissions/dayzOffline.chernarusplus/init.c:6  Function main
```

**What is most misleading**: the cited entity is **vanilla and random** (here a `Rangefinder`), so
the message points anywhere except the mod you just added. And the client does NOT fail -
loads well (`PlayerBase OnStoreLoad SUCCESS`) and closes cleanly behind the server, reinforcing
the mistaken reading of "client issue".

**Cause**: DayZServer `dayzOffline.*` missions are SHARED between projects. A project running
without CF persists entities without CF's `modstorage` data; the next one that does include CF
reads them and crashes.

**Remedy** (convention already established in the mission folder itself, with 4 occurrences:
`storage_1_corrupt-modstorage-20260720 / 0728 / 0729 / 0802`): with processes stopped, **rename**
`storage_1` → `storage_1_corrupt-modstorage-<YYYYMMDD>` and let server regenerate. It is a rename, not
deletion, so it is reversible - but **starting again with CF on that storage crashes again**:
what is preserved is evidence, not a state you can return to with CF enabled.

**Consequence that must be told to user BEFOREHAND**: world and character are reset.

Cross-ref `SP-062` (same action - rename `storage_1` - for a different reason: persisted
entities that re-fire `EEInit`). Combined rule: **any change in mod set
altering who writes `modstorage` requires clean storage**, same as a measurement boot.

### The trap is BIDIRECTIONAL and the rule is decided at LAUNCH (measured 2026-08-21)

The reverse direction also bites, and faster: a server **without** CF starting on a
`storage_1` written **with** CF enters a VME storm - `!!! Scripted variables corrupted upon
"<entity>"` for EACH persisted entity (measured: **15,688 in ~3 min**, plain `-mod=@DayZ_MCP`
on a storage freshly saved by a server with CF) - and can die midway through writing
leaving the storage WORSE: rewritten entities lose their CF modstorage, and next
server that DOES include CF crashes with the signature above. Thus crossings chain together:
server-without-CF rewrites -> server-with-CF crashes -> rotation.

**Rule when launching on shared mission**: either `-mod=` includes CF, or `storage_1` is rotated
BEFORE starting. There is no third stable option - storage becomes "CF-flavored" as soon as a
server with CF saves once. Rotate = rename with reason
(`storage_1.bak-<YYYYMMDD>-<HHMM>-<reason>`, with processes stopped; occurrences 2026-08-21:
`-1605-modstorage-corrupt`, `-1610-cfless-storm`). Which storage needs rotation is told by server's
own RPT: line `[StorageDirs] :: Selected storage directory:`.

## `modstorage` warning has 12 failures: turn it into preflight, not a paragraph (added 2026-08-29)

The section "Introducing CF on a mission with persistence written WITHOUT CF = hard server
crash" (added 2026-08-02) is correct and **has failed again**. Counted today host-direct in
the shared mission folder `DayZServer\mpmissions\dayzOffline.chernarusplus`:

    12 storage_1*corrupt-modstorage* folders, from 2026-07-20 to 2026-08-29,
    from at least 5 different projects (subbrz, amglf, gunracks, nocf-gate, lfquad2).

12 occurrences in 40 days. A note skipped 12 times is not fixed by reading it more
carefully the 13th time: precondition is MECHANICAL and is being asked by hand.

**Operational rule: persistence belongs to the mod set that wrote it.** Before launching
with a `-mod=` different from previous run on that same mission, rotate. It is not "if
you suspect": it is **whenever list changes**, and adding ONE mod already changes it.

    # with processes stopped
    $m = "<mission>"
    Rename-Item -LiteralPath "$m\storage_1" -NewName "storage_1_corrupt-modstorage-$(Get-Date -f yyyyMMdd)_<project>"

Rename, not deletion: it is reversible. But starting again with CF on that storage crashes again,
so what is preserved is evidence, not a state you can return to.

**Warning to give BEFORE rotating**: world and character of that mission are reset.

And the process failure mode that let it slip this time, which is the one to recognize:
**precondition was verified against plan A, and plan changed.** I was going to use a new,
own copy of the mission, so "clean mission, no storage" was TRUE when dispatched. Then
the tool rejected the absolute path --`dayz_test_run` validates `mission` field against
`_MISSION_ALIASES` and only accepts `chernarus|livonia|sakhal`, see `dayz_mcp\dayz_test_tool.py:135`--
pushing me to SHARED mission. Discard traveled with old plan and no one re-evaluated it.

**A discard is surnamed with the plan that justified it: if path changes, preconditions you
cleared are unverified again.** Applies to any caveat in this skill, not just
this one.

## Measured test-cycle patches promoted on 2026-08-31

The following rules apply to state after 2026-08-29 harvest. When
they correct a historical section, this block's correction rules; previous section is preserved
as evidence of measured evolution.

### Mixed build: `-include` filters sync, does not define PBO (SP-083 / SP-168, corrected by SP-177)

The historical statements about mixed mods in `windows-launch-cycle.md` ("THE CYCLE", SP-083 and SP-168) need two boundaries. AddonBuilder uses a native route
for `config.cpp`, `.p3d`, and `.rvmat` discovered from faces, and another ordinary sync
route for `.c`, `.paa`, `.ogg`, `.layout`, and `.csv`. `-include` governs this second route; it is
not the final manifest. An `.rvmat` cited only from `config.cpp` can still be missing.

The published template of this skill does not pass a list today in
`Invoke-Build` of `templates/dayz-test.ps1`. Therefore, for a mixed mod do not accredit generic `-Build`:
use a build passing an adequate list for ordinary payload and validate actual PBO entries
afterward. Require at least equality of paths and counts for source `.c`, and check
separately materials cited by config. Do not add `*.rvmat` to a list and take it as proof.
Authoritative build semantics and full gate live in
`skills/dayz-build-pbo/SKILL.md` (finding SP-177).

### Binarize before spending a boot (SP-125)

Every candidate `.p3d` needs a binarize PASS verdict before entering a PBO, even if
final packing uses `-packonly`: packonly preserves MLOD, but does not make engine accept a
model that binarize rejects. Group models in the change and pay this gate once before build;
post-build census remains mandatory and tests another boundary.

### Offline identity between source and deployed PBO (SP-144)

Before planning by `path:line` citations or spending an in-game cycle, test what bytes the
game will compile:

1. Extract deployed PBO to a scratch with an extractor that correctly expands `Cprs`
   entries; validate extractor first against a known baseline.
2. Compute SHA-256 of file inside PBO and of source file cited by plan.
3. Demand equality for each file underpinning the change. A recent container mtime does not
   accredit its entries.

If hashes differ, plan is citing a tree different from runtime. Rebuild and repeat the
gate before diagnosing logic. This offline check is the cheap discriminant complementing
the `srcprobe` of SP-078.

### Deploy guard protects destination, does not freeze entire box (SP-150)

On a shared box, "zero DayZ processes" is too broad. Before replacing a PBO require
the two conditions protecting that destination:

1. No live process references target mod in its `CommandLine`/modline, measured with
   `Win32_Process`; executable name is not enough.
2. Target PBO allows exclusive opening with `FileShare.None`.

Record baseline hash just before copying and verify published hash after. If either
condition fails, do not deploy. If both pass, do not close processes from other lanes loading other
mods.

## Two traps of the build-deploy-test cycle that make a useless run green (added 2026-08-31)

Both measured on 2026-08-31 closing an engine gate. Neither gives an error; both let
you draw conclusions from a run that did not test what you think.

### 1. `DSSignFile` returns 0 after a failed build - and signs the OLD PBO

`dayz_test_run` (and any live client/server) leaves the PBO **locked**. Rebuilding with
AddonBuilder while the run is up gives `[ERROR]: Build failed`, and if the script chains
signing, `DSSignFile` exits with **`EXIT=0`** quite happily: it has signed the previous binary.

Chained in a `.ps1`, the result is a `SIGN=0` that seems to confirm deployment.

**Stop the run before rebuilding**, and verify the result by **the PBO table against
source size**, never by exit codes:

```
scripts\4_World\LFG10_Probe.c    3579     <- and on disk: 3579
scripts\5_Mission\LFG10_Driver.c 4756     <- and on disk: 4756
```

It is the same doctrine that is already in `DAYZ_INFRA.md` ("the verdict of a build is the PBO
file table, not the exit code"), extended to signing: **the exit code of `DSSignFile` says
nothing about whether the build got in.**

### 2. Persistence returns the subject as the previous run left it

An experiment measuring entity state (health, wetness, quantity, temperature) **cannot
rely on spawn loadout**. Measured: character returned with garment at `wetlevel=4
hplevel=2`, exactly where previous run had left it, so control for new run
started **already past the threshold it had to cross** - and would have given "control does not
fire" falsely.

The probe **normalizes the subject** before measuring anything (`SetWet(0)`, `SetHealthLevel(0)`, whatever
applies) and records it in log. And if there is a client part depending on that state, it binds to
**the condition, not a timer**: wait to observe subject already normalized, because
normalization itself is a state change that can clobber what you were about to measure.

### 3. A signature negative control that cannot fail (added 2026-10-26)

[EXACT][CLAIM-SIGN-NEGATIVE-CONTROL] `DSCheckSignatures` does not check every byte of a PBO,
nor the PBO's own SHA-1 trailer against its content. Measured on the LFQuad v1.0.1 release
(`Return0` key, the default v3 signature of `DSSignFile`, 2026-10-26): one byte changed inside
the `data\LFQuad_wheel_rear_co.paa` entry, with the trailer left as it was, still answered
`Signature ... is OK`. Two controls did fail with `is wrong`: the previous build's PBO next
to the new `.bisign`, and the new PBO with one byte of a `.c` entry changed and the trailer
recomputed, which is what any repacker writes. Build the negative control the way a packer
would, or from another PBO; a raw byte flip proves nothing about the signature. Another build's
PBO only fails when the two builds differ in an entry the signature covers: Arma2Quad v1.0.3-rc
(2026-11-05), which differed from v1.0.2 only in the `Arma2Quad_body.p3d` entry (its bytes and
timestamp) and the trailer, answered `is OK` with the v1.0.2 PBO next to its new `.bisign`, while
its `.c`-byte control answered `is wrong`. For a change that only touches models or textures, the
`.c`-byte control is the one that can fail.

## The post-build gate of generated `dayz-test.ps1` checks EXISTENCE, not freshness (added 2026-08-31)

Complements the previous section, does not repeat it: there lies the doctrine ("the verdict of a
build is the PBO file table, not the exit code"); here is **the instrument that
this very skill generates and that violates it**, with its exact line and the fix.

Origin: ticket `fb-20260830-011217-668f` from the pipeline inbox (`project: LFQuad2`,
2026-08-30 01:12), archived by another session. The phrasing "checks that PBO EXISTS,
not that it is the new one" is theirs.

### What the generated script does today

Verified on 2026-08-31 on **three independently generated copies**, not on one:

```
A6_MK47_dev\tools\dayz-test.ps1:422-429
ExpandedBuilding_dev\tools\dayz-test.ps1:403-408
LFGungame_dev\tools\dayz-test.ps1:353-354
```

The sequence, taken from `A6_MK47_dev\tools\dayz-test.ps1:422-429`:

```powershell
if ($p.ExitCode -ne 0) { Die "AddonBuilder failed (exit $($p.ExitCode)). ..." }
$pbo = Join-Path $target "$Mod.pbo"
if (-not (Test-Path $pbo)) { Die "Build reported success but $pbo is missing." }
# Sanity: ... -lt 4096 ...
Ok "deployed: $pbo ($((Get-Item $pbo).Length) b)"
```

Three checks, and **none of the three looks at whether the PBO is from THIS build**:

| Check | What it answers | What it does NOT answer |
|---|---|---|
| `$p.ExitCode -ne 0` | if AddonBuilder returned != 0 | nothing if it returns 0 **and still fails** - measured in the ticket: `[ERROR]: Build failed` in its log with exit 0 |
| `Test-Path $pbo` | if **a** PBO exists | if it is the new one. Previous one also exists |
| `Length -lt 4096` | if it came out ridiculously small | nothing: a full old PBO weighs megabytes and easily passes |

With game running target PBO is **locked**, AddonBuilder's final copy
fails, and wrapper prints `[ok] deployed` and exits with **exit 0** on previous binary.
It is the same lock from `DSSignFile` section, one step before: there old PBO is signed,
here it is declared deployed.

### The three levels, and why gate must be on the third

**Existence** ("there is a PBO") is satisfied by previous build. **Freshness** ("this PBO is
newer than build") is satisfied by a new empty PBO. Only **content** ("this PBO
contains these sources") answers the question asked by the one testing the mod.

The minimal fix, which costs two lines and closes the measured case:

```powershell
$before = if (Test-Path $pbo) { (Get-Item $pbo).LastWriteTimeUtc } else { [datetime]::MinValue }
# ... Start-Process AddonBuilder ...
if (-not (Test-Path $pbo)) { Die "Build reported success but $pbo is missing." }
if ((Get-Item $pbo).LastWriteTimeUtc -le $before) {
    Die "PBO did not change: AddonBuilder did not rewrite it (destination locked by a live run?). The deployed PBO is still the previous one."
}
```

The good fix is the content gate, and is written in **complementary form**: not a
list of what could have been left behind, but the positive statement **"every current source
is in deployed PBO with its size/sha"**. The source list is short and you
traverse it; that of things that can stay stale has no end.

That gate is not theoretical: on 2026-08-31 two gates of that form -one of byte-for-byte identity
against a snapshot, another of "each source present in PBO with its sha256"- detected in
another mod a PBO that had appeared in the tree and was not deployed. A `Test-Path` would
not have seen anything.

### When this bites

Whenever rebuilt with game running, which is just what the filepatching
cycle invites you to do. Before rebuilding, **stop the run** (see `DSSignFile` section). And if
you are going to chain build → sign → deploy in an unattended batch or in parallel lanes,
put the freshness gate before signing: signing the previous binary and deploying it produces
an artifact that seems correct in all steps and does not contain the change.

**Cheap sign that it happened to you**: AddonBuilder log says `[ERROR]: Build failed` and
your wrapper says `[ok] deployed` next. If those two lines coexist in the same
run, the PBO you are going to test is the old one.

**Two more masks of the same trunk (af59 round 2, measured 2026-09-08).** (1) The generated launcher FABRICATES its own destination: `Invoke-Build` creates `<WorkDrive>\Mods\@<Mod>\Addons` with `New-Item -Force` if missing, and `-BuildOnly` / `-Mode none` reach `Invoke-Build` without passing through the preflight, so a missing `Mods` folder becomes a PLAIN folder that silently receives the PBO - the script prints `[ok] deployed` and the engine never reads it (reproduced literally: `exit=0; Mods created=True; junction=False`; the two lines are in 6 of 6 mod trees and in the template). The destination check - exists AND is a reparse point - must run from the build path itself before copying, not only in the interactive preflight. (2) Add the stdout text gate beside the byte gate: capture AddonBuilder stdout (`Start-Process -RedirectStandardOutput`) and require `Build Successful` while rejecting `[ERROR]: Build failed`. The pair discriminates: a false "Successful" with an untouched PBO dies on the mtime/hash gate; a touched-but-failed build dies on the text gate. A FIRST legit build has no previous PBO, so the byte comparison must be guarded (compare only when a previous PBO existed). [EXACT] (measured, SP-380]
