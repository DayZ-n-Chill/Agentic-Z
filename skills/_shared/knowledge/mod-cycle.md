# The mod cycle, once: what to install, which order, which skill

Tier 3 pack: a map of one pass through making a DayZ mod (understand, write, lint, pack, deploy, test, debug) and a route table from "I want X" to the skill or tool. It came in with the DayZ Modding Knowledge Pack import. It is an index, not a tutorial: the procedures live in the skills it names.

Skill names written plain (dayz-vehicles, enforce-script-reference) are the Knowledge Pack's; a name with a leading slash is an existing Agentic-Z skill. Where the import merged a Knowledge Pack skill into an existing Agentic-Z skill, use ours: `/dayz-preflight` for the environment check, `/dayz-lint` and `/dayz-gate` for the offline checks, `/dayz-build-pbo` for packing, `/dayz-launch-test` and `/dayz-stop-test` for the local server and client, `/dayz-logwatch` for the logs. Tool behaviour and exit codes below are the Knowledge Pack's own statements about its tools, not yet checked on `P:\`.

## What has to be on the machine

Nothing here ships DayZ, DayZ Tools, Blender or the game data.

| Need | Why |
|---|---|
| DayZ plus unpacked vanilla data on `P:\` | Ground truth for scripts, models and configs. Agents grep `P:\scripts\` (`1_core`, `3_game`, `4_world`) instead of inventing APIs. |
| DayZ Tools (AddonBuilder, Object Builder, Workbench, TexView / ImageToPAA) | AddonBuilder packs PBOs; the others inspect and convert assets. |
| `P:\` mounted | The work-drive convention. It does not remount itself after a reboot: mount it from DayZ Tools (Tools, Mount P drive) or with `/dayz-workdrive`. |
| `P:\Mods` as a junction to `<DayZ>\!Workshop` | Where a deployed PBO has to land for the engine to see it. |
| `DayZDiag_x64.exe` | Local file-patching launch. The retail exe is the wrong runtime for this loop. |
| Python 3 | The tools under `scripts/tools/`. Model work also needs the py3d fork in `scripts/tools/py3d`, not the unrelated PyPI package named `py3d`. |
| Optional: Blender (with `bpy`), Community Framework, Dabs Framework, VPP Admin Tools | Only when the skill or project in hand actually uses them. |
| Optional: DayZ-MCP | Lets an agent drive a running DayZDiag server and client. See `docs/dayz-mcp.md`. |

For model work, install the py3d fork and assert it is not the PyPI namesake:

```text
pip install -e scripts/tools/py3d
python -c "import py3d; assert py3d.IS_DAYZ_FORK; print(py3d.__version__)"
```

The fork version the Knowledge Pack pinned is 1.10.1 (distribution name `py3d-dayz`, import name `py3d`). Six of the model skills once shipped a py3d 1.4.0 wheel; that wheel is gone and the editable install replaces it.

Environment check: a missing `P:\` is a hard fail. Missing Tools, vanilla data, the workshop junction or DayZDiag are warnings in the Knowledge Pack's preflight, and the user decides whether to continue. `DAYZ_TOOLS_PATH` and `DAYZ_VANILLA_DATA_PATH` override the search when the layout is not the Steam default.

## The cycle

One pass, in this order. In-game time is expensive (minutes per boot), so exhaust offline work, batch every pending change into one test and have a plan B before asking for a rebuild.

### 1. Understand

- For anything non-trivial, write a spec first (dayz-feature-spec): success criteria, in-game Given/When/Then scenarios, and a Forward Contract listing every classname, `model.cfg` selection, `.p3d` proxy and stringtable key the next phase will use.
- Then load the domain skill from the route table below.
- There is no command for this step. The agent greps vanilla under `P:\scripts\` and cites `path:line`.

### 2. Write

- dayz-mod-workflow covers how: map client and server data before any feature, the anti-confabulation rules, the edge-case checklists.
- enforce-script-reference is the Enforce Script and `config.cpp` reference. Load it before writing script or config.
- If more than two APIs in a file are still assumed rather than looked up, stop and look them up.

### 3. Lint offline

The linter is `scripts/tools/dayz-script-validator`. It runs from the tree with no install:

```text
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
```

- Exit `0` PASS, `1` FAIL, `2` WARN. Exit 1 blocks packing. `--terse` prints the verdict on line one.
- If the addon has UI, also run `python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>`. It checks `FindAnyWidget` literals against the widgets a `.layout` declares and `#STR_` keys against the stringtable.
- `/dayz-build-pbo` (the Knowledge Pack's dayz-pbo-build was merged into it; see its `references/pre-build-checks.md`) walks seven further checks by hand: folder layout, `config.cpp`, `model.cfg`, textures, LODs, stringtable, scripts. They are a checklist, not a bundled command.
- Do not run `scripts/tools/dayz-script-validator/scripts/vanilla_control.py` as part of making a mod. It is a gate for people changing the linter, walks Bohemia's tree and takes two to four minutes on DayZ 1.30.

When the work is a model, a layout or an animation, reach for the matching tool before a build (`docs/knowledge-pack-tools.md`). The `python -m dayz_*` forms do not resolve until that tool is installed (`python -m pip install -e scripts/tools/<name>`) or its package is on `PYTHONPATH`. Two forms run straight from the tree:

```text
python skills/dayz-p3d-audit/scripts/audit_p3d.py --scan-dir P:\<Mod>
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check
```

`audit_p3d.py` imports `py3d`. A wheeled vehicle audited without `--scan-dir` (or `--config`) skips the FireGeometry wheel-slot check and can print clean while the wheels never simulate.

### 4. Pack

The canonical AddonBuilder line (AddonBuilder lives under DayZ Tools in `Bin\AddonBuilder\`):

```text
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons ^
    -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

- Pass `-clear`, or a stale `-temp` copy packs yesterday's `.c`.
- Never put sources under `P:\temp\*`. AddonBuilder wipes that folder.
- A scripts-only addon (no `.p3d`, no `.paa`): the default binarize can drop the `.c` files and still print `Build Successful`. Pack it with `-packonly`:

```text
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear -packonly
```

- A mixed addon (models plus scripts) still needs binarize; `-packonly` is the wrong mode there. Confirm the `.c` files actually landed in the PBO.

### 5. Deploy

There is no separate deploy step. AddonBuilder's destination is the deploy (`P:\Mods\@<ModName>\Addons`), and `P:\Mods` must be the workshop junction the environment check verified.

### 6. Test in game

- The Knowledge Pack's dayz-test-ingame does not ship a launcher to run from the repo root. It ships a PowerShell template (`dayz-test.ps1`) and three `.bat` wrappers that are copied into `<Mod>_dev\tools\` with `__MODNAME__` replaced. The template assumes a `P:\` work-drive layout and has to be re-pointed for any other.
- `-Mod` is required (the CfgPatches name, no dashes). `-Mode all` starts the server and then the client on DayZDiag. `-Build` drives AddonBuilder first. `-Preflight` only checks.
- Offline (single exe) mode is marked `[DESIGN]` in that skill: validate it in game before trusting it.
- File patching: script and config edits are the general case for hot reload; `.p3d`, `.paa` and `.rvmat` need a rebuild. On some installs the PBO wins even for scripts, and the skill documents a `srcprobe` test to tell which is loaded.
- Optional automatic driving (spawn, orbit, screenshot, raycast) is dayz-mcp-verify, which talks to DayZ-MCP. Its acceptance ladder for a drivable vehicle is spawn, render, get in, drive, wheel direction.

### 7. Debug

- Six layers, top down: config, entity, actions, client conditions, server, response. Do not debug layer N+1 until layer N is confirmed.
- Logs: `script.log` for script compile and runtime errors, `*.RPT` for engine and assets, both under the profiles folder the launcher created.
- The in-script instruments are prints, `Shape` (`P:\scripts\1_core\proto\endebug.c:153`), `DbgUI` (`P:\scripts\1_core\proto\dbgui.c:59`) and `DiagMenu` (`P:\scripts\1_core\proto\endebug.c:240`). There is no command that "runs the debugger".
- Two in-game cycles of the same kind with no measurable progress: stop. Bisect or change strategy. A third rebuild is not a plan.

## I want X, open Y

| I want | Open |
|---|---|
| Check the machine is ready | `/dayz-preflight` |
| Start mod work as a whole (write, review, port, build, boot, publish) | dayz-mod-dev |
| Spec a non-trivial feature first | dayz-feature-spec |
| Implement or debug (the how) | dayz-mod-workflow |
| Write Enforce Script or `config.cpp` | enforce-script-reference |
| A car, truck, quad or boat | dayz-vehicles |
| A motorbike (1.30 only) | dayz-motorbikes |
| A racing-game rip into a drivable car | rip-vehicle-import, then dayz-vehicles |
| A plane, seaplane or helicopter | dayz-aviation |
| A firearm (entity, `CfgWeapons`) | dayz-weapons |
| A zombie, survivor or human NPC | dayz-characters |
| Worn clothing | dayz-clothing |
| A fence, gate, tent or other buildable | dayz-basebuilding |
| Save and load, CF ModStorage, schema migration | dayz-persistence |
| HUD, `.layout`, widgets, Dabs MVC | dayz-ui-development; offline parse with `scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check` |
| A widget rectangle or click centre | A geometry parser plus `ui_rects.py`; not in this repo (`docs/knowledge-pack-tools.md`) |
| `.layout` text, color or image | `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>` |
| Rigid bodies, raycasts, "I walk through it" | dayz-physics-engine |
| `CfgSoundShaders`, sounds not playing on a dedicated server | dayz-sound-system |
| `.ptc` or a particle script | `/dayz-particles` |
| A door, hatch or lid | dayz-doors |
| Sandstorms, heat, oil pits, hazard areas | dayz-environment-hazards |
| Bunkers, tunnels, terrain holes | dayz-underground |
| Textures, `.paa`, `.rvmat`, PBR | dayz-texture-pipeline |
| Author a `.p3d` from Blender or py3d | dayz-model-pipeline plus `scripts/tools/py3d` |
| Collision, winding, silent `.p3d` killers | `/dayz-p3d-audit` |
| Model loads white, untextured or invisible | `scripts/tools/dayz-model-preflight` (install the tool first) |
| Preview an MLOD `.p3d` without launching DayZ | `scripts/tools/dayz-3d-viewer` (install the tool first) |
| Inspect or edit a model as Recipe JSON | dayz-p3d-inspector |
| Align a proxy by eye | dayz-proxy-align |
| Animation never plays, inspect an RTM | dayz-animation-pipeline plus `scripts/tools/dayz-animation-formats` |
| Realistic motion gates | dayz-realistic-animation-director |
| Animate in Blender | blender-animation |
| Retarget mocap | mixamo-retarget |
| Build or review geometry in Blender | blender-assembly, blender-visual-review |
| A legible UV atlas | uv-clean-atlas |
| Expansion eAI | dayz-ai-patterns |
| Learn from someone else's PBO | dayz-pbo-reverse-engineering |
| Pack, "is this addon ready" | `/dayz-build-pbo` plus the linter above |
| Launch DayZDiag with the mod | dayz-test-ingame |
| Test in game through MCP | dayz-mcp-verify plus `docs/dayz-mcp.md` |
| Audit persistence or data-loss risk | rigorous-data-audit |
| Find the root cause of a bug | systematic-debugging |
| Compare two binarized models | `scripts/tools/dayz-odol-strict` (the backend is external) |
| Vehicle proxy graph and fit | `scripts/tools/dayz-vehicle-proxy-contract` |
| An AI-generated mesh into DayZ | ai-3d-to-dayz, 3d-generation-harness |
| What is true of a skill on which build | `docs/compatibility-matrix.md` |
| Touch a linter rule | `python scripts/tools/dayz-script-validator/scripts/vanilla_control.py` |

## A worked first move

"Help me make this ripped car drivable in DayZ."

1. rip-vehicle-import if it is a racing-game rip (the import pipeline), otherwise dayz-vehicles (authoring).
2. enforce-script-reference for any Enforce Script or config work.
3. dayz-feature-spec first if it is non-trivial: lock the Forward Contract (classnames, `model.cfg` selections, wheel names) before coding.
4. Build, deploy and launch locally; verify in game.
5. dayz-mcp-verify, or by hand, to confirm spawn, get in, drive and correct wheel direction.

Throughout: verify every class and field against vanilla (`P:\scripts\`), respect the client/server split, and batch the in-game tests.

## What this map does not cover

A DayZ install guide, Workshop signing and production server operation are outside the imported material.
