# When the client will not start

How to tell an environment failure from a mod failure when a DayZ client or build dies before it writes a useful log: the work drive missing after a reboot, a Steam registry key that points at a dead process, the wrong Steam account, quoting, and a diag that never writes logs.

These are measured results from one Windows test machine. None is a vanilla script fact, so none is checked on `P:\`. The symptom table for sessions that do start is in `troubleshooting.md`.

## After a reboot `P:` is gone, and FileBank packs nothing with exit 0

`P:` is a `subst`, not a disk link: it does not survive a reboot, let alone a hard crash. Everything the Bohemia tools and the launcher touch hangs off it (`P:\Mods`, `P:\<Mod>`, `P:\<Mod>_dev\_server\profiles`, `P:\scripts`, `P:\DZ`).

The costly part is how it fails. With `P:` missing:

```text
FileBank.exe -property prefix=<Mod> -exclude <lst> -dst <staging> P:\<Mod>
exit=0
<staging>\<Mod>.pbo is 79 bytes
```

Exit 0, a 79-byte PBO and not a single message, the same failure as AddonBuilder's `Build failed` with exit 0: the tool counts packing zero files as success.

Check it before any build or launch:

```powershell
Test-Path -LiteralPath "P:\"          # if False:
subst P: "<work-drive-folder>"        # in this repo: /dayz-workdrive
```

Check the anchors too, not just the root: `P:\<Mod>\config.cpp`, `P:\Mods\@<Mod>\Addons`, `P:\scripts`, `P:\DZ`. Validate the PBO by size and entry count before you publish; a package of a few hundred bytes is this failure.

## The Steam pid in the registry can be dead

The launch prerequisites ask that `HKCU\Software\Valve\Steam\ActiveProcess` has `pid != 0` and `ActiveUser != 0`. That is necessary but not enough: after a hard crash the key keeps the old Steam pid, Steam starts again with another pid and does not always rewrite the key in time. DayZ reads the pid, looks for the process, does not find it, and dies. With the registry at one pid and the running `steam.exe` at another, the "not zero" check passed on a broken system. Ask whether that process exists:

```powershell
$k  = Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess'
$st = Get-Process -Name steam -ErrorAction SilentlyContinue
$ok = $st -and ($st.Id -contains [int]$k.pid) -and $k.ActiveUser -ne 0
```

The failure looked the same three times:

| Signal | Value |
|---|---|
| Modal dialog | `unable to locate running instance of Steam` |
| Dump exception | `0x80000003` (breakpoint), same address each time |
| Client CPU | 0 s: alive but stopped |
| Client RPT | Frozen at 847 B, header only |
| Loaded modules | About 69, the last ones Steam's (`gameoverlayrenderer64.dll`, `tier0_s64.dll`) |

`0x80000003` is not a crash. It is a deliberate `int 3` of the diag exe when it shows its dialog, which is why the process stays alive at 0 CPU and why the Windows Event Viewer shows no failure: DayZ writes its own `.mdmp` and halts.

The reliable fix is to copy the running `steam.exe` pid into the key, with guards: the key unchanged between two reads, a valid `ActiveUser`, exactly one running `steam.exe` in your session and its install path, checked again just before writing and verified after. Write from a shell outside any sandboxed (MSIX) app, because a write from inside one reaches only that app's private registry copy (`managed-launcher.md`, on the Steam prerequisite). Restarting Steam (`steam.exe -shutdown` and relaunch) keeps the login but may not rewrite the key: after one restart the key kept the old pid and the new one appeared only in `HKLM\SOFTWARE\Valve\Steam\SteamPID`. If you restart, check that the key matches a running process before you launch the client.

The probe that tells the two states apart is `SteamAPI_IsSteamRunning`, not `SteamAPI_Init`. With a stale key, DayZ's own `steam_api64.dll` returned `Init` OK and `IsSteamRunning` false, and the client died anyway; after copying the pid both returned true and the client got in. A check that only calls `Init` passes on the broken state.

## Two Steam facts the registry cannot answer

- Which account is logged in: read `logs/connection_log.txt` under the Steam install for `[Logged On, ...] [U:1:<accountID>] RecvMsgClientLogOnResponse() : 'OK'`, where `SteamID64 = accountID + 76561197960265728`.
- Whether that account owns DayZ: `steamapps/appmanifest_221100.acf`, field `"LastOwner"`.

If the logged-in account is not the `LastOwner`, the client dies about a second after launch with the same header-only RPT and `0x80000003` while every registry check passes. Comparing the dump's `Caching Steam ID: <id>` with `LastOwner` settles it in a minute.

## Read the dump before you guess

A minidump carries a `MINIDUMP_EXCEPTION_STREAM` (type 6) and a `MODULE_LIST` (type 4). About 60 lines of Python pull out the exception code and the module that holds `ExceptionAddress`. Read it before theorising about drivers or the mod: `0x80000003` rules out both "render crash" and "corrupt mod".

Before you look for the cause in your change, deploy the previous build and reproduce. When the PBO from before the change failed the same way, that cleared the change in one cycle and moved the search to the environment. An A/B with the old build costs the same as testing one theory, and it decides.

## Reading live logs, and a run already released

DayZDiag keeps the RPT and `script_*.log` open, so `Get-Content` or `ReadAllText` can throw `IOException` at any point of a wait loop. To watch a live peer, open the file with explicit sharing:

```powershell
$fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read,
                     [IO.FileShare]::ReadWrite)
try { $text = [IO.StreamReader]::new($fs).ReadToEnd() } finally { $fs.Dispose() }
```

In the managed lifecycle, keep the `run_id` and use the public tools. When a low-level call finds a `released` run, the order is `adopt`, then `stop`; `stop` alone can only return `run_not_adopted`. If another session already cleaned it up, `run_not_adoptable` with no run processes and an RPT ending in `Termination successfully completed` is an orderly shutdown, not a crash.

## Quote the whole argument

For `name=value` arguments with spaces, quote the whole token:

```text
-profiles="<profiles-path>"      # wrong: quotes only around the value
"-profiles=<profiles-path>"      # right: one complete token
```

Do the same for `-config=`, `-mission=` and `-mod=`. In Windows PowerShell 5.1, an array passed to `Start-Process -ArgumentList` does not guarantee each element is quoted, so do not take it as proof of the command line the game received. The managed route of this skill passes a structured array and stays the normal way.

## A diag that never writes logs

For a hang at 0 CPU with no RPT, first run the minimal control, `DayZDiag_x64.exe -server` with no other arguments, and add the arguments back one at a time. On the measured build about 53 loaded modules meant "has not reached the UI yet" and 69 to 78 meant a real start; use that gap as a signature of that build, not as a constant. Read the real command line from `Win32_Process`; the cut-off header line of the RPT does not show it reliably.

Decide by the form of the failure before you touch the mod:

| Form | Next step |
|---|---|
| Alive, 0 CPU, no RPT and no dump | The minimal control and the argument bisection above. |
| Dies with a header-only RPT and an `ErrorMessage_*.mdmp`, no `crash_*.log`, even with no mods | Start a server of the same build. A stable server with a large RPT next to a bare client that crashes points at the client's native or graphics path; confirm with another project's profile in the same window. |
| Fails only when `-mod` is added | Now look at the mod and its load order. |

"It was rebooted" can be measured too: compare `Win32_OperatingSystem.LastBootUpTime`, and check that no process older than the stated reboot survives. Fast Startup can keep the kernel across a shutdown; a full reboot changes that value.
