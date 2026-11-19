# From code to Workshop on DayZ 1.30

How a change becomes a mod that loads on DayZ 1.30 or later, on Windows or Linux: which skill runs each step, the rules every mod task needs, where to look an API up, which pack to read for each kind of request, how to port a mod to 1.30, and where the Community Framework and Expansion notes live.

Builds before 1.30 are not covered; do not write `#ifdef` branches for them unless the user asks for a mod that must still load on an older server. `/dayz-init` sets a clone up and shows status, `/dayz-route` (then `dayz-router`) picks the specialist, and `skills/_shared/README.md` lists every knowledge file by topic.

A fact with a `P:\` citation was read in that vanilla file. A fact marked measured comes from booting test mods on a server and is not checked on `P:\`. Third-party facts name the mod they describe.

## The loop

| Step | What happens | Run or read |
|---|---|---|
| Scope | A feature that is more than a few lines gets a spec first: what success looks like and what the next step needs from it. The plan and task list come from `dayz-mod-architect`. | `/dayz-scope-mod` ("Scoping a feature") |
| Write | Read the pack for the domain (table below), follow `skills/dayz-scope-mod/references/implementation-protocol.md`, and look up every API before you use it. A new mod starts with `/dayz-new-mod`. | The pack, the implementation protocol |
| Build | Validate, pack, sign. | `/dayz-lint`, `/dayz-build-pbo`; detail in `skills/dayz-build-pbo/references/` |
| Boot | A PBO that builds is not a tested mod. Boot it on a local server, compare the script module counts with a vanilla boot, read `script_*.log`. | `/dayz-launch-test`, `/dayz-gate ingame`, `/dayz-logwatch`; this folder |
| Check in game | When the change is visible or driven by the player. | `/dayz-gate behavior`, `/dayz-gate visual`; what makes an in-game check valid in `in-game-check-validity.md` |
| Publish | Only when the user says so. | `/dayz-release-pack`, `/dayz-server-kit`; `skills/dayz-build-pbo/references/workshop-publish.md` on Windows, `skills/dayz-build-pbo/references/dayzmake-linux.md` on Linux |

## Rules for every task

- Look it up before you use it. Check every class, method, enum value and config token against the target build's sources before it goes into code (next section). Unchecked names are the most common reason a mod does not compile.
- The engine defines only the current version (`DAYZ_X_XX`, `P:\scripts\1_core\defines.c:12` to `:14`). Plain current code needs no version `#ifdef`, and never use `DIAG_DEVELOPER` or `BUILD_EXPERIMENTAL` to mean a version (`dayz-1-30-server-measured.md`, on the version define).
- Use forward slashes in every path, `CfgMods` `files[]` included (`dayz-1-30-server-measured.md`, on script module paths).
- Every PBO sits in `@Mod/addons/`. A PBO at the mod folder root is silently ignored (`skills/dayz-build-pbo/references/pre-build-checks.md`). In this repo builds deploy to `P:\Mods\@<ModName>\Addons\`.
- Load order follows `requiredAddons`, not the `-mod` list (`dayz-1-30-server-measured.md`, on load order). Never build a fix on a position in the `modded class` chain.
- A `modded class` lives in the script module of the class it modifies (`skills/_shared/enscript/patterns/modded_class.md`).
- A compile error can crash the server right after `Can't compile ... script module!` (`dayz-1-30-server-measured.md`, on compile failures). When a server dies at boot, read `script_*.log` first.
- `FindFile` works again from the first 1.30 patch. `CF.FindFileEx` and copied `FindFile` path helpers are leftovers to remove on that build or later (`dayz-1-30-server-measured.md`, on `FindFile`).
- Never write into Steam's folders for test servers or Workshop content. Test servers run from a tree of their own; in this repo that is `.server/<instance>/`. The two exceptions are on Linux: the client's own Proton prefix, and a symlink to the test mod in the client's install folder, which you create by hand and remove after the run (`linux-headless-client.md`, on mods on the client). This does not conflict with the Windows `P:\Mods` junction to `!Workshop` that Tier 2 requires.
- Uploading to the Workshop is the user's call. Prepare the commands; never run them unasked.
- On Linux, build and sign with dayzmake 1.0.0 or newer, never the original armake2 (`skills/_shared/linux-proton.md`, "dayzmake, the DayZ fork of armake2").

## Look it up before you use it

In this order:

1. The vanilla files on `P:\`. The Tier 2 search rule: Grep `P:\scripts\` for a known name, use the `dayz-rag` search for a question by meaning, then open the hit and cite `path:line`. `/dayz-ask` does the same for a one-off question. `P:\` holds whatever build was last unpacked onto it, so unpack it again after a game update and check which build it holds.
2. The packs: `skills/_shared/enscript/README.md` for Enforce Script, `skills/_shared/enscript/depth/` (its `global-functions.md`, `language-builtins.md`, `entity-inventory-api.md` and `dayz-1-30-enforce-script.md`), and each pack's own `dayz-1-30-*.md` files.
3. A local API index, for a machine with no `P:\` (Linux) or when you want inherited members in one answer: `extract-dayz-sources.sh`, `build-api-index.py` and `dayz-api.py` in `scripts/tools/dayz-linux/` (its `README.md` and `skills/_shared/linux-proton.md` say how). `dayz-api.py class CarScript --inherited`, `find`, `chain`, `sub`, `enum` and `src` answer from the index; `src X` names the declaring file, so read the body there and cite `path:line`. Build the index locally and never commit it.
4. Online, when neither is at hand: `https://diff.yadz.app/api/classes/<Name>.json` (latest build, one class as JSON) and the BohemiaInteractive/DayZ-Script-Diff repository for exact bodies. Remote mirrors can lag a release.

For Community Framework and Expansion classes, read their public script repositories at a pinned commit, read the mod under `P:\Mods\` when it is installed, or index an extracted Workshop copy with `build-api-index.py --mod <name>`. Our own checked notes are `skills/_shared/enscript/integrations/community_framework.md`, `dabs_framework.md` and `expansion_style.md` in the same folder.

## Which pack to read

Match the request and read that pack or skill first; read more than one when the request spans domains. To pick the agent that does the work, use `/dayz-route`.

| Request mentions | Read |
|---|---|
| Enforce Script, `modded class`, `config.cpp`, `CfgPatches`, `CfgMods`, `ScriptRPC`, sync variables, `CallLater`, inputs | `skills/_shared/enscript/README.md` and its `depth/` folder |
| How to implement, client and server split, "it doesn't work", error catalog | `skills/dayz-scope-mod/references/implementation-protocol.md`, `debug-protocol.md`, `error-catalog.md` |
| Spec, acceptance criteria, "ready to code?" | `/dayz-scope-mod` |
| `OnStoreSave`, `OnStoreLoad`, CF ModStorage, storage versions, `types.xml`, `events.xml`, Central Economy files | `skills/_shared/persistence/` |
| `serverDZ.cfg`, `cfggameplay.json`, mission files, starting a local server, the mod does not load | `/dayz-add-server`, `/dayz-launch-test`; `server-and-mission-config.md` |
| PBO, prefix, signing, keys, Workshop | `/dayz-build-pbo` and its `references/`, `/dayz-release-pack` |
| Environment check: `P:`, DayZ Tools, Workshop folder | `/dayz-preflight` |
| Mod setup errors before packing | `/dayz-lint` |
| UI, `.layout`, widgets, HUD, Dabs | `skills/_shared/ui/README.md`; `/dayz-layout-preview` for offline previews |
| Cars, trucks, boats, motorbikes, aircraft | `skills/_shared/vehicles/README.md` and `/dayz-p3d-audit` |
| Firearms; clothing and characters; doors and locks; base building | `skills/_shared/weapons/`; `skills/_shared/wearables/`; `skills/_shared/animation/building-doors.md`; `skills/_shared/persistence/base-building-structures.md` |
| AI (Expansion eAI), infected | `skills/_shared/ai/` |
| Physics, collisions, ragdoll; sound; particles | `skills/_shared/physics/README.md`; `skills/_shared/audio-fx/README.md`; `/dayz-particles` |
| Sandstorm, heat, oil pits; terrain holes, bunkers | `skills/_shared/world/README.md` |
| Models `.p3d`, LODs, memory points | `skills/_shared/models/`, `/dayz-p3d-audit`, `skills/dayz-model-tools/` |
| Textures `.paa`, `.rvmat`; animations | `skills/_shared/textures/` and `/dayz-pack-texture`; `skills/_shared/animation/README.md` and `skills/dayz-animation-pipeline/` |
| Reading a third-party mod | `/dayz-import-mod` |
| Checking in game: spawning, raycasts, captures, vehicle checks | `in-game-check-validity.md`, which links the rest |
| A mod that runs beside CF, COT or Expansion; a DayZ update | `/dayz-conflict-check`; `/dayz-upgrade-guard` |

## Porting or reviewing a mod for 1.30

1. Boot it unchanged on a server of the target build and read `script_*.log` for `(E)` and `(W)` lines. The first error matters; the rest are often a cascade.
2. Walk the 1.30 files of every pack the mod touches (each `dayz-1-30-*.md`) and `dayz-1-30-server-measured.md`. Quick greps over the mod's scripts: `ProcessVariables`, `OnCEUpdate`, `m_ElapsedSinceLastUpdate`, `CreateFrontLight`, `ToggleHeadlights`, `TakeEntityToCargo`, `TakeEntityAsAttachment`, `CombinationLock`, `GetSupportProvided`, `Is3rdPersonDisabled`, `CCTWaterSurface`, raw `ERPCs` integers, `files[]` with backslashes, `Workbench.` outside `#ifdef WORKBENCH`, `FindFileEx`, `GetMissionFolderPath`, `$storage:` before the first `OnUpdate`.
3. Report each finding with `file:line` and its replacement, then fix, rebuild and boot again until the log is clean and every script module the mod adds files to counts above the vanilla baseline.
4. Back up `storage_1` before a server's first boot on a new release; older servers cannot read it back. The storage version is `GAME_STORAGE_VERSION`, 144 on DayZ 1.30 (`P:\scripts\3_game\global\game.c:5`).

`/dayz-upgrade-guard` snapshots the vanilla classes before and after a DayZ update and lists the mod classes whose vanilla parents changed; run it alongside these steps.

## Community Framework and Expansion

Third-party mod behaviour, not vanilla. The CF version, the Expansion load order with its Workshop ids, the failure without Dabs Framework and the storage caveats are in `dayz-1-30-server-measured.md`, on Community Framework and Expansion (the one copy to keep current). CF storage: `skills/_shared/persistence/cf-modstorage.md` and `skills/_shared/persistence/versioning-and-migration.md`. Scripted AI brains: `skills/_shared/ai/design-ideas.md`. The Expansion market UI: `skills/_shared/ui/expansion-market-menu.md`. Clashes with CF, COT and Expansion: `/dayz-conflict-check`.

## Testing a mod or a server

- Windows: `/dayz-add-server` once, then `/dayz-launch-test`, `/dayz-gate` for the scripted checks and `/dayz-logwatch` while you play (`README.md` in this folder).
- Linux: the native `DayZServer` from a private tree, the retail client headless under Proton, and the self-reporting AutoTest mod (`linux-native-server.md` and `linux-headless-client.md`). DayZ Tools and DayZDiag under Proton: `skills/_shared/linux-proton.md`.
- Ports and instances: on Windows the test machine runs one DayZ instance at a time on the default port 2302; never kill another session's DayZ process without asking (`test-machine-sharing.md`). On the Linux native server every server takes its own tree and its own non-default ports; each used about 7.5 GB resident with the Expansion bundle, so check free memory first if two must overlap (`linux-native-server.md`).
- Either way: a vanilla boot as the baseline, and a deliberate syntax error as the probe when an override silently does nothing. An unchanged script module count in a module the mod adds files to means its scripts did not load.

## Building, signing, publishing

On Windows, `/dayz-build-pbo` (AddonBuilder), then `/dayz-release-pack` and `/dayz-server-kit` for the release texts and the server owner's files; DsUtils signing and the Publisher or SteamCMD upload are in `skills/dayz-build-pbo/references/workshop-publish.md`. On Linux, the `dayz-mod-pack.sh` helper in `scripts/tools/dayz-linux/` over dayzmake, and the `workshop` uploader (`skills/dayz-build-pbo/references/dayzmake-linux.md`). Keep the private key out of git and out of the upload folder, use one key per mod family, and sign after the final build.
