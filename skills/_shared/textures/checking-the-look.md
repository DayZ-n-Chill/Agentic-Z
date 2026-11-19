# Checking the look

What to check before handing texture and material work over, then what to ask the user to look at once the files are written. The asset specialist cannot see the screen, so it hands the user the Object Builder and in-game lists in its report and asks what they saw. It never launches Object Builder or DayZ itself.

## Before handing over

Each line points at the file that explains it; this section states no game facts of its own.

**Inputs**

- The mod's root folder and its packed paths are known.
- The model selections involved are checked in the model.
- The intended behaviour is named: texture only, surface response, damage look, emissive or glass, penetration, Multi, or the MatPBR route.
- A close vanilla `.rvmat` and `config.cpp` have been read.

**Texture files**

- Every path the game reads ends in `.paa` and is an in-game path (`dz\...` or the mod's prefix), never a local disk path.
- Source files (`.png`, `.tga`, `.xcf`, `.psd`, `.blend`, `.sbsar`) are kept out of the packed paths, or in a source folder the build leaves out, and none is named in a `.rvmat` or in config.
- The orientation of the `_nohq` source is known, and an OpenGL (Y+) source was converted to DirectX (Y-). A source that does not state its convention got a candidate from `normal_convention.py` and the candidate was confirmed another way; exit code 0 alone is not proof (`normal-maps.md`).
- How the written `_nohq` is packed was read from the file or from an ImageToPAA round trip, not assumed from the suffix (`normal-maps.md`, "Reading a packed `_nohq`"). Amplitude and relief were measured on the decoded PNG.
- If the normal was built from albedo brightness: a known dark seam was swept and reads as a valley, not a ridge, and the gain was calibrated on this atlas (`normal-maps.md`).
- The `_smdi` channels are intended, and the `_smdi`, `_as` and `_co` levels were compared with a vanilla asset of the same family whose material constants match (`smdi-and-levels.md`).
- An `_as` was checked per channel (`baked-atlas-checks.md`).
- Alpha is used on purpose, in a `_ca` or a see-through material.

**`.rvmat`**

- `PixelShaderID` and `VertexShaderID` are present and are the pair the route calls for (`rvmat-stages.md`).
- A Super material has the stages its kind of asset expects, or leaves one out on purpose (`rvmat-cookbook.md`).
- Damage and destruct materials carry a wear macro in Stage3 when a visible damage look is expected.
- An emissive material uses checked `emmisive[]` values and has an off material where one is needed.
- A glass or chrome material was cloned from a similar vanilla one.
- A penetration material has `surfaceInfo` naming a `.bisurf` and is assigned to the collision LOD faces.
- A Multi material has its Stage4 mask on the UV set that covers the mesh once (`multi-materials.md`).
- A borrowed vanilla material had its Stage4, Stage5 and every `uvSource` checked for the donor's baked data (`baked-atlas-checks.md`).
- `rvmat_lint.py` (shipped with `/dayz-pack-texture`, usage in `rvmat-cookbook.md`) ran on every new or changed `.rvmat`. `/dayz-p3d-audit --rvmat` and `/dayz-lint` add their own checks before a build.

**MatPBR and `.emat`** (only for a material on that route; the checks are in `matpbr-emat.md`)

- The `.emat` and its stub `.rvmat` share a file name, every map is a Workbench resource ID, the normal map was not DXT compressed, and the asset needs neither `healthLevels[]` damage looks nor terrain.

**Config** (`config-wiring.md`)

- The names in `hiddenSelections[]` match the model, and `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` follow their order.
- No selection that a script repaints has an empty texture in config (`runtime-material-swaps.md`).
- `healthLevels[]` names the normal, damage and destruct materials where a damage look is wanted.
- Vehicle light on and off keys are cloned from the same vehicle family.

**Questions to ask before writing final files**, when the answer is unknown: the mod's root folder and packed path; the exact selections that get a texture or material swap; whether the model has one UV set or two; whether the texture is cosmetic only or must change surface, damage, glass, light or penetration behaviour; whether the result is a change to the mod or a standalone reference.

## In Object Builder

This part is **tool knowledge**: it describes Object Builder, not a vanilla file. The user opens only the mod's own MLOD `.p3d`, for example with `/dayz-launch-objectbuilder`. Vanilla `.p3d` files under `P:\DZ\` are binarized and stay closed.

1. **Faces carry the right files.** Select the faces of each part and open Face Properties. The texture field shows the `_co` or `_ca` and the material field shows the `.rvmat`, both as in-game paths that start with the mod's `$PBOPREFIX$` (`MyMod\data\vest_co.paa`). A path starting with `P:\` breaks once the mod is packed.
2. **The color sits where it should.** In the textured 3D view, check that the `_co` is not stretched, that seams line up, and that no face shows the wrong part of the texture.
3. **Hidden selection parts.** Faces in a hidden selection get their texture from `hiddenSelectionsTextures[]` in game, so Object Builder may show a different texture there. Judge those parts in game.
4. **Glass and frame are separate.** Glass faces use the glass material and frame faces the frame material. If one material covers both, ask dayz-object-builder for separate selections.

The Object Builder view is a preview. Judge highlights, reflections and damage looks in game. `/dayz-p3d-audit` also reports `P:\` paths in the model's `.rvmat` files.

## In game

Once the user has packed the mod with `/dayz-build-pbo` and started it with `/dayz-launch-test`, ask them to spawn the item and check:

| Look at | Good | If not |
|---|---|---|
| The item on the ground, in hands, worn (clothing) and in the inventory preview | Same textures everywhere | A view with the wrong texture uses another model or hidden selection; send it to dayz-config-specialist or dayz-object-builder |
| Surface detail as the light moves over it | Bumps and seams look raised | Flat: `Stage1` path wrong or still the placeholder. Pushed in: the normal map's green channel is likely flipped (**tool knowledge**; `_nohq` is DirectX style, see `suffixes-and-sizes.md`); the user exports it again |
| Highlights in sun and in shade | Cloth stays matte, metal shines, glass glints | Change `_smdi`, `specular[]` and `specularPower` toward the values in `surface-recipes.md` |
| Glass | See-through, with the frame behind it visible | Opaque: the color texture is `_co`, or its alpha is white (`surface-recipes.md`) |
| Each health level (the user damages the item) | Worn, then damaged, then ruined look | No change: `healthLevels[]` points every level at one material (`rvmat-stages.md`) |
| Thermal optics, only when a `StageTI` was written | The thermal texture shows | Check the `_ti_ca` path |

Three notes for reading what the user reports:

- **Checking the normal direction needs the right light.** Flipping the green channel changes the shading only for light that crosses the texture's V axis, so a groove that runs along U must be lit from the top or the bottom of the texture, not along it. Two renders that look the same prove nothing. `/dayz-pack-texture` ships a script that measures a source map's convention before it is packed (`normal-maps.md`).
- **A material set from script is judged by the frame.** `GetObjectMaterial` was seen returning the script's material while the item rendered vanilla, and an empty string while the override was visible (`runtime-material-swaps.md`). Ask the user what they see; do not accept a log line as proof.
- **A part that never appears** can be a hidden selection whose config texture is an empty string, which hides it on purpose (`runtime-material-swaps.md`).

A missing texture or material is also written to the client log. Ask the user to check the newest log in `.server\!ClientDiagLogs\` for lines naming the mod's `.paa` or `.rvmat` files, or to run `/dayz-gate ingame`, which reads those logs for them.
