---
name: dayz-p3d-audit
description: >
  Audits DayZ MLOD .p3d models for collision, action-targeting, physics, animation and
  structural problems, and scans config.cpp, model.cfg and .rvmat files for absolute
  P:\ paths. Reports findings only. Use when a mod object has no collision, actions
  don't appear, players walk through placed objects, a Blender-exported model fails
  in-game, textures are missing, animations don't play, or the user asks to review,
  check or audit a p3d or mod.
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-p3d-audit

Validates .p3d model files, config.cpp, model.cfg, and .rvmat materials against
DayZ engine requirements — targeting the failure modes that produce zero engine
errors but break collision, targeting, animation, or textures.

Follow `.claude/skills/_shared/dayz-conventions.md`. The script runs `/dayz-preflight` first and stops if it fails.

## How to run

```bash
# Requires py3d:
pip install git+https://github.com/KoffeinFlummi/py3d.git

# Audit one or more models (MLOD source, not binarized ODOL):
python <skill-dir>/scripts/audit_p3d.py path/to/model.p3d [more.p3d ...]

# Include config/model.cfg path checks:
python <skill-dir>/scripts/audit_p3d.py model.p3d --config path/to/config.cpp --model-cfg path/to/model.cfg

# Check .rvmat materials for P:\ paths:
python <skill-dir>/scripts/audit_p3d.py --rvmat path/to/a.rvmat path/to/b.rvmat

# Full mod sweep (all .p3d, config.cpp, .rvmat, model.cfg; other inputs are ignored):
python <skill-dir>/scripts/audit_p3d.py --scan-dir path/to/mod/
```

Exit 2 if no input is given. Exit 1 if any .p3d has a CRITICAL finding, any text file
has a `P:\` path, or a file or the `--scan-dir` folder is missing or unreadable;
otherwise exit 0 (WARNING and NOTE findings on .p3d files are printed but don't fail
the run). Only MLOD source files can be audited; binarized ODOL
files are rejected. When a model has several Visual LODs, LOD0 is the one checked.
Interpret findings with the references below.

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
   c. autocenter=0 LOD property? → If missing: add
   d. pos center in Memory?      → If missing: add at (0,0,0)
   e. Component01 covers all?    → If partial: extend selection
   f. Mesh watertight?           → If open: close gaps
   g. Geometry LOD exists?       → If missing: create one

6. Animations not playing?
   → Check flag_mast selection in Visual LOD
   → Check flag_mast_axis (2 points) in Memory LOD
   → Check AnimationSources in config.cpp matches model.cfg

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
