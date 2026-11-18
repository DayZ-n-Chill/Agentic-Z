# Aircraft on CarScript

What a plane or helicopter that inherits `CarScript` and flies in script relies on: which entity events fire, what the car body does to a scripted velocity, how angular velocity is expressed, when the body may sleep, and what stops the engine.

Vanilla facts cite `P:\`. Facts from shipped mods name the mod and come from its own scripts. Results measured in game on a test helicopter built on `CarScript` say so; neither kind is checked on `P:\`.

## Why CarScript

Vanilla ships no aircraft that flies. The native helicopter classes hold no flight code in script (`helicopters.md`), and there is no fixed-wing class. Every community aircraft in this pack does the same thing (LM_Planes for planes; RFFS, MH6, SIB and DayZ Expansion for helicopters): inherit `CarScript`, keep a full ground `SimulationModule` for taxiing, and fly in script on top. `CarScript` brings wheels, crew seats, fluids, the damage system and engine sound for free.

| Layer | Vanilla parent | Where |
|---|---|---|
| Config | `class CarScript: Car` in addon `DZ_Vehicles_Wheeled` | `P:\DZ\vehicles\wheeled\config.cpp:236` |
| Script | `class CarScript extends Car` | `P:\scripts\4_world\entities\vehicles\carscript.c:94` |

The config still needs wheels, axles, a gearbox and an engine block (`simulation.md`), and the script still needs every override a car must have (`class-hierarchy.md`). Engine values that only matter on the ground can stay rough when script takes over in the air: LM_Planes ships `rpmRedline = 80000` and never tunes it. Write the aircraft's own code; the mods here are patterns to learn from, not code to copy.

## Where the flight loop runs

- `EOnSimulate` does not fire on a `CarScript` child by default. The constructor registers only `POSTSIMULATE` and `POSTFRAME` (`P:\scripts\4_world\entities\vehicles\carscript.c:207` and `:208`). Put `SetEventMask(EntityEvent.SIMULATE)` in the aircraft's constructor (the flag is at `P:\scripts\1_core\proto\enentity.c:94`); RFFS does (`RFFSHeli_Core.c:180` and `:181` in its scripts). Without it the mod compiles, spawns and idles, and the flight model never runs.
- `super.EOnSimulate` is empty. `CarScript` has no `EOnSimulate`, so `super` reaches the empty body in `IEntity` (`enentity.c:201` to `:203`). Skipping it protects nothing; a comment saying it "would run engine and fluids twice" is wrong.
- The car's real work each tick is in `EOnPostSimulate` (`carscript.c:807`): engine, fluids, part health, the automatic engine stop, exhaust and wheel effects. Much of it sits behind `IsServerOrOwner()` (`carscript.c:845`), so it runs on the owner client too.
- If you pump the solver by hand because the native event went quiet, pump both events, as RFFS does (`RFFSHeli_Core.c:1014` and `:1015` call `EOnSimulate` then `EOnPostSimulate`), or accept that the owner pauses the car's fluid and health tick. Pumping only `EOnSimulate` flies, but while it runs the owner has a frozen fuel and damage clock and no exhaust or wheel effects.
- `EOnFrame` runs once per drawn frame, not at a fixed rate. The vanilla comment on the `FRAME` event says "new frame event, called each frame" (`enentity.c:65`), and `EOnFrame` passes the real delta in `timeSlice` (`enentity.c:183`). Never pump with a fixed dt. RFFS's "every 5 ms" pump (`RFFSHeli_Core.c:1008` to `:1015`) really runs at most once a frame and passes `0.025` each time, so its simulated time runs at frame rate times 0.025: 1.5 times real time at 60 FPS and 3 times at 120. Keep the idea, not the timing: add the real `timeSlice` to an accumulator, run fixed steps of the solver's own dt while it lasts, and cap the steps per frame so one long frame cannot snowball.
- Refresh a "native event went quiet" detector only from the native event. If the pump refreshes it, the pump throttles itself to one call per gap.

## What the car body does to SetVelocity

Setting velocity directly (`SetVelocity`, `P:\scripts\1_core\proto\enphysics.c:111`) does fly a `CarScript` body. RFFS flies that way: its `SetVelocityAdjusted` (`RFFSHeli_Core.c:2481`) scales X and Z and passes Y straight to `SetVelocity`. The fixes below were checked in game with a pilot flying the test helicopter.

1. The body applies gravity after the scripted velocity. If the solver already subtracts gravity (`accelY = lift - GRAVITY`), the body subtracts it again and the climb cancels: the measured vertical speed was the target minus `g * dt`, a steady 0.21 m/s per tick too low. `dBodyEnableGravity(this, false)` (`enphysics.c:69`) made no difference on a `CarScript` body. Add `GRAVITY * dt` back to the vertical velocity each flight tick, as RFFS does (`RFFSHeli_Core.c:1854`).
2. Clear the leftover spin after `SetOrientation`: call `dBodySetAngularVelocity(this, vector.Zero)` (`enphysics.c:165`), or the body's own spin fights the orientation written each tick and the rotation and seat camera judder. RFFS does (`RFFSHeli_Core.c:1892`). This smooths rotation only; jittery position is a network matter (`aviation-networking.md`).
3. Wheel suspension pulls the vertical speed back to about 0 whenever a wheel touches the ground, so a wheeled test model cannot lift off. Test without wheels, with an `OnDebugSpawn` that skips the wheel `CreateInInventory` calls; a real helicopter has skids.
4. An idle car body sleeps, so `EOnSimulate` stops and the flight state stalls; the collective did nothing until the pilot drove forward to wake it. `dBodyActive(this, ActiveState.ALWAYS_ACTIVE)` from `EEInit` helped but was not always enough, and whether the body stays awake with a pilot seated and the engine on is still open. Wake it in the get-in or engine start hook. `dBodyActive` is at `enphysics.c:64` and `ActiveState` at `P:\scripts\1_core\physics\activestate.c:9`.

A rubberband is not a reason to change the flight mode. RFFS has no client pose smoothing: it syncs only instruments (`RFFSHeli_Core.c:189` to `:208`), leaves the pose to the car's own replication, and calls `dBodyActive(this, ActiveState.ACTIVE)` while flying (`RFFSHeli_Core.c:1005` and `:1006`). When a `CarScript` helicopter rubberbands under a pilot, the cause is almost always a custom client smoother (dead reckoning plus a client `SetPosition`) fighting the native replication. Remove it before you consider forces. A scripted path flown offline with `SetPosition` and `SetVelocity` can show a small stutter that tempts you to add a smoother, but piloted flight behaves differently. Judge the flight mode in game with real inputs.

The in-game test bridge (`skills/dayz-launch-test/references/mcp/`) can prepare any `CarScript` as a test vehicle. It runs the vehicle's own `OnDebugSpawn` unless every declared wheel, the fuel and any vital battery or spark plug are already there, and reports the vehicle as not ready if they still are not. So it prepares a test helicopter exactly as that helicopter's `OnDebugSpawn` does (point 3). Calling `OnDebugSpawn` late from `EEInit` also works.

## Angular velocity and axes

- Angular velocity is not yaw, pitch and roll. `dBodySetAngularVelocity(body, angvel)` takes a world space axis vector in radians per second; the vanilla comment reads "Angular velocity, rotation around x, y and z axis (not yaw/pitch/roll)" (`P:\scripts\1_core\proto\enphysics.c:163`). Passing a solver's Euler rates straight in is wrong in units and in frame.
- The axis map. The worked example for `YawPitchRollMatrix("70 15 45", mat)` (`P:\scripts\1_core\proto\enmath3d.c:127` to `:130`) matches `Rz(pitch) * Ry(yaw) * Rx(roll)` to 4e-7, with `mat[i]` the model's basis vectors in world space. The vehicle camera reads `dBodyGetAngularVelocity` and maps Y to yaw, Z to pitch and X to roll (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:128` to `:134`). Use the right hand rule about the world axes, and check a derivation against the vanilla example first: a wrong sign turns the airframe against the command, which looks like the fix made it worse.
- When the code writes an absolute orientation, work out any angular velocity you publish from the change in pose (`GetTransform` before and after the write, with the small angle rotation vector `w*dt = 1/2 * sum_i (b_i x a_i)`), never from the solver's pitch, roll and yaw rate fields. Cosmetic and safety terms change the target orientation without touching those fields; on the test helicopter a yaw and roll pendulum, a levelling nudge and a liftoff assist all did. Publishing the rate fields commands a rotation the next write undoes, so the body turns one way and snaps back, which is the judder a zero angular velocity write is often added to hide. The pose change is also zero by itself wherever the pose is held or clamped.
- Engine forward is `+Z`. A position measured from a model file may need its Z negated before `ModelToWorld`; `aviation-model-axes.md` has the probe.

## Putting the body to sleep safely

A vehicle that forces `dBodyActive(this, ActiveState.INACTIVE)` each frame to stop ground jitter needs all of these:

1. Never sleep the body in the same tick as `EEInit` (checked in game). The collider may not finish registering: players walk through the visible model, it pushes from somewhere else, and get-in actions fail. The gap between `EEInit` and the first frame varies by boot (about 1.5 s while the world loads, 3 to 5 ms after a connect), so the fault comes and goes with no code change. Keep physics awake for about 3 s after `EEInit` before the first sleep; that alone brought collision back on the test helicopter.
2. Sleep only when settled: speed near zero and height near the ground (in-game check partial). A saved aircraft can come back in flight or moving, and sleeping it there freezes it in the air and can split the physics from the visible model. The reverse matters as much: a body born asleep does not wake just because code stops forcing `INACTIVE`, so request `ActiveState.ACTIVE` while the settled check is false.
3. Give the settled height check no lower bound (measured). A grounded vehicle's pivot can sit below the surface, -0.02 m on one airframe, so a `0 <= height` test rejects a settled body. Check only the upper bound and the speed.
4. Cap tuned values where they are used. A loader helper such as `ClampMinValue(name, value, minimum, fallback)` has no upper clamp, and its fourth argument is the fallback for non-finite values. Apply the safety maximum at the point of use, for example `Math.Min(tuned, CAP)`; never assume a loader capped a value.

## What stops the engine

So a flight design does not stop it by accident:

| Trigger | Vanilla code |
|---|---|
| Driver leaves while not in neutral | `OnDriverExit`: `if (GetGear() != GetNeutralGear()) EngineStop();` (`P:\scripts\4_world\entities\vehicles\carscript.c:940` to `:948`) |
| Battery or plug taken off | `EEItemDetached` (`carscript.c:545` to `:573`) |
| Destroyed, out of fuel, or engine health gone | `EngineStop` in `EOnPostSimulate` (`carscript.c:848` to `:851`) |
| A vital spark plug or glow plug missing | `CheckVitalItemCallback` (`carscript.c:853` and `:854`) |
| Driver unconscious or dead | `MarkCrewMemberUnconscious` and `MarkCrewMemberDead` (`carscript.c:1658` to `:1677`) |

- A fixed direct gear stops the engine at every dismount. A design that forces one gear from `OnInput` (for example `ShiftTo(CarGear.FIRST)`, as MH6 does) hits the first row with nothing in the log. Everything tied to `EngineIsOn()` can then shut through `OnEngineStop` too: cameras, sight views, HUD state.
- The version above `CarScript` is empty: `void OnDriverExit(Human player) {}` in `Transport` (`P:\scripts\3_game\vehicles\transport.c:227`). Leaving out `super` in an override loses only the gear check; the other rows live in other callbacks.
- For a design where the engine stays on and `OnInput` puts the fixed gear back, override it without `super`; the next pilot's input tick restores the gear. Not yet checked in game:

```c
override void OnDriverExit(Human player)
{
    ShiftTo(GetNeutralGear());
}
```

- Still open: an engine that keeps running with no driver changes the sleep rules above. Check that keeping the body awake does not depend only on `CrewMember(0)`, and whether the fuel drain in `EOnPostSimulate` continues while the body is `INACTIVE`.

## Engine state on other machines

`EngineIsOn()` is not authoritative on a machine that does not own the vehicle:

- The vanilla start and stop actions are driver actions. `ActionStartEngine` needs a local `GetCommand_Vehicle()` and `CrewDriver() == player` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:26` to `:37`); `ActionStopEngine` checks the same (`P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\vehicles\actionstopengine.c:16` to `:33`).
- The driver becomes the pawn owner on sitting down: `OnVehicleSeatDriverEnter` calls `identity.Possess(pawn)` inside `#ifdef FEATURE_NETWORK_RECONCILIATION` (`P:\scripts\4_world\entities\manbase\playerbase.c:4561` to `:4577`).
- Vanilla trusts the engine state for simulation only behind `IsServerOrOwner()` (`carscript.c:2592` to `:2601`) and tells other clients through the synced `m_CarEngineSoundState` (registered at `carscript.c:285`, read in `OnVariablesSynchronized` at `:446` and `:447`).
- A client that joins after the engine started can see `EngineIsOn()` as off until someone gets in and forces a resync (checked in game). For rotor visuals seen by others, mirror the engine state in a synced variable the server sets from `OnEngineStart` and `OnEngineStop`, and register it after the constructor's existing sync variables so the order stays stable (`_shared/enscript/patterns/netsync.md`).

## Floating

Vanilla declares `class Buoyancy` on `BoatScript` (`P:\DZ\vehicles\water\config.cpp:32`). LM_Planes puts one on `CarScript` aircraft and adds water handling in script; `aviation-seaplanes.md` has the block, the two templates and the water checks.

## Where to go next

| Need | Open |
|---|---|
| Helicopters: the native classes, the community flight models, which to build from | `helicopters.md` |
| Owner prediction, ownership timing, camera smoothing | `aviation-networking.md` |
| Custom flight inputs that read zero, actions in the seat, input excludes | `aviation-inputs-and-actions.md` |
| Lights and battery after DayZ 1.30 | `aviation-dayz-1-30.md` |
| Lift and stall, presets, sounds, weapons, each helicopter mod, flight testing | The aircraft table in `README.md` |
