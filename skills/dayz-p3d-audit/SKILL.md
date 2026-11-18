---
name: dayz-p3d-audit
description: "Audits DayZ .p3d models and their config.cpp, model.cfg and .rvmat for collision, action, physics, animation, winding and path problems (report only). Use when an object has no collision or actions, players walk through it, raycasts miss it, a Blender export fails, a vehicle's wheels don't simulate, textures are missing, animations don't play, or the user asks to review, check, validate or audit a .p3d model, its model.cfg, its .rvmat or a whole mod's paths."
argument-hint: "<model.p3d ...> [--config <config.cpp>] [--model-cfg <model.cfg>] [--rvmat <file.rvmat>]... | --scan-dir <mod-dir>"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-p3d-audit

Validates .p3d model files, config.cpp, model.cfg, and .rvmat materials against
DayZ engine requirements, targeting the failure modes that produce zero engine
errors but break collision, targeting, animation, or textures.

Follow `skills/_shared/dayz-conventions.md`. The script runs `/dayz-preflight` first and stops if it fails.

It reports and never edits a file. To look inside a model or move its memory points use the p3d inspector of `/dayz-model-tools`; to build or fix a model follow the generated model pipeline (`skills/_shared/models/generated-model-pipeline.md`); to place proxies use the proxy editor of `dayz-model-tools`.

## How to run

The script reads .p3d files with py3d. It uses the DayZ fork of py3d kept in this repo under `scripts/tools/py3d/`, the one py3d copy every skill in this repo shares, and loads it from that folder with nothing to install. `requirements.txt` names that same folder. Use it only where `import py3d` must work as an installed package, and run it from the repo root, because pip reads the path in it against the current folder:

```cmd
python -m pip install -r skills\dayz-p3d-audit\requirements.txt
```

Only the fork has `P3D.validate()`. With it the audit adds the fork's findings, the winding checks among them, in a `--- py3d validate() ---` section. When `scripts/tools/py3d/` is missing the script falls back to whatever py3d is installed; if that is the stock py3d library, which has no `validate()`, the section says the checks did not run, and winding has to be checked by hand (`references/winding-methodology.md`).

**Audit one or more models** (MLOD source, not binarized ODOL):
```cmd
python "<skill-dir>\scripts\audit_p3d.py" path\to\model.p3d [more.p3d ...]
```

**Include config/model.cfg path checks and the model.cfg animation check:**
```cmd
python "<skill-dir>\scripts\audit_p3d.py" model.p3d --config path\to\config.cpp --model-cfg path\to\model.cfg
```

**Check .rvmat materials for P:\ paths:**
```cmd
python "<skill-dir>\scripts\audit_p3d.py" --rvmat path\to\a.rvmat --rvmat path\to\b.rvmat
```
Repeat `--rvmat` once per file; a `.p3d` written after it is still audited as a model.
`P:\` paths inside `//` or `/* */` comments are ignored, since the engine never reads them.

**Full mod sweep** (all .p3d, config.cpp, .rvmat, model.cfg; other inputs are ignored):
```cmd
python "<skill-dir>\scripts\audit_p3d.py" --scan-dir path\to\mod\
```
The sweep ends with a `SCAN SUMMARY` line counting CRITICAL findings, `P:\` paths and
ODOL rejects across the failing files, then one line per failing file with its own counts.
A backup model (a `.p3d` with `.bak` in its name or under a `.bak` folder) is skipped and named.

Animations are checked from model.cfg. The script finds the `CfgModels` class named
after the model file (inherited from its parent class when it has no `Animations` of
its own) and, for each animation, checks that its `selection` exists in the Visual LOD,
that its `axis` has exactly 2 points in the Memory LOD, and that any `begin` and `end`
points exist there. The model.cfg comes from `--model-cfg`, or under `--scan-dir` from
the model's folder or the nearest parent folder. Without a model.cfg, animations are
not checked.

The Geometry LOD `autocenter` property is checked only when the config.cpp (`--config`,
or under `--scan-dir` the nearest one found the same way) has a class whose
`model` is this p3d and that sets `autocenter = 0` (either one may come from a parent class in
the same file). Kits and ordinary items do not use it, so they get no finding. The
same config decides the `pos center` checks: a missing `pos center` (WARNING) or one far
from the origin (NOTE) is reported only for those autocenter=0 items. The missing `box_placing_min/max` NOTE
appears only for a model with no Geometry LOD (the hologram uses the Geometry LOD
bounding box first) and never when `boundingbox_min/max` are present. Memory LOD point
names match without case (`Pos Center` counts as `pos center`), like the animation lookups.
A config.cpp that exists but cannot be read is an `ERROR` that fails the run, since the
autocenter and `pos center` checks could not be decided.

Degenerate faces are measured over the whole polygon: a quad is split into two triangles,
so a valid quad whose first three vertices lie on one line is not flagged.

Four checks read the whole model and print under `--- Whole model ---`:

| Check | Finding |
|---|---|
| Needle triangles in a `ComponentNN` of the Geometry, View or Fire Geometry LOD | CRITICAL for a triangle under 1e-6 m², or under 1e-4 of the square of its longest edge. In game a hull holding one took no ray. The finding names the point to drop. |
| Resolved vertices of the most detailed Visual LOD | CRITICAL over 65,535 distinct (point, normal, uv) corners; WARNING when only the raw counts exceed it, or when a vehicle body's LOD is heavy before its proxies are added. |
| Vehicle body Geometry LOD without the named property `class=vehicle` | CRITICAL (parity with every vanilla wheeled body). |
| Vehicle body whose wheel-slot selection is missing from the Fire Geometry LOD | CRITICAL; needs the config.cpp (`--config`, or the nearest one under `--scan-dir`). Without one the output says the check was not run. |

A model is treated as a vehicle body when a selection name contains `damper`. Always pass
`--config` for a vehicle body: without it the body can pass while its wheels will never simulate
(`references/vehicle-checks.md`).

The `--- py3d validate() ---` section holds the DayZ fork's findings, each with its LOD and code,
for example `LOD[1] [ERR_WINDING_INVERTED] ...`. The fork's ERROR prints as CRITICAL and its WARN
as WARNING. A fork finding that this script already makes itself on the same LOD is left out
(autocenter, `pos center`, component naming and the coverage WARN on the Geometry LOD, whose
coverage ERROR still prints as CRITICAL; watertight and
degenerate faces, `P:\` paths on faces), because the script's own version knows the config.cpp
and model.cfg. The fork guesses an animation's selection from the axis name; that guess is left
out when a model.cfg was checked and is only a WARNING when none was. A winding finding is a
trigger to check the model per component, not a verdict (`references/winding-absolute-check.md`).

Exit codes:

- **0**: no CRITICAL, P-DRIVE or ERROR finding. WARNING and NOTE findings are printed
  but never fail the run.
- **1**: any .p3d has a CRITICAL finding, any text file (config.cpp, .rvmat, model.cfg)
  has a `P:\` path, printed as a `P-DRIVE` finding with its line number, or a file or
  the `--scan-dir` folder is missing or unreadable. A binarized ODOL .p3d (not MLOD) and
  a .p3d that cannot be read also give exit 1, with a `[FAIL]` line on stderr naming why. When
  the only failures are ODOL files, the last line is `OVERALL: NOT AUDITED` (the file was
  never checked) instead of `OVERALL: ISSUES FOUND`.
- **2**: no input was given, or py3d was not found (no `scripts/tools/py3d/` folder and
  no installed py3d). The second case names the missing folder and prints the
  `python -m pip install -r` line above.

Only MLOD source files can be audited; binarized ODOL files are rejected. Audit the
MLOD the model was built from (the .p3d Object Builder saves; Addon Builder binarizes it
when packing). Agentic-Z ships no debinarizer, so a vanilla or third-party ODOL model
with no source cannot be audited here. When a model
has several Visual LODs, LOD0 is the one checked. Interpret findings with the
references below.

A clean audit is not proof the model works in game. py3d's checks prove internal
consistency, not that the geometry is right (`references/winding-absolute-check.md`, "The
three py3d gates"), and several faults cannot be seen from one file
(`references/manual-checks.md`). Spawning the built model in game is the last check.

## Vehicle checks

Three more scripts check ground and water vehicles. The vehicle pack (`skills/_shared/vehicles/README.md`) says what each finding means.

| Script | What it checks | Input |
|---|---|---|
| `scripts\audit_getin_wheels.py` | Get-in memory points, seat selections and wheel axis handedness | One or more MLOD `.p3d` files |
| `scripts\gate_odol_sections.py` | Whether each named selection of a binarized model has a section the engine draws | One ODOL `.p3d` taken out of the packed PBO, and the selection names |
| `scripts\check_odol_bone_refs.py` | Which skeleton bone the vertices of a section bind to in a binarized model | One ODOL `.p3d` taken out of the packed PBO, and a texture substring |

They read only the files you pass, so they do not gate on `/dayz-preflight`. `audit_getin_wheels.py` loads py3d like the audit. The two ODOL scripts do not use py3d (it reads MLOD only): they need an external ODOL parser, the `bis_reader` and `odol_reader` modules of an ODOL to MLOD converter that reads ODOL version 56, which this repo does not ship. Point at its folder with `--backend-root <dir>` or the environment variable `DAYZ_ODOL_BACKEND_ROOT` (also read by `scripts/tools/dayz-odol-strict/`); without it they exit 2 and say what is missing.

**Get-in anchors, seats and wheel axes:**
```cmd
python "<skill-dir>\scripts\audit_getin_wheels.py" path\to\car.p3d [path\to\control.p3d ...]
```
For each model it prints the LOD list; each get-in anchor of the Memory LOD (`crewdriver`, `crewcodriver`, `pos_driver`, `pos_driver_dir`, `pos_codriver`, `pos_codriver_dir`, `seat_con_1_1`, `seat_con_2_1`) as `OK` with point count and centroid, `EMPTY` or `ABSENT`; the unit direction of each wheel axis (`wheel_1_1_axis` to `wheel_2_2_axis`), where left and right axes with different X signs predict one side spinning backwards under a shared `angle1` (`animation-sign-and-axis.md` of the vehicle pack); and which seat selections (`seat_driver`, `seat_codriver`, `seatback_driver`, `seatback_codriver`) the Geometry, View Geometry and Fire Geometry LODs hold. Pass a car that works in game next to the one under test and compare the blocks. Exit 0 when every anchor, wheel axis (two points or more) and seat selection (in Geometry or View Geometry) is present; 1 with a `FAIL:` line per defect; 2 for no input, a missing or unparsable file (`INPUT_ERROR:`, no report printed) or no py3d. The required names are the two-seat roster of the reference quad: a four-seat car is checked on its front pair, and a car without seat-back selections gets a `FAIL:` for each, so read those lines against the car's own `Crew` config. The rules are in `invariants-get-in-and-seats.md` and `invariants-wheels-and-hubs.md` of the vehicle pack.

**Drawable sections in a binarized model:**
```cmd
python "<skill-dir>\scripts\gate_odol_sections.py" path\to\binarized.p3d --selection screen_nav --selection light_dashboard [--lod 0 --lod 1100] [--keyword dashboard] [--backend-root path\to\odol-backend]
```
Run it on the `.p3d` extracted from the PBO you are about to deploy, after any change that adds geometry or a textured selection: a selection can be in every string table and still never render, because its section decides (`animation-bake-and-odol-sections.md` of the vehicle pack). It prints the ODOL version and LODs, the bones named like a gated selection or keyword, and for each LOD read (default 0 and 1100) the counts, bounding box, keyword textures and materials (default keywords `gps`, `marker`, `cluster`, `screen`, `argb`, `color`, `dashboard`, `cab_screen`), faces no section covers, and proxies; for each `--selection` its faces, vertices, sections (face range, bone range, texture, material, `special` flags), vertex positions, UVs and bone references, and face areas in square millimetres. Exit 0 when every gated selection is drawable in every LOD read (or no `--selection` was given); 1 with a `FAIL:` line when a selection is missing, not sectional (not in `CfgModels` `sections[]`), owns no section, or has a section without the hidden-selection bit `0x20000` in `special` (a `0x0000C000` section is never drawn); 2 for no input, a missing file, an MLOD file, an unreadable file, a `--lod` the model lacks or no parser. A selection absent from the first-person LOD on purpose fails at 1100: pass `--lod 0` alone.

**Which bone a section binds to:**
```cmd
python "<skill-dir>\scripts\check_odol_bone_refs.py" path\to\binarized.p3d --texture gps_arrow [--texture cluster --max-faces 2] [--reference-texture cluster_co.paa] [--lod 0] [--backend-root path\to\odol-backend]
```
Use it when a section passes the gate above and still does not show: a vertex bound to a bone whose hide animation starts at phase 1 is invisible from spawn. For each LOD it lists every section whose texture path contains a `--texture` substring (with `--max-faces N`, only sections of at most N faces; a witness quad has two) and, per vertex, the bone name, index and weight or `NONE/static`. `--reference-texture` also prints the bone of the first vertex of a section known to render (the first of more than ten faces whose texture ends with that suffix). Read the bones against the model's `model.cfg` animations; the script reports and does not judge. Exit 0 when the report printed; 2 for no `--texture`, a missing or unreadable file, a `--lod` the model lacks or no parser.

## Diagnostic decision tree

```
1. Can you SEE the object in-game?
   NO  → Check model path in config.cpp (backslash prefix, case)
   YES ↓

2. Is the object buried/floating?
   BURIED → Missing autocenter=0 in config.cpp AND/OR LOD property
   FLOATING → autocenter=0 on a kit class (only placed objects need it)
   CORRECT ↓

3. Does floating text (item name) appear near it?
   NO  → Entity not spawned. Check CreateObjectEx, server logs
   YES ↓

4. Do debug Print() in ActionCondition appear in script log?
   YES → ActionCondition rejecting. Read prints to find which check fails
   NO  ↓ (P3D Geometry LOD issue: engine can't raycast)

5. Run audit_p3d.py and check:
   a. Collision winding inward   → Every face of every collision component
      on every component?           must wind INWARD (references/p3d-killers.md
                                    section 1). An ERR_WINDING_INVERTED finding
                                    (DayZ fork of py3d) is the trigger; confirm
                                    per component, then reverse only the faces
                                    that read outward with face.vertices.reverse(),
                                    never a vertices[1]/[2] swap (a quad crosses).
                                    Without the fork, verify per
                                    references/winding-methodology.md (the script
                                    deliberately omits the naive centroid check:
                                    it false-positives on DayZ)
   b. Component01 present?       → Lowercase component01 is fine (a NOTE;
                                    vanilla binarized models use it). Another
                                    spelling is a WARNING: rename to Component01
   c. autocenter=0 LOD property? → If missing: add (checked only when config.cpp
                                    sets autocenter = 0)
   d. pos center in Memory? (autocenter=0 items only) → If missing: add at (0,0,0)
   e. Components cover all?      → The Component selections together cover
                                    every vertex and face; each component is
                                    one convex closed piece. If some are left
                                    out: add them to a component
   f. Mesh watertight?           → If open: close gaps
   g. Geometry LOD exists?       → If missing: create one
   h. Geometry LOD mass set?     → The audit prints the mass as a NOTE, or says
                                    the LOD has none
   i. Collision faces have a     → CRITICAL when any face in the Geometry,
      material?                     GeoPhys or FireGeo LOD has none: assign a
                                    penetration .rvmat (references/p3d-killers.md
                                    section 10). In the ViewGeo LOD it is only a
                                    WARNING, since View Geometry faces often
                                    carry no material
   j. No needle triangle in a    → If the audit names one: build that hull again
      component?                    without the point it names, the corner
                                    opposite the needle's longest edge
                                    (references/collision-mesh-hygiene.md)
   k. Vehicle: wheels attach but → Run with --config. A wheel-slot selection
      never simulate?               missing from the Fire Geometry LOD is the
                                    silent cause (references/vehicle-checks.md)

6. Animations not playing?
   → Run audit_p3d.py with --model-cfg: the selection each model.cfg
     animation names must exist in the Visual LOD, and its axis must
     exist in the Memory LOD with exactly 2 points
   → Check that config.cpp AnimationSources match the source names
     in model.cfg

7. Textures missing/white?
   → Check P:\ paths in config.cpp hiddenSelectionsTextures
   → Check P:\ paths in .rvmat files
   → Verify .paa files exist at referenced paths
```

## References

Deep material lives in `<skill-dir>\references\`. Open only the file the question needs.

| Question | Open |
|---|---|
| Which model faults break a `.p3d` with no engine error, and what does each finding mean? Blender export pitfalls and script-side gotchas. | `references/p3d-killers.md` |
| What was measured in game for the winding, component and coverage killers, and what else is worth knowing about the other model killers? | `references/killers-detail.md` |
| How are needle triangles detected and fixed, and what goes wrong in source meshes used for collision? | `references/collision-mesh-hygiene.md` |
| Which config.cpp and .rvmat checks apply (`P:\` paths, placed-object properties, AnimationSources, hiddenSelections, the Super shader stage layout)? | `references/config-rvmat-checks.md` |
| How do I verify face winding by hand (Check A, B, C), which heuristics mislead, and what is the Blender import checklist? | `references/winding-methodology.md` |
| How does each winding state read on measured models, and how do I turn a Check B result into a safe fix? Where do offline checks stop (the in-game spawn gate)? | `references/winding-diagnostics.md` |
| What do `ERR_WINDING_INVERTED` and `ERR_WINDING_VS_NORMALS` mean, which side do I fix, and why is a clean py3d result not proof? How does the winding sign change in the binarized model? | `references/winding-absolute-check.md` |
| What does the audit check on a vehicle body, and which vehicle faults (wheel memory points, ride height, mass, crew, the get-in contract) must be measured by hand? | `references/vehicle-checks.md` |
| What did the vehicle killers look like on real mods (mass tagged in the wrong LOD, wheel-well clearance, crew seat components, crew proxy triangles, the vertex ceiling), with the measurements? | `skills/_shared/vehicles/p3d-vehicle-killers.md` (vehicles pack) |
| The audit passes and the model still misbehaves: which faults can it not see (frame parity between sibling models, UVs, LOD count, face indices, the vertex budget), and how do I trust a new gate? What changes on Linux? | `references/manual-checks.md` |

Model facts that are not faults (LODs, memory points, selections, named properties,
proxies) are in the `_shared/models/` pack.
