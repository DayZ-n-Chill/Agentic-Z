# Starting DayZDiag by hand

What to check when you start DayZDiag yourself, outside `/dayz-launch-test` and outside dayz-mcp's managed lifecycle: reading defines from the log, a stale Steam session seen from inside a desktop app, the profiles path, the environment a crash dump carries, and owning the process. Each trap cost a run when a 1.30 Experimental install was probed by hand.

These were measured on a Windows test machine with the third-party dayz-mcp tooling present, and are not checked on `P:\`. The registry side of the Steam session is also covered in `managed-launcher.md` ("The client needs Steam") and `troubleshooting.md`.

## Read the defines from the script log

Each script module logs a line of the form `Module: <name>; ...; defines: "..."`. Reading it after a launch to the main menu, about 20 seconds, answers "is X defined in this executable?" without a probe mod. It also shows the version define: 1.30 logs `DAYZ_1_30`. Vanilla declares the placeholder `DAYZ_X_XX` and documents it as "filled in with the current Major and Minor version (e.g. DAYZ_1_16)" (`P:\scripts\1_core\defines.c:12` to `:14`).

## A desktop app can show the game a dead Steam

The Claude and Codex desktop apps run under MSIX registry virtualization: every process they start sees a private, frozen copy of `HKCU\Software\Valve\Steam\ActiveProcess`. After Steam restarts, a game launched from inside the app reads a dead Steam `pid`, logs `Unable to locate a running instance of Steam` and shows an error dialog while `steam.exe` runs.

- Compare the app's view with the real value: read the real hive through WMI `StdRegProv`, and the app's copy with `Get-ItemProperty` inside the app. Both must point at the live `steam.exe` before you launch.
- Launch through WMI (`Win32_Process.Create`) so the game reads the real key, or bring the copy in line right before launching. Writing the value from a shell inside the app fixes only the private copy, and only until the next Steam restart.
- Never start or restart Steam from a shell inside the app. The new Steam registers in the private copy, and the real key can be left at `pid = 0, ActiveUser = 0`: the WMI check outside reports it broken while the app's own view looks healthy, and dayz-mcp's `auto_remediate_steam` cannot fix it because its worker runs inside the app too.
- Never write or delete another program's `HKCU` keys from an app shell. A write creates the private copy; a delete leaves a tombstone that hides the real key even after it is written again outside. The copy goes away only with the app closed and its hive edited offline.

## Keep the profiles path short and new

- A profiles path of about 245 characters ended in `0xC0000005` after one second with no log written; a short path did not repeat it. Steam was broken at the same time, so the cause is likely, not isolated. Keep `-profiles=` short.
- Give each run a new `-profiles=` folder. A readiness check that read the newest `script_*.log` found a log left by an earlier run in the same folder and reported the server ready and the client connected at once: the run looked healthy and measured nothing. A client that never loads its textures fools a visual check the same way (`window-capture-pitfalls.md`, "Runs that never load their textures").

## Start the game with a short environment

A DayZ `ErrorMessage_*.mdmp` or crash minidump embeds the parent's whole environment block, and an agent shell usually holds API keys and passwords. On every crash the DayZ CrashReporter also sends "analytical data" before it offers the dump.

Start DayZ with `ProcessStartInfo.UseShellExecute = $false` and remove every variable not on a short list: `SystemRoot`, `Path`, `TEMP`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `ProgramFiles*`, the processor and OS variables, and `ComSpec`. Delete dumps you do not need.

## Own the process

A probe outside the managed lifecycle starts and stops only the process it launched, by its process id, and holds the dayz-mcp lease while it runs so no managed run lands on top of it. Closing rules: `automated-cells.md`, "Whoever opens a process closes it".
