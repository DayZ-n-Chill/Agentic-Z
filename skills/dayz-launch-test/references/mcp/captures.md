# Screen captures

How `capture_screenshot` and `camera_set` take a frame, which frames say nothing about the mod, how to photograph a raised weapon, and how to measure UI pixels in a capture.

The verbs belong to the third-party dayz-mcp tool. What they do was measured in game with it and is not checked on `P:\`; `MCPBridge.c` lines are dayz-mcp's own source. Vanilla facts cite the vanilla file.

## Where the picture comes from

Spawning, rays, telemetry and the camera all run inside the game. The picture does not: it is a grab of the rendered client window from outside the game. The vanilla `MakeScreenshot` (`P:\scripts\1_core\proto\proto.c:142`) does not work in the diag build; it creates the `ScreenShots` folder and never writes a file. So dayz-mcp and `/dayz-gate visual` both grab the window.

| Grab | Behaviour |
|---|---|
| `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)` on the client's main window | Captures the 3D game area even when another window covers it and without taking focus, as long as the Windows session is unlocked and the display is on. |
| `CopyFromScreen` | Works only with the window in front. |

A covered DayZDiag window drops to about 20 FPS, so anything timed on the client depends on which window holds the foreground.

Two captures that are byte for byte the same across different camera poses caught a stale frame, not the render. Judge a capture on a crop of the game area, not on the variance of the whole frame.

Each capture costs about 25,000 tokens of context at 240 to 320 pixels. Batch them (`playbooks.md`, section "The report").

## Black frames

- Display asleep: the capture is black although the client runs. It looks like a broken mod render and is the Windows compositor. Bring the client window to the front and send an input nudge (a mouse move, or the F15 key) before every `capture_screenshot`.
- Locked Windows session: with `LogonUI` running, `capture_screenshot` fails with `capture_backend_failed` on every attempt while the client stays alive and polling. No window grab works then, from dayz-mcp or from any script. Before you plan captures for an unattended run, check `Get-Process LogonUI`.

## Frames that say nothing about the model

- Loading screen or menu. The grab can catch the loading screen or the client's pause menu instead of the world. Wait 30 to 40 s for the scene to settle and capture again from several angles. If the client comes up in the pause menu, `ui_click` on `continuebtn` closes it; Escape does not (`actions-ui-and-inventory.md`).
- Everything flat, vanilla terrain and sky included. The client did not load its textures, so hold back any texture verdict. Check that the client window has focus and capture again after the scene settles; textured runs can open with 4 to 11 s of flat frames. If the scene stays flat, the run's visual evidence is `SETUP_FAIL`: relaunch. The detail is in `../window-capture-pitfalls.md`, section "Runs that never load their textures".

A top-down pose shows proxy alignment on a car clearly: `cam_pos=[carX+3, 16, carZ+1]`, `look_at=[carX, ground+0.1, carZ]`.

## The streamed world follows the player, not the camera

- Before you spawn, read `query_player_state.pos` and place the object next to the player. A free camera more than 1 km away does not make the world stream there; it can photograph bare terrain while a raycast on the server confirms the object exists.
- After several `camera_set` calls, a series of identical frames from different positions means the camera is orphaned. There is no `camera_release`; restart or reconnect the client before you blame the asset.

## Giving the player back after `camera_set`

`camera_set` always takes control away from the player: the bridge calls the mission's `PlayerControlDisable` (vanilla `P:\scripts\5_mission\mission\missiongameplay.c:886`). The `restore_gameplay` verb asks the client to release the scripted camera and give control back, and the `drive_probe_client` check does the same internally. It can answer `restore_unverified`, and when `camera_set` has frozen the client render it never succeeds (`_shared/vehicles/test-stand-and-mcp.md`).

So after an MCP check that used `camera_set`, do not assume the user can take over the player to test by hand.

- When the work passes from an MCP check to a manual test (driving, judging feel or looks), relaunch the game without `@DayZ_MCP`, or use a client that never received `camera_set` in that session. A clean client has normal control.
- If the client is already affected, send `restore_gameplay` and confirm the render is alive with `distinct_frames` in `capture_screenshot`. If it answers `restore_unverified` or the frames do not change, reconnect (Escape, Disconnect, Reconnect), which recreates the player with a clean camera, or relaunch. Trying to restore control in place only loses time.

## A first-person vehicle HUD cannot be photographed with `camera_set`

`camera_set` installs a scripted camera. A HUD that shows only when `DayZPlayerCamera1stPersonVehicle.Cast(player.GetCurrentCamera())` succeeds (the class is at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`) hides under it. That is correct HUD behaviour, not a bug in the HUD or the bridge. Capture it through the user's own view, or through a headless mode the mod provides. To get the player camera back, use `restore_gameplay` as above.

## Capturing a raised weapon

There is no player input verb, so force the raise inside a mod, on the client. The captured character is the client's local player, so an override in the server's `init.c` does not change what the client draws: the server log says `raised=1` and the capture shows the weapon lowered.

Put a `modded class MissionGameplay` in a small test mod whose `CfgMods` class declares a `missionScriptModule` with `files[]={"MyMod/Scripts/5_Mission"}`. The `.c` file must be in the PBO: `/dayz-build-pbo` packs scripts through its include list, and a direct AddonBuilder build needs `-packonly` for the same reason (`../troubleshooting.md`).

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
| `OverrideRaise` | Declared on `HumanInputController`. | `P:\scripts\3_game\human.c:268` |
| `HumanInputControllerOverrideType` | `ENABLED` is "Permenantly active until DISABLED is passed" (vanilla spelling); `ONE_FRAME` applies once. | `human.c:7` to `:12` |
| `IsRaised()` | The third person aim pose starts when `m_MovementState.IsRaised()` is true, so a sustained raise is enough. | `P:\scripts\4_world\entities\dayzplayerimplement.c:1742` |
| `SetIronsights()` | Do not call it: it forces the ironsight camera, which fights the free camera, and called on the server it left the weapon untextured. | `dayzplayerimplement.c:363` |
| `WeaponADS()` | An input flag with no script override; the override block of `HumanInputController` has no entry for it, so it reads 0 even while aiming works. | `human.c:86`; `:253` to `:274` |

Read success from `IsRaised()` or the client log, not from `WeaponADS()`. Keep `OverrideRaise(ENABLED)` in the server's `init.c` too, so the server agrees.

Judge the grip by eye at native resolution on a crop of one frame, never on a rescaled contact sheet. The grip itself and its geometric check belong to the `dayz-animation-pipeline` skill (weapon in hands).

## Measuring UI in a capture

Measured on one UI case:

- The `width` and `height` of `dayz_test_run` do not set the client resolution: 1280x720 was asked for and the real viewport was 846x461. Do not spend a reboot on changing resolution.
- To sweep resolutions, call `SetWindowPos` from the host (user32, `SWP_NOZORDER`) on the live client window, then `ui_reload_layout`. The viewport is measured again at once and the scene and run are kept, so N resolutions cost N reloads, not N boots.
- On Windows 11 the window frame is 11 px left and right, 45 px of title bar and 11 px at the bottom. A full resolution `capture_screenshot` maps 1:1 to the viewport: `engine_px = image_px - (11, 45)`.
- The root of `ui_tree` with a proportional `size 1 1` is the real viewport. Trust it over the launch request.
- Widgets with the exact flags render at their declared size times (height / 1080), positions included. If a reference panel does not show exactly that factor, the calibration is wrong, not the layout.
- `ui_tree` does not expose a `TextWidget`'s text (`text_readable=false`). Measure glyphs on the frame (full resolution, cropped, per pixel), and put a tag in each string so you can find it in the capture.
