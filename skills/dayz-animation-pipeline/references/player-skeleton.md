# Player skeleton: bones by zone

The bones of the DayZ player skeleton, grouped by zone, for mapping a Blender armature onto it when authoring `.txa`, `.anm` or `.rtm` clips. The names come from `P:\DZ\anims\cfg\skeletons.anim.xml`. Two of its blocks matter here:

- `player_testing.xob` (from :110) is the survivor's. `SurvivorBase` names it as `skeletonName` and as `meshObject` (`P:\DZ\characters\data\config.cpp:155` to `:158`). Despite the word "testing" it is the skeleton players use, and it is the block that declares the IK helpers, weapon bones, face bones and camera helpers.
- `hermit_newbindpose.xob` (from :2) is the one the infected bind (`skeletonName`, `P:\DZ\characters\zombies\config.cpp:76`). It shares the body bone names and is the only block that still carries `index` values.

Some guides call the first block a test skeleton and the second the production one. The configs say otherwise: `player_testing.xob` is the survivor's.

Bone names must match exactly. A mismatch logs `Bone X doesn't exist in skeleton OFP2_ManSkeleton` in the RPT and that bone does not move.

## Core and spine

| Bone | Note |
|---|---|
| `Scene_Root` | The outermost transform (`P:\DZ\anims\cfg\skeletons.anim.xml:112` in the survivor block, `:4` in the infected one). |
| `EntityPosition` | The bone the engine moves the entity with: `movement = "true"` (`P:\DZ\anims\cfg\skeletons.anim.xml:113`, and `:5`). Graph side: `anim-graph.md`. |
| `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Neck1`, `Head` | `skeletons.anim.xml:120` to `:127` (survivor), `:8` to `:16` (infected). |
| `LookAt` | The look target. It is listed for the infected skeleton (`P:\DZ\anims\cfg\skeletons.anim.xml:17`) and for `z_hermit.xob` (`:444`); the survivor block does not list it. There is no `Pin` or `Pin Look At` bone anywhere. |

## Legs (left and right alike)

`LeftUpLeg`, `LeftUpLegRoll`, `LeftKneeExtra`, `LeftLeg`, `LeftLegRoll`, `LeftFoot`, `LeftToeBase`, and the `Right` set. Hip helpers: `LeftHipExtra`, `RightHipExtra`, `LeftHip_Helper`, `RightHip_Helper` (`skeletons.anim.xml:275` to `:278` for the survivor, `:104` to `:107` for the infected).

## Arms (left and right alike)

`LeftShoulder`, `LeftArm`, `LeftArmRoll`, `LeftForeArm`, `LeftForeArmRoll`, `LeftHand`, and the `Right` set plus `RightArmExtra`. Hand area helpers: `LeftHand_Dummy`, `LeftWristExtra`, `LeftForeArmExtra`, `LeftElbowExtra`, `LeftArmExtra` and their `Right` mirrors (`skeletons.anim.xml:74` to `:78`, `:100` to `:103`, in the infected block).

### The hands hang off the twist bones, not the forearm

The parent of `RightHand` and `LeftHand` is `RightForeArmRoll` and `LeftForeArmRoll`, the twist bone, not the forearm: forearm, then forearm roll, then hand, then fingers (`ofp2-manskeleton-parents.txt`). A tool that sets the wrist's world orientation through a local rotation must divide by the real parent. Skipping the roll bone leaks its rotation into the wrist and drops the fingers by up to about 11 cm, so the trigger finger leaves the trigger. In the weapon viewer this was first misread as a mirrored quaternion; it was found by drawing the in-game bone positions as overlay points, not by reasoning about quaternion conventions.

### A twist bone sits at every limb joint

```
Arm   -> ArmRoll   -> ForeArm -> ForeArmRoll -> Hand
UpLeg -> UpLegRoll -> Leg     -> LegRoll     -> Foot
```

Forward kinematics that walks arm to forearm, or upper leg to leg, skips a bone and leaks its rotation the same way.

Three more facts a guessed hierarchy gets wrong (measured while fitting a quad's rider, where 5 of 77 guessed parents were wrong and the worst would have lifted the pelvis 0.95 m):

- `Pelvis` hangs off `Scene_Root`. `EntityPosition`, the movement bone, is its sibling, not its parent.
- The `ElbowExtra` bones hang off the `ArmRoll` bones.
- The `HipExtra` bones hang off `Pelvis`.

### Where the parent table comes from

The obvious sources do not carry it. `P:\DZ\anims\cfg\skeletons.anim.xml` has no `parent` attribute anywhere, only `index`, `movement` and `lod`. A SEAnim file written by DayZATool's `--extract-anim` carries names and keys but no parents. The bind pose model does: `DayZATool.exe --extract-mdl DZ\characters\bodies\player_testing.xob` (`P:\DZ\characters\bodies\player_testing.xob`) writes `player_testing.semodel` with 148 bones and one root.

The SEModel header as read from the bytes: `magic[7] = "SEModel"`, `version` uint16 at 7, `headerSize` uint16 at 9 (20), presence flags at 11 to 13, `boneCount` uint32 at 14 (148), `meshCount` at 18, `matCount` at 22, three reserved bytes, names from offset 29. Bone records are 73 bytes each with the parent index as int32 right after one flags byte. The check that makes the read trustworthy: 73 is the only record size that gives parents in range and exactly one root. The full table is `ofp2-manskeleton-parents.txt`.

DayZATool runs from a shell with no window, but throws `InvalidOperationException` on `Console.ReadKey` when its input is redirected. It does so after writing the output, so ignore the exception and check that the file exists.

### `RightHand_Dummy` and `LeftHand_Dummy`

- `RightHand_Dummy` is a helper, distinct from the hand bone `RightHand`. The survivor block lists it at `P:\DZ\anims\cfg\skeletons.anim.xml:115` with `lod = "1"`, next to `RightHand` at `:147`. The infected block has it at `:100` with `lod = "2"`, and `z_hermit.xob` at `:525`. A guide that calls it "a helper in lod 2" is quoting the infected block's value.
- It anchors what the player holds. Moving `RightHand_Dummy` moves the held item. In the parent table `Weapon_Root` hangs off it.
- `LeftHand_Dummy` (`P:\DZ\anims\cfg\skeletons.anim.xml:116` for the survivor, `:74` for the infected) is the same helper on the left. The left hand is what follows the magazine in a reload; there are no magazine bones in use (see "Marked for removal").
- The names are exact: PascalCase with one underscore, never "right hand dummy".

Measured in game (DayZ 1.30.164014 Experimental):

- The item in hands sits on `RightHand_Dummy` within about 4 mm, and at rest the hands fall exactly on the IK pose.
- So the right grip is rigid. If a clip turns the right hand relative to the item, the item turns with it and the other hand slips out of its grip. Put any slack, such as a handle pivoting in the fist, on the left hand.
- `GetTransform` of an item in hands is a trap: its second row is the dummy's Z, its third the dummy's Y, and its first points opposite to the model's +X as drawn. Do not place item parts with that X.

## Fingers

Per hand: `Ring`, `Pinky`, `Middle`, `Index` and `Thumb`, each numbered 1 to 4, for example `LeftHandIndex1` (`skeletons.anim.xml:54` to `:73` for the left hand). All `lod = "2"`: leave them for a first pass at a weapon clip, and pose them for hand detail.

## IK helpers

Declared at `P:\DZ\anims\cfg\skeletons.anim.xml:149` to `:157`:

| Bones | Role |
|---|---|
| `RightHandOrigin`, `LeftHandOrigin` | IK origins. |
| `LeftHandIKTarget`, `LeftHandIK`, `RightHandIK` | IK chain ends. |
| `LeftForeArmDirection`, `RightForeArmDirection`, and the two `...DirectionOrigin` bones | Elbow direction. |

The graph's weapon IK node names these roles itself: `ikpose_weaponoffset = RightHand_Dummy`, `ikpose_secchainoffset = LeftHandIKTarget`, `ikpose_chainoffset = RightHandOrigin` and the elbow directions (`P:\DZ\anims\workspaces\player\player_main\combat.agf:29` to `:35`). When authoring a weapon clip, pose these helpers, not the raw forearm bones.

**Position is not orientation.** Measured in game on a custom weapon (2026-06-17): the helpers place the support hand, but turning `LeftHandIKTarget`, `LeftHandOrigin` or `LeftHand_Dummy` by 40 degrees changed nothing visible. Vanilla changes the support hand's grip by turning the wrist bone `LeftHand` and the finger bones. Evidence: the two vanilla OTS-14 IK poses for the same weapon, one on the handguard and one on the forward grip, differ by 24.8 degrees on `LeftHand` and 20 to 55 degrees on the fingers, with no difference on the helpers and none in position.

- **A reusable technique:** extract two vanilla IK poses of one weapon with different grips (DayZATool to SEAnim), and compare bone by bone. The bones that differ are the ones that control the grip.
- **A caveat:** an extracted pose may not key `LeftHand` at all. The AKS-74U pose keys the helpers only. To author a wrist roll, start from a pose that keys `LeftHand`, such as an OTS-14 one.
- **A limit found later:** on a weapon whose geometry does not match the reference animation, turning `LeftHand` did nothing either; see `skills/_shared/weapons/hand-animation-and-grip.md`.

### The frame an IK pose is keyed in

Measured offline on five vanilla two handed IK poses, each extracted with DayZATool 1.3 (`--extract-anim <anm> 100`; 43 bones, one pose). Not checked on `P:\`, where the `.anm` files are binary.

An IK pose keys `LeftHandIKTarget` in the held object's frame, which is the frame of `RightHand_Dummy`: that bone's key (rotation R as a quaternion in XYZW order, translation t) takes the object to the hand. The right wrist expressed in the object's frame, `p = -Rᵀt`, mirrors `LeftHandIKTarget` across the grip axis in the four symmetric grips (cm, SEAnim axes):

| IK pose | Right wrist, `-Rᵀt` | `LeftHandIKTarget` | Mirrored on | Worst axis off |
|---|---|---|---|---|
| `ik/two_handed/cookingpot.anm` | (−9.1, +14.2, +1.5) | (−8.6, −15.7, +1.1) | Y | 1.5 |
| `ik/two_handed/cauldron.anm` | (−9.0, +12.5, +5.4) | (−8.5, −12.9, +4.9) | Y | 0.5 |
| `ik/vehicles/batterytruck.anm` | (+29.4, +7.7, +6.1) | (−28.0, +8.0, +9.1) | X | 3.0 |
| `ik/vehicles/radiator_car.anm` | (−30.9, −10.0, +17.6) | (+29.4, −7.7, +24.9) | X | 7.3 |

`ik/two_handed/batterycar.anm` holds its battery off centre and mirrors nothing: (+16.2, −8.7, −0.5) against (−2.3, +19.5, +3.2). The truck battery and the radiator settle the quaternion convention: read as `-Rt` instead, their mirrors are 37 and 46 cm off. The pot's and the cauldron's keys are close to a half turn, so both readings agree within 2.3 cm there and decide nothing.

- `RightHandOrigin` mirrors nothing in the five, and its frame is not known. In game (a tray item, DayZDiag 1.29) a pose that counter rotated it along with the object broke the right arm. Do not treat it as the object's frame.
- `LeftHandOrigin` equals `LeftHandIKTarget` in the pot's pose and sits 4 to 12 cm from it in the other four. Its frame was not tested on its own.
- These three helpers are not bones of the bind pose model: the XML declares them, and the 148 bone parent table has none of them. It has `RightHandIK` and `LeftHandIK`, both under `RightHand_Dummy`. No table gives the three helpers' frame; the mirror above is the evidence.

**Axes.** In the object's frame SEAnim X is the model's X, SEAnim Y the model's Z (depth) and SEAnim Z the model's Y (up); the signs are not fixed.

- The truck battery's wrists sit at +29.4 and −28.0 cm on SEAnim X, just past the ends of its first LOD (X ±26.0 cm, 24.0 cm tall, Z −11.1 to +12.0).
- The pot's sit at +14.2 and −15.7 cm on SEAnim Y, which cannot be the pot's vertical: its first LOD is 25.6 × 24.2 × 26.5 cm with the base at the origin, so one wrist would be 14 cm up its side and the other 16 cm under its base.
- `GetTransform` of an item in hands shows the same swap in game.
- In game, turning `RightHand_Dummy` 90 degrees about SEAnim Y tipped a tray over its long axis. So turning an object about its own vertical inside an IK pose is a turn about SEAnim Z. That is inferred, not tried in game.

When only the direction a held object points is wrong, turn the model instead (`item-ik-and-hide.md`, "Turn the model, not the IK pose").

## Weapon bones

Declared at `P:\DZ\anims\cfg\skeletons.anim.xml:254` to `:264`, the holsters at `:284` to `:286`:

| Bones | Role |
|---|---|
| `Weapon_Root` | The weapon's main anchor. |
| `Weapon_Bullet`, `Weapon_Trigger`, `Weapon_Magazine`, `Weapon_Bolt` | Weapon parts a player clip can move. Script maps a weapon's own selections onto them with `AddItemBoneRemap` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1580`). |
| `Weapon_Bone_01` to `Weapon_Bone_06` | Spare slots for further moving parts. |
| `Weapon_Holster`, `Pistol_Holster`, `Weapon2hnd_Holster` | Where a holstered or shouldered weapon hangs. |
| `weapon` | Lower case, an older name kept (`skeletons.anim.xml:290`). |

## Face

`Face_Hub`, `Face_Jawbone`, `Face_Chin`, `Face_Eyelids`, `Face_Forehead`, the `Face_Brow`, `Face_Lip` and `Face_Cheek` groups, `Face_Tongue`, `EyeLeft`, `EyeRight` (`skeletons.anim.xml:171` onward). All `lod = "2"`: relevant for character mods, not for gameplay clips.

## Other helpers

| Bone | Role |
|---|---|
| `Opponent` | The entity being interacted with, such as a melee target (`skeletons.anim.xml:114`). |
| `Camera3rd_Helper`, `Camera1st_lock_dummy` | Camera anchors (`skeletons.anim.xml:117`, `:282`). |
| `Marker` | A general marker (`skeletons.anim.xml:289`). |

## Marked for removal: do not use

The survivor block ends with a group under the comment `To Be removed` (`P:\DZ\anims\cfg\skeletons.anim.xml:293` to `:302`): `Bullet`, `Trigger`, `Magazine`, `Bolt`, `Bullets_Magazine`, `Bullets_holder`, `Bullets_on_holder`, `Universal1`, `Universal2`. They are still listed, but Bohemia has marked them for removal and the weapon bones above (`Weapon_Bolt`, `Weapon_Magazine` and the rest) are what vanilla's bone remap uses. A guide that treats any of them as standard is out of date.

## Bringing the skeleton into Blender

1. Take the bone names from the XML above, or the official rig from Bohemia's public `DayZ-Misc` repository.
2. Build the armature with exactly these names, PascalCase with the underscores.
3. For weapon work, key the IK helpers and `RightHand_Dummy`, since those are what the engine reads.
4. Round trip before the game: export, read the file back with the inspector in `scripts/tools/dayz-animation-formats/`, and compare the bone count and names. The RPT names any wrong bone on the first in-game test.

## What 1.30 changed for skeletons

- The limit of 250 bones across all skeletons is gone, and the engine takes a bone's global index from its name instead of the XML (Bohemia's 1.30 changelog; not checked on `P:\`).
- In the 1.30 XML most skeletons carry no `index` any more: in 19 of the 20 skeleton blocks only `EntityPosition` has one, and seven of them list their other bones bare, for example `<bone name="Pelvis"/>` under `ovis_gmelini_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:986` to `:989`). The first block, `hermit_newbindpose.xob`, still has an `index` on 24 bones (`Pelvis` at `:8` to `LookAt` at `:17`, and on). A claim that every index except `EntityPosition`'s is gone is not what the file on `P:\` shows.
- So the XML's remaining job is the `lod` of each bone and the bones the `.xob` lacks.

### The ragdoll bones

1.30 ships the player's ragdoll as text: `P:\DZ\characters\bodies\human.ragdoll`, named by the survivor's `ragdoll` key (`P:\DZ\characters\data\config.cpp:160`). It has 11 bodies with a total mass of 73.9 kg, their collision shapes using `flesh.bisurf` (`P:\DZ\characters\bodies\human.ragdoll:9`):

| Ragdoll bone | Parent | Mass (kg) | Shapes | Joint limits, min then max | Stiffness / damper |
|---|---|---|---|---|---|
| `pelvis` (`:4`) | root | 17.0 | `Spine1` capsule r 0.1 h 0.2, `Spine2` capsule r 0.1 h 0.1 | none | none |
| `spine3` (`:22`) | `pelvis` | 15.0 | `Spine3` capsule r 0.12 h 0.1 | −15 −20 −35, 15 20 5 | 0.8 / 0.4 |
| `head` (`:38`) | `spine3` | 6.1 | `Head` sphere r 0.1 | −70 −35 −40, 70 35 45 | 0.8 / 0.3 |
| `leftarm` (`:53`), `rightarm` (`:84`) | `spine3` | 2.1 each | arm capsule r 0.04 h 0.25 | −15 −45 −45, 15 130 45 | default |
| `leftforearm` (`:68`), `rightforearm` (`:99`) | the arm | 1.7 each | forearm capsule r 0.04 h 0.2 | 0 −45 −45, no maximum set | default |
| `leftupleg` (`:117`), `rightupleg` (`:158`) | `pelvis` | 7.5 each | upper leg capsule r 0.05 h 0.425 | −5 −10 −120, 5 60 70 | damper 0.3 |
| `leftleg` (`:133`), `rightleg` (`:174`) | the upper leg | 6.6 each | leg capsule r 0.04 h 0.4, foot capsule r 0.03 h 0.175 | −5 −2 −5, 5 2 120 | damper 0.3 |

The masses, joint limits and shape sizes were all read on `P:\`.
