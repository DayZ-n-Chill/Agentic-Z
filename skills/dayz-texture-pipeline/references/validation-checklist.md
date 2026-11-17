# Validation checklist

The checks to run before handing texture and material work over: inputs, texture files, the `.rvmat`, the MatPBR route, config, the linter, and what to look at in game.

How to read it: each line points at the reference that explains it. This file states no game facts of its own.

## Inputs

- The mod's root folder and its packed paths are known.
- The model selections involved are checked in the model.
- The intended behaviour is named: texture only, surface response, damage look, emissive or glass, penetration, Multi, or the MatPBR route.
- A close vanilla `.rvmat` and `config.cpp` have been read.

## Texture files

- Every path the game reads ends in `.paa`.
- The orientation of the `_nohq` source is known, and an OpenGL (Y+) source was converted to DirectX (Y-). A source that does not state its convention got a candidate from `normal_convention.py` (exit code 0: the albedo and curl readings agree and stay stable across the map's blocks; `INCONCLUSIVE` is not an answer), and the candidate was confirmed another way: the baker's export setting, or a raking light render where a known groove reads as a groove. For that render the light crosses V (it is not parallel to U), the groove runs along U, and the copy with the green inverted reads it as a ridge; two renders that look the same are inconclusive. Exit code 0 alone is not proof (`map-conventions.md`).
- How the written `_nohq` is packed was read from the file (DXT5, raw red at 0, the `SWIZ` tag `05 04 02 03`) or from an ImageToPAA round trip, not assumed from the suffix. Amplitude and relief were measured on the decoded PNG.
- If the normal was built from albedo brightness: a known dark seam was swept and reads as a valley, not a ridge, and the Sobel gain was calibrated on this atlas, not copied from another map.
- The `_smdi` channels are intended: G is specular strength and B is gloss. R is forced to white by the conversion.
- The `_smdi`, `_as` and `_co` levels were compared with a vanilla asset of the same family whose material constants match (`map-conventions.md`).
- An `_as` was checked per channel: the shadow is in green (`baked-atlas-to-paa.md`).
- Alpha is used on purpose, in a `_ca` or a see-through material.
- No source file (`.png`, `.tga`, `.psd`) is named in a `.rvmat` or in config.

## RVMAT

- `PixelShaderID` and `VertexShaderID` are present and are the pair the route calls for.
- A Super material has Stage1, Stage3, Stage5, Stage6 and Stage7 as its kind of asset expects, or leaves one out on purpose.
- Damage and destruct materials carry a wear macro in Stage3 when a visible damage look is expected.
- An emissive material uses checked `emmisive[]` values and has an off material where one is needed.
- A glass or chrome material was cloned from a similar vanilla one.
- A penetration material has `surfaceInfo` naming a `.bisurf` and is assigned to the collision LOD faces.
- A Multi material has its Stage4 mask on the UV set that covers the mesh once (usually `tex1`, or `tex` when the tiling textures read `tex1`).
- A borrowed vanilla material had its Stage4, Stage5 and every `uvSource` checked for the donor's baked data (`baked-atlas-to-paa.md`).

## MatPBR and `.emat`

Only for a material on the route in `matpbr-emat-pipeline.md`. Skip it for Super and Multi.

- The `.emat` and its `.rvmat` have the same file name and differ only in extension.
- The `.rvmat` is a stub: the two shader IDs and no stages.
- The `.emat` holds one `MatPBR { ... }` block with `AlbedoMap`, `NormalMap`, `RoughnessMap`, `MetalnessMap` and `AOMap`, and `EnvReflMap ... cube` unless the material is meant not to reflect.
- Every map in the `.emat` is named by a resource ID in braces, not a plain path, which shows it was imported in Workbench and not typed by hand.
- The environment cube map source is exactly 256 x 128 before the EDDS import.
- The normal map was not DXT compressed; every other map was.
- If the asset needs `healthLevels[]` damage looks, or is terrain, MatPBR is not used for it.

## Config

- The names in `hiddenSelections[]` match the model.
- `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` are in the order of the selections.
- No selection that a script repaints has an empty texture in config (`_shared/textures/runtime-material-swaps.md`).
- `healthLevels[]` names the normal, damage and destruct materials where a damage look is wanted.
- Vehicle light on and off keys are cloned from the same vehicle family.
- No local disk path appears in config.

## Tools

Run the linter on each new or changed `.rvmat`:

```cmd
python "<skill-dir>\scripts\rvmat_lint.py" path\to\material.rvmat --pdrive-root P:\
python "<skill-dir>\scripts\rvmat_lint.py" path\to\material.rvmat --warnings-as-errors
python "<skill-dir>\scripts\rvmat_lint.py" path\to\material.rvmat --json
```

It reports differences that depend on the kind of asset as warnings, not errors. `/dayz-p3d-audit --rvmat` adds the check for `P:\` paths inside a `.rvmat`, and `/dayz-lint` checks the mod's file references before a build.

## In game

Hand the user the list in `_shared/textures/checking-the-look.md`, and add what applies:

- Look at the asset in daylight and in shadow.
- Check the normal direction under a strong light that crosses V.
- Check wet and bright lighting for a highlight that is too strong.
- Damage the item, or force its health level, where it has damage looks.
- For lights, switch them on and off.
- For penetration surfaces, test the bullet impact sound and effect.
- For Multi, check each mask color and the blend borders.
- Judge a material applied from script by the frame, never by `GetObjectMaterial`.
