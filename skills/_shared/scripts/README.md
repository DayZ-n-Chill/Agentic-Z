# Shared helper scripts

Helper scripts that more than one skill uses. The shell scripts are the Linux route (POSIX `sh` or `bash`, `/proc`, Proton) and do nothing useful on Windows; the two Python scripts run on both. The full guide, with what was measured and what was not, is `skills/_shared/linux-proton.md` (section 7 has the same table with more detail).

None of these scripts calls `/dayz-preflight`: the shell scripts replace the Windows tools preflight checks for, and the two Python scripts only read the folders named on their command line.

## Which script answers which question

| Question | Script |
|---|---|
| Is the Linux machine set up (Proton, DayZ Tools prefix, dayzmake), and how do I run a DayZ Tools program or `DayZDiag` under Proton? | `dayz-proton.sh` (`doctor`, `init`, `winpath`, `tool`, `gui`, `binarize`, `headless start/shot/stop`) |
| How do I lay out, build, sign and check a mod for the Workshop with dayzmake? | `dayz-mod-pack.sh` (`init`, `keygen`, `build`, `check`, `publish-hint`; it never uploads) |
| Where is the native DayZ Server that Steam installed? | `find-dayzserver.sh` |
| How do I get a private server folder that leaves the Steam install untouched? | `make-server-tree.sh` |
| Which ports can a test server use right now? | `free-ports.sh` |
| How do I run the retail client with no monitor and take a screenshot of it? | `dayz-client-headless.sh` (`start`, `shot`, `stop`, `status`) |
| How do I run one automated client and server test and collect its logs? | `dayz-client-test.sh` |
| How do I unpack the scripts and configs of an install or a mod on Linux? | `extract-dayz-sources.sh` |
| How do I build a script API index from unpacked scripts, for a machine with no work drive? | `build-api-index.py` |
| How do I look up a class, its members, its subclasses or an enum in that index? | `dayz-api.py` (`class`, `find`, `sub`, `enum`, `src`, `chain`, `defines`) |

The index that `build-api-index.py` writes holds Bohemia's and mod authors' declarations. Build it locally and never commit it.

## Tests

| File | Covers | Runs on |
|---|---|---|
| `test_shared_api_index.py` | `build-api-index.py` and `dayz-api.py` | Windows and Linux |
| `test_dayz_proton.py` | `dayz-proton.sh` | Linux only (skips on Windows) |
| `test_linux_helpers.py` | the other shell scripts, on a fake Steam tree | Linux only (skips on Windows) |

Where the Linux material continues: `skills/dayz-build-pbo/references/dayzmake-linux.md` (building and signing), `skills/dayz-test-ingame/references/linux-native-server.md` and `linux-headless-client.md` in the same folder (running the server and client), `skills/dayz-preflight/references/linux.md` (what replaces each preflight check).
