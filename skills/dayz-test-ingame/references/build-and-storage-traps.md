# Build and storage traps that make a test run meaningless

Measured ways a build, deploy and test cycle goes green without testing the change: backups packed into the PBO, a locked PBO that is never replaced, a post-build check that only tests existence, `DSSignFile` signing the old PBO, and mission storage (`storage_1`) written by a different mod set, above all with or without Community Framework.

How the pieces map to this repo: the build step (`dayz-test.ps1 -Build`, `Invoke-Build`) is `/dayz-build-pbo`; launching server and client (`-Mode all`) is `/dayz-launch-test`; stopping is `/dayz-stop-test`; reading the logs is `/dayz-logwatch`; the pass or fail verdict is `/dayz-gate`. The mod source that the text calls `P:\<Mod>` is the junction to `workspace/<ModName>/`, and the profile folders it calls `<Mod>_dev\_server\profiles` and `<Mod>_dev\_client\profiles` are `.server/<instance>/Profiles` and `.server/!ClientDiagLogs` here.

Terms used below: "this box" and "this install" in dated findings mean the Windows test machine the measurement was taken on, not yours. `[EXACT]` marks a flag, path or behaviour that was verified in a real run; `[DESIGN]` marks something plausible that was not verified, so check it in game before relying on it.

These are measured results and tool behaviour (AddonBuilder, FileBank, DSSignFile, DSCheckSignatures, Community Framework). They are not yet checked on `P:\`.

## Backups (.bak_*) in scripts/ inflate the PBO and break grep-verify (added 2026-07-14)

`Invoke-Build -packonly` copies the mod tree as it is, so any `<file>.c.bak_*` left next to the `.c` (a backup made before editing) gets packed into the PBO. It does not break the game (Enforce compiles only `*.c`, ignores `.bak_*`), but it (a) inflates the PBO and (b) breaks PBO verification by grep-of-the-blob - an old anchor reads as present because it lives in a `.bak`, not the active `.c`. Measured 2026-07-14 on a helicopter mod: 827,593 bytes with 29 `.bak` inside vs 115,609 bytes after moving them out (7x bloat + stale code shipped).

Rule: in `Invoke-Build`, before packing, move/exclude `*.bak*` from `$src` (or warn if `Get-ChildItem $src -Recurse -Include *.bak*` is non-empty). When verifying a PBO by text, count occurrences (`Cnt`) instead of `Contains` - a `.bak` copy makes `Contains` lie. Never leave `.bak_` files in the mod's `scripts/`; keep them outside the mod source tree. Cross-ref `/dayz-build-pbo` (packaging).

## Clean storage before any measurement boot - persisted entities re-fire EEInit (added 2026-07-14)

Vehicles (and other persistent entities) saved in the mission's `storage_1` run their `EEInit` again on the next boot. Any logic armed there - a test `CallLater`, a JSON-driven spike/tuning mode, a countdown - fires again on every persisted instance at once. Real case (2026-07-11): two helicopters from the day before re-armed their W0 spike at boot and flew off on their own after 60 s (two phantom CSV pairs contaminating the corpus, so the data no longer came from the one run being measured; the user even saw them fly with no explanation).

Rule: before every boot meant for measurement (cells, spikes, telemetry), the mission storage must be clean - rename `storage_1` -> `storage_1.bak_<date>_<reason>` (reversible), not only after a dirty kill. The current SOP only covers the dirty kill / stream-damage case (see the symptom table in `troubleshooting.md`). The rename also purges test entities accumulated from earlier sessions. Cross-ref `dayz-mcp-verify` (`SKILL.md`, "The loop": step 2 takes the session lease, step 8 releases it and stops the run).

## Introducing CF on a mission with persistence written without CF crashes the server (added 2026-08-02)

If a project adds **Community Framework** (and with it Dabs/VPP) to a mission whose `storage_*` was
written in runs **without** CF, the server starts, loads the mission and **dies** when it reads the
persisted entities. Exact signature (measured 2026-08-02, server `crash_*.log`):

```
SCRIPT (E): Virtual Machine Exception
Reason: Failed to read modstorage for entity Type=Rangefinder, Position=<...>
Class: 'CF_ModStorageObject<ItemBase>'
  JM/CF/.../modstorage\cf_modstorageobject.c:142  Function OnStoreLoad_CF
  .../mpmissions/dayzOffline.chernarusplus/init.c:6  Function main
```

**What is most misleading**: the cited entity is **vanilla and random** (here a `Rangefinder`), so
the message points anywhere except the mod you just added. And the client does not fail: it
loads normally (`PlayerBase OnStoreLoad SUCCESS`) and closes cleanly after the server, which reinforces
the mistaken reading of a client problem.

**Cause**: DayZServer's `dayzOffline.*` missions are shared between projects. A project running
without CF persists entities without CF's `modstorage` data; the next one that does include CF
reads them and crashes.

**Remedy** (the convention already used in the mission folder itself, with 4 occurrences:
`storage_1_corrupt-modstorage-20260720 / 0728 / 0729 / 0802`): with the processes stopped, **rename**
`storage_1` → `storage_1_corrupt-modstorage-<YYYYMMDD>` and let the server regenerate it. It is a rename, not
a deletion, so it is reversible - but **starting again with CF on that storage crashes again**:
what is preserved is evidence, not a state you can return to with CF enabled.

**Tell the user before rotating**: the world and the character are reset.

Cross-ref "Clean storage before any measurement boot" above (the same action, renaming `storage_1`, for a different reason: persisted
entities that re-fire `EEInit`). Combined rule: **any change in the mod set that
changes who writes `modstorage` requires clean storage**, the same as a measurement boot.

### The trap works in both directions, and the rule is decided at launch (measured 2026-08-21)

The reverse direction also bites, and faster: a server **without** CF starting on a
`storage_1` written **with** CF enters a storm of Virtual Machine Exceptions - `!!! Scripted variables corrupted upon
"<entity>"` for each persisted entity (measured: **15,688 in about 3 min**, plain `-mod=@DayZ_MCP`
on a storage freshly saved by a server with CF) - and can die partway through writing,
leaving the storage worse: rewritten entities lose their CF modstorage, and the next
server that does include CF crashes with the signature above. So the crossings chain together:
a server without CF rewrites the storage, a server with CF then crashes on it, and the storage has to be rotated.

**Rule when launching on a shared mission**: either `-mod=` includes CF, or `storage_1` is rotated
before starting. There is no third stable option: the storage carries CF data as soon as a
server with CF saves once. To rotate, rename it with a reason
(`storage_1.bak-<YYYYMMDD>-<HHMM>-<reason>`, with the processes stopped; occurrences on 2026-08-21:
`-1605-modstorage-corrupt`, `-1610-cfless-storm`). The server's own RPT says which storage needs rotating,
on the line `[StorageDirs] :: Selected storage directory:`.

## `modstorage` warning has 12 failures: turn it into preflight, not a paragraph (added 2026-08-29)

The section "Introducing CF on a mission with persistence written without CF crashes the server"
(added 2026-08-02) is correct and **has failed again**. Counted on 2026-08-29 in
the shared mission folder `DayZServer\mpmissions\dayzOffline.chernarusplus`:

    12 storage_1*corrupt-modstorage* folders, from 2026-07-20 to 2026-08-29,
    from at least 5 different projects.

12 occurrences in 40 days. A note skipped 12 times is not fixed by reading it more
carefully the 13th time: the precondition can be checked by a script, and it is being checked by hand.

**Operational rule: persistence belongs to the mod set that wrote it.** Before launching
with a `-mod=` that differs from the previous run on the same mission, rotate. The rule is not "if
you suspect a problem": it applies **whenever the list changes**, and adding one mod already changes it.

    # with processes stopped
    $m = "<mission>"
    Rename-Item -LiteralPath "$m\storage_1" -NewName "storage_1_corrupt-modstorage-$(Get-Date -f yyyyMMdd)_<project>"

Rename, not deletion: it is reversible. But starting again with CF on that storage crashes again,
so what is preserved is evidence, not a state you can return to.

**Warning to give before rotating**: the world and character of that mission are reset.

And the process failure that let it slip this time, which is the one to recognize:
**the precondition was checked against the first plan, and then the plan changed.** The plan was a new,
private copy of the mission, so "clean mission, no storage" was true when the run was dispatched. Then
the tool rejected the absolute path (`dayz_test_run` validates the `mission` field against
`_MISSION_ALIASES` in dayz-mcp's `dayz_test_tool.py` and only accepts `chernarus|livonia|sakhal`),
which pushed the run onto the shared mission. The precondition had been ruled out under the old plan, and no one checked it again under the new one.

**A precondition you ruled out holds only for the plan you ruled it out under: if the plan changes,
check it again.** This applies to every caveat in this skill, not just this one.

## Test-cycle rules measured up to 2026-08-31

The following rules were measured up to 2026-08-31. Where one of them corrects an earlier
section, the rule here wins; the earlier section is kept as the record of how the measurement
changed.

### Mixed build: `-include` filters sync, does not define PBO

The historical statements about mixed mods in `windows-launch-cycle.md` ("THE CYCLE", the two paragraphs on mixed mods) need two boundaries. AddonBuilder uses a native route
for `config.cpp`, `.p3d`, and `.rvmat` discovered from faces, and another ordinary sync
route for `.c`, `.paa`, `.ogg`, `.layout`, and `.csv`. `-include` governs this second route; it is
not the final manifest. An `.rvmat` cited only from `config.cpp` can still be missing.

The published template of this skill does not pass a list today in
`Invoke-Build` of `templates/dayz-test.ps1`. So for a mixed mod, do not trust the plain `-Build`:
use a build that passes a suitable `-include` list for the ordinary files, then check the
entries actually in the PBO. Require at least equality of paths and counts for source `.c`, and check
separately materials cited by config. Do not add `*.rvmat` to a list and take it as proof.
Authoritative build semantics and full gate live in
`skills/dayz-build-pbo/SKILL.md`.

### Binarize before spending a boot

Every candidate `.p3d` needs a binarize PASS verdict before entering a PBO, even if
final packing uses `-packonly`: packonly preserves MLOD, but does not make engine accept a
model that binarize rejects. Group models in the change and pay this gate once before build;
post-build census remains mandatory and tests another boundary.

### Offline identity between source and deployed PBO

Before planning by `path:line` citations or spending an in-game cycle, test what bytes the
game will compile:

1. Extract deployed PBO to a scratch with an extractor that correctly expands `Cprs`
   entries; validate extractor first against a known baseline.
2. Compute SHA-256 of file inside PBO and of source file cited by plan.
3. Require equal hashes for every file the change depends on. A recent PBO modified time says
   nothing about the files inside it.

If hashes differ, plan is citing a tree different from runtime. Rebuild and repeat the
gate before diagnosing logic. This offline check is the cheap discriminant complementing
the `srcprobe` discriminator in `windows-launch-cycle.md`.

### Deploy guard protects destination, does not freeze entire box

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
scripts\4_World\MyMod_Probe.c    3579     <- and on disk: 3579
scripts\5_Mission\MyMod_Driver.c 4756     <- and on disk: 4756
```

It is the same rule as for the build itself (the verdict of a build is the PBO
file table, not the exit code; `skills/_shared/knowledge/environment-and-infra.md` records that AddonBuilder
exits 0 on some error paths), extended to signing: **the exit code of `DSSignFile` says
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

[EXACT] `DSCheckSignatures` does not check every byte of a PBO,
nor the PBO's own SHA-1 trailer against its content. Measured on a quad-bike mod release
(the default v3 signature of `DSSignFile`, 2026-10-26): one byte changed inside
a `_co.paa` texture entry, with the trailer left as it was, still answered
`Signature ... is OK`. Two controls did fail with `is wrong`: the previous build's PBO next
to the new `.bisign`, and the new PBO with one byte of a `.c` entry changed and the trailer
recomputed, which is what any repacker writes. Build the negative control the way a packer
would, or from another PBO; a raw byte flip proves nothing about the signature. Another build's
PBO only fails when the two builds differ in an entry the signature covers: a second mod's release candidate
(2026-11-05), which differed from its previous release only in one `.p3d` entry (its bytes and
timestamp) and the trailer, answered `is OK` with the previous release's PBO next to its new `.bisign`, while
its `.c`-byte control answered `is wrong`. For a change that only touches models or textures, the
`.c`-byte control is the one that can fail.

## The post-build gate of a generated `dayz-test.ps1`: existence, freshness, content (added 2026-08-31)

Complements the previous section, does not repeat it: there lies the rule ("the verdict of a
build is the PBO file table, not the exit code"); here is what a generated `dayz-test.ps1`
checks after AddonBuilder returns, and what each check can and cannot prove.

### What copies generated before 2026-08-31 check

Verified on 2026-08-31 on three independently generated copies, not on one. The sequence
after AddonBuilder returns:

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
| `$p.ExitCode -ne 0` | if AddonBuilder returned != 0 | nothing if it returns 0 **and still fails** - measured: `[ERROR]: Build failed` in its log with exit 0 |
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

The freshness gate costs two lines and closes the measured case. `Invoke-Build` in
`templates/dayz-test.ps1` carries it now (it also probes the deployed PBO for exclusive write
before building and reads AddonBuilder's log), so regenerate an older copy from the template
or add the gate by hand:

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
traverse it; that of things that can stay stale has no end. The template does not carry a
content gate; `/dayz-build-pbo` does (it compares the PBO's entry table with the staged source).

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

**Two more masks of the same trunk (measured 2026-09-08).** (1) The generated launcher FABRICATES its own destination: `Invoke-Build` creates `<WorkDrive>\Mods\@<Mod>\Addons` with `New-Item -Force` if missing. In copies generated before that date a build-only run reached `Invoke-Build` without passing through the preflight, so a missing `Mods` folder became a PLAIN folder that silently received the PBO - the script printed `[ok] deployed` and the engine never read it (reproduced literally: `exit=0; Mods created=True; junction=False`). The current template runs `Invoke-Preflight` before every build and creates the junction when `Mods` is missing, but when `Mods` exists as a plain folder it only warns and the build goes on. The destination check - exists AND is a reparse point - must run from the build path itself before copying. (2) Add the stdout text gate beside the byte gate: capture AddonBuilder stdout (`Start-Process -RedirectStandardOutput`) and require `Build Successful` while rejecting `[ERROR]: Build failed`. The pair discriminates: a false "Successful" with an untouched PBO dies on the mtime/hash gate; a touched-but-failed build dies on the text gate. A FIRST legit build has no previous PBO, so the byte comparison must be guarded (compare only when a previous PBO existed). The current template carries the byte gate and half of the text gate: `Invoke-Build` stops on `Build failed`, but when `Build Successful` is missing it only warns and falls back to the freshness check (`templates/dayz-test.ps1`, `Invoke-Build`). [EXACT] (measured)
