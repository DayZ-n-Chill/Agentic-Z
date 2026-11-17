# DayZ handoff: from a Blender action to a `.txa`

What this skill hands to the DayZ animation pipeline when the motion is meant for a DayZ character or weapon: which export route to use, what to key and what to leave out, the coordinate conventions, the loop notetracks, and what the `dayz-animation-pipeline` skill already owns.

## How to read this file

- A fact about the vanilla game cites the vanilla file on `P:\` as `path:line`. Those lines were opened and checked on 2026-11-17. Binary files (`.anm`) have no lines; what is said about them was read from the bone and event names in the file.
- Everything else is third-party or measured and is **not yet checked on `P:\`**: the behaviour of the DayZAnimationPlugin (jdfnc24's `DayZAnimationPluginDemo` and the maintained Sanitoeter05 fork, called `DayZAnimationPlugin_MAINTAINED` here), of DayZATool and of Workbench, and results measured in two mod projects whose notes are not shipped with Agentic-Z. A tag in brackets names where a measured result comes from:

| Tag | Source (not shipped) |
|---|---|
| WAP 06-29 | WeaponAnimPipeline (a Three.js animation viewer and its export tools), in-game pipeline test handoff, 2026-06-29 |
| WAP 07-05 | WeaponAnimPipeline, grip workflow with the viewer, 2026-07-05 |
| WAP code | WeaponAnimPipeline scripts `tools/seanim_export.py` and `tools/txa/viewer_to_txa_via_plugin.py`, read directly |
| SR2M 06-30 | A6_SR2M (a weapon mod), close-out of the strike animation pipeline, 2026-06-30 |
| SR2M 07-01 | A6_SR2M, unjam loop handoff, 2026-07-01 |
| SR2M 07-02 | A6_SR2M, unjam done handoff, 2026-07-02 |
| SR2M script | A6_SR2M, re-authoring script for the strike animation, 2026-07-02 |

- The "strike" animation is the A6_SR2M unjam animation in which the character hits the weapon; its files keep their project name `golpe` (`golpe.anm`, `golpe_retimed.json`).
- A file named without a folder (`weapon-in-hands.md`) is a reference of the `dayz-animation-pipeline` skill, in `skills/dayz-animation-pipeline/references/`.

The contract was extracted on 2026-07-09 by reading those skill references and project notes; nothing in it was inferred from search snippets.

---

## Pipeline routes (A and C)

The existing pipeline is Layer 2 of `dayz-animation-pipeline` (skeletal `.anm` authoring). It was built as the WeaponAnimPipeline project (an interactive Three.js viewer) and validated end to end on A6_SR2M (a real weapon mod). Two export routes lead from a posed skeleton to the binary `.anm` DayZ loads. The skill calls them **Route A** and **Route C**; the project notes call the same two mechanisms "Via A" and "Ruta C".

### Route A: `.txa` (DayZAnimationPlugin) → Workbench → `.anm`. The canonical route

- Definition (`weapon-anim-authoring-viewer.md`, "Route A (canonical)"): `tools/txa/dump_viewer_world.py` + `viewer_to_txa_via_plugin.py` → `.txa` → Workbench → `.anm`. It handles root motion. Use it for the grip.
- It is the only validated route for full-body and action animations: Route C is not valid for full-body action animations (jam, unjam, melee); the A6_SR2M strike animation (2026-06-30) confirmed that full-body work goes through Route A (`weapon-anim-authoring-viewer.md`).
- The full recipe that was run and confirmed in game (SR2M 06-30, "the correct pipeline"):
  1. Author in the viewer → animation JSON (for example `golpe_retimed.json`).
  2. `python tools/txa/dump_viewer_world.py golpe_retimed.json <scratch>/golpe_world.json` (WeaponAnimPipeline project script, not shipped here). It converts the per-frame, per-bone viewer state to FK **world** space.
  3. `blender --background --python tools/txa/viewer_to_txa_via_plugin.py -- <world.json> <out.txa> ADD <spine_up_bones.json>` (project script, not shipped here). It poses the plugin's own rig and calls the plugin's real Blender **export operator** to write the `.txa`; that operator "handles all of the convention" (WAP 06-29).
  4. **Workbench (GUI, a step only a person does)**: Resource Manager → right-click the `.txa` → "Register & Import" the first time, "Reimport Resource" after that → produces `.anm` and `.anm.meta`.
  5. Optional command-line post-process for corrections the plugin does not expose (bone exclusion, notetracks): `DayZATool --extract-anim` → `.seanim` → Python edits with `skills/dayz-animation-pipeline/scripts/seanim_writer.py` → `DayZATool --generate-anim` → final `.anm`. This step needs no GUI.
  6. Deploy the `.anm` to `<Mod>/animations/` and rebuild the PBO. File patching does not reload an `.anm`.
- Used for: full-body action animations (the jam and unjam strike) and, per the grip workflow note, authoring the weapon **grip** itself ("Export: Route A is mandatory for the grip", WAP 07-05).
- Status: **closed and confirmed in game** for the strike animation's body, head and weapon staying in the hand (SR2M 06-30). The loop and unjam fixes below were built and deployed through this route; the **final in-game confirmation of the last polish pass (loop, micro-jerk and thumb) was still pending** at the last handoff read, because the user interrupted the test (SR2M 07-02).
- Tool and version: `DayZAnimationPlugin_MAINTAINED` (the Sanitoeter05 fork), cloned wherever the user keeps it. It needs **Blender 4.4+ or 5.x** (that session used Blender 5.1). See "Blender-side conventions" below.
- A pure-Python `.txa` writer, `pose_to_txa.py`, exists in the WeaponAnimPipeline project but does **not** close the root frame correctly (the body lies down). It was checked and is broken; use the plugin-based script of Route A instead (WAP 06-29).

### Route C: `.seanim` (CLI) → DayZATool → `.anm`. Weapon-bone and partial tracks only

- Definition (`weapon-anim-authoring-viewer.md`, "Route C (CLI)"): `skills/dayz-animation-pipeline/scripts/seanim_export.py` → `.seanim` → `DayZATool --generate-anim <f>.seanim 100` → `.anm`. Rotations and rest only. The viewer → SEAnim quaternion convention `(-vy,-vz,vx,vw)` is exact on fingers, but `LeftHand` does not obey it (a separate wrist process), so do not use Route C for the support-hand wrist. Use Route C only for weapon-bone and partial tracks.
- The project script says the same in its header (WAP code, `tools/seanim_export.py` docstring): viewer quaternions are rig-local and point along +Y, DayZ's bone-local frame points along +X; they are "NOT guaranteed to be in DayZ's exact convention. The in-game test is the gate".
- DayZATool does not read `.txa` at all. It has only `--extract-anim`, `--generate-anim` and `--extract-mdl`, all on `.seanim` (WAP 06-29).
- Status: used to deploy a first test unjam animation straight onto A6_SR2M for a manual in-game test (WAP 06-29); replaced by Route A once the full-body strike animation showed Route C is not enough for anything beyond isolated weapon-bone channels.
- Still the right tool for baking hand-authored finger and thumb corrections into an already exported `.anm` without running Workbench again. It was used for the final thumb-curl fix on `golpe.anm` (SR2M 07-02).

---

## Interface point for this skill

**This section matters most: what this skill must produce so it plugs into Route A without deriving anything again.**

### The recommended artifact: pose the plugin's own rig, export with the plugin's own operator

Every animation in this pipeline that was confirmed in game was made by loading the rig of `DayZAnimationPlugin_MAINTAINED` (`_AssetSamples\JD_Master_Rig (No IK Bones).blend`, armature object `_DayZ_Character`, 151 bones; `weapon-anim-blender-complete.md`, and the constants `PLUGDIR`, `BLEND` and `arm=bpy.data.objects['_DayZ_Character']` in WAP code), keyframing it, and letting the plugin's **own** export operator (`export_scene.txa`, `ExportTxa.py`) write the `.txa`. That operator is what handles all of the convention correctly: `mtxFix`, the root frame, the per-component swaps and the quaternion negation ("the plugin's EXPORT operator handles all of the convention ... real plugin round trip, median 0.0°", WAP 06-29).

**The WeaponAnimPipeline `tools/txa/*.py` scripts exist only to bridge a tool that is not Blender (a custom Three.js viewer) into Blender. A skill that drives Blender directly through the Blender MCP server does not need that bridge.** It can pose `_DayZ_Character` with `bpy` calls (through `execute_blender_code`) and call the plugin's `bpy.ops.export_scene.txa(...)` directly. That is a strictly shorter path to the same artifact Route A already produces and Workbench and the rest of the pipeline already consume. This is the main finding: **do not invent a JSON interchange format. Pose the plugin's rig and call its export operator.**

### The deliverable, in priority order

1. **Preferred**: a Blender scene where `_DayZ_Character` (or the vanilla-named equivalent from `P:\DZ\anims\cfg\skeletons.anim.xml`) has a keyframed Action, made with the `DayZAnimationPlugin_MAINTAINED` add-on registered, then exported through **File > Export > DayZ Animation (.txa)** (`export_scene.txa`) with the right **Type** for the kind of animation (`FB`, `IK1H`, `IK2H` or `ADD`; see "Blender-side conventions"). The handoff artifact is the `.txa` file plus a note of which `.anm` it should become. The user's remaining step is Workbench "Register & Import" (or "Reimport Resource"), two clicks in the GUI, then the wiring, which `dayz-animation-pipeline` owns (see below).
2. **Fallback, when posing through the Blender MCP server is impractical for a track**: write the same **world-space JSON** the bridge script reads, so the user's working `viewer_to_txa_via_plugin.py` runs unchanged. The schema, read from the code (WAP code, `tools/txa/viewer_to_txa_via_plugin.py`):
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
3. **Only for isolated weapon-bone or partial tracks (never full body, never the support-hand wrist)**: the "viewer anim JSON" Route C reads. The schema, read from the code (WAP code, `tools/seanim_export.py`):
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
   This feeds `seanim_export.py --anim <json> --rig data/jd_dayz.json --out out.seanim` (the shipped exporter is `skills/dayz-animation-pipeline/scripts/seanim_export.py`; `data/jd_dayz.json` is the JD rig file of the WeaponAnimPipeline project). The user then runs `DayZATool --generate-anim out.seanim 100`. DayZATool is a closed .NET program for Windows with a command line and no GUI step; an agent on a Windows host can run it headless (`skeletal-anm-enfusion.md`, 2026-09-28).

### What this skill never does (owned downstream)

- It never writes `.asi` wiring, the `AddItemInHandsProfileIK` or `AddItemBoneRemap` Enforce Script calls, `config.cpp` or `model.cfg`. That is Layer 1 and Layer 3 of `dayz-animation-pipeline` (see the do-not-duplicate list below).
- It never claims to have run Workbench or the in-game test. It mentions DayZATool as run only when it ran it and read the file it wrote (`tooling-and-walls.md`: never imply the agent ran Workbench, FBXToRTM or DayZATool when it did not).
- It never derives the `mtxFix` and quaternion-swap math again from scratch. That math is calibrated (see "Coordinate conventions"), and deriving it again cost several wasted sessions in the project history.

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

### Rules (third-party and measured; not yet checked on `P:\` unless a line says so)

- **The target skeleton is always `OFP2_ManSkeleton`.** Bone names must match **exactly** (PascalCase with underscores), or the RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone silently does not animate. Stated in three references: `player-skeleton.md`, `skeletal-anm-enfusion.md` and `weapon-anim-blender-complete.md`. On `P:\`, `OFP2_ManSkeleton` is the skeleton name stored inside the character models (for example `P:\DZ\characters\tops\shirt_m_new_anim_system.p3d`); the bone names animation uses are the `player_testing.xob` list above.
- **`RightHand_Dummy`** is the weapon anchor; the whole weapon is its child. In the A6_SR2M **full-body action animation**, animating `RightHand_Dummy` was a bug: it overrode the grip of the ikpose and the weapon flew to the character's back. The fix in production was to leave `RightHand_Dummy` out of the `.anm`, so the ikpose holds the weapon (SR2M 06-30; `player-skeleton.md` says what the dummy is and does). The vanilla unjam clips above do carry a `RightHand_Dummy` track, so the engine accepts one with the right values; leaving it out is the tested fix when you do not have vanilla-derived values.
- **Spine-up exclusion (action animations only)**: vanilla action animations (reload, fire, chamber, jam) leave out `EntityPosition`, `Pelvis` and the leg chain; the idle and locomotion layer supplies those. Including them makes the character "flop" (lie down or clip underground in game). Found in production (SR2M 06-30) and confirmed in code (WAP code, `tools/seanim_export.py`): the `--rest-pose` bone mask cuts the emitted bone list down to the bones present in a vanilla reference SEAnim, with the comment "vanilla action anims are spine-UP — they exclude EntityPosition/Pelvis/legs; the idle provides the lower body. Including the rig's absolute root/pelvis orientation makes the player flop in-game." The vanilla clips above confirm the spine-up bone list.
- **`Weapon_*` bones need correct values or must be dropped, never placeholder values.** `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet` and `Weapon_Bone_01` to `Weapon_Bone_06` are real skeleton bones the player rig drives (see the table above). If a viewer or tool exports them with placeholder or default values instead of the real vanilla-derived transform, the weapon mesh visibly stretches. The cause was measured with a DayZATool extraction, not guessed (SR2M 06-30): `Weapon_Bone_01..06` collapsed to `(0,0,0)` against vanilla `(-11.43,0.79,-2.48)`, about 11.7 cm of displacement, which is the stretched weapon mesh. The fix was to drop all 10 `Weapon_*` bones from that animation (72 → 62 bones), accepting that the bolt does not move during that one action.
- **IK helper bones must not be keyframed for non-IK (full-body or additive) animations.** `LeftHandOrigin`, `RightHandOrigin`, the `...ForeArmDirection` bones, `LeftHandIKTarget` and the rest are missing from the plugin's "No IK Bones" rig until "Tools > Add Survivor IK Bones" is run; the plugin's importer silently drops their tracks when it was not run first, and stray keys on them "corrupt full-body/additive exports" according to the plugin author (`weapon-anim-blender-complete.md`). The source worded this as "do not exist in the vanilla skeleton"; the vanilla animation skeleton does list them (table above), and the vanilla action clips do not key them.
- **Hands are parented to the twist (roll) bone, not the raw forearm.** In Blender the real parent of `RightHand` is `RightForeArmRoll`, not `RightForeArm`. Skipping the roll bone when computing a wrist's local quaternion from world space leaks rotation into the wrist and can drop the fingers by up to about 11 cm. Checked by drawing in-game bone positions as an overlay, not by quaternion theory (`player-skeleton.md`, SP-039), and reproduced the same way in the viewer tooling (WAP 06-29).
- **IK helpers do not roll the wrist.** Rotating `LeftHandIKTarget`, `LeftHandOrigin` and the like does not change the hand or wrist orientation in game; only the raw `LeftHand` and the finger bones do (shown with 4 ikpose variants and an RMS pixel difference; `player-skeleton.md`, supported by `weapon-in-hands.md`).
- **A weapon-states `.anm` has 2 to 4 keys per channel, not a fixed "exactly 3 frames".** An earlier draft of the pipeline reference claimed exactly 3 (closed, open, jammed). The correction checked against vanilla is 2 to 4 keys; Workbench trims near-duplicates (`anim-graph.md`, read by its headers only, so check the wording there if it matters; `weapon-in-hands.md` has the table: the AKM weapon-states clip has 2 distinct frames, not 3).

---

## Coordinate conventions

All of this section is plugin, tool and measured behaviour; not yet checked on `P:\`.

### Route A (`.txa` through the plugin): `mtxFix` and the component swap

- Axis fix (`mtxFix`): a **+90° rotation about Z that swaps Blender's X and Y axes**, matrix `[[0,1,0],[-1,0,0],[0,0,1]]`, applied the same way in the plugin's `ImportTxa.py`, `ExportTxa.py` and `ExportTxo.py` (`weapon-anim-blender-complete.md`, which cites `ImportTxa.py:141` and `ExportTxa.py:194,228`).
- The component swap in the `.txa` text is a **separate** transform from the axis fix; do not merge the two. Translation and scale are written as **X Z Y**; the quaternion is written as **(x, z, y, -w)**; a final `FQuaternion(-w,-x,-y,-z)` is also applied on export (`weapon-anim-blender-complete.md`, which cites `Txa.py:480-496,550-566`, `DayzAnimUtils.py:35-39` and `ExportTxa.py:250`).
- The same formula was derived again and confirmed against a real calibration pair in the project, not only quoted from the plugin source (WAP 06-29): `rot_txa = mtxFix·viewer_local·mtxFixᵀ`, quaternion in the file `(x,z,y,−w)`, and the note that **the root frame does not close correctly in a pure-Python implementation** (JD rig `EntityPosition→Pelvis` against `.txa` `Scene_Root→{EntityPosition,Pelvis}`). This is why Route A must go through the real plugin in Blender, not a hand-written `.txa` writer.
- Unit scale: `fUnitScale` defaults to 1.0 in the plugin; assume 1.0 until a difference shows up (`weapon-anim-blender-complete.md`, marked `[verify]` there).

### Route C (viewer JSON → `.seanim`): calibrated, exact

- *Scope (2026-10-02):* exact for the JD rig, the rig of the calibration pair (the `--rig data/jd_dayz.json` command in "The deliverable", item 3). The BI FBX rig that `skills/dayz-animation-pipeline/scripts/build_rig_dayz.py` builds has the JD bone frames turned 90° about Z; through this formula every one of its bone frames comes out turned 90° (its rest offsets land 44 to 90° off vanilla's, median 90°). The shipped `skills/dayz-animation-pipeline/scripts/seanim_export.py` reads the rig and gives the FBX rig `(−x,−z,−y,w)` and `(x,z,y)` instead, derived offline and played in game on 2026-10-02 for one `LeftArm` pose, which this formula sent out to the side instead of forward (`weapon-anim-authoring-viewer.md`, "Route C bone-frame maps, per rig"). In game, this route played one full-body action wrong (the strike animation; see the status of Route C above).
- Rotation: viewer-local quaternion `(x,y,z,w)` → SEAnim `(−y,−z,x,w)`. Position (rest offset): `(x,y,z)` → `(y,z,−x)`, in **centimeters** (rig meters × 100). Calibrated against a real `.anm` (`JD_SVD_Fire`, `.txa` through the plugin against the `.anm` DayZATool extracted): **73 bone and frame pairs, exact to 0.00° globally**, DayZATool round-trip error 0.0007° (WAP code, the in-code comment in `tools/seanim_export.py` is the primary source; confirmed independently in WAP 06-29). The skill states the same formula as `(-vy,-vz,vx,vw)`, where "v" marks the viewer components (`weapon-anim-authoring-viewer.md`).
- The formula is verified **exact on fingers**, but **`LeftHand` (the raw wrist bone) does not obey it**: a separate wrist process that is not solved yet. So never use Route C to author the support-hand wrist orientation (`weapon-anim-authoring-viewer.md`).
- `UNIT_CM = 100.0` is hard-coded as "rig meters -> SEAnim cm (verified vs aks74u_reference finger offsets)" (WAP code, `tools/seanim_export.py`; the shipped exporter keeps the same constant).

### General Blender ↔ DayZ axis convention (geometry and rig import, not only animation export)

- Blender Z-up → viewer Y-up: `(x', y', z') = (x, z, −y)`, for the animation viewer's rig alignment (`weapon-anim-authoring-viewer.md`). It is right there because it is a proper rotation (det +1) into the viewer's **right-handed** Three.js frame. It is not DayZ space, which is left-handed, so viewer-frame coordinates (`rig_dayz.json`) written into a p3d as they are land mirrored. The step into DayZ carries a det −1 map: the position flip game model space → viewer `(x, y, −z)` that `weapon-in-hands.md` reports as validated in game, and Route C above, which maps positions with `(y, z, −x)` (det −1) and quaternion vectors with `(−y, −z, x)`, the axial-vector form of the same reflection, for the JD rig (`jd_dayz.json`); the FBX rig's `rig_dayz.json` takes `(x, z, y)` and `(−x, −z, −y)` (2026-10-02). For geometry, Blender → DayZ is `(x, y, z) → (x, z, y)`, det −1 (Rule 12 of the dayz-model-pipeline skill, in-game test 2026-10-01). *(Corrected 2026-10-01: this line used to call the viewer map "DayZ Y-up" and cited `x'=x, y'=z, z'=-y` as the model-pipeline equivalent; that det +1 map mirrors.)*
- **FBX rig scale trap** (it bit two projects: a custom big-infected character and this pipeline): the official BI rig FBX imports with the **mesh at object scale 0.01** and the **armature at scale 1**. They live in separate spaces (armature in cm, T-pose, origin at the pelvis; mesh in meters, origin at the feet). Reading bone world positions naively puts the skeleton about 35x off the mesh. The fix is to bind again in one consistent space: derive a uniform scale from a known correspondence (for example wrist-bone X against half the mesh width gives `s≈0.0101`), translate to align the bounding-box centers, then apply the Y-up axis fix. Full recipe in `weapon-anim-authoring-viewer.md`. **This FBX rig bug is why the pipeline switched to the plugin's own `JD_Master_Rig` (no scale bug) as the authoring rig instead of the raw BI FBX.**
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

### What follows for the clip (measured in A6_SR2M; not yet checked on `P:\`)

- **Root cause chain when `LoopStart` and `LoopEnd` are missing.** The unjam action is driven by the timer, not by a notetrack. A `.anm` with no loop section **ends** at its last frame (about 1.7 s for a 51-frame animation). `IsActionFinished()` turns true, the unjam start state is not waiting for that, so the machine gets the abort event and goes straight back to the jammed state. The continuous action fires again, and the 5 s timer **never accumulates**, because the animation never stays in progress long enough. Vanilla avoids this because its jam animation has `LoopStart` and `LoopEnd` (frames 22 and 200 in `p_erc_jam_pm73`, measured with a DayZATool extraction), so the command loops and `IsActionFinished()` stays false until the timer ends it. Full trace against the vanilla scripts: SR2M 07-02. The vanilla half of this chain is the list above.
- **Notetrack format**: `LoopStart` and `LoopEnd`, written as `Name||-1`, "identical to what the vanilla extraction gives" (SR2M 07-02, repeated in SR2M script).
- **Loop length rule**: the loop must last **at least as long as the engine timer (5 s for unjam); about 6 s is recommended**. The timer then fires before the loop completes one cycle and the wrap-around is never seen. This is what vanilla does (vanilla loop lengths seen: 5.9 to 6.9 s, always above the 5 s timer). So the loop does not have to be a perfectly closed cycle when it is long enough; a shorter closed loop also works but is harder to author cleanly (SR2M script; first reached in SR2M 07-02: "an unjam animation with no LoopStart/LoopEnd aborts halfway and the weapon never unjams; the loop must last at least the 5 s timer or close seamlessly").
- **The outro after `LoopEnd`** carries the notetrack that resolves the state (for example `Weapon_Unjammed`), timed near its end; the vanilla outro is about 2.5 to 3.2 s (SR2M script).
- **The micro-jerk lesson (not obvious, cost a full session)**: the engine leaves the loop from **whatever pose is current when the timer fires**, not necessarily the pose authored at the `LoopEnd` frame. If the outro's start pose differs from the loop's late-cycle pose there is a visible snap. The practical fix: from a frame well before `LoopEnd` (for example from about frame 140 in a loop of about 195 frames), settle the moving part into the "ready" pose and hold it through `LoopEnd`, so the pose already matches the outro's start wherever the timer fires (SR2M 07-02, section 2; restated as an authoring rule in SR2M script).
- **A first attempt that did not fix the loop** (kept so it is not tried again): adding only mid-animation notetracks (`Weapon_CanUnjam_Start`, `Weapon_CanUnjam_End`, `Weapon_Unjammed`) with no `LoopStart` and `LoopEnd`. They survived the `.anm` round trip, but the loop problem stayed exactly as it was (SR2M 07-01). This confirms that the unjam transitions do not consume `Weapon_CanUnjam_Start` and `Weapon_CanUnjam_End` at all (SR2M 07-02; the vanilla check is the last line of the list above).
- The fps convention for loop-frame math is the same 30 fps default as above.

---

## What `dayz-animation-pipeline` already covers (do-not-duplicate list)

Treat all of the following as already owned and point to them; do not author them again. All of these files are in `skills/dayz-animation-pipeline/`.

| Reference file | Owns | Why this skill must not duplicate it |
|---|---|---|
| `skills/dayz-animation-pipeline/SKILL.md` | The top-level routing table (object, skeletal, vehicle rider, anim graph), the definition of the Layer 1/2/3 seam, the one-animation-mod wall and its 2026-06-28 correction (graph replacement only; weapon animations do not conflict) | It is the front door. This skill should be reachable **from** that routing table (a row pointing here), not replace it. |
| `skills/dayz-animation-pipeline/references/config-driven-animation.md` | The full `model.cfg` `class Animations` property reference (type, source, selection, axis, begin/end, minValue/maxValue, sourceAddress, angle0/1, offset0/1, hideValue), `class AnimationSources` in `config.cpp`, the full list of engine `source` values, the `SetAnimationPhase` and `GetAnimationPhase` script interface | This is Layer 1 (config-driven object, door and lever animation), unrelated to skeletal character and weapon animation. A Blender authoring skill for skeletal animation never touches it. |
| `skills/dayz-animation-pipeline/references/item-ik-and-hide.md` | Pattern A (reuse a vanilla `.anm` for carry IK on heavy items through `AddItemInHandsProfileIK` with a 4-argument call and no weapon states) and Pattern B (hide on attach through a `hide`-type animation) | Both patterns are "reuse vanilla, author nothing new", the opposite of what a Blender authoring skill does. |
| `skills/dayz-animation-pipeline/references/skeletal-rtm.md` | The legacy RTM route (Arma era, `FBXToRTMGui.exe`, Arma3ObjectBuilder) | The skill and `tooling-and-walls.md` say it is legacy, reverse-engineered and **not** the route for player and weapon animations: "RTM is the #1 wrong turn" (`weapon-anim-blender-complete.md`). This skill should warn against it, not implement it. |
| `skills/dayz-animation-pipeline/references/skeletal-anm-enfusion.md` | The overview of the Enfusion `.txa`, SEAnim and `.anm` pipeline, the two-route framing, the source-of-truth repository URLs | The Route A and Route C summary above was checked against this file; it owns "which route for what". |
| `skills/dayz-animation-pipeline/references/player-skeleton.md` | The full bone catalog by zone (core and spine, legs, arms, fingers, IK helpers, weapon bones, face, misc and legacy) | Point to this catalog instead of listing bone names again; it already carries the SP-039 twist-bone parent trap and the `RightHand_Dummy` facts cited above. |
| `skills/dayz-animation-pipeline/references/anim-graph.md` | The state machine and `CMD_*` command catalog, `#Var` declarations, the ASI `$animsetinstance` structure, the player ASI catalog, the weapon-state path convention, the "reload is not additive" correction, the Workbench Animation Editor `#eventtable` trick, the minimal creature-graph workflow | This is the wiring and graph layer downstream of any `.anm` this skill produces. Point here for anything about **how** an `.anm` gets selected at runtime. (This contract read only its headers.) |
| `skills/dayz-animation-pipeline/references/weapon-in-hands.md` | The full grip and ADS memory-point contract (`eye`, `usti hlavne`, `konec hlavne`, `bolt_axis` and so on), the grip validator tool, the "geometric parity is the grip fix" doctrine, the finding that ikpose does not roll the wrist, the live bone-dump technique for poses the engine IK resolves | This is the definitive answer to "why does the weapon look wrong in the hand". A Blender authoring skill defers to it and does not derive grip fixes again. |
| `skills/dayz-animation-pipeline/references/weapon-anim-authoring-viewer.md` | **The existing Layer 2 interactive authoring pipeline itself** (viewer, IK, keyframe timeline, both export routes, the viewer feature set as of 2026-07-05) | **The file with the highest overlap risk.** It is "a blender-animation skill" in spirit, built as a custom Three.js viewer instead of live Blender. This skill's pitch is "the same outcome, driven inside real Blender through MCP", not a second, parallel viewer. |
| `skills/dayz-animation-pipeline/references/weapon-anim-blender-complete.md` | The most complete single reference: the Blender version matrix, add-on install, rig roster, IK-helper setup, the craft of each animation type (ikpose, fire, weapon states, reload, aim space, magazine tracking), `.txa` export types and text format, Workbench compile traps, the full `config.cpp`, `.asi` and Enforce Script wiring contract (`AddItemInHandsProfileIK`, `AddItemBoneRemap`, the 42 `WeaponOperations.*` state names), mod folder scaffolding | Point to it for anything mechanical about the Blender plugin (export types, event markers, `.txo`) instead of explaining it again. This contract read its first 516 lines of 906; the rest likely covers deploy, packaging and troubleshooting, so check it before assuming a gap. |
| `skills/dayz-animation-pipeline/references/vehicle-rider-ik-pose.md` | The IK-from-anchors solver for seated vehicle poses (2-bone analytic IK plus a straight spine, 21 solved joints), the rest-pose calibration requirement, the frame-of-reference caveat | A different domain (vehicle seating, not weapon or action animation), but the same rest-pose calibration and coordinate-frame caveats apply; point to the solver math, do not copy it. |
| `skills/dayz-animation-pipeline/references/handlebar-and-steering-config.md` and `skills/dayz-animation-pipeline/references/dual-entry-action-pattern.md` | Layer 1 config-driven rotation of vehicle parts, and a scripted pattern that snaps the get-in to a seat side | Not read for this contract; out of scope for a Blender animation skill (config and script layer, not authoring). |
| `skills/dayz-animation-pipeline/references/selection-painter-for-actions.md` and `skills/dayz-animation-pipeline/references/py3d-1.0.0-quirks.md` | Painting and writing `.p3d` named selections for action raycasts, and the py3d traps met doing it | The model-editing side (adding the selections and axes an animation drives). The dayz-p3d-inspector and dayz-model-pipeline skills own it, not an animation authoring skill. |
| `skills/dayz-animation-pipeline/references/blender-authoring.md` | **The existing "Layer 2 programmatic Blender authoring" stub**: the headless `bpy` keyframing recommendation, bone-name discipline, FPS and scale, coordinate caveats | **The second highest overlap risk.** It is the headless Blender authoring guidance this skill extends. It marks several things `[TBD-verify]` (the exact axis conversion, whether SEAnim or FBX export needs a manual axis fix) that the citations above have since settled by measurement (`mtxFix`, the Y-up fix, the Route A and Route C formulas). Close those there instead of opening them again. |
| `skills/dayz-animation-pipeline/references/tooling-and-walls.md` | The canonical tool inventory table, the two-format split (RTM against `.anm`), the walls (one animation mod, the closed-format caveats of RTM and `.anm`), the signing and deploy pointer, the "what to hand the user" checklist | The handoff message of this skill follows that checklist; it does not invent its own handoff format. |
| Sibling skill `mixamo-retarget` | Retargeting Mixamo or FBX mocap onto any armature (including the DayZ skeleton) through the Blender MCP server, fuzzy bone matching, the rest-pose mismatch caveat | It already drives Blender through the same MCP tool (`execute_blender_code`) this skill uses, and is the closest precedent for a live Blender MCP session that touches the DayZ skeleton. Its output feeds Layer 2 as a keyframe **source**, not as a shortcut around the rest of the pipeline. Status: experimental, not validated on a fixture. |
| The dayz-model-pipeline skill, `references/animations.md` | An independent, fairly complete restatement of the same `model.cfg`, `CfgSkeletons`, `CfgModels` and `class Animations` syntax as `config-driven-animation.md` (rotation, translation and hide types, axis, minValue/maxValue, angle0/1) | **An overlap between two other skills**, not something to copy a third time. If this skill ever has to mention config-driven animation in passing, point at `dayz-animation-pipeline` (the animation skill) as canonical, not at the model pipeline. |

---

## Blender-side conventions

Plugin and tool behaviour; not yet checked on `P:\`.

- **The Blender version depends on the plugin fork, and the metadata lies. Check the code, not `bl_info`.** The original `jdfnc24/DayZAnimationPluginDemo` needs **Blender 3.6.8 to 4.0** (it breaks on 4.1 and later with `AttributeError: 'Mesh' object has no attribute 'calc_normals_split'`). The **maintained Sanitoeter05 fork**, the one this pipeline uses, needs **Blender 4.4+ or 5.x** (it calls `action.fcurve_ensure_for_datablock`, a 4.4+ API, and a helper named `generate_fcurves_bl51`), yet its own `bl_info` declares `'blender': (2, 80, 0)` (`weapon-anim-blender-complete.md`; the same correction is in `tooling-and-walls.md`). The working environment of the project used **Blender 5.1** (SR2M 06-30).
- **Install is a manual folder copy, not a zip.** Copy `BlenderPlugin/DayzAnimationTools` into `%AppData%\Roaming\Blender Foundation\Blender\<version>\scripts\addons\DayzAnimationTools`, then enable "DayZ Animation Tools" in Preferences > Add-ons. Blender's "Install from file" does not work on this download (`weapon-anim-blender-complete.md`).
- **Where the plugin lives**: wherever the user cloned `DayZAnimationPlugin_MAINTAINED`. Both the add-on and its `_AssetSamples` rig and pose blends are under that folder; the bridge script keeps the folder and the blend as its `PLUGDIR` and `BLEND` constants (WAP code). Ask the user for the folder; do not guess it.
- **The rig that is the source of truth**: `_AssetSamples\JD_Master_Rig (No IK Bones).blend` is `OFP2_ManSkeleton` with the vanilla bone names and custom display shapes on the main bones. This is the rig to pose (`weapon-anim-blender-complete.md`). A second candidate, the raw BI FBX `animation_rig_character.fbx` (114 bones), has the scale-space bug described under "Coordinate conventions"; prefer the JD rig (`weapon-anim-authoring-viewer.md`).
- **"Add Survivor IK Bones" (`import_scene.addsurvivorik`) must run before authoring any IK or grip pose.** It creates `LeftHandOrigin`, `RightHandOrigin` and the `...ForeArmDirection` bones and adds Blender IK constraints on `LeftHand` and `RightHand` with baked pole angles **−127.9° (left) and +45.3° (right)**. Importing or authoring an IK `.txa` without it silently drops those bone tracks (the importer prints a warning). The other way round, never key these helper bones for a non-IK animation (`weapon-anim-blender-complete.md`).
- **The Export Type carries real weight; it is not cosmetic.** `FB` (Full Body: emotes only; it injects a `Scene_Root`), `IK1H` and `IK2H` (grip ikpose, a single keyframe; the plugin restricts the export to the IK bone list by itself, so do not select bones first), `RL` (rarely used; treated as `ADD` in practice), `ADD` (reload, fire, chamber, jam, weapon states; use "Selected Bones Only"). Exporting **all** bones on a reload or action animation makes the character "turn into a meatball" in game (`weapon-anim-blender-complete.md`).
- **Never key scale.** The engine ignores it (see "Coordinate conventions").
- **Workbench silently trims consecutive keyframes that are nearly identical.** An authored hold can collapse to fewer frames than intended. Author holds with real keyframe differences, and always keep the source `.txa` next to its `.anm`, because Workbench can edit an `.anm` again only when the `.txa` is present (`weapon-anim-blender-complete.md`).
- **Never assume which way the rig faces. Measure it.** A hard-coded assumption that the character faces `+X` was wrong. The JD rig faces **−Z** when aimed (measured from the hip and shoulder forward vectors: `fwdHip=(0.75,0,-0.66)`, `fwdShoulder=(0.57,0,-0.82)`), and the bug was diagnosed as "roll" for a full session before it was found to be "yaw" (WAP 06-29). The general lesson: measure the rig's forward before writing any orientation fix.
- **The character import scale `f=0.7901` is not part of this pipeline.** It belongs to a different project (a custom big-infected character mesh import), not to weapon or action animation authoring. Do not apply it here without checking its source first; character import is the job of the dayz-characters skill.

---

## Open questions

Things the sources do not answer, or that were not verified when this contract was written. Flag them to the user or check them again; do not guess.

1. **Character work was not covered.** The contract was written without reading the dayz-characters skill, so nothing here speaks for character import or rigging. Read that skill for those.
2. **The `f=0.7901` and `T2=(−x,z,y)` scale and orientation convention** was not found in the weapon projects. It appears to be a **mesh-import and rig-binding scale fact for one character model** (the big-infected project), not a general animation authoring convention. Probably irrelevant to this skill; confirm it in that project's own notes before using it.
3. **The Blender-side SEAnim plugin (SE2Dev `io_anim_seanim`) was never used in this project history.** All concrete work tested in game went through `DayZAnimationPlugin_MAINTAINED` (`.txa`) or through the Python `seanim_writer.py`, which is a standalone reader and writer, not a Blender importer. `io_anim_seanim` is cited only as existing (`tooling-and-walls.md`); it was not run or validated.
4. **The Route C calibration formula (`(-vy,-vz,vx,vw)`, cm scale) was calibrated against exactly one weapon and animation pair** (`JD_SVD_Fire`, 73 bone and frame samples). It is described as global (not per bone) and exact, but check it again if the maintained plugin fork or the Blender version changes, because the formula depends on the plugin's `mtxFix` and component-swap internals. *(2026-10-02: global across bones, but tied to the rig: it is the JD rig's map; see the Route C scope note above.)*
5. **The final in-game confirmation of the fully fixed `golpe.anm`** (loop, seamless ping-pong, micro-jerk fix, thumb curl) was still pending at the last handoff read (SR2M 07-02; the user interrupted the test). "Route A: closed, confirmed in game" above covers the earlier body, head and weapon-grip fix of 2026-06-30, not the loop and unjam polish pass. Check the A6_SR2M project's own handoff for what happened after 2026-07-02 before assuming it is fully closed.
6. **The viewer's "build 2026-07-05" feature set** (absolute sliders per finger and thumb, a live hyperextension guard, keyframe auto-update) is described here second hand, from handoff prose; `skills/dayz-animation-pipeline/scripts/build_viewer.py` was not read in full for this contract. To match or extend that behaviour inside Blender, read the script.
7. **`anim-graph.md` was read by its section headers only.** For the exact `CMD_*` and ASI grammar, read it in full; do not rely on the header list in the table above.

---

## Findings from eval runs (2026-07-10)

Measured during benchmark runs of this skill; not yet checked on `P:\` unless a line says so.

- **Ring and pinky finger chains of the JD rig.** The wave-action eval run left them out of the export, on the grounds that in `JD_Master_Rig (No IK Bones).blend` they hang from the carpal bones `RightHandRing` and `RightHandPinky`, which it said do not exist in the vanilla skeleton, so their local transforms would refer to a parent the engine does not have. That reason does not hold on `P:\`: the vanilla player skeleton lists all four carpal bones (`P:\DZ\anims\cfg\skeletons.anim.xml:230` for `RightHandRing`; the others are in the table under "Skeleton and exclusion rules"), and the vanilla unjam clips key them. What the run did show is that the Thumb, Index and Middle chains, which parent straight to `RightHand`, export safely, and that an export without the ring and pinky chains plays. Exporting those two chains with their carpal bones has not been tested in game here; test it before relying on either choice.
- **Palm-orientation gate for gestures**: see "Before you deliver" in `SKILL.md`. Measure the character's forward from bone geometry and assert the palm normal numerically; judge stills only from an on-axis camera.

---

## Sources

Skill references read for the contract, all in `skills/dayz-animation-pipeline/` (the read was full unless noted): `SKILL.md`; `references/skeletal-anm-enfusion.md`; `references/player-skeleton.md`; `references/weapon-anim-blender-complete.md` (lines 1 to 516 of 906); `references/weapon-anim-authoring-viewer.md`; `references/tooling-and-walls.md`; `references/blender-authoring.md`; `references/vehicle-rider-ik-pose.md`; `references/config-driven-animation.md` (lines 1 to 115); `references/weapon-in-hands.md`; `references/item-ik-and-hide.md` (lines 1 to 40); `references/anim-graph.md` (headers only). Also the `mixamo-retarget` skill's `SKILL.md`, and the dayz-model-pipeline skill's `references/animations.md` (lines 1 to 79) and `SKILL.md` (searched, not read in full).

Project notes read in full (not shipped; see the tag table at the top): the WeaponAnimPipeline README and its handoffs of 2026-06-28 (next session), 2026-06-29 (in-game pipeline test), 2026-06-29 (weapon part animation) and 2026-07-05 (grip workflow with the viewer); the A6_SR2M handoffs of 2026-06-30 (strike pipeline close-out), 2026-07-01 (unjam loop) and 2026-07-02 (unjam done), and its re-authoring script of 2026-07-02.

Project code read directly: `tools/seanim_export.py` (lines 1 to 70) and `tools/txa/viewer_to_txa_via_plugin.py` (lines 1 to 60) of WeaponAnimPipeline.

Vanilla files opened on `P:\` on 2026-11-17: the files cited by line above, and the two binary unjam clips named under "Skeleton and exclusion rules".
