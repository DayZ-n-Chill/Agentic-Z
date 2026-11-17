# Aircraft inputs and in-seat actions

Custom flight inputs on a `CarScript` aircraft and the actions a seated pilot runs: why a custom input reads zero in the seat, how to read it on the server, where a deadzone and a "stick is active" flag belong, and what a sight or camera interface must do so it does not eject the pilot. Vanilla facts cite `P:\` (1.30 scripts). Results from the LFHeli helicopter project and facts read from shipped mods are marked and are not checked on `P:\`.

The `inputs.xml` file format, the `CfgMods` line and the `UAInput` API are in `skills/_shared/enscript/integrations/input_bindings.md`. The LM_Planes binding scheme is in the `dayz-aviation` skill's `references/inputs-and-bindings.md`.

## A wrong name fails silently

A `UA*` action name mistyped anywhere in the chain compiles clean and reads 0 forever, with no error:

1. the `<input name="...">` declaration in the mod's `inputs.xml`,
2. the string passed to the script read (`SyncedValue("...")` or `GetInputByName("...")`),
3. the `loc=` key in the mod's `stringtable.csv` (it only affects the label, but check it in the same pass).

Compare the names one to one, character by character, across the three files before the first boot. The file is registered with `inputs = "<Mod>/inputs.xml"` in the mod's `CfgMods` class, and `loc=` keys resolve from the `stringtable.csv` at the mod root.

## Reading inputs on the server: SyncedValue

The shipped helicopters with a server side solver (SIB and RFFS) read the pilot's inputs on the server through the crew member's input interface. The source notes list MH6 with them, though its recovered flight script reads on the owner (next section):

- `CrewMember(0)` returns the pilot (`P:\scripts\3_game\vehicles\transport.c:187`), and `GetInputInterface()` returns that player's `UAInterface` (`P:\scripts\3_game\entities\man.c:19`).
- `SyncedValue(string action, bool check_focus = true)` returns the action state as a float, 0 or 1 for a button and `<0, 1>` for an analog axis with deadzones applied (`P:\scripts\3_game\inputapi\uainput.c:116-120`). Two opposing actions make one channel from -1 to 1: `right - left`.

**The driver's client must prime each custom action** (LFHeli, 2026-07-12; this was the fix that worked after an input context theory was refuted). Reading on the server is not enough. The owner client in the driver seat must call `player.GetInputInterface().SyncedValue("UA...")` for each custom action every tick and discard the result: that call is what enrols the action in the synced input stream the server reads. RFFS does it (`RFFSHeli_Core.c:491-501` and `:1145` on the client, `:547-554` on the server).

- Priming with `LocalValue()` (`P:\scripts\3_game\inputapi\uainput.c:58`) through a kept `UAInput` does not work: it is gated by the vehicle's active input group and never reaches the synced stream, so the server's `SyncedValue` stays 0 in the seat.
- Symptom: the custom keys are dead only while seated, and the vanilla car inputs still work.
- **No input `<context>` is needed.** RFFS, a shipped `CarScript` helicopter that works, declares none and calls neither `ActivateContext` nor `ActivateExclude`; its `modded_Inputs.xml` holds only `<actions>`, `<sorting>` and `<preset>`.
- When diagnosing "custom vehicle inputs read 0 in the seat", read the `modded_Inputs.xml` of the shipped mod whose architecture is closest (RFFS for `CarScript` plus `SyncedValue`), not of mods that run their own Pawn (MH6, Expansion): those do not answer the context or priming question.

## Reading inputs on the owner: local reads into the move

An aircraft that predicts on the owner (`aviation-networking.md`) reads locally and ships the values in its move. LM_Planes caches the `UAInput` objects once with `GetUApi().GetInputByName("...")` (`P:\scripts\3_game\inputapi\uainput.c:218`) and reads `LocalValue()` in `OnInput`; MH6 polls `LocalHold()` (`P:\scripts\3_game\inputapi\uainput.c:62`) in `EOnPostSimulate`. Caching avoids a lookup by string every input frame.

## Default bindings players already know

The DayZ Expansion helicopter preset is the muscle memory default for new helicopter bindings (read from the preset block of `DayZExpansion\Vehicles\Scripts\Data\Inputs.xml`): cyclic on `kW`, `kS`, `kA`, `kD`; collective up and down on `kLShift` and `kZ`; anti-torque on `kQ` and `kE`; auto hover on `kX`. On a gamepad: thumbstick for cyclic, triggers for collective, shoulder buttons for anti-torque.

## Deadzone and the "stick is active" flag

- **Put the deadzone in the input reader, not in the solver.** A solver that gates on an exact input value (LFHeli's weathervane uses `pedal == 0.0`) needs the analog deadzone upstream: snap to zero, then rescale with `(|v| - dz) / (1 - dz)` (LFHeli uses 0.10). The solver and its offline twin then stay byte identical, and keyboard input of 0 or 1 passes through unchanged.
- **A probe taken after the smoothing filter is not raw** (LFHeli, 2026-08-07). When the solver decides attack against release, or arms auto level, with a boolean `axis != 0`, that axis must be the raw input. A first order filter (`cmd = cmd + (raw - cmd) * k`) writes its output over the working axis and decays asymptotically: it never reaches exactly `0.0`, so the flag stays true forever after the stick is released. Symptom: the attack constant is used on release as well (the stick "does not return"), and anything gated on "no input" (auto level, self level, rest damping) never fires. Keep the raw value in its own field at the moment the input is read, and decide activity only from it, on every side that simulates. In LFHeli `FilterCommandAxes` does `m_CyclicPitch = m_CyclicPitchCmd` (`LFHeliInputs.c:272`); the server probe then read `m_Inputs.m_CyclicPitch` after the filter (`LFHeli_Base.c` near line 1219) and fed it to `StepStateMachine` as the pitch-active flag. So the owner used the raw value and the server the filtered one; they desynced once both sides simulated, and re-level never armed. Verified in code; the in-game A/B flight was still pending.

## Engine start and stop actions

RFFS and SIB replace the vanilla car actions with their own start and stop actions and block the vanilla ones on their class. MH6 keeps vanilla `ActionStartEngine` and `ActionStopEngine`, relabels the prompt, and gates its flight loop on `EngineIsOn()`. What `EngineIsOn()` means on each machine is in `aviation-carscript-base.md`.

## Continuous actions in the seat and camera interfaces

From LFHeli's sight work (2026-08-31), verified in game unless marked:

1. **A continuous action's progress while seated depends on `m_CommandUID`.** `CMD_ACTIONMOD_OPENDOORFW` can animate in a seat and never advance progress, so `OnFinishProgress` never runs and the action looks dead without an error. The one vanilla continuous seated action that completes is `ActionStartEngine`, which sets `m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_STARTENGINE` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:14`). Use that command for this pattern.
2. **An interface that shares a key with seat actions must consume that input.** `SetDisabled(true)` on the input controller (`P:\scripts\3_game\human.c:22`) does not stop action input. On open, call `AddActiveInputExcludes({"menu"})` (declared at `P:\scripts\3_game\gameplay.c:800`, implemented by the mission at `P:\scripts\5_mission\mission\missiongameplay.c:1001`); record whether this interface installed the exclude, and remove it only under that flag on every exit path. Otherwise the same hold that closes the interface can complete the vanilla get-out and eject the player's body while spectating.
3. **Interrupt before excluding.** Installing an exclude while a continuous action is active can hide its release and leave the action manager in progress for good, after which no actions are offered until a relog or an interrupt. Before the exclude, call the vanilla client path `RequestInterruptAction()` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:1341`).
4. **Every `UAInput` read returns zero during an exclude** (verified in code). Raw `KeyState(KeyCode.KC_X)` (`P:\scripts\1_core\proto\ensystem.c:291`) and `GetMouseState` (`P:\scripts\1_core\proto\ensystem.c:326`) still work, but `KeyState` reads the physical key and ignores rebinding. Use it only as a coarse escape path, and read the live binding when rebinding has to be right.
