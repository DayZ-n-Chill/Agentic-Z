# No-token commands

Every `.bat` here runs an Agentic-Z script directly (a skill script, or the repo tools in this folder). Run it from a terminal (a double-clicked window closes before you can read the result): Claude is not involved, so it costs no Claude tokens. The one exception is `evals.bat`, which runs `claude -p` once per question (except with `--dry-run`), so a real run spends tokens. Each forwards its arguments to the script; add `--help` for the full options. Every wrapper except `stop-test.bat` (which only runs `taskkill` and needs no Python) runs `python` when it works and otherwise falls back to the `py` launcher, so either one on PATH is enough. You need Python 3 installed: when neither runs, the `scripts\dayz` wrappers other than `dayz-search.bat` stop with `[FAIL] Python 3 not found` and exit 9009. The `scripts\setup` and `scripts\dev` wrappers (including `preflight.bat`, often the first one a new user runs) and `dayz-search.bat` have no such check: without Python, Windows prints `'py' is not recognized as an internal or external command` and the wrapper exits 9009, which means Python 3 is missing from PATH.

A few wrappers call an outside paid API instead, with your own key from `.env` or the environment:

- `ask.bat` and `dayz-search.bat` send each question to Voyage AI to embed it, which spends a few Voyage tokens per search. `ask.bat --grep` skips Voyage and searches the files on P: directly, and `ask.bat` does the same on its own, spending nothing, when `VOYAGE_API_KEY` is not set or no search index is installed.
- `search-index.bat` embeds the whole vanilla corpus with Voyage, which spends a large share of the Voyage free tier. It asks before building when the projected total nears the free tier. `search-download.bat` installs the prebuilt index instead and spends no Voyage tokens.
- `route.bat` asks TypeSafe's Jev only when its own rules are not confident and `TYPESAFE_API_KEY` is set.

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
| `triage.bat` | Match log lines against known errors (`--stdin` for a pasted log) | `triage.bat .server\chernarus\Profiles\script_2026-10-24_03-07-37.log` (DayZ names each script log `script_<date>_<time>.log`) |
| `deploy-pbo.bat` | Copy a bundle's prebuilt PBOs into place | `deploy-pbo.bat MyBundle` |
| `add-server.bat` | Set up a local test server | `add-server.bat chernarus` |
| `launch-test.bat` | Start a diag server and client with your mod | `launch-test.bat MyVest --server chernarus` |
| `logwatch.bat` | Watch a test session's logs and triage each new error line | `logwatch.bat --server chernarus` |
| `stop-test.bat` | Stop the test session | `stop-test.bat` |
| `cot-bootstrap.bat` | Give yourself COT admin on the test server | `cot-bootstrap.bat MyVest` |
| `pack-texture.bat` | Convert PNG or TGA to `.paa` | `pack-texture.bat vest_co.png` |
| `build-imageset.bat` | Pack UI sprites into an imageset | `build-imageset.bat --help` |
| `layout-preview.bat` | Draw a `.layout` as PNGs at several screen sizes | `layout-preview.bat gui\layouts\hud.layout` |
| `clean-workspace.bat` | Delete managed mod folders under `workspace\` with their `P:\<ModName>\` junctions and deployed `P:\Mods\@<ModName>\` copies (a mod folder holding `.git` is skipped; a deployed copy is removed only when it carries the toolkit's `.agentic-z-scaffold` ownership marker, so a hand-copied or subscribed one stays and the run prints a warning naming it); `--dry-run` lists them first | `clean-workspace.bat --mod MyVest --dry-run` |
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
| `sync-skills.bat` | Link the skills into Codex and Gemini. `--agents` replaces that default list: `--agents claude codex gemini` links all three, while `--agents claude` alone links only Claude Code |
| `agentic-z-update.bat` | Pull template updates into a clone |

## Repo maintenance (`scripts\dev\`)

| File | What it does |
|---|---|
| `docs-sync.bat` | Keep the wiki matching the source files |
| `clean-repo.bat` | Reset the clone. After one prompt it deletes every managed mod folder under `workspace\` (a mod folder holding `.git` is skipped), its `P:\<ModName>\` junction and its deployed `P:\Mods\@<ModName>\` copy (only when that copy carries the toolkit's `.agentic-z-scaffold` ownership marker; any other copy stays, with a warning), and all of `.server\`, including the `serverDZ.cfg` and mission files git tracks. Mod source that is not in git is lost. Run `--dry-run` first to see the list, and add `--keep-server` to keep `.server\` |
| `evals.bat` | Ask agents their answer tests (`--baseline` compares the scores with the baseline, `--dry-run` asks nothing). Costs tokens: one `claude -p` call per question |

Prefer buttons? The `agentic-z-panel` plugin puts the common ones beside the chat: `/plugin install agentic-z-panel@dayz-n-chill`, then `/dayz-panel`.
