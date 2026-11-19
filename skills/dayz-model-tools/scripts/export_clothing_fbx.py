#!/usr/bin/env python3
"""
Artist handoff: export MLOD worn clothing models to FBX with Blender, keeping
the bone weights, then re-import each FBX in a clean scene to prove the vertex
groups survived.

Usage (headless Blender; everything after "--" belongs to this script):
    blender -b --python export_clothing_fbx.py -- --out <folder>
        [--texture <diffuse.png>] [--bones leftarm,rightarm,...] <worn_m.p3d> [<worn_f.p3d> ...]

Per model it writes <folder>/<name>.fbx with:
  - the first visual LOD: geometry and UVs (V flipped for Blender)
  - the diffuse PNG as the material's base color, when --texture is given
    (convert the .paa to .png first with DayZ Tools ImageToPAA, which also
    converts in that direction)
  - a weight-carrier armature: one bone per bone selection, placed at the
    weighted centroid of its points. FBX drops vertex groups that no armature
    deforms, so the armature is there only to carry them.

Axis map DayZ -> Blender is (x, y, z) -> (x, z, y): determinant -1 and its own
inverse. The garment lands like the official rig (Z up, front -Y, left +X)
with faces outward. An earlier version of this script used (x, -z, y), a mirror
image with inward faces; a package made that way goes back through
(x, z, -y), never through this map.

Offline: reads the given files and writes under --out. Runs inside Blender's
Python and needs the DayZ fork of py3d there (scripts/tools/py3d is added to
the path when it exists); exits 2 when it is missing or too old.
"""
import argparse
import os
import sys
from pathlib import Path

PY3D_DIR = Path(__file__).resolve().parents[3] / "scripts" / "tools" / "py3d"
MIN_PY3D = (1, 6, 0)
DEFAULT_BONES = ["leftarm", "rightarm", "leftforearm", "rightforearm", "leftupleg", "rightupleg", "neck", "pelvis", "spine", "spine3"]


def load_py3d():
    """Import the DayZ fork of py3d, preferring the repo copy; exit 2 with a hint when unusable."""
    if PY3D_DIR.is_dir():
        sys.path.insert(0, str(PY3D_DIR))
    try:
        import py3d
    except ImportError:
        print("[FAIL]  py3d not installed in Blender's Python. Run its python with: -m pip install -e scripts/tools/py3d", file=sys.stderr)
        sys.exit(2)
    version = tuple(int(part) for part in str(getattr(py3d, "__version__", "0")).split(".")[:3] if part.isdigit())
    if not getattr(py3d, "IS_DAYZ_FORK", False) or version < MIN_PY3D:
        print(
            "[FAIL]  this script needs the DayZ fork of py3d %s or newer (found %s at %s)."
            % (".".join(map(str, MIN_PY3D)), getattr(py3d, "__version__", "?"), getattr(py3d, "__file__", "?")),
            file=sys.stderr,
        )
        sys.exit(2)
    return py3d


def script_args(argv):
    """The arguments after "--" on Blender's command line; all of them when there is no "--"."""
    return argv[argv.index("--") + 1:] if "--" in argv else argv[1:]


def dayz_to_blender(c):
    """(x, y, z) -> (x, z, y). Determinant -1 and its own inverse, so the same map brings the mesh back."""
    return (c[0], c[2], c[1])


def export_model(bpy, Vector, py3d, p3d_path, out_dir, texture, bones):
    """Build mesh, weight-carrier armature and material for one model and export them as FBX."""
    objname = os.path.splitext(os.path.basename(p3d_path))[0]
    with open(p3d_path, "rb") as f:
        model = py3d.P3D(f)
    lod = model.lods[0]
    pt_index = {id(pt): i for i, pt in enumerate(lod.points)}
    verts = [dayz_to_blender(pt.coords) for pt in lod.points]
    faces = []
    uvs_per_face = []
    for face in lod.faces:
        faces.append([v.point_index for v in face.vertices])
        uvs_per_face.append([(v.uv[0], 1.0 - v.uv[1]) for v in face.vertices])

    mesh = bpy.data.meshes.new(objname)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    li = 0
    for poly, face_uvs in zip(mesh.polygons, uvs_per_face):
        for k in range(poly.loop_total):
            uv_layer.data[li].uv = face_uvs[k]
            li += 1

    obj = bpy.data.objects.new(objname, mesh)
    bpy.context.collection.objects.link(obj)

    bone_weights = {}
    bone_heads = {}
    for selname, sel in lod.selections.items():
        nm = selname.lower()
        if nm not in bones:
            continue
        entries = []
        acc = Vector((0, 0, 0))
        tot = 0.0
        for pt, w in sel.points.items():
            wv = float(w) if w is not None else 0.0
            if wv > 0:
                i = pt_index[id(pt)]
                entries.append((i, wv))
                acc += Vector(verts[i]) * wv
                tot += wv
        bone_weights[nm] = entries
        bone_heads[nm] = (acc / tot) if tot else Vector((0, 0, 1))

    arm_data = bpy.data.armatures.new(objname + "_rig")
    arm_obj = bpy.data.objects.new(objname + "_rig", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    for nm in bones:
        if nm not in bone_heads:
            continue
        eb = arm_data.edit_bones.new(nm)
        h = bone_heads[nm]
        eb.head = h
        eb.tail = h + Vector((0, 0, 0.08))
    bpy.ops.object.mode_set(mode="OBJECT")

    for nm, entries in bone_weights.items():
        vg = obj.vertex_groups.new(name=nm)
        for i, wv in entries:
            vg.add([i], wv, "REPLACE")

    obj.parent = arm_obj
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj

    mat = bpy.data.materials.new(objname + "_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if texture and os.path.exists(texture):
        teximg = mat.node_tree.nodes.new("ShaderNodeTexImage")
        teximg.image = bpy.data.images.load(texture)
        mat.node_tree.links.new(teximg.outputs["Color"], bsdf.inputs["Base Color"])
    mesh.materials.append(mat)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    fbx_path = os.path.join(out_dir, objname + ".fbx")
    bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, path_mode="COPY", embed_textures=False, add_leaf_bones=False)
    print("EXPORTED %s: %d verts %d faces %d bone-groups" % (fbx_path, len(verts), len(faces), len(bone_weights)))
    return objname, fbx_path, sorted(bone_weights)


def verify_reimport(bpy, objname, fbx_path, expected_groups):
    """Re-import one FBX and report its counts; False when a vertex group was lost."""
    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    meshes = [o for o in bpy.data.objects if o.name not in before and o.type == "MESH"]
    assert meshes, "no mesh reimported for %s" % objname
    o = meshes[0]
    gnames = sorted(g.name for g in o.vertex_groups)
    wsum = 0
    for v in o.data.vertices[:500]:
        wsum += sum(g.weight for g in v.groups)
    print("REIMPORT %s: %d verts %d vgroups %s uv=%s sample500_weightsum=%.1f" % (
        objname, len(o.data.vertices), len(o.vertex_groups), gnames[:4], len(o.data.uv_layers) > 0, wsum))
    lost = [g for g in expected_groups if g not in gnames]
    if lost:
        print("[FAIL]  %s lost vertex groups on reimport: %s" % (objname, ", ".join(lost)), file=sys.stderr)
    return not lost


def main(argv=None):
    parser = argparse.ArgumentParser(prog="export_clothing_fbx.py", description="Export MLOD worn clothing to FBX with its bone weights.")
    parser.add_argument("p3d", nargs="+", help="worn clothing models, MLOD")
    parser.add_argument("--out", required=True, help="output folder for the .fbx files")
    parser.add_argument("--texture", help="diffuse PNG used as base color")
    parser.add_argument("--bones", help="comma-separated bone selections to carry (default: the ten plate-armor regions)")
    args = parser.parse_args(script_args(sys.argv) if argv is None else argv)

    py3d = load_py3d()
    import bpy
    from mathutils import Vector

    bones = [b.strip().lower() for b in args.bones.split(",") if b.strip()] if args.bones else DEFAULT_BONES
    os.makedirs(args.out, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    exported = [export_model(bpy, Vector, py3d, path, args.out, args.texture, bones) for path in args.p3d]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    ok = all([verify_reimport(bpy, objname, fbx_path, groups) for objname, fbx_path, groups in exported])
    if not ok:
        return 1
    print("FBX_EXPORT_ALL_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
