# Offline tools

What each tool under `scripts/tools/` does, how to run it and what it refuses to do. Two tables at the end say which tool to reach for, by symptom and by task.

Thirteen Python tools live under `scripts/tools/`. They are offline and deterministic,
except the experimental
[`dayz-terrain-builder-runner`](#scriptstoolsdayz-terrain-builder-runner), which
drives a Terrain Builder it launched; none of them phone home, and none of
them guess. Most are stdlib-only;
[`dayz-vehicle-proxy-contract`](#scriptstoolsdayz-vehicle-proxy-contract) also
needs numpy, scipy, matplotlib and this repo's py3d, and
[`dayz-navmesh-compare`](#scriptstoolsdayz-navmesh-compare) needs numpy for its
terrain inputs only.

**Install before invoking.** The `python -m <tool>` forms below resolve only
once that tool is installed — `python -m pip install -e scripts/tools/<name>` from the
repository root. On a fresh clone they fail with `No module named`, which
reads like a broken tool and is a missing install. `dayz-script-validator`,
`dayz-vehicle-proxy-contract` and `dayz-layout-viewer` also ship a script path
and run from the tree without installing; each tool's section gives the
command. `dayz-ui-lab`, `skill-runtime-pin`, `dayz-pbo-diff`,
`dayz-navmesh-compare` and `dayz-terrain-builder-runner` have no package: they
are scripts only, run from the tree.

They exist because the DayZ asset pipeline fails *silently*: a `.p3d` written
with a stale selection loads white, a mistyped RTM signature produces an
animation that never plays, a `.layout` typo yields an empty screen with no
error. Each tool turns one of those silent failures into an early, actionable
one.

| Tool | What it does | Writes files? |
|---|---|---|
| [`py3d`](#scriptstoolspy3d) | Read and write MLOD `.p3d` models | **Yes** — with atomic write + verify |
| [`dayz-animation-formats`](#scriptstoolsdayz-animation-formats) | Read/write/inspect RTM and SEAnim v1 | Yes |
| [`dayz-model-preflight`](#scriptstoolsdayz-model-preflight) | Gate a `.p3d` against a contract before export | No — read-only |
| [`dayz-odol-strict`](#scriptstoolsdayz-odol-strict) | Inspect and diff binarized ODOL models | No — read-only |
| [`dayz-ui-lab`](#scriptstoolsdayz-ui-lab) | Parse, compose, render and diff `.layout` UIs offline; give the 1.30 widget IDs | Reports only |
| [`dayz-layout-viewer`](#scriptstoolsdayz-layout-viewer) | Preview a `.layout` as HTML at four viewports | **Yes** — one `.preview.html` |
| [`dayz-3d-viewer`](#scriptstoolsdayz-3d-viewer) | Convert MLOD `.p3d`, PAA and RVMAT to glTF + HTML | **Yes** — `.glb`, PNG, HTML |
| [`dayz-script-validator`](#scriptstoolsdayz-script-validator) | Lint Enforce, `config.cpp`, `.layout` and `.rvmat` before packing | Reports only |
| [`dayz-vehicle-proxy-contract`](#scriptstoolsdayz-vehicle-proxy-contract) | Audit vehicle proxy graph, fit, engine properties and PBO closure | Reports only; `repair` stages copies outside the addon |
| [`skill-runtime-pin`](#scriptstoolsskill-runtime-pin) | Capture one commit of a skills repository and expose one derived runtime adapter | **Yes** — new task-local root only |
| [`dayz-pbo-diff`](#scriptstoolsdayz-pbo-diff) | Compare the entries of two PBOs by SHA-256, and their header properties | Reports only — one new JSON |
| [`dayz-navmesh-compare`](#scriptstoolsdayz-navmesh-compare) | Compare two `.nm` navmeshes tile by tile, by structure, against terrain edits and routes | Reports only — one new JSON |
| [`dayz-terrain-builder-runner`](#scriptstoolsdayz-terrain-builder-runner) | EXPERIMENTAL, Windows only: drive a Terrain Builder it launched by Win32 messages | **Yes** — its state file and `menu.json`; Terrain Builder rewrites its own settings on exit |

---

## Two `.layout` parsers

There are two readers. Neither is a superset of the other. Pick by the
question you are asking, not by which file you already have open. Only the
format parser, `dayz-ui-lab`, is in this repo; the geometry parser,
`layout_ast.py`, is not.

Measured on 2026-08-19 over a working tree of 819 `.layout` files:

| | `layout_ast.py` (not in this repo) | `dayz-ui-lab` (in this repo) |
|---|---|---|
| Job | GEOMETRY | FORMAT |
| Keeps | 11 geometry and flag keys | all keys |
| Exceptions over 819 | 0 | 57 (45 are copies of ONE HUD layout, 12 are XML files) |
| Continuation `\` + newline | does not reconstruct it | one LF — matches what was measured in DayZDiag |
| Serves | rectangles, click centres, reachability | render, scenarios, and anything that reads text/color/image |

Choice rule, in one line: **if you need where a widget IS, the geometry parser; if you need what it SAYS, the format parser. Neither is a superset of the other.**

A third, older parser (`renderer/parse.py`) is **superseded** and is not in
this repo. On Windows paths it **silently stripped the backslash**
(`gui\layouts\foo.edds` → `guilayoutsfoo.edds`). Do not write a reader that
does the same.

Inline-format collapse into `position` was a measured defect of the format
parser: grouping by physical line in `Parser.parse_values` turned
`ImageWidgetClass Bg { position 0 0 size 1 1 stretch 1 ignorepointer 1 { } }`
into a single `position` attribute holding the whole list. It is fixed **for
the vocabulary the parser knows**: `parse_values`
consumes by measured key arity, and that input now yields four attributes. The
bound is the point. An attribute missing from `ATTRIBUTE_ARITY` still falls back
to line grouping, so two unknown keys written inline still collapse into one —
measured, `{ zzz_custom 0 0 yyy_other 1 1 }` yields one attribute, while
`{ position 0 0 zzz_custom 7 }` splits correctly because the known key's arity
ends its run. Adding an attribute to the table is what extends the fix. The
geometry parser splits by arity throughout.

A screen-rectangle predictor (`ui_rects.py`: `predict` / `lint` / `centers`)
sits on the geometry parser. It is **not in this repo**: this repo ships the
format lab, not a second, partial geometry model. Unmodelled anchors (`halign left_ref` /
`valign top_ref`, `hexactpos 1`) are refused, not guessed. The route table in
`skills/_shared/knowledge/mod-cycle.md` lists it as outside this repo.

---

## `scripts/tools/py3d`

A pure-Python reader/writer for the **MLOD `.p3d`** format, the editable
non-binarized model format. Most asset scripts in the skills import it.

It carries anti-corruption guards: the paths that would silently produce a
broken `.p3d` fail early with an actionable message.

- `lod.new_selection(name)` — get-or-create a selection that binds and registers.
- `lod.set_memory_point(name, xyz)` / `get_memory_points()` — idempotent upsert.
- `lod.faces_by_material()` / `faces_for_material(n)` — case-insensitive match.
- `p3d.save(path, verify=True, backup_dir=...)` — atomic write with reopen,
  re-parse and invariant check; on failure the original stays byte-intact.
- `p3d.validate()` → `list[Finding]` (stale selection, weight range, normals
  budget, …).
- A complete fail-closed proxy lifecycle: raw/engine frame conversion,
  `add_proxy`, strict enumeration, in-place align, index-safe remove.

```bash
pip install -e scripts/tools/py3d
```

The distribution is named **`py3d-dayz`**; the import name stays `py3d`. A
different, unrelated library is published on PyPI as `py3d`, so assert you got
this one:

```bash
python -c "import py3d; assert py3d.IS_DAYZ_FORK; print(py3d.__version__)"
```

Current version **1.10.1**. The pinned wheel is built from that source:
`py3d_dayz-1.10.1-py3-none-any.whl`, SHA-256
`c9f000a51e6aca83104a8f021ef5e3eefe8d7f0a5b053623544b49dbdd5d1785`
(`scripts/tools/py3d/rollout/wheel-manifest.json`; the wheel itself is not in this repo).
Known limitations are listed in `scripts/tools/py3d/KNOWN-ISSUES.md` — read it before
assuming a bug is yours.

## `scripts/tools/dayz-animation-formats`

Strict reader/writer for **SEAnim v1** and **DayZ RTM** (`RTM_MDAT` and
`RTM_0101`), plus deterministic JSON inspection.

```bash
python -m dayz_animation_formats inspect input.rtm --output anatomy.json
```

Unsupported signatures fail closed rather than being parsed on a guess. The
frozen fixtures are independently decoded by Arma3ObjectBuilder
during validation, so the reader is checked against a second implementation and
not only against itself.

**Out of scope, deliberately:** BMTR, and `.anm` conversion.

## `scripts/tools/dayz-model-preflight`

A read-only gate that answers "will this `.p3d` survive export?" *before* you
spend a build on finding out. Driven by a versioned JSON contract, it composes
`py3d.validate()` with the intended scale, the bone selections that must exist
and be non-empty, and determinant-aware face-lineage and winding checks.

```bash
python -m dayz_model_preflight check target.p3d \
  --contract preflight.json --json preflight-result.json
```

Requires this repo's py3d `>=1.6.0`. Missing or ambiguous one-to-one lineage is
reported `INVALID`: the tool never guesses a mapping and never repairs a model.

## `scripts/tools/dayz-script-validator`

The **offline gate**: a pre-PBO linter for Enforce Script, `config.cpp`,
`.layout` and `.rvmat`. It catches the family of mistakes that compile-check
clean in an editor and only surface when the script module compiles at boot —
where the symptom is a dead module, a frozen loading screen or a ghost class,
and the diagnosis costs a full in-game cycle.

```bash
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

Exit `0` PASS / `1` FAIL / `2` WARN, findings as JSON on stdout. Under a second
over a full addon, so it belongs in every pass rather than at the end.

`--terse` swaps the JSON report for a verdict on the **first line** and one line
per finding. The exit code is the machine channel; this is the one a human or an
agent actually reads, and it is what the editor hook surfaces.

```
PASS
WARN - 1 warning
  ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN  [WARN] scripts/4_World/Foo.c line 239: ...
```

Rules are one module per defect under `scripts/detectors/`, over a source
stripped of comments and string literals by `scripts/stripper.py` so a pattern
mentioned inside a literal never fires. Coverage today spans refcount misuse
(`delete`), preprocessor traps (empty `#ifdef`), method-scope locals, unchecked
`ctx.Read`, the `SetSynchDirty` contract, `RegisterRecipies` (the vanilla hook
really is spelled with the typo), config classes declared under the wrong
`CfgXxx`, missing `.layout` files and `$PBOPREFIX$` mismatches.

`ui_reconcile.py` is the companion cross-check: `FindAnyWidget`/`FindWidget`
literals against the widgets a `.layout` actually declares, and `#STR_` keys
against the stringtable. Both classes of bug compile fine and only appear when
the menu opens.

**Known coverage limit, stated up front.** Four detectors read curated tables in
`scripts/shared/vanilla_reference.py` that are deliberately small, because the
linter does not parse the vanilla script tree at runtime. That trades false
negatives for a guarantee of no false positives from that path. **A green run is
not proof of absence**, and it predicts that the module compiles and the asset
loads — never that the engine behaves. Behaviour is the online layer's job.

**Vanilla control — linter authors only, not a mod-cycle step.** Before
committing a change under `scripts/tools/dayz-script-validator/` (a new rule, a
touched detector, a touched parser), compare the linter's findings on
Bohemia's vanilla tree against the pinned baseline:

```bash
python scripts/tools/dayz-script-validator/scripts/vanilla_control.py
```

A full run on DayZ 1.30 takes two to four minutes
(`scripts/tools/dayz-script-validator/README.md`; not re-timed here). Without a
local vanilla tree the control SKIPs with exit 2. A green control only
proves the linter is silent on that tree; it does not prove the new rule
catches anything. Optional flags from `--help`: `--vanilla-root`,
`--baseline`, `--update`, `--json`.

## `scripts/tools/dayz-vehicle-proxy-contract`

The **offline vehicle-proxy gate**: it checks that every declared proxy on a
vehicle host is reachable, that the source OBJ still fits the assembled P3D
within the manifest thresholds, that required engine properties such as
`autocenter=0` are present, that animated selections do not steal a proxy
triangle unless the manifest names that exact host/LOD/selection triple, and
that the deployed PBO still hashes to the source bytes.

```bash
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py audit \
  --manifest <manifest.json> --out <outdir>
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py preview \
  --manifest <manifest.json> --out <outdir>
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py repair \
  --manifest <manifest.json> --staging <abs-staging-dir> \
  --operation set-autocenter-zero|yaw180|affine-fit
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py self-test
```

Exit `0` PASS / `1` FAIL / `2` self-test control miss / `3` self-test broken /
`4` input or internal error / `64` usage. `audit` publishes
`report.json`, `summary.txt` and `lod-overview.json` into a new `--out`
directory, or nothing at all on exit `4`. `preview` adds sampled point-cloud
PNGs. `repair` stages copies under a new absolute directory outside the addon
root; it does not rewrite the source tree and it does not pack a PBO.

The manifest is the only place paths live. Every stored path
(`addon_root`, `host_p3d`, `cfgconvert`, source scene, piece OBJ, deployed
PBO) must already be absolute. The tool has no default `C:\...` converter
or addon root.

Needs this repo's py3d, numpy, scipy and matplotlib. `CfgConvert` is an
external adapter named by the manifest, not a bundled binary.

**A green run is not proof the vehicle plays.** It predicts that the declared
proxy graph, the source-to-assembly fit, the required properties and the
deployed bytes match the contract. It does not predict look, animation, IK,
damage zones, get-in points or physics. Deferred host-axis warnings
(`P3D-AXIS-SELECTION-DEFERRED`) are explicit about that: steering and damper
motion remain an online gate. Behaviour is the online layer's job.

## `scripts/tools/dayz-odol-strict`

Fail-closed, read-only anatomy inspection and deterministic diff for **ODOL
v53–v55** — the binarized model format the engine actually ships.

```bash
python -m dayz_odol_strict inspect input.p3d \
  --backend-root <external-backend> --json anatomy.json
python -m dayz_odol_strict diff reference.json candidate.json
```

The adapter, the schemas, the backend manifest
(`scripts/tools/dayz-odol-strict/backend/manifest-v1.json`) and three binary
fixtures are in this repo. The ODOL parser backend itself is **not**: it stays
external, pinned by SHA-256 in that manifest, and is loaded only inside an
isolated subprocess.

**There is no ODOL writer and no partial-success mode**, and neither is planned.
Inspecting a binarized model is a diagnostic; producing one is the engine's job.

## `scripts/tools/dayz-ui-lab`

An offline lab for DayZ `.layout` UIs: parse a layout into a JSON IR, compose
scenarios from shells and subviews, emit a deterministic semantic render at a
given viewport, and diff two renders into actionable defects. This is the
**format** parser in [Two `.layout` parsers](#two-layout-parsers). Geometry
(rectangles, click centres) is a different reader, outside this repo.

```bash
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>
python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check
python scripts/tools/dayz-ui-lab/dayz_ui_lab/scenario.py --scenario s.json --viewport 1920x1080
python scripts/tools/dayz-ui-lab/dayz_ui_lab/render.py --scenario s.json --viewport 1920x1080 --out render.json
python scripts/tools/dayz-ui-lab/dayz_ui_lab/diff.py --observed render.json --expected ref.json --report diff.json
python scripts/tools/dayz-ui-lab/dayz_ui_lab/corpus.py --root .
python scripts/tools/dayz-ui-lab/dayz_ui_lab/widget_ids.py derive <layout> [--json]
python scripts/tools/dayz-ui-lab/dayz_ui_lab/widget_ids.py scan <dir> [--json]
python scripts/tools/dayz-ui-lab/dayz_ui_lab/widget_ids.py collide <layout> [--json]
```

`diff.py` reports broken references, clipping, overlap and missing states per
widget and scenario. `corpus.py` is the regression gate: it parses the corpora
pinned in `scripts/tools/dayz-ui-lab/corpora/manifest.json` (VPP Admin Tools,
DayZ Expansion, TraderPlus, TraderX and a negative set), compares every tracked
`.layout` against them by content so that none of their layouts is kept in the
repo, and reports a tracked `.layout` outside the tool's own fixture folders.
The corpora are not in this repo: point
`scripts/dev/knowledge-pack/sources/local-roots.json` (untracked; copy
`local-roots.example.json`) at your own copies. A corpus with no configured
root is reported `CORPUS-ROOT-MISSING` and fails the run, so "not measured"
cannot look like "passes". Measured on 2026-07-28 with all five configured:
**376/376 layouts, zero diagnostics**.

`widget_ids.py` gives the IDs by which a DayZ 1.30 layout variant addresses
vanilla widgets (`Class "{id}" { Prefab "{id}" }`; how they are derived:
`skills/dayz-ui-development/references/layout-variants-130.md`). `derive` lists
each widget with the ID its layout stores, the ID derived from its name and its
ancestors' names, and whether the two match; where a layout stores an ID, that
is the one that counts. `scan` counts the stored and the matching IDs of every
`.layout` under a folder, and `collide` lists the IDs that two widgets of one
layout share, such as the two `top` siblings of
`xbox/day_z_ingamemenu_xbox.layout`. Stdlib only; it reads through `parse.py`.
Exit 2 on a file it cannot read or parse; `scan` exits 1 when a file fails to
parse, and `collide` when an ID is shared. On the 1.30.164200 and 1.30.164289
vanilla layouts `scan` counts 1,438 stored IDs, 1,395 of them derived.

**The offline render is not the engine.** It is a semantic model good enough to
catch structural mistakes before a build; DayZDiag remains the golden reference
for anything that depends on real rasterization, fonts or the live widget tree.

## `scripts/tools/dayz-layout-viewer`

Emits one self-contained `*.preview.html` for a `.layout`, with the same tree
drawn at **four viewports** (1080p, 1440p, ultrawide 21:9, 720p) plus the
parser's diagnostics. In it exact widgets keep their declared pixels at every
viewport while proportional ones scale. The engine draws exact units as 1/1080
of the screen height (`dayz-ui-development` Rule 3, measured in game), so off
1080p that difference is the viewer's model, not the game's: trust its other
viewports only for widgets with no exact ancestor. *(Corrected 2026-10-03: this called
the difference the "looked right in the mockup, wrong in game" failure made
visible without a build.)*

```bash
python scripts/tools/dayz-layout-viewer/build_viewer.py <layout> [-o out.html]
```

It reads through `dayz-ui-lab`'s format parser, so it inherits that contract —
including the continuation and fail-closed escape behaviour — rather than
carrying a second lexer. It is **not** `dayz-ui-lab/dayz_ui_lab/render.py`, which emits
semantic scenario JSON and no HTML.

**A structural approximation, not the rasterizer.** Its README enumerates what
it does not do, and the list is the useful part: no font atlas, no `.paa` /
`.edds` decode, no script-side `SetColor` / `SetText`, no spacer re-flow (the
authored `position`/`size` are drawn, and the engine overwrites those), no
`.styles`, and no claim about the `right_ref` / `bottom_ref` offset sign, which
is still unverified. Trust it for structure and anchoring; for pixels, colour
and fonts, DayZDiag.

## `scripts/tools/dayz-3d-viewer`

Convert an MLOD `.p3d` plus optional `.paa` / `.rvmat` into a `.glb` and a
standalone Three.js HTML viewer. Two HTML modes: `embedded` (typed arrays
and base64 textures, no `fetch`) and `web` (external `.glb` via
`GLTFLoader`).

```bash
python -m dayz_3d_viewer p3d-to-glb model.p3d model.glb
python -m dayz_3d_viewer paa-to-png base_co.paa base_co.png
python -m dayz_3d_viewer parse-rvmat housing.rvmat
python -m dayz_3d_viewer build-viewer model.p3d --textures ./tex --mode embedded
```

Requires this repo's py3d `>=1.6.0`. Pillow and LZO are optional extras
(`[paa]`, `[lzo]`); a missing extra exits 2 with a one-line message.
Generated HTML loads **three.js 0.185.1 from jsDelivr** — it is not
bundled, so a render needs a network. Known converter gaps (SWIZ, proxy
triangles, ViewPilot at resolution 1100) are listed in
`scripts/tools/dayz-3d-viewer/KNOWN-ISSUES.md` and are not repaired here.

## `scripts/tools/skill-runtime-pin`

Capture **every blob** of one clean commit of a skills repository into a new
task-local root and add one derived discovery adapter. It is not a host launcher and it does not
prove the rest of a global catalog is off.

```powershell
python scripts/tools/skill-runtime-pin/runtime_pin.py materialize --source <skills-repo> --commit <sha> --task-root <new-task-root>
python scripts/tools/skill-runtime-pin/runtime_pin.py verify --task-root <task-root>
python scripts/tools/skill-runtime-pin/runtime_pin.py assemble --task-root <task-root> --consumer cursor
python scripts/tools/skill-runtime-pin/runtime_pin.py inspect-prompt --task-root <task-root> --prompt-input <dump.txt>
python scripts/tools/skill-runtime-pin/runtime_pin.py grade --task-root <task-root> --transcript <transcript.json>
```

The capture stays byte-identical to the git objects. The adapter is
**DERIVED** (`<skill>-<short-commit>`), points at the captured original
`SKILL.md`, and holds a canary whose nonce is never placed in the assembled
prompt. Codex `--ignore-user-config` is not HOME isolation; Cursor has no
exclusive catalog. Consumer argv is `[DESIGN]` until someone runs the real
Cursor/Codex probes. A nonce without a read or injection of the original is a
failed grade, not a pin.

## `scripts/tools/dayz-pbo-diff`

Compare the entries of two uncompressed PBOs by the SHA-256 of each entry's
payload, and their header properties: did the new package change only what
you meant to change?

```bash
python scripts/tools/dayz-pbo-diff/pbo_diff.py --old <old.pbo> --new <new.pbo> --out <diff.json>
python scripts/tools/dayz-pbo-diff/pbo_diff.py --old <old.pbo> --new <new.pbo> --out <diff.json> --ignore-prefix data/layers/
```

Stdlib only. Both PBOs are read through the fail-closed reader of
`dayz-vehicle-proxy-contract` (`digest_pbo`): a compressed entry, an unsafe,
duplicate or non-ASCII name and a truncated archive are refused (exit 1), never
skipped. `differing` lists every entry whose bytes differ or that is on one
side only; `--ignore-prefix` filters a view (`differing_not_ignored`), not the
comparison. `--out` must not exist. Between two AddonBuilder runs a different
`.p3d` entry proves nothing by itself (`skills/dayz-build-pbo/references/post-build-gates.md`).

## `scripts/tools/dayz-navmesh-compare`

Compare two `.nm` navmeshes tile by tile by structure (polygon and vertex
counts, vertical bounds) instead of bytes. NavMeshGenerator rewrites almost
every tile's bytes between runs: in the measurement its README cites, 966 286
of 966 289 tiles changed bytes and 138 changed structure, so a hash says that
everything changed.

```bash
python scripts/tools/dayz-navmesh-compare/compare_navmesh.py --old-nm <accepted.nm> --new-nm <new.nm> --out <report.json>
python scripts/tools/dayz-navmesh-compare/compare_navmesh.py --old-nm <accepted.nm> --new-nm <new.nm> --out <report.json> --old-terrain <old.npz> --new-terrain <new.npz> --cell-m 6 --routes <routes.txt>
```

Exit `0` for `PASS_NO_STRUCTURE_DELTA` and `PASS_LOCAL_STRUCTURE_DELTA`, `1`
for `REVIEW` (with `review_reasons`), `2` usage, `3` refused. The reader is
fail-closed: magic and version of the file and of every tile, the offset
table, one tile per cell, bounds against the cell. Stdlib only without terrain
inputs, numpy with them. Verified envelope: one 12 288 m world in 12.5, 25 or
50 m tiles, TESM 6 and DNAV 11; any other layout is read and reported as
outside it. Unchanged structure along a route is not a locomotion result.

## `scripts/tools/dayz-terrain-builder-runner`

**Experimental.** Drive a Terrain Builder this runner launched by Win32
messages only (`PostMessage(WM_COMMAND)`, `WM_SETTEXT`), without taking the
focus or moving the mouse. Windows only; it imports anywhere and every
command refuses off Windows.

```powershell
$env:TBRUNNER_TB_EXE = "<DayZ Tools>\Bin\TerrainBuilder\terrainBuilder.exe"
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py launch
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py menu
python scripts/tools/dayz-terrain-builder-runner/tbrunner.py command <menu id>
```

Verified on 2026-10-03 for menu commands and the standard file dialogs;
**not** for Generate Layers, a real import or a WRP export. Use a disposable
instance (`probe` posts every enabled entry under a prefix), back up
`TerrainBuilder.opt`, `GUILayout.opt` and `Proj.vdat` (rewritten on exit), and
press Terrain Builder's own dialog buttons by label: their ids are swapped (Ok
2, Cancel 1). Its README holds the gotchas.

---

## Two helpers that are not tools of their own

- `scripts/tools/sync_generated.py` regenerates and checks the sealed copy of
  `skills/_shared/viewer_core.py` that `dayz-3d-viewer` ships inside its
  package (`scripts/tools/dayz-3d-viewer/dayz_3d_viewer/viewer_core.py`). Edit
  the source, never the copy, then run
  `python scripts/tools/sync_generated.py sync --root .`; `check --root .`
  exits 1 when the copy has drifted. The seal is a SHA-256 over the raw bytes
  of the source, which is why `.gitattributes` keeps that file LF.
- `scripts/tools/viewer-gate/render_check.mjs` is a Node smoke test for a
  generated Three.js viewer page:
  `node scripts/tools/viewer-gate/render_check.mjs <html|url> [--png out.png] [--expected-three 0.185.1]`.
  It needs puppeteer (`PUPPETEER_MODULE`) and a Chrome or Chromium
  (`PUPPETEER_EXECUTABLE_PATH`). A green run means the page loaded, drew and
  reported the three.js revision it imported with no errors; it does not mean
  the picture or the exported coordinates are right.

---

## What is deliberately absent

The DayZ 3D pipeline still needs more than this — Blender→`.p3d` assembly,
PNG→PAA encoding, PBO packing. Those are done with Blender and DayZ Tools,
which are not in this repo; `skills/_shared/knowledge/mod-cycle.md` lists what
to install. PAA *decoding* is in `scripts/tools/dayz-3d-viewer`.

The screen-rectangle predictor (`ui_rects.py`) is also absent on purpose: this
repo ships the format lab, not a geometry model. See
[Two `.layout` parsers](#two-layout-parsers).

The in-game verification bridge (DayZ-MCP) is described in
[`dayz-mcp.md`](dayz-mcp.md) and in the bridge protocol note,
`skills/_shared/knowledge/mcp-bridge-protocol.md`.

---

## Reaching for a tool

The skills say how to build something; the tools say whether it survived. An
agent that forgets they exist reasons about a symptom it could have measured,
or writes a one-off parser for a format that already has a reader. Name the
tool to the user when the work reaches one of these rows, including when the
answer is "install it first".

### By symptom: reach for this before theorising

| What is observed | First instrument | What it settles |
|---|---|---|
| Model loads white, untextured or invisible | `python -m dayz_model_preflight check <p3d> --contract <json>` | Whether the selections, scale and winding the export needed are actually in the file |
| `binarize` refuses the model | same, plus `py3d.validate()` | Which LOD breaks a budget, instead of bisecting by rebuild |
| Animation never plays | `python -m dayz_animation_formats inspect <rtm> --output anatomy.json` | Whether the signature and bone track are what the engine expects |
| Layout renders empty, or a widget is missing | `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout> --check` | Broken references and structure, offline, with no build |
| Need a widget rectangle or click centre | geometry parser + `ui_rects.py` (not in this repo; see [Two `.layout` parsers](#two-layout-parsers)) | Absolute screen rect / centre; unmodelled anchors are refused, not guessed |
| Need text, color or image from a `.layout` | `python scripts/tools/dayz-ui-lab/dayz_ui_lab/parse.py <layout>` | Full-key format parse, not geometry |
| About to change a linter rule | `python scripts/tools/dayz-script-validator/scripts/vanilla_control.py` | Whether the new rule is silent on Bohemia's tree |
| Need a 3D preview of an MLOD `.p3d` without launching DayZ | `python -m dayz_3d_viewer build-viewer <p3d>` | Whether the visual LOD, textures and materials survived the export |
| Two builds differ and nobody knows where | `python -m dayz_odol_strict diff <ref.json> <cand.json>` | The field that changed, not a visual impression |
| A rebuilt PBO should differ only where you changed it | `python scripts/tools/dayz-pbo-diff/pbo_diff.py --old <old.pbo> --new <new.pbo> --out <diff.json>` | Which entries' bytes changed or appeared, and whether the header properties did |
| A regenerated navmesh "changed everywhere" | `python scripts/tools/dayz-navmesh-compare/compare_navmesh.py --old-nm <old.nm> --new-nm <new.nm> --out <report.json>` | Which tiles changed structure rather than bytes, how far from the terrain edit and under which routes |
| A change looks right in Blender but wrong in game | the in-game bridge ([`dayz-mcp.md`](dayz-mcp.md)) | The engine's opinion, which is the only one that counts |
| You are about to parse or emit a `.p3d` by hand | `py3d` | Do not write a bespoke codec; this one fails closed and verifies its own writes |

### By task: what is in play before you start

| Task | Tools | Note |
|---|---|---|
| Importing or authoring a model | `py3d`, then `dayz-model-preflight` | Preflight is a gate, not a repair: it never guesses a mapping and never edits the model |
| Comparing against a shipped asset | `dayz-odol-strict` | Read-only, and its backend is not in this repo: external and hash-pinned, installed separately |
| Animation, RTM or SEAnim work | `dayz-animation-formats` | BMTR and `.anm` conversion are deliberately out of scope |
| UI and `.layout` work | `dayz-ui-lab` | The offline render is a semantic model, not the engine; DayZDiag stays the golden reference |
| Need a widget rectangle or click centre | `layout_ast.py` + `ui_rects.py` (not in this repo) | Contract in [Two `.layout` parsers](#two-layout-parsers) |
| Need `.layout` text / color / image | `dayz-ui-lab` | Format parser; see the two-parser contract above |
| Changing a linter rule, detector or parser | `vanilla_control.py` | Gate for linter authors, not a mod-cycle step |
| Preview an MLOD `.p3d` / PAA / RVMAT | `dayz-3d-viewer` | HTML loads three.js 0.185.1 from a CDN; SWIZ, proxies and ViewPilot 1100 are documented gaps |
| Verifying anything in-game | the MCP bridge | Wiring example in [`dayz-mcp.md`](dayz-mcp.md), deliberately not auto-started |
| Rebuilding or patching a PBO | `dayz-pbo-diff` | Payload SHA-256 per entry; between two builds a different `.p3d` entry proves nothing by itself |
| Regenerating a terrain's navmesh | `dayz-navmesh-compare` | Structure, not bytes; verified only for one 12 288 m world in 12.5, 25 or 50 m tiles |
| Driving Terrain Builder without the desktop | `dayz-terrain-builder-runner` | EXPERIMENTAL, Windows only: menus and file dialogs verified; Generate Layers, imports and WRP export not; a disposable instance only |
| Working on Linux (DayZ Tools, DayZDiag, `P:`) | `skills/_shared/scripts/dayz-proton.sh` | Runs BI's tools under Proton in private prefixes; native dayzmake / `workshop` first. Guide and measured matrix: `skills/_shared/linux-proton.md` |
| Testing a mod on Linux without dayz-mcp (native server, headless retail client), building and publishing with dayzmake | `make-server-tree.sh`, `free-ports.sh`, `dayz-client-test.sh` and `dayz-mod-pack.sh` in `skills/_shared/scripts/` | References: `skills/dayz-test-ingame/references/linux-native-server.md` and `linux-headless-client.md` beside it, and `skills/dayz-build-pbo/references/dayzmake-linux.md` |

Two habits make the difference. Propose the tool **before** the expensive step,
not after it fails: that is the whole point of a preflight. And when a tool
reports clean, say which check ran clean; "preflight passed" without naming the
contract does not say what was verified.

## Running the tool tests

Each tool keeps its suite in its own `tests/` folder (`skill-runtime-pin` has
none there; `scripts/dev/knowledge-pack/tests/packctl/test_packctl_runtime_pin.py`
covers it). `python -m pytest -q scripts/tools` from the repository root runs
them all in one process, and CI runs them as part of the repo's test command
(`.github/workflows/tests.yml`). That works only while every test module has a
unique file name: two test files with the same basename in different folders
abort the whole collection with "import file mismatch" before a single test
runs. Name a new test module after its tool.
