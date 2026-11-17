# Scripted camera exit, interfaces opened from a seat, and the loading screen hook

Three lifecycle contracts that sit next to UI work and fail late: leaving a scripted camera (spectator, CCTV, drone), opening an interface while the player sits in a vehicle, and replacing the loading screen background.

**How facts are marked here.** A `P:\` path with a line was opened and checked on `P:\` (DayZ 1.30). Results described as checked against a working implementation or measured in game are from a shipped mod on DayZ 1.29 (unless a line says otherwise) and are not yet checked on `P:\`.

---

## Contents

- [Scripted camera exit lifecycle](#scripted-camera-exit-lifecycle)
- [In seat interfaces: interrupt before excluding input](#in-seat-interfaces-interrupt-before-excluding-input)
- [Loading screen hook contract](#loading-screen-hook-contract)

## Scripted camera exit lifecycle

Added 2026-08-31. Use this checklist for a spectator, CCTV, drone, thermal or other scripted camera. The failure usually shows on **exit**, after the feature itself looked finished.

1. **Reuse the engine camera.** Take `Camera.GetCurrentCamera()` (`P:\scripts\3_game\entities\camera.c:7`) and activate it. Do not create an unmanaged `staticcamera` object: compared with a working implementation that reuses the engine camera, that route could crash.
2. **Keep that camera active through `SelectPlayer`.** Deactivating it first leaves the engine with no active camera while the player is selected. Call `SetActive(false)` (`P:\scripts\3_game\entities\camera.c:45`) in the cleanup after the selection.
3. **Enable the `HumanInputController` again before `SelectPlayer`, not after it.** The restored third person camera reads that input in `UpdateUDAngleUnlocked` (called at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera3rdperson.c:54-55`). The symptom is specific: first person works, while third person stays pinned to the old camera transform and the player's actions are missing. `SetDisabled(bool pState)` is declared at `P:\scripts\3_game\human.c:22`.
4. **Do not use a continuous action's key as the exit key.** Use a separate key such as SPACE or ESC. Otherwise the action manager can keep an action in progress. The third person camera narrows the up and down look while an action runs and the player is not in free look: on 1.30 it takes the limits from `player.GetLookLimits(...)` every frame (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera_base.c:176-180`). On 1.29 the same file was read as blocking the look outright during such an action (1.29 is not on `P:\`); whether a running action still narrows the limits on 1.30 is decided inside `GetLookLimits` and is not yet checked.

How far each rule was verified:

- Rules 1 and 2 were checked against a working implementation in a shipped mod.
- Rules 3 and 4 were checked in the vanilla scripts and match the observed difference between first and third person, but each cause is not yet confirmed in game.
- `Input.ChangeGameFocus(+1)` and `(-1)` were also seen around entry and exit; their effect in this camera contract is unverified.
- "Vanilla never calls it" is not a reason to remove a mechanism that works. `HumanInputController.SetDisabled` has no callers under `P:\scripts` (a search for `.SetDisabled(` finds none on 1.30), yet removing it broke the working implementation.

## In seat interfaces: interrupt before excluding input

Added 2026-08-31. For an interface opened while the player is seated, `HumanInputController.SetDisabled(true)` does not by itself stop action input. When the interface shares a key with a seat action, one hold of that key can close the interface **and** complete the vanilla action underneath it.

- Add the mission input exclude you need (for example `{"menu"}`) on open, with `AddActiveInputExcludes` (`P:\scripts\3_game\gameplay.c:800`). Remove it on **every** exit path (`RemoveActiveInputExcludes`, `P:\scripts\3_game\gameplay.c:798`), guarded by a flag, so a half finished open cannot release an exclude that someone else owns.
- **Before you add an exclude, interrupt any continuous action already running** with `ActionManagerClient.RequestInterruptAction()` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:1341`). Excluding input first can hide the key release and leave the action manager "in progress" until the player logs in again.
- While the exclude is active, `UAInput.LocalValue()` reads zero. The raw `KeyState(KeyCode key)` (`P:\scripts\1_core\proto\ensystem.c:291`) and `GetMouseState` (`P:\scripts\1_core\proto\ensystem.c:326`) still read the hardware, but `KeyState` ignores the player's key bindings. Use it only as a rough fallback.

The command modification that lets a continuous action progress while seated, and the server owned state needed so players who join late see the vehicle correctly, are vehicle topics: see the vehicles pack (`skills/_shared/vehicles/`), not this skill.

## Loading screen hook contract

Added 2026-08-31. This replaces the timer and the hand written `.edds` in the first finding of `community-findings.md`.

- A loading screen mod hooks `LoadingScreen`, `LoginQueueBase` and `LoginTimeBase` with `modded class X` and **no `extends` clause**. `LoadingScreen` is a plain class, not a `UIScriptedMenu` (`P:\scripts\3_game\dayzgame.c:704`); `LoginQueueBase` (`:110`) and `LoginTimeBase` (`:213`) already inherit through `LoginScreenBase` (`:63`).
- Do not add a `Timer` only to rotate backgrounds. Add up `timeslice` in `LoadingScreen.OnUpdate(float timeslice)` (`P:\scripts\3_game\dayzgame.c:832`, called every loading frame at `:3034-3037`), and in the inherited `LoginScreenBase.Update(float timeslice)` (`:69`) for the queue and login time screens. Loading has no known total length, so rotate on a fixed period; do not try to split the duration.
- Use a `.paa` made by DayZ Tools `ImageToPAA.exe` (`/dayz-pack-texture`). Do not ship a hand written `.edds`. Decoding your file back is an inspection step, not proof that the engine will draw what your writer produced.
- Replacing the background does not reset the reveal mask. `LoadMaskTexture` and `SetMaskProgress` are `ImageWidget` calls (`P:\scripts\1_core\proto\enwidgets.c:282` and `:296`), and vanilla sets `m_ImageBackground.SetMaskProgress(0.0)` when the screen shows (`P:\scripts\3_game\dayzgame.c:854`). A black frame can be the vanilla mask at low progress, not a broken texture.
- For a diagnostic full reveal, `SetMaskProgress(1.0)` alone does not last, because `ProgressAsync` writes the value again every frame. Detach that updater with `ProgressAsync.SetUserData(null)` (`P:\scripts\3_game\progressasync.c:4`; vanilla attaches the background at `P:\scripts\3_game\dayzgame.c:774`), and only for the controlled diagnostic.
- Never apply a tone correction worked out from an offline model of the transfer function. Measure a known texture from an in game screenshot first.
