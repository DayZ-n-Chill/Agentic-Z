---
name: ai-3d-to-dayz
description: "Front end for making a DayZ prop, item or other static asset with AI generation: image or text to 3D, cleanup and low-poly manifold retopology, UVs, the high-to-low normal bake, PBR maps and the handoff to .p3d, .paa and .rvmat. Use when the user asks to generate a 3D object or model for DayZ, create a prop from scratch, go from an image to 3D, convert an AI-made GLB into a .p3d, wants a realistic low-poly asset, or names Hunyuan, Tripo or Rodin (Spanish: 'generar un objeto 3D para DayZ', 'generar un modelo 3D para DayZ', 'crear un prop desde cero', 'convertir un GLB de IA en .p3d'). It picks the generator and the front-end gates and feeds dayz-model-pipeline, the texture pipeline and /dayz-build-pbo; it does not replace them. Not for humanoids or animation."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# AI 3D to DayZ

A front end that uses AI generation to get from an idea to a 3D asset that is ready for DayZ. It is a workflow scaffold: the structure and the handoffs are verified, while the specific tool picks are unverified and marked "validate" until a test confirms them.

Follow `skills/_shared/dayz-conventions.md`. This skill runs no scripts, so there is no preflight gate.

**Status.** Tool names, versions and settings marked "validate" are unverified: check one against the actual tool before trusting it. Nothing in this file about tools or measured results can be checked against the vanilla files on `P:\` (not yet checked on `P:\`). The vanilla facts, the infected class chain and `SetScale`, are cited where they appear.

## What to read

| Question | Read |
|---|---|
| Which coordinate map, face order and normals to use when the mesh is written to an MLOD `.p3d`, and how to read a winding census | `<skill-dir>\references\mlod-winding.md` |

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
3. **Clean and retopologize.** Import the GLB into Blender (use `blender-assembly`). Reduce it to a low-poly manifold mesh with Retopoflow (manual) or Quad Remesher, or with an AI auto-retopo (Tripo, Rodin, Hunyuan) followed by a cleanup that is not optional.
4. **UVs and the normal bake (high to low).** This step makes the `_nohq`. Blender Cycles, selected to active (select the high mesh first, then the low, so the low mesh is the active one), Bake Type Normal, Non-Color, margin 8 px, and tune Extrusion and Max Ray Distance. DayZ's `_nohq` is DirectX style (Y-), so invert the green channel on export (Rule 11 of `blender-assembly`): the convention was measured by calibration against a vanilla `_nohq`, not checked on `P:\`.
5. **Texture on the UVs.** Tool: Modddif (validate; backlog item 3: whether it respects the UVs and whether its maps are usable is unverified). Color goes to `_co` and normal to `_nohq`; it does not output roughness or metallic. The `_smdi` is made separately (manual PBR in Blender, or a repack of Tripo's ORM map). Do not remesh a mesh that has already been retopologized.
6. **Handoff to DayZ.** Assemble the MLOD `.p3d`. The recommended option is the Arma 3 Object Builder add-on for Blender, which is in common use for DayZ and which writes LODs, proxies and named selections natively; py3d (`scripts/tools/py3d/`, notes in `skills/_shared/py3d-mlod-notes.md`) is the other. For the `_smdi`, repack roughness and metallic with the SubstanceToArma preset (R = white, G = metal, B = roughness inverted); the channel layout vanilla uses is in `skills/_shared/textures/suffixes-and-sizes.md`. Convert to `.paa` with `/dayz-pack-texture` (ImageToPAA) or TexView, build the `.rvmat` and binarize. Continue with `dayz-texture-pipeline`, `dayz-model-pipeline` and `/dayz-build-pbo`. Preview with the `dayz-3d-viewer` skill. Validate in game with `/dayz-launch-test`. Before writing the MLOD, read `references/mlod-winding.md`.

## Hard rules (the pitfalls that break DayZ)

- **AI output is only a high-poly blockout. It does not produce an asset that is ready for DayZ.** The Bohemia Interactive and Enfusion pipeline needs manifold, closed, convex geometry, and its Model Quality Assurance marks non-manifold, ngon and non-convex geometry as defects, which is exactly what AI generation plus auto-retopo produces. AI output always goes through manual retopology (Retopoflow or Quad Remesher), UVs, the bake and validation in Object Builder before it becomes a `.p3d`. AI auto-retopo alone is not sufficient. This ties in with the binarize vertex limit, covered in `dayz-model-pipeline`.
- **Never trust AI vision for the placement, orientation or scale of a `.p3d`.** It is the documented weak link: it rotates by 90 degrees and does not reposition. Use numeric checks (`verify_bounds`) and a diff against the reference image (`blender-visual-review`).
- A texture tool must texture over the existing UVs, not remesh a model that has already been retopologized. Verify this on any new tool before putting it into the pipeline.
- DayZ vertices are point × normal × uv, per LOD. The budget is not "faces"; shared normals reduce the count.
- Tool names, versions and settings marked "validate" are unverified. Confirm them against the actual tool before writing them down as truth.

## Tool shortlist

| Tool | Role | Status |
|---|---|---|
| Hunyuan 2.1 (local) | Generate the high-poly blockout, with polygon control | Available; no skill in this repo automates it |
| Tripo / 3D AI Studio | Generate a low-poly mesh, retopo, PBR | Access confirmed; ranked first, at 71.8%, in a third-party low-poly comparison (not checked here); Smart Low-Poly is behind a paywall |
| Blender with Retopoflow or Quad Remesher (or ZRemesher, InstaLOD) | Manifold retopology, UVs, bake | Core and unavoidable: AI does not replace it |
| Arma 3 Object Builder (Blender add-on) | Native MLOD `.p3d`: LODs, proxies, named selections, RVMAT, RTM | In common use for DayZ, and a dependency of DayZ-LOD-Tools; replaces or complements py3d |
| Modddif (formerly "Modif" or "Motif") | Color (`_co`) and normal (`_nohq`) over existing UVs | Free; no roughness or metallic |
| 3D AI Studio / Meshy Texture | Full PBR (albedo, normal, roughness, metallic) over existing UVs | Confirmed; repack to `_smdi` |
| Sloyd (parametric) | Templated props (barrels, crates, weapons) with quads, UVs and LODs out of the box | Less cleanup than AI for simple props |
| Rodin (Hyper3D) | Mesh editing, parts, PBR | Access confirmed; ranked third in the same low-poly comparison |
| AI animation (Mixamo, AccuRig, Cascadeur and others) | Humanoid rig and animation | Low value for DayZ props |

## Validation backlog (harden this skill as items close)

1. Done. A/B generation of the same DayZ prop with local Hunyuan 2.1 and with Tripo, for geometry and polygon control: settled by a 2026-06-10 comparison on an Mk 47 model and a 2026-06-23 full-body case (tool results, not checked on `P:\`). Local 2.1 wins as the default (free, organic shapes, concept iteration); fal Hunyuan 3.1 Pro for fine hard surface; fal Rodin 2.5 for organic full bodies; Tripo 2.5 gave an efficient direct low-poly mesh (92k triangles) but was not the pick.
2. The high-to-low normal bake, then export, then `_nohq.paa`, then validation in game.
3. Modddif on prepared UVs: does it respect the UVs, and do its maps work as `_co` and `_nohq`?
4. A LOD batch through the Blender MCP: a prompt that decimates to N targets and downscales the textures, as a LOD prototype. Any visual decimation needs the user's approval first: ask before, and the default is that the user does it by hand.

When an item is confirmed, replace its "validate" mark with the verified data and where it was measured.

## Characters and infected (added 2026-06-23)

For a humanoid character or a creature (a zombie, a DayZ infected), do not author from scratch: reskin a vanilla one. A custom infected inherits `ZombieMaleBase` (`P:\DZ\characters\zombies\config.cpp:549`), whose parent `ZombieBase` carries the `enfanimsys` block (`P:\DZ\characters\zombies\config.cpp:71`) that names the mesh object, the animation graph and the skeleton, so the skeleton, the vanilla animations and the AI come free by inheritance. The real cost is rigging the mesh to the vanilla bones. The giant infected build named that skeleton `OFP2_ManSkeleton` in its `model.cfg`; that name is not in the unpacked text files on `P:\` (not yet checked on `P:\`). The full recipe is in the `dayz-characters` skill.

Bake the size into the mesh. `SetScale` is declared on `IEntity` (`P:\scripts\1_core\proto\enentity.c:448`) and vanilla calls it on the static objects its object spawner places (`P:\scripts\3_game\objectspawner.c:61`); it is reported not to hold on entities at run time, and the collision is reported not to follow it (reported behaviour, not checked on `P:\`).

Organic full-body mesh generation goes through fal Rodin (added 2026-06-23).

## Reference preparation and the planar check (added 2026-07-27)

- Prepare the reference with rembg, autocrop, a white background, a margin and filled transparent holes; use the full body when the output needs it. After generating, validate `trimesh.extents`: an axis near zero is a planar failure even when the render looks plausible.

## On Linux

Everything above is the Windows workflow and stays valid there. Agentic-Z is a Windows workspace; these notes are kept for a Linux user. The Proton setup, the measured tool matrix and the pitfalls are in the shared Linux and Proton note (`skills/_shared/linux-proton.md`). This section only says what changes for this skill.

- Pack, sign and binarize with dayzmake, the DayZ fork of armake2, at a pinned version. Which version to pin and how to install it are in `skills/dayz-build-pbo/references/dayzmake-linux.md` ("Get the right dayzmake"). Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. The original armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake v1.0.0 includes them) and it lacks the DayZ-only functions dayzmake keeps adding. The shell script `skills/_shared/scripts/dayz-mod-pack.sh` wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`); its notes are in the same `dayzmake-linux.md`. A 2026-11-03 comparison of a textured cube against Bohemia's binarize from a `P:` root matched byte for byte (dayzmake commit `7dcb3cf`, which `v1.0.0` contains). That is not an in-game ODOL check.
- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>` (the script is `skills/_shared/scripts/dayz-proton.sh`); a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton: `dayz-proton.sh gui ObjectBuilder <p3d>`, `gui TexView <paa>`. Object Builder opened and displayed a model; editing in it was not exercised. The offline checks (py3d, the model preflight and the 3D viewer, all under `scripts/tools/`) are Python and run natively.
- In-game checks on Linux: the Linux notes of the `dayz-test-ingame` skill (`skills/dayz-test-ingame/references/linux.md`).

## Building, testing and publishing the mod

When this work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), follow `dayz-mod-dev`, the entry point for mod development, and use `/dayz-lint`, `/dayz-build-pbo` and `/dayz-launch-test` for the build and test loop.
