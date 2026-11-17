# DayZ 1.30 and the environment checks

A review of this skill against DayZ 1.30 found no statement that 1.30 makes false. Every check in `preflight.py` holds as it did on 1.29, and 1.30 adds no new probe. What 1.30 adds is launch options and Workbench editors worth knowing about while the environment is being prepared. Preflight still launches nothing.

Source: the modding section of Bohemia's DayZ 1.30 experimental changelog. Not yet checked on `P:\`: these are engine and tool behaviours, which no script or config file on `P:\` records. The "Checked" column says what was confirmed on an installed game and DayZ Tools, both version 1.30.164289.

| Since 1.30 | What the changelog says | What it means for this skill | Checked |
|---|---|---|---|
| `-cacheP3D=0/1` launch option | It creates `.p3dcache` files next to `.p3d` files, so later launches of the game or Buldozer are quicker when working with unbinarized assets. | Mention it when the user is about to iterate on unbinarized (MLOD) models in Buldozer. The cache files sit beside the `.p3d` and are not packed into a shipping PBO. | The strings `cacheP3D` and `p3dcache` are in `DayZ_x64.exe` and `DayZDiag_x64.exe`; `cacheP3D` is also in `workbenchApp.exe`. The speed-up was not measured. |
| `-mod` accepts an unpacked folder | `-mod` can point at a physical folder, and RV configs can be read when a mod is loaded unpacked. | Preflight still checks `P:\` and the `P:\Mods` junction, because the packed deploy path needs both. Iterating on an unpacked folder is the job of the launch and test skills (`/dayz-launch-test`). | Changelog only. |
| Workbench editors | A ragdoll editor, an Enfusion config editor and the 2021 Enfusion Animation Editor. | Nothing to check. Open them from Workbench (`/dayz-launch-workbench`); do not invent separate install paths for them. | Workbench 1.30.164289 is the usual `Bin\Workbench\workbenchApp.exe` under DayZ Tools. That exe holds `RagdollEditWindow` and `RagdollConfigEditWindow` classes and an "Animation Editor" menu string. The editors were not opened. |

The knowledge pack this came from had no Workbench 1.30 exe to inspect and treated the editors as changelog-only. The "Checked" cell above is what an installed copy shows.

The Object Builder viewer check in `object-builder-viewer.md` is the same on 1.30. Pair it with `-cacheP3D` only once DayZ Tools 1.30 is the installed version.

Where the rest lives: the launch flags and command lines belong to the in-game test skills (`/dayz-launch-test`, and `skills/dayz-test-ingame/references/dayz-1-30-test-ingame.md`), and the mesh cache and model side belong to the `dayz-model-pipeline` skill (`skills/dayz-model-pipeline/references/dayz-1-30-model-pipeline.md`).
