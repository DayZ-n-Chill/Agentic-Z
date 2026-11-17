# Unpacking a PBO on Linux

What changes for this skill on Linux: which dayzmake version may unpack a PBO you did not build, the fallback for older versions, and the shell equivalents.

Not yet checked on `P:\`: this is tool behaviour read from dayzmake's source and measured by the knowledge pack's author, not a statement about vanilla data.

The workflow in `SKILL.md` is the Windows one and stays valid there. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in `skills/_shared/linux-proton.md`; this file only says what changes here. `inventory.py` is plain Python and runs on Linux unchanged.

- **Require dayzmake `v2.0.0` or later before running `dayzmake unpack` on any PBO you did not build yourself.** (`CLAIM-DAYZMAKE-UNPACK-V2-CONTAINMENT`) dayzmake `v2.0.0` (tag `v2.0.0`, commit `f31056ae`, https://github.com/bzed/dayzmake/releases/tag/v2.0.0; `src/pbo.rs`, `safe_relative_path` and `crosses_symlink`) checks relative entry paths, rejects symlink traversal and skips unsafe entries. (`CLAIM-DAYZMAKE-UNPACK-NO-CONTAINMENT`) dayzmake `v1.0.0` (`src/pbo.rs:724,731-733`) joins each entry name onto the output folder with no containment check, then creates the parent folders and the file: a `..\x` entry escapes, an absolute name replaces the base, and `--force` overwrites existing files. Dropping `--force` alone is not a fix.
- **Fallback below `v2.0.0`.** Copy the PBO to a private directory first, so it cannot change between the check and the extraction. List all entry names of that same copy with `dayzmake inspect <pbo>` (or `inventory.py`, which names unsafe entries) and refuse the PBO if any name holds a control character (a byte below 0x20, or 0x7f), starts with `/` or `\`, has a `..` segment (with `/` or `\`), or has a drive letter (`X:`). Then unpack that copy into a fresh, empty directory.
- Keep `--force` only where its reason is the `$PBOPREFIX$` collision and containment is enforced (`v2.0.0` or later, or names already checked).
- Reading one file with `dayzmake cat <pbo> <name>` (to stdout, nothing written to disk) is an alternative to extracting that file. It is never a check of the rest of the PBO.
- Rapified configs: `dayzmake derapify`.
- Helpers that extract a whole game install are external and not part of this repo.
- Obfuscated PBOs are not covered by this; they need a JAPM recovery tool first (see `SKILL.md`).
- PowerShell loops (`Get-ChildItem … | ForEach-Object`) become `find … -name '*.pbo' -exec …`.
