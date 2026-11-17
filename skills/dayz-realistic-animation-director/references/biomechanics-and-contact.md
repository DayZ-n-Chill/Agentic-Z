# Biomechanics and contact

Anatomy, positive contact, relative lock, sliding and collision rules for hands, arms and the things they hold. Vanilla facts cite `P:\`. Lines marked "1.30 changelog" come from the 1.30 experimental modding changelog and are not yet checked on `P:\`.

## Whole-chain rule

A believable endpoint can hide an impossible chain. Sample every load-bearing joint and segment from the contact point back to the body. For a left-hand weapon interaction this normally includes all five digits, wrist, forearm and twist chain, elbow, upper arm, shoulder and the clavicle and spine contribution allowed by the DayZ export mask.

Treat joint-limit tables as calibration aids, not universal truths. Rig rest axes, species, stylisation and retargeting change the numerical representation. A hard limit needs a reference or a measured rig convention.

Bone indices are not a stable reference either. Up to 1.29 `skeletons.anim.xml` set fixed bone indices and the engine had a 250-bone limit; the 1.30 changelog says the limit is removed and the engine works out the global index at run time from a hash of the bone name. On `P:\` the skeletons added in 1.30 carry an `index` only on `EntityPosition` (`P:\DZ\anims\cfg\skeletons.anim.xml:988`). Address bones by name.

## Fingers

- Check MCP, PIP, DIP and tip positions, not only the fingertip.
- Build a per-frame hand-width axis from stable roots; a fixed world axis becomes wrong when the wrist rotates.
- Check ordered projection at multiple joint levels.
- Represent each phalanx with a capsule sized from the visible mesh or an approved hand reference.
- Check explicit adjacent pairs: thumb-index, index-middle, middle-ring and ring-pinky.
- A finger may curl, but it must remain in its intended flexion plane unless abduction is explicitly authored.
- Never fix lateral crossing by forcing PIP or DIP twist. Correct the responsible metacarpal or MCP orientation and re-evaluate the complete chain.
- Review a close-up from palm, dorsal and end-on views; a full-body render cannot resolve distal phalanges.

## Wrist and arm

- Judge wrist flexion and extension, radial and ulnar deviation and twist separately when the rig permits it.
- Reject a wrist that reaches the target by compensating with overextension.
- Solve shoulder and clavicle placement before hiding reach error in the wrist.
- Audit elbow pole stability and shoulder continuity through the complete transition; three-frame position spikes are stutter even when key poses look correct.
- Preserve the runtime start and end pose supplied by the DayZ contract instead of eyeballing a close approximation.

## Positive contact

Every intended contact declares:

- actor and target landmarks or surfaces;
- `contact_on`, rigid and slip phases and `release`;
- allowed surface distance and penetration band;
- permitted target surface;
- relative-lock tolerances;
- release clearance path.

No collision and positive contact are separate checks. A hand 20 mm away can pass a collision audit while visibly missing the handle.

For a fist around a handle, define the cavity or heel surface, not the wrist origin or an arbitrary fingertip. If the landmark is derived from bones, subtract the measured flesh or capsule radius when calculating surface distance.

## Relative lock and sliding

During rigid contact, compare `T_actor^-1 * T_target` every sampled frame. This catches hierarchy, constraint and coordinate-frame errors that identical scalar curves miss.

For authored sliding:

- split the contact window;
- define the permitted translation axis and range;
- keep forbidden axes and rotation locked;
- start a new rigid baseline when the slide ends.

At release, stop enforcing lock and begin enforcing clearance. The hand should create space before crossing receiver or weapon geometry.

### Multi-part mechanical and vehicle contact in DayZ 1.30

1. **Articulated weapon mechanisms and bone remaps.** Do not treat a firearm as one rigid item. Vanilla maps several mechanical bones of a weapon onto the character skeleton through a per-weapon remap table:
   - Luger P08: `LugerBoneRemap` maps `bolt` to `Weapon_Bolt`, `slide` to `Weapon_Bone_01`, `toggle1` to `Weapon_Bone_02` and `toggle2` to `Weapon_Bone_03` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1621`), registered for `Luger_Base` on the next line. During cocking, check the finger and thumb lock against `Weapon_Bone_02` (the toggle), not against the receiver root.
   - Lee-Enfield: `LeeEnfieldBoneRemap` maps `bolthandle` to `Weapon_Bolt`, `boltbody` to `Weapon_Bone_01` and `bullet1` to `Weapon_Bone_02` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1605`). During bolt cycling the relative lock follows `Weapon_Bolt` along its rotation and pull axis, with sliding tolerances along the receiver track.
2. **Motorbike handlebar and footpeg anchors.**
   - Motorbike riders use the animation instances `MOTO1` and `MOTO2` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13-14`). The vehicle subgraph pins the hands with two-bone IK nodes, for example `AnimSrcNodeIK2Target AnimNodeIK2Target0` and `AnimSrcNodeIK2 AnimNodeIK2hands` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:17` and `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:31`), and blends on `VehicleSteering` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:50`).
   - Relative lock on the grips must stay at zero drift during normal riding loops, while wrist twist and elbow pole angles adjust smoothly to the steering angle.
   - Footpegs declare positive contact on the boot soles; a gear shift or rear brake gives a momentary ankle pitch without breaking the footpeg contact plane.

## Collision

- Separate allowed contact pairs from forbidden intersections.
- Sample the complete path; fast motion can tunnel between keyframes.
- Use adaptive subframes or denser sampling around fast transitions.
- For hands, include finger-finger, finger-weapon, palm-weapon and wrist or forearm-weapon pairs.
- For mechanisms, check the complete moving assembly and its travel envelope.

## Visual override

Numeric proxies approximate skin, clothing and perceived weight. If a clear multi-angle render or in-game capture shows overlap, miss, float or overextension, mark the gate failed even if the proxy says PASS. Preserve the case and improve the proxy before the next candidate.
