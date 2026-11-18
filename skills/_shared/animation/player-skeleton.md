# Player skeleton

Which bones the DayZ player skeleton has, grouped by zone, how they hang together, and which helpers an IK pose keys, for mapping a Blender armature onto it when authoring `.txa`, `.anm` or `.rtm` clips. The names come from `P:\DZ\anims\cfg\skeletons.anim.xml`; the measured parent table is `player-skeleton-parents.txt`.

Two blocks of that file matter:

- `player_testing.xob` (from `:110`) is the survivor's skeleton. `SurvivorBase` names it as `skeletonName` and `meshObject` (`P:\DZ\characters\data\config.cpp:155` to `:158`). Despite the name it is what players use, and it is the block that declares the IK helpers, weapon bones, face bones and camera helpers. Guides that call it a test skeleton are wrong.
- `hermit_newbindpose.xob` (from `:2`) is what the infected bind (`skeletonName`, `P:\DZ\characters\zombies\config.cpp:76`). It shares the body bone names and is the only block that still has `index` values on bones other than `EntityPosition`.

Bone names must match exactly, PascalCase with the underscores. A wrong name logs `Bone X doesn't exist in skeleton OFP2_ManSkeleton` in the RPT and that bone does not move.

## Core and spine

| Bone | Note |
|---|---|
| `Scene_Root` | The outermost transform (`skeletons.anim.xml:112` in the survivor block, `:4` in the infected one). |
| `EntityPosition` | The bone the engine moves the entity with, `movement = "true"` (`:113`, and `:5`). Graph side: `anim-graphs.md`. |
| `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Neck1`, `Head` | `:120` to `:127` (survivor), `:8` to `:16` (infected). |
| `LookAt` | The look target, listed for the infected (`:17`) and `z_hermit.xob` (`:444`) but not the survivor. No `Pin` or `Pin Look At` bone exists. |

## Legs and arms

Legs, left and right alike: `LeftUpLeg`, `LeftUpLegRoll`, `LeftKneeExtra`, `LeftLeg`, `LeftLegRoll`, `LeftFoot`, `LeftToeBase`. Hip helpers: `LeftHipExtra`, `RightHipExtra`, `LeftHip_Helper`, `RightHip_Helper` (`:275` to `:278` survivor, `:104` to `:107` infected).

Arms, left and right alike: `LeftShoulder`, `LeftArm`, `LeftArmRoll`, `LeftForeArm`, `LeftForeArmRoll`, `LeftHand`, plus `RightArmExtra` on the right. Hand area helpers: `LeftHand_Dummy`, `LeftWristExtra`, `LeftForeArmExtra`, `LeftElbowExtra`, `LeftArmExtra` and their right mirrors (`:74` to `:78`, `:100` to `:103`, infected block).

## How the limbs hang together

Every limb joint has a twist bone between the two segments:

| Chain | Order |
|---|---|
| Arm | `Arm`, `ArmRoll`, `ForeArm`, `ForeArmRoll`, `Hand`, then the fingers |
| Leg | `UpLeg`, `UpLegRoll`, `Leg`, `LegRoll`, `Foot` |

So `RightHand` and `LeftHand` hang off `RightForeArmRoll` and `LeftForeArmRoll`, not the forearm. A tool that sets the wrist's world orientation through a local rotation must divide by the real parent. Skipping the roll bone leaks its rotation into the wrist and drops the fingers by up to about 11 cm, enough to take the trigger finger off the trigger. When a pose tool shows that symptom, draw the in game bone positions as overlay points before suspecting the quaternion convention.

Three more parents a guessed hierarchy gets wrong, measured while fitting a rider to a test vehicle, where 5 of 77 guessed parents were wrong and the worst would have lifted the pelvis 0.95 m:

- `Pelvis` hangs off `Scene_Root`. `EntityPosition` is not in the bind pose parent table, so where it sits is not checked.
- The `ElbowExtra` bones hang off the `ArmRoll` bones.
- The `HipExtra` bones hang off `Pelvis`.

`skeletons.anim.xml` has no `parent` attribute (only `index`, `movement` and `lod`), and a SEAnim from DayZATool's `--extract-anim` has names and keys but no parents. The bind pose model has them: `DayZATool.exe --extract-mdl DZ\characters\bodies\player_testing.xob` (`P:\DZ\characters\bodies\player_testing.xob`) writes `player_testing.semodel` with 148 bones and one root. Its header: `magic[7] = "SEModel"`, `version` uint16 at byte 7, `headerSize` uint16 at 9 (20), flags at 11 to 13, `boneCount` uint32 at 14 (148), `meshCount` at 18, `matCount` at 22, three reserved bytes, names from 29. Bone records are 73 bytes, the parent index an int32 right after one flags byte; 73 is the only record size that gives parents in range and exactly one root. DayZATool runs without a window but throws `InvalidOperationException` on `Console.ReadKey` when its input is redirected, after it has written the file, so ignore the exception and check the file exists.

## The hand helpers

- `RightHand_Dummy` is a helper, separate from `RightHand`. The survivor block lists it at `:115` with `lod = "1"`, next to `RightHand` at `:147`; the infected block has it at `:100` with `lod = "2"`, and `z_hermit.xob` at `:525`. A guide that calls it "a helper in lod 2" quotes the infected block.
- It carries what the player holds: moving it moves the item, and `Weapon_Root` hangs off it in the parent table.
- `LeftHand_Dummy` (`:116` survivor, `:74` infected) is the left mirror. The left hand follows the magazine in a reload; no magazine bones are in use (see "Bones marked for removal").

Measured in game on 1.30:

- The item in the hands sits on `RightHand_Dummy` within about 4 mm, and at rest the hands land exactly on the IK pose.
- So the right grip is rigid. If a clip turns the right hand against the item, the item turns too and the other hand slips off. Put any slack, such as a handle pivoting in the fist, on the left hand.
- `GetTransform` of an item in the hands misleads: its second row is the dummy's Z, its third the dummy's Y, and its first points against the model's +X. Do not place item parts with that X.

## Fingers

Per hand `Ring`, `Pinky`, `Middle`, `Index` and `Thumb`, numbered 1 to 4, such as `LeftHandIndex1` (`:208` to `:229` for the left hand). `Ring` and `Pinky` each also have an unnumbered base bone above the numbered ones: `LeftHandRing`, `LeftHandPinky` and their right mirrors. All `lod = "2"`: skip them on a first pass at a weapon clip and pose them for hand detail.

## IK helpers

Declared at `skeletons.anim.xml:149` to `:157`:

| Bones | Role |
|---|---|
| `RightHandOrigin`, `LeftHandOrigin` | IK origins. |
| `LeftHandIKTarget`, `LeftHandIK`, `RightHandIK` | IK chain ends. |
| `LeftForeArmDirection`, `RightForeArmDirection` and the two `...DirectionOrigin` bones | Elbow direction. |

The graph's weapon IK node names the roles: `ikpose_weaponoffset = RightHand_Dummy`, `ikpose_secchainoffset = LeftHandIKTarget`, `ikpose_chainoffset = RightHandOrigin` and the elbow directions (`P:\DZ\anims\workspaces\player\player_main\combat.agf:29` to `:35`). For a weapon clip, pose these helpers, not the raw forearm bones.

The helpers place the support hand but do not turn it. Measured in game on a custom weapon, turning `LeftHandIKTarget`, `LeftHandOrigin` or `LeftHand_Dummy` by 40 degrees changed nothing visible. Vanilla changes the support grip by turning the wrist bone `LeftHand` and the fingers: the two vanilla OTS-14 IK poses, handguard and forward grip, differ by 24.8 degrees on `LeftHand` and 20 to 55 degrees on the fingers, and not at all on the helpers or in position.

- To find which bones control a grip, extract two vanilla IK poses of one weapon with different grips (DayZATool to SEAnim) and compare them bone by bone.
- An extracted pose may not key `LeftHand` at all; the AKS-74U pose keys the helpers only. To author a wrist roll, start from a pose that keys `LeftHand`, such as an OTS-14 one.
- On a weapon whose geometry does not match the reference animation, turning `LeftHand` does nothing either (`weapon-in-hands.md`).

## The frame an IK pose is keyed in

Measured offline on five vanilla two handed IK poses, each extracted with DayZATool 1.3 (`--extract-anim <anm> 100`; 43 bones, one pose). Not checked on `P:\`, where the `.anm` files are binary.

An IK pose keys `LeftHandIKTarget` in the held object's frame, which is the frame of `RightHand_Dummy`: that bone's key (rotation R as an XYZW quaternion, translation t) takes the object to the hand. The right wrist in the object's frame, `p = -Rᵀt`, mirrors `LeftHandIKTarget` across the grip axis in the four symmetric grips (cm, SEAnim axes):

| IK pose | Right wrist, `-Rᵀt` | `LeftHandIKTarget` | Mirrored on | Worst axis off |
|---|---|---|---|---|
| `ik/two_handed/cookingpot.anm` | (-9.1, +14.2, +1.5) | (-8.6, -15.7, +1.1) | Y | 1.5 |
| `ik/two_handed/cauldron.anm` | (-9.0, +12.5, +5.4) | (-8.5, -12.9, +4.9) | Y | 0.5 |
| `ik/vehicles/batterytruck.anm` | (+29.4, +7.7, +6.1) | (-28.0, +8.0, +9.1) | X | 3.0 |
| `ik/vehicles/radiator_car.anm` | (-30.9, -10.0, +17.6) | (+29.4, -7.7, +24.9) | X | 7.3 |

`ik/two_handed/batterycar.anm` holds its battery off centre and mirrors nothing: (+16.2, -8.7, -0.5) against (-2.3, +19.5, +3.2). The truck battery and the radiator settle the quaternion convention, since read as `-Rt` their mirrors are 37 and 46 cm off; the pot's and cauldron's keys are near a half turn, so both readings agree there within 2.3 cm.

- `RightHandOrigin` mirrors nothing in the five, and its frame is not known. In game, a tray pose that counter rotated it with the object broke the right arm, so do not treat it as the object's frame.
- `LeftHandOrigin` equals `LeftHandIKTarget` in the pot's pose and sits 4 to 12 cm from it in the other four. Its frame was not tested alone.
- These three helpers are not in the bind pose model: the XML declares them, but the 148 bone parent table lacks them. It has `RightHandIK` and `LeftHandIK`, both under `RightHand_Dummy`.

In the object's frame SEAnim X is the model's X, SEAnim Y the model's Z (depth) and SEAnim Z the model's Y (up); the signs vary. The truck battery's wrists sit at +29.4 and -28.0 cm on SEAnim X, just past the ends of its first LOD (X ±26.0 cm, 24.0 cm tall, Z -11.1 to +12.0). The pot's sit at +14.2 and -15.7 cm on SEAnim Y, which cannot be its vertical: its first LOD is 25.6 by 24.2 by 26.5 cm with the base at the origin, so one wrist would be 14 cm up its side and the other 16 cm under its base. `GetTransform` of an item in the hands shows the same swap. In game, turning `RightHand_Dummy` 90 degrees about SEAnim Y tipped a tray over its long axis, so turning an object about its own vertical inside an IK pose should be a turn about SEAnim Z (inferred, not tried). When only the direction a held object points is wrong, turn the model instead (`items-in-hands.md`, "Turn the model, not the IK pose").

## Weapon bones

Declared at `skeletons.anim.xml:254` to `:264`, holsters at `:284` to `:286`:

| Bones | Role |
|---|---|
| `Weapon_Root` | The weapon's main anchor. |
| `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt` | Parts a player clip can move. Script maps a weapon's own selections onto them with `AddItemBoneRemap` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1580`). |
| `Weapon_Bone_01` to `Weapon_Bone_06` | Spare slots for more moving parts. |
| `Weapon_Holster`, `Pistol_Holster`, `Weapon2hnd_Holster` | Where a holstered or shouldered weapon hangs. |
| `weapon` | Lower case, an older name kept (`:290`). |

## Face and other helpers

Face bones (`:171` onward): `Face_Hub`, `Face_Jawbone`, `Face_Chin`, `Face_Eyelids`, `Face_Forehead`, the `Face_Brow`, `Face_Lip` and `Face_Cheek` groups, `Face_Tongue`, `EyeLeft`, `EyeRight`. All `lod = "2"`: for character mods, not gameplay clips.

| Bone | Role |
|---|---|
| `Opponent` | The entity being interacted with, such as a melee target (`:114`). |
| `Camera3rd_Helper`, `Camera1st_lock_dummy` | Camera anchors (`:117`, `:282`). |
| `Marker` | A general marker (`:289`). |

## Bones marked for removal

The survivor block ends with a group under the comment `To Be removed` (`:293` to `:302`): `Bullet`, `Trigger`, `Magazine`, `Bolt`, `Bullets_Magazine`, `Bullets_holder`, `Bullets_on_holder`, `Universal1`, `Universal2`. Do not use them; vanilla's bone remap uses the `Weapon_` bones above. A guide that treats them as standard is out of date.

## Bringing the skeleton into Blender

1. Take the names from the XML, or the official rig from Bohemia's public `DayZ-Misc` repository.
2. Build the armature with exactly these names.
3. For weapon work, key the IK helpers and `RightHand_Dummy`, which the engine reads.
4. Round trip before the game: export, read the file back with the inspector in `scripts/tools/dayz-animation-formats/`, and compare bone count and names. The RPT names any wrong bone on the first in game test.

## What 1.30 changed for skeletons

- The 250 bone limit across all skeletons is gone and the engine takes a bone's global index from its name (Bohemia's 1.30 changelog; not checked on `P:\`).
- In 19 of the 20 skeleton blocks only `EntityPosition` keeps an `index`, and seven list their other bones bare, such as `<bone name="Pelvis"/>` under `ovis_gmelini_skeleton.xob` (`:986` to `:989`). The first block, `hermit_newbindpose.xob`, still has an `index` on 24 bones (`Pelvis` at `:8` to `LookAt` at `:17`, and on), so the claim that every index but `EntityPosition`'s is gone does not match `P:\`.
- The XML's remaining job is each bone's `lod` and the bones the `.xob` lacks.

## The ragdoll bones

1.30 ships the player's ragdoll as text: `P:\DZ\characters\bodies\human.ragdoll`, named by the survivor's `ragdoll` key (`P:\DZ\characters\data\config.cpp:160`). It has 11 bodies, 73.9 kg in all, with collision shapes on `flesh.bisurf` (`human.ragdoll:9`):

| Ragdoll bone | Parent | Mass (kg) | Shapes | Joint limits, min then max | Stiffness / damper |
|---|---|---|---|---|---|
| `pelvis` (`:4`) | root | 17.0 | `Spine1` capsule r 0.1 h 0.2, `Spine2` capsule r 0.1 h 0.1 | none | none |
| `spine3` (`:22`) | `pelvis` | 15.0 | `Spine3` capsule r 0.12 h 0.1 | -15 -20 -35, 15 20 5 | 0.8 / 0.4 |
| `head` (`:38`) | `spine3` | 6.1 | `Head` sphere r 0.1 | -70 -35 -40, 70 35 45 | 0.8 / 0.3 |
| `leftarm` (`:53`), `rightarm` (`:84`) | `spine3` | 2.1 each | arm capsule r 0.04 h 0.25 | -15 -45 -45, 15 130 45 | default |
| `leftforearm` (`:68`), `rightforearm` (`:99`) | the arm | 1.7 each | forearm capsule r 0.04 h 0.2 | 0 -45 -45, no maximum set | default |
| `leftupleg` (`:117`), `rightupleg` (`:158`) | `pelvis` | 7.5 each | upper leg capsule r 0.05 h 0.425 | -5 -10 -120, 5 60 70 | damper 0.3 |
| `leftleg` (`:133`), `rightleg` (`:174`) | the upper leg | 6.6 each | leg capsule r 0.04 h 0.4, foot capsule r 0.03 h 0.175 | -5 -2 -5, 5 2 120 | damper 0.3 |
