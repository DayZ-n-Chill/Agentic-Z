---
name: dayz-p3d-audit
---

## Overview

&gt;

> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-p3d-audit

Validates .p3d model files, config.cpp, model.cfg, and .rvmat materials against
DayZ engine requirements — targeting the failure modes that produce zero engine
errors but break collision, targeting, animation, or textures.

## Preflight gate

Per the L2 rule (`.claude/skills/_shared/dayz-conventions.md`), every DayZ skill that does work gates on `/dayz-preflight` first. The audit reads `.p3d` files which can live anywhere, but the moment you point it at `P:\` paths or a built mod, an unmounted P-drive silently produces wrong results. Run `/dayz-preflight` before this skill.

## Quick start

```bash
# Requires py3d:
pip install git+https://github.com/KoffeinFlummi/py3d.git

# Audit one or more models (MLOD source, not binarized ODOL):
python <skill-dir>/scripts/audit_p3d.py path/to/model.p3d [more.p3d ...]

# Include config/model.cfg path checks:
python <skill-dir>/scripts/audit_p3d.py model.p3d --config path/to/config.cpp --model-cfg path/to/model.cfg

# Full mod sweep (all .p3d, config.cpp, .rvmat, model.cfg):
python <skill-dir>/scripts/audit_p3d.py --scan-dir path/to/mod/
```

Exit 0 = no CRITICAL/WARNING findings. The script covers the P3D structural checks
plus `P:\` path detection in text files; interpret findings with the references below.

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
  properties, AnimationSources, hiddenSelections) and .rvmat checks (paths, texture stages).
- **`references/winding-methodology.md`** — how to actually verify face winding
  (edge-pair topology, averaged-normal checks), which heuristics mislead and why,
  known traps, and the full Blender-import checklist.
