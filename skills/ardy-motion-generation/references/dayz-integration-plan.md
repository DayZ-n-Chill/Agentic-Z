# ARDY to DayZ integration plan (unverified)

The steps that would turn an ARDY `.npz` into a DayZ `.anm`, which of them are untested, and the open questions to settle first.

This whole document is design: a plan and a hypothesis, not a tested procedure. No step of the chain has been run. Before writing retargeting code, read it in full and decide with the user whether each stretch gets its own checkpoint. A change that touches more than one mod or skill file needs the user's approval first; do not chain the four steps in one session without stopping in between.

## Why this plan exists without being verified

The use chosen for ARDY is full-body survivor locomotion (running, jumping, vaulting). For that to become playable in DayZ a conversion chain is needed that does not exist today. Writing the plan down now saves a later session from working out again what is missing, but **do not take it as a verdict that the chain works**: each arrow below is a plausible point of failure that nobody has explored.

## The complete chain

```
ARDY .npz ("core" skeleton: world-space joints + rotations + root + foot contacts)
  │
  │  [DESIGN] Step 1: parsing
  ▼
Import into Blender (custom Python script, numpy to armature)
  │
  │  [DESIGN] Step 2: the highest-risk step
  ▼
Retarget to OFP2_ManSkeleton (the DayZ player skeleton)
  │
  │  [EXISTING: the pipeline already used and verified, see dayz-animation-pipeline]
  ▼
Export .txa → Workbench → .anm (SEAnim / DayZATool)
  │
  ▼
In-game gate
```

Only the last leg (`.txa` to `.anm` to in game) has a verified pipeline: it is the one `dayz-animation-pipeline` already uses for any skeletal player animation. Steps 1 and 2 are new territory.

## Step 1: parse the `.npz`

Low technical risk: it is a numpy archive with a documented structure (`posed_joints [T,J,3]`, rotations, root, foot contacts). Write a script that loads it and inspects the actual shape of the first generated output before assuming the layout. The README does not give the exact dtype or axis order (XYZ or XZY, Y-up or Z-up).

The axis convention matters twice. Blender is Z-up; the DayZ engine is Y-up (`vector.Up` is `"0 1 0"`, `P:\scripts\1_core\proto\enconvert.c:120`), and the Blender to DayZ export does that conversion (see the axis and winding caveats in the model skills). Confirm the `.npz` convention with a real file; do not assume the convention of another pipeline.

## Step 2: retarget to the DayZ player skeleton (the step that can kill the plan)

Structurally this is the problem the `mixamo-retarget` skill already solves, partly and experimentally: mapping a generic external skeleton onto the specific bone hierarchy DayZ expects. Differences that may make it harder than the Mixamo case:

- The ARDY "core" skeleton has no documented official mapping to any game format (not FBX, not BVH, not SMPL). The bone-by-bone map has to be derived by hand, comparing names and hierarchy against the full DayZ player bone map (core and spine, legs, arms, IK helpers, fingers). That map is in `dayz-animation-pipeline`; the vanilla bone list is `hermit_newbindpose.xob` in `P:\DZ\anims\cfg\skeletons.anim.xml:2`.
- The exact bone count of "core" is not known from an official source (a video said 27; that is not confirmed on research.nvidia.com or GitHub). Count the actual joints of the first generated `.npz` before trying to map.
- DayZ expects fingers, the hand helpers `LeftHand_Dummy` and `RightHand_Dummy` (both `lod = "2"`, `P:\DZ\anims\cfg\skeletons.anim.xml:74` and `P:\DZ\anims\cfg\skeletons.anim.xml:100`) and several IK helpers (`RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget`, listed for `player_testing.xob` at `P:\DZ\anims\cfg\skeletons.anim.xml:149-151`). A generic "core" skeleton of 27 bones probably covers none of them. Leg and torso locomotion may map reasonably well, but hands and fingers will probably have to stay in their bind pose (unanimated) or inherit from another source.

**Open question to settle with the first test:** is retargeting only legs, torso and spine (leaving arms and hands untouched, or additive) enough for the real goal of running, jumping and vaulting? If yes, the retargeting scope shrinks a lot and the risk drops. Decide this before trying to map hands and fingers, which is where this kind of retarget usually fails most.

## Steps 3 and 4: export and the final pipeline

Once an FK pose exists on the Blender armature with the correct DayZ bone names, the rest of the chain (`.txa`, Workbench, `.anm`) is the pipeline `dayz-animation-pipeline` already verified. Nothing new is designed there; run the known process (see that skill for the export details).

## Alternatives if direct retargeting does not pay off

If step 2 costs too much for the actual benefit:

- Use ARDY only as a **visual reference** (a playblast) and animate by hand in Blender or Cascadeur, instead of trying an automatic one-to-one retarget. This loses "real time" but avoids the skeleton mapping problem.
- Check whether Cascadeur covers the same locomotion goal without ARDY's non-standard skeleton problem. In the source notes' comparison of animation tools Cascadeur got a conditional medium verdict and was the only one with custom skeleton, IK and FK, and physics support. That comparison note is not part of this repo.

## Cross-references

- `dayz-animation-pipeline`: the full bone map of the DayZ player, needed to design the step 2 mapping, and the final `.txa`, Workbench and `.anm` route.
- `mixamo-retarget`: the same kind of problem (external retarget onto DayZ), still experimental. Read what failed or stayed open there before going down the same path.
- `dayz-realistic-animation-director`: the acceptance contract and evidence states for whatever motion comes out of the chain.
