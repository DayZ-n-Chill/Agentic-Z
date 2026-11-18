# Scripted cameras, seat interfaces and the loading screen

How to leave a scripted camera cleanly, how to open an interface while the player sits in a vehicle, and how to hook the loading screen. All three look finished and then fail on exit or on the next login.

## Leaving a scripted camera

Follow these four rules for a spectator, CCTV, drone, thermal or any other scripted camera. The failure usually shows when the player leaves the camera.

1. Reuse the engine camera. Take `Camera.GetCurrentCamera()` (`P:\scripts\3_game\entities\camera.c:7`) and activate it. Don't create an unmanaged `staticcamera` object; a shipped mod that reuses the engine camera works where that route can crash.
2. Keep that camera active through `SelectPlayer`. Turning it off first leaves the engine with no active camera while the player is selected. Call `SetActive(false)` (`camera.c:45`) in the cleanup after the selection.
3. Enable the `HumanInputController` again before `SelectPlayer`, not after. The restored third person camera reads that input in `UpdateUDAngleUnlocked` (called at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera3rdperson.c:54` and `:55`). Get it wrong and first person works while third person stays pinned to the old camera and the player's actions are missing. `SetDisabled(bool pState)` is at `P:\scripts\3_game\human.c:22`.
4. Don't use a continuous action's key to leave. Use a separate key such as Space or Esc, or the action manager can keep an action running. While an action runs and the player is not in free look, the third person camera takes its up and down limits from `player.GetLookLimits(...)` every frame (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercamera_base.c:152` to `:156`).

Rules 1 and 2 match a working shipped mod. Rules 3 and 4 follow from the vanilla scripts and match the difference seen between first and third person, but each cause is not confirmed in game. Whether a running action still narrows the look limits on 1.30 is decided inside `GetLookLimits` and is not checked. `Input.ChangeGameFocus(+1)` and `(-1)` also show up around entry and exit in camera mods; their effect here is unverified.

`HumanInputController.SetDisabled` has no callers under `P:\scripts` (a search for `.SetDisabled(` finds none), yet the working mod breaks without it. Vanilla not calling something is no reason to remove it from a mechanism that works.

## Interfaces opened from a seat

For an interface opened while the player is seated, `HumanInputController.SetDisabled(true)` does not stop action input on its own. When the interface shares a key with a seat action, one hold of that key can close the interface and complete the vanilla action underneath it.

- Before you add an input exclude, interrupt any continuous action already running with `ActionManagerClient.RequestInterruptAction()` (`P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:1341`). Excluding input first can hide the key release and leave the action manager stuck in progress until the player logs in again.
- Add the exclude you need (for example `{"menu"}`) on open with `AddActiveInputExcludes` (`P:\scripts\3_game\gameplay.c:800`). Remove it on every exit path with `RemoveActiveInputExcludes` (`gameplay.c:798`), guarded by a flag, so a half finished open never releases an exclude someone else owns.
- While the exclude is active, `UAInput.LocalValue()` reads zero. The raw `KeyState(KeyCode key)` (`P:\scripts\1_core\proto\ensystem.c:291`) and `GetMouseState` (`ensystem.c:326`) still read the hardware, but `KeyState` ignores the player's key bindings, so use it only as a rough fallback.

Letting a continuous action progress while seated, and the server state that makes late joiners see the vehicle right, are vehicle topics: see `_shared/vehicles/`.

## Loading screen classes

Four classes can be hooked, all in `P:\scripts\3_game\dayzgame.c`:

| Class | Base | Line |
|---|---|---|
| `LoginScreenBase` | `UIScriptedMenu` | `:63` |
| `LoginQueueBase` | `LoginScreenBase` | `:110` |
| `LoginTimeBase` | `LoginScreenBase` | `:213` |
| `LoadingScreen` | none; a plain class that owns `m_WidgetRoot` | `:704` |

Hook each with `modded class X { ... }` and no `extends` clause. `modded class LoginQueueBase extends UIScriptedMenu` is wrong syntax; the chain already runs through `LoginScreenBase`.

`LoadingScreen` declares its widgets at `dayzgame.c:706` to `:724` and fills them with `m_WidgetRoot.FindAnyWidget` in the constructor (`:729` to `:743`):

| Field | Type | Widget name |
|---|---|---|
| `m_ImageWidgetBackground`, `m_ImageBackground` | `ImageWidget` | `ImageBackground` (both point at it) |
| `m_ImageLogoMid` | `ImageWidget` | `ImageLogoMid` |
| `m_ImageLogoCorner` | `ImageWidget` | `ImageLogoCorner` |
| `m_ImageLoadingIcon` | `ImageWidget` | `ImageLoadingIcon` |
| `m_ProgressLoading` | `ProgressBarWidget` | `LoadingBar` |
| `m_TextWidgetTitle` | `TextWidget` | `TextWidget` |
| `m_TextWidgetStatus` | `TextWidget` | `StatusText` |
| `m_ModdedWarning` | `TextWidget` | `ModdedWarning` |

## Rotating the background

Don't add a `Timer` just to rotate backgrounds. Add up `timeslice` in `LoadingScreen.OnUpdate(float timeslice)` (`dayzgame.c:832`, called every loading frame from `:3034` to `:3037`) and, for the queue and login time screens, in the inherited `LoginScreenBase.Update(float timeslice)` (`:69`). Loading has no known total length, so rotate on a fixed period. `Show()` (`:848`) is the place to pick the first image:

```c
modded class LoadingScreen
{
    protected ref TStringArray m_MyMod_Images = { "MyMod/data/loading_01.paa", "MyMod/data/loading_02.paa" };
    protected int m_MyMod_Index;
    protected float m_MyMod_Elapsed;

    override void Show()
    {
        m_MyMod_Index = Math.RandomInt(0, m_MyMod_Images.Count());
        m_ImageWidgetBackground.LoadImageFile(0, m_MyMod_Images[m_MyMod_Index]);
        m_ImageLogoMid.Show(false);
        m_ImageLogoCorner.Show(false);
        m_ModdedWarning.Show(false);
        super.Show();
    }

    override void OnUpdate(float timeslice)
    {
        super.OnUpdate(timeslice);
        m_MyMod_Elapsed += timeslice;
        if (m_MyMod_Elapsed < 15.0)
            return;
        m_MyMod_Elapsed = 0;
        m_MyMod_Index = (m_MyMod_Index + 1) % m_MyMod_Images.Count();
        m_ImageWidgetBackground.LoadImageFile(0, m_MyMod_Images[m_MyMod_Index]);
    }
}
```

The class names, fields and widget names are checked on `P:\`; the override itself is not tested in game.

- Make the `.paa` with DayZ Tools `ImageToPAA.exe` (`/dayz-pack-texture`). Don't ship a hand written `.edds`; decoding your own file back proves nothing about what the engine draws.
- `LoadImageFile(0, path)` takes a `.paa` or `.edds` path or the imageset form `"set:NAME image:NAME"` (for the set name trap see `imagesets-draw-order-progress-bars.md`). Not checked in game.
- Whether the layout itself can be swapped from `Show()` is not checked in game.

## The reveal mask

A new background keeps the vanilla reveal mask. `LoadMaskTexture` and `SetMaskProgress` are `ImageWidget` calls (`P:\scripts\1_core\proto\enwidgets.c:282` and `:296`), and vanilla calls `m_ImageBackground.SetMaskProgress(0.0)` when the screen shows (`dayzgame.c:854`). A black frame can be the mask at low progress, not a broken texture. Passing `""` to `LoadMaskTexture` is said to remove the mask; not checked in game.

For a diagnostic full reveal, `SetMaskProgress(1.0)` alone doesn't last, because `ProgressAsync` writes the value again every frame. Detach it with `ProgressAsync.SetUserData(null)` (`P:\scripts\3_game\progressasync.c:4`; vanilla attaches the background at `dayzgame.c:774`), and only for that diagnostic.

Never apply a tone correction worked out from an offline model. Measure a known texture in an in game screenshot first.
