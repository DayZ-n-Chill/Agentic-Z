# Ragdoll files and fall damage (DayZ 1.30)

Covers the 1.30 changes to player physics: the data driven `.ragdoll` file, `PhysicsSetSimpleDeath` against `PhysicsSetRagdoll`, the guard against waking while falling, the exponential fall damage curve, and the line moves of the action cursor code.

Not covered here: binding a `.ragdoll` to a character (`ragdoll =` on `SurvivorBase`) belongs to the dayz-characters skill, and the animation graph side (the surrender state and its events) to the dayz-animation-pipeline skill.

Citations are `P:\...:line`, opened on `P:\` (a 1.30 build). `1.29:<path>:<line>` is a line in the 1.29 scripts, which are not on `P:\` and were not re-checked. Code blocks marked `[EXACT]` are copied from the cited file. `[UNVERIFIED]` means no script call site or no in-game test; `[INFERRED]` and `[DESIGN]` are reasoning, not test results.

## 1. `.ragdoll` and `RagdollDef`

- Up to 1.29 the player ragdoll's collision and mass lived in native code; script only saw `PhysicsSetRagdoll`.
- From 1.30 vanilla ships a text `RagdollDef` next to the body: `P:\DZ\characters\bodies\human.ragdoll`.
- Workbench added a ragdoll editor for `.ragdoll` files (1.30 experimental modding changelog).
- There is no `LoadRagdollFile` or similar call in `P:\scripts`. `[UNVERIFIED]` whether a custom creature loads a `.ragdoll` of the same name on its own through the `.xob` GUID.

### Infected do not ragdoll

Measured in game on 1.30.164078, 2026-10-16.

`[EXACT]` The ragdoll API is on `Human` only. `PhysicsSetSimpleDeath`, `PhysicsSetRagdoll` and `PhysicsIsRagdoll` are declared at `P:\scripts\3_game\human.c:1449-1452`, inside `class Human : Man` (`P:\scripts\3_game\human.c:1359`). Infected inherit `DayZInfected`, then `DayZCreatureAI`, then `DayZCreature`, then `EntityAI` (`P:\scripts\3_game\entities\dayzinfected.c:104`, `P:\scripts\3_game\entities\dayzanimal.c:191` and `:24`), so none of those calls exist on an infected and a script call to one will not compile. The same declarations are in builds 1.30.164014, 1.30.164078 and 1.30.164200 (not checked on `P:\`, which holds one build).

Config and clips did not work around it in that test. A custom infected (its own `.xob`, with its own 1.30 graph) was given `ragdoll = "DZ/characters/bodies/human.ragdoll";` in both `enfanimsys` blocks, and its death states were pointed at vanilla player death `.anm` clips that embed the `Ragdoll` event (`p_erc_death01_F` and others). Both test kills ran `DayZInfectedCommandDeathModdable`, played the full clip and froze in the last pose. There was no limp body and no RPT error.

- The RPT logs no `Initializing ragdoll` line at default verbosity, not even for a player death. The absence of that line proves nothing either way; only the in-game result does.
- A custom `.ragdoll` for the infected `.xob` is untested. `[INFERRED]` It may not help: in the test the infected death command played clips that carry the `Ragdoll` event and no ragdoll started, so a working definition might never be activated either.
- `[DESIGN]` The remaining route is a corpse swap. On server death, delete the infected, spawn a `PlayerBase` survivor at the same transform, move the clothing, gear and weapon onto it, then kill it so the player death path ragdolls it. The head and hands become a vanilla survivor's. Untested.

### The vanilla file

```c
// [EXACT] P:\DZ\characters\bodies\human.ragdoll:1
RagdollDef {
 Object "{D470A4E7581CCE23}DZ/anims/workspaces/player/Models/player_m_editorpreview.xob"
 {
  RagdollBone pelvis {
   Mass 17
   Offset -0.008 -0.011 0
   Geometries {
    PhysicsCapsuleGeometry Spine1 {
     SurfaceProperties "DZ/data/data/penetration/flesh.bisurf"
     Offset 0 0.914 0.015
     Orientation 0 0 90
     Radius 0.1
     Height 0.2
    }
    PhysicsCapsuleGeometry Spine2 {
     Offset 0 1.061 0
     Radius 0.1
     Height 0.1
    }
   }
   {
```

The head is a sphere, not a capsule:

```c
// [EXACT] P:\DZ\characters\bodies\human.ragdoll:38
      RagdollBone head {
       Mass 6.1
       Offset 0.094 0 0
       Geometries {
        PhysicsSphereGeometry Head {
         SurfaceProperties "DZ/data/data/penetration/flesh.bisurf"
         Offset 0 1.672 -0.009
         Radius 0.1
        }
       }
       JointMinLimits -70 -35 -40
       JointMaxLimits 70 35 45
       JointStiffness 0.8
       JointDamper 0.3
      }
```

`[DESIGN]` Author a custom humanoid ragdoll by copying this tree, matching the `RagdollBone` names to the skeleton, and keeping `SurfaceProperties` on a penetration `.bisurf`. Joint limits are degrees relative to the parent.

Masses in the vanilla file, in kg, by line of `P:\DZ\characters\bodies\human.ragdoll`: pelvis 17 (`:5`), spine3 15 (`:23`), head 6.1 (`:39`), leftarm 2.1 (`:54`), leftforearm 1.7 (`:69`), rightarm 2.1 (`:85`), rightforearm 1.7 (`:100`), leftupleg 7.5 (`:118`), leftleg 6.6 (`:134`), rightupleg 7.5 (`:159`), rightleg 6.6 (`:175`). The sum is 73.9 kg. The 87.5 kg that `dBodyGetMass` read on a live player (see `SKILL.md`) is a different body: the player's controller body, not this ragdoll definition.

## 2. `PhysicsSetSimpleDeath` against `PhysicsSetRagdoll`

Up to 1.29 the `PhysicsSetRagdoll` comment was at `1.29:3_game\human.c:1417-1418`, and death called `PhysicsSetRagdoll(true)` at `1.29:4_world\entities\dayzplayerimplement.c:736`.

```c
// [EXACT] P:\scripts\3_game\human.c:1448
	//! Old system for handling player death state, was previously handled by PhysicsSetRagdoll
	proto native	void		PhysicsSetSimpleDeath(bool pEnable);
	
	proto native	void		PhysicsSetRagdoll(bool pEnable);
	proto native	bool		PhysicsIsRagdoll();
```

`PhysicsIsFalling` also documents ragdoll motion:

```c
// [EXACT] P:\scripts\3_game\human.c:1426
	//! returns true if physics controller is falling 
	//! returns true if the ragdoll is moving greater than 1m/s
	proto native 	bool		PhysicsIsFalling(bool pValidate);
```

The death branch that starts no death command, from 1.30:

```c
// [EXACT] P:\scripts\4_world\entities\dayzplayerimplement.c:743
			else
			{
				PhysicsSetSimpleDeath(true);
			}
```

The unconscious ragdoll query lives on the command, not only on `Human`:

```c
// [EXACT] P:\scripts\3_game\human.c:644
	proto native void 	WakeUp(int targetStance = -1);
	proto native bool	IsWakingUp();

	proto native bool   IsRagdoll();
```

Vanilla clears the vehicle re-attach while that ragdoll is active:

```c
// [EXACT] P:\scripts\4_world\entities\manbase\playerbase.c:3346
			if (hcu && hcu.IsRagdoll())
			{
				// Don't attach us back to the vehicle once we wake up
				m_TransportCache = null;
			}
```

## 3. Waking up while falling

Up to 1.29 there was only `m_UnconsciousTime > 2` at `1.29:4_world\entities\manbase\playerbase.c:3184`, then `hcu.WakeUp`. An in-game test of a 0.5 s wake buried the player 40 m under the terrain (see `SKILL.md`).

```c
// [EXACT] P:\scripts\4_world\entities\manbase\playerbase.c:3419
						//! protection for a player being broken when attempting to wake them up too early into unconsciousness
						if (m_UnconsciousTime > 2)
						{
							// If the player is falling then prevent waking up
							if (false == PhysicsIsFalling(false))
							{
								int wakeUpStance = DayZPlayerConstants.STANCEIDX_PRONE;
	
								//! Don't set the stance if we are swimming or in a vehicle, stance change animation could play
								if (m_Swimming.m_bWasSwimming || m_LastCommandBeforeUnconscious == DayZPlayerConstants.COMMANDID_VEHICLE)
									wakeUpStance = -1;
	
								hcu.WakeUp(wakeUpStance);
```

`[DESIGN]` A custom get-up from unconsciousness or a ragdoll must keep both guards. `PhysicsIsFalling(false)` is true while the ragdoll moves faster than 1 m/s (`P:\scripts\3_game\human.c:1426-1428`), so a ragdoll that is still tumbling will not wake.

## 4. Fall damage `CurveExp`

Up to 1.29 the curve was a linear `Math.InverseLerp` (`HandleFallDamage`, `1.29:4_world\entities\dayzplayerimplementfalldamage.c:97`) with `HEALTH_HEIGHT_LOW = 5`, `HEALTH_HEIGHT_HIGH = 14`, `SHOCK_HEIGHT_LOW = 3`, `SHOCK_HEIGHT_HIGH = 12`, `BROKENLEGS_HEIGHT_LOW = 5` and `BROKENLEGS_HEIGHT_HIGH = 9` (`1.29:4_world\entities\dayzplayerimplementfalldamage.c:26-32`).

```c
// [EXACT] P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:26
	const float		HEALTH_HEIGHT_LOW 		= 2;
	const float		HEALTH_HEIGHT_HIGH 		= 12;

	private const float		SHOCK_HEIGHT_LOW 		= 0;
	private const float		SHOCK_HEIGHT_HIGH 		= 8;
	private const float		BROKENLEGS_HEIGHT_LOW 	= 3;
	private const float		BROKENLEGS_HEIGHT_HIGH 	= 8;
```

```c
// [EXACT] P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:92
	float CurveExp(float low, float high, float value, float power)
	{
	    float t = Math.InverseLerp(low, high, value);
	    t = Math.Clamp(t, 0, 1);
	    return Math.Pow(t, power);
	}
```

The powers `HandleFallDamage` passes to `CurveExp` (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:104-139`): health 2.0, shock 2.0, broken legs 2.5, bleeding hands and feet 1.8, bleeding legs 2.0, gloves 2.0, shoes 2.2, pants 2.0, bleeding chance 2.0.

```c
// [EXACT] P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:160
	private float Randomize(int pType, float pValue)
	{
		if (pValue == 1)
			return pValue;
```

The ammo names are unchanged: `FALL_DAMAGE_AMMO_HEALTH` is `"FallDamageHealth"` and `FALL_DAMAGE_AMMO_SHOCK` is `"FallDamageShock"` (`P:\scripts\4_world\entities\dayzplayerimplementfalldamage.c:20-21`), applied with `ProcessDirectDamage` at `:155-156`. Both ammo classes are in `P:\DZ\weapons\melee\config.cpp` (`FallDamageHealth` at `:2182`, `FallDamageShock` at `:2201`).

`[DESIGN]` A 1.29 `modded class` that lists `HEALTH_HEIGHT_LOW = 5` again and uses `InverseLerp` will compile and then silently restore the old, weaker curve. Replace the body with `CurveExp`, or do not override the constants.

## 5. Action cursor (View Geometry) and liquid surfaces

The rule that the action cursor sees View Geometry still holds (`SKILL.md`, truth 2). Only the lines moved:

- `RaycastRVProxy`: `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:255`. `RaycastRVParams` still defaults to `ObjIntersectView` (`P:\scripts\3_game\global\dayzphysics.c:88`).
- Ground fallback with `RayCastBullet` and `ROADWAY|TERRAIN|WATERLAYER`: `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:383-384`.
- A liquid surface with no object gets utility 0.01 (the `LIQUID_NONE` test, `P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:532-534`). The `ActionTarget` constructor takes `surfaceName` (`:125`), and `GetSurfaceLiquidType()` reads the result (`:184-187`).

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:255
		if (DayZPhysics.RaycastRVProxy(rayInput, results))
```

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:383
			PhxInteractionLayers collisionLayerMask = PhxInteractionLayers.ROADWAY|PhxInteractionLayers.TERRAIN|PhxInteractionLayers.WATERLAYER;
			DayZPhysics.RayCastBullet(m_RayStart,m_RayEnd,collisionLayerMask,null,hitObject,contact_pos,hitNormal,hitFraction);
```

```c
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actiontargets.c:532
		//! surfaces with liquid source
		if (m_SurfaceInfo && m_SurfaceInfo.GetLiquidType() != LIQUID_NONE)
			return 0.01;
```

## 6. Related 1.30 notes (next to physics, owned elsewhere)

- `disableSimulation` on house based entities, with `Entity.DisableSimulation` and `GetIsSimulationDisabled` (`P:\scripts\3_game\entities\entity.c:3-6`): a model pipeline topic (dayz-model-pipeline skill); listed in the 1.30 experimental modding changelog.
- `SurfaceInfo.GetSoundHitType` and `SoundHitType`: listed in the official 1.30 changelog but not present in `P:\scripts\3_game\surfaceinfo.c` (0 matches for `SoundHitType` in `P:\scripts`). `[UNVERIFIED]`.
- The Motorbike branch (`Motorbike.CastTo`) inside `RegisterTransportHit` (`P:\scripts\3_game\entities\entityai.c:4166-4183`): see `damage-and-transporthit.md`. Vehicle authoring belongs to the dayz-vehicles and dayz-motorbikes skills.
- `DayZPlayer.IsFirstRenderFrame` (`P:\scripts\3_game\dayzplayer.c:1186-1189`): a skip for catch-up ticks, not a rigid body call.
