# Object Builder's external viewer (Buldozer) path

Buldozer is the cheap answer to "how does it look?". Object Builder starts the game engine as a viewer, so materials, alpha and animations can be previewed without paying for a build and an in-game test. Object Builder starts the viewer from one registry value. When that value names an exe that does not exist, or is empty, the preview never opens and nothing reports an error, so the question gets answered in game instead.

`preflight.py` does not run this check. Run it by hand before a session that will lean on Object Builder previews.

Not yet checked on `P:\`: this is registry and tool behaviour, which no vanilla file records. The measurements are listed under "What was measured".

## The check

The value is `%External Viewer` under `HKCU\Software\Bohemia Interactive\Dayz Tools\Object Builder\CConfig`. It holds the viewer's command line: the exe in quotes, then ` -buldozer` and its options. Read it and test the exe:

```powershell
$v = (Get-ItemProperty 'HKCU:\Software\Bohemia Interactive\Dayz Tools\Object Builder\CConfig').'%External Viewer'
$exe = ($v -split ' -buldozer')[0].Trim('"')
if ($exe) { Test-Path $exe } else { 'not set' }
```

| Result | Meaning | What to tell the user |
|---|---|---|
| `True` | The viewer exe exists. | Nothing to fix. |
| `False` | The value names an exe that is not there. | Report it as a failure of this check and suggest the real path, `<steamapps>\common\DayZ\DayZ_x64.exe` (`find_dayz_game()` in `preflight.py` returns that folder). |
| `not set` | The value is empty, so no viewer is configured. | Same suggestion: set the value to the real exe followed by ` -buldozer`. |
| An error that the key does not exist | Object Builder has never been configured on this machine. | Run `/dayz-setup-objectbuilder` first, then repeat the check. |

Do not write the registry value from this skill. Report the result and the suggested path, and let the user set it.

## Why the default is broken

On one install the value pointed at `<steamapps>\common\DayZ_x64.exe`, without the `DayZ\` folder, which is why the viewer was dead out of the box. The DayZ Tools installer probably wrote that path; this was not confirmed.

A second install (DayZ Tools with game 1.30.164289) showed a different broken state: the value existed but was empty, and the `Bin\ObjectBuilder\ObjectBuilder_defaultSettings.reg` file that `/dayz-setup-objectbuilder` imports has no `%External Viewer` line at all. So expect either a wrong path or an empty value on a machine nobody has fixed, and treat both as "no preview".

## What was measured

- First install: configured path `Test-Path` gave `False`, the real path gave `True`, and `P:\Buldozer` was present.
- The cost of not checking: about 20 work sessions on one vehicle project paid for full in-game cycles to answer "does it show?" questions (label alpha, needle size, a quad behind the screen) that Buldozer was never used for.
- Second install: the snippet above printed `not set`; the game exe was at `<steamapps>\common\DayZ\DayZ_x64.exe` and nothing was at `<steamapps>\common\DayZ_x64.exe`. `P:\Buldozer` did not exist there.

## Not verified yet

Nobody has measured that Buldozer opens a custom `.p3d` together with its `.rvmat` files. Until that is measured, do not make "preview in Buldozer" a visual gate in the model or vehicle skills. This check only tells you whether the viewer can start.

On DayZ 1.30 the check itself is unchanged; see `dayz-1-30.md` for the `-cacheP3D` option that goes with Buldozer work. On Linux the key lives in the tools prefix's registry and the check was not run; see `linux.md`.
