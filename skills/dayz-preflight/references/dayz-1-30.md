# DayZ 1.30 and the environment check

What DayZ 1.30 changes around the environment check: one new launch option, unpacked mod folders and three Workbench editors. Every check in `preflight.py` holds on 1.30 as it did on 1.29, and 1.30 needs no new probe. Preflight still launches nothing.

## What 1.30 adds

The rows come from the modding section of the DayZ 1.30 changelog. They are engine and tool behaviour, which no script or config file on `P:\` records, so the last column says what was confirmed on an installed DayZ 1.30 and DayZ Tools 1.30.

| Since 1.30 | What the changelog says | What it means here | Confirmed on the install |
|---|---|---|---|
| `-cacheP3D=0/1` launch option | Writes `.p3dcache` files next to `.p3d` files, so later starts of the game or Buldozer load unbinarized models faster. | Mention it when the user is about to iterate on MLOD models in Buldozer. The cache files sit beside the `.p3d` and are not packed into a shipping PBO. | The strings `cacheP3D` and `p3dcache` are in `DayZ_x64.exe` and `DayZDiag_x64.exe`, and `cacheP3D` is in `workbenchApp.exe`. The speed gain was not measured. |
| `-mod` takes an unpacked folder | `-mod` can name a physical folder, and RV configs load from a mod that is not packed. | Preflight still checks `P:\` and the `P:\Mods` junction, because the packed deploy path needs both. Iterating on an unpacked folder belongs to `/dayz-launch-test`. | Changelog only. |
| New Workbench editors | A ragdoll editor, an Enfusion config editor and the 2021 Enfusion Animation Editor. | Nothing to check. Open them from Workbench (`/dayz-launch-workbench`); they have no install path of their own. | Workbench is still `Bin\Workbench\workbenchApp.exe` under DayZ Tools. The exe holds the `RagdollEditWindow` and `RagdollConfigEditWindow` classes and an "Animation Editor" menu string. The editors were not opened. |

## Where the rest lives

- The Object Builder viewer check in `object-builder-viewer.md` is the same on 1.30. Pair it with `-cacheP3D` only once DayZ Tools 1.30 is installed.
- Launch flags and command lines: `/dayz-launch-test` and `skills/dayz-launch-test/references/dayz-1-30.md`.
- The mesh cache and the model side: `skills/_shared/models/dayz-1-30-models.md`.
