# Pitfalls when reverse-engineering a PBO

What goes wrong when studying somebody else's mod: wrong conclusions from names and partial code, an extraction that did not decode the payload, a companion PBO that seems lost, and how to read a `.p3d` without py3d.

Not yet checked on `P:\` except where a vanilla file is named: the cases below are third-party mod behaviour (an aircraft mod, a gunner-seat mod and a trader mod), not vanilla.

## Anti-patterns seen during the work

1. **Don't trust file names.** A PBO named `aviation_dials` turned out to be a source-only distribution.
2. **Don't confuse ZIP or RAR contents with PBO contents.** Source PBOs often wrap asset archives; those archives are not the mod.
3. **Don't assume parameter overrides are simple.** A "simple" 99-line parameter file for one aircraft of the measured mod refers to a custom base class with more than 60 `Get*` methods and 1,900 lines of logic.
4. **Don't claim convergence without an honest search.** Mark a finding `confirm` only after a search of `skills/` proves the pattern is documented.
5. **Don't change a skill without reading it back.** Adding to a file that already has the section creates duplicates; always re-read.
6. **Don't put apostrophes in a heredoc that sits inside a single-quoted `bash -c '...'` string.** The first apostrophe ends the outer quoted string and breaks parsing. A plain `cat <<'EOF'` heredoc is safe: its body is literal. Write the file with the editor tool when the content has apostrophes and must pass through `bash -c`.
7. **Don't put backslashes in JSON evidence paths.** Use forward slashes (`TheirMod/Scripts/4_World/file.c`); a JSON parser rejects an unescaped backslash.
8. **A class that is used but not found means the extractor dropped it, not that it is absent.** If the code calls `new FooCommand(...)` and no recovered file defines `class FooCommand`, do not conclude it lives elsewhere or must be re-derived from scratch. Recovery tools lose real blocks (the JAPM recovery extractor has a size filter and names blocks by `original_size`, so names collide: 133 extracted, 122 saved). Decompress every entry in the size range of a script by brute force and search for the class name before calling it unrecoverable. Verified: `HumanGunnerCommand`, a 626-byte block, was filtered out of the recovery of a gunner-seat mod; brute force found it, and it changed how the mechanic was read.
9. **Don't infer runtime behaviour from partial control flow.** Reading `key_Forward.ForceDisable(false)` and concluding "the player can walk" was wrong: the movement call was commented out, and a `HumanCommandScript` ignores locomotion input in any case. A behaviour claim ("can move", "fires") must be traced to the entity that governs it (the active `HumanCommand`, the state machine), not to input gating or setup code that may be vestigial, disabled or overridden later. Honest verification applies to runtime behaviour, not only to API signatures.

## Recover historical artifacts before declaring a companion missing

Before concluding that a referenced PBO or archive is unrecoverable, search the delivery history and the metadata as well as the live files:

- Use cloud-sync metadata to recover the resource tree, names, sizes, timestamps, content hashes and deletion provenance. A live hydration mapping proves only that a mapping exists; it does not prove the payload bytes remain.
- Inspect the browser's download history for stable attachment or channel identifiers, but never keep expiring signed query strings, cookies or credentials.
- Search the normal delivery UI, linked announcement channels included, and keep each recovered revision separately with its timestamp and SHA-256.
- Treat Jump Lists, Recycle Bin metadata, Steam manifests and caches, and archive indexes as supporting evidence, not as the missing payload.

Hash and size metadata can prove identity if a copy appears later, but cannot stand in for the bytes. A later revision is a historical reference, never an unlabelled replacement for the missing exact version. This sequence recovered a later companion revision after metadata first identified the exact deleted artifact, in a case measured on 2026-07-20.

## Prove that extraction decoded the payload before measuring it

`ExtractPbo` is the extractor in the workflow. Do not use `PboViewer.exe` for an automated sweep: it can report `Pbo successful unpack`, return exit 0, and write entries marked `Cprs` under the correct file names while leaving their bytes compressed. A file that exists and a success message do not prove extraction. `inventory.py` counts the compressed entries of a PBO, so you know beforehand whether this trap applies.

Checks before parsing the result:

1. Extract to an explicit scratch destination with `ExtractPbo`. A fallback that writes beside the input must never run against a read-only Workshop source; copy the PBO to scratch first.
2. Compare representative output sizes with a trusted extraction. A layout expected at 6,444 bytes but written at 1,579 bytes is still compressed, even though its name is right.
3. Do not replace the extractor with hand-written LZSS. Bohemia's variant uses a 4,096-byte ring buffer pre-filled with spaces; a wrong decoder can produce text that starts plausibly and then degrades, which is more dangerous than a hard failure.
4. Run the existing parser against a known baseline before measuring improvements. In the measured trader mod case, reproducing the earlier 42 of 46 layouts first was the control that made the later 46 of 46 credible.

Treat a baseline mismatch as an extraction failure. Stop the sweep instead of drawing findings from bytes whose decoding has not been proved.

## ODOL version before parsing a model (1.30)

A 1.30 vanilla `.p3d` is ODOL version 56 (1.29: version 54, not checkable on `P:\`, which holds the 1.30 data). Read header bytes 4 to 7 before parsing a binarized model; a reader written for version 54 fails with `ValueError: subsection not found`. Checked here on the unpacked 1.30 data: `P:\DZ\gear\camping\wooden_case.p3d` and `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` both start with `ODOL` followed by the 32-bit value 56. More detail is in `skills/_shared/vehicles/dayz-1-30-vehicles.md`.

## Reading a `.p3d` without py3d

For a binary `.p3d` when py3d is not available, pull the printable strings:

```powershell
# Strings extraction (printable ASCII, 4 characters or more)
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

This captures memory points, selection names and texture references. It is not as complete as py3d (no geometry, no LODs), but it is enough to identify a model's structure.

## Lessons from a 43-PBO aircraft mod

- **Re-scope on day 1 if the inventory contradicts the assumption.** 42 of 43 PBOs were source-only. That saved weeks.
- **The pass 1 dimensional sweep is the 80/20 win.** It catches all major patterns. Pass 2 catches custom code. Pass 3 usually gives diminishing returns.
- **Template detection speeds up pass 2.** Once you see that all aircraft are clones of two templates, you can confirm clone status quickly and look for new patterns in the customised ones.
- **Author fingerprints emerge.** By pass 2 you see the naming, code style and sound-asset ownership patterns that let you predict the next quirk.
- **Notes are essential.** About 20% of the findings fit no skill but are valuable reference. Do not lose them.
