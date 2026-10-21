# No-token commands

Every `.bat` here runs an Agentic-Z skill script directly. Double-click it or run it from a terminal: no AI is involved, so it costs no tokens. Each forwards its arguments to the script; add `--help` for the full options.

Use the slash command instead when you want Claude to run the step as part of a bigger task and read the result for you.

## Daily DayZ work (`scripts\dayz\`)

| File | What it does | Example |
|---|---|---|
| `status.bat` | Active mod, PBO age, test servers, DayZ Diag and search status | `status.bat` |
| `new-mod.bat` | Create a new mod in `workspace\` | `new-mod.bat MyVest --author Me` |
| `import-mod.bat` | Bring an existing mod folder in, or clone a GitHub link | `import-mod.bat --source D:\Mods\MyVest` |
| `add-scaffold.bat` | Add missing standard pieces to a mod | `add-scaffold.bat MyVest --piece junction` |
| `recipe.bat` | Start a mod plan from a recipe: weapon, vest or craftable | `recipe.bat vest MyVest` |
| `scope-mod.bat` | Lock editing to one mod | `scope-mod.bat MyVest` |
| `lint.bat` | Find errors that would stop a mod loading, with PASS or FAIL | `lint.bat MyVest` |
| `conflict-check.bat` | Find class name and path collisions with CF, COT and Expansion, with PASS or FAIL | `conflict-check.bat MyVest` |
| `balance.bat` | Compare item stats with similar vanilla items and flag outliers | `balance.bat MyVest` |
| `build-pbo.bat` | Pack a mod into a PBO | `build-pbo.bat MyVest` |
| `gate.bat` | Build, in-game, behavior or visual check with PASS or FAIL | `gate.bat build MyVest` |
| `health.bat` | Write a mod's health page: last build, last test, open findings, history | `health.bat MyVest` |
| `triage.bat` | Match log lines against known errors (`--stdin` for a pasted log) | `triage.bat .server\chernarus\Profiles\script.log` |
| `deploy-pbo.bat` | Copy a bundle's prebuilt PBOs into place | `deploy-pbo.bat MyBundle` |
| `add-server.bat` | Set up a local test server | `add-server.bat chernarus` |
| `launch-test.bat` | Start a diag server and client with your mod | `launch-test.bat MyVest --server chernarus` |
| `logwatch.bat` | Watch a test session's logs and triage each new error line | `logwatch.bat --server chernarus` |
| `stop-test.bat` | Stop the test session | `stop-test.bat` |
| `cot-bootstrap.bat` | Give yourself COT admin on the test server | `cot-bootstrap.bat MyVest` |
| `pack-texture.bat` | Convert PNG or TGA to `.paa` | `pack-texture.bat vest_co.png` |
| `build-imageset.bat` | Pack UI sprites into an imageset | `build-imageset.bat --help` |
| `layout-preview.bat` | Draw a `.layout` as PNGs at several screen sizes | `layout-preview.bat gui\layouts\hud.layout` |
| `clean-workspace.bat` | Remove DayZ scaffolds and their deployed files | `clean-workspace.bat --mod MyVest` |
| `upgrade-guard.bat` | Snapshot vanilla classes before a DayZ update, then list the mod classes it affects | `upgrade-guard.bat check MyVest` |
| `p3d-audit.bat` | Audit a `.p3d` model and its config | `p3d-audit.bat --help` |
| `types-edit.bat` | Add, change or remove a `types.xml` entry, or merge a pasted chunk (`--merge`) | `types-edit.bat --help` |
| `types-split.bat` | Split one big `types.xml` into category files | `types-split.bat --help` |
| `release-pack.bat` | Write the Workshop text, changelog, classname list and install notes | `release-pack.bat MyVest --version 1.0.0` |
| `server-kit.bat` | Zip the types entries, `cfgeconomycore.xml` lines, load order and public key | `server-kit.bat MyVest --mission chernarus` |
| `workbench.bat` | Open Workbench | `workbench.bat --mod MyVest` |
| `objectbuilder.bat` | Open Object Builder | `objectbuilder.bat` |
| `route.bat` | Show who should handle a request | `route.bat "build MyVest"` |
| `ask.bat` | Answer a vanilla DayZ question with checked `path:line` citations | `ask.bat "how does food spoil"` |
| `dayz-search.bat` | Search the vanilla RAG index from the terminal | `dayz-search.bat "food spoilage"` |
| `search-download.bat` | Install the prebuilt search index | `search-download.bat` |
| `search-index.bat` | Build the search index yourself | `search-index.bat --full` |

## Setup (`scripts\setup\`)

| File | What it does |
|---|---|
| `preflight.bat` | Check P:, DayZ Tools, vanilla data and the Workshop link |
| `workdrive.bat` | Mount P: after a reboot |
| `setup-objectbuilder.bat` | Configure Object Builder on a new machine |
| `statusline.bat` | Install the DayZ status line (`--remove`, `--status`) |
| `sync-skills.bat` | Link the skills into Claude Code, Codex and Gemini |
| `agentic-z-update.bat` | Pull template updates into a clone |

## Repo maintenance (`scripts\dev\`)

| File | What it does |
|---|---|
| `docs-sync.bat` | Keep the wiki matching the source files |
| `clean-repo.bat` | Clear generated files before a push |
| `evals.bat` | Ask agents their answer tests and compare the scores with the baseline (`--dry-run` asks nothing) |

Prefer buttons? The `agentic-z-panel` plugin puts the common ones beside the chat: `/plugin install agentic-z-panel@dayz-n-chill`, then `/dayz-panel`.
