# DayZ handoff: from a Blender action to a `.txa`

What this skill hands to the DayZ animation pipeline when the motion is meant for a DayZ character or weapon: which export route to use, what to key and what to leave out, the coordinate conventions, the loop notetracks, and what the `dayz-animation-pipeline` skill already owns.

## How to read this file

- A fact about the vanilla game cites the vanilla file on `P:\` as `path:line`. Those lines were opened and checked on 2026-11-17. Binary files (`.anm`) have no lines; what is said about them was read from the bone and event names in the file.
- Everything else is **not yet checked on `P:\`**. It is either the behaviour of a tool that is not part of the game (the DayZ Animation Tools plugin for Blender, DayZATool, Workbench) or a result measured in game or with DayZATool during weapon animation work in 2026. A measured result carries its date in brackets, for example "(measured 2026-06-30)".
- "The plugin" is the DayZ Animation Tools add-on for Blender. It exists in two builds: the original, `DayZAnimationPluginDemo`, and the maintained one, `DayZAnimationPlugin_MAINTAINED`. Unless a line says otherwise, "the plugin" means the maintained build.
- "The plugin rig" is the rig that ships with the plugin, `_AssetSamples\JD_Master_Rig (No IK Bones).blend`.
- "The viewer" is the Three.js animation viewer of `dayz-animation-pipeline` (`skills/dayz-animation-pipeline/scripts/build_viewer.py`, described in `weapon-anim-authoring-viewer.md`).
- "The strike animation" is the worked example used throughout: an unjam animation for a custom weapon in which the character hits the weapon. Its files are called `strike.anm` and `strike_retimed.json` here.
- A file named without a folder (`weapon-in-hands.md`) is a reference of the `dayz-animation-pipeline` skill, in `skills/dayz-animation-pipeline/references/`.

---

## Pipeline routes (A and C)

The existing pipeline is Layer 2 of `dayz-animation-pipeline` (skeletal `.anm` authoring). It is built around the viewer and was validated end to end in game on the strike animation. Two export routes lead from a posed skeleton to the binary `.anm` DayZ loads: **Route A** and **Route C**.

### Route A: `.txa` (the plugin) → Workbench → `.anm`. The canonical route

- Definition (`weapon-anim-authoring-viewer.md`): the viewer's world pose is dumped and written to a `.txa` through the plugin in Blender, then Workbench compiles the `.txa` to `.anm`. It handles root motion. Use it for the grip.
- It is the only validated route for full-body and action animations: Route C is not valid for full-body action animations (jam, unjam, melee). The strike animation confirmed that full-body work goes through Route A (measured 2026-06-30; `weapon-anim-authoring-viewer.md`).
- The full recipe that was run and confirmed in game (measured 2026-06-30):
  1. Author in the viewer → animation JSON (for example `strike_retimed.json`).
  2. Convert the per-frame, per-bone viewer state to FK **world** space with a dump script (`dump_viewer_world.py <anim.json> <world.json>`; the script is not shipped with Agentic-Z). The world-space JSON it writes is the schema under "The deliverable", item 2.
  3. `blender --background --python viewer_to_txa_via_plugin.py -- <world.json> <out.txa> ADD <spine_up_bones.json>` (a bridge script, not shipped with Agentic-Z). It poses the plugin rig and calls the plugin's real Blender **export operator** to write the `.txa`; that operator handles all of the convention.
  4. **Workbench (GUI, a step only a person does)**: Resource Manager → right-click the `.txa` → "Register & Import" the first time, "Reimport Resource" after that → produces `.anm` and `.anm.meta`.
  5. Optional command-line post-process for corrections the plugin does not expose (bone exclusion, notetracks): `DayZATool --extract-anim` → `.seanim` → Python edits with `skills/dayz-animation-pipeline/scripts/seanim_writer.py` → `DayZATool --generate-anim` → final `.anm`. This step needs no GUI.
  6. Deploy the `.anm` to `<Mod>/animations/` and rebuild the PBO. File patching does not reload an `.anm`.
- Used for: full-body action animations (the jam and unjam strike) and authoring the weapon **grip** itself. Route A is mandatory for the grip (measured 2026-07-05).
- Status: **closed and confirmed in game** for the strike animation's body, head and weapon staying in the hand (measured 2026-06-30). The loop and unjam fixes below were built and deployed through this route; the **final in-game confirmation of the last polish pass (loop, micro-jerk and thumb) is still pending**, because the in-game test of 2026-07-02 was interrupted.
- Tool and version: `DayZAnimationPlugin_MAINTAINED`, cloned wherever the user keeps it. It needs **Blender 4.4+ or 5.x** (the confirmed runs used Blender 5.1). See "Blender-side conventions" below.
- A pure-Python `.txa` writer (`pose_to_txa.py`, not shipped with Agentic-Z) was tried and does **not** close the root frame correctly (the body lies down). Do not write a `.txa` by hand; go through the plugin (measured 2026-06-29).

### Route C: `.seanim` (CLI) → DayZATool → `.anm`. Weapon-bone and partial tracks only

- Definition (`weapon-anim-authoring-viewer.md`): `skills/dayz-animation-pipeline/scripts/seanim_export.py` → `.seanim` → `DayZATool --generate-anim <f>.seanim 100` → `.anm`. Rotations and rest only. The viewer → SEAnim quaternion convention `(-vy,-vz,vx,vw)` is exact on fingers, but `LeftHand` does not obey it (a separate wrist process), so do not use Route C for the support-hand wrist. Use Route C only for weapon-bone and partial tracks.
- Viewer quaternions are rig-local and point along +Y; DayZ's bone-local frame points along +X. A Route C export is not guaranteed to be in DayZ's exact convention, so the in-game test is the gate.
- DayZATool does not read `.txa` at all. It has only `--extract-anim`, `--generate-anim` and `--extract-mdl`, all on `.seanim` (measured 2026-06-29).
- Status: used to deploy a first test unjam animation straight onto the custom weapon for a manual in-game test (2026-06-29); replaced by Route A once the full-body strike animation showed Route C is not enough for anything beyond isolated weapon-bone channels.
- Still the right tool for baking hand-authored finger and thumb corrections into an already exported `.anm` without running Workbench again. It was used for the final thumb-curl fix on `strike.anm` (2026-07-02).

---

## Interface point for this skill

**This section matters most: what this skill must produce so it plugs into Route A without deriving anything again.**

### The recommended artifact: pose the plugin's own rig, export with the plugin's own operator

Every animation in this pipeline that was confirmed in game was made by loading the plugin rig (`_AssetSamples\JD_Master_Rig (No IK Bones).blend` under the `DayZAnimationPlugin_MAINTAINED` folder, armature object `_DayZ_Character`, 151 bones; `weapon-anim-blender-complete.md`), keyframing it, and letting the plugin's **own** export operator (`export_scene.txa`, `ExportTxa.py`) write the `.txa`. That operator is what handles all of the convention correctly: `mtxFix`, the root frame, the per-component swaps and the quaternion negation. A round trip through the plugin measured a median error of 0.0° (2026-06-29).

**The dump and bridge scripts of Route A exist only to bring poses from a tool that is not Blender (the viewer) into Blender. A skill that drives Blender directly through the Blender MCP server does not need that bridge.** It can pose `_DayZ_Character` with `bpy` calls (through `execute_blender_code`) and call the plugin's `bpy.ops.export_scene.txa(...)` directly. That is a strictly shorter path to the same artifact Route A already produces and Workbench and the rest of the pipeline already consume. The rule that follows: **do not invent a JSON interchange format. Pose the plugin rig and call its export operator.**

### The deliverable, in priority order

1. **Preferred**: a Blender scene where `_DayZ_Character` (or the vanilla-named equivalent from `P:\DZ\anims\cfg\skeletons.anim.xml`) has a keyframed Action, made with the plugin registered, then exported through **File > Export > DayZ Animation (.txa)** (`export_scene.txa`) with the right **Type** for the kind of animation (`FB`, `IK1H`, `IK2H` or `ADD`; see "Blender-side conventions"). The handoff artifact is the `.txa` file plus a note of which `.anm` it should become. The user's remaining step is Workbench "Register & Import" (or "Reimport Resource"), two clicks in the GUI, then the wiring, which `dayz-animation-pipeline` owns (see below).
2. **Fallback, when posing through the Blender MCP server is impractical for a track and the user has the Route A bridge script**: write the **world-space JSON** that script reads, so it runs unchanged. The schema:
   ```
   {
     "fps": 30,
     "order": ["Bone1", "Bone2", ...],       // bone names, any order (the script depth-sorts parent-first)
     "parent": {"Bone2": "Bone1", ...},       // bone -> parent bone name map
     "frames": [
       { "Bone1": {"q": [x,y,z,w], "p": [px,py,pz]}, ... },   // per frame, per bone WORLD-space quat + pos
       ...
     ]
   }
   ```
   The quaternion field order is **[x,y,z,w]**. The script converts to Blender's `Quaternion(w,x,y,z)` constructor order itself (`Quaternion((q[3],q[0],q[1],q[2]))`), so do not put Blender-order quaternions into this JSON.
3. **Only for isolated weapon-bone or partial tracks (never full body, never the support-hand wrist)**: the viewer animation JSON that Route C reads. The schema:
   ```
   {
     "fps": 30,
     "bone_order": ["Bone1", ...],
     "keyframes": [0, 15, 40, ...],           // frame indices that are authored keyframes
     "frames": [
       { "bones": { "Bone1": [x,y,z,w], ... } },   // per frame, per bone LOCAL (rig-frame) quaternion
       ...
     ]
   }
   ```
   This feeds `python skills/dayz-animation-pipeline/scripts/seanim_export.py --anim <json> --rig <rig.json> --out out.seanim`, where `<rig.json>` is the rig JSON the animation was authored on (the exporter detects from its rest offsets whether it is the plugin rig or the BI FBX rig). The user then runs `DayZATool --generate-anim out.seanim 100`. DayZATool is a closed .NET program for Windows with a command line and no GUI step; an agent on a Windows host can run it headless (`skeletal-anm-enfusion.md`, 2026-09-29).

### What this skill never does (owned downstream)

- It never writes `.asi` wiring, the `AddItemInHandsProfileIK` or `AddItemBoneRemap` Enforce Script calls, `config.cpp` or `model.cfg`. That is Layer 1 and Layer 3 of `dayz-animation-pipeline` (see the do-not-duplicate list below).
- It never claims to have run Workbench or the in-game test. It mentions DayZATool as run only when it ran it and read the file it wrote (`tooling-and-walls.md`: never suggest the agent ran Workbench when it did not).
- It never derives the `mtxFix` and quaternion-swap math again from scratch. That math is calibrated (see "Coordinate conventions"), and deriving it again has cost several wasted sessions.

---

## Skeleton and exclusion rules

### Checked on `P:\`

The survivor's animation skeleton is the bone list named `player_testing.xob`:

| What | Vanilla line |
|---|---|
| The `player_testing.xob` bone list starts | `P:\DZ\anims\cfg\skeletons.anim.xml:110` |
| The player workspace previews the model `player_testing.xob` | `P:\DZ\anims\workspaces\player\player_inventory\player_inventory.aw:12` |
| `EntityPosition` (the root that carries movement) | `P:\DZ\anims\cfg\skeletons.anim.xml:113` |
| `RightHand_Dummy` | `P:\DZ\anims\cfg\skeletons.anim.xml:115` |
| `Pelvis` | `P:\DZ\anims\cfg\skeletons.anim.xml:120` |
| `RightForeArmRoll`, listed just before `RightHand` | `P:\DZ\anims\cfg\skeletons.anim.xml:146` |
| IK helpers `RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget` | `P:\DZ\anims\cfg\skeletons.anim.xml:149-151` |
| IK helpers `LeftForeArmDirection`, `RightForeArmDirection` and their `...DirectionOrigin` pair | `P:\DZ\anims\cfg\skeletons.anim.xml:154-157` |
| Carpal bone `LeftHandRing` | `P:\DZ\anims\cfg\skeletons.anim.xml:208` |
| Carpal bone `LeftHandPinky` | `P:\DZ\anims\cfg\skeletons.anim.xml:225` |
| Carpal bone `RightHandRing` | `P:\DZ\anims\cfg\skeletons.anim.xml:230` |
| Carpal bone `RightHandPinky` | `P:\DZ\anims\cfg\skeletons.anim.xml:247` |
| `Weapon_Root`, then `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt`, `Weapon_Bone_01` to `Weapon_Bone_06` | `P:\DZ\anims\cfg\skeletons.anim.xml:254-264` |

The list holds 172 `<bone>` entries (lines 112 to 302). The file lists names only, not parents, so parent claims below are not checked here.

Two vanilla unjam clips were read for their track names: `P:\DZ\anims\anm\player\reloads\ak101\p_erc_unjam_ak101_ras.anm` and `P:\DZ\anims\anm\player\reloads\pm73\p_erc_jam_pm73_ras.anm` (both binary). The AK-101 clip names 73 bones, from `Spine` to `Weapon_Bone_06`:

- It has no `EntityPosition`, no `Pelvis` and no leg bone. Vanilla action clips are spine-up.
- It has no IK helper bone (`...Origin`, `...Direction`, `LeftHandIKTarget`).
- It does carry `LeftHand_Dummy` and `RightHand_Dummy`, the four carpal bones `LeftHandRing`, `LeftHandPinky`, `RightHandRing` and `RightHandPinky`, and the ten weapon bones `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt` and `Weapon_Bone_01` to `Weapon_Bone_06`.
- Its events include `Weapon_CanUnjam_Start`, `LoopStart`, `Weapon_CanUnjam_End`, `LoopEnd`, `Weapon_BulletEject`, `Weapon_Cocked` and `Weapon_Unjammed`. The PM73 clip has the same shape.

### Rules (tool behaviour and measured results; not yet checked on `P:\` unless a line says so)

- **The target skeleton is always `OFP2_ManSkeleton`.** Bone names must match **exactly** (PascalCase with underscores), or the RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone silently does not animate (`player-skeleton.md`, `skeletal-anm-enfusion.md`, `weapon-anim-blender-complete.md`). On `P:\`, `OFP2_ManSkeleton` is the skeleton name stored inside the character models (for example `P:\DZ\characters\tops\shirt_m_new_anim_system.p3d`); the bone names animation uses are the `player_testing.xob` list above.
- **`RightHand_Dummy`** is the weapon anchor; the whole weapon is its child. In the strike animation, a **full-body action animation**, animating `RightHand_Dummy` was a bug: it overrode the grip of the ikpose and the weapon flew to the character's back. The fix was to leave `RightHand_Dummy` out of the `.anm`, so the ikpose holds the weapon (measured 2026-06-30; `player-skeleton.md` says what the dummy is and does). The vanilla unjam clips above do carry a `RightHand_Dummy` track, so the engine accepts one with the right values; leaving it out is the tested fix when you do not have vanilla-derived values.
- **Spine-up exclusion (action animations only)**: vanilla action animations (reload, fire, chamber, jam) leave out `EntityPosition`, `Pelvis` and the leg chain; the idle and locomotion layer supplies those. Including the rig's absolute root and pelvis orientation makes the character "flop" (lie down or clip underground in game; measured 2026-06-30). The vanilla clips above confirm the spine-up bone list. `seanim_export.py` applies the same mask with `--rest-pose`: it cuts the emitted bone list down to the bones present in a vanilla reference SEAnim of the same slot.
- **`Weapon_*` bones need correct values or must be dropped, never placeholder values.** `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet` and `Weapon_Bone_01` to `Weapon_Bone_06` are real skeleton bones the player rig drives (see the table above). If a viewer or tool exports them with placeholder or default values instead of the real vanilla-derived transform, the weapon mesh visibly stretches. The cause was measured with a DayZATool extraction, not guessed (2026-06-30): `Weapon_Bone_01..06` collapsed to `(0,0,0)` against vanilla `(-11.43,0.79,-2.48)`, about 11.7 cm of displacement, which is the stretched weapon mesh. The fix was to drop all 10 `Weapon_*` bones from that animation (72 → 62 bones), accepting that the bolt does not move during that one action.
- **IK helper bones must not be keyframed for non-IK (full-body or additive) animations.** `LeftHandOrigin`, `RightHandOrigin`, the `...ForeArmDirection` bones, `LeftHandIKTarget` and the rest are missing from the plugin's "No IK Bones" rig until "Tools > Add Survivor IK Bones" is run; the plugin's importer silently drops their tracks when it was not run first, and stray keys on them corrupt full-body and additive exports (`weapon-anim-blender-complete.md`). These bones are in the vanilla animation skeleton (table above), but the vanilla action clips do not key them.
- **Hands are parented to the twist (roll) bone, not the raw forearm.** In Blender the real parent of `RightHand` is `RightForeArmRoll`, not `RightForeArm`. Skipping the roll bone when computing a wrist's local quaternion from world space leaks rotation into the wrist and can drop the fingers by up to about 11 cm. Checked by drawing in-game bone positions as an overlay, not by quaternion theory (`player-skeleton.md`), and reproduced the same way in the viewer (measured 2026-06-29).
- **IK helpers do not roll the wrist.** Rotating `LeftHandIKTarget`, `LeftHandOrigin` and the like does not change the hand or wrist orientation in game. In an IK pose, turning the raw `LeftHand` bone was absorbed by the engine's IK as well on a custom weapon without grip parity (4 ikpose variants, compared by RMS pixel difference); what the pose drives visibly is the finger curl. To change how the support hand sits, match the weapon's geometry to a reference clip whose hand already sits that way (measured in game 2026-06-17; `player-skeleton.md`, `weapon-in-hands.md`).
- **A weapon-states `.anm` has 2 to 4 keys per channel, not a fixed "exactly 3 frames"** (closed, open, jammed). Workbench trims near-duplicates (`anim-graph.md`; `weapon-in-hands.md` has the table: the AKM weapon-states clip has 2 distinct frames, not 3).

---

## Coordinate conventions

All of this section is plugin, tool and measured behaviour; not yet checked on `P:\`.

### Route A (`.txa` through the plugin): `mtxFix` and the component swap

- Axis fix (`mtxFix`): a **+90° rotation about Z that swaps Blender's X and Y axes**, matrix `[[0,1,0],[-1,0,0],[0,0,1]]`, applied the same way in the plugin's `ImportTxa.py`, `ExportTxa.py` and `ExportTxo.py` (plugin source `ImportTxa.py:141` and `ExportTxa.py:194,228`; `weapon-anim-blender-complete.md`).
- The component swap in the `.txa` text is a **separate** transform from the axis fix; do not merge the two. Translation and scale are written as **X Z Y**; the quaternion is written as **(x, z, y, -w)**; a final `FQuaternion(-w,-x,-y,-z)` is also applied on export (plugin source `Txa.py:480-496,550-566`, `DayzAnimUtils.py:35-39` and `ExportTxa.py:250`; `weapon-anim-blender-complete.md`).
- The same formula was confirmed against a real calibration pair, not only read from the plugin source (measured 2026-06-29): `rot_txa = mtxFix·viewer_local·mtxFixᵀ`, quaternion in the file `(x,z,y,−w)`. **The root frame does not close correctly in a pure-Python implementation** (the plugin rig has `EntityPosition→Pelvis`, the `.txa` has `Scene_Root→{EntityPosition,Pelvis}`). This is why Route A must go through the real plugin in Blender, not a hand-written `.txa` writer.
- Unit scale: `fUnitScale` defaults to 1.0 in the plugin; assume 1.0 until a difference shows up (not verified).

### Route C (viewer JSON → `.seanim`): calibrated, exact

- *Scope (2026-10-02):* exact for the plugin rig, the rig of the calibration pair. The BI FBX rig that `skills/dayz-animation-pipeline/scripts/build_rig_dayz.py` builds has the plugin rig's bone frames turned 90° about Z; through this formula every one of its bone frames comes out turned 90° (its rest offsets land 44 to 90° off vanilla's, median 90°). The shipped `skills/dayz-animation-pipeline/scripts/seanim_export.py` reads the rig and gives the FBX rig `(−x,−z,−y,w)` and `(x,z,y)` instead, derived offline and played in game on 2026-10-02 for one `LeftArm` pose, which this formula sent out to the side instead of forward (`weapon-anim-authoring-viewer.md`, "Route C bone-frame maps, per rig"). In game, this route played one full-body action wrong (the strike animation; see the status of Route C above).
- Rotation: viewer-local quaternion `(x,y,z,w)` → SEAnim `(−y,−z,x,w)`. Position (rest offset): `(x,y,z)` → `(y,z,−x)`, in **centimeters** (rig meters × 100). Calibrated against a real `.anm` (the plugin's sample SVD fire clip: its `.txa` through the plugin against the `.anm` DayZATool extracted): **73 bone and frame pairs, exact to 0.00° globally**, DayZATool round-trip error 0.0007° (measured 2026-06-29). `weapon-anim-authoring-viewer.md` states the same formula as `(-vy,-vz,vx,vw)`, where "v" marks the viewer components.
- The formula is verified **exact on fingers**, but **`LeftHand` (the raw wrist bone) does not obey it**: a separate wrist process that is not solved yet. So never use Route C to author the support-hand wrist orientation (`weapon-anim-authoring-viewer.md`).
- The exporter hard-codes `UNIT_CM = 100.0` (rig meters to SEAnim centimeters, checked against the finger offsets of an AKS-74U reference clip).

### General Blender ↔ DayZ axis convention (geometry and rig import, not only animation export)

- Blender Z-up → viewer Y-up: `(x', y', z') = (x, z, −y)`, for the animation viewer's rig alignment (`weapon-anim-authoring-viewer.md`). It is right there because it is a proper rotation (det +1) into the viewer's **right-handed** Three.js frame. It is not DayZ space, which is left-handed, so viewer-frame coordinates (`rig_dayz.json`) written into a p3d as they are land mirrored. The step into DayZ carries a det −1 map: the position flip game model space → viewer `(x, y, −z)`, validated in game (`weapon-in-hands.md`), and Route C above, which maps positions with `(y, z, −x)` (det −1) and quaternion vectors with `(−y, −z, x)`, the axial-vector form of the same reflection, for the plugin rig; the FBX rig's `rig_dayz.json` takes `(x, z, y)` and `(−x, −z, −y)` (2026-10-02). For geometry, Blender → DayZ is `(x, y, z) → (x, z, y)`, det −1 (Rule 12 of the dayz-model-pipeline skill, in-game test 2026-10-01). The det +1 map `x'=x, y'=z, z'=-y` is the viewer map, not a DayZ map; used for DayZ geometry it mirrors.
- **FBX rig scale trap** (it has bitten a custom big-infected character and this pipeline): the official BI rig FBX imports with the **mesh at object scale 0.01** and the **armature at scale 1**. They live in separate spaces (armature in cm, T-pose, origin at the pelvis; mesh in meters, origin at the feet). Reading bone world positions naively puts the skeleton about 35x off the mesh. The fix is to bind again in one consistent space: derive a uniform scale from a known correspondence (for example wrist-bone X against half the mesh width gives `s≈0.0101`), translate to align the bounding-box centers, then apply the Y-up axis fix. Full recipe in `weapon-anim-authoring-viewer.md`. **This FBX rig bug is why the pipeline uses the plugin rig (no scale bug) as the authoring rig instead of the raw BI FBX.**
- Game model space → viewer (Three.js): position `(x, y, −z)` (a z flip: Enfusion is left-handed, Three.js is right-handed). The naive quaternion z flip `(−x,−y,z,w)` renders **mirrored**; rebuild the pose from measured **positions**, not from a flipped quaternion (`weapon-in-hands.md`).
- **FPS**: the engine default, assumed everywhere in this pipeline, is **30 fps**. Set the exporter option "Override Fps" to 30 (0 means use the scene fps). 20 to 25 fps for a slower, deliberate feel also works, and so does 60 (`weapon-anim-blender-complete.md`).
- **Scale is never keyed and is ignored.** DayZ ignores bone scale. The plugin's Scale Keys export option is off by default, and scale is dropped when the file is binarized even if the `.txa` holds it (`weapon-anim-blender-complete.md`).

---

## Loop metadata

This mechanism is solved, not obvious, and was expensive to find (3 rebuild cycles before the root cause). Apply it correctly the first time for any hold action that a script timer ends. Unjam is the concrete case; the mechanism is the same for any continuous action that plays until script stops it.

### The vanilla unjam timer, checked on `P:\`

- The unjam sub-machine sets `m_jamTime = 5.0` when it is entered: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:218`.
- Each update of `WeaponUnjamming_Start` adds `dt` to `m_dtAccumulator`: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:29`.
- Only when `m_dtAccumulator >= m_jamTime` does it go on: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:38`.
- It then starts the `UNJAMMING_END` action and posts `WeaponEventUnjammingTimeout`: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:41-42`.
- That event moves the machine from `m_start` to `m_eject`: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:199`.
- Entering that state is what calls `SetJammed(false)`: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:87`.
- On PC, letting go of the key before the timer ends starts `UNJAMMING_INTERRUPT` and the weapon stays jammed: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:56`.
- On every update the player's inventory (`HandleWeaponEvents`) asks the weapon command `IsActionFinished()`: `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:396`.
- When the action is finished it checks `IsWaitingForActionFinish()` on the weapon: `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:398`.
- When the current state is not waiting, it sends `WeaponEventHumanCommandActionAborted`: `P:\scripts\4_world\systems\inventory\dayzplayerinventory.c:414`.
- `WeaponUnjamming_Start` does not override `IsWaitingForActionFinish`, and the base answer for a state with no sub-machine is false: `P:\scripts\4_world\entities\firearms\fsm\states\weaponstatebase.c:152`.
- `LoopEnd` is an event name in the player event table: `P:\DZ\anims\workspaces\player\player_eventtable.ae:35`.
- `LoopStart` is the next entry: `P:\DZ\anims\workspaces\player\player_eventtable.ae:36`.
- The notetrack `Weapon_Unjammed` is registered as a weapon event: `P:\scripts\3_game\human.c:1096`.
- It becomes `WeaponEventAnimUnjammed`: `P:\scripts\4_world\entities\firearms\fsm\events.c:272`.
- That event (`__uj_`) moves `m_eject` on to `m_chamber` when the weapon has ammo: `P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:201`.
- `Weapon_CanUnjam_End` is registered too: `P:\scripts\3_game\human.c:1088`.
- So is `Weapon_CanUnjam_Start`: `P:\scripts\3_game\human.c:1089`.
- They become `WeaponEventAnimCanUnjamEnd` and `WeaponEventAnimCanUnjamStart`: `P:\scripts\4_world\entities\firearms\fsm\events.c:264-265`. No transition of the unjam sub-machine uses either one; its transitions are the lines from `:199` to `:207` of `weaponunjamming.c`.

### What follows for the clip (measured on the strike animation; not yet checked on `P:\`)

- **Root cause chain when `LoopStart` and `LoopEnd` are missing.** The unjam action is driven by the timer, not by a notetrack. A `.anm` with no loop section **ends** at its last frame (about 1.7 s for a 51-frame animation). `IsActionFinished()` turns true, the unjam start state is not waiting for that, so the machine gets the abort event and goes straight back to the jammed state. The continuous action fires again, and the 5 s timer **never accumulates**, because the animation never stays in progress long enough. Vanilla avoids this because its jam animation has `LoopStart` and `LoopEnd` (frames 22 and 200 in `p_erc_jam_pm73`, measured with a DayZATool extraction), so the command loops and `IsActionFinished()` stays false until the timer ends it (measured 2026-07-02). The vanilla half of this chain is the list above.
- **Notetrack format**: `LoopStart` and `LoopEnd`, written as `Name||-1`, identical to what a DayZATool extraction of the vanilla clip gives (measured 2026-07-02).
- **Loop length rule**: the loop must last **at least as long as the engine timer (5 s for unjam); about 6 s is recommended**. The timer then fires before the loop completes one cycle and the wrap-around is never seen. This is what vanilla does (vanilla loop lengths seen: 5.9 to 6.9 s, always above the 5 s timer). So the loop does not have to be a perfectly closed cycle when it is long enough; a shorter closed loop also works but is harder to author cleanly. An unjam animation with no `LoopStart` and `LoopEnd` aborts halfway and the weapon never unjams (measured 2026-07-02).
- **The outro after `LoopEnd`** carries the notetrack that resolves the state (for example `Weapon_Unjammed`), timed near its end; the vanilla outro is about 2.5 to 3.2 s.
- **The micro-jerk lesson (not obvious, cost a full session)**: the engine leaves the loop from **whatever pose is current when the timer fires**, not necessarily the pose authored at the `LoopEnd` frame. If the outro's start pose differs from the loop's late-cycle pose there is a visible snap. The practical fix: from a frame well before `LoopEnd` (for example from about frame 140 in a loop of about 195 frames), settle the moving part into the "ready" pose and hold it through `LoopEnd`, so the pose already matches the outro's start wherever the timer fires (measured 2026-07-02).
- **A first attempt that did not fix the loop** (kept so it is not tried again): adding only mid-animation notetracks (`Weapon_CanUnjam_Start`, `Weapon_CanUnjam_End`, `Weapon_Unjammed`) with no `LoopStart` and `LoopEnd`. They survived the `.anm` round trip, but the loop problem stayed exactly as it was (measured 2026-07-01). This agrees with the vanilla scripts: the unjam transitions do not consume `Weapon_CanUnjam_Start` and `Weapon_CanUnjam_End` at all (the last line of the list above).
- The fps convention for loop-frame math is the same 30 fps default as above.

---

## What `dayz-animation-pipeline` already covers (do-not-duplicate list)

Treat all of the following as already owned and point to them; do not author them again. All of these files are in `skills/dayz-animation-pipeline/`.

| Reference file | Owns | Why this skill must not duplicate it |
|---|---|---|
| `skills/dayz-animation-pipeline/SKILL.md` | The top-level routing table (object, skeletal, vehicle rider, anim graph), the definition of the Layer 1/2/3 seam, the one-animation-mod wall (graph replacement only; weapon animations do not conflict) | It is the front door. This skill should be reachable **from** that routing table (a row pointing here), not replace it. |
| `skills/dayz-animation-pipeline/references/config-driven-animation.md` | The full `model.cfg` `class Animations` property reference (type, source, selection, axis, begin/end, minValue/maxValue, sourceAddress, angle0/1, offset0/1, hideValue), `class AnimationSources` in `config.cpp`, the full list of engine `source` values, the `SetAnimationPhase` and `GetAnimationPhase` script interface | This is Layer 1 (config-driven object, door and lever animation), unrelated to skeletal character and weapon animation. A Blender authoring skill for skeletal animation never touches it. |
| `skills/dayz-animation-pipeline/references/item-ik-and-hide.md` | Pattern A (reuse a vanilla `.anm` for carry IK on heavy items through `AddItemInHandsProfileIK` with a 4-argument call and no weapon states) and Pattern B (hide on attach through a `hide`-type animation) | Both patterns are "reuse vanilla, author nothing new", the opposite of what a Blender authoring skill does. |
| `skills/dayz-animation-pipeline/references/skeletal-rtm.md` | The legacy RTM route (Arma era, `FBXToRTMGui.exe`, Arma3ObjectBuilder) | RTM is legacy, reverse-engineered and **not** the route for player and weapon animations; it is the most common wrong turn (`weapon-anim-blender-complete.md`, `tooling-and-walls.md`). This skill should warn against it, not implement it. |
| `skills/dayz-animation-pipeline/references/skeletal-anm-enfusion.md` | The overview of the Enfusion `.txa`, SEAnim and `.anm` pipeline, the two-route framing, where to get the tools | It owns "which route for what"; the Route A and Route C summary above agrees with it. |
| `skills/dayz-animation-pipeline/references/player-skeleton.md` | The full bone catalog by zone (core and spine, legs, arms, fingers, IK helpers, weapon bones, face, misc and legacy) | Point to this catalog instead of listing bone names again; it already carries the twist-bone parent trap and the `RightHand_Dummy` facts cited above. |
| `skills/dayz-animation-pipeline/references/anim-graph.md` | The state machine and `CMD_*` command catalog, `#Var` declarations, the ASI `$animsetinstance` structure, the player ASI catalog, the weapon-state path convention, the "reload is not additive" correction, the Workbench Animation Editor `#eventtable` trick, the minimal creature-graph workflow | This is the wiring and graph layer downstream of any `.anm` this skill produces. Point here for anything about **how** an `.anm` gets selected at runtime. |
| `skills/dayz-animation-pipeline/references/weapon-in-hands.md` | The full grip and ADS memory-point contract (`eye`, `usti hlavne`, `konec hlavne`, `bolt_axis` and so on), the grip validator tool, the "geometric parity is the grip fix" doctrine, the finding that ikpose does not roll the wrist, the live bone-dump technique for poses the engine IK resolves | This is the definitive answer to "why does the weapon look wrong in the hand". A Blender authoring skill defers to it and does not derive grip fixes again. |
| `skills/dayz-animation-pipeline/references/weapon-anim-authoring-viewer.md` | **The existing Layer 2 interactive authoring pipeline itself** (viewer, IK, keyframe timeline, both export routes, the viewer feature set as of 2026-07-05) | **The file with the highest overlap risk.** It is "a blender-animation skill" in spirit, built as a custom Three.js viewer instead of live Blender. This skill's pitch is "the same outcome, driven inside real Blender through MCP", not a second, parallel viewer. |
| `skills/dayz-animation-pipeline/references/weapon-anim-blender-complete.md` | The most complete single reference: the Blender version matrix, add-on install, rig roster, IK-helper setup, the craft of each animation type (ikpose, fire, weapon states, reload, aim space, magazine tracking), `.txa` export types and text format, Workbench compile traps, the full `config.cpp`, `.asi` and Enforce Script wiring contract (`AddItemInHandsProfileIK`, `AddItemBoneRemap`, the 42 `WeaponOperations.*` state names), mod folder scaffolding, deploy, packaging and troubleshooting | Point to it for anything mechanical about the Blender plugin (export types, event markers, `.txo`) instead of explaining it again. |
| `skills/dayz-animation-pipeline/references/vehicle-rider-ik-pose.md` | The IK-from-anchors solver for seated vehicle poses (2-bone analytic IK plus a straight spine, 21 solved joints), the rest-pose calibration requirement, the frame-of-reference caveat | A different domain (vehicle seating, not weapon or action animation), but the same rest-pose calibration and coordinate-frame caveats apply; point to the solver math, do not copy it. |
| `skills/dayz-animation-pipeline/references/handlebar-and-steering-config.md` and `skills/dayz-animation-pipeline/references/dual-entry-action-pattern.md` | Layer 1 config-driven rotation of vehicle parts, and a scripted pattern that snaps the get-in to a seat side | Out of scope for a Blender animation skill (config and script layer, not authoring). |
| `skills/dayz-animation-pipeline/references/selection-painter-for-actions.md` and `skills/dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` | Painting and writing `.p3d` named selections for action raycasts, and the py3d traps met doing it | The model-editing side (adding the selections and axes an animation drives). The dayz-p3d-inspector and dayz-model-pipeline skills own it, not an animation authoring skill. |
| `skills/dayz-animation-pipeline/references/blender-authoring.md` | **The "Layer 2 programmatic Blender authoring" notes**: the headless `bpy` keyframing recommendation, bone-name discipline, FPS and scale, coordinate caveats | **The second highest overlap risk.** It is the headless Blender authoring guidance this skill extends. Where it leaves the axis conversion open, the measured answers are in "Coordinate conventions" above (`mtxFix`, the Y-up fix, the Route A and Route C formulas). |
| `skills/dayz-animation-pipeline/references/tooling-and-walls.md` | The canonical tool inventory table, the two-format split (RTM against `.anm`), the walls (one animation mod, the closed-format caveats of RTM and `.anm`), the signing and deploy pointer, the "what to hand the user" checklist | The handoff message of this skill follows that checklist; it does not invent its own handoff format. |
| Sibling skill `mixamo-retarget` | Retargeting Mixamo or FBX mocap onto any armature (including the DayZ skeleton) through the Blender MCP server, fuzzy bone matching, the rest-pose mismatch caveat | It already drives Blender through the same MCP tool (`execute_blender_code`) this skill uses, and is the closest precedent for a live Blender MCP session that touches the DayZ skeleton. Its output feeds Layer 2 as a keyframe **source**, not as a shortcut around the rest of the pipeline. Status: experimental, not validated on a fixture. |
| The dayz-model-pipeline skill, `references/animations.md` | An independent, fairly complete restatement of the same `model.cfg`, `CfgSkeletons`, `CfgModels` and `class Animations` syntax as `config-driven-animation.md` (rotation, translation and hide types, axis, minValue/maxValue, angle0/1) | **An overlap between two other skills**, not something to copy a third time. If this skill ever has to mention config-driven animation in passing, point at `dayz-animation-pipeline` (the animation skill) as canonical, not at the model pipeline. |

---

## Blender-side conventions

Plugin and tool behaviour; not yet checked on `P:\`.

- **The Blender version depends on the plugin build, and the metadata lies. Check the code, not `bl_info`.** The original build, `DayZAnimationPluginDemo`, needs **Blender 3.6.8 to 4.0** (it breaks on 4.1 and later with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`). The **maintained build**, the one this pipeline uses, needs **Blender 4.4+ or 5.x** (it calls `action.fcurve_ensure_for_datablock`, a 4.4+ API, and a helper named `generate_fcurves_bl51`), yet its own `bl_info` declares `'blender': (2, 80, 0)` (`weapon-anim-blender-complete.md`, `tooling-and-walls.md`). The confirmed runs used **Blender 5.1** (2026-06-30).
- **Install is a manual folder copy, not a zip.** Copy `BlenderPlugin/DayzAnimationTools` into `%AppData%\Roaming\Blender Foundation\Blender\<version>\scripts\addons\DayzAnimationTools`, then enable "DayZ Animation Tools" in Preferences > Add-ons. Blender's "Install from file" does not work on this download (`weapon-anim-blender-complete.md`).
- **Where the plugin lives**: wherever the user cloned `DayZAnimationPlugin_MAINTAINED`. Both the add-on and its `_AssetSamples` rig and pose blends are under that folder. Ask the user for the folder; do not guess it.
- **The rig that is the source of truth**: `_AssetSamples\JD_Master_Rig (No IK Bones).blend` is `OFP2_ManSkeleton` with the vanilla bone names and custom display shapes on the main bones. This is the rig to pose (`weapon-anim-blender-complete.md`). A second candidate, the raw BI FBX `animation_rig_character.fbx` (114 bones), has the scale-space bug described under "Coordinate conventions"; prefer the plugin rig (`weapon-anim-authoring-viewer.md`).
- **"Add Survivor IK Bones" (`import_scene.addsurvivorik`) must run before authoring any IK or grip pose.** It creates `LeftHandOrigin`, `RightHandOrigin` and the `...ForeArmDirection` bones and adds Blender IK constraints on `LeftHand` and `RightHand` with baked pole angles **−127.9° (left) and +45.3° (right)**. Importing or authoring an IK `.txa` without it silently drops those bone tracks (the importer prints a warning). The other way round, never key these helper bones for a non-IK animation (`weapon-anim-blender-complete.md`).
- **The Export Type carries real weight; it is not cosmetic.** `FB` (Full Body: emotes only; it injects a `Scene_Root`), `IK1H` and `IK2H` (grip ikpose, a single keyframe; the plugin restricts the export to the IK bone list by itself, so do not select bones first), `RL` (rarely used; treated as `ADD` in practice), `ADD` (reload, fire, chamber, jam, weapon states; use "Selected Bones Only"). Exporting **all** bones on a reload or action animation makes the character "turn into a meatball" in game (`weapon-anim-blender-complete.md`).
- **Never key scale.** The engine ignores it (see "Coordinate conventions").
- **Workbench silently trims consecutive keyframes that are nearly identical.** An authored hold can collapse to fewer frames than intended. Author holds with real keyframe differences, and always keep the source `.txa` next to its `.anm`, because Workbench can edit an `.anm` again only when the `.txa` is present (`weapon-anim-blender-complete.md`).
- **Never assume which way the rig faces. Measure it.** A hard-coded assumption that the character faces `+X` was wrong. The plugin rig faces **−Z** when aimed (measured from the hip and shoulder forward vectors: `fwdHip=(0.75,0,-0.66)`, `fwdShoulder=(0.57,0,-0.82)`), and the bug was diagnosed as "roll" for a full session before it was found to be "yaw" (measured 2026-06-29). The general lesson: measure the rig's forward before writing any orientation fix.
- **The character import scale `f=0.7901` is not part of this pipeline.** It belongs to the mesh import of one custom big-infected character, not to weapon or action animation authoring. Do not apply it here; character import is the job of the dayz-characters skill.

---

## Open questions

Not verified. Flag them to the user or check them again; do not guess.

1. **Character import and rigging are not covered here.** Read the dayz-characters skill for those.
2. **The `f=0.7901` and `T2=(−x,z,y)` scale and orientation convention** does not come from weapon animation work. It appears to be a **mesh-import and rig-binding scale fact for one character model** (a custom big-infected character), not a general animation authoring convention. Probably irrelevant to this skill; confirm it before using it.
3. **The SEAnim add-on for Blender (`io_anim_seanim`) has not been run or validated here.** All work tested in game went through the plugin (`.txa`) or through the Python `seanim_writer.py`, which is a standalone reader and writer, not a Blender importer (`tooling-and-walls.md` lists the add-on).
4. **The Route C calibration formula (`(-vy,-vz,vx,vw)`, cm scale) was calibrated against exactly one weapon and animation pair** (the plugin's sample SVD fire clip, 73 bone and frame samples). It is global across bones and exact, but check it again if the plugin build or the Blender version changes, because the formula depends on the plugin's `mtxFix` and component-swap internals. *(2026-10-02: global across bones, but tied to the rig: it is the plugin rig's map; see the Route C scope note above.)*
5. **The final in-game confirmation of the fully fixed `strike.anm`** (loop, seamless ping-pong, micro-jerk fix, thumb curl) is still pending; the test of 2026-07-02 was interrupted. "Route A: closed, confirmed in game" above covers the earlier body, head and weapon-grip fix of 2026-06-30, not the loop and unjam polish pass.
6. **The viewer's feature set of 2026-07-05** (absolute sliders per finger and thumb, a live hyperextension guard, keyframe auto-update) is not described in detail here. To match or extend that behaviour inside Blender, read `skills/dayz-animation-pipeline/scripts/build_viewer.py`.
7. **The exact `CMD_*` and ASI grammar is in `anim-graph.md`.** Read it in full for that; the table above names only its topics.

---

## Findings from eval runs (2026-07-10)

Measured during benchmark runs of this skill; not yet checked on `P:\` unless a line says so.

- **Ring and pinky finger chains of the plugin rig.** The wave-action eval run left them out of the export, on the grounds that in `JD_Master_Rig (No IK Bones).blend` they hang from the carpal bones `RightHandRing` and `RightHandPinky`, which it said do not exist in the vanilla skeleton, so their local transforms would refer to a parent the engine does not have. That reason does not hold on `P:\`: the vanilla player skeleton lists all four carpal bones (`P:\DZ\anims\cfg\skeletons.anim.xml:230` for `RightHandRing`; the others are in the table under "Skeleton and exclusion rules"), and the vanilla unjam clips key them. What the run did show is that the Thumb, Index and Middle chains, which parent straight to `RightHand`, export safely, and that an export without the ring and pinky chains plays. Exporting those two chains with their carpal bones has not been tested in game here; test it before relying on either choice.
- **Palm-orientation gate for gestures**: see "Before you deliver" in `SKILL.md`. Measure the character's forward from bone geometry and assert the palm normal numerically; judge stills only from an on-axis camera.
