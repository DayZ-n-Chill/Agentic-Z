# AI generated meshes

How to take a mesh from an image or text to 3D generator to a static DayZ prop or item: cleanup, low poly retopology, UVs, the normal bake, the PBR maps and the handoff to `.p3d`, `.paa` and `.rvmat`. The model pack (`lods.md`), the texture pack (`_shared/textures/README.md`) and `/dayz-build-pbo` do the rest; this file only gets the mesh to them.

Use it for props, items and objects with mechanical parts: weapons, containers, gear, world props. Do not use it for a humanoid character or for anything whose main need is skeletal animation; see "Characters and infected" below.

Tool names and settings in this file are tool knowledge, not facts from a vanilla file. A tool marked "unverified" has not been tested in this pipeline yet: try it on one model before relying on it.

## From idea to `.p3d`

1. **Reference image.** A clean image with a white background, lit from all sides, with no other objects. Remove the background before any image to 3D step. Reference tools (unverified): Nano Banana, Krea, 3D AI Studio.
2. **Generate the mesh.** Geometry matters more than texture, because the texture is redone for DayZ. Always set a polygon limit; without one every generator writes millions of triangles. Local Hunyuan 2.1 takes `target_face_number`. Tripo and 3D AI Studio are paid routes; ask them for low poly with polygon control. No skill in this repo drives either.
3. **Clean and retopologize.** Import the GLB into Blender (`blender-assembly.md`). Reduce it to a low poly closed mesh with Retopoflow or Quad Remesher, or with a generator's own auto retopology followed by a manual cleanup.
4. **UVs and the normal bake.** This makes the `_nohq`. In Blender Cycles use selected to active (select the high mesh, then the low one so it is active), bake type Normal, Non-Color, margin 8 px, and tune Extrusion and Max Ray Distance. DayZ's `_nohq` is DirectX style (green down), so invert the green channel on export (`blender-assembly.md`). That convention was calibrated against a vanilla `_nohq`; it is not checked on `P:\`.
5. **Texture over the UVs.** Modddif (unverified: whether it keeps the UVs and whether its maps work) writes color to `_co` and normal to `_nohq`, and no roughness or metallic. Make the `_smdi` separately, by hand in Blender or by repacking Tripo's ORM map. Never remesh a mesh that is already retopologized.
6. **Hand off to DayZ.** Write the MLOD `.p3d` with the Arma 3 Object Builder add-on for Blender, which writes LODs, proxies and named selections natively, or with py3d (`scripts/tools/py3d/`, `py3d-generation.md`). Repack roughness and metallic into the `_smdi` with the SubstanceToArma preset (R white, G metal, B inverted roughness); the vanilla channel layout is in `_shared/textures/suffixes-and-sizes.md`. Convert to `.paa` with `/dayz-pack-texture` or TexView, write the `.rvmat` and binarize. Preview with the 3D viewer (`tools-3d-viewer.md`) and test in game with `/dayz-launch-test`. Read "Writing the MLOD" below first.

## What a generator never gives you

- A generated mesh is a high poly blockout, never a finished asset. It has open edges and ngons, while every collision part (the `ComponentNN` selections of Geometry, Fire Geometry and View Geometry) must be closed and convex (`lods.md`). Always retopologize by hand, unwrap, bake and check it in Object Builder before it becomes a `.p3d`. Auto retopology alone is not enough, and the Binarize vertex limit still applies (`lods.md`, "Limits").
- Never trust a vision model for placement, rotation or scale. It turns parts by 90 degrees and does not move them. Use numeric checks (`verify_bounds`) and a comparison with the reference image (`blender-visual-review.md`).
- A texture tool must paint over the existing UVs. Check this on any new tool before it joins the pipeline.
- A DayZ vertex is a point, a normal and a UV, counted per LOD. Budget vertices, not faces; shared normals lower the count.

## Tools

| Tool | Role | Status |
|---|---|---|
| Hunyuan 2.1, local | High poly blockout with polygon control; the default for organic shapes and concept work | Works; no skill drives it |
| Hunyuan 3.1 Pro (fal) | Fine hard surface | Preferred for hard surface |
| Rodin 2.5 (fal, Hyper3D) | Organic full bodies, mesh editing, parts, PBR | Preferred for full bodies |
| Tripo 2.5, 3D AI Studio | Direct low poly mesh (92k triangles in one comparison), retopology, PBR | Works; Smart Low-Poly is paid |
| Blender with Retopoflow or Quad Remesher (or ZRemesher, InstaLOD) | Closed retopology, UVs, bake | Always needed |
| Arma 3 Object Builder add-on for Blender | Native MLOD: LODs, proxies, named selections, RVMAT, RTM | In common use for DayZ |
| Modddif | `_co` and `_nohq` over existing UVs | Free; no roughness or metallic |
| 3D AI Studio or Meshy Texture | Full PBR over existing UVs | Works; repack to `_smdi` |
| Sloyd | Template props (barrels, crates, weapons) with quads, UVs and LODs | Less cleanup than a generator for simple props |
| Mixamo, AccuRig, Cascadeur | Humanoid rig and animation | Little use for props |

Still to test: the full chain from bake to `_nohq.paa` in game; Modddif on prepared UVs; decimating to several LOD targets through the Blender MCP. Ask the user before any visual decimation; by default the user does it by hand.

## Characters and infected

For a humanoid or a creature, reskin a vanilla one instead of building from scratch. A custom infected inherits `ZombieMaleBase` (`P:\DZ\characters\zombies\config.cpp:549`), whose parent `ZombieBase` carries the `enfanimsys` block that names the mesh, the animation graph and the skeleton (`:71`). The skeleton, vanilla animations and AI come by inheritance; the real work is rigging the mesh to the vanilla bones. A giant infected build named that skeleton `OFP2_ManSkeleton` in its `model.cfg`; that name is not in the unpacked text files on `P:\`. The full recipe is in `_shared/ai/custom-infected.md` and `_shared/wearables/references/body-rigging.md`.

Bake the size into the mesh. `SetScale` is declared on `IEntity` (`P:\scripts\1_core\proto\enentity.c:448`) and vanilla calls it on the static objects its spawner places (`P:\scripts\3_game\objectspawner.c:61`). Reported, not checked on `P:\`: it does not hold on entities at run time, and collision does not follow it.

## Preparing the reference

Prepare the image with rembg, autocrop, a white background, a margin and filled transparent holes; use the full body when the output needs it. After generating, read `trimesh.extents`: an axis near zero is a flat failure even when the render looks right.

On Linux the tools for packing, signing, binarizing, Object Builder and TexView under Proton are in `_shared/linux-proton.md`. To end with a mod that builds and loads, follow `skills/dayz-launch-test/references/mod-loop.md` with `/dayz-lint`, `/dayz-build-pbo` and `/dayz-launch-test`.

## Writing the MLOD

A generated mesh reaches the MLOD as Blender geometry, so it takes the Blender rule of `axes-and-winding.md`: the reflection `(x,y,z)` to `(x,z,y)`, face order kept, normals negated (`py3d.blender_to_dayz`), plus a chirality check. Do not reverse the visual faces unless that source was measured to need it. Read the result with `/dayz-p3d-audit`.

Do not judge this route by the older census threshold (95% or more negative reads `SOLID`). Measured offline on MLODs rebuilt by `scripts/tools/py3d/tests/test_s7_blender_to_dayz.py`, with the census `dot(cross(v1-v0, v2-v0), mean_stored_normal)` and faces under `1e-9` left out:

| Export | Census | In game |
|---|---|---|
| The reflection, face order kept, normals negated | 0% negative, read as `INVERTED` | Solid and reads correctly |
| The same with every face reversed | 100% negative, `SOLID` | Inside out |
| The older recipe: rotation, faces reversed, normals outward | 100% negative, `SOLID` | Mirrored |
