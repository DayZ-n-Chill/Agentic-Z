---
name: dayz-mod-dev
description: "Reading guide and rule set for DayZ mod development on 1.30 or later, for a mod as a whole: writing, reviewing or porting a mod in Enforce Script (vanilla, Community Framework, Expansion) and taking it through build, local server boot, in-game check and Workshop release, on Windows or Linux. Use for 'write, fix or review my mod', 'port this mod to 1.30', 'my mod builds but does not work', a mod that spans several domains, CF or Expansion dependencies and load order, or 'what is the workflow from code to Workshop'. It names the domain skill and pack to read for each kind of request (vehicles, weapons, UI, persistence, models, testing, packaging) and carries the rules every mod task needs; read it alongside them whenever the work has to end in a mod that loads."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# DayZ mod development: where to start

Follow `skills/_shared/dayz-conventions.md`. This skill is reference only; it runs no scripts, so there is no preflight gate.

It does not repeat the domain skills. It says which one to read, carries the rules every mod task needs, and lays out the loop that turns code into a mod that loads. Read it together with the domain skill, and with `dayz-mod-workflow` (how to implement and debug) once code is being written.

Three other entry points keep their own jobs; this skill does not replace them:

- `/dayz-init` sets a clone up and is the status hub that runs the `/dayz-*` scripts.
- `/dayz-route` (then `dayz-router`) picks the specialist agent for a request; the role table is in `docs/dayz-modding.md`.
- This skill is what an agent reads once it has the task: rules, reading list, loop.

Target: **DayZ 1.30 or later** (written against 1.30.164289). Builds before 1.30 are not covered; do not write `#ifdef` branches for them unless the user asks for a mod that must still load on an older server. On a newer build, check a fact against that build's sources before relying on it.

Marks used here: a fact with a `P:\` citation was read in that vanilla file. "Measured" facts come from booting test mods on a server and name the build they were measured on; they are not yet checked on `P:\` because a source file cannot show them. Third-party facts name the mod they describe.

## The loop

| Step | What happens | Run or read |
|---|---|---|
| 1. Scope | A non-trivial feature first gets a spec: success criteria and a forward contract. The plan and task list come from `dayz-mod-architect`. | `dayz-feature-spec` |
| 2. Write | Read the domain skill (router below) and `dayz-mod-workflow`; look up every API before using it (next section). A new mod starts with `/dayz-new-mod`. | domain skill, `dayz-mod-workflow` |
| 3. Build | Validate, pack, sign. | `/dayz-lint`, `/dayz-build-pbo`; depth in `skills/dayz-build-pbo/references/` |
| 4. Boot it | A PBO that builds is not a tested mod. Boot it on a local server, compare the script module counts with a vanilla boot, read `script_*.log`. | `/dayz-launch-test`, `/dayz-gate ingame`, `/dayz-logwatch`; depth in `dayz-test-ingame` |
| 5. Verify in game | When the change is visible or driven by the player. | `/dayz-gate behavior`, `/dayz-gate visual`; `dayz-test-ingame`, `dayz-mcp-verify` |
| 6. Publish | Only when the user says so. | `/dayz-release-pack`, `/dayz-server-kit`; `skills/dayz-build-pbo/references/workshop-publish.md` on Windows, `skills/dayz-build-pbo/references/dayzmake-linux.md` on Linux |

## Rules for every task

- **Look it up before you use it.** Every class, method, enum value and config token is checked against the target build's sources before it goes into code (next section). Unverified names are the most common cause of a mod that does not compile.
- **The engine defines only the current version.** Vanilla documents one define "filled in with the current Major and Minor version", `DAYZ_X_XX` (`P:\scripts\1_core\defines.c:12-14`). Measured on the Linux server build 1.30.164014: its module lines list `DAYZ_1_30` and not `DAYZ_1_29`. So plain current code needs no version `#ifdef`, and `#ifdef DAYZ_1_30` would drop the code on the next release. Never use `DIAG_DEVELOPER` or `BUILD_EXPERIMENTAL` to mean a version.
- **Forward slashes in every path**, including `CfgMods` `files[]`. Measured on the Linux server build 164014: with backslashes a 1.30 server compiles none of the mod's scripts and reports no error (not tested again on build 25963285 or on Windows). `/dayz-new-mod` already writes forward slashes; keep them as the safe habit.
- **Every PBO sits in `@Mod/addons/`.** A PBO at the mod folder root is silently ignored. In this repo builds deploy to `P:\Mods\@<ModName>\Addons\`.
- **Load order follows `requiredAddons`, not the `-mod` list** (the loading order measured on the Linux server build 1.30.164014; launching in dependency order is a careful recipe, not a guarantee). Never build a fix on a position in the `modded class` chain; hook an event that runs after the behaviour you counteract.
- **A `modded class` lives in the script module of the class it modifies.** `Transport` is declared in `3_Game` (`P:\scripts\3_game\vehicles\transport.c:68`), so `modded class Transport` in `4_World` fails with `Unknown type 'Transport'`.
- **A compile error can crash the server** right after `Can't compile ... script module!`. When a server dies at boot, read `script_*.log` before anything else.
- **`FindFile` works again from 1.30.164200.** Its declaration is unchanged: `FindFile`, `FindNextFile` and `CloseFindFile` are at `P:\scripts\1_core\proto\ensystem.c:520-522`. Measured on Linux build 25963285: `$profile:`, `$mission:`, `$saves:` and `$storage:` resolve again; the first stable 1.30 release was broken (`dayz-mod-workflow`, `references/dayz-1-30-server-measured.md`). `CF.FindFileEx` and copied `FindFile` path helpers are leftovers to remove on that build or later.
- **Never write into Steam's directories for test servers or Workshop folders.** Test servers run from a tree of their own; in this repo that is `.server/<instance>/`. The two exceptions are on Linux: the client's own Proton prefix, and a symlink to the test mod in the client's install folder, which you create by hand and must remove after the run. The headless client script runs the game in the client's own Proton prefix but does not create the mod symlink (`dayz-test-ingame`, `references/linux-headless-client.md`, section 2). This does not contradict the Windows `P:\Mods` junction to `!Workshop` that Tier 2 requires.
- **Uploading to the Workshop is the user's call.** Prepare the commands; never run them unprompted.
- **On Linux, build and sign with dayzmake 1.0.0 or newer**, never the original armake2: that is built for Arma, leaves `*.c` out of the signature and lacks the DayZ-only functions dayzmake adds (`skills/_shared/linux-proton.md`, section 1).

Details and evidence for the measured rules: `dayz-mod-workflow`, `references/dayz-1-30-server-measured.md`.

## Look it up before you use it

In this order:

1. **The vanilla files on `P:\`.** This is the Tier 2 search rule: Grep `P:\scripts\` for a known name, the `dayz-rag` search for a question by meaning, then open the hit and cite `path:line`. `/dayz-ask` does the same for a one-off question. `P:\` holds whatever build was last unpacked onto it, not necessarily the installed one, so unpack it again after a game update and check which build it holds before relying on it.
2. **The packs.** `skills/_shared/enscript/README.md` for Enforce Script, `enforce-script-reference` (its `references/verified-api-catalog.md` and `references/dayz-1-30-enforce-script.md`), and the domain skill's `references/dayz-1-30-*.md`.
3. **A local API index**, for a machine with no `P:\` (Linux) or when you need inherited members in one answer. Three helpers sit in the repo's `skills/_shared/scripts/` folder: `extract-dayz-sources.sh` (scripts plus derapified configs, about 90 s), `skills/_shared/scripts/build-api-index.py` and `skills/_shared/scripts/dayz-api.py`. From the repo root:

   ```sh
   S="skills/_shared/scripts"
   bash "$S/extract-dayz-sources.sh" "<DayZ install>" /var/tmp/dz-src
   python3 "$S/build-api-index.py" /var/tmp/dz-src/scripts ~/.cache/dayz-api   # or set DAYZ_API_DIR
   python3 "$S/dayz-api.py" class CarScript --inherited    # members, including every base class
   python3 "$S/dayz-api.py" find 'OnCEIterate'             # member lines matching a regex
   python3 "$S/dayz-api.py" chain PlayerBase               # base class chain
   python3 "$S/dayz-api.py" sub Weapon_Base                # subclasses; "enum X" and "src X" likewise
   ```

   `src X` names the declaring file; read the body there and cite `path:line`. Pass `--force` to `extract-dayz-sources.sh` only to replace a non-empty output folder that has no `pbo-map.tsv`; otherwise it refuses, so an unrelated folder is not overwritten. The index holds Bohemia's declarations, so build it locally and never commit it to a mod or to this repo.
4. **Online**, when neither is at hand: `https://diff.yadz.app/api/classes/<Name>.json` (latest build, one class as JSON) and the BohemiaInteractive/DayZ-Script-Diff repository for exact bodies. Remote mirrors can lag a release.

CF and Expansion classes: read their public script repositories on GitHub (Community Framework, DayZ Expansion Scripts) at a pinned commit, read the mod under `P:\Mods\` when it is installed, or index an extracted Workshop copy with `build-api-index.py --mod <name>`. Our own checked notes are `skills/_shared/enscript/integrations/community_framework.md`, `dabs_framework.md` and `expansion_style.md` in the same folder.

## Router

Match the request and read that skill first; read more than one when the request spans domains. This table picks reading material. To pick the agent that does the work, use `/dayz-route`.

| Request mentions | Read |
|---|---|
| Enforce Script, `modded class`, `config.cpp`, `CfgPatches`, `CfgMods`, `ScriptRPC`, sync variables, `CallLater`, inputs | `enforce-script-reference`, and the pack index `skills/_shared/enscript/README.md` |
| How to implement or debug, "it doesn't work", client and server split, error catalog | `dayz-mod-workflow` (and `systematic-debugging`) |
| Spec, acceptance criteria, "ready to code?" | `dayz-feature-spec` |
| `OnStoreSave`, `OnStoreLoad`, CF ModStorage, storage versions, `types.xml`, `events.xml`, Central Economy files | `dayz-persistence` (`references/central-economy-files.md`); audits: `rigorous-data-audit` |
| `serverDZ.cfg`, `cfggameplay.json`, mission files, starting a local server, the mod does not load | `/dayz-add-server`, `/dayz-launch-test`; `dayz-test-ingame` (`references/server-and-mission-config.md`) |
| PBO, prefix, signing, keys, Workshop | `/dayz-build-pbo` (and its `references/`), `/dayz-release-pack` |
| Environment check: `P:`, DayZ Tools, Workshop folder | `/dayz-preflight` |
| Mod setup errors before packing | `/dayz-lint` |
| UI, `.layout`, widgets, HUD, Dabs | `dayz-ui-development` |
| Cars, trucks, boats | `dayz-vehicles` |
| Motorbikes (read both) | `dayz-motorbikes` and `dayz-vehicles` |
| Aircraft | `dayz-aviation` |
| Firearms / clothing / doors and locks / base building | `dayz-weapons` / `dayz-clothing` / `dayz-doors` / `dayz-basebuilding` |
| Characters and infected / AI (Expansion eAI) | `dayz-characters` / `dayz-ai-patterns` |
| Physics, collisions, ragdoll / sound / particles | `dayz-physics-engine` / `dayz-sound-system` / `dayz-particles` |
| Sandstorm, heat, oil pits / terrain holes, bunkers | `dayz-environment-hazards` / `dayz-underground` |
| Models `.p3d`, LODs, memory points | `dayz-model-pipeline`, `dayz-p3d-audit`, `dayz-p3d-inspector` |
| Textures `.paa`, `.rvmat` / animations | `dayz-texture-pipeline` / `dayz-animation-pipeline` |
| Proxies on a host model / previewing `.p3d`, `.paa`, `.rvmat` / UV atlases | `dayz-proxy-align` / `dayz-3d-viewer` / `uv-clean-atlas` |
| Assets from AI generation or a ripped vehicle | `ai-3d-to-dayz` / `rip-vehicle-import` |
| Animation authoring in Blender, Mixamo retargeting, realistic motion | `blender-animation`, `mixamo-retarget`, `dayz-realistic-animation-director` |
| Blender geometry, render review | `blender-assembly`, `blender-visual-review` |
| Reading a third-party mod | `dayz-pbo-reverse-engineering` |
| Verifying in game through the dayz-mcp server | `dayz-mcp-verify` |
| A mod that runs beside CF, COT or Expansion; a DayZ update | `/dayz-conflict-check`; `/dayz-upgrade-guard` |

## Porting or reviewing a mod for 1.30 or later

1. Boot it unchanged on a server of the target build and read `script_*.log` for `(E)` and `(W)` lines. The first error matters; the rest are often a cascade.
2. Walk the 1.30 references of every domain the mod touches (each skill's `references/dayz-1-30-*.md`) and `references/dayz-1-30-server-measured.md` in `dayz-mod-workflow`. Quick greps over the mod's scripts: `ProcessVariables`, `OnCEUpdate`, `m_ElapsedSinceLastUpdate`, `CreateFrontLight`, `ToggleHeadlights`, `TakeEntityToCargo`, `TakeEntityAsAttachment`, `CombinationLock`, `GetSupportProvided`, `Is3rdPersonDisabled`, `CCTWaterSurface`, raw `ERPCs` integers, `files[]` with backslashes, `Workbench.` outside `#ifdef WORKBENCH`, `FindFileEx`, `GetMissionFolderPath`, `$storage:` before the first `OnUpdate`.
3. Report each finding with `file:line` and the replacement, then fix, rebuild and boot again until the log is clean and every script module the mod adds files to counts above the vanilla baseline.
4. Back up `storage_1` before a server's first boot on a new release; older servers cannot read it back. The storage version is `GAME_STORAGE_VERSION` (`P:\scripts\3_game\global\game.c:5`).

`/dayz-upgrade-guard` snapshots the vanilla classes before and after a DayZ update and lists the mod classes whose vanilla parents changed; run it alongside these steps.

## Community Framework and Expansion

Third-party mod behaviour, not vanilla.

- **CF.** Use the regular Workshop CF 1.5.9 or newer (Workshop id 1559212036), one dependency: `JM_CF_Scripts`. `#ifdef CF_MODULES` detects it without a hard dependency. Removing CF from a tree whose storage was written with CF is an observed breakage. Whether adding CF needs a wipe is a hypothesis that was not isolated: isolate first (rebuild with the same storage kept, or copy the storage aside) before rotating `storage_1`.
- **Expansion** needs CF, Dabs Framework and DayZ-Expansion-Licensed before the Bundle. The ids, the order and the failure without Dabs are in section 8 of `references/dayz-1-30-server-measured.md` in `dayz-mod-workflow` (the one copy to keep current).
- More: sections 8 and 9 of that file; CF storage in `dayz-persistence` (`references/cf-modstorage.md`) and `skills/_shared/persistence/versioning-and-migration.md`; Expansion AI in `dayz-ai-patterns`; the Expansion market UI in `dayz-ui-development`; collisions with CF, COT and Expansion in `/dayz-conflict-check`.

## Testing a mod or a server

- **Windows.** In this repo: `/dayz-add-server` once, then `/dayz-launch-test` (a DayZDiag server and client with the same mods), `/dayz-gate` for the scripted gates and `/dayz-logwatch` while you play. The managed cycle through the dayz-mcp server and its `dayz-test.ps1` template is in `dayz-test-ingame`.
- **Linux.** The native `DayZServer` from a private tree, the retail client headless under Proton, and the self-reporting AutoTest mod: `dayz-test-ingame`, `references/linux-native-server.md` and `references/linux-headless-client.md`. DayZ Tools and DayZDiag under Proton: `skills/_shared/linux-proton.md`.
- **Ports and instances.** On Windows the test machine runs one DayZ instance at a time on the default port 2302, which `/dayz-launch-test` and `/dayz-gate` use; never kill another session's DayZ process without asking (`dayz-test-ingame`, `references/windows-launch-cycle.md`). On the Linux native server every server takes its own tree and its own non-default game, query and RCon ports, and you run the trees one at a time: each used about 7.5 GB resident with the Expansion bundle, so check free memory first if two must overlap (`references/linux-native-server.md`).
- **Either way:** a vanilla boot as the baseline, and a deliberate syntax error as the probe when an override silently does nothing. Compare each script module the mod adds files to against the vanilla baseline count; an unchanged count in such a module means its scripts did not load.

## Building, signing, publishing

Windows: `/dayz-build-pbo` (AddonBuilder), `/dayz-release-pack` and `/dayz-server-kit` for the release texts and the server owner's files; DsUtils signing and the Publisher or SteamCMD upload are in `skills/dayz-build-pbo/references/workshop-publish.md`. Linux: the `dayz-mod-pack.sh` helper in `skills/_shared/scripts/` (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`) over dayzmake, and the `workshop` uploader (`skills/dayz-build-pbo/references/dayzmake-linux.md`). Keep the private key out of git and out of the upload folder; one key per mod family; sign after the final build.
