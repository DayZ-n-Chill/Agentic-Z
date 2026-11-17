---
name: dayz-pbo-reverse-engineering
description: "Studies a DayZ mod somebody else built: classifies its PBOs from their headers, extracts them with Mikero ExtractPbo, and sweeps the files for patterns with a path:line evidence ledger until no new pattern turns up. Use when the user wants to reverse engineer a PBO, extract patterns from a Workshop or third-party mod, understand a mod before forking or extending it, audit one for compatibility or quality, or catalog its 3D assets. Not for packing your own mod (/dayz-build-pbo) or auditing your own models (/dayz-p3d-audit)."
argument-hint: "<file.pbo | folder> [more ...] [--json] [--no-trailer]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-pbo-reverse-engineering

A workflow for pulling patterns out of another author's DayZ mod in a way that can be checked afterwards. It is the opposite direction of `/dayz-build-pbo`. On a large Workshop item (43 PBOs, an aircraft mod) the method gave 130 patterns over two passes and about 30 loop turns. The figures quoted from that run are measurements on a third-party mod, not checked on `P:\`.

Follow `skills/_shared/dayz-conventions.md`. `inventory.py` only reads the `.pbo` files it is given, so it does not run `/dayz-preflight`.

## When to use

- Extract patterns from another author's mod (Workshop PBOs).
- Understand a mod before forking or extending it.
- Audit a third-party mod for security, compatibility or quality.
- Catalog the 3D assets a Workshop item ships.
- Learn techniques from a prolific modder's catalog.

Not for:

- Building your own PBO: `/dayz-build-pbo`.
- Auditing your own model files: `/dayz-p3d-audit`.
- Implementation work: `/dayz-mod-dev` and the domain packs.
- An obfuscated PBO (GUID, `COM1` or BOM file names, encrypted strings). Recover it first with a JAPM recovery tool, plus a KGB deobfuscator for the `KGB_DF` marker. This repo ships neither. Without them, report that the PBO is obfuscated and stop; do not sweep obfuscated output.

Respect the mod author's terms: study and compatibility work is the purpose here, and repacking somebody else's content is the user's decision and responsibility.

## How to run the inventory

```cmd
python "<skill-dir>\inventory.py" <file.pbo | folder> [more ...] [--json] [--no-trailer]
```

| Argument | Required? | Notes |
|---|---|---|
| `<file.pbo \| folder>` | yes, one or more | A folder is searched for `.pbo` files at any depth. |
| `--json` | no | One JSON list with every field per PBO, for the state ledger. |
| `--no-trailer` | no | Skips the checksum trailer, which hashes the whole file; use it on very large PBOs. |

It reads each PBO's header with `dayz-build-pbo\pbo_entries.py` and never extracts or decompresses anything, so it is safe on a read-only Workshop folder. For each PBO it prints:

```
[OK]    ...\addons\TheirMod.pbo
       prefix: TheirMod   entries: 4   payload: 12,345 bytes
       kind:   deployable mod (config plus scripts, models or layouts)
       types:  .bin 1, .c 1, .p3d 1, .paa 1

1 PBO(s): 1 mod
```

| Kind | Rule | Meaning |
|---|---|---|
| deployable mod | A non-empty `config.bin` or `config.cpp`, plus at least one `.c`, `.p3d` or `.layout` | Worth the full sweep. |
| config-only | A non-empty config and none of those | Mounts but ships no code or model. A scripts mod packed without its `.c` files looks like this (the post-build gates reference of `/dayz-build-pbo`). |
| source asset distribution | No usable config, and archives or source art (`.rar`, `.zip`, `.7z`, `.fbx`, `.blend`, `.max`, `.obj`, `.psd`, `.spp`, `.tga`) | Nothing the game loads. Catalog it; do not sweep it as a mod. |
| data only | No config and no source art | Loaded only if another PBO refers to its files. |

Warnings: an empty config entry, compressed entries (prove the extractor decoded them, `references/pitfalls.md`), GUID-like or unsafe entry names (path traversal, a drive letter, a Windows device name, a control character: signs of obfuscation or of a PBO that should not be extracted over existing files), and a missing checksum trailer. Exit code 1 when a file is not a readable PBO or none was found, otherwise 0.

Outside an agent session, `scripts\dayz\pbo-inventory.bat` runs `inventory.py` with the same arguments.

## The workflow

### Step 0: setup

`ExtractPbo.exe` from the Mikero DePboTools does the extraction. Its default install folder is `Mikero\DePboTools\bin` under the 32-bit Program Files folder:

```powershell
$extract = Join-Path ${env:ProgramFiles(x86)} "Mikero\DePboTools\bin\ExtractPbo.exe"
Test-Path $extract
```

If it is missing, install it from https://mikero.bytex.digital/Downloads. Allow two to three times the PBO's size in free disk space if you keep the binaries.

### Step 1: inventory pass

Classify every PBO before any deep work, with `inventory.py` above (or `ExtractPbo -LB -P <pbo>`, which lists contents without extracting). The marker to look for: a PBO whose config is absent or zero bytes is a source distribution, with nothing to load as a mod; a PBO with a substantial config plus `.c` scripts and `.p3d` models is a deployable mod.

In one measured Workshop item, 42 of 43 PBOs turned out to be source-only distributions. The inventory pass saved weeks of misdirected work. Always do it first, and re-scope on the first day if it contradicts the assumption.

### Step 2: extraction

```powershell
& $extract -P "<pbo path>" "<workdir>\<category>\"
```

- `-P`: do not pause on completion. Mandatory for scripting. It also applies when printing the syntax: a bare `ExtractPbo.exe` waits for a key press and hangs the shell until killed; `ExtractPbo -P` prints the syntax and exits.
- Do not use `-W` (warnings are errors): it is too strict for unfinished or legacy PBOs.
- `-LB`: listing only.
- `-R`: do not convert binarised param files. Required when the listing shows `config.bin` and a packaged `config.cpp` in the same folder: without `-R` the converter writes a `.cpp` from the `.bin`, collides with the packaged one, and extraction aborts at the first collision (exit 11, "already exists. Will not overwrite it."). Measured with ExtractPbo 2.35 / DePbo DLL 10.13, 2026-09-26.
- Keep `<workdir>` short and shallow (a folder near a drive root): nested PBO folders under a long destination exceed MAX_PATH and abort with "cannot make folder" (exit 11).
- ExtractPbo creates `<destination>\<pbo basename>\` from the PBO prefix.
- ExtractPbo prints to stderr. Windows PowerShell 5.1 shows that as `NativeCommandError`, which is a wrapper artifact and not a failure. Do not redirect stderr with `2>&1`.
- Extract to a scratch folder, never beside a read-only Workshop source, and prove the payload was decoded before reading it (`references/pitfalls.md`).

The state ledger and the notes go under `output/<project>-extraction/` in this repo (`_state/` and `notes/`); the extracted files stay in `<workdir>`.

### Step 3: state ledger

Four files in `_state/`: `queue.md` (ordered work units), `seen.json` (what was read), `findings.jsonl` (one finding per line, evidence mandatory) and `skill_changes.md` (every change applied to a skill or pack). Formats: `references/state-ledger.md`.

### Step 4: dimensional sweep (pass 1)

Process one PBO's files in this order:

1. `config.cpp` at the root: entity declarations, mod metadata
2. `config.cpp` per sub-entity: per-class vehicle or item configs
3. `model.cfg`: skeleton, animations, sections
4. `Scripts/` `.c` files: Enforce Script logic
5. `.layout` files: UI widgets
6. `.rvmat` materials: sample 5 to 10 representatives
7. `.ptc` particles
8. Sounds: the config and a sample of `.ogg` names
9. `.p3d` models: string extraction on about three representatives
10. Shared sub-folders (for example an assets folder used by every entity)
11. Leftovers: graphics, `Inputs.xml`, anything else

For each file: read it, identify the patterns, classify each one's novelty by searching this repo's `skills/` folder (the skills and the packs under `skills/_shared/`) for existing coverage, pick where it belongs, and write one line to `findings.jsonl` with `path:line` evidence. Novelty and target rules: `references/state-ledger.md`.

### Step 5: per-entity deep dive (pass 2)

Process one entity per unit (one aircraft, vehicle or weapon). Look for what the dimensional sweep does not show: custom logic beyond parameter overrides, per-entity tuning, inheritance variations, unique features (combat code, special physics). In the measured aircraft mod a unit gave about 3 to 10 findings; aircraft with custom code gave 9 to 11, pure parameter overrides about 3. Once you see that most entities are clones of one or two templates, confirm the clones quickly and spend the time on the customised ones.

### Step 6: convergence and report

Strict rule: two consecutive passes with fewer than 2 novel findings means converged. In practice diminishing returns is the signal: pass 1 typically gives 50 to 100 novel findings, pass 2 gives 20 to 40, pass 3 fewer than 5. If pass 2 drops below half of pass 1 and most of its novel findings are minor cross-entity synthesis, stop and ask the user instead of burning turns on confirmations. Write `_state/CONVERGED.md` with the metrics and the final report (`references/state-ledger.md`).

## Rules that keep the result honest

- **Evidence is mandatory.** Every finding carries `<relative path>:<line range>`. Never write "function X does Y" without it, and never extrapolate behaviour: document what is literally in the code.
- **Their code is not a reference.** It may use undocumented engine calls, have bugs, or carry dead code. Document the pattern and note suspected problems separately. A fact taken from a mod names that mod; it is not a fact about vanilla until a file on `P:\` confirms it.
- **Do not claim `new` without searching `skills/` first**, and do not claim `confirm` unless the existing file documents the exact pattern.
- **Changing a skill or pack is a repo change.** Apply findings to this repo only when the user asked for that, re-read the target file first, follow the pack rules in `skills/_shared/README.md`, and log the change in `skill_changes.md`. Corrections to a rule go through `/dayz-record-correction`.

## References

Deep material lives in `<skill-dir>\references\`.

| Question | File |
|---|---|
| What goes in `queue.md`, `seen.json`, `findings.jsonl` and `skill_changes.md`? How do I classify novelty, decide between adding to a skill and creating one, run the loop, and write the final report? | `references/state-ledger.md` |
| What goes wrong (trusting file names, missing classes, inferring runtime behaviour, a "successful" extraction that left the payload compressed, a missing companion PBO), and how do I read a `.p3d` without py3d? | `references/pitfalls.md` |
| How do I unpack a PBO safely on Linux with dayzmake? | `references/linux.md` |

## Do not

- Don't extract into, or beside, a Workshop folder or anything under `P:\Mods\`; use a scratch folder.
- Don't sweep obfuscated output, and don't replace the extractor with hand-written decompression (`references/pitfalls.md`).
- Don't copy another author's files into `workspace\` or a pack. The output of this skill is findings with evidence.
