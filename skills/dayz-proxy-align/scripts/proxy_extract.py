#!/usr/bin/env python3
"""
proxy_extract.py - read every proxy of a host MLOD .p3d into a recipe JSON.

The recipe holds the body mesh of the first visual LOD, and for each proxy its
triangle in face vertex order, the frame derived by angle sort (proxy_frame.py),
an `ambiguous` flag for the 90/45/45 tie, and the model path it points at.
proxy_canon.py, worn_overlay.py and proxy_viewer.py read this recipe.

Usage:
  python proxy_extract.py <host.p3d> <recipe.json>
"""
import sys, os, json, re
import py3d
from proxy_frame import derive_frame

SLOT_MAP = {
    "body":"Body","feet":"Feet","gloves":"Gloves","legs":"Legs","vest":"Vest",
    "headgear":"Headgear","mask":"Mask","eyewear":"Eyewear","armband":"Armband",
    "hips":"Hips","backpack":"Back",
}
def slot_of(proxy_name):
    base = proxy_name.split("\\")[-1]
    base = re.sub(r"\.\d+$", "", base)
    base = re.sub(r"_dz$", "", base)
    return SLOT_MAP.get(base, base)
def ref_model(proxy_name):
    p = proxy_name[len("proxy:"):] if proxy_name.startswith("proxy:") else proxy_name
    return re.sub(r"\.\d+$", "", p)

def main(src, out):
    with open(src, "rb") as f:
        m = py3d.P3D(f)
    lod0_i = min(range(len(m.lods)), key=lambda i: m.lods[i].resolution)
    lod = m.lods[lod0_i]
    pt_idx = {id(p): i for i, p in enumerate(lod.points)}
    fc_idx = {id(fc): i for i, fc in enumerate(lod.faces)}

    proxies = []
    proxy_face_set = set()
    for name, sel in lod.selections.items():
        if not name.startswith("proxy:"):
            continue
        fcs = [fc for fc, w in (sel.faces or {}).items() if w > 0]
        proxy_face_set.update(fc_idx[id(fc)] for fc in fcs)
        if fcs:
            ordered = [v.point_index for v in fcs[0].vertices][:3]
        else:
            ordered = sorted({pt_idx[id(p)] for p, w in (sel.points or {}).items() if w > 0})
        tri = [list(lod.points[i].coords) for i in ordered]
        if len(tri) == 3:
            anchor, R, ambiguous, angles = derive_frame(tri)
            frame = R.tolist()
        else:
            anchor, frame, ambiguous, angles = (tri[0] if tri else [0,0,0]), None, None, []
        proxies.append({
            "name": name, "slot": slot_of(name), "lod": lod0_i,
            "point_indices": ordered, "triangle": tri,
            "origin": list(lod.points[ordered[0]].coords) if ordered else [0, 0, 0],
            "ref_model": ref_model(name),
            "frame": frame, "ambiguous": ambiguous,
            "angles_deg": [round(a, 2) for a in angles],
        })
    proxies.sort(key=lambda p: p["slot"])

    positions = [list(p.coords) for p in lod.points]
    faces = []
    for fi, face in enumerate(lod.faces):
        if fi in proxy_face_set:
            continue
        vi = [v.point_index for v in face.vertices]
        if len(vi) == 3:
            faces.append(vi)
        elif len(vi) == 4:
            faces.append([vi[0], vi[1], vi[2]]); faces.append([vi[0], vi[2], vi[3]])
        elif len(vi) > 4:
            for k in range(1, len(vi) - 1):
                faces.append([vi[0], vi[k], vi[k+1]])

    xs=[p[0] for p in positions]; ys=[p[1] for p in positions]; zs=[p[2] for p in positions]
    bbox = {"min":[min(xs),min(ys),min(zs)], "max":[max(xs),max(ys),max(zs)]}

    recipe = {"model": os.path.basename(src), "source_path": os.path.abspath(src),
              "lod0_index": lod0_i, "body": {"positions": positions, "faces": faces},
              "bbox": bbox, "proxies": proxies}
    with open(out, "w") as f:
        json.dump(recipe, f)

    print("model=%s body verts=%d tris=%d proxies=%d" % (recipe["model"], len(positions), len(faces), len(proxies)))
    print("proxy frames (angle-sort; AMBIG = degenerate 90/45/45 tie -> rotation undefined):")
    for p in proxies:
        o=p["origin"]
        print("  %-10s %-16s o=(%+.3f,%+.3f,%+.3f) angles=%s %s" % (
            p["slot"], p["name"].split("\\")[-1], o[0],o[1],o[2], p["angles_deg"],
            "AMBIG" if p["ambiguous"] else "ok"))
    return recipe

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    main(sys.argv[1], sys.argv[2])
