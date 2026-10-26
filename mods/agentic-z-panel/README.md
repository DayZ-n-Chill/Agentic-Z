# agentic-z-panel

A Claude Code panel for Agentic-Z. It shows the DayZ state beside the chat and has one-click buttons that run the Agentic-Z skill scripts directly, so a press costs no model tokens.

**Windows only.** The panel runs `cmd /c`, `tasklist` and `%USERPROFILE%`, and the scripts it calls need DayZ Tools and the P: drive.

## Install

```text
/plugin install agentic-z-panel@dayz-n-chill
```

The panel opens by itself when a session starts. After closing it, click **Agentic-Z panel** just above the prompt, or run `/dayz-panel`.

## What it shows

Whether P: is mounted, the active mod (from `/dayz-init`), and whether a DayZ test session is running, each with a green or red dot. The buttons sit in framed cards (Build and check, Test session, Tools, Ask vanilla DayZ), and the last run shows in a card framed green or red by its outcome.

`/dayz-panel` also replies in the chat with the same state, where Agentic-Z was found, and the last run.

## Updates

At session start the panel reads the marketplace list on GitHub. When it lists a newer panel, a toast, a line at the top of the panel and the `/dayz-panel` reply say so, with the command to run:

```text
claude plugin update agentic-z-panel@dayz-n-chill
```

Then restart Claude Code. Offline, the check shows nothing.

## Buttons

| Button | Key | Runs |
|---|---|---|
| Check setup | `e` | `dayz-preflight/preflight.py` |
| Add test server | `v` | `dayz-add-server/add_server.py chernarus` |
| New mod (a text field) | Enter | `dayz-new-mod/new_mod.py <name>`; type `MyVest by YourName` for a first mod, to set the author |
| Import mod (a text field) | Enter | `dayz-import-mod/import_mod.py --source <path or GitHub link>` |
| Mount P: | `p` | `dayz-workdrive/mount.py` |
| Build PBO | `b` | `dayz-build-pbo/build.py <active mod>` |
| Check build | `c` | `dayz-gate/gate.py build <active mod>` |
| Check in game | `g` | `dayz-gate/gate.py ingame <active mod>` |
| Deploy prebuilt | `d` | `dayz-deploy-pbo/deploy.py <active mod>` |
| Launch | `l` | `dayz-launch-test/launch.py <active mod>` |
| Stop | `s` | `dayz-stop-test/stop_test.bat` |
| Workbench | `w` | `dayz-launch-workbench/launch.py --mod <active mod>` |
| Object Builder | `o` | `dayz-launch-objectbuilder/launch.py` |
| Logs | `t` | `dayz-logwatch/logwatch.py --since 30 --duration 3 --mod <active mod>` |
| Health page | `h` | `dayz-health/health.py <active mod>` |
| Release pack | `k` | `dayz-release-pack/release_pack.py <active mod>` |
| Ask vanilla (a text field) | Enter | `dayz-ask/ask.py --top-k 10 --excerpt-lines 60 "<question>"` |
| Deep dive (under an answer) | `v` | `dayz-ask/ask.py --top-k 25 --excerpt-lines 200 "<question>"`, then a longer answer |
| Continue in chat (under an answer) | `m` | puts the question and answer in the prompt box for the main conversation |
| Refresh | `r` | re-checks the state |

The Python scripts run with `python` when it works, otherwise the `py` launcher, the same as the `scripts\dayz` wrappers. With neither, the button runs nothing and shows a `Python 3 not found` message. Scripts run with UTF-8 output, so an answer that quotes a non-ASCII character cannot crash them.

One action runs at a time; a second press while one runs only shows a toast. Every press reads the state again first, so a mod picked with `/dayz-init` after the panel opened is used without pressing Refresh. Each run shows a toast when it ends and keeps its result line in the panel. An ask keeps its verdict with the reason or notes under it, and one that finds nothing (`NONE`) shows "nothing found", not "failed".

## Where it finds Agentic-Z

The clone that holds the session folder (that folder or the nearest parent with `.claude\skills\dayz-preflight\preflight.py`), otherwise the newest version in the plugin cache under `%USERPROFILE%\.claude\plugins\cache\dayz-n-chill\agentic-z`.

The active mod comes from `.claude\local-memory\dayz-init-state.json` in that clone. With no clone (a plugin install), it comes from the nearest folder at or above the session folder that holds that file, stopping before the home folder (`%USERPROFILE%\.claude` is Claude Code's user config, and the skill scripts ignore a state file there too).

## Tests

```text
claude plugin test mods/agentic-z-panel
```

`scripts/dev/test_repo_integrity.py` also checks that every script the buttons name exists, so a renamed skill script fails the pytest run.

More detail: `docs/token-saving.md`, section 8.
