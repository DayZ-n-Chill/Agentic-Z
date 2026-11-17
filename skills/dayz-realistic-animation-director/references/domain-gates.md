# Domain gates

Extra checks for each kind of animation: player actions, hands with a weapon or object, locomotion, creatures, vehicle occupants, mechanical props and physics simulation. Use only the sections the task needs, on top of the common contract and the current `dayz-animation-pipeline` route.

Vanilla facts cite `P:\`. Lines marked "1.30 changelog" state 1.30 engine changes that are not yet checked on `P:\`. Comparisons with 1.29 cannot be checked on a 1.30 `P:\`.

## Player or humanoid action

- Verify the allowed body layer and export mask before authoring.
- Track centre-of-mass implication, shoulder and clavicle contribution and counter-motion.
- Preserve locomotion and root channels that the runtime layer owns.
- Test stance and camera variants that can change IK or blending.
- Review transitions into and out of the action, not only its central pose.
- **Surrender state (1.30).** Up to 1.29 surrendering put an invisible `SurrenderDummyItem` in the hands to block reloading and interaction. In 1.30 that class is marked `Obsolete` (`P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1`), and the only code that still looks for it in the hands is the obsolete `CheckEmoteLockedState` (`P:\scripts\4_world\classes\emotemanager.c:1212`). Surrender is now a player state: `SetSurrenderState` on `PlayerBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:2116`), read with `IsSurrendered` on `Man` (`P:\scripts\3_game\entities\man.c:67`) and cleared by `ClearSurrenderState` (`P:\scripts\4_world\classes\emotemanager.c:1246`). Do not author interactions that assume an invisible dummy weapon in the hands during surrender.
- **Switching the animation instance from script.** `SetAnimationInstanceByName` on `Human` takes the instance name and a blend time (`P:\scripts\3_game\human.c:1384`); the vanilla comment warns it can desync when misused. To go back to the unarmed base pose, vanilla registers an `"Empty"` profile on `player_main.asi` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1548`).
- **Per-stance speed and camera rotation limits.** `HumanInputController` can cap movement speed and freeze horizontal camera rotation per stance:
  - `SetErectSpeedLimit`, `SetCrouchSpeedLimit` and `SetProneSpeedLimit`, each `(bool bShouldDisable, int pMaxErectSpeed)` (`P:\scripts\3_game\human.c:230-232`);
  - `DisableErectCameratHorizontalRotation`, `DisableCrouchCameratHorizontalRotation` and `DisableProneCameraHorizontalRotation`, each `(bool pDisable)` (`P:\scripts\3_game\human.c:240-242`; the `Camerat` spelling is vanilla's).

  Author transitions knowing that wide horizontal looking can be locked during heavy or prone gestures.
- **Animation tags.** A graph tag bound with `BindTag` is tested with `IsTag` on `HumanAnimInterface` (`P:\scripts\3_game\human.c:319`).
- **Full-body action constants added in 1.30.** `DayZPlayerConstants` lists eleven full-body actions from 256 up, `CMD_ACTIONFB_COMBINATIONLOCK` to `CMD_ACTIONFB_WETCLOTHWELL` (`P:\scripts\3_game\dayzplayer.c:889-899`). The stance comes from the vanilla comment on each line (`pne` prone, `cro` crouch, `erc` erect):

  | Constant | Value | Stance | Use |
  |---|---|---|---|
  | `CMD_ACTIONFB_COMBINATIONLOCK` | 256 | prone | combination lock; the erect and crouch variant is `CMD_ACTIONMOD_COMBINATIONLOCK`, also 256 |
  | `CMD_ACTIONFB_WASHFACEPOND` | 257 | crouch | washing the face at a pond; the modifier variant is `CMD_ACTIONMOD_WASHFACE` |
  | `CMD_ACTIONFB_BUILDROPELADDER` | 258 | crouch | crafting a rope ladder |
  | `CMD_ACTIONFB_BRICKSTACK` | 259 | erect, crouch | stacking bricks |
  | `CMD_ACTIONFB_BRICKTROWEL` | 260 | erect, crouch | trowel masonry |
  | `CMD_ACTIONFB_MIX_MORTAR` | 261 | crouch | mixing mortar in a bucket |
  | `CMD_ACTIONFB_DRINKWELL_BUCKET` | 262 | erect | drinking from a well bucket |
  | `CMD_ACTIONFB_SHARPEN` | 263 | crouch | sharpening a stone tool |
  | `CMD_ACTIONFB_WASHFACEWELL` | 264 | erect | washing the face at a well |
  | `CMD_ACTIONFB_WETCLOTH` | 265 | crouch | wetting a cloth at a pond |
  | `CMD_ACTIONFB_WETCLOTHWELL` | 266 | erect | wetting a cloth at a well |

  `CMD_ACTIONMOD_COMBINATIONLOCK` is at `P:\scripts\3_game\dayzplayer.c:766`; `CMD_ACTIONMOD_WASHFACE` follows it with no value written, so it is one higher.

## Hand with weapon or object

- Apply every rule in `biomechanics-and-contact.md`.
- Identify the functional moving assembly before posing.
- Define jammed, closed, open or equivalent mechanical states from verified geometry or data.
- Keep contact lock until the declared release; after release enforce clearance.
- Validate a regrip as approach, open hand, enclose target, close, rather than teleporting a closed fist.
- Compare start and end against the real runtime IK pose.
- **Item in hands without an instance change.** `OnItemInHandsChanged` on `HumanItemAccessor` takes `pChangeAnimationInstance`, default `true` (`P:\scripts\3_game\humanitems.c:112`); passing `false` changes the item without switching the animation instance. `EnableAutoAnimInstUpdateOnHandsChange` turns the automatic switch on or off (`P:\scripts\3_game\humanitems.c:115`).
- **Dedicated weapon and tool `.asi` profiles.** Vanilla gives many tools and weapons their own instance file instead of the generic one-handed or two-handed one. Each row is an `AddItemInHandsProfileIK` line in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c`:

  | Item class | Instance file under `dz/anims/workspaces/player/player_main/` | Line |
  |---|---|---|
  | `BandageDressing` | `props/player_main_1h_bandage.asi` | `:1251` |
  | `Sickle` | `props/player_main_1h_sickle.asi` | `:747` |
  | `HayHook` | `weapons/player_main_1h_hayhook.asi` | `:753` |
  | `Hatchet` | `weapons/player_main_1h_hatchet.asi` | `:757` |
  | `Pitchfork` | `weapons/player_main_2h_pitchfork.asi` | `:807` |
  | `Sword` | `weapons/player_main_2h_sword.asi` | `:809` |
  | `Luger_Base` | `weapons/player_main_luger08.asi`, with `LugerBoneRemap` at `:1621` | `:395` |
  | `MP18_Base` | `weapons/player_main_mp18.asi` | `:432` |
  | `LeeEnfield_Base` | `weapons/player_main_leeEnfield.asi`, with `LeeEnfieldBoneRemap` at `:1605` | `:446` |
  | `SCARH_Base` and `SCARL_Base` | `weapons/player_main_SCARH.asi` for both | `:444`, `:445` |

  On 1.29 only `SCARH_Base` had a dedicated file among these (not checkable on a 1.30 `P:\`). Audit hand poses against the exact weapon or prop `.asi` profile rather than assuming generic `player_main_1h.asi` or `player_main_2h.asi`.

## Locomotion

- Define gait, stride, cadence, stance and root-motion ownership.
- Check foot locking, ground penetration, slip distance and support transitions.
- Track pelvis and centre-of-mass arcs and upper-body counter-rotation.
- Match cycle pose and velocity at the seam.
- Test slopes and turning only if the DayZ graph or runtime consumer will exercise them.
- Audit transitions under the per-stance speed limits above (`SetErectSpeedLimit`, `SetCrouchSpeedLimit`, `SetProneSpeedLimit`). When a speed limit is enforced, root motion scaling must not cause foot sliding.

## Creature

- Obtain the actual skeleton, rest pose and gait reference for that species and rig.
- **Bone indices (1.30).** Up to 1.29 `skeletons.anim.xml` set fixed indices and the system was limited to 250 bones. 1.30 changelog: the limit is removed, indices are worked out at run time from a hash of the bone name, and manual indices are ignored except on `EntityPosition`. On `P:\` the survivor skeleton `hermit_newbindpose.xob` still lists `index` 10 to 36 on its core bones (`P:\DZ\anims\cfg\skeletons.anim.xml:8` for `Pelvis`), while the four animal skeletons new in 1.30 carry it only on `EntityPosition` (`P:\DZ\anims\cfg\skeletons.anim.xml:988`). Those four are `ovis_gmelini_skeleton.xob` (mouflon, `P:\DZ\anims\cfg\skeletons.anim.xml:986`), `canis_familiaris_dobermann_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:1047`), `canis_familiaris_german_shepherd_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:1121`) and `varanus_griseus_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:1194`).
- **Graph files.** Creature graphs are `.agf` files in Enfusion config syntax, listed by an `AnimSrcGraph` index: the wolf index names `Wolf_MainGraph.agf` under `GraphFilesResourceNames` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:157`). The 1.29 wolf graph was already two text files in the older `$AnimGraph 7 {` syntax, not one binary file.
- **Procedural terrain alignment.** Quadrupeds rotate bones from the terrain slope with `AnimSrcNodeProcTransform`. The wolf's `AlignToTerrain_Rot` node (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5`) starts:

  ```
  AnimSrcNodeProcTransform AlignToTerrain_Rot {
   EditorPos -1 -4.7
   Child "Master_SM"
   Expression "SlopeAngleX  * 0.01745329251994329576923690768489"
   Bones {
    AnimSrcNodeProcTrBoneItem "{6930A8DF8B23795C}" {
     Bone "scene_root"
     Axis X
     Space Model
     Op Rotate
     Amount 1
    }
  ```

  The next item in the same list is `lflegcollarbone`. Validate that the root and collarbone rotation follow the slope angle `SlopeAngleX`, so the feet do not sink into slopes.
- **Prediction and look poses.** The wolf graph uses `AnimSrcNodePrediction` on `EntityPosition` with `PercentTime 0.3` for translation and rotation (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:52`), and `AnimSrcNodePose2` nodes for looking, for example `StandNervousLookAt_ANIM` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:2024`).
- **Infected mind states.** `MINDSTATE_COWER` is the last infected mind state (`P:\scripts\3_game\entities\dayzinfected.c:18`); it is new in 1.30. The infected look pose is an `AnimSrcNodePose2` driven by `LookDirX` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:8`), blended in by `AggroLookBlendT`, an `AnimSrcNodeBlendT` with the condition `Look` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:19`).

## Vehicle occupant

- Source seat, grip, pedal or footrest and steering anchors from actual model data.
- Keep hands and feet locked to moving controls through their travel.
- Audit elbow and knee solutions at steering extremes and animation transitions.
- Validate get-in and get-out approach side and clearance separately from the seated loop.
- Delegate anchor extraction and vehicle runtime behaviour to their domain skills.
- **Motorbikes (1.30).**
  - Animation instances: `MOTO1 = 10` and `MOTO2 = 11` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13-14`), returned by `Motorbike_01_ColorBase` (`VehicleAnimInstances.MOTO1` at `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:50`) and `Motorbike_02_ColorBase` (`VehicleAnimInstances.MOTO2` at `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:51`). They model a Jawa 50 cc and the three-wheeled Jawa Bitrak (model names not checked on `P:\`).
  - Camera: the third-person motorbike camera is `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`). Its class `DayZPlayerCamera3rdPersonVehicleMotorbike` follows with spring lag (`CONST_SPRING_SMOOTHTIME_YAW` at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:258`).
  - Handlebar IK: the grip uses continuous two-bone IK nodes, `AnimSrcNodeIK2` and `AnimSrcNodeIK2Target`, in the vehicle subgraph, including the motorbike pair `MotoEngineIKTarget` and `MotoEngineVehicleIK` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1436` and `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1446`).
  - Rider dynamics: torso, spine and head lean are driven by the graph variables `VehicleSteering`, `VehicleThrottle` and `VehicleSuspension`, declared in the index (`P:\DZ\anims\workspaces\player\player_main\player_main.agr:113`, `P:\DZ\anims\workspaces\player\player_main\player_main.agr:118` and `P:\DZ\anims\workspaces\player\player_main\player_main.agr:205`) and used in the subgraph (`VehicleSuspension` at `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1544`).
  - Transition query: `IsTransitioning` on `HumanCommandVehicle` returns `IsGettingIn() || IsGettingOut() || IsSwitchSeat()` (`P:\scripts\3_game\human.c:735-738`).
  - Crash and ejection: when the vehicle says a crew member should eject, vanilla activates `eModifiers.MDF_UNCONSCIOUSNESS`, with a comment that this is temporary until a ragdoll command exists (`P:\scripts\4_world\entities\dayzplayerimplement.c:2454-2458`).

## Mechanical object or prop

- Identify selection and hierarchy, pivot and axis, limits and all attached sub-pieces.
- Use physically plausible acceleration, hard-stop, overshoot and damping for the mechanism.
- Check travel envelope and object-object collisions.
- Confirm whether DayZ drives it through `model.cfg`, script, weapon bones or skeletal animation; this decision belongs to `dayz-animation-pipeline`.
- **Graph and template constraints (1.30).**
  - No buffer nodes (1.30 changelog): `Buffer Save` and `Buffer Use` nodes are removed from animation graphs. Keep state in control variables (`AnimSrcGCTVar*`, for example `AnimSrcGCTVarFloat VehicleSteering` at `P:\DZ\anims\workspaces\player\player_main\player_main.agr:113`).
  - Named template groups (1.30 changelog): anonymous animation groups (`$groupType { #ngroupnames 0 ... }`) are no longer supported in `.ast` templates. Every group declares a `Name`, as vanilla does (`Name "ActionContinuous"` at `P:\DZ\anims\workspaces\player\player_main\player_main.ast:4`); `Name "Default"` and `Name ".unnamed"` are other valid forms.
  - Instance files use the `AnimSetInstanceSource` class (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`) instead of the older `$animsetinstance` syntax.

## Physics simulation

- Use `blender-animation` for simulation setup and bake discipline.
- Bake once before sampling; repeated unbaked evaluation is not deterministic evidence.
- Validate contacts and energy and settling after bake.
- Confirm the export route can carry the baked result into DayZ; do not assume Blender-only deformation survives.
- **Ragdoll and simple death are separate (1.30).** The 1.30 changelog adds a Workbench Ragdoll Editor for `.ragdoll` files; vanilla ships `P:\DZ\characters\bodies\human.ragdoll`. Script separates animated death from ragdoll simulation:
  - `PhysicsSetSimpleDeath` handles the animated death; the vanilla comment calls it the old system (`P:\scripts\3_game\human.c:1449`);
  - `PhysicsSetRagdoll` and `PhysicsIsRagdoll` handle the physical ragdoll (`P:\scripts\3_game\human.c:1451-1452`);
  - `IsRagdoll` on `HumanCommandUnconscious` says whether an unconscious character is ragdolling (`P:\scripts\3_game\human.c:647`).

  When authoring death animations, note that one vanilla death branch calls `PhysicsSetSimpleDeath(true)` rather than starting a ragdoll (`P:\scripts\4_world\entities\dayzplayerimplement.c:745`).
