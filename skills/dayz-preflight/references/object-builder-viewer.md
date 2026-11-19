# Object Builder's external viewer

How to check the registry value that tells Object Builder where Buldozer, its game engine preview, lives. When that value names a missing exe or is empty, the preview never opens and nothing reports an error. `preflight.py` does not run this check; run it by hand before a session that leans on Object Builder previews.

Buldozer is the cheap way to answer "how does it look?": materials, alpha and animations show without a build and an in-game test. Without it those questions get answered in game, one full build and launch at a time.

This is registry and tool behaviour, which no vanilla file records, so none of it is checked on `P:\`.

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
| `False` | The value names an exe that is not there. | Report the check as failed and suggest the real path, `<steamapps>\common\DayZ\DayZ_x64.exe` (`find_dayz_game()` in `preflight.py` returns that folder). |
| `not set` | The value is empty, so no viewer is configured. | Same suggestion: set the value to the real exe followed by ` -buldozer`. |
| An error that the key does not exist | Object Builder has never been configured on this machine. | Run `/dayz-setup-objectbuilder` first, then repeat the check. |

Never write the registry value from this skill. Report the result and the suggested path, and let the user set it.

## Why a fresh install is usually broken

Expect one of two broken states on a machine nobody has fixed, and treat both as "no preview":

- **A wrong path.** One install pointed at `<steamapps>\common\DayZ_x64.exe`, without the `DayZ\` folder; `Test-Path` gave `False` for it and `True` for the real path. The DayZ Tools installer probably wrote it; that is not confirmed.
- **An empty value.** Another install, with DayZ Tools and the game at 1.30, had the value present but empty. The `Bin\ObjectBuilder\ObjectBuilder_defaultSettings.reg` file that `/dayz-setup-objectbuilder` imports has no `%External Viewer` line at all.

`P:\Buldozer` was present on the first install and missing on the second, so its absence alone says nothing about the viewer.

Skipping the check is expensive: on one vehicle project about 20 work sessions paid for full in-game cycles to answer "does it show?" questions (label alpha, needle size, a quad behind the screen) that Buldozer could have answered.

## What the check does not prove

Nobody has confirmed that Buldozer opens a custom `.p3d` together with its `.rvmat` files. Until that is tested, do not make "preview in Buldozer" a visual gate in the model or vehicle skills. This check only tells you whether the viewer can start.

On DayZ 1.30 the check is unchanged; `dayz-1-30.md` covers the `-cacheP3D` option that goes with Buldozer work. On Linux the key lives in the tools prefix's registry and the check has not been run there; see `skills/_shared/linux-proton.md`, "The work drive on Linux".
