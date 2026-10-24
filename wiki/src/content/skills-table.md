| Skill | What it does |
| --- | --- |
| **Setup** | |
| `/dayz-init` | Runs a setup wizard on first use, with an optional spec step, and then serves as a status hub for the active mod. |
| `/dayz-preflight` | Checks the P drive, DayZ Tools, vanilla data and the Workshop link. |
| `/dayz-workdrive` | Mounts the P drive after a reboot without opening DayZ Tools. |
| `/dayz-setup-objectbuilder` | Configures Object Builder on a new machine. |
| **Mods** | |
| `/dayz-new-mod` | Creates a new mod with the standard folders and files. |
| `/dayz-import-mod` | Brings an existing mod folder or a GitHub repository into the workspace. |
| `/dayz-add-scaffold` | Adds missing standard pieces to an existing mod. |
| `/dayz-recipe` | Starts a plan from a recipe (new weapon, new vest or new craftable item) for the architect to complete. |
| `/dayz-scope-mod` | Restricts editing to one mod. |
| `/dayz-clean-workspace` | Removes the mods it created and their builds. |
| **Build** | |
| `/dayz-lint` | Finds errors that would prevent a mod from loading, before packing. Runs first inside the build gate and `/dayz-build-pbo`. |
| `/dayz-build-pbo` | Packs a mod into a PBO with AddonBuilder. |
| `/dayz-deploy-pbo` | Copies prebuilt PBOs and keys into place without AddonBuilder. |
| **Test** | |
| `/dayz-add-server` | Sets up a local test server instance. |
| `/dayz-launch-test` | Starts a diag server and client with the selected mods. |
| `/dayz-stop-test` | Stops the test session. |
| `/dayz-cot-bootstrap` | Grants admin rights in Community Online Tools on the test server. |
| `/dayz-logwatch` | Watches the logs during a test session and triages each new error as it appears. |
| **Checks, routing and status** | |
| `/dayz-gate` | Runs the build, in-game, behavior and visual checks as scripts that print PASS or FAIL, with known-error triage. |
| `/dayz-conflict-check` | If your mod uses add-ons such as CF, COT or Expansion, finds prefix, path and class collisions with them. |
| `/dayz-upgrade-guard` | After a DayZ update, lists mod classes whose vanilla parent classes changed. |
| `/dayz-balance` | Compares item stats with similar vanilla items and flags outliers. |
| `/dayz-health` | Produces a page for each mod with the last build, last test, open findings and gate history. |
| `/dayz-route` | Shows which skill, specialist or team should handle a request. |
| `/dayz-statusline` | Installs a status line that shows P:, the active mod, DayZ Diag and index age. |
| **Art and UI** | |
| `/dayz-pack-texture` | Converts images to `.paa` and checks their suffixes. |
| `/dayz-build-imageset` | Packs UI sprites into an imageset. |
| `/dayz-layout-preview` | Renders a `.layout` as PNG images at several screen sizes and flags widgets that fall off screen. |
| `/dayz-p3d-audit` | Finds collision, physics and structure problems in models. |
| `/dayz-particles` | Provides reference material for making particle effects without Workbench. |
| `/dayz-launch-objectbuilder` | Opens Object Builder on a model. |
| `/dayz-launch-workbench` | Opens Workbench on a mod's project. |
| **Server economy** | |
| `/dayz-edit-types` | Adds, changes, removes or merges `types.xml` entries. |
| `/dayz-split-types` | Splits one large `types.xml` into 19 category files. |
| **Release** | |
| `/dayz-release-pack` | Writes the Workshop description, a changelog entry, the classname list and installation notes for server owners. |
| `/dayz-server-kit` | Packages types.xml entries, cfgeconomycore lines, the load order and the public key into a ZIP file for server owners. |
| **RAG search** | |
| `/dayz-search-index` | Builds the game files index. |
| `/dayz-search-download` | Downloads a prebuilt index instead. |
| `/dayz-ask` | Answers a plain-English question about vanilla DayZ with verified path:line citations. |
| **Team and repository** | |
| `/dayz-record-correction` | Turns a user correction into a team rule. |
| `/sync-skills` | Links the skills into Claude Code, Codex and Gemini (clones only). |
| `/agentic-z-update` | Pulls template updates into a clone (clones only). |
| `/docs-sync` | Keeps the documentation wiki in line with the source files (clones only). |
| `/clean-repo` | Runs a cleanup across every domain of the repository (clones only). |
