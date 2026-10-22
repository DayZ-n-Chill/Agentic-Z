# agentic-z-panel

A Claude Code panel for Agentic-Z. It shows the DayZ state beside the chat and has one-click buttons that run the Agentic-Z skill scripts directly, so a press costs no model tokens.

**Windows only.** The panel runs `cmd /c`, `tasklist` and `%USERPROFILE%`, and the scripts it calls need DayZ Tools and the P: drive.

## Install

```text
/plugin install agentic-z-panel@dayz-n-chill
```

Then run `/dayz-panel` to open the panel.

## What it shows

Whether P: is mounted, the active mod (from `/dayz-init`), and whether a DayZ test session is running.

## Buttons

| Button | Key | Runs |
|---|---|---|
| Mount P: | `p` | `dayz-workdrive/mount.py` |
| Build PBO | `b` | `dayz-build-pbo/build.py <active mod>` |
| Check build (PASS/FAIL) | `c` | `dayz-gate/gate.py build <active mod>` |
| Check in game (PASS/FAIL) | `g` | `dayz-gate/gate.py ingame <active mod>` |
| Deploy prebuilt PBOs | `d` | `dayz-deploy-pbo/deploy.py <active mod>` |
| Launch test | `l` | `dayz-launch-test/launch.py <active mod>` |
| Stop test | `s` | `dayz-stop-test/stop_test.bat` |
| Open Workbench | `w` | `dayz-launch-workbench/launch.py --mod <active mod>` |
| Open Object Builder | `o` | `dayz-launch-objectbuilder/launch.py` |
| Check test logs | `t` | `dayz-logwatch/logwatch.py --since 30 --duration 3 --mod <active mod>` |
| Health page | `h` | `dayz-health/health.py <active mod>` |
| Release pack | `k` | `dayz-release-pack/release_pack.py <active mod>` |
| Ask vanilla (a text field) | Enter | `dayz-ask/ask.py "<question>"` |
| Refresh | `r` | re-checks the state |

One action runs at a time; a second press while one runs only shows a toast. Every press reads the state again first, so a mod picked with `/dayz-init` after the panel opened is used without pressing Refresh. Each run shows a toast when it ends and keeps its result line in the panel.

## Where it finds Agentic-Z

The clone that holds the session folder (that folder or the nearest parent with `.claude\skills\dayz-preflight\preflight.py`), otherwise the newest version in the plugin cache under `%USERPROFILE%\.claude\plugins\cache\dayz-n-chill\agentic-z`.

The active mod comes from `.claude\local-memory\dayz-init-state.json` in that clone. With no clone (a plugin install), it comes from the nearest folder at or above the session folder that holds that file.

## Tests

```text
claude plugin test mods/agentic-z-panel
```

`scripts/dev/test_repo_integrity.py` also checks that every script the buttons name exists, so a renamed skill script fails the pytest run.

More detail: `docs/token-saving.md`, section 8.
