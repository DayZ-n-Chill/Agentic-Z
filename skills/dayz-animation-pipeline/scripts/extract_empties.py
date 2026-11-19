"""Write the world matrices of the rig FBX's helper empties to empties_armworld.json.
Runs inside Blender, on the same FBX as fbx_extract.py:

    blender -b --python-exit-code 1 --python extract_empties.py -- <animation_rig_character.fbx>

The FBX path comes from the argument after "--", else from DAYZ_ANIM_RIG_FBX,
else the file is looked for by its name in the current folder. Exits 1 and
writes nothing when the FBX has no RightHand_Dummy empty.
"""
import bpy, json, os, stat, sys, tempfile
from mathutils import Matrix

# Working directory shared by every stage of this pipeline. Override with
# DAYZ_ANIM_SCRATCH; the default is stable across runs so each stage finds the
# previous one's output.
SCR = os.environ.get("DAYZ_ANIM_SCRATCH") or os.path.join(tempfile.gettempdir(), "dayz-anim-pipeline")
os.makedirs(SCR, exist_ok=True)
# Drop the previous run's file first, before the import can fail: if this run
# fails, build_rig_dayz.py finds none and stops instead of building on stale
# anchors. A copy restored read-only is made writable first; a file that still
# cannot be removed stops the script here with that error.
path = os.path.join(SCR, "empties_armworld.json")
if os.path.exists(path):
    os.chmod(path, stat.S_IWRITE)
    os.remove(path)

# Same FBX as fbx_extract.py, found the same way: build_rig_dayz.py pairs both outputs.
bpy.ops.wm.read_factory_settings(use_empty=True)
after_dashes = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
fbx = (after_dashes[0] if after_dashes else "") or os.environ.get("DAYZ_ANIM_RIG_FBX") or "animation_rig_character.fbx"
bpy.ops.import_scene.fbx(filepath=fbx)
bpy.context.view_layer.update()
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

def world_of(o):
    # Compose the parent chain by hand: the empties this FBX imports disabled in
    # viewports (hide_viewport), RightHand_Dummy, LeftHand_Dummy and Weapon_Root
    # among them, keep matrix_world at the origin even after view_layer.update().
    # Assumes what that FBX has: one armature, parent bones without
    # use_relative_parent, and no hidden helper without a parent.
    if o.parent is None:
        return o.matrix_world
    if o.parent_type == 'BONE' and o.parent_bone:
        # child of bone: the parent frame sits at the bone's tail
        pb = arm.pose.bones[o.parent_bone]
        bl = arm.data.bones[o.parent_bone].length
        return arm.matrix_world @ pb.matrix @ Matrix.Translation((0, bl, 0)) @ o.matrix_parent_inverse @ o.matrix_basis
    # parented to another object (Weapon_Root hangs from RightHand_Dummy)
    return world_of(o.parent) @ o.matrix_parent_inverse @ o.matrix_basis

# Helper empties build_rig_dayz.py turns into anchors.
keys = ["RightHand_Dummy", "LeftHand_Dummy", "Weapon_Root", "weapon", "LeftHandIK", "RightHandIK",
        "LeftHandIKTarget", "RightHandIK_Helper", "Camera1st_lock_dummy"]
out = {}
for o in bpy.data.objects:
    if o.type == 'EMPTY' and o.name in keys:
        w = world_of(o)
        out[o.name] = [[round(w[r][c], 6) for c in range(4)] for r in range(4)]

# build_rig_dayz.py turns RightHand_Dummy into the anchor that build_viewer.py's
# poseReady() puts the weapon on (the page's default idle pose uses a fixed
# point instead); without it poseReady() falls back to (0, 1.3, 0.2) without a
# word, so stop here. Exit code 1 in Blender.
if "RightHand_Dummy" not in out:
    raise SystemExit("extract_empties: no RightHand_Dummy empty in %s; nothing written" % fbx)

with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f)
print("WROTE", path)
for k, m in out.items():
    print("  %-20s (%.3f,%.3f,%.3f)" % (k, m[0][3], m[1][3], m[2][3]))
absent = [k for k in keys if k not in out]
if absent:
    print("not in this FBX:", ", ".join(absent))
