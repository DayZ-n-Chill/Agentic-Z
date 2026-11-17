# The checks on Linux

Everything in `SKILL.md` is the Windows workflow and stays valid there. `preflight.py` looks for `P:\` and reads the Windows registry, so on Linux it stops at the first check with `[FAIL]  P:\ is NOT mounted`. This file says what replaces each check. The Proton setup, the measured tool matrix and the pitfalls are in the Linux note, `skills/_shared/linux-proton.md`.

Not yet checked on `P:\`: the table below was measured on Debian with Steam and Proton in November 2026. `dayz-proton.sh` is the helper script that the Linux note documents; it is `skills/_shared/scripts/dayz-proton.sh`.

| Windows check | Linux equivalent |
|---|---|
| DayZ Tools, DayZ and DayZ Server located | `dayz-proton.sh doctor`. It reads `libraryfolders.vdf` and the app manifests, and prints the game versions and any pending updates. |
| `P:\` mounted | A plain directory recorded by `dayz-proton.sh init <dir>`. `doctor` prints it. |
| `DayZDiag_x64.exe` found | It is in the DayZ folder (Steam app 221100) and runs under Proton. |
| Workshop folder | `<library>/steamapps/workshop/content/221100/<id>` |
| Registry values | They do not exist on the host. `init` writes the values the tools read into its own private prefix. |

`init` is the Linux counterpart of mounting `P:`. The rule for mounting carries over: do not run it unasked. Tell the user what it does (it creates private prefixes under `~/.local/share/dayz-proton` and takes about two minutes) and let them run it.

The Object Builder viewer value described in `object-builder-viewer.md` lives in the tools prefix's registry on Linux. That check was not run there.
