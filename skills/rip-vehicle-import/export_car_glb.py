# Export a session A .blend to car.glb for the classify viewer (generic, any car).
# Runs inside Blender, not under plain Python. It needs no P:\ drive and no DayZ Tools.
# Usage:
#   blender --background --python-exit-code 1 --python export_car_glb.py -- --blend <sessionA.blend> --out <viewer_dir>\car.glb
# Stamps dz_coll/dz_reason in memory only (never saves the .blend) and exports node
# extras (source_id, dz_coll, dz_review, dz_movable_group, dz_reason) with no materials.
# source_id, dz_review and dz_movable_group must already be custom properties on the objects.
import bpy
import os
import sys

COLLS = ("DZ_INCLUDE", "DZ_EXCLUDE", "DZ_MOVABLE")


def arg(name):
    tail = sys.argv[sys.argv.index("--") + 1:]
    return tail[tail.index(name) + 1]


BLEND = arg("--blend")
OUT = arg("--out")

bpy.ops.wm.open_mainfile(filepath=BLEND)
for o in bpy.data.objects:
    member = [c.name for c in o.users_collection if c.name in COLLS]
    o["dz_coll"] = member[0] if member else ""
    o["dz_reason"] = str(o.get("dz_exclude_reason", ""))
for lc in bpy.context.view_layer.layer_collection.children:
    lc.hide_viewport = False
for c in bpy.data.collections:
    c.hide_render = False

os.makedirs(os.path.dirname(OUT), exist_ok=True)
kwargs = dict(filepath=OUT, export_format="GLB", export_extras=True,
              export_cameras=False, export_lights=False, export_apply=False,
              export_materials="NONE")
try:
    bpy.ops.export_scene.gltf(**kwargs)
    mode = "full"
except TypeError as e:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_extras=True)
    mode = "minimal (%r)" % e
print("GLB_DONE mode=%s bytes=%d" % (mode, os.path.getsize(OUT)))
