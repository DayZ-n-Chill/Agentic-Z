# Aircraft on CarScript

The vanilla contracts a plane or helicopter leans on when it inherits `CarScript` and flies in script: which entity events fire, what the car body does to a scripted velocity, how angular velocity is expressed, when the body may sleep, and what stops the engine. Vanilla facts cite `P:\`, which holds the 1.30 scripts. Facts from shipped mods name the mod, and results measured in the TestHeli helicopter project (a third-party `CarScript` helicopter) say so; neither kind is checked on `P:\`.

## Why CarScript

Vanilla ships no flyable aircraft. The native helicopter classes hold no flight code in script (`helicopters.md`) and there is no fixed-wing class. Every shipped community aircraft documented in this pack (LM_Planes for planes; RFFS, MH6, SIB and DayZ Expansion for helicopters) does the same thing: inherit `CarScript`, keep a complete ground `SimulationModule` as the taxi fallback, and fly in script on top of it. `CarScript` brings wheels, crew seats, fluids, the damage system and engine sound for free.

| Layer | Vanilla parent | Where |
|---|---|---|
| Config | `class CarScript: Car` in addon `DZ_Vehicles_Wheeled` | `P:\DZ\vehicles\wheeled\config.cpp:236` |
| Script | `class CarScript extends Car` | `P:\scripts\4_world\entities\vehicles\carscript.c:94` |

The config still needs wheels, axles, a gearbox and an engine block (`simulation.md`), and the script still needs every mandatory override of a car (`class-hierarchy.md`). Engine values that only matter on the ground can stay rough when script takes over in the air: LM_Planes ships `rpmRedline = 80000` and never tunes it. Write the aircraft's own code; the mods named here are patterns to learn from, not sources to copy.

## Events: where the flight loop runs

- **`EOnSimulate` does not fire on a `CarScript` child by default.** The constructor registers only `POSTSIMULATE` and `POSTFRAME` (`P:\scripts\4_world\entities\vehicles\carscript.c:207-208`; lines 325 to 326 in 1.29). A flight loop in `EOnSimulate` needs `SetEventMask(EntityEvent.SIMULATE)` in the aircraft's constructor (the `SIMULATE` flag is at `P:\scripts\1_core\proto\enentity.c:94`). RFFS does exactly this (`RFFSHeli_Core.c:180-181`). When it is missing the mod compiles, spawns and idles normally, and the flight model never runs.
- **`super.EOnSimulate` is an empty stub.** `CarScript` has no `EOnSimulate` override, so `super` reaches the empty body in `IEntity` at `P:\scripts\1_core\proto\enentity.c:201-203`. Skipping it protects nothing, and a comment claiming it "would run engine and fluids twice" is false.
- **The car's real work per tick is in `EOnPostSimulate`** (`P:\scripts\4_world\entities\vehicles\carscript.c:807`; line 948 in 1.29): engine, fluids, part health, the automatic engine stop, exhaust and wheel effects. Much of it is behind `IsServerOrOwner()` (`P:\scripts\4_world\entities\vehicles\carscript.c:845`), so it is meant to run on the owner client too.
- **If the solver is pumped by hand because the native event went quiet, pump both events**, as RFFS does (`RFFSHeli_Core.c:1014-1015` calls `EOnSimulate` then `EOnPostSimulate`), or say plainly that the owner suspends the car's fluid and health tick. Pumping only `EOnSimulate` flies, but for the whole pumped window the owner carries a frozen fuel and damage clock and dead exhaust and wheel effects.
- **`EOnFrame` runs once per rendered frame, not at a fixed rate.** The `FRAME` event is documented as "new frame event, called each frame" (`P:\scripts\1_core\proto\enentity.c:65-69`) and `EOnFrame` hands the real delta in `timeSlice` (`P:\scripts\1_core\proto\enentity.c:183`). Never pump with a hardcoded dt. RFFS's "every 5 ms" pump (`RFFSHeli_Core.c:1008-1015`) is really "at most once per frame", and because it passes a hardcoded `0.025` per call its simulated time runs at frame rate times 0.025: 1.5 times real time at 60 FPS, 3 times at 120, drifting with every frame rate change. Copy the architecture, not the cadence: bank the real `timeSlice` in an accumulator and run fixed steps of the solver's own dt while it lasts, with a ceiling on steps per frame so one long frame cannot avalanche.
- **A silence detector must be refreshed only by the native event.** If the pump refreshes the clock that decides "the native event went quiet", the pump gates itself down to one call per gap.

## Kinematic flight: what the car body does to SetVelocity

Setting the velocity directly (`SetVelocity`, `P:\scripts\1_core\proto\enphysics.c:111`) does fly a `CarScript` body. RFFS ships that way: its `SetVelocityAdjusted` (`RFFSHeli_Core.c:2481` in the PBO) scales only X and Z and passes Y raw to `SetVelocity`. The fixes below were verified in game with a pilot flying, in TestHeli on 2026-07-14.

1. **Gravity is applied after the scripted velocity.** If the solver already subtracts gravity (`accelY = lift - GRAVITY`), the dynamic body subtracts it again and the climb cancels: measured `realVy = tgtVy - g*dt`, a constant -0.21 m/s per tick. `dBodyEnableGravity(this, false)` (`P:\scripts\1_core\proto\enphysics.c:69`) made no difference on a `CarScript` body in that test. The fix is to add `GRAVITY * dt` back to the vertical velocity each flight tick, as RFFS does (`RFFSHeli_Core.c:1854`).
2. **Kill the residual spin after `SetOrientation`.** Call `dBodySetAngularVelocity(this, vector.Zero)` (`P:\scripts\1_core\proto\enphysics.c:165`), or the body's own angular velocity fights the orientation written each tick and the rotation and the seat camera judder. RFFS does this (`RFFSHeli_Core.c:1892`). It smooths rotation only; jittery position is a replication matter (`aviation-networking.md`).
3. **Wheel suspension re-anchors the vertical velocity whenever a wheel touches the ground.** A wheeled placeholder cannot lift off: the measured vertical speed was clamped back to about 0 near the ground. Test without wheels (an `OnDebugSpawn` that skips the wheel `CreateInInventory` calls); a real helicopter model has skids.
4. **An idle car body sleeps, so `EOnSimulate` stops and the state machine stalls.** The collective did nothing until the pilot drove the vehicle to wake it. `dBodyActive(this, ActiveState.ALWAYS_ACTIVE)` from `EEInit` helped but was not enough in one run; whether the body stays awake with a pilot seated and the engine on is still open. Wake it in the get-in or engine start hook. `dBodyActive` is at `P:\scripts\1_core\proto\enphysics.c:64` and the `ActiveState` values at `P:\scripts\1_core\physics\activestate.c:9`.

**A rubberband is not a reason to change the flight mode.** RFFS has no client side pose smoothing: it syncs only instruments (`RFFSHeli_Core.c:189-208`), trusts the car's native replication for the pose, and calls `dBodyActive(this, ActiveState.ACTIVE)` while flying (`RFFSHeli_Core.c:1005-1006`). When a `CarScript` helicopter rubberbands under a pilot, the cause is almost always a custom client smoother (dead reckoning plus a client side `SetPosition`) fighting native replication. Remove it before considering forces. An offline test (a scripted trajectory with `SetPosition` in the air plus `SetVelocity`) flies and can even show a small stutter that tempts adding a smoother, but piloted flight with real inputs behaves differently. Judge the flight mode in game with real inputs before adding smoothing or freezing the mode. A rubberband alone is not evidence for switching to forces.

Test fixture note: the in-game test bridge described in `skills/dayz-launch-test/references/mcp/` can prepare any `CarScript` as a fixture. It runs the vehicle's own `OnDebugSpawn` unless every declared wheel, the fuel and any vital battery or spark plug are already present, and reports the fixture as not ready when they still are not, so it conditions a test helicopter exactly as that helicopter's `OnDebugSpawn` does (see point 3). Conditioning from `EEInit` with a delayed `OnDebugSpawn` call remains an option.

## Angular velocity and axes

- **Angular velocity is not yaw, pitch and roll.** `dBodySetAngularVelocity(body, angvel)` takes an axis vector in world space, in radians per second; the vanilla doc reads "Angular velocity, rotation around x, y and z axis (not yaw/pitch/roll)" (`P:\scripts\1_core\proto\enphysics.c:163`). Feeding a solver's Euler rate triple straight in is wrong in units and in frame.
- **The axis map.** Two independent vanilla sources agree. The worked example for `YawPitchRollMatrix("70 15 45", mat)` at `P:\scripts\1_core\proto\enmath3d.c:127-130` matches `Rz(pitch) * Ry(yaw) * Rx(roll)` to 4e-7, with `mat[i]` being the model's basis vectors in world space. The vehicle camera reads `dBodyGetAngularVelocity` and routes component Y to yaw, Z to pitch and X to roll (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:128-134`). Right hand rule about the world axes. Check against the doc example before trusting a derivation: a wrong sign makes the airframe rotate against the command, which reads as "the fix made it worse".
- **Rate accumulators are not the derivative of the pose that was written.** When the actuator writes an absolute orientation, derive any published angular velocity from the pose delta (`GetTransform` before and after the write, small angle rotation vector `w*dt = 1/2 * sum_i (b_i x a_i)`), never from the integrator's pitch, roll and yaw rate fields. Cosmetic and protective terms routinely change the target orientation without touching those fields; in TestHeli a yaw and roll pendulum, a stabiliser level nudge and a liftoff assist all did. Publishing the accumulators commands a rotation the next absolute write contradicts, so the body integrates one way and the write snaps it back, which is the judder a zero angular velocity write is usually added to hide. The pose delta form is also zero by itself wherever the pose is held or clamped.
- **Engine forward is +Z.** A coordinate measured from a model file may need its Z negated before `ModelToWorld`; `aviation-model-axes.md` has the probe.

## Sleeping the body safely

A vehicle that forces `dBodyActive(this, ActiveState.INACTIVE)` every frame to stop ground jitter needs all of these (TestHeli, 2026-08-31):

1. **Never sleep the body in the same tick as `EEInit`** (verified in game). The collider can fail to finish registering: the visible mesh can be walked through where it is shown, pushes from another position, and get-in actions do not complete. The gap between `EEInit` and the first frame varies by boot (about 1.5 s while the world loads, 3 to 5 ms after a connect with the frame loop running), so the fault can appear and vanish with no code change. Keep physics active for about 3 s after `EEInit` before the first sleep; that warm-up alone restored collision in TestHeli.
2. **Sleep only when settled** (design approved, in-game check partial): speed near zero and height near the terrain. A persisted aircraft can be restored in flight or in motion; sleeping it there freezes it in the air and can separate the physics from the visible shell. The mirror case matters as much: a body born asleep does not wake just because code stops forcing `INACTIVE`. Request `ActiveState.ACTIVE` explicitly while the settled check is false.
3. **Give the settled height check no lower bound** (measured). A grounded vehicle's pivot can be below the surface height (-0.02 m on one airframe), so require only the upper bound plus the velocity condition; a `0 <= height` test rejects a valid settled body.
4. **Cap tuned values at the consumer** (verified in that project). Its loader helper `ClampMinValue(name, value, minimum, fallback)` has no upper clamp, and the fourth argument is the fallback for non-finite values. Enforce a safety maximum where the value is used, for example `Math.Min(tuned, CAP)`; the general rule is not to assume a loader capped a value.

## Engine, gear and the driver leaving

What stops a `CarScript` engine, so a flight design does not stop it by accident:

| Trigger | Vanilla code |
|---|---|
| Driver leaves while the gearbox is not in neutral | `OnDriverExit`: `if (GetGear() != GetNeutralGear()) EngineStop();` at `P:\scripts\4_world\entities\vehicles\carscript.c:940-948` (lines 1207 to 1215 in 1.29) |
| Battery or plug detached | `EEItemDetached` at `P:\scripts\4_world\entities\vehicles\carscript.c:545-573` |
| Destroyed, out of fuel or engine health gone | `EngineStop` in `EOnPostSimulate` at `P:\scripts\4_world\entities\vehicles\carscript.c:848-851` |
| Vital spark plug or glow plug missing | `CheckVitalItemCallback` at `P:\scripts\4_world\entities\vehicles\carscript.c:853-854` |
| Driver unconscious or dead | `MarkCrewMemberUnconscious` and `MarkCrewMemberDead` at `P:\scripts\4_world\entities\vehicles\carscript.c:1658-1677` |

- **A fixed direct gear stops the engine on every dismount.** A design that forces one gear from `OnInput` (for example `ShiftTo(CarGear.FIRST)`, as MH6 does) hits the first row with no error logged. Everything gated on `EngineIsOn()` can then close through `OnEngineStop` as well: cameras, sight sessions, HUD state.
- **The implementation above `CarScript` is empty**: `void OnDriverExit(Human player) {}` in `Transport` (`P:\scripts\3_game\vehicles\transport.c:224`). Leaving out `super` in an override loses only the gear check; the other rows live in other callbacks.
- **Minimal override** (design; the in-game check was still pending in TestHeli) for "engine on means the fixed gear is engaged again by `OnInput`". Do not call `super` in it; the next pilot's input tick restores the direct gear:

```c
override void OnDriverExit(Human player)
{
    ShiftTo(GetNeutralGear());
}
```

- **Open check.** An engine that stays alive without a driver changes the sleep case above. Check that keeping the body awake does not depend only on `CrewMember(0)`, and find out whether the fuel drain in `EOnPostSimulate` continues while the body is `INACTIVE`.

`EngineIsOn()` is not an authority bit on a machine that does not own the vehicle:

- The vanilla start and stop actions are driver actions. `ActionStartEngine` needs a local `GetCommand_Vehicle()` and `CrewDriver() == player` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:26-37`), and `ActionStopEngine` checks the same (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\vehicles\actionstopengine.c:16-33`).
- The driver becomes the pawn owner on sitting down: `OnVehicleSeatDriverEnter` calls `identity.Possess(pawn)` inside `#ifdef FEATURE_NETWORK_RECONCILIATION` (`P:\scripts\4_world\entities\manbase\playerbase.c:4561-4577`).
- Vanilla trusts the engine state for simulation only behind `IsServerOrOwner()` (`P:\scripts\4_world\entities\vehicles\carscript.c:2592-2601`) and reaches other clients through the net synced `m_CarEngineSoundState` (registered at `P:\scripts\4_world\entities\vehicles\carscript.c:285`, read in `OnVariablesSynchronized` at `P:\scripts\4_world\entities\vehicles\carscript.c:446-447`).
- **Late joiners** (verified in game in TestHeli): a client that joins after the engine started can see `EngineIsOn()` as off until someone mounts and causes a resync. For remote rotor visuals and the like, mirror the engine state in a net sync variable the server writes from `OnEngineStart` and `OnEngineStop`, and register it at the end of the constructor's existing bank of sync variables so the bitstream order stays stable (`skills/_shared/enscript/patterns/netsync.md`).

## Seaplanes and water

Vanilla declares `class Buoyancy` on `BoatScript` at `P:\DZ\vehicles\water\config.cpp:32`. LM_Planes puts a `class Buoyancy` on `CarScript` children (a flying boat, a seaplane and an amphibious car) and adds active water physics in script; whether the car simulation reads that class is an LM_Planes result, not checked in game here. Water is detected with `SurfaceIsSea` and `SurfaceIsPond` (`P:\scripts\3_game\global\game.c:1196` to `:1197`). The config block, the two water physics templates and the presets are in the skill's `references/aerodynamics-and-flight-physics.md`.

## Where the depth is

| Need | Open |
|---|---|
| Helicopters: the native classes, the community flight models, which to build from | `helicopters.md` |
| Owner prediction, the Pawn pipeline, ownership timing, camera smoothing | `aviation-networking.md` |
| Custom flight inputs that read zero, in-seat actions, input excludes | `aviation-inputs-and-actions.md` |
| Lights, battery and line numbers after 1.30 | `aviation-dayz-1-30.md` |
| Everything else (lift and stall, presets, sounds, weapons, per-mod breakdowns, flight testing) | the aircraft table of `README.md` |
