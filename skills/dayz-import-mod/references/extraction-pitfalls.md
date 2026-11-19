# Pitfalls in a packed mod study

What goes wrong in a study of somebody else's PBOs (`study-a-packed-mod.md`): wrong conclusions from names and partial code, an extraction that did not decode the payload, a model read with the wrong reader, and the Linux differences.

The cases below are third-party mod behaviour, not vanilla, except where a vanilla file is named.

## Wrong conclusions

1. **Don't trust file names.** A PBO named like a gauge set turned out to be a source-only distribution.
2. **Don't confuse ZIP or RAR contents with PBO contents.** Source PBOs often wrap asset archives; those archives are not the mod.
3. **Don't assume parameter overrides are simple.** A 99-line parameter file for one vehicle referred to a custom base class with more than 60 `Get*` methods and 1,900 lines of logic.
4. **A class that is used but not found means the recovery dropped it, not that it is absent.** If the code calls `new FooCommand(...)` and no recovered file defines `class FooCommand`, do not conclude it lives elsewhere. Recovery tools lose real blocks (one filters by size and names blocks by their original size, so names collide: 133 extracted, 122 saved). Decompress every entry in the size range of a script and search for the class name before calling it unrecoverable. In one gunner-seat mod a 626-byte `HumanGunnerCommand` block was filtered out, and finding it changed how the mechanic was read.
5. **Don't infer runtime behaviour from partial control flow.** Reading `key_Forward.ForceDisable(false)` and concluding "the player can walk" was wrong: the movement call was commented out, and a `HumanCommandScript` moves the character only through its own hooks, `PreAnimUpdate`, `PrePhysUpdate` and `PostPhysUpdate` (`P:\scripts\3_game\human.c:1236`, hooks at `:1288`, `:1306` and `:1322`), so locomotion input does nothing unless the command reads it. Trace a behaviour claim ("can move", "fires") to the entity that governs it (the active `HumanCommand`, the state machine), not to input gating or setup code that may be disabled or overridden later.

## Prove that extraction decoded the payload

Do not use `PboViewer.exe` for an automated sweep: it can report `Pbo successful unpack`, return exit 0, and write entries marked `Cprs` under the right file names while leaving their bytes compressed. A file that exists and a success message do not prove extraction. `pbo_inventory.py` counts the compressed entries of a PBO, so you know beforehand whether this trap applies.

Before parsing the result:

1. Extract with `ExtractPbo` to an explicit scratch destination. A fallback that writes beside the input must never run against a read-only Workshop source; copy the PBO to scratch first.
2. Compare representative output sizes with a trusted extraction. A layout expected at 6,444 bytes but written at 1,579 bytes is still compressed, although its name is right.
3. Do not replace the extractor with hand-written LZSS. The PBO variant uses a 4,096-byte ring buffer pre-filled with spaces; a wrong decoder can produce text that starts plausibly and then degrades, which is worse than a hard failure.
4. Run your parser against a known baseline before measuring improvements: reproducing an earlier 42 of 46 parsed layouts first is what made a later 46 of 46 credible.

Treat a baseline mismatch as an extraction failure and stop the sweep.

## Models

Read the ODOL version in header bytes 4 to 7 before parsing a binarized `.p3d`; the version per game build and the failure a wrong reader gives are in `skills/_shared/vehicles/dayz-1-30-vehicles.md`.

When py3d is not available, the printable strings of a binary `.p3d` give its memory points, selection names and texture paths (no geometry, no LODs):

```powershell
$bytes = [System.IO.File]::ReadAllBytes($p3d)
$current = ""
$strings = New-Object System.Collections.Generic.HashSet[string]
foreach ($b in $bytes) {
    if ($b -ge 32 -and $b -le 126) { $current += [char]$b }
    else {
        if ($current.Length -ge 4) { [void]$strings.Add($current) }
        $current = ""
    }
}
$strings | Where-Object { $_ -match '^(axis_|pos_|light_|seat_|dmgzone_)' } | Sort-Object
```

## On Linux

`pbo_inventory.py` is plain Python and runs unchanged. The Proton setup and the dayzmake version rule (2.0.0 or later before unpacking a PBO you did not build) are in `skills/_shared/linux-proton.md` and `skills/dayz-build-pbo/references/dayzmake-linux.md`. What this study adds:

- **Below dayzmake 2.0.0**, copy the PBO to a private folder first, so it cannot change between the check and the extraction. List every entry name of that copy with `dayzmake inspect <pbo>` or `pbo_inventory.py`, and refuse the PBO if a name holds a control character (a byte below 0x20, or 0x7f), starts with `/` or `\`, has a `..` segment, or has a drive letter (`X:`). Then unpack the copy into a fresh, empty folder.
- Keep `--force` only where its reason is the `$PBOPREFIX$` collision and containment is enforced (2.0.0 or later, or names already checked).
- `dayzmake cat <pbo> <name>` prints one file to stdout without writing to disk. It is never a check of the rest of the PBO.
- Rapified configs: `dayzmake derapify`.
- PowerShell loops (`Get-ChildItem ... | ForEach-Object`) become `find ... -name '*.pbo' -exec ...`.
