# Extra checks per kind of animation

Which checks to add, on top of the common contract in `motion-contract.md`, for a player action, a hand on a weapon or object, locomotion, a creature, a vehicle occupant, a mechanical prop and a physics simulation. Use only the sections the task needs.

Lines that say "1.30 changelog" give Bohemia's stated 1.30 engine changes that are not checked on `P:\`. Comparisons with 1.29 cannot be checked on a 1.30 `P:\`.

## Player or humanoid action

- Check which body layer and export mask the action may use before you key it.
- Track where the centre of mass goes, what the shoulder and clavicle add, and the counter motion.
- Leave the locomotion and root channels the game layer owns alone.
- Test the stances and camera modes that can change IK or blending.
- Review the way into and out of the action, not only its middle.
- Surrender is a player state in 1.30, not an item. `SurrenderDummyItem` is marked `Obsolete` (`P:\scripts\4_world\entities\itembase\surrenderdummyitem.c:1`), and only the obsolete `CheckEmoteLockedState` still looks for it in the hands (`P:\scripts\4_world\classes\emotemanager.c:1212`). `SetSurrenderState` on `PlayerBase` sets it (`P:\scripts\4_world\entities\manbase\playerbase.c:2116`), `IsSurrendered` on `Man` reads it (`P:\scripts\3_game\entities\man.c:67`) and `ClearSurrenderState` clears it (`emotemanager.c:1246`). Do not key an interaction that expects a hidden dummy in the hands during surrender.
- `SetAnimationInstanceByName` on `Human` switches the animation instance from script, with a blend time (`P:\scripts\3_game\human.c:1384`); the vanilla comment warns it can desync when misused. To return to the unarmed base, vanilla registers an `"Empty"` profile on `player_main.asi` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:1548`).
- `HumanInputController` can cap speed and freeze horizontal camera turning per stance: `SetErectSpeedLimit`, `SetCrouchSpeedLimit`, `SetProneSpeedLimit`, each `(bool bShouldDisable, int pMaxErectSpeed)` (`human.c:230` to `:232`), and `DisableErectCameratHorizontalRotation`, `DisableCrouchCameratHorizontalRotation`, `DisableProneCameraHorizontalRotation`, each `(bool pDisable)` (`:240` to `:242`). Vanilla spells two of them `Camerat`; keep that spelling. Plan for wide looking being locked during heavy or prone gestures.
- A graph tag bound with `BindTag` is tested with `IsTag` on `HumanAnimInterface` (`human.c:319`).

`DayZPlayerConstants` lists eleven full body actions from 256 up (`P:\scripts\3_game\dayzplayer.c:889` to `:899`). The stance comes from the vanilla comment on each line (`pne` prone, `cro` crouch, `erc` erect):

| Constant | Value | Stance | Use |
|---|---|---|---|
| `CMD_ACTIONFB_COMBINATIONLOCK` | 256 | prone | Combination lock; the erect and crouch version is `CMD_ACTIONMOD_COMBINATIONLOCK`, also 256 (`dayzplayer.c:766`). |
| `CMD_ACTIONFB_WASHFACEPOND` | 257 | crouch | Washing the face at a pond; the modifier version is `CMD_ACTIONMOD_WASHFACE`, which follows line 766 with no value, so 257. |
| `CMD_ACTIONFB_BUILDROPELADDER` | 258 | crouch | Making a rope ladder. |
| `CMD_ACTIONFB_BRICKSTACK` | 259 | erect, crouch | Stacking bricks. |
| `CMD_ACTIONFB_BRICKTROWEL` | 260 | erect, crouch | Trowel work. |
| `CMD_ACTIONFB_MIX_MORTAR` | 261 | crouch | Mixing mortar in a bucket. |
| `CMD_ACTIONFB_DRINKWELL_BUCKET` | 262 | erect | Drinking from a well bucket. |
| `CMD_ACTIONFB_SHARPEN` | 263 | crouch | Sharpening a stone tool. |
| `CMD_ACTIONFB_WASHFACEWELL` | 264 | erect | Washing the face at a well. |
| `CMD_ACTIONFB_WETCLOTH` | 265 | crouch | Wetting a cloth at a pond. |
| `CMD_ACTIONFB_WETCLOTHWELL` | 266 | erect | Wetting a cloth at a well. |

## Hand on a weapon or object

- Apply every rule in `motion-biomechanics.md`.
- Find the whole moving assembly before posing.
- Take jammed, closed, open and similar states from checked geometry or data.
- Keep the contact locked until the declared release, then check clearance.
- Show a regrip as approach, open hand, close round the target, grip; never jump a closed fist into place.
- Compare start and end with the real in game IK pose.
- `OnItemInHandsChanged` on `HumanItemAccessor` takes `pChangeAnimationInstance`, default `true` (`P:\scripts\3_game\humanitems.c:112`); `false` changes the item without switching the instance. `EnableAutoAnimInstUpdateOnHandsChange` turns the automatic switch on or off (`:115`).

Many vanilla tools and weapons have their own instance file instead of the generic one or two handed one. Each row is an `AddItemInHandsProfileIK` line in `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c`; check hand poses against that file, not `player_main_1h.asi` or `player_main_2h.asi`:

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
| `SCARH_Base`, `SCARL_Base` | `weapons/player_main_SCARH.asi` for both | `:444`, `:445` |

Reported, not checkable on a 1.30 `P:\`: on 1.29 only `SCARH_Base` of these had its own file.

## Locomotion

- Define gait, stride, cadence, stance and who owns root motion.
- Check foot lock, ground sinking, slip distance and the hand over from one support foot to the other.
- Track the pelvis and centre of mass arcs and the upper body counter turn.
- Match pose and velocity at the loop seam.
- Test slopes and turns only when the graph or game will use them.
- Under a per stance speed limit (`SetErectSpeedLimit` and the others above) scaled root motion must not make the feet slide.

## Creature

- Get the real skeleton, rest pose and gait reference for that species and rig.
- Address bones by name. The 1.30 changelog drops the 250 bone limit and fixed indices except on `EntityPosition`. On `P:\` the infected skeleton `hermit_newbindpose.xob` (`skeletonName` in `P:\DZ\characters\zombies\config.cpp:76`) still lists `index` values on its core bones (`Pelvis` at `P:\DZ\anims\cfg\skeletons.anim.xml:8`), while the four animal skeletons new in 1.30 carry one only on `EntityPosition` (`:988`): `ovis_gmelini_skeleton.xob` (mouflon, `:986`), `canis_familiaris_dobermann_skeleton.xob` (`:1047`), `canis_familiaris_german_shepherd_skeleton.xob` (`:1121`) and `varanus_griseus_skeleton.xob` (`:1194`).
- Creature graphs are `.agf` files in Enfusion config syntax listed by an `AnimSrcGraph` index; the wolf's names `Wolf_MainGraph.agf` under `GraphFilesResourceNames` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_graph.agr:157`). The 1.29 wolf graph was already two text files, in the older `$AnimGraph 7 {` syntax.
- Quadrupeds turn bones to the terrain slope with `AnimSrcNodeProcTransform`. Check that the root and collarbones follow `SlopeAngleX` so the feet do not sink into slopes. The wolf's `AlignToTerrain_Rot` (`P:\DZ\animals\animations\!graph_files\wolf\wolf_maingraph.agf:5`) starts with `scene_root`, then `lflegcollarbone`:

```c
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

- The wolf graph predicts `EntityPosition` with `AnimSrcNodePrediction` and `PercentTime 0.3` for translation and rotation (`wolf_maingraph.agf:52`) and looks with `AnimSrcNodePose2` nodes such as `StandNervousLookAt_ANIM` (`:2024`).
- `MINDSTATE_COWER`, new in 1.30, is the last infected mind state (`P:\scripts\3_game\entities\dayzinfected.c:18`). The infected look pose is an `AnimSrcNodePose2` driven by `LookDirX` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:8`), blended in by `AggroLookBlendT`, an `AnimSrcNodeBlendT` on the condition `Look` (`:19`).

## Vehicle occupant

- Take seat, grip, pedal or footrest and steering anchors from the real model.
- Keep hands and feet locked to moving controls through their whole travel.
- Check elbow and knee solutions at full steering and through transitions.
- Check the get in and get out side and clearance apart from the seated loop.
- Leave anchor extraction and vehicle behaviour to the vehicle pack.

Motorbikes in 1.30:

| Part | Fact |
|---|---|
| Instances | `MOTO1 = 10`, `MOTO2 = 11` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:13` and `:14`), returned by `Motorbike_01_ColorBase` (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:50`) and `Motorbike_02_ColorBase` (`motorbike_02.c:51`). They are a Jawa 50 cc and the three wheeled Jawa Bitrak (model names not checked on `P:\`). |
| Camera | `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`); its class `DayZPlayerCamera3rdPersonVehicleMotorbike` lags on a spring (`CONST_SPRING_SMOOTHTIME_YAW`, `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:258`). |
| Handlebar IK | Two bone IK nodes `AnimSrcNodeIK2` and `AnimSrcNodeIK2Target` in the vehicle subgraph, including the pair `MotoEngineIKTarget` and `MotoEngineVehicleIK` (`P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1436` and `:1446`). |
| Rider lean | Torso, spine and head lean follow `VehicleSteering`, `VehicleThrottle` and `VehicleSuspension`, declared in `P:\DZ\anims\workspaces\player\player_main\player_main.agr:113`, `:118` and `:205` and used in the subgraph (`VehicleSuspension` at `vehicles.agf:1544`). |
| Transitions | `IsTransitioning` on `HumanCommandVehicle` returns `IsGettingIn() || IsGettingOut() || IsSwitchSeat()` (`P:\scripts\3_game\human.c:735` to `:738`). |
| Crash | When the vehicle says a crew member should eject, vanilla applies `eModifiers.MDF_UNCONSCIOUSNESS`, with a comment that this stands in until a ragdoll command exists (`P:\scripts\4_world\entities\dayzplayerimplement.c:2454` to `:2458`). |

## Mechanical object or prop

- Find the selection and hierarchy, pivot and axis, limits and every attached piece.
- Give the mechanism believable acceleration, hard stop, overshoot and damping.
- Check its travel and collisions with other objects.
- Confirm whether DayZ drives it through `model.cfg`, script, weapon bones or a skeletal clip; `model-cfg-animations.md` and `anm-clips.md` decide that.
- 1.30 changelog: `Buffer Save` and `Buffer Use` graph nodes are removed. Keep state in control variables (`AnimSrcGCTVar*`, for example `AnimSrcGCTVarFloat VehicleSteering` at `player_main.agr:113`).
- 1.30 changelog: unnamed groups (`$groupType { #ngroupnames 0 ... }`) are no longer allowed in `.ast` templates. Every group has a `Name`, as vanilla's do (`Name "ActionContinuous"`, `P:\DZ\anims\workspaces\player\player_main\player_main.ast:4`); `Name "Default"` and `Name ".unnamed"` are also valid.
- Instance files use the `AnimSetInstanceSource` class (`P:\DZ\anims\workspaces\player\player_main\player_main.asi:1`), not the older `$animsetinstance` syntax.

## Physics simulation

- Set up and bake the simulation as `blender-mcp-workflow.md` says.
- Bake once before sampling; evaluating an unbaked simulation again and again does not give the same result.
- Check contacts, energy and settling after the bake.
- Confirm the export route can carry the baked result into DayZ; Blender only deformation does not survive by default.

Ragdoll and animated death are separate. The 1.30 changelog adds a Workbench Ragdoll Editor for `.ragdoll` files, and vanilla ships `P:\DZ\characters\bodies\human.ragdoll`. `PhysicsSetSimpleDeath` runs the animated death, which the vanilla comment calls the old system (`human.c:1449`); `PhysicsSetRagdoll` and `PhysicsIsRagdoll` handle the physical ragdoll (`:1451` and `:1452`); `IsRagdoll` on `HumanCommandUnconscious` says whether an unconscious character is ragdolling (`:647`). One vanilla death branch calls `PhysicsSetSimpleDeath(true)` instead of starting a ragdoll (`dayzplayerimplement.c:745`).
