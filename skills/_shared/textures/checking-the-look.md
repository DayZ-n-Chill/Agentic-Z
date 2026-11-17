# Checking the look

What to ask the user to look at once textures and materials are written. The asset specialist cannot see the screen, so it hands the user this list in its report and asks what they saw. It never launches Object Builder or DayZ itself.

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

- **Checking the normal direction needs the right light.** Flipping the green channel changes the shading only for light that crosses the texture's V axis, so a groove that runs along U must be lit from the top or the bottom of the texture, not along it. Two renders that look the same prove nothing. `/dayz-texture-pipeline` has a script that measures a source map's convention before it is packed.
- **A material set from script is judged by the frame.** `GetObjectMaterial` was seen returning the script's material while the item rendered vanilla, and an empty string while the override was visible (`runtime-material-swaps.md`). Ask the user what they see; do not accept a log line as proof.
- **A part that never appears** can be a hidden selection whose config texture is an empty string, which hides it on purpose (`runtime-material-swaps.md`).

A missing texture or material is also written to the client log. Ask the user to check the newest log in `.server\!ClientDiagLogs\` for lines naming the mod's `.paa` or `.rvmat` files, or to run `/dayz-gate ingame`, which reads those logs for them.
