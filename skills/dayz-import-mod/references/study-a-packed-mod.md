# Studying a packed mod

How to learn from a mod somebody else built and shipped only as PBOs: classify the PBOs, extract them, and sweep the files for patterns with `path:line` evidence until no new pattern turns up. It is the opposite direction of `/dayz-build-pbo`, and the path `/dayz-import-mod` points to when it refuses a Steam Workshop link because there is no source to import.

This is a working method, not a statement about vanilla data. A pattern found in a mod is a fact about that mod until a file on `P:\` confirms it; for example the vehicle base class it builds on is `class CarScript extends Car` at `P:\scripts\4_world\entities\vehicles\carscript.c:94`.

## When to use it

- Understand a mod before forking or extending it (the `dayz-mod-architect` lists this sweep as a main-session task before the first wave).
- Audit a third-party mod for compatibility, security or quality.
- Pull patterns out of a Workshop mod, or catalog the 3D assets it ships.

Not for:

- Building your own PBO: `/dayz-build-pbo`.
- Auditing your own models: `/dayz-p3d-audit`.
- An obfuscated PBO (GUID, `COM1` or BOM file names, encrypted strings, a `KGB_DF` marker). It needs a PBO recovery tool and a deobfuscator first, and this repo ships neither. Report that the PBO is obfuscated and stop; do not sweep obfuscated output.

Respect the author's terms: study and compatibility work is the purpose. Repacking somebody else's content is the user's decision and responsibility.

## The extractor

`ExtractPbo.exe` from Mikero's DePboTools does the extraction. Its default install folder is `Mikero\DePboTools\bin` under the 32-bit Program Files folder:

```powershell
$extract = Join-Path ${env:ProgramFiles(x86)} "Mikero\DePboTools\bin\ExtractPbo.exe"
Test-Path $extract
```

If it is missing, install it from https://mikero.bytex.digital/Downloads. Allow two to three times the PBO's size in free disk space if you keep the binaries. On Linux, see "On Linux" in `extraction-pitfalls.md`.

## Inventory first

Classify every PBO before any deep work, with `pbo_inventory.py` (`SKILL.md`, "Studying a packed mod") or `ExtractPbo -LB -P <pbo>`, which lists the contents without extracting. A PBO whose config is absent or zero bytes has nothing to load as a mod: it is a source distribution when it holds archives or source art, and data only when it holds neither. A PBO with a substantial config plus `.c` scripts and `.p3d` models is a deployable mod.

Do this first, and change the plan the same day if it contradicts what you expected: in one large Workshop item, 42 of 43 PBOs were source-only distributions.

## Extraction

```powershell
& $extract -P "<pbo path>" "<workdir>\<category>\"
```

- `-P`: do not pause on completion. Mandatory for scripting. It also applies when printing the syntax: a bare `ExtractPbo.exe` waits for a key press and hangs the shell until killed; `ExtractPbo -P` prints the syntax and exits.
- Do not use `-W` (warnings are errors): it is too strict for unfinished or legacy PBOs.
- `-LB`: listing only.
- `-R`: do not convert binarised param files. Required when the listing shows `config.bin` and a packaged `config.cpp` in the same folder: without `-R` the converter writes a `.cpp` from the `.bin`, collides with the packaged one, and extraction aborts at the first collision (exit 11, "already exists. Will not overwrite it."). Measured with ExtractPbo 2.35 and DePbo DLL 10.13.
- Keep `<workdir>` short and shallow (a folder near a drive root): nested PBO folders under a long destination exceed MAX_PATH and abort with "cannot make folder" (exit 11).
- ExtractPbo writes the files under `<destination>\<prefix path>\`, where the prefix path is the PBO's prefix, not its file name: `ai.pbo` has the prefix `DZ\AI`, so its files land in `<destination>\DZ\AI\`.
- ExtractPbo prints to stderr. Windows PowerShell 5.1 shows that as `NativeCommandError`, which is a wrapper artifact and not a failure. Do not redirect stderr with `2>&1`.
- Extract to a scratch folder, never beside a read-only Workshop source or under `P:\Mods\`, and prove the payload was decoded before reading it (`extraction-pitfalls.md`).

The ledger and the notes go under `output/<project>-extraction/` (`_state/` and `notes/`); the extracted files stay in `<workdir>`.

## The ledger

Four files in `_state/`: `queue.md` (ordered work units), `seen.json` (what was read), `findings.jsonl` (one finding per line, evidence mandatory) and `skill_changes.md` (every change applied to a skill or pack). Formats, novelty rules and the final report: `extraction-ledger.md`.

## First pass: file type by file type

Process one PBO's files in this order:

1. `config.cpp` at the root: entity declarations, mod metadata
2. `config.cpp` per sub-entity: per-class vehicle or item configs
3. `model.cfg`: skeleton, animations, sections
4. `Scripts/` `.c` files: Enforce Script logic
5. `.layout` files: UI widgets
6. `.rvmat` materials: sample 5 to 10 representatives
7. `.ptc` particles
8. Sounds: the config and a sample of `.ogg` names
9. `.p3d` models: py3d, or string extraction on about three representatives (`extraction-pitfalls.md`)
10. Shared sub-folders (for example an assets folder used by every entity)
11. Leftovers: graphics, `Inputs.xml`, anything else

For each file: read it, identify the patterns, classify each one's novelty by searching this repo's `skills/` folder (the skills and the packs under `skills/_shared/`), pick where it belongs, and write one line to `findings.jsonl` with `path:line` evidence.

## Second pass: entity by entity

One entity per unit (one vehicle, weapon or item). Look for what the dimensional sweep does not show: custom logic beyond parameter overrides, per-entity tuning, inheritance variations, unique features. A unit typically gives 3 findings for a pure parameter override and 9 to 11 for an entity with custom code. Once most entities turn out to be clones of one or two templates, confirm the clones quickly and spend the time on the customised ones.

## When to stop, and the report

Two consecutive passes with fewer than 2 novel findings means converged. In practice falling returns are the signal: the first pass typically gives 50 to 100 novel findings, the second 20 to 40, a third fewer than 5. If the second drops below half of the first and most of its novel findings are small links between entities, stop and ask the user instead of spending turns on confirmations. Write `_state/CONVERGED.md` with the metrics and the final report (`extraction-ledger.md`).

## Rules that keep the result honest

- **Evidence is mandatory.** Every finding carries `<relative path>:<line range>`. Never write "function X does Y" without it, and never extrapolate behaviour: document what is literally in the code.
- **Their code is not a reference.** It may use undocumented engine calls, have bugs or carry dead code. Document the pattern and note suspected problems separately. A fact taken from a mod names that mod; it is not a fact about vanilla until a file on `P:\` confirms it (Tier 2, "Cite, then verify").
- **Search `skills/` before you call a finding `new`**, and call it `confirm` only when the existing file documents the exact pattern.
- **Changing a skill or pack is a repo change.** Apply findings only when the user asked for that, re-read the target file first, follow the pack rules in `skills/_shared/README.md`, and log the change in `skill_changes.md`. Corrections to a rule go through `/dayz-record-correction`.
- **Never copy another author's files** into `workspace\` or a pack. The output is findings with evidence.
