---
name: dayz-characters
description: "Runs the offline winding and normal gate on the source .p3d of a DayZ humanoid (a custom infected, survivor or NPC) before it is packed, so an inside-out model or normals stored the wrong way show before a test cycle. Use after building a character .p3d from Blender, before every pack, or when a character renders inside-out, see-through or lit inverted. The knowledge about rigging, binding, baking and the LODs of a new body is in the wearables pack, skills/_shared/wearables/README.md."
argument-hint: "<model.p3d> [--py3d <py3d-folder>]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-characters

Runs the winding gate on a character model. The gate script ships with the model tools; this skill is the entry point for running it on a body.

Follow `skills/_shared/dayz-conventions.md`. The gate reads one source file and starts no DayZ tool, so it does not run `/dayz-preflight`; packing and in-game testing go through `/dayz-build-pbo` and `/dayz-launch-test`, which do.

## How to run

Run it on the source MLOD after building the `.p3d` and before every pack:

```cmd
python "<skill-dir>\..\dayz-model-tools\scripts\check_dayz_winding.py" path\to\model.p3d
python "<skill-dir>\..\dayz-model-tools\scripts\check_dayz_winding.py" path\to\model.p3d --py3d path\to\py3d
```

| Exit | Meaning |
|---|---|
| 0 | PASS: every closed shell of every visual LOD is wound inward and its stored normals agree. A PASS that left open or flat parts unscored says so |
| 1 | A model defect, with the fix printed in order: winding first, then normals |
| 2 | Invalid input, a binarized ODOL file, a py3d that is not the DayZ fork, or a LOD with nothing measurable |

The gate needs the py3d DayZ fork in `scripts/tools/py3d/`. A PASS cannot see a mirrored export; check that on an asymmetric feature in game (the chiral check in `skills/_shared/wearables/references/body-rigging.md`, section 6). What the gate reads, how to apply its fixes and what a PASS does not cover: `skills/_shared/models/tools-winding-gate.md`.

Outside an agent session, `scripts\dayz\check-winding.bat` runs the same script with the same arguments.

## Where the character knowledge is

| Question | Read |
|---|---|
| How do I rig a new body to the vanilla skeleton and export it with weights? Why does it explode, face backward or render inside-out? | `skills/_shared/wearables/references/body-rigging.md` |
| Why does a body that looks fine at rest deform under animation? What does an infected bind to? Is my mesh mirrored? | `skills/_shared/wearables/references/canonical-bind.md` |
| How do I unwrap and bake normal and AO maps for a rigged body? | `skills/_shared/wearables/references/body-uv-bake.md` |
| Which LODs does a new body need, how do I model a see-through hole, why can size not come from a scale call? | `skills/_shared/wearables/references/body-lods.md` |
| How is the 1.30 survivor ragdoll bound? | `skills/_shared/wearables/references/ragdoll.md` |
| Which class does a custom infected inherit, and what must its model keep for the AI? | `skills/_shared/ai/custom-infected.md` |
| What does a survivor inherit from `SurvivorBase`? | `skills/_shared/wearables/references/characters.md` |
