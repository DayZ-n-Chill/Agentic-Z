# Character work on Linux

Covers what changes for this skill when the mod is built on Linux instead of Windows: packing and binarizing, the work drive, the GUI tools, and which checks run natively.

How to read the marks: this is tool behaviour reported by the source project (a comparison dated 2026-11-03), not vanilla game data, so nothing here can be checked on `P:\`. This repo is a Windows workspace; the rest of the skill describes the Windows workflow and stays valid there.

The Proton setup, the measured tool matrix and the pitfalls are in the shared Linux and Proton notes (`skills/_shared/linux-proton.md`). This file only says what changes for character work.

- **Pack, sign and binarize with dayzmake 1.0.0 or newer**, a DayZ fork of armake2 (<https://github.com/bzed/dayzmake>), pinned to `v1.0.0`: the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from the `v1.0.0` release page, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`. Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed.
- **Upstream armake2 is no substitute.** It is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake 1.0.0 includes them), and it lacks the DayZ-only functions dayzmake keeps adding.
- **Wrapper.** The shared helper script `skills/_shared/scripts/dayz-mod-pack.sh` wraps those commands (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`).
- **How far it was checked.** A textured cube binarized this way matched Bohemia's binarize from a `P:` root byte for byte (fork commit `7dcb3cf`, then still named armake2; `v1.0.0` contains it). That is not an in-game check of a binarized model, and not a check of a skinned character.
- **The work drive.** `P:\` is a plain directory mapped by the shared helper script `dayz-proton.sh init <dir>` (`skills/_shared/scripts/dayz-proton.sh`). A `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...` there.
- **GUI tools.** Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>` and `dayz-proton.sh gui TexView <paa>`. Object Builder opened and displayed a model; editing in it was not exercised.
- **Offline checks run natively.** The winding gate, py3d and the other Python tools under `scripts/tools/` are plain Python.
- **In-game checks.** Follow the Linux notes of the `dayz-test-ingame` skill (`skills/dayz-test-ingame/references/linux.md`).
