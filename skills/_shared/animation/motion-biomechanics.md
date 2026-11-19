# Biomechanics and contact

What makes a hand, wrist, arm and held object believable: the whole chain, fingers, positive contact, a grip that stays locked or slides on purpose, and collision. The checker types that measure each rule are in `motion-contract.md`.

## Check the whole chain

A good looking fingertip can hide an impossible arm. Sample every joint that carries load, from the contact point back to the body. For a left hand on a weapon that is all five digits, the wrist, the forearm and its twist bone, the elbow, the upper arm, the shoulder, and whatever clavicle and spine motion the DayZ export mask allows.

Joint limit tables are a starting point, not a law. Rest axes, species, style and retargeting all change the numbers, so a hard limit needs a reference or a measured convention for that rig.

Address bones by name, not index. Up to 1.29 `skeletons.anim.xml` fixed the indices and the engine allowed 250 bones; the 1.30 changelog says the limit is gone and the index comes from a hash of the name at run time. The skeletons added in 1.30 carry an `index` only on `EntityPosition` (`P:\DZ\anims\cfg\skeletons.anim.xml:988`).

## Fingers

- Check the MCP, PIP, DIP and tip positions, not only the tip.
- Build the hand's width axis per frame from stable roots; a fixed world axis goes wrong as soon as the wrist turns.
- Check the finger order across the hand at several joint levels.
- Give each phalanx a capsule sized from the visible mesh or an approved hand reference.
- Check the neighbouring pairs: thumb and index, index and middle, middle and ring, ring and pinky.
- A finger may curl, but it stays in its own bending plane unless spread is keyed on purpose.
- Never fix fingers that cross by twisting the PIP or DIP. Correct the metacarpal or MCP that causes it, then check the whole chain again.
- Review a close up from the palm, the back of the hand and end on; a full body render cannot show the last finger joints.

## Wrist and arm

- Judge bending, sideways tilt and twist of the wrist separately when the rig allows it.
- Reject a wrist that reaches its target by overextending.
- Place the shoulder and clavicle first, before you hide reach error in the wrist.
- Watch the elbow direction and the shoulder through the whole move; a three frame jump in position is stutter even when the key poses look right.
- Keep the exact start and end pose the DayZ route gives you, not a near copy by eye.

## Positive contact

Every intended contact names:

- the actor and target landmarks or surfaces;
- when contact starts, when it is rigid, when it may slip, and when it releases;
- the allowed surface distance and how far it may sink in;
- the target surface it may touch;
- the lock tolerances;
- the path it clears on release.

No collision and real contact are separate checks. A hand 20 mm off the handle passes a collision check and still visibly misses.

For a fist round a handle, define the inside of the fist or the heel of the hand, not the wrist origin or a random fingertip. When the landmark comes from bones, subtract the flesh or capsule radius to get the surface distance.

## A grip that stays locked, or slides on purpose

During rigid contact compare `T_actor^-1 * T_target` on every sampled frame. That catches hierarchy, constraint and frame errors that matching curves miss.

For a slide that is meant:

- split the contact window around it;
- name the axis it may move along and how far;
- keep the other axes and the rotation locked;
- start a new rigid baseline when the slide ends.

At release stop checking the lock and start checking clearance. The hand makes room before it crosses the receiver or weapon.

## Moving weapon parts and vehicle controls

A firearm is not one rigid item. Vanilla maps a weapon's moving parts onto character skeleton bones per weapon:

| Weapon | Remap | What the hand locks to |
|---|---|---|
| Luger P08 | `LugerBoneRemap`: `bolt` to `Weapon_Bolt`, `slide` to `Weapon_Bone_01`, `toggle1` to `Weapon_Bone_02`, `toggle2` to `Weapon_Bone_03` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`, registered for `Luger_Base` on the next line) | When cocking, the fingers and thumb lock to `Weapon_Bone_02`, the toggle, not to the receiver. |
| Lee-Enfield | `LeeEnfieldBoneRemap`: `bolthandle` to `Weapon_Bolt`, `boltbody` to `Weapon_Bone_01`, `bullet1` to `Weapon_Bone_02` (`dayzplayercfgbase.c:1605`) | When cycling, the hand follows `Weapon_Bolt` through its turn and pull, with slide tolerance along the receiver. |

Motorbike riders use the instances `MOTO1` and `MOTO2` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13` and `:14`). The vehicle subgraph pins the hands with two bone IK nodes such as `AnimSrcNodeIK2Target AnimNodeIK2Target0` and `AnimSrcNodeIK2 AnimNodeIK2hands` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:17` and `:31`) and blends on `VehicleSteering` (`:50`). The grips stay locked with no drift through a riding loop while wrist twist and elbow direction follow the steering smoothly. Footpegs are positive contacts on the boot soles; a gear change or rear brake tips the ankle for a moment without leaving the peg's plane.

## Collision

- Separate allowed contact pairs from forbidden overlaps.
- Sample the whole path; fast motion passes through things between keys.
- Sample more densely around fast transitions.
- For hands, check finger and finger, finger and weapon, palm and weapon, and wrist or forearm and weapon.
- For a mechanism, check the whole moving assembly and its travel.

## When the picture and the numbers disagree

Capsules only approximate skin, clothing and weight. When a clear render from several angles or an in game capture shows overlap, a miss, floating or overextension, fail the check even if the numbers pass. Keep the case and improve the capsules before the next attempt.
