# AI generation to DayZ

A front end that uses AI generation (image or text to 3D) to get from an idea to a static DayZ prop or item: cleanup, low-poly manifold retopology, UVs, the high-to-low normal bake, PBR maps and the handoff to `.p3d`, `.paa` and `.rvmat`. It picks the generator and the front-end gates and feeds the model and texture packs and `/dayz-build-pbo`; it does not replace them. It is a workflow scaffold: the structure and the handoffs are verified, while the specific tool picks are unverified and marked "validate" until a test confirms them.

**Status.** Tool names, versions and settings marked "validate" are unverified: check one against the actual tool before trusting it. Nothing in this file about tools or measured results can be checked against the vanilla files on `P:\` (not yet checked on `P:\`). The vanilla facts, the infected class chain and `SetScale`, are cited where they appear.

## When to use

- The user wants an object, prop or item for a DayZ mod and does not want to, or cannot, model it by hand.
- A reference image exists, or one can be generated.
- The target is a static prop or item, or one with mechanical parts: weapons, containers, gear, world props.
- Do not use it for humanoid characters, or when the main need is skeletal animation. This pipeline does not cover DayZ's config-driven animation. For characters and infected see "Characters and infected" below.

## Pipeline (idea to .p3d)

1. **Reference.** A clean image: white background, lit from all sides, no extra objects. Tools (validate): Nano Banana, Krea, 3D AI Studio. Always remove the background before image to 3D.
2. **Generate the mesh.** Geometry matters more than texture, because the texture is remade for DayZ. Routes known to be available:
   - **Hunyuan 2.1, local** (RTX 3090): control `target_face_number`. No skill in this repo automates it.
   - **Tripo or 3D AI Studio** (paid access): a paid route to a mesh; ask for low poly with polygon control. No skill in this repo automates it.
   - Control the polygon count during generation. Without a limit, every tool produces millions of triangles.
3. **Clean and retopologize.** Import the GLB into Blender (`blender-assembly.md`). Reduce it to a low-poly manifold mesh with Retopoflow (manual) or Quad Remesher, or with an AI auto-retopo (Tripo, Rodin, Hunyuan) followed by a cleanup that is not optional.
4. **UVs and the normal bake (high to low).** This step makes the `_nohq`. Blender Cycles, selected to active (select the high mesh first, then the low, so the low mesh is the active one), Bake Type Normal, Non-Color, margin 8 px, and tune Extrusion and Max Ray Distance. DayZ's `_nohq` is DirectX style (Y-), so invert the green channel on export (Rule 11 of `blender-assembly.md`): the convention was measured by calibration against a vanilla `_nohq`, not checked on `P:\`.
5. **Texture on the UVs.** Tool: Modddif (validate; backlog item 3: whether it respects the UVs and whether its maps are usable is unverified). Color goes to `_co` and normal to `_nohq`; it does not output roughness or metallic. The `_smdi` is made separately (manual PBR in Blender, or a repack of Tripo's ORM map). Do not remesh a mesh that has already been retopologized.
6. **Handoff to DayZ.** Assemble the MLOD `.p3d`. The recommended option is the Arma 3 Object Builder add-on for Blender, which is in common use for DayZ and which writes LODs, proxies and named selections natively; py3d (`scripts/tools/py3d/`, notes in `skills/_shared/py3d-mlod-notes.md`) is the other. For the `_smdi`, repack roughness and metallic with the SubstanceToArma preset (R = white, G = metal, B = roughness inverted); the channel layout vanilla uses is in `skills/_shared/textures/suffixes-and-sizes.md`. Convert to `.paa` with `/dayz-pack-texture` (ImageToPAA) or TexView, build the `.rvmat` and binarize. Continue with the texture pack (`skills/_shared/textures/README.md`), the model pack (`lods.md`) and `/dayz-build-pbo`. Preview with the 3D viewer tool (`tools-3d-viewer.md`). Validate in game with `/dayz-launch-test`. Before writing the MLOD, read "Writing the MLOD" below.

## Hard rules (the pitfalls that break DayZ)

- **AI output is only a high-poly blockout. It does not produce an asset that is ready for DayZ.** AI generation plus auto-retopo produces non-manifold geometry and ngons, and the collision parts (the `ComponentNN` selections of the Geometry, Fire Geometry and View Geometry LODs) must be closed and convex (`lods.md`); the visual LODs have no convexity rule. AI output always goes through manual retopology (Retopoflow or Quad Remesher), UVs, the bake and validation in Object Builder before it becomes a `.p3d`. AI auto-retopo alone is not sufficient. This ties in with the binarize vertex limit (`lods.md`, "Limits").
- **Never trust AI vision for the placement, orientation or scale of a `.p3d`.** It is the documented weak link: it rotates by 90 degrees and does not reposition. Use numeric checks (`verify_bounds`) and a diff against the reference image (`blender-visual-review.md`).
- A texture tool must texture over the existing UVs, not remesh a model that has already been retopologized. Verify this on any new tool before putting it into the pipeline.
- DayZ vertices are point × normal × uv, per LOD. The budget is not "faces"; shared normals reduce the count.
- Tool names, versions and settings marked "validate" are unverified. Confirm them against the actual tool before writing them down as truth.

## Tool shortlist

| Tool | Role | Status |
|---|---|---|
| Hunyuan 2.1 (local) | Generate the high-poly blockout, with polygon control | Available; no skill in this repo automates it |
| Tripo / 3D AI Studio | Generate a low-poly mesh, retopo, PBR | Access confirmed; Smart Low-Poly is behind a paywall |
| Blender with Retopoflow or Quad Remesher (or ZRemesher, InstaLOD) | Manifold retopology, UVs, bake | Core and unavoidable: AI does not replace it |
| Arma 3 Object Builder (Blender add-on) | Native MLOD `.p3d`: LODs, proxies, named selections, RVMAT, RTM | In common use for DayZ; replaces or complements py3d |
| Modddif (formerly "Modif" or "Motif") | Color (`_co`) and normal (`_nohq`) over existing UVs | Free; no roughness or metallic |
| 3D AI Studio / Meshy Texture | Full PBR (albedo, normal, roughness, metallic) over existing UVs | Confirmed; repack to `_smdi` |
| Sloyd (parametric) | Templated props (barrels, crates, weapons) with quads, UVs and LODs out of the box | Less cleanup than AI for simple props |
| Rodin (Hyper3D) | Mesh editing, parts, PBR | Access confirmed |
| AI animation (Mixamo, AccuRig, Cascadeur and others) | Humanoid rig and animation | Low value for DayZ props |

## Validation backlog (harden this file as items close)

1. Done. A/B generation of the same DayZ prop with local Hunyuan 2.1 and with Tripo, for geometry and polygon control: settled by a 2026-06-10 comparison on an Mk 47 model and a 2026-06-23 full-body case (tool results, not checked on `P:\`). Local 2.1 wins as the default (free, organic shapes, concept iteration); fal Hunyuan 3.1 Pro for fine hard surface; fal Rodin 2.5 for organic full bodies; Tripo 2.5 gave an efficient direct low-poly mesh (92k triangles) but was not the pick.
2. The high-to-low normal bake, then export, then `_nohq.paa`, then validation in game.
3. Modddif on prepared UVs: does it respect the UVs, and do its maps work as `_co` and `_nohq`?
4. A LOD batch through the Blender MCP: a prompt that decimates to N targets and downscales the textures, as a LOD prototype. Any visual decimation needs the user's approval first: ask before, and the default is that the user does it by hand.

When an item is confirmed, replace its "validate" mark with the verified data and where it was measured.

## Characters and infected

For a humanoid character or a creature (a zombie, a DayZ infected), do not author from scratch: reskin a vanilla one. A custom infected inherits `ZombieMaleBase` (`P:\DZ\characters\zombies\config.cpp:549`), whose parent `ZombieBase` carries the `enfanimsys` block (`P:\DZ\characters\zombies\config.cpp:71`) that names the mesh object, the animation graph and the skeleton, so the skeleton, the vanilla animations and the AI come free by inheritance. The real cost is rigging the mesh to the vanilla bones. The giant infected build named that skeleton `OFP2_ManSkeleton` in its `model.cfg`; that name is not in the unpacked text files on `P:\` (not yet checked on `P:\`). The full recipe is in `skills/_shared/ai/custom-infected.md` and `skills/_shared/wearables/references/body-rigging.md`.

Bake the size into the mesh. `SetScale` is declared on `IEntity` (`P:\scripts\1_core\proto\enentity.c:448`) and vanilla calls it on the static objects its object spawner places (`P:\scripts\3_game\objectspawner.c:61`); it is reported not to hold on entities at run time, and the collision is reported not to follow it (reported behaviour, not checked on `P:\`).

Organic full-body mesh generation goes through fal Rodin.

## Reference preparation and the planar check

- Prepare the reference with rembg, autocrop, a white background, a margin and filled transparent holes; use the full body when the output needs it. After generating, validate `trimesh.extents`: an axis near zero is a planar failure even when the render looks plausible.

## On Linux, and building the mod

On Linux the tool matrix (dayzmake for packing, signing and binarizing, Object Builder and TexView under Proton) is in `_shared/linux-proton.md`. To end in a mod that builds, loads and ships, follow `skills/dayz-launch-test/references/mod-loop.md` and use `/dayz-lint`, `/dayz-build-pbo` and `/dayz-launch-test`.

## Writing the MLOD

A generated mesh reaches the MLOD as Blender geometry (steps 3 and 4), so it takes the Blender rule of `axes-and-winding.md`: the det = -1 map `(x,y,z) -> (x,z,y)`, face order kept, normals negated (`py3d.blender_to_dayz`), plus a chirality check. Do not reverse the visual faces unless that source's own lineage was measured to need it. Read the result with `/dayz-p3d-audit`, not with a census threshold borrowed from another pipeline.

A census of `dot(cross(v1-v0, v2-v0), mean_stored_normal)` (faces with `abs(dot) < 1e-9` left out) on the three ways one model was exported shows why the older thresholds (at least 95% negative reads `SOLID`) mislead on this route. Measured offline on 2026-10-03, on the MLODs of the in-game test of that rule, rebuilt byte for byte by `scripts/tools/py3d/tests/test_s7_blender_to_dayz.py`:

| Export | Census | In game |
|---|---|---|
| The reflection (det = -1 map, face order kept, normals negated) | 0% negative, `INVERTED` by those thresholds | Rendered solid and read correctly |
| The same export with every face reversed (winding outward) | 100% negative, `SOLID` | Inside out |
| The older recipe: det = +1 map, faces reversed, normals outward | 100% negative, `SOLID` | A mirror |
