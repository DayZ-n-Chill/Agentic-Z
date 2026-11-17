# Weapon hand animation and grip

How a weapon gets its hand pose and its reload and fire clips, what a custom weapon can change without replacing the player graph, and what was measured about making the support hand close on a custom weapon. The class and profile basics are in `weapon-classes.md` ("Hand animations"); the model names are in `model-selections.md`. Full authoring workflows are in the dayz-animation-pipeline skill (`skills/dayz-animation-pipeline/SKILL.md`).

## What vanilla binds to a weapon class

One line per weapon in `DayZPlayerTypeRegisterItems` binds four things:

```c
pType.AddItemInHandsProfileIK("AKM_Base", "dz/anims/workspaces/player/player_main/weapons/player_main_akm.asi", fireArmsItemBehaviour, "dz/anims/anm/player/ik/weapons/akm.anm", "dz/anims/anm/player/reloads/AKM/w_akm_states.anm");
```

(`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:412`.)

| Part | What it is |
|---|---|
| The instance, `player_main_akm.asi` | Maps the weapon's states to player clips. One per weapon under `P:\DZ\anims\workspaces\player\player_main\weapons\`. |
| The behaviour, `fireArmsItemBehaviour` | How the item is held and moved with. |
| The IK pose, `akm.anm` | One pose: where the hands sit on this weapon. |
| The weapon states clip, `w_akm_states.anm` | The weapon's own parts in their start states (closed, open, jammed). |

A fifth piece is the bone remap, which lets player clips move the weapon's parts: `bolt` to `Weapon_Bolt`, `magazine` to `Weapon_Magazine`, `trigger` to `Weapon_Trigger`, `charging` to `Weapon_Bone_01`, `bullet` to `Weapon_Bullet` for rifles (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1579`, registered with `AddItemBoneRemap` at :1580).

## State names in a weapon instance

Lines have the form `WeaponOperations.<stance>.<state>`. `ErcRas` is erect with the weapon raised and `PneRas` is prone and raised; a weapon instance lists each state under both (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi:19` and `:70` for `FireCocked`).

| Tutorials call it | Real state | Where |
|---|---|---|
| "weapon cocked" | `FireCocked` | `P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi:19` |
| "mag remove" | `ReloadMagazineDetach` | `P:\DZ\anims\workspaces\player\player_main\weapons\player_main_1911.asi:52` |
| "bullet in chamber" | Not a state. Chambering is the graph commands `CMD_Reload_Chambering` and `CMD_Reload_ChamberingFast`. | `P:\DZ\anims\workspaces\player\player_main\player_main.agr:275`, `:278` |

The full list of names a weapon instance may use is the `WeaponOperations` group of the player template (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1217`).

The graph chooses the fire state from the value of the fire command: `FireCocked` starts on `GetCommandI(CMD_WeaponFire) == 2` (`P:\DZ\anims\workspaces\player\player_main\combat.agf:1120` to `:1123`). The "mag remove" clip only draws the hand moving away; the inventory script decides when the magazine really leaves the weapon.

Reloads are not additive animations. `CMD_Modifier_Additive` drives the sickness modifiers; reloads have their own commands, `CMD_Reload_Magazine`, `CMD_Reload_BoltAction`, `CMD_Reload_Chambering`, `CMD_Reload_ChamberingFast` and `CMD_Reload_Clip` (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:269` to `:284`).

## The IK roles

The graph's weapon IK node says which helper bone plays which role (`P:\DZ\anims\workspaces\player\player_main\combat.agf:29` to `:35`):

| Key | Bone | Role, from the node's own comments |
|---|---|---|
| `ikpose_chainoffset` | `RightHandOrigin` | Where the right hand was in the IK pose. |
| `ikpose_weaponoffset` | `RightHand_Dummy` | The weapon's offset from the right hand. |
| `ikpose_secchainoffset` | `LeftHandIKTarget` | The left hand's target, relative to the weapon. |
| `ikpose_chainmiddledir`, `ikpose_chainmiddlediro` | `RightForeArmDirection`; `RightHandOrigin,RightForeArmDirectionOrigin` | Right elbow direction, and its original. |
| `ikpose_secchainmiddledir`, `ikpose_secchainmiddlediro` | `LeftForeArmDirection`; `LeftHandOrigin,LeftForeArmDirectionOrigin` | Left elbow direction, and its original. |

These are graph settings. They are not keys of `config.cpp`, `model.cfg` or the template.

## A custom weapon without a graph replacement

A mod weapon that inherits a registered vanilla class reuses that class's profile (`weapon-classes.md`). To give it its own clips, a mod adds its own instance file, a child of a vanilla one that lists only the states it changes, and registers the weapon class with that instance in `ModItemRegisterCallbacks.RegisterFireArms` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:321`). Because that binds one item class and replaces no graph file, several weapon mods can each do it. That a mod's own instance and clips play this way is the source pack's in-game result, not something vanilla files can show; the walkthrough is in the dayz-animation-pipeline skill.

When changing or adding one animation for a custom item or weapon, the working habit reported by the animation workshop videos the source pack drew on:

1. Find the vanilla instance closest to what is wanted.
2. Inherit it; do not write an instance from scratch.
3. Change only the state, clip or line that must change. Locomotion and additive lines inherited from the parent are delicate and break easily when overwritten.
4. Watch states with very few frames: a state whose clip ends on its second frame leaves the engine showing two frames.

Reported unsolved in those videos (March 2024, not rechecked): holding two weapons at once, the full bow mechanic, and custom additive locomotion.

## The three clips of a weapon

| Clip | What it holds | Notes |
|---|---|---|
| IK pose | One pose of hands and fingers on the weapon. | Named by the `IkPose` line of the weapon's instance and by the call above. Poses are shared: the AKM's instance names the `izh18` pose (`P:\DZ\anims\workspaces\player\player_main\weapons\player_main_akm.asi:6`). |
| Weapon states | Only the `Weapon_` bones, one frame per start state. | The engine picks a frame with `SetInitState(int pFrameIndex)`; the comment above it says each frame of the animation is one init state (`P:\scripts\3_game\human.c:1108` to `:1112`). The authoring intent is three frames (closed, open, jammed). The source pack read 2 to 4 stored keys per channel in the vanilla clips, because Workbench drops keys that are nearly equal; `w_akm_states.anm` has 2. |
| Action clips | Reload, fire, chamber, jam. | Mapped per state in the instance's `Lines`. They play over the states clip, so an unjam clip must start on the jammed frame's bolt position or the bolt jumps (measured by the source pack). |

All vanilla AKM clips the source pack extracted run at 30 frames per second: fire 11 frames, magazine removal 22, charging handle 44, full magazine swap 55, chambering 107, jam clearing 230.

The `WeaponOperations` group has 42 states and exactly two columns, `ErcRas` and `PneRas` (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1262` to `:1265`). There is no crouch column; do not invent `WeaponOperations.CroRas`. The names `Jamming Cancel` and `Jamming Check` contain a space (`P:\DZ\anims\workspaces\player\player_main\player_main.ast:1245`, `:1246`). The column is chosen by the graph from the stance: `WeaponStancePne` starts on `Stance == 2` (`P:\DZ\anims\workspaces\player\player_main\combat.agf:1169` to `:1172`).

## `reloadAction` does not drive the reload

`reloadAction` in a weapon's config is a leftover key. Vanilla rifles do not set it: neither `P:\DZ\weapons\firearms\ak74\config.cpp` nor `P:\DZ\weapons\firearms\svd\config.cpp` contains it. It survives on two classes in `P:\DZ\data\config.cpp` (`reloadAction="ReloadBow"` at `P:\DZ\data\config.cpp:4592`, `reloadAction="ManActReloadAT"` at `P:\DZ\data\config.cpp:4756`). The reload clips come from the instance file by state name. Leave the key out of a custom weapon.

## A held action is timed by script, and its clip must loop

Unjamming is driven by a timer, not by the clip's length. `WeaponUnjamming` sets `m_jamTime = 5.0` (`P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:218`); `WeaponUnjamming_Start` counts in `OnUpdate` and posts the timeout once `m_dtAccumulator >= m_jamTime` (`P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:27` to `:42`), and the following state calls `SetJammed(false)` (`P:\scripts\4_world\entities\firearms\fsm\states\weaponunjamming.c:87`). Releasing the key first interrupts it and the weapon stays jammed.

The source pack traced, and for the working case measured in game, that a custom unjam clip must carry `LoopStart` and `LoopEnd` notes so the gesture keeps looping while the timer runs. Without them the clip ends, the action reads as finished and the weapon returns to jammed. Structure and note format: `skills/dayz-animation-pipeline/references/weapon-anim-blender-complete.md`.

## Model rules that keep inherited hands and sights right

Measured by the source pack on generated rifles checked against a debinarized AKM; the point names occur in `P:\DZ\weapons\firearms\akm\akm.p3d`, the coordinates are not checkable there. What each name is read for is in `model-selections.md`.

- `usti hlavne` and `konec hlavne` share Y and Z, so the bore is level. A rear point 4.6 cm high tilted one build's line of fire by 6.3 degrees.
- `bolt_axis` is parallel to the bore.
- `eye` sits about as high over the bore as on the reference weapon (5.2 cm on the AKM).
- The ejection direction (`nabojnicestart` to `nabojniceend`) is within about 25 degrees of the reference.
- The weapon model has no hand points. The hands come from the player's clips, so a custom weapon is fitted by moving the whole model with one offset until its bore and grip have the reference's relation to the origin. The checker for this is `skills/dayz-animation-pipeline/scripts/weapon_grip_viewer.py`.

## Authoring notes for the hands

From the same videos; practice, not checked on `P:\`:

- Moving `RightHand_Dummy` moves the weapon. Lining up the stock with the collarbone and getting the forearm angles right is the most sensitive part of the rig.
- The left hand follows the magazine during a reload through `LeftHand` and `LeftHand_Dummy`. The older `Magazine`, `Bullets_Magazine` and `Bullets_holder` bones in the skeleton XML sit in a group marked for removal (`P:\DZ\anims\cfg\skeletons.anim.xml:293` to `:300`). Helper bones for the magazine's path live only in the author's Blender file.
- The fire IK looks confusing in the animation editor; having the weapon model in the Blender rig helps.
- Constraints and numbers in Blender help with posing but are not exported as they are. Export, look at the elbow, shoulder and grip gaps in game, and repeat.

## Making the support hand close on a custom weapon

All of this section was measured in game by the source pack's A6_SR2M project (a custom submachine gun using the AKS-74U animations, June 2026), and by its reading of a working third party mod. None of it is checked on `P:\`.

**Turning the wrist in the IK pose does not turn the support hand.** On a custom weapon with no hand memory points, four variants of the IK pose with the `LeftHand` bone turned 90 degrees about different axes rendered the same in game. A 180 degree roll changed the hand area of a screenshot less (RMS 7.8) than a change of finger curl did (RMS 11). The only part of the IK pose that visibly applied was the finger curl (the `LeftHand` finger bones).

**Why.** The support hand is posed by the reference animation, anchored to the weapon's origin (`Weapon_Root` under `RightHand_Dummy`). The vanilla AKM has no hand memory points at all. What decides where and how the hand lands is how closely the custom weapon's geometry matches the weapon the animation was made for, not the IK pose. The project's `weapon_grip_viewer.py` measures that gap: against the AKS-74U its weapon's bore was aligned, but the weapon sat about 3 cm lower with a shorter barrel, so the hand landed high and forward with a flat palm instead of an upright one.

**This corrects an earlier over-generalisation.** Two vanilla IK poses of one weapon (the OTS-14 held by the handguard and by its forward grip) differ by 24.8 degrees on `LeftHand`. That difference exists because both poses were authored against a weapon whose geometry matches. It does not mean that turning `LeftHand` on a weapon that does not match will reproduce the orientation. For an upright palm on a custom foregrip, match the geometry to an animation whose hand already lands upright, or adjust the weapon's geometry or offset.

**What worked: raise the weapon to the hand.** The lever was moving the whole weapon model up to where the animation puts the support hand.

- The working third party mod (KarmaKrew, Workshop 2864245850; its Vikhr and SR-2M) gets its grip with vanilla IK poses (`Vikhr.anm`, `pm73_IK.anm`, both registered in vanilla at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:434`, `:425`), the firearm behaviour and matching geometry. It has no player animation replacement, no changed base pose and no scripted bones.
- The number: the project's bore was 2.4 cm lower above the weapon's origin than the reference (0.066 m against 0.090 m), so the animation's hand landed on top of the barrel. Moving the whole model up 0.024 m closed the grip.
- The rule of thumb: when the animation's levers (IK pose position or rotation, behaviour, forward kinematics on `LeftHand`) turn out to do nothing, move the weapon, not the animation.
- It closed both stances. The IK pose is shared between the lowered and the aiming stance, and the worry was that fixing one would open the other. The same raised weapon closed the lowered stance (shipped) and the aiming stance (third person). A per stance instance override remains a fallback that was not needed.

**Capturing the aiming pose to check it.**

- Force the raise on the client, not in the server's `init.c`: the character being captured is the client's own player, and a server side override did not move what the client rendered. The call is `OverrideRaise(HumanInputControllerOverrideType overrideType, bool value)` on the input controller (`P:\scripts\3_game\human.c:268`).
- Judge success by `IsRaised()`, not `WeaponADS()`. `WeaponADS()` is an input flag (`P:\scripts\3_game\human.c:86`) and gave a false success. The third person aiming pose depends on the movement state being raised (`m_MovementState.IsRaised()`, `P:\scripts\4_world\entities\dayzplayerimplement.c:1742`).
- Do not use `SetIronsights` (`P:\scripts\4_world\entities\dayzplayerimplement.c:363`) for this; it fights a free camera.
- Judge the hand at native resolution. In a scaled contact sheet the hand is about 30 pixels, and a good grip was once declared to have had no effect from a thumbnail.
