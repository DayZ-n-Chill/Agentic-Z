# DayZ 1.30 — launch / session-test deltas

Companion to the rules in `../SKILL.md` ("Rules that hold on every route"). Diag-only managed lifecycle, absolute
`-mod` paths, and the filepatching-vs-PBO caveats still hold. This file is the
1.30 launch-flag and action-injection delta.

Script line numbers cite the vanilla scripts unpacked on `P:\scripts\` and were re-opened there for
this file. Quoted changelog lines come from the DayZ 1.30 Experimental modding changelog. Runtime behaviour
of the new exe flags is [CHANGELOG] / [UNVERIFIED]: it was read from the changelog, not measured with a
1.30 DayZ Tools binary. Measurements made with the third-party dayz-mcp tooling, and readings of the 1.29
scripts (1.29 is not unpacked on `P:\`), are not yet checked on `P:\`.

## Unpacked `-mod` folder (configs without packing)

(until 1.29: this skill's loop was "re-pack the PBO, deploy it where the
engine reads mods, and launch DayZDiag".) (since 1.30 [CHANGELOG], the 1.30 Experimental modding changelog):

> Changed: Mods now have their own named filesystem
> Changed: Improved unpacked mod workflow; -mod can now point to a physical folder
> Changed: RV configs can now be read when loaded as an unpacked mod

[DESIGN] For **config.cpp / script** iteration, `-mod` may name the addon
**source folder** (still prefer absolute paths; the silent-no-mount gotcha of
bare `@Name` is unchanged). `.p3d` / `.paa` still follow the existing
filepatching-does-not-reload-binaries rule. A shipping test still packs.

[EXACT] Measured bound of that [DESIGN] (dedicated server, 1.30.164014 Exp, 2026-09-27): an unpacked `-mod` folder mounts as a `relative directory` (RPT: `Adding relative directory ...` vs a PBO's `Adding package ... (pbo count: N)`); with a `CfgMods` block it injects the mod's define into the script modules and loads its scripts, but it does NOT merge its `config.cpp` into the runtime config tree — `ConfigIsExisting("CfgPatches <mod>")` stays false. World configs (`CfgWorlds` terrain `Holes`) therefore require a PACKED PBO: unpacked, `SurfaceIsHole` stays false and the RPT logs `No entry 'config.bin/CfgWorlds/<world>.Holes'`; the same PBO mounted and measured true when packed (the PBO may carry `config.cpp` as text, no binarize needed). Measured in game, DayZ 1.30.164014 Exp.

## New launch flags

(since 1.30 [CHANGELOG], the 1.30 Experimental modding changelog):

> Added: '-resolveFilePatchingUsingEnfusion=0/1' for file patching to
> prioritize looking through named enfusion filesystems before checking
> launched directory (requires -filepatching, always enabled in Workbench)
> Added: '-cacheP3D=0/1' command line launch option, creates .p3dcache files
> next to .p3d files to allow for quicker subsequent launches of the
> Game/Buldozer when working with unbinarized assets

[DESIGN] Append to Diag argv when iterating unpacked / MLOD assets, for
example:

`-filePatching -resolveFilePatchingUsingEnfusion=1 -cacheP3D=1`

Requires `-filePatching`. Workbench always enables the resolve flag.
`.p3dcache` siblings are local caches — do not commit them as product.

## Headless roboclients vs `Mode=all`

(since 1.30) `CGame.IsHeadless()` and `IsHeadlessOrDedicatedServer()`
(`P:\scripts\3_game\global\game.c:1130`, `:1136`) —
see `skills/dayz-mod-workflow/references/dayz-1-30-mod-workflow.md`. This skill's
MCP composition still requires `-Mode all` for a **rendered** client
(`dayz-mcp-verify`: headless has no window to grab).

[DESIGN] A load-test roboclient is `IsHeadless()==true` and must not be used
as the capture peer. Script that skips VFX should use
`IsHeadlessOrDedicatedServer()` so roboclients match dedicated.

`IsHeadless` is absent from the 1.29 `3_Game\Global\Game.c` (a 1.29 reading, not yet checked on `P:\`).

Measured 2026-09-26 on build 1.30.164014: the headless client (`-headlessMode=1`)
crashes before loading `World`, so there is no headless load-test roboclient in
this build yet. Server-side dummy bots do the job instead; details and numbers in
`skills/dayz-mcp-verify/references/dayz-1-30-mcp-verify.md` § Roboclients vs server-side
dummy bots.

## Launching the 1.30 DayZDiag directly (outside the managed lifecycle)

On 2026-09-26 the managed launcher still ran the 1.29 install (managed runs on
1.30.164200 are recorded from 2026-10-26 in
`skills/dayz-mcp-verify/references/dayz-1-30-mcp-verify.md`). Probing the Exp install by hand
on that date (measured with the dayz-mcp tooling)
hit six traps, each costing a run:

1. **The script log is the define oracle.** Each module logs
   `Module: <name>; …; defines: "…"`. Reading that line after a launch to the main
   menu (~20 s) answers "is X defined in this exe?" without writing a probe mod.
   It also shows the version define, `DAYZ_1_30`.
2. **From the Claude desktop app the game can read a dead Steam PID.** The app sees a
   private, frozen copy of `HKCU\Software\Valve\Steam\ActiveProcess` (MSIX registry
   virtualization). After Steam restarts, a game launched from the app reads a
   dead PID, logs `Unable to locate a running instance of Steam` and shows an error
   dialog while `steam.exe` runs. Compare the app's view with the real value (WMI
   `StdRegProv`) and the live `steam.exe`; then launch through WMI
   (`Win32_Process.Create`) or sync the copy right before launching. Writing the
   value from a shell inside the app only fixes the private copy, and only until the
   next Steam restart.
   Two measured corollaries (2026-09-23/24). Never START or restart Steam from a shell inside the sandboxed app: the new Steam registers in the private copy, and the REAL key can be left at `pid = 0, ActiveUser = 0` — a state the outside WMI check reports as broken while the app's own view looks healthy, and which `auto_remediate_steam` cannot fix because the worker sits inside the app too. Never write or delete another app's HKCU keys from an app shell: a write creates the private copy (shadow), a delete leaves a tombstone that hides the real key even after it is rewritten outside; the shadow only disappears with the app closed and the hive loaded offline. Preflight BOTH views: WMI `StdRegProv` reads the real hive, `Get-ItemProperty` inside the app reads the copy the launched client will see — require both to point at the live `steam.exe`. [EXACT] (measured)
3. **A very long `-profiles=` path is a crash suspect.** A ~245-character profiles
   path ended in `0xC0000005` after 1 s with no log written; a short path did not
   repeat it. Steam was broken at the same time, so the cause is probable, not
   isolated. Keep profiles paths short.
4. **Launch DayZ with a whitelisted environment.** A DayZ `ErrorMessage_*.mdmp` or
   crash minidump embeds the parent's whole environment block, and an agent shell
   usually carries API keys and passwords. On every crash the DayZ CrashReporter
   also sends "analytical data" before offering the dump. Start DayZ with
   `ProcessStartInfo.UseShellExecute = $false` and remove every variable not on a
   short whitelist (`SystemRoot`, `Path`, `TEMP`, `USERPROFILE`, `APPDATA`,
   `LOCALAPPDATA`, `ProgramFiles*`, processor/OS variables, `ComSpec`), and delete
   dumps you do not need.
5. **Own the PID.** Out-of-lifecycle probes start and stop only the process they
   launched, and hold the MCP lease while they run so no managed run lands on top.
6. **Use a fresh `-profiles=` directory per run.** A readiness check that greps the
   newest `script_*.log` found a log left by an earlier run in the same directory.
   It reported the server ready and the client connected at +0 s (2026-09-26): the
   run looked healthy and measured nothing. A client that never loads its textures fools a visual check the same way (`session-findings.md`, the section on untextured runs and a moving 1PP eye).

## Measuring server load

What worked on 2026-09-26 (dummy-bot load, same measurement session):

- **Cap the server.** Uncapped, the Diag server ran at ~1958 FPS and FPS was no load
  signal (10 moving dummies: 1900; 25 idle: 1908). `-limitFPS=60` (the 1.30 exe
  carries a `limitfps` switch) turns frame drops into the saturation point and makes
  process CPU per window comparable across load steps.
- **Meter frames inside the server.** Count `timeslice` in an `override void OnUpdate(float timeslice)`
  of the server mission (`P:\scripts\5_mission\mission\missionserver.c:108`) and log per
  window: frames, seconds, FPS, max frame time. Sample the process
  `TotalProcessorTime` every second from outside and join by timestamp.
- **Bracket the run with baselines, and do not trust a fixed warm-up.** The first three
  windows of run 2 (a fresh storage) ran at 36-84 % machine CPU. In run 3 a 120 s
  warm-up was not enough either: its first baseline used 0.276 server cores, against
  0.001 at the baseline taken after deleting all load. Record a baseline at both ends,
  and treat a large mismatch as an inconclusive comparison.
- **Check post-spawn idle windows.** After 15 s settles in run 2, the idle window right
  after spawning 25 dummies used 0.201 server cores against 0.010 in the moving window
  after it, with the machine nearly idle (3.8 % CPU). At 50 dummies the gap was 0.179
  against 0.032 cores, but machine CPU was 49.2 % during that idle window. The cause
  was not isolated. Run 3 used 45 s settles and its idle windows after spawning 50 and
  100 averaged 60.0 FPS; that does not make 45 s a validated settle time for CPU.
- **Keep the CPU sampler cheap, and check it for gaps.** In run 3 the 1 s sampler went
  58.7 s without a sample across a spawn. Its loop also ran a WMI machine-CPU query and
  a script-log scan every 5 s; the cause was not isolated. The gap crossed two windows,
  which kept only 32 and 43 of their 45 s sampled. An analyzer that takes the nearest
  samples around a window then mixes stages into its CPU delta. Use the samples inside
  the window, report how much of it they cover, and drop the window when coverage is
  short. The in-server FPS meter was unaffected.
- **Write CSV numbers with the invariant culture.** On an es-ES host,
  `'{0:F3}' -f` writes decimal commas and silently splits every CSV row into
  extra columns. Use `[string]::Format([Globalization.CultureInfo]::InvariantCulture, …)`.

## `PerformActionStart` in SP — pending guard + `UA_AM_INIT`

(until 1.29: this skill cited `actionmanagerclient.c:762`.) (since 1.30:
the method is at `:804`. Singleplayer no longer overwrites an in-flight
pending/current action.)

```
// [EXACT] P:\scripts\4_world\classes\useractionscomponent\actionmanagerclient.c:804-828
	void PerformActionStart(ActionBase action, ActionTarget target, ItemBase item, Param extra_data = NULL)
	{
		if (!g_Game.IsMultiplayer())
		{
			if (!m_PendingActionData && !m_CurrentActionData)
			{
				m_PendingActionData = new ActionData;
	
				if (!action.SetupAction(m_Player, target, item, m_PendingActionData, extra_data))
					m_PendingActionData = null;
			}
		}
		else
		{
			ActionStart(action, target, item, extra_data);
		}
	}
	
	override int GetActionState()
	{
		if (m_PendingActionData)
			return UA_AM_INIT;
		
		return super.GetActionState();
	}
```

1.29 contrast: line `:762` of the same file was the old `PerformActionStart` line (a 1.29 reading, not yet
checked on `P:\`).

`UA_AM_INIT = 14` was inserted; later `UA_AM_*` values shifted:

```
// [EXACT] P:\scripts\3_game\constants.c:506-511
	const int 		UA_INITIALIZE = 12;
	const int		UA_CHECK_CON = 13;
	const int		UA_AM_INIT = 14;
	const int		UA_AM_PENDING = 15;
	const int		UA_AM_ACCEPTED = 16;
	const int		UA_AM_REJECTED = 17;
```

[DESIGN] Autotest that injects a second `PerformActionStart` in SP without
waiting for idle will silently no-op. Wait until `GetActionState()` is not
`UA_AM_INIT` / not pending. Never hardcode the integer `14` — use the
constant.

MP path is unchanged: `PerformActionStart` still calls `ActionStart` directly
(`:816-819`).

## Navmesh / Tools (session awareness)

Custom terrains: regenerate `.nm` (no backwards compatibility, per the 1.30
changelog). Workbench 1.30 was not available when this was written; treat Tools
UI claims as [CHANGELOG].
