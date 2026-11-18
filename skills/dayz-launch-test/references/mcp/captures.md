# Captures: how the frame is taken and when it lies

How `capture_screenshot` and `camera_set` behave, which frames say nothing about the mod (black, flat, stale, wrong camera), how to capture a raised weapon, and how to measure UI in a capture.

The verbs are dayz-mcp's; their behaviour and the measurements here are third-party, taken in game sessions with that tool, and not yet checked on `P:\`. Vanilla facts cite the vanilla file. `MCPBridge.c:NNN` lines are dayz-mcp's own source at the time of the measurement.

## Where the picture comes from

Control and data are engine-native and server-authoritative (spawn, raycast, telemetry, camera). The one piece that is not native is the picture: a grab of the rendered client window. The vanilla `MakeScreenshot` (`P:\scripts\1_core\proto\proto.c:142`) does not work in the diag build: in live runs it made the `ScreenShots` folder and never wrote a file. dayz-mcp and `/dayz-gate visual` therefore both grab the window from outside the game.

## How the window grab behaves

- `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)` on the client's main window does capture the D3D game area: the full scene in more than 20 captures, even with another window covering it and without taking focus, as long as the Windows session is unlocked and the display is on (measured in game, DayZDiag 1.29, 2026-09-28). A black game area means the display is off, not that the route cannot read D3D; a locked session makes the capture fail outright (see "Black frames" below).
- `CopyFromScreen` only works with the window in front.
- A covered DayZDiag window also drops to about 20 FPS, so anything timed on the client depends on who holds the foreground.
- Byte-identical captures between camera poses mean the grab caught a stale frame, not the render. Validate on a crop of the game area, not on the variance of the whole frame (this corrects an older rule of 2026-08-12).
- Each capture costs about 25,000 tokens of context at 240 to 320 pixels; batch them (`playbooks.md`, "The report").

## Black frames

- **Display asleep** (verified live 2026-07-11): capturing with the display asleep gives a black frame although the client runs. On that date a locked session also gave black frames. The fix used then was to bring the client window to the foreground and send an input wiggle (mouse, or the F15 key) before every `capture_screenshot`. The misleading symptom: it looks like "the mod's render is broken" and it is the compositor.
- **Locked Windows session**: with `LogonUI` alive, `capture_screenshot` does not return a black frame, it fails outright with `capture_backend_failed` on every attempt while the game client stays alive and polling. Before budgeting captures in an unattended run, run `Get-Process LogonUI`: with a locked session there is no host capture at all, for the MCP capture and for any window-grab script.

## Frames that say nothing about the model

- **Loading screen or menu overlay.** The grab sometimes catches the loading screen or the client's "Continue" menu instead of the render. Wait for the scene to settle (30 to 40 s, in the background if the harness blocks a foreground sleep) and capture again, from several angles. The client can come up in the pause menu: `ui_click` on `continuebtn` closes it, Escape does not (`actions-ui-and-inventory.md`).
- **Everything flat, vanilla terrain and sky included.** That is not a flaky grab of the model: withhold the texture verdict, check that the client window has focus and capture again after settling, since textured runs have opened with 4 to 11 s of flat frames. If the scene stays flat, its visual evidence is `SETUP_FAIL` and the run is relaunched. The measurements are in this skill's session findings (an import project of 2026-10).
- **A useful top-down pose** that shows proxy alignment or misalignment on a car clearly: `cam_pos=[carX+3, 16, carZ+1]`, `look_at=[carX, ground+0.1, carZ]`.

## The bubble follows the player, not the camera

- Before the spawn, read `query_player_state.pos` and place the object next to the player. A free camera more than 1 km away does not force streaming: it can photograph bare terrain even while the server confirms the object by raycast.
- After several `camera_set` calls, treat any series of identical frames from different positions as an orphan camera. There is no `camera_release`; restart or reconnect the client before diagnosing the asset.

## `camera_set` takes the player's controls away, and `restore_gameplay` does not always give them back

`camera_set` always suppresses player control (`SuppressGameplay()` in the bridge, which calls the mission's `PlayerControlDisable`, vanilla `P:\scripts\5_mission\mission\missiongameplay.c:886`). The `restore_gameplay` lifecycle verb asks the client to release the scripted camera and give control back; the `drive_probe_client` gate also does it internally. The verb has limits: it can answer `restore_unverified`, and when `camera_set` has left the client render frozen it never reaches green (`skills/_shared/vehicles/test-stand-and-mcp.md`). Not yet checked on P:\: the bridge source is not part of the vanilla data. After an MCP smoke test that used `camera_set` (free camera or a static look-at camera), do not assume the user can take control of the player to test by hand.

Rule: when the work passes from an MCP smoke test to a manual test by the user (driving, judging feel or looks), relaunch the game without `@DayZ_MCP`, or at least with a client that never received `camera_set` in that session. A clean client has normal control. If the client was already affected, send `restore_gameplay` and confirm the render is alive with `distinct_frames` in `capture_screenshot`; if it answers `restore_unverified` or the frames do not change, reconnect (Escape, Disconnect, Reconnect), which recreates the player with a clean camera and control, or relaunch. Seen in a car project session where time was lost trying to restore control in place, and the user had to close the game and ask for a normal relaunch.

## A HUD gated on the first-person vehicle camera cannot be photographed with `camera_set`

`camera_set` installs a scripted camera. A HUD that shows only when `DayZPlayerCamera1stPersonVehicle.Cast(player.GetCurrentCamera())` succeeds (the class is at `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:4`) hides under that camera. That is correct HUD behaviour, not a bug of the HUD or of the bridge. Capture it through the user's manual free look or through a headless mode the mod provides. There is no `camera_release`; the `restore_gameplay` verb is the way to ask for the player camera back, and if it answers `restore_unverified`, reconnect or relaunch as in the section above.

## Capturing a raised weapon

Verified on a rifle project's grip gate. There is no player input tool, so the weapon raise is forced inside a mod, on the client. The captured character is the client's local player, so an override in the server's `init.c` does not change the pose the client renders. The exact symptom of doing it server-side only: the server log says `raised=1` and the capture shows the weapon lowered.

Put a `modded class MissionGameplay` in a small gate mod (its `CfgMods` class declares a `missionScriptModule` with `files[]={"Mod/Scripts/5_Mission"}`). The `.c` file must be in the PBO: `/dayz-build-pbo` packs scripts through its include list, and a direct AddonBuilder build needs `-packonly` for the same reason (this skill's `../troubleshooting.md`).

```c
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

		// ENABLED stays on; ONE_FRAME flickers back to idle
		input.OverrideRaise(HumanInputControllerOverrideType.ENABLED, true);
	}
}
```

- `OverrideRaise` is declared at `P:\scripts\3_game\human.c:268`; `HumanInputControllerOverrideType.ENABLED` is "active until DISABLED is passed" and `ONE_FRAME` applies once (`P:\scripts\3_game\human.c:7-12`).
- The third-person aim pose depends only on `IsRaised()`: the aiming model starts when `m_MovementState.IsRaised()` is true (`P:\scripts\4_world\entities\dayzplayerimplement.c:1742`). A sustained raise is enough. Do not call `SetIronsights()` (`P:\scripts\4_world\entities\dayzplayerimplement.c:363`): it forces the ironsight camera, which fights the MCP free camera, and called on the server it left the weapon untextured.
- `WeaponADS()` (`P:\scripts\3_game\human.c:86`) is an input flag with no script override: the override block of `HumanInputController` (`P:\scripts\3_game\human.c:253-274`) has no entry for it. So it reads 0 even when aiming works. The success signal is `IsRaised()` or the client log, not `WeaponADS()`.
- Keep `OverrideRaise(ENABLED)` on the server too (in `init.c`) so the server agrees.
- Judge the grip by hand at native resolution (crop a frame of the orbit), never on a rescaled contact sheet. The grip mechanism and its geometric check belong to the dayz-animation-pipeline skill (weapon in hands).

## UI in a capture: resolution sweep without a reboot, and pixel calibration

Measured on one UI case (run dbca698d):

- The `width` and `height` of `dayz_test_run` do not set the client resolution (1280x720 was requested, the real viewport was 846x461). Do not spend a reboot on changing resolution.
- Validated technique: `SetWindowPos` from the host (user32, `SWP_NOZORDER`) on the live client window, then `ui_reload_layout`. The viewport measures again at once, and the scenario and the run are kept. A sweep of N resolutions costs N reloads, not N boots.
- Measured window frame on Windows 11: outer size minus client size is 11 px left and right, 45 px of title, 11 px at the bottom. A full-resolution `capture_screenshot` is 1:1 with the viewport: `engine_px = image_px - (11, 45)`.
- The root of `ui_tree` with a proportional `size 1 1` is the real viewport. Use it as the resolution oracle instead of trusting the launch request.
- Factor control: widgets with exact flags render at the declared size times (height / 1080), positions included. If the reference panel does not give exactly that factor, the calibration is wrong, not the layout.
- A `TextWidget` does not expose its text through `ui_tree` (`text_readable=false` by contract). To measure glyphs the instrument is the frame (full resolution, crop, per-pixel measurement), never the tree. Put a tag inside each string so the case can be recognised in the capture.
