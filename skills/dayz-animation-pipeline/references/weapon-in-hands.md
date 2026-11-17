# Weapon in the hands: grip, sights and the memory points a weapon needs

How a custom weapon sits in the player's hands is decided by three things, and only one of them is in the weapon's `.p3d`:

1. **The player's clips.** The weapon's instance file (`player_main_rifle.asi`, `weapons\player_main_akm.asi` and so on) and its IK pose place the hands. A weapon `.p3d` carries no hand points: the Memory LOD of a debinarized vanilla `akm.p3d` (read 2026-06-11) has no hand or grip selection. The bones involved are in `player-skeleton.md` (`RightHand_Dummy`, the IK helpers); the instance files are in `anim-graph.md`.
2. **The weapon's frame.** The engine hangs the model's origin on the hand (the `RightHand_Dummy` and `Weapon_Root` chain). How the grip and the handguard lie relative to the origin, on the vanilla weapon whose clips the custom weapon inherits, is the grip contract. If the custom weapon's grip and handguard occupy the same region of model space as the reference's, the inherited hands land correctly.
3. **The weapon's memory points:** muzzle, ejection, axes, sight.

So checking a grip means comparing geometry with the reference weapon in the same model space. That is what `weapon_grip_viewer.py` draws and checks.

The short, checked version of the grip findings is in `skills/_shared/weapons/hand-animation-and-grip.md`. Results below marked as measured in game are not checked on `P:\`.

## Memory points of a vanilla rifle (AKM)

Read from the Memory LOD of a debinarized `akm.p3d`; coordinates rounded, model space, muzzle toward −X, Y up. The point names all occur in the binarized `P:\DZ\weapons\firearms\akm\akm.p3d`; the coordinates cannot be checked there without converting the model. Where the meaning is marked "not checked" it fits the pattern but was not confirmed: keep the vanilla shape.

| Name | Points | On the AKM | Meaning |
|---|---|---|---|
| `eye` | 1 | (0.23, 0.15, −0.01): 5.2 cm above the bore, on the bore's Z | Camera anchor for iron sights. |
| `usti hlavne` | 1 | (−0.4331, 0.0976, −0.0102) | Muzzle tip (Czech for "barrel mouth"): muzzle flash and where the projectile leaves. |
| `konec hlavne` | 1 | (−0.0252, 0.0976, −0.0102) | Rear end of the barrel. Same Y and Z as the muzzle: the two define the bore line. |
| `nabojnicestart`, `nabojniceend` | 1 each | Direction up, right and to the rear | Path of the ejected case. |
| `bolt_axis` | 2 | Parallel to the bore | Travel of the bolt or charging handle. |
| `trigger_axis` | 2 | Across the weapon (±Z) at the trigger | Trigger animation axis. |
| `magazine_axis` | 2 | Roughly vertical (−Y) | Magazine animation axis; exact use not checked. |
| `recoil` | 2 | Same coordinates as `magazine_axis` | Recoil axis; not checked. |
| `weapon back` | 1 | (0.0712, 0.0976, −0.0102), on the bore line | Rear anchor; possibly the back holster, not checked. |
| `ce_center`, `ce_radius` | 1 each | | Placement sphere for the central economy. |
| `invview` | 1 | | Inventory preview camera. |
| `boundingbox_min`, `boundingbox_max` | 1 each | | Bounds. |

What script and config read from these names is in `skills/_shared/weapons/model-selections.md`.

Rules worth enforcing on any custom rifle. Each was broken by a real generated build of an MK47 (2026-06-11) and caught by the checker:

- `usti hlavne` and `konec hlavne` share Y and Z, a level bore. The MK47 had the rear point 4.6 cm high, which tilted the line of fire 6.3 degrees.
- `bolt_axis` is parallel to the bore.
- `magazine_axis` and `recoil` point the way the reference family's do (roughly vertical on the AKM; the MK47 had them sideways, 90 degrees off).
- The ejection direction is within about 25 degrees of the reference (the MK47 was 42 degrees off, with no rearward part).
- The height of `eye` over the bore is close to the reference (about 5 cm for AKM irons). An eye at rail height changes the sight camera.

## The grip viewer and checker

```cmd
python <skill-dir>\scripts\weapon_grip_viewer.py --weapon MyRifle.p3d --ref akm_mlod.p3d --ref-label "AKM vanilla" --out grip_viewer.html --report grip_report.json
```

- Both inputs must be MLOD and in their final model space, with every offset applied. A binarized reference has to be converted to MLOD first with a converter the user supplies; none ships here.
- The command line prints the checklist and the findings, so it works without a browser and in automation.
- The page adds: the custom mesh with a translucent ghost of the reference, both sets of memory points, the bore line and the sight line with their deviations, the axes at the model origin (the hand anchor), and estimated hand zones taken from the reference (the grip is below and behind the middle of `trigger_axis`; the support hand is at the handguard proxy anchor, or 55 percent along the bore).
- The hand zones are estimates. The real pose is the player's clip; the honest check is how the grip and handguard overlap the ghost.
- The overlays are unlit so lighting cannot hide them, and proxy triangles are stripped from the first LOD, because they otherwise draw as giant spikes.
- three.js comes through the shared viewer core, as the script's header describes. Open the page once and check it renders before handing it to the user.

## Fitting the hands: one offset for the whole model

When the custom weapon inherits a vanilla base (for example the AKM's clips), parity comes from moving the whole model, geometry, memory points and proxies together, by one offset, so that its bore and grip have the reference's relation to the origin. Never move the grip alone.

Worked example, an MK47 build: its assembler applies one global offset (+0.0326 on Y, −0.0102 on Z, taken from matching `usti hlavne` with the AKM's) exactly once when the model is assembled. Check that an offset is applied once; applying it twice is the classic failure. Then run the grip viewer again on the final `.p3d` taken out of the PBO.

## Turning the wrist in the IK pose does not turn the hand

Measured in game on a custom submachine gun with no hand memory points, inheriting the AKS-74U clips, 2026-06-17.

Rotating the `LeftHand` bone in the IK pose did not reorient the support hand. The engine's IK lines the hand up with the weapon again and absorbs the wrist rotation. Four variants of the IK pose with `LeftHand` turned 90 degrees about different local axes (120 to 180 degrees apart) all rendered the same. A pixel difference of the hand region gave RMS 7.8 for a 180 degree wrist roll, less than a change of finger curl (RMS 11). What the IK pose does drive visibly is the finger curl (the `LeftHand` thumb, index, middle, ring and pinky bones).

So the way to change how the support hand is oriented on a custom weapon is geometric parity: a reference clip whose hand already sits that way, checked with `weapon_grip_viewer.py`, or a change to the weapon's geometry or offset.

Do not over-read a difference between two vanilla IK poses. Two poses of one weapon (the OTS-14 held normally and by its barrel handle) do differ on `LeftHand`, but both were authored against a weapon that has grip parity. That does not mean rotating `LeftHand` on a weapon without parity reproduces the orientation.

## Testing pose and grip variants in game without fooling yourself

From the same tests, 2026-06-17:

- **Compare on the same weapon.** Make one `CfgWeapons` class deriving from the real weapon per IK pose variant and register each clone with its own clip through `AddItemInHandsProfileIK`. Comparing variants across different weapons mixes in each weapon's balance and handguard, which swamps the difference being read.
- **When the difference is small, measure it.** Take the RMS difference of the hand region between variants and against a change known to be visible (a finger curl), to separate signal from capture noise such as lighting and timing.
- **Run that measurement on full resolution crops only.** A whole panel RMS over a scaled down contact sheet, where the support hand is about 30 pixels, once led to a working grip being called inert; the user's eye on the full image saw the closed grip that the thumbnail hid. RMS answers "did anything change", not "is it right". Crop the hand zone from the full resolution capture of each angle and look at it.
- **Capture conditions.** A fully overcast scene (`overcast` at 1.0) kills the glint that washes the weapon white. Capture all variants quickly so exposure does not drift between them. In a cycle over several weapons, keep the wait per weapon shorter than the cycle period, or the captures slip onto the next weapon.

## The fix that worked: raise the weapon to the hand

Measured in game on the same submachine gun, 2026-06-23. After every lever on the player's side had been shown to do nothing in game (the IK target's position and rotation in the IK pose, the behaviour flag, forward kinematics on `LeftHand`), the grip was fixed by the geometry. The weapon's bore sat 2.4 cm lower over the weapon's origin than on a working reference (bore at Y 0.090 on the reference against 0.066), so the support hand, which lands at a fixed point in skeleton space, came down on top of the barrel. Moving the whole model up 0.024 on Y raised the weapon into the hand and the hand closed on the foregrip. The idle grip was right in game.

The rule: when moving the IK targets does nothing, stop tuning the animation. Move the weapon to the hand, not the hand to the weapon.

### Working mods use vanilla IK poses and matching geometry

A third-party weapon pack that shows a closed foregrip grip was taken apart (third-party mod behaviour, not vanilla). The whole technique is the plain call `AddItemInHandsProfileIK(class, a rifle parent .asi, the firearms behaviour, a vanilla IK pose, states)`. The lever is choosing a vanilla IK pose whose `LeftHandIKTarget` lands where the weapon really has a handguard; it used the poses vanilla registers for the `Vikhr` and `PM73Rak_Base` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:434`, `:425`). There is no custom player animation mod, no changed base pose and no scripted bone work.

So a custom weapon gets its grip from three things: the firearms behaviour, a stock vanilla IK pose, and geometry where that pose lands. It does not need a full player animation mod.

### The IK pose is shared by all stances

The IK pose (the fourth argument) applies to every stance. The base raised pose differs per stance (the `Locomotion.<stance>Ras` idle, aim and sight lines), and the aim lines add the aim space clip, which opens the support hand. So a geometry and IK pose pair that closes the idle grip can still leave the aim grip open, with the hand off the weapon and the front "floating". Rolling the wrist in the shared IK pose cannot close only the aim. The fix per stance is to override the weapon's aim and sight `Locomotion` lines in a child `.asi`: the parent rifle instance maps them, and third-party weapon packs override them.

On the measured submachine gun that worry did not come true (check of 2026-06-23): the same raise that closed the idle also closed the aim in third person, comparable to the reference. Lifting the weapon into the hand served both stances, because both base poses anchor the support hand to the same zone relative to the weapon. Keep the per stance override as the fallback for a weapon that still shows an open aim grip after the idle is closed.

### Forcing the aim stance for a capture: on the client

To capture the aim grip of a scripted or spawned player, force the raise every frame with `OverrideRaise(HumanInputControllerOverrideType.ENABLED, true)` on the input controller (`P:\scripts\3_game\human.c:268`). In the enum `HumanInputControllerOverrideType`, `ENABLED` stays active until `DISABLED` is passed and `ONE_FRAME` applies once (`P:\scripts\3_game\human.c:7` to `:11`); with `ONE_FRAME` the pose flickers and drops back to idle.

- **It must run on the client**, not in the server mission's `init.c`. The captured character is the client's own player, and a server side override does not move the pose the client renders: the server logged the raise while the weapon rendered lowered. Ship it as a `modded class MissionGameplay` with an `OnUpdate` override in a small test mod that declares a `missionScriptModule`.
- The third person aim pose depends only on the movement state being raised (`m_MovementState.IsRaised()`, `P:\scripts\4_world\entities\dayzplayerimplement.c:1742`), so a held raise is enough.
- Do not call `SetIronsights()`. It forces the sight camera, fights a free camera, and on the server side left the weapon untextured.
- `WeaponADS()` is an input flag (`P:\scripts\3_game\human.c:86`) and has no override among the input controller's `Override...` methods, which run from `OverrideMovementSpeed` to `OverrideFreeLook` (`P:\scripts\3_game\human.c:253` to `:274`). It reads 0 even when aiming works. The success signal is `IsRaised()` or the client log.
- Keep a matching `OverrideRaise` on the server so the server agrees.

The full recipe with a drop in snippet is in the dayz-mcp-verify skill.

## How a custom weapon animation is bound

A custom weapon animation reaches the player through three separate artifacts, bound per item class in script. None of them edits the player graph, so several mods can each do it (`anim-graph.md`, "Which changes collide").

- `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` (`P:\scripts\3_game\dayzplayer.c:243`) binds the weapon class to its instance file, an IK pose and a weapon states clip.
- `AddItemBoneRemap(itemClass, pairs)` (`P:\scripts\3_game\dayzplayer.c:252`) maps the weapon's part selections to the player skeleton's `Weapon_` bones.

Do not mix up the three kinds of clip. The frame counts are from DayZATool extracts of the vanilla AKM clips:

| Artifact | What it is | Vanilla AKM | Where it is named |
|---|---|---|---|
| IK pose (`ik/weapons/<weapon>.anm`) | One static placement of hands and fingers on the gun. | 2 frames at 30 frames per second, the second a byte exact copy of the first, so one pose. The AKM's instance reuses the `izh18` pose (`IkPose` line, `P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:6`). | The `IkPose` line of the `.asi`; the fourth argument of `AddItemInHandsProfileIK`. |
| Weapon states (`w_<weapon>_states.anm`) | Drives only the `Weapon_` bones: bolt and bullet. | 2 distinct frames (`Weapon_Bolt` slides, `Weapon_Bullet` ejects). Not a fixed 3; Workbench trims to 2 to 4 keys per channel. | The fifth argument; `SetInitState` reads it. |
| Action clips (reload, fire, chamber, jam) | Authored as differences, roughly shoulders down, played over the idle. | Magazine removal 22 frames, full swap 55, charging handle 44, chambering 107, fire 11, jam 230, all at 30 frames per second. | The `Lines` of the `.asi`. |

The action clips play on top of the weapon states clip and override those bones while they play. The IK chain itself is set up in the graph's weapon IK node (the `ikpose_` keys, `P:\DZ\anims\workspaces\player\player_main\combat.agf:29` to `:35`), not in any config file. The `reloadAction` key of `CfgWeapons` is legacy and is not how reloads are driven; leave it out, as vanilla rifles do (`weapon-anim-blender-complete.md`, "The `reloadAction` key is legacy").

## Reproducing the grip in an offline viewer

What decides the grip, and how far it can be reproduced offline without guessing (worked out 2026-06-28).

### What sets the grip, the complete list

1. **Attachment.** The weapon mounts by its model origin on `Weapon_Root` and `RightHand_Dummy`. The weapon `.p3d` has no hand points.
2. **The hands are the weapon's IK pose**, the fourth argument of `AddItemInHandsProfileIK`. Checked by extracting a custom grip clip with DayZATool: 43 bones, keying the IK helpers (`RightHandOrigin`, `LeftHandOrigin`, `LeftHandIKTarget`, the `ForeArmDirection` bones) and the fingers, not the raw `LeftHand` and `RightHand`. That clip inherits the AKS-74U pose.
3. **Where the weapon lies relative to its origin.** The hand falls at a fixed point of the IK pose; the weapon's geometry is moved (one global offset) so its grip falls there. A short submachine gun, with about 0.18 m between pistol grip and foregrip, has no parity with a rifle hand spacing of about 0.33 m, so the support hand does not grip until parity is reached.
4. **Stance and aim.** The aim space clip (`P:\DZ\anims\anm\player\layered\aim\2handed\p_2hd_erc_aimspace.anm`, 39 frames forming a two dimensional grid of directions, per its DayZATool extract) is neutral at its centre frame, index 19: at most 0.7 degrees, mostly 0.0. So there is no separate sight pose to add at the centre. The plugin's sample base pose `Rifle_Erect_Idle_Ras (Soft_Aim).txa` already is the raised aim at centre; the aim space only deflects when aiming up, down or to the sides.

### A Blender pipeline that reads the real grip offline

Take the plugin's sample rig that has IK bones (`Poses/Rifle/M4 Rifle IK.blend` in its sample assets: 155 bones, with real constraints from the hands to `RightHandOrigin` and `LeftHandOrigin`). Apply the base pose `.txa` through the plugin, then the grip IK pose as a plugin action on its IK helper bones. The rig's IK then resolves the hands onto the weapon, and the world transforms of `Weapon_Root`, hands and fingers can be read. The base raised pose gives a rifle hand spacing of about 0.33 m; the M4 pose combined gave 0.326 m, which confirms the base pose already is the rifle configuration.

### Why it does not close fully offline

Applying a specific weapon's IK pose (its `.anm` or SEAnim) directly offline runs into the bone frame convention for rotations, which only the game settles for good. `Weapon_Root` on the plugin's rig without IK bones poses the weapon crossed or upside down (measured); the rig with IK bones poses it properly, so use that one. Do not guess: orienting the weapon by a finger axis, a fixed −90 degree turn on the support wrist, nudging it forward. About eight such variants were tried, and all failed or did not carry to another weapon.

### Tools and the reference capture

- DayZATool: `--extract-anim <input.anm> <scale=100>` takes no output path and writes the `.seanim` next to the input; `--generate-anim` is the reverse. The vanilla aim and IK pose clips are under `P:\DZ\anims\anm\player\layered\aim\` and `P:\DZ\anims\anm\player\ik\weapons\`.
- Keep in-game reference captures (the grip closed on the foregrip). A capture run on the retail client took 10 to 15 minutes, so reuse captures instead of repeating them lightly.

### Starting the viewer from the right pose

Model: the base pose (the raised aim), the weapon on `Weapon_Root` with its parity geometry, and the hands in the IK pose's configuration, not a guessed hand fit. For the viewer to be editable its pose function must rebuild from the base pose's forward kinematics, not from the T pose.

## The elbow cannot be derived offline: read it from the live skeleton

Measured in game, 2026-06-28. Offline resolution of the IK pose gets the hands right, because the IK target positions are static data. The elbow is resolved by the engine's IK at run time from the forearm direction pole and does not come out cleanly offline: the plugin's Blender pole gave a winged elbow, and a plain swivel guess went the opposite way (the right elbow guessed tucked, measured 81.7 degrees open; the left 50.4). Do not iterate on it by eye.

The reliable source is a dump of the live player skeleton in model space:

- **Calls.** `GetBoneIndexByName` on `Human` (`P:\scripts\3_game\human.c:1417`; vanilla uses it on the player for `RightHand_Dummy` at `P:\scripts\4_world\entities\dayzplayerimplement.c:628`), then `GetBonePositionMS` and `GetBoneRotationMS` on `Object` (`P:\scripts\3_game\entities\object.c:237`, `:242`). Model space is relative to the player entity, so the pose does not depend on where the player stands or faces. Only −1 from `GetBoneIndexByName` means a missing bone; valid ids can be negative (`vehicle-rider-ik-pose.md`).
- **Mechanism.** A client side `modded class MissionGameplay` that forces the raise (`OverrideRaise`, above) and, once `IsWeaponRaiseCompleted()` is true (`P:\scripts\4_world\entities\dayzplayerimplement.c:935`) and about 120 frames have settled, prints each bone's model space position and quaternion once. The `Print` lands in the client's `script_*.log` in its profile folder, not in the RPT.
- **Enforce Script.** Build the printed string in single line statements (`ln = ln + ...`). An expression continued with `+` over several lines is a compile error.
- **From game model space to a three.js viewer.** Position is `(x, y, −z)`: the flip of Z takes Enfusion's left handed space to three.js's right handed one. The matching quaternion flip `(−x, −y, z, w)` rendered mirrored, so rebuild from positions, which are solid, not from the raw quaternions. The clean fix: keep the pose resolved offline, whose hands are right, and work out the exact swivel angle that puts the resolved elbow on the measured one. With the same shoulder and hand the elbow lies on the swivel arc; solve the signed angle about the shoulder to hand axis. It lands within about 5 mm and leaves the hands alone.

The same method serves any pose the engine's IK resolves (a vehicle rider, a heavy item being carried): static data gives the positions, and the joints the IK resolves are read from the game.

## An IK pose keys helper targets, not the arm

A real IK pose keys eight IK bones (`LeftHandIKTarget`, `RightHandIKTarget`, `LeftHandOrigin`, `RightHandOrigin`, `LeftForeArmDirection`, `RightForeArmDirection` and the two `ForeArmDirectionOrigin` bones) together with every finger and the `_Dummy` bones. Checked on an extracted grip clip (43 bones). It does not key the raw arm, forearm and hand bones: the hand is placed by the IK target and the elbow by the forearm direction.

The weapon viewer's rig without IK bones lacks those eight, so exporting a native IK pose from it would mean synthesizing them, which is not trivial. Prefer a vanilla IK pose plus geometric parity. The viewer's part in grip work is in `weapon-anim-authoring-viewer.md`, "Authoring a grip with the viewer".

## See also

- `player-skeleton.md`: the hand and IK bones the clips pose.
- `anim-graph.md`: the instance chain that picks the clip per weapon and state.
- `item-ik-and-hide.md`: `AddItemInHandsProfileIK` reused for heavy items.
- The dayz-p3d-inspector skill: reading an MLOD and editing memory points when the checker finds a problem.
