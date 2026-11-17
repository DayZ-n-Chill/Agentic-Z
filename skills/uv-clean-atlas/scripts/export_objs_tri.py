# Export a mesh object as a triangulated, sanitized OBJ (PartUV-friendly):
# triangulate, dissolve degenerate faces, drop loose verts/edges.
# Usage: blender -b <file.blend> -P export_objs_tri.py -- <object_name> <out.obj>
import bpy, bmesh, sys, os

argv = sys.argv[sys.argv.index("--") + 1:]
OB_NAME, OUT_OBJ = argv[0], argv[1]

ob = bpy.data.objects[OB_NAME]
for o in bpy.data.objects:
    o.select_set(o is ob)
bpy.context.view_layer.objects.active = ob

bm = bmesh.new()
bm.from_mesh(ob.data)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
loose_v = [v for v in bm.verts if not v.link_faces]
if loose_v:
    bmesh.ops.delete(bm, geom=loose_v, context='VERTS')
loose_e = [e for e in bm.edges if not e.link_faces]
if loose_e:
    bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
me2 = bpy.data.meshes.new(OB_NAME + "_tri")
bm.to_mesh(me2)
bm.free()
ob2 = bpy.data.objects.new(OB_NAME + "_tri", me2)
bpy.context.collection.objects.link(ob2)
for o in bpy.data.objects:
    o.select_set(o is ob2)
bpy.context.view_layer.objects.active = ob2
tris = sum(len(p.vertices) - 2 for p in me2.polygons)
print(f"SANITIZED: verts={len(me2.vertices)} tris={tris}")
os.makedirs(os.path.dirname(OUT_OBJ), exist_ok=True)
bpy.ops.wm.obj_export(filepath=OUT_OBJ, export_selected_objects=True,
                      export_materials=False, export_uv=False, export_normals=False,
                      apply_modifiers=True)
print("EXPORTED", OUT_OBJ, os.path.getsize(OUT_OBJ))
