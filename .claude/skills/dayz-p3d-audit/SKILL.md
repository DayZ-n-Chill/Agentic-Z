---
name: dayz-p3d-audit
description: "Audits DayZ .p3d models and their config.cpp, model.cfg and .rvmat for collision, action, physics, animation and path problems (report only). Use when an object has no collision or actions, players walk through it, a Blender export fails, textures are missing, animations don't play, or the user asks to review, check or audit a .p3d model, its model.cfg or its .rvmat."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-p3d-audit

Validates .p3d model files, config.cpp, model.cfg, and .rvmat materials against
DayZ engine requirements — targeting the failure modes that produce zero engine
errors but break collision, targeting, animation, or textures.

Follow `.claude/skills/_shared/dayz-conventions.md`. The script runs `/dayz-preflight` first and stops if it fails.

## How to run

The script reads .p3d files with py3d. Install it once:

```cmd
python -m pip install -r "<skill-dir>\requirements.txt"
```

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
python "<skill-dir>\scripts\audit_p3d.py" --rvmat path\to\a.rvmat path\to\b.rvmat
```

**Full mod sweep** (all .p3d, config.cpp, .rvmat, model.cfg; other inputs are ignored):
```cmd
python "<skill-dir>\scripts\audit_p3d.py" --scan-dir path\to\mod\
```

Animations are checked from model.cfg. The script finds the `CfgModels` class named
after the model file (inherited from its parent class when it has no `Animations` of
its own) and, for each animation, checks that its `selection` exists in the Visual LOD,
that its `axis` has exactly 2 points in the Memory LOD, and that any `begin` and `end`
points exist there. The model.cfg comes from `--model-cfg`, or under `--scan-dir` from
the model's folder or the nearest parent folder. Without a model.cfg, animations are
not checked.

The Geometry LOD `autocenter` property is checked only when the config.cpp (`--config`,
or under `--scan-dir` the nearest one found the same way) has a class with
`autocenter = 0`. Kits and ordinary items do not use it, so they get no finding The same config decides the
`pos center` checks: a missing `pos center` (WARNING) or one far from the origin (NOTE)
is reported only for those autocenter=0 items. The missing `box_placing_min/max` NOTE
appears only for a model with no Geometry LOD (the hologram uses the Geometry LOD
bounding box first) and never when `boundingbox_min/max` are present.

Exit codes:

- **0**: no CRITICAL finding and no `P:\` path. WARNING and NOTE findings on .p3d files
  are printed but don't fail the run.
- **1**: any .p3d has a CRITICAL finding, any text file has a `P:\` path, or a file or
  the `--scan-dir` folder is missing or unreadable.
- **2**: no input was given, or py3d is not installed. The second case prints the
  `python -m pip install -r` line above.

Only MLOD source files can be audited; binarized ODOL files are rejected. When a model
has several Visual LODs, LOD0 is the one checked. Interpret findings with the
references below.

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
   NO  ↓ (P3D Geometry LOD issue — engine can't raycast)

5. Run audit_p3d.py and check:
   a. Face winding outward?      → Verify per references/winding-methodology.md
                                    (the script deliberately omits the naive
                                    centroid check — it false-positives on DayZ)
   b. Component01 uppercase C?   → If wrong case: rename
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

Deep material lives in `<skill-dir>\references\`:

- **`references/p3d-killers.md`** — the 10 silent P3D killers (inverted winding,
  Component01 case, autocenter LOD property, missing LODs, memory points, animation
  selections, collision-LOD surface materials, …) plus Blender export pitfalls and
  script-side gotchas that co-occur during debugging.
- **`references/config-rvmat-checks.md`** — config.cpp checks (P:\ paths, placed-object
  properties, AnimationSources, hiddenSelections) and .rvmat checks (paths, plus the
  Super-shader stage layout to review by hand).
- **`references/winding-methodology.md`** — how to actually verify face winding
  (edge-pair topology, averaged-normal checks), which heuristics mislead and why,
  known traps, and the full Blender-import checklist.
