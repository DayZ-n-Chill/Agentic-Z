# Aircraft inputs and seat actions

Why a custom flight input reads zero in the seat, how to read it on the server or the owner, where a deadzone and a "stick is active" flag belong, and what a sight or camera screen must do so it does not throw the pilot out.

Vanilla facts cite `P:\`. Facts read from shipped mods name the mod. Results measured on a test helicopter built on `CarScript` say so; neither kind is checked on `P:\`. The `inputs.xml` format and the `UAInput` API are in `_shared/enscript/integrations/input_bindings.md`; the LM_Planes key scheme is in `aviation-input-bindings.md`.

## A wrong name fails silently

A `UA*` action name mistyped anywhere in the chain compiles and reads 0 forever, with no error. Before the first boot, compare the name character by character in:

1. the `<input name="...">` line in the mod's `inputs.xml`;
2. the string the script reads (`SyncedValue("...")` or `GetInputByName("...")`);
3. the `loc=` key in `stringtable.csv`, which only changes the label but belongs in the same check.

The file is registered with `inputs = "<Mod>/inputs.xml"` in the mod's `CfgMods` class, and `loc=` keys come from the `stringtable.csv` at the mod root.

## Reading inputs on the server

SIB and RFFS, the helicopters with a server side solver, read the pilot's input on the server:

- `CrewMember(0)` returns the pilot (`P:\scripts\3_game\vehicles\transport.c:190`), and `GetInputInterface()` returns that player's `UAInterface` (`P:\scripts\3_game\entities\man.c:19`).
- `SyncedValue(string action, bool check_focus = true)` returns the action state as a float: 0 or 1 for a button, and a value from 0 to 1 with deadzones applied for an analog axis (`P:\scripts\3_game\inputapi\uainput.c:116` to `:120`). Two opposite actions make one channel from -1 to 1: `right - left`.

The driver's client must prime each custom action. Reading on the server is not enough: the owner client in the driver seat must call `player.GetInputInterface().SyncedValue("UA...")` for each custom action every tick and throw the result away. That call is what puts the action into the synced input stream the server reads. RFFS does it (`RFFSHeli_Core.c:491` to `:501` and `:1145` on the client, `:547` to `:554` on the server). Checked in game on the test helicopter.

- Priming with `LocalValue()` (`uainput.c:58`) on a kept `UAInput` does not work: the vehicle's active input group gates it, so it never reaches the synced stream and the server reads 0.
- The sign: the custom keys are dead only while seated, and the vanilla car inputs still work.
- No input `<context>` is needed. RFFS declares none and calls neither `ActivateContext` nor `ActivateExclude`; its `modded_Inputs.xml` holds only `<actions>`, `<sorting>` and `<preset>`.
- When custom inputs read 0 in the seat, compare against the shipped mod whose design is closest: RFFS for `CarScript` plus `SyncedValue`. MH6 and Expansion run their own Pawn classes and do not answer this question.

## Reading inputs on the owner

An aircraft that predicts on the owner (`aviation-networking.md`) reads locally and sends the values in its move. LM_Planes looks up each `UAInput` once with `GetUApi().GetInputByName("...")` (`uainput.c:218`) and reads `LocalValue()` in `OnInput`; MH6 polls `LocalHold()` (`uainput.c:62`) in `EOnPostSimulate`. Looking up once saves a string lookup every input frame (`aviation-script-performance.md`).

## Keys players already know

The DayZ Expansion helicopter preset is what players expect for a new helicopter (read from the preset block of its `Vehicles\Scripts\Data\Inputs.xml`): cyclic on `kW`, `kS`, `kA` and `kD`; collective up and down on `kLShift` and `kZ`; anti-torque on `kQ` and `kE`; auto hover on `kX`. On a gamepad: the stick for cyclic, the triggers for collective, the shoulder buttons for anti-torque.

## Deadzone and the "stick is active" flag

- Put the deadzone in the input reader, not the solver. A solver that tests an exact input value (a weathervane check on `pedal == 0.0`) needs the deadzone before it: snap to zero, then rescale with `(|v| - dz) / (1 - dz)`; the test helicopter uses `0.10`. The solver and its offline copy then stay the same, and keyboard values of 0 and 1 pass through untouched.
- Decide "active" from the raw input, never from the smoothed one. A first order filter (`cmd = cmd + (raw - cmd) * k`) only approaches 0 and never reaches exactly `0.0`, so an `axis != 0` test on its output stays true forever after the stick is released. The attack rate is then used on release too (the stick does not come back), and everything that waits for "no input" (auto level, self levelling, damping at rest) never runs. Store the raw value in its own field when you read it, and decide activity from that field on every side that simulates. On a test helicopter, the input filter wrote the smoothed value back over the input axis, and the server read that axis after filtering and used it as the pitch-active flag, so the owner used the raw value and the server the filtered one, they drifted apart once both simulated, and levelling never armed. Found in the mod's code; not yet confirmed by an in-game comparison.

## Engine start and stop actions

RFFS and SIB replace the vanilla car actions with their own start and stop actions and block the vanilla ones on their class. MH6 keeps the vanilla `ActionStartEngine` and `ActionStopEngine`, changes the prompt text, and runs its flight loop only while `EngineIsOn()`. What `EngineIsOn()` means on each machine is in `aviation-carscript-base.md`.

## Seat actions and camera screens

Checked in game on the test helicopter's sight unless marked:

1. A continuous action in a seat advances only with the right `m_CommandUID`. With `CMD_ACTIONMOD_OPENDOORFW` it can animate and never progress, so `OnFinishProgress` never runs and the action looks dead with no error. The one vanilla continuous seat action that completes is `ActionStartEngine`, which sets `m_CommandUID = DayZPlayerConstants.CMD_ACTIONMOD_STARTENGINE` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actionstartengine.c:14`). Use that command.
2. A screen that shares a key with seat actions must take that input. `SetDisabled(true)` on the input controller (`P:\scripts\3_game\human.c:22`) does not stop action input. On open, call `AddActiveInputExcludes({"menu"})` (declared at `P:\scripts\3_game\gameplay.c:800`, implemented at `P:\scripts\5_mission\mission\missiongameplay.c:1001`), remember that this screen added it, and remove it on every exit path only when it did. Otherwise the same hold that closes the screen can finish the vanilla get-out and throw the player's body out while they look through the sight.
3. Interrupt before you exclude. Adding an exclude while a continuous action runs can hide its release and leave the action manager stuck, offering no actions until a relog or an interrupt. Call `RequestInterruptAction()` first (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:1341`).
4. Every `UAInput` read returns zero during an exclude (found in the code). Raw `KeyState(KeyCode.KC_X)` (`P:\scripts\1_core\proto\ensystem.c:291`) and `GetMouseState` (`:326`) still work, but `KeyState` reads the physical key and ignores rebinding. Use it only as a rough way out, and read the live binding when rebinding matters.
