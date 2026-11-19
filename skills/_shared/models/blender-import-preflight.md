# Imported meshes in Blender

What to check before you work on a mesh imported into Blender, and how to reduce and reshape such meshes without breaking them. All of it is Blender behaviour measured offline in Blender 5.1, so none of it is checked on `P:\`.

## Before you work on an FBX

1. **Custom split normals.** A 3ds Max FBX with custom split normals can crash Blender 5.1 in `mesh_set_custom_normals`. Import with `use_custom_normals=False`, then recalculate normals from the intended smoothing. That is fine for a pipeline where py3d derives the final data.
2. **Scale inheritance.** Blender 5.1 removed `apply_scale_options` and `apply_unit_scale` from the FBX importer, and `global_scale` and `bake_space_transform` do not repair per node scale inheritance. List each family of objects with its world bounding box (`matrix_world @ vertex`) against a rebuild of the root frame, and rebuild only the families whose measured anchors confirm the transform. When a native `.blend` of the same asset exists, take its large parts and rebuild only the moving parts that exist in the FBX alone.
3. **A clean scene.** Import into a factory clean scene; the same FBX can come in with different local axes after `open_mainfile()`. Bring native `.blend` data in with `bpy.data.libraries.load(..., link=False)` instead of importing into a loaded scene.
4. **Hidden objects on export.** Before each per object OBJ export, set `hide_viewport=False` and call `hide_set(False)`. With selected object export, Blender can return `{'FINISHED'}` and skip a hidden object. Check that every expected file exists after its export.

## Reducing a curved surface

For the LODs of a curved surface, use Decimate in COLLAPSE mode and protect the important features with an inverted vertex group. Measure the triangle count and whether each feature survived. Never use planar dissolve as a reducer without checking the count after triangulating.

COLLAPSE can zero or flip corner normals; what to fall back to is in `axes-and-winding.md`, "Visual LODs". Ask the user before decimating any LOD the player sees (`generated-model-pipeline.md`).

## Attachments with a fixed bounding box

On an attachment whose bounding box is fixed, measure the whole group in the export frame after each feature. If the box is already full, make relief by stepping down or recessing the area around it, not by adding geometry that stands out of it.

## Reshaping vanilla rocks

Vanilla models on `P:\` are binarized, so a vanilla rock has to go through an outside ODOL to MLOD converter before Blender can open it; this repo ships none. Measured while reshaping two vanilla rocks:

- A vanilla rock's visual LOD is a double shell, about 0.4 m apart. When you rebuild surface from it, keep only the upward faces that are the first hit from above, or the inner shell comes back. A first hit filter opens holes on overhanging flanks, so leave the flanks alone. To check for holes, cast a fan of horizontal rays from inside at several heights; a ray that escapes is a hole.
- An imported rock is an unwelded triangle soup with flipped faces and cracks. Offsetting along vertex normals to build an inner face pushed about 2% of it outside, and ray parity inside tests are unreliable with cracks. To test whether a point is inside, rasterize the outer contour per height slice (flood fill from outside plus a Euclidean distance transform).
- Build an inner face from a cracked rock as a height field: each column rises until it is a minimum distance from the nearest surface (`BVHTree.find_nearest`), capped by the top seen from above. Filling 2D slices from outside leaked above about 14.9 m on one rock, and displacing the mesh pushed vertices out.
