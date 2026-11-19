# Weapon in the hands

How a custom weapon sits in the player's hands and sights, which memory points a weapon needs, how to check the grip against a vanilla reference, and why the fix for a bad grip is geometry. A complete weapon animation from Blender is in `weapon-anim-blender.md`; the weapons pack links to these two files for hand animation. Results marked measured in game are not checked on `P:\`.

## Three things set the grip

1. The player's clips. The weapon's instance file (`player_main_rifle.asi`, `weapons\player_main_akm.asi` and so on) and its IK pose place the hands. A weapon `.p3d` carries no hand points; the Memory LOD of a debinarized vanilla `akm.p3d` has no hand or grip selection. The bones are in `player-skeleton.md`, the instance files in `anim-graphs.md`.
2. The weapon's frame. The engine hangs the model's origin on the hand through `RightHand_Dummy` and `Weapon_Root`. When the custom weapon's grip and handguard occupy the same model space as those of the vanilla weapon whose clips it inherits, the inherited hands land right.
3. The weapon's memory points: muzzle, ejection, axes, sight.

So checking a grip means comparing geometry with the reference weapon in the same model space, which is what `weapon_grip_viewer.py` draws and checks.

## Memory points of a vanilla rifle

Read from the Memory LOD of a debinarized AKM; model space, muzzle toward -X, Y up, rounded. The names all occur in the binarized `P:\DZ\weapons\firearms\akm\akm.p3d`; the coordinates cannot be checked there without converting it. A meaning marked "not checked" fits the pattern but is unconfirmed; keep the vanilla shape.

| Name | Points | On the AKM | Meaning |
|---|---|---|---|
| `eye` | 1 | (0.23, 0.15, -0.01), 5.2 cm above the bore on its Z | Camera anchor for iron sights. |
| `usti hlavne` | 1 | (-0.4331, 0.0976, -0.0102) | Muzzle tip (Czech for "barrel mouth"): muzzle flash and where the round leaves. |
| `konec hlavne` | 1 | (-0.0252, 0.0976, -0.0102) | Rear of the barrel. Same Y and Z as the muzzle; the two define the bore. |
| `nabojnicestart`, `nabojniceend` | 1 each | Up, right and to the rear | Path of the ejected case. |
| `bolt_axis` | 2 | Parallel to the bore | Bolt or charging handle travel. |
| `trigger_axis` | 2 | Across the weapon (±Z) at the trigger | Trigger axis. |
| `magazine_axis` | 2 | Roughly vertical (-Y) | Magazine axis; exact use not checked. |
| `recoil` | 2 | Same coordinates as `magazine_axis` | Recoil axis; not checked. |
| `weapon back` | 1 | (0.0712, 0.0976, -0.0102), on the bore | Rear anchor, possibly the back holster; not checked. |
| `ce_center`, `ce_radius` | 1 each | | Placement sphere for the central economy. |
| `invview` | 1 | | Inventory preview camera. |
| `boundingbox_min`, `boundingbox_max` | 1 each | | Bounds. |

What script and config read from these names is in `_shared/weapons/model-selections.md`.

Check these on any custom rifle; a generated test rifle broke every one:

- `usti hlavne` and `konec hlavne` share Y and Z, so the bore is level. A rear point 4.6 cm high tilts the line of fire 6.3 degrees.
- `bolt_axis` is parallel to the bore.
- `magazine_axis` and `recoil` point the way the reference family's do (roughly vertical on the AKM, not sideways).
- The ejection direction is within about 25 degrees of the reference, with a rearward part.
- `eye` sits about as high over the bore as on the reference (about 5 cm for AKM irons). An eye at rail height changes the sight camera.

## The grip viewer and checker

```bat
py skills\dayz-animation-pipeline\scripts\weapon_grip_viewer.py --weapon MyMod_Rifle.p3d --ref akm_mlod.p3d --ref-label "AKM vanilla" --out grip_viewer.html --report grip_report.json
```

- Both inputs are MLOD in their final model space with every offset applied. A binarized reference must be converted to MLOD first with a converter the user supplies; none ships here.
- The command prints the checklist and findings, so it works without a browser.
- The page shows the custom mesh over a translucent ghost of the reference, both sets of memory points, the bore and sight lines with their deviations, the axes at the origin (the hand anchor), and estimated hand zones from the reference (the grip below and behind the middle of `trigger_axis`; the support hand at the handguard proxy anchor, or 55 percent along the bore). The zones are estimates; the real check is how grip and handguard overlap the ghost.
- Overlays are unlit so lighting cannot hide them, and proxy triangles are stripped from the first LOD because they draw as huge spikes. three.js comes through the shared viewer core; open the page once and check it renders before handing it over.

## Fitting the hands: move the whole model

When the weapon inherits a vanilla base such as the AKM's clips, move the whole model (geometry, memory points and proxies) by one offset so its bore and grip relate to the origin as the reference's do. Never move the grip alone. One test rifle's assembler applied +0.0326 on Y and -0.0102 on Z, taken from matching `usti hlavne` with the AKM's, once at assembly. Check the offset is applied exactly once; applying it twice is the usual failure. Then run the grip viewer again on the final `.p3d` taken out of the PBO.

## Turning the wrist in the IK pose does not turn the hand

Measured in game on a custom submachine gun with no hand memory points, inheriting the AKS-74U clips: turning the `LeftHand` bone in the IK pose did not turn the support hand, because the engine's IK lines the hand up with the weapon again. Four IK poses with `LeftHand` turned 90 degrees about different local axes all rendered the same; a pixel difference of the hand region gave RMS 7.8 for a 180 degree roll, less than a finger curl change (RMS 11). What the IK pose visibly drives is finger curl.

So change the support hand's orientation with geometric parity: a reference clip whose hand already sits that way, checked with `weapon_grip_viewer.py`, or a change to the weapon's geometry or offset. Two vanilla OTS-14 poses (held normally and by the barrel handle) differ on `LeftHand`, but both were made for a weapon with parity; that does not mean turning `LeftHand` works on a weapon without it.

## The fix that works: raise the weapon to the hand

On the same submachine gun every lever on the player's side did nothing in game: the IK target's position and rotation, the behaviour flag, forward kinematics on `LeftHand`. Its bore sat 2.4 cm lower over the origin than on a working reference (Y 0.066 against 0.090), so the support hand, which lands at a fixed point in skeleton space, came down on the barrel. Moving the whole model up 0.024 on Y put the weapon into the hand, and the hand closed on the foregrip. When moving the IK targets does nothing, stop tuning the animation: move the weapon to the hand.

Working mods do the same. A third party weapon pack with a closed foregrip grip uses only `AddItemInHandsProfileIK(class, a rifle parent .asi, the firearms behaviour, a vanilla IK pose, states)` (its own scripts, not vanilla), choosing a vanilla pose whose `LeftHandIKTarget` lands where its weapon has a handguard: the poses vanilla registers for `Vikhr` and `PM73Rak_Base` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:434` and `:425`). No player animation mod, no changed base pose, no scripted bones. A custom weapon's grip comes from the firearms behaviour, a stock vanilla IK pose and geometry where that pose lands.

The IK pose, the fourth argument, applies to every stance, while the raised base pose differs per stance (`Locomotion.<stance>Ras` idle, aim and sight lines) and the aim lines add the aim space clip, which opens the support hand. So a pair that closes the idle grip could leave the aim grip open. On the measured submachine gun it did not: the same raise closed the aim in third person too, because both base poses anchor the support hand to the same zone. If a weapon still shows an open aim grip after the idle closes, override its aim and sight `Locomotion` lines in a child `.asi`, as third party weapon packs do.

## Testing grip variants in game

- Compare on one weapon: one `CfgWeapons` class per IK pose variant, each derived from the real weapon and registered with its own clip through `AddItemInHandsProfileIK`. Variants on different weapons mix in each weapon's balance and handguard.
- Measure small differences: RMS of the hand region between variants and against a change known to show (a finger curl), to separate signal from lighting and timing noise. Run it on full resolution crops; on a scaled down contact sheet the hand is about 30 pixels, and a working grip has been called inert that way. RMS says whether something changed, not whether it is right; look at the crop.
- Capture with `overcast` at 1.0, which kills the glint that washes the weapon white, and capture all variants quickly so exposure does not drift. Cycling over several weapons, keep the wait per weapon shorter than the cycle, or captures slip onto the next weapon.

To capture the aim grip, force the raise every frame with `OverrideRaise(HumanInputControllerOverrideType.ENABLED, true)` (`P:\scripts\3_game\human.c:268`). `ENABLED` stays until `DISABLED` is passed and `ONE_FRAME` applies once (`:7` to `:11`); with `ONE_FRAME` the pose flickers back to idle.

- Run it on the client, as a `modded class MissionGameplay` with an `OnUpdate` override in a small test mod that declares a `missionScriptModule`. A raise forced only on the server is logged there, but the client still renders the weapon lowered. Keep a matching `OverrideRaise` on the server so both agree.
- The third person aim pose depends only on the movement state being raised (`m_MovementState.IsRaised()`, `P:\scripts\4_world\entities\dayzplayerimplement.c:1742`), so a held raise is enough.
- Do not call `SetIronsights()`: it forces the sight camera, fights a free camera, and server side left the weapon untextured.
- `WeaponADS()` is an input flag (`human.c:86`) with no override among the `Override...` methods (`:253` to `:274`), and reads 0 even when aiming works. Use `IsRaised()` or the client log.

Run such a test mod with `/dayz-launch-test` and read its result from `script.log`; posing a raised weapon for a screenshot is in `skills/dayz-launch-test/references/screenshots-and-cameras.md`, "Capturing a raised weapon".

## How a custom weapon animation is bound

Three files, bound per item class in script, none editing the player graph, so several mods can each do it (`anim-graphs.md`, "Which changes collide"). `AddItemInHandsProfileIK(itemClass, asi, behavior, ikPose.anm, weaponStates.anm)` (`P:\scripts\3_game\dayzplayer.c:243`) binds the class to its instance file, an IK pose and a weapon states clip; `AddItemBoneRemap(itemClass, pairs)` (`:252`) maps its part selections to the skeleton's `Weapon_` bones. Frame counts are from DayZATool extracts of the vanilla AKM clips:

| File | What it is | Vanilla AKM | Named in |
|---|---|---|---|
| IK pose (`ik/weapons/<weapon>.anm`) | One static placement of hands and fingers on the gun. It keys seven IK bones (`LeftHandIKTarget`, `LeftHandOrigin`, `RightHandOrigin`, both `ForeArmDirection` bones and their origins), every finger and the `_Dummy` bones (43 bones on an extracted grip clip), not the raw arm, forearm and hand. | 2 frames at 30 fps, the second a byte exact copy of the first. The instance's `IkPose` line names `izh18` (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:6`) while script registers `akm.anm` (`dayzplayercfgbase.c:412`); which one the engine uses is not known. | The `.asi` `IkPose` line and the fourth argument, which can differ. |
| Weapon states (`w_<weapon>_states.anm`) | Drives only the `Weapon_` bones: bolt and bullet. | 2 distinct frames (`Weapon_Bolt` slides, `Weapon_Bullet` ejects); Workbench trims to 2 to 4 keys per channel. | The fifth argument; `SetInitState` reads it. |
| Action clips (reload, fire, chamber, jam) | Differences, roughly shoulders down, over the idle. | Magazine out 22 frames, full swap 55, charging handle 44, chambering 107, fire 11, jam 230, all at 30 fps. | The `.asi` `Lines`. |

Action clips play over the states clip and override those bones while they run. The IK chain is set up in the graph's weapon IK node (the `ikpose_` keys, `P:\DZ\anims\workspaces\player\player_main\combat.agf:29` to `:35`), not in config. The `reloadAction` key of `CfgWeapons` is legacy; leave it out, as vanilla rifles do (`weapon-anim-wiring.md`, "The reloadAction key is legacy").

## Reproducing the grip offline

What sets the grip, completely: the weapon mounts by its origin on `Weapon_Root` and `RightHand_Dummy`; the hands are the IK pose; the weapon's geometry is offset so its grip falls where that pose puts the hand; and stance and aim. A short submachine gun, about 0.18 m from pistol grip to foregrip, has no parity with a rifle hand spacing of about 0.33 m. The aim space clip (`P:\DZ\anims\anm\player\layered\aim\2handed\p_2hd_erc_aimspace.anm`, 39 frames on a two dimensional grid of directions) is neutral at its centre frame, index 19 (at most 0.7 degrees), so there is no separate sight pose at the centre: the plugin's sample base pose `Rifle_Erect_Idle_Ras (Soft_Aim).txa` already is the raised aim.

To read the real grip in Blender, use the plugin's sample rig with IK bones (`Poses/Rifle/M4 Rifle IK.blend`, 155 bones, with constraints from the hands to `RightHandOrigin` and `LeftHandOrigin`). Apply the base pose `.txa`, then the grip IK pose as a plugin action on the IK helpers; the rig's IK puts the hands on the weapon and `Weapon_Root`, hands and fingers can be read. Combined with the M4 pose the hand spacing is 0.326 m, confirming the base pose is the rifle setup. On the plugin's rig without IK bones `Weapon_Root` poses the weapon crossed or upside down. Applying a weapon's IK pose directly still meets the bone frame convention, which only the game settles; do not guess (orienting by a finger axis, a fixed -90 degree wrist turn, nudging forward all failed or did not carry to another weapon). DayZATool's `--extract-anim <input.anm> <scale=100>` takes no output path and writes the `.seanim` next to the input; the vanilla aim and IK pose clips are under `P:\DZ\anims\anm\player\layered\aim\` and `P:\DZ\anims\anm\player\ik\weapons\`. Keep in game reference captures of the closed grip; one capture run takes 10 to 15 minutes. An editable viewer rebuilds its pose from the base pose's forward kinematics, not the T pose.

## The elbow cannot be derived offline

Offline the IK pose gets the hands right, since the targets are static data, but the engine solves the elbow at run time from the forearm direction pole. The plugin's Blender pole gave a winged elbow and a swivel guess went the other way (right elbow guessed tucked, measured 81.7 degrees open; the left 50.4). Read it from the live skeleton instead:

- `GetBoneIndexByName` on `Human` (`human.c:1417`; vanilla uses it for `RightHand_Dummy` at `dayzplayerimplement.c:628`), then `GetBonePositionMS` and `GetBoneRotationMS` on `Object` (`P:\scripts\3_game\entities\object.c:237` and `:242`), in model space relative to the player. Only -1 means a missing bone; valid ids can be negative (`rider-pose-measured.md`).
- A client side `modded class MissionGameplay` forces the raise and, once `IsWeaponRaiseCompleted()` is true (`dayzplayerimplement.c:935`) and about 120 frames have settled, prints each bone's position and quaternion once. `Print` lands in the client's `script_*.log` in its profile folder, not the RPT. Build the string in single line statements (`ln = ln + ...`); an expression continued over lines with `+` does not compile.
- Into a three.js viewer, position becomes `(x, y, -z)`, from Enfusion's left handed space to three.js's right handed one. The matching quaternion flip `(-x, -y, z, w)` rendered mirrored, so rebuild from positions. Keep the offline pose, whose hands are right, and solve the signed swivel angle about the shoulder to hand axis that puts the elbow on the measured one; it lands within about 5 mm and leaves the hands alone.

The same method serves any pose the engine's IK solves, such as a vehicle rider or a heavy carried item. A native IK pose export from the weapon viewer's rig would have to synthesize the seven IK bones it lacks; prefer a vanilla IK pose plus geometric parity (`weapon-anim-viewer.md`, "A fuller viewer").

See also `items-in-hands.md` for `AddItemInHandsProfileIK` reused for heavy items, and the model tools' `.p3d` inspector for editing memory points when the checker finds a problem.
