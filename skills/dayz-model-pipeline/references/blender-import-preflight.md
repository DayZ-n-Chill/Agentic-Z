# Blender import preflight and mesh editing notes

What to check before geometry work on a mesh that was imported into Blender, and what was measured while reducing and reshaping such meshes. All of it is Blender behavior measured by the source author (the Blender version is named in each note), so nothing here is checked on `P:\`.

Evidence labels: `[OFFLINE MEASURED]` is measured in Blender without the game.

## FBX import preflight for Blender 5.x (SP-068, added 2026-08-31)

Run these checks before Path A geometry work:

1. **Custom split normals.** A 3ds Max FBX with custom split normals can crash Blender 5.1.1 in `mesh_set_custom_normals`. Import with `use_custom_normals=False`, then recalculate normals from the intended smoothing. This is acceptable for a technical pipeline in which py3d derives the final data.
2. **Scale inheritance.** Blender 5.1 removed `apply_scale_options` and `apply_unit_scale` from the FBX importer. `global_scale` and `bake_space_transform` do not repair per node RSrs scale inheritance. Take a census of object families with world space bounding boxes (`matrix_world @ vertex`) against the root frame reconstruction, and rebuild only the families whose measured anchors validate the transform. When a native `.blend` for the same asset exists, prefer its large parts and reconstruct only the moving families that exist in the FBX alone.
3. **Clean scene.** Import into a factory clean scene. The same FBX can produce different local axes after `open_mainfile()`. Combine native `.blend` data with `bpy.data.libraries.load(..., link=False)` instead of importing into an already loaded scene.
4. **Hidden objects on export.** Before every per object OBJ export, set `hide_viewport=False` and call `hide_set(False)`. With selected object export, Blender can return `{'FINISHED'}` while silently skipping a hidden object. Assert that every expected output file exists after its export.

## Reducing a curved surface (lesson LL-024)

For the LODs of a curved surface, use Decimate in COLLAPSE mode and protect the critical features with an inverted vertex group. Measure the triangle count and whether each feature survived. Do not use planar dissolve as a reducer without checking the count after triangulating.

Decimate COLLAPSE can also zero or invert corner normals; `axes-and-winding.md` ("Decimate COLLAPSE corner normals") says what to fall back to. Any decimation of a LOD the player sees needs the user's approval first (the decimation gate in `SKILL.md`).

## Attachments with a contractual bounding box (lesson LL-134)

On an attachment whose bounding box is fixed by contract, measure the full group in the export frame after each feature. If the box is closed, create relief by stepping down or recessing the surrounding area instead of adding geometry that stands proud of it.

## Editing imported vanilla meshes: rocks (SP-451, added 2026-10-01)

Measured offline in Blender 5.1 headless while reshaping a vanilla rock for a mod (SecretRock R6 and R7):

- **`[OFFLINE MEASURED]` A vanilla rock's visual LOD is a double shell (about 0.4 m apart).** When restoring surface from it, keep only the upward facing faces that are the first hit from above; the inner shell comes back if you do not filter. Deleting or replacing with a first hit filter opens holes on overhanging flanks: leave the flanks alone. Cheap check: a fan of horizontal rays cast from inside at several heights. A ray that escapes is a hole.
- **`[OFFLINE MEASURED]` An imported rock mesh is an unwelded triangle soup with flipped faces and cracks.** Offsetting the surface along vertex normals (to build an inner face) pushed about 2 % of it outside, and ray parity inside tests are unreliable with cracks. To test "is inside the rock", rasterize the outer contour per z slice (flood fill from outside plus a Euclidean distance transform).
- **`[OFFLINE MEASURED]` Building an inner face from a cracked rock: use a height field.** Each column rises until it sits at a minimum distance from the nearest surface (`BVHTree.find_nearest`), capped by the top seen from above. Filling 2D slices from outside leaked above about 14.9 m on R6, and displacing the mesh pushed vertices out.

Vanilla models on `P:\` are binarized, so a vanilla rock has to come through an external ODOL to MLOD converter before Blender can open it; Agentic-Z ships none.
