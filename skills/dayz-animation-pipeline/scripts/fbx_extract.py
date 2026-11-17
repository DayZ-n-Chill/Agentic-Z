"""Dump the Bohemia character rig FBX to rig_raw.json. Runs inside Blender:

    blender -b --python-exit-code 1 --python fbx_extract.py -- <animation_rig_character.fbx>

The FBX is the character rig from Bohemia's public DayZ-Misc repository. Its
path comes from the argument after "--", else from DAYZ_ANIM_RIG_FBX, else the
file is looked for by its name in the current folder. Give extract_empties.py
the same FBX: build_rig_dayz.py pairs the two outputs.

Writes rest matrices, parents and lengths of every bone, every empty, and the
Male_body mesh with its four strongest skin weights per vertex.
"""
import bpy, json, os, sys, tempfile
from mathutils import Matrix

# Working directory shared by every stage of this pipeline. Override with
# DAYZ_ANIM_SCRATCH; the default is stable across runs so each stage finds the
# previous one's output.
SCR = os.environ.get("DAYZ_ANIM_SCRATCH") or os.path.join(tempfile.gettempdir(), "dayz-anim-pipeline")
os.makedirs(SCR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
# Same FBX as extract_empties.py, found the same way.
after_dashes = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
fbx = (after_dashes[0] if after_dashes else "") or os.environ.get("DAYZ_ANIM_RIG_FBX") or "animation_rig_character.fbx"
bpy.ops.import_scene.fbx(filepath=fbx)

def m2l(m):
    return [[round(m[r][c], 6) for c in range(4)] for r in range(4)]

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
AW = arm.matrix_world

bones = []
for b in arm.data.bones:
    mw = AW @ b.matrix_local          # rest, world (Blender Z-up, meters)
    bones.append({
        "name": b.name,
        "parent": b.parent.name if b.parent else None,
        "world": m2l(mw),
        "length": round(b.length, 6),
    })

empties = []
for o in bpy.data.objects:
    if o.type == 'EMPTY':
        empties.append({
            "name": o.name,
            "parent": o.parent.name if o.parent else None,
            "parent_bone": (o.parent_bone or None),
            "world": m2l(o.matrix_world),
        })

# Male_body mesh: world verts, triangulated faces, top-4 skin weights
mo = bpy.data.objects["Male_body"]
me = mo.data
MW = mo.matrix_world
vg_name = {vg.index: vg.name for vg in mo.vertex_groups}
verts = []
weights = []
for v in me.vertices:
    co = MW @ v.co
    verts.append([round(co.x, 5), round(co.y, 5), round(co.z, 5)])
    gw = sorted(((g.group, g.weight) for g in v.groups), key=lambda x: -x[1])[:4]
    tot = sum(w for _, w in gw) or 1.0
    weights.append([[vg_name.get(gi, "?"), round(w / tot, 5)] for gi, w in gw if w > 0])
faces = []
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(1, len(vs) - 1):
        faces.append([vs[0], vs[k], vs[k + 1]])

data = {
    "source": os.path.basename(fbx),
    "armature_world": m2l(AW),
    "units": "blender_world_zup_meters",
    "bones": bones,
    "empties": empties,
    "mesh": {"name": "Male_body", "verts": verts, "faces": faces, "weights": weights},
}
out = os.path.join(SCR, "rig_raw.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f)
print("WROTE", out)
print("bones", len(bones), "empties", len(empties), "verts", len(verts), "faces", len(faces))
