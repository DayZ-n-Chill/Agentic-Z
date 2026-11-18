# Deploy checks and crash fingerprints

How to prove the packed PBO holds the models you approved, how to check `config.cpp` syntax before the game reads it, and how to tell whether two native crashes come from the same place.

The cases below were measured on third-party vehicle mods (a helicopter, a sports coupe and a quad), not on vanilla, and are not checked on `P:\`.

## Read the property on the packed model

A manifest that compares file hashes cannot see a fix that adds or changes a property of a `.p3d` (`autocenter`, `class`, `sbsource`, `lodnoshadow`). If the PBO was packed from models built before the fix, it compares the same wrong file on both sides and passes. On a test helicopter, `autocenter=0` was added to the hull's visual LOD in the generator, but the PBO was packed from older models: of the 48 extracted models, the 8 sub-models carried it and all 40 hulls did not.

After `ExtractPbo`, read the property per LOD on the extracted files. Two rules keep that check usable:

- Write the expected value per model and LOD in a table, with a reason on each row, never as "all LODs". A healthy pack holds control models that are meant not to change, and a blanket check rejects them and gets switched off on its first run.
- The generator must pass its own check. The Memory LOD has no geometry to re-centre, so it never carries `autocenter`; an "all LODs" rule would fail the generator's own output. Declare exclusions; do not assume them.

## Link the checked model to the one the game loads

A check on a separate ODOL staging folder says nothing about the deployed PBO. `-packonly` packs whatever format sits in the source tree, and matching MLOD and ODOL files by path does not link them. On a test coupe the check passed the ODOL doors (about 2 MB each) while the live PBO carried the MLOD doors from the source tree.

Before deploying a checked model:

1. List the PBO and extract every `.p3d` entry.
2. Require the expected signature (`ODOL` where the model must be binarized).
3. Require each entry's SHA-256 to equal the approved staged file.
4. Fail on a wrong signature, a missing entry, two paths that differ only in case or slash direction, or a hash mismatch.

Record the SHA-256 of the mounted PBO at every launch. Without it, no crash analysis can prove which file the game loaded.

## Compare code bytes, not fault addresses

The RPT's `Fault address` does not identify a crash site: address space randomisation moves the module base, so the same code prints different addresses on different runs. The site is identified by `Prev. code bytes` and `Fault code bytes` (16 bytes each) together with the engine `Version`.

On a test coupe, six `C0000374` crashes printed two different addresses but had identical code bytes and identical low 16 bits: one code site in one build. The same comparison showed the crash appeared with both MLOD and ODOL models, so the model format was not the cause.

Report "same detection signature" or "different detection signature", never "same bug". `C0000374` is heap corruption detected when memory is freed, not where the bad write happened, so an identical signature does not prove an identical cause.

## Check `config.cpp` syntax offline

`-packonly` does not rapify, so the config ships as text and the game's parser is the first to read it. The script validator does not check config syntax either. Use two checks:

- `/dayz-lint` rule `config-syntax` (`skills/dayz-lint/SKILL.md`) catches unbalanced braces, a missing `;` or `};`, an array without `[]`, and a missing `;` between array items. It does not resolve inheritance.
- `CfgConvert` parses the whole file as the engine does and resolves every base class, including nested `class X: X` chains such as `class SimulationModule: SimulationModule` (`P:\DZ\vehicles\wheeled\config.cpp:1371`) with `class Axles: Axles` inside it (`:1431`).

```bat
"<DayZ Tools>\Bin\CfgConvert\CfgConvert.exe" -bin -dst <tmp>.bin <config.cpp>
```

A pass means nothing until two planted errors fail it:

| Planted error | What `CfgConvert` reports |
|---|---|
| Remove the brace that closes `CfgVehicles` | `line NNN: /CfgVehicles/: Missing '}'` |
| Misspell a base class inside the new block | `Undefined base class 'ClutchTypo'` |

The second one proves the nested `class X: X` chains are resolved, which is the real risk when you write variant classes. Dropping the `;` after a closing `}` is not a usable planted error: `CfgConvert` accepts it.
