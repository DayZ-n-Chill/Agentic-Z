# Screenshots and cameras

How a picture of the running game is taken, which frames say nothing about the mod, what a scripted camera does to the player, how to pose a raised weapon for a capture, and how to measure UI pixels in a capture.

Vanilla facts cite the file on `P:\`. The rest was measured in game on DayZDiag 1.29 and 1.30 on Windows and is not checked on `P:\`. Brightness bands, hidden client windows and runs that never load their textures are in `window-capture-pitfalls.md`.

## Where the picture comes from

The vanilla `MakeScreenshot` (`P:\scripts\1_core\proto\proto.c:142`) does not work in the diag build: it creates the `ScreenShots` folder and never writes a file. So a capture is a grab of the rendered client window from outside the game, and `/dayz-gate visual` does the same.

| Grab | Behaviour |
|---|---|
| `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)` on the client's main window | Captures the 3D game area even when another window covers it and without taking focus, as long as the Windows session is unlocked and the display is on. |
| `CopyFromScreen` | Works only with the window in front. |

A covered DayZDiag window drops to about 20 FPS, so anything timed on the client depends on which window holds the foreground. Two captures that are byte for byte the same across different camera poses caught a stale frame, not the render. Judge a capture on a crop of the game area, not on the variance of the whole frame.

## Frames that say nothing about the mod

- Display asleep: the grab is black although the client runs. It is the Windows compositor, not the mod. Bring the client window to the front and send an input nudge (a mouse move, or the F15 key) before each grab.
- Locked Windows session: with `LogonUI` running, no window grab works, from any script. Check `Get-Process LogonUI` before you plan captures for an unattended run.
- Loading screen or pause menu. Wait 30 to 40 s for the scene to settle and capture again. The client can come up in the pause menu; Escape does not close it, but clicking its `continuebtn` button does.
- Everything flat, vanilla terrain and sky included: the client did not load its textures, so hold back any texture verdict (`window-capture-pitfalls.md`, "Runs that never load their textures").
- A test mission with an empty `main()` creates no player, so the client draws no world and the frame is black. The stock `dayzOffline.chernarusplus` creates the player and the world draws.

## The streamed world follows the player, not the camera

Place the object next to the player. A free camera more than 1 km from the player does not make the world stream there; it can photograph bare terrain while a server-side raycast confirms the object exists.

For repeatable captures, set the date to noon (the vanilla `SetDate` takes all five of year, month, day, hour and minute, `P:\scripts\3_game\global\world.c:46`) and full overcast: diffuse light removes the glint of direct sun that burns weapons and materials to white. Do not set the time multiplier to 0 while animations are pending, because it freezes the simulation. A top-down pose shows proxy alignment on a car clearly: the camera 16 m up and 3 m to one side, looking at the car's centre just above the ground.

For an item or weapon, judge proportions against a real-world reference, and look hardest at orientation and winding: that is where generated and imported meshes tend to fail.

## A scripted camera takes the player away

Installing a scripted camera from mission script usually goes with `PlayerControlDisable` (`P:\scripts\5_mission\mission\missiongameplay.c:886`), which takes control from the player, and a free camera that also calls `DisableSimulation(true)` stops the player's simulation. A camera of class `staticcamera` with the simulation left on keeps the world and the player running.

- A stopped player simulation never completes a vehicle get-in: the seat command hangs. Never use a free camera that stops the simulation between a capture and a drive.
- Giving control back needs `DisableSimulation(false)` and `PlayerControlEnable`, and it does not always take. When the render stays frozen or control does not return, reconnect (Escape, Disconnect, Reconnect), which recreates the player with a clean camera, or relaunch. Trying to restore in place only loses time.
- When the work passes from a scripted capture to a person's own test (driving, judging feel or looks), relaunch without the test camera code, or use a client that never had a scripted camera in that session.
- With the player seated in a vehicle, a scripted camera can report that it did not move and still show the requested outside view; check the frame itself. That is how a driver's pose can be checked from outside.

## A first-person vehicle HUD hides under a scripted camera

A HUD that shows only when `DayZPlayerCamera1stPersonVehicle.Cast(player.GetCurrentCamera())` succeeds (the class is at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`) hides under any scripted camera. That is correct HUD behaviour, not a bug. Capture it through the player's own view.

## Capturing a raised weapon

The captured character is the client's local player, so a raise forced in the server's `init.c` does not change what the client draws: the server log says raised and the capture shows the weapon lowered. Force the raise on the client, in a small test mod whose `CfgMods` class declares a `missionScriptModule` with `files[]={"MyMod/Scripts/5_Mission"}`. The `.c` file must be in the PBO: `/dayz-build-pbo` packs scripts through its include list (`troubleshooting.md`).

```c
// MyMod/Scripts/5_Mission/MyMod_RaiseWeapon.c
modded class MissionGameplay
{
	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);

		PlayerBase player = PlayerBase.Cast(g_Game.GetPlayer());
		if (!player)
			return;

		HumanInputController input = player.GetInputController();
		if (!input)
			return;

		// ENABLED stays on; ONE_FRAME drops back to idle
		input.OverrideRaise(HumanInputControllerOverrideType.ENABLED, true);
	}
}
```

| Call | What to know | Source |
|---|---|---|
| `OverrideRaise` | Declared on `HumanInputController`. The same override block forces movement speed and angle, aim change on X and Y, melee evade, the third person shoulder and free look, which is how to pose the player for a capture with no input. | `P:\scripts\3_game\human.c:268`; the block `:253` to `:274` |
| `HumanInputControllerOverrideType` | `ENABLED` is "Permenantly active until DISABLED is passed" (vanilla spelling); `ONE_FRAME` applies once. | `human.c:7` to `:12` |
| `IsRaised()` | The third person aim pose starts when `m_MovementState.IsRaised()` is true, so a sustained raise is enough. | `P:\scripts\4_world\entities\dayzplayerimplement.c:1742` |
| `SetIronsights()` | Do not call it: it forces the ironsight camera, which fights a scripted camera, and called on the server it left the weapon untextured. | `dayzplayerimplement.c:363` |
| `WeaponADS()` | An input flag with no override; it reads 0 even while aiming works. | `human.c:86` |

Read success from `IsRaised()` or the client log, not from `WeaponADS()`. Keep `OverrideRaise(ENABLED)` in the server's `init.c` too, so the server agrees. Judge the grip by eye at native resolution on a crop of one frame; the grip itself belongs to `_shared/animation/weapon-in-hands.md`.

## Measuring UI in a capture

Measured on one UI case:

- Asking the launcher for a resolution does not set the client viewport: 1280x720 was asked for and the real viewport was 846x461. Read the root widget's size, a proportional `size 1 1`, and trust it over the request.
- To sweep resolutions, call `SetWindowPos` from the host (user32, `SWP_NOZORDER`) on the live client window and reload the layout. The viewport is measured again at once and the scene is kept, so N resolutions cost N reloads, not N boots.
- On Windows 11 the window frame is 11 px left and right, 45 px of title bar and 11 px at the bottom. A full resolution grab maps 1:1 to the viewport: engine pixel = image pixel minus (11, 45).
- Widgets with the exact flags render at their declared size times (height / 1080), positions included. If a reference panel does not show exactly that factor, the calibration is wrong, not the layout.
- A widget tree read from script does not give a `TextWidget`'s visible text layout. Measure glyphs on the frame (full resolution, cropped, per pixel), and put a tag in each string so you can find it in the capture.
- `Print(variable)` prefixes the line with `string name = '...'`, and the client log cuts lines at 255 characters (the server log does not): print short expressions.
