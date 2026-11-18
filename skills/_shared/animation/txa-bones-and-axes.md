# Bones and axes for a `.txa` export

Which skeleton bones a Blender clip keys or leaves out for DayZ, and how the plugin and the SEAnim exporter turn Blender axes into DayZ axes. The export routes and the plugin setup are in `blender-txa-export.md`.

Vanilla facts cite `P:\`. The `.anm` files are binary, so what is said about them comes from the bone and event names they hold. Plugin and exporter behaviour is not checked on `P:\`; results measured in game say so.

## The vanilla player skeleton

The survivor's animation skeleton is the bone list named `player_testing.xob`; the player workspace previews that model (`P:\DZ\anims\workspaces\player\player_inventory\player_inventory.aw:12`).

| Bone or group | Line in `P:\DZ\anims\cfg\skeletons.anim.xml` |
|---|---|
| Start of the `player_testing.xob` list | `:110` |
| `EntityPosition`, the root that carries movement | `:113` |
| `RightHand_Dummy` | `:115` |
| `Pelvis` | `:120` |
| `RightForeArmRoll`, listed just before `RightHand` | `:146` |
| IK helpers `RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget` | `:149` to `:151` |
| IK helpers `LeftForeArmDirection`, `RightForeArmDirection` and their `...DirectionOrigin` pair | `:154` to `:157` |
| Carpal bones `LeftHandRing`, `LeftHandPinky`, `RightHandRing`, `RightHandPinky` | `:208`, `:225`, `:230`, `:247` |
| `Weapon_Root`, then `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt`, `Weapon_Bone_01` to `Weapon_Bone_06` | `:254` to `:264` |

The list holds 172 `<bone>` entries (`:112` to `:302`). It names bones only, not parents. On `P:\`, `OFP2_ManSkeleton` is the skeleton name stored inside character models such as `P:\DZ\characters\tops\shirt_m_new_anim_system.p3d`.

The vanilla AK-101 unjam clip `P:\DZ\anims\anm\player\reloads\ak101\p_erc_unjam_ak101_ras.anm` keys 73 bones, from `Spine` to `Weapon_Bone_06`:

- No `EntityPosition`, no `Pelvis`, no leg bone: action clips start at the spine.
- No IK helper bone.
- Both hand dummies, the four carpal bones and the ten weapon bones.
- Events `Weapon_CanUnjam_Start`, `LoopStart`, `Weapon_CanUnjam_End`, `LoopEnd`, `Weapon_BulletEject`, `Weapon_Cocked` and `Weapon_Unjammed`.

The PM73 jam clip `P:\DZ\anims\anm\player\reloads\pm73\p_erc_jam_pm73_ras.anm` keys the same set, with only the loop and unjam events: `Weapon_CanUnjam_Start`, `LoopStart`, `Weapon_CanUnjam_End`, `LoopEnd` and `Weapon_Unjammed`.

## What to key and what to leave out

- Bone names must match `OFP2_ManSkeleton` exactly, or the RPT logs `Error: Bone X doesn't exist in skeleton OFP2_ManSkeleton` and that bone does not move (`player-skeleton.md`, `anm-clips.md`).
- Action clips (reload, fire, chamber, jam) leave out `EntityPosition`, `Pelvis` and the legs, as the vanilla clips above do; idle and locomotion supply those. Keying the rig's root and pelvis makes the character lie down or sink into the ground (measured in game). `seanim_export.py --rest-pose` applies the same cut: it keeps only the bones a vanilla reference SEAnim of the same slot has.
- `RightHand_Dummy` is the weapon anchor, and the whole weapon hangs from it (`player-skeleton.md`). In a full body action clip, keying it with made up values overrode the grip and threw the weapon onto the character's back (measured in game). The vanilla unjam clips do key it, so the engine accepts a track with the right values; leave it out when you have no values taken from vanilla.
- `Weapon_*` bones need real values or must be left out, never placeholders. Placeholders stretch the weapon mesh: a DayZATool extract showed `Weapon_Bone_01` to `_06` at `(0, 0, 0)` against vanilla `(−11.43, 0.79, −2.48)`, about 11.7 cm off. Leaving all ten out (72 bones down to 62) fixed it, at the cost of a bolt that does not move in that clip.
- Never key IK helper bones (`LeftHandOrigin`, `RightHandOrigin`, the `...ForeArmDirection` bones, `LeftHandIKTarget`) in a full body or additive clip. They are in the vanilla skeleton, but the vanilla action clips do not key them, and stray keys on them break full body and additive exports (`weapon-anim-blender.md`).
- Hands hang from the twist bone. In Blender the parent of `RightHand` is `RightForeArmRoll`, not `RightForeArm`. Skipping the roll bone when turning a world rotation into the wrist's local one leaks rotation into the wrist and can drop the fingers by about 11 cm (measured as an in game bone overlay; `player-skeleton.md`).
- IK helpers do not roll the wrist. Turning `LeftHandIKTarget` or `LeftHandOrigin` does not change the hand in game, and in an IK pose the engine's IK also absorbs a turn of the raw `LeftHand` bone; what the pose visibly drives is the finger curl. To change how the support hand sits, match the weapon's geometry to a vanilla clip whose hand already sits that way (measured in game; `weapon-in-hands.md`).
- A weapon states `.anm` has two to four keys per channel, not exactly three (closed, open, jammed), because Workbench trims near duplicates; the AKM states clip has two distinct frames (`weapon-in-hands.md`).
- The plugin rig's ring and pinky chains hang from the carpal bones, which the vanilla skeleton has (`:230` and the table above) and the vanilla unjam clips key. A wave clip exported without the ring and pinky chains plays; the thumb, index and middle chains, which hang straight from `RightHand`, export safely. Exporting ring and pinky with their carpal bones is not tested in game; test it before relying on either choice.

## Axes in the plugin's `.txa` export

- The axis fix `mtxFix` turns 90 degrees about Z and swaps Blender's X and Y. The matrix `[[0,1,0],[-1,0,0],[0,0,1]]` (row major, as `mathutils` reads it) maps +X to −Y, a −90 degree turn; the exporter applies `mtxFix.inverted()`, the +90 degree turn `[[0,-1,0],[1,0,0],[0,0,1]]`. The plugin applies it the same way in `ImportTxa.py:141`, `ExportTxa.py:194` and `:228`, and in `ExportTxo.py`.
- The component swap in the `.txa` text is a separate step; do not merge it with the axis fix. Translation and scale are written X Z Y, the quaternion as `(x, z, y, −w)`, and a final `FQuaternion(−w, −x, −y, −z)` is applied on export (`Txa.py:480` to `:496` and `:550` to `:566`, `DayzAnimUtils.py:35` to `:39`, `ExportTxa.py:250`).
- A calibration pair confirms it: `rot_txa = mtxFix · viewer_local · mtxFixᵀ`, written as `(x, z, y, −w)`. The root frame is why the plugin must do the export: the plugin rig has `EntityPosition` over `Pelvis`, while the `.txa` has `Scene_Root` over both.
- `fUnitScale` defaults to 1.0; assume 1.0 (not tested otherwise).
- Clips run at 30 fps by default. Set the exporter's "Override Fps" to 30 (0 uses the scene's rate); 20 to 25 fps for a slower feel, or 60, also work.
- Never key scale. The plugin's Scale Keys option is off by default, and whether binarizing drops scale held in a `.txa` is not confirmed.

## Axes in the SEAnim export

| Rig | Rotation `(x, y, z, w)` becomes | Rest offset `(x, y, z)` becomes |
|---|---|---|
| The plugin rig | `(−y, −z, x, w)` | `(y, z, −x)` |
| Bohemia's FBX rig built by `build_rig_dayz.py` | `(−x, −z, −y, w)` | `(x, z, y)` |

Offsets are in centimetres: the exporter hard codes `UNIT_CM = 100.0`, checked against the finger offsets of a vanilla AKS-74U clip. The plugin rig map was calibrated against the plugin's sample SVD fire clip (its `.txa` through the plugin against the `.anm` DayZATool extracted): 73 bone and frame pairs exact to 0.00 degrees, with a DayZATool round trip error of 0.0007 degrees. That is one clip; check again if the plugin build or the Blender version changes, since the map depends on the plugin's axis fix and swaps.

The FBX rig's bone frames are the plugin rig's turned 90 degrees about Z. Through the plugin rig map every one of its bones comes out turned 90 degrees (rest offsets 44 to 90 degrees off vanilla, median 90), and a forward `LeftArm` raise goes out to the side. `seanim_export.py` reads the rig and applies the right map; the FBX rig map was worked out offline and played in game for one `LeftArm` pose (`weapon-anim-viewer.md`, its section on the bone frame maps per rig).

## Axes between Blender, the viewer and DayZ

- Blender Z up into the viewer's Y up is `(x, y, z)` to `(x, z, −y)`, a proper rotation (determinant +1) into Three.js's right handed frame. DayZ is left handed, so viewer coordinates (`rig_dayz.json`) written into a `.p3d` unchanged land mirrored.
- Game model space into the viewer is `(x, y, −z)`, a Z flip, tested in game (`weapon-in-hands.md`). Flipping a quaternion the same naive way, `(−x, −y, z, w)`, renders mirrored; rebuild the pose from measured positions instead.
- For geometry, Blender into DayZ is `(x, y, z)` to `(x, z, y)`, determinant −1, tested in game (`_shared/models/generated-model-rules.md`). The determinant +1 viewer map used for DayZ geometry mirrors it.
- Bohemia's FBX rig imports with the mesh at object scale 0.01 and the armature at scale 1, in separate spaces: armature in centimetres, T-pose, origin at the pelvis; mesh in metres, origin at the feet. Read naively, the skeleton sits about 35 times off the mesh. Bind again in one space: take a uniform scale from a known match (wrist bone X against half the mesh width gives `s≈0.0101`), move the bounding box centres together, then apply the Y up fix. The full method is in `weapon-anim-viewer.md`. This trap is why the plugin rig, which has no scale problem, is the rig to author on.
