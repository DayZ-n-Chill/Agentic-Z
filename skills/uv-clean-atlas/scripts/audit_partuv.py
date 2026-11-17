# Audit a PartUV result with the same metrics as our pipeline, then re-pack its
# charts with the semantic shelf packer for an apples-to-apples comparison.
# Usage: blender -b -P audit_partuv.py -- <in.obj> <out_dir> <tag> <out.blend>
# <out.blend> holds the imported mesh with the shelf-packed UVs and its own
# materials. It is saved before any grid render, because the render replaces the
# object's materials and adds a camera and a light.
import bpy, sys, os

argv = sys.argv[sys.argv.index("--") + 1:]
IN_OBJ, OUT_DIR, TAG, OUT_BLEND = argv[0], argv[1], argv[2], argv[3]

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# uv_metrics.py is bundled next to this script
import uv_metrics
import uv_shelf_pack


def import_obj():
    # An empty factory scene drops every object, material, camera and light,
    # including what an earlier grid render left behind.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=IN_OBJ)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    ob = max(meshes, key=lambda o: len(o.data.polygons))
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    return ob


# Raw PartUV layout first; its render dirties the scene, so the shelf pass re-imports.
ob = import_obj()
print(f"IMPORTED: {ob.name} polys={len(ob.data.polygons)} uv_layers={[l.name for l in ob.data.uv_layers]}")
uv_metrics.score_and_render(ob, OUT_DIR, TAG + "_raw")

ob = import_obj()
n_isl, n_pan, n_str, n_spk = uv_shelf_pack.shelf_pack(ob.data)
print(f"SHELF_PACK: islands={n_isl} panels={n_pan} strips={n_str} specks={n_spk}")
os.makedirs(os.path.dirname(os.path.abspath(OUT_BLEND)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
uv_metrics.score_and_render(ob, OUT_DIR, TAG + "_shelf")
print("DONE_AUDIT_PARTUV")
