# Authoring weapon clips

How to author each kind of player weapon clip in Blender (IK pose, fire, weapon states, reload, hold actions), what a full body action on a weapon must leave out, and the rules vanilla clips follow for helper bones. Setup and the rig are in `weapon-anim-blender.md`; export and compile in `weapon-anim-compile.md`.

## Rules for every clip

- Author at 30 frames per second: set "Override Fps" to 30 in the exporter (0 uses the scene rate). 20 to 25 feels slower and deliberate; 60 is valid. Every vanilla AKM clip runs at 30 (`weapon-anim-testing.md`, "Frame budget of the vanilla AKM clips").
- Never key scale; DayZ ignores bone scale, and scale keys are off by default on import and export.
- Leave the legs to locomotion. Idle and aim poses key the legs only as the static idle; reload, fire and state clips key from the shoulders down, and the plugin's bone list for survivor reloads has no leg bone.

## The IK pose

Key four controls, inserting keys on selected channels only:

| Control | Role |
|---|---|
| `LeftHandOrigin` | Where the support hand is; a child of `RightHand_Dummy`, so it follows the weapon. |
| `RightHandOrigin` | Position and rotation of the whole grip relative to the shoulder. |
| `LeftForeArmDirection` | Left elbow direction. |
| `RightForeArmDirection` | Right elbow direction. |

Export as "Survivor IK 2h" or "Survivor IK 1h". The plugin limits the export to the survivor IK bones, writes one key and sets the end frame to 1; do not select bones first or treat it as a clip.

Turning `LeftHand` or the IK helpers does not turn the support wrist in game, because the engine's IK lines the hand up with the weapon again; the pose visibly drives finger curl. To change how the support hand sits, match the weapon's geometry to a reference whose hand already sits that way (`weapon-in-hands.md`).

A vanilla IK pose file holds 2 frames at 30 fps, the second a byte for byte copy of the first; write a duplicate frame if a tool wants two. For the AKM the instance's `IkPose` line names the `izh18` pose (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:6`) while script registers `AKM_Base` with `dz/anims/anm/player/ik/weapons/akm.anm` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`). Which one the engine uses is not known, so set both to the same pose on a custom weapon.

Practice, not checked on `P:\`: moving `RightHand_Dummy` moves the weapon, and lining the stock up with the collarbone and getting the forearm angles right is the most sensitive part. The fire IK looks confusing in the animation editor; the weapon model in the Blender scene helps. Blender constraints help with posing but are not exported as such: export, look at the elbow, shoulder and grip gaps in game, and repeat.

The sight camera hangs on the weapon model's `eye` memory point (about 5.2 cm above the bore on the AKM). Sight alignment comes from the weapon's geometry and the IK pose, not leg or locomotion bones; `usti hlavne` and `konec hlavne` share Y and Z and `bolt_axis` is parallel to the bore. Canted irons mean the weapon's frame, stock angle or eye and bore line need fixing (`weapon-in-hands.md`).

## Fire

About 7 frames at 30. Key only what moves, usually the right index finger and `Weapon_Bolt`. Start with the trigger already pulled on frame 0, move `Weapon_Bolt` out and back (the plugin's SVD sample moves it 0, 0.031, 0.090, 0.121, 0.081, 0.040 along X), and add the bullet eject event (`#event 1 "Weapon_BulletEject"` in that sample). A belt fed weapon's belt motion goes here too.

## Weapon states

Author three frames, one per state: 0 bolt closed, 1 bolt open, 2 jammed. Only the `Weapon_` bones matter; use the plugin's "weapon bones" selection. Set the end frame to 2, not 1, or only two frames are written and open and jammed break. Export as Additive, "Selected Bones Only", 30 fps. At run time the engine picks a frame with `SetInitState(int pFrameIndex)` (`P:\scripts\3_game\human.c:1112`).

The stored clip is not always 3 frames. Workbench trims consecutive keys that are nearly the same, so vanilla `w_*_states.anm` clips store 2, 3 or 4 keys per channel (counted on the 47 clips of 1.29; 1.30 has 50). `w_akm_states.anm` is 2 frames with two poses: `Weapon_Bolt` at (0, 0, 0) then (5.61, 0, 0), `Weapon_Bullet` near 0 then (-17.38, -4.02, 4.03), ejected. How many start states the engine reads per weapon cannot be told offline.

The bolt's rest position comes from this clip, not an action clip (measured in game). On a jam the engine sets `Weapon_Bolt` to the jammed frame through `SetInitState`; an unjam clip overrides it only while it plays, so its frame 0 must equal the jammed frame or the bolt jumps. Take the values from an extract (`DayZATool --extract-anim w_<weapon>_states.anm 100`) rather than by eye; on one submachine gun they were closed 0, jammed -2.2 cm, open -4.3 cm along the bone's X.

## Reload, charge, chamber, jam

- Key small rotations of `Spine`, `Spine1` to `Spine3`, `Neck` and `Head`, both arms and hands, and the moving `Weapon_` parts; the small spine, neck and head motion is what makes it look human.
- The Additive export writes only bones with keys.
- Use "visual location/rotation" keying for a bone a constraint drives.
- "Additive" is how the clip is authored, not a graph node; vanilla reloads run on their own `CMD_Reload_` commands with nothing additive about them (`anim-graphs.md`, "Reload is not additive").
- The "Survivor Reload" export type exists in the plugin, but no difference from Additive has been seen in game; treat reloads as Additive.

Misleading names: `ReloadMagazineDetach` maps to a clip whose file name says `mag_remove` and that is the hand coming back from the hip, not a removal (not checked on `P:\`). `FireCocked` is firing while cocked. "Bullet in chamber" is not a state (`anim-instances-and-templates.md`, "Weapon state names").

There is no magazine bone, so fake the tracking:

1. In edit mode duplicate `LeftHand` (say `LeftHandMagTrack`), parent it to `LeftHand` and place it where the hand holds the magazine.
2. Give `Weapon_Magazine` Copy Location and Copy Rotation constraints to it.
3. Key the constraints on and off over the reach with visual keying; plain keys snap when the constraints switch.
4. Bake the action with visual keying and clean the curves.

Do not author aim space (the grid of look directions bows and repeaters use) with the plugin; editing it turns the character into a floating lump.

## One pose per weapon class

Registering a different instance or IK pose for a foregrip by branching in the callback (`if (weapon.withGrip) ...`) cannot work:

- Every item in hands call takes a class name or is global, none a weapon or player: `SetDefaultItemInHandsProfile` (`P:\scripts\3_game\dayzplayer.c:225`), `ResetItemInHandsProfiles` (`:229`), `AddItemInHandsProfile` (`:240`), `AddItemInHandsProfileIK` (`:243`), `AddItemBoneRemap` (`:252`).
- Registration runs once when the player type is set up, in `DayZPlayerTypeRegisterItems` (`dayzplayercfgbase.c:334`), which calls the mod callback `RegisterFireArms` (`:460`). It is not run per weapon and ignores attaching; there is no weapon object in it.
- The fallback is the class hierarchy: register on a base class and override on a subclass, from the root `Inventory_Base` with the apple pose (`:373`). The condition is the class, not the attachments.
- `ResetItemInHandsProfiles` and adding again is global to the player type and affects every player.

So author one pose that reads well with and without the attachment, as vanilla does. Two class names swapped in `EEItemAttached` and `EEItemDetached` is possible but fragile and multiplies per attachment. Since 1.30 `SetAnimationInstanceByName` on `Human` switches the instance at run time (`human.c:1384`), and the player gets `OnItemInHandsChanged` (`P:\scripts\3_game\entities\man.c:163`, overridden at `P:\scripts\4_world\entities\dayzplayerimplement.c:997`), which could swap a profile when a grip is mounted. It is measured only for surrender (vanilla) and a vehicle rider (`rider-pose-measured.md`), and the native warns of desync; treat it as a lead to test.

## Full body action clips on a weapon

Measured in game on a custom submachine gun:

- Leave the `Weapon_` bones out unless they carry correct values. A pipeline that treats the weapon as rigid in the hand exports `Weapon_Bolt`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bullet` and `Weapon_Bone_01` to `06` at the export rig's rest, typically (0, 0, 0) against (-11.43, 0.79, -2.48) in the vanilla `p_erc_jam_cancel_pm73_ras`, about 11.7 cm off, and the engine stretches the weapon mesh to them. Extract the `.anm` with DayZATool, drop the `Weapon_` bones with `seanim_writer.py`, generate again; the weapon then stays in its base pose. To detect it, compare frame 0 of the `Weapon_Bone_` tracks with the weapon's vanilla clip; centimetres off means bad values.
- Key the spine up only; leave `EntityPosition`, `Pelvis` and the legs out so the action does not fight locomotion.
- Never animate `RightHand_Dummy`, the weapon's anchor; the grip loses the weapon. Remove what the export got wrong and let the IK pose and base state place it.

## Hold actions need loop notes

Every action the player holds a key for, unjamming above all, needs `LoopStart` and `LoopEnd` notes. Unjamming runs on a timer, not the clip: `WeaponUnjamming` sets `m_jamTime = 5.0` (`P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:218`); `WeaponUnjamming_Start` adds up time in `OnUpdate` and posts the timeout once `m_dtAccumulator >= m_jamTime` (`:27` to `:42`); the next state calls `SetJammed(false)` (`:87`). Releasing the key first interrupts and the weapon stays jammed. The timer needs the weapon command still looping, with `IsActionFinished()` of `HumanCommandWeapons` false (`P:\scripts\3_game\human.c:1032`), and the notes keep the clip looping. Without them, by the state machine, the clip plays once, reads finished, goes back to jammed and fires again while the key is held, so the player sees an endless struggle (traced, not run). With them the unjam completes at about 5 s (measured). `Weapon_CanUnjam_...` or `Weapon_Unjammed` events do not replace the loop.

Copy the structure of a vanilla jam clip (extract `p_erc_jam_<weapon>_ras.anm`): intro from frame 0 to `LoopStart`, the struggle between `LoopStart` and `LoopEnd`, repeating while the key is held, and the outro to the end with `Weapon_Unjammed` (the rechamber); `LoopEnd` comes before `Weapon_Unjammed`. The note form that survives DayZATool is `LoopStart||-1` and `LoopEnd||-1`. To add them, extract the `.anm`, add the notes with `seanim_writer.py` and generate (bones kept within 1e-3, notes kept). When testing, hold the key; a tap plays the cancel clip and the weapon stays jammed, as in vanilla.

## Helper bones in vanilla clips

Measured offline on 8 vanilla clips:

- `ArmExtra`, `ForeArmExtra` and `WristExtra` hold half their sibling's local rotation (a slerp halfway from identity), the siblings being `ArmRoll`, `ForeArmRoll` and `Hand`: median error 0.2 to 1 degree, at most 4.
- `ElbowExtra` holds about half the `ForeArm` swing without its twist (median 3 to 7 degrees, up to about 26); its rest axes differ from the forearm's by 7.32 degrees.
- `ArmRoll` and `ForeArmRoll` are pure twist about the bone (swing at most 0.9 degree).

The parent table is `player-skeleton-parents.txt`. A clip that leaves the helpers still or bends the roll bones gives pinched elbows and stepped wrists. After authoring, recompute the helpers by that rule (roll bones as pure twist, turned toward the original elbow and wrist) and check: helpers within 1 degree (elbow within 7), roll swing within 1 degree, hands unchanged. That check is a design, not a measured gate.

Fix the quaternion's sign before splitting a rotation. `q` and `-q` are the same rotation, but `2*atan2(x, w)` puts them 360 degrees apart, so halving gives halves 180 degrees apart. In game the forearm twisted like a sweet wrapper with the hand in place (`ForeArmRoll` at -121 to -146 degrees from its parent against +49 at rest). Force `w >= 0` first; a test with the identity misses it, a test with `-q` fails by 180 degrees.

To check a pose survived a tool, compare per component, not by angle: align signs (negate one if the dot product is negative), then take the largest component difference against about 5e-6. `2·acos(dot)` turns rounding near rest into 0.1 to 0.2 degrees, reported 0.18 degrees for a true 0.00 on quaternions not exactly unit length, and about 0.8 degrees for a real 0.002 on float32 quaternions with norms of 0.99999. Normalize and use `atan2`. An error flat across all bones points at the measuring, not the pose.

## Continuous actions get no arm IK

The weapon IK node `NormalWeaponIK` (`P:\DZ\anims\workspaces\player\player_main\locomotion.agf:3860`) comes before the queue `LocomotionQ` (`:3602`), and `ActionMaster` enters at that queue (`:3617`). As far as the graph was read, the continuous action state machine has no weapon IK node of its own, so the arms get no IK during a continuous action (matches what was measured in game). Borrowing another object's animation set borrows its geometry too: the second hand goes to that object's grip. The pot holds 28.7 cm between the wrists and left the left hand of a 57.5 cm tray 33.5 cm from its grip through a whole pour. Compare the wrist spacing of a borrowed set's IK pose with yours first.
