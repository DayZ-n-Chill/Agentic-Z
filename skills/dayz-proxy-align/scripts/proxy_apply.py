#!/usr/bin/env python3
"""
proxy_apply.py - write aligned proxy triangles back into an MLOD .p3d.

Reads the edits JSON written by proxy_canon.py or exported by the viewer, loads
the MLOD with py3d (not through the /dayz-p3d-inspector recipe and build path),
and sets the point coordinates of each proxy's triangle. Everything else (the
geometry, other selections such as woodup1 and zbytek, the Geometry and Memory
LODs, #UVSet#) is written back unchanged, because only the listed points change.

Usage:
  python proxy_apply.py <src.p3d> <edits.json> <out.p3d> [--verify]
"""
import sys, json
import py3d

def apply_edits(src, edits_path, out):
    with open(edits_path) as f:
        data = json.load(f)
    with open(src, "rb") as f:
        m = py3d.P3D(f)
    n = 0
    for e in data["edits"]:
        lod = m.lods[e["lod"]]
        for pi, coord in zip(e["point_indices"], e["new_triangle"]):
            lod.points[pi].coords = tuple(float(c) for c in coord)
            n += 1
    with open(out, "wb") as f:
        m.write(f)
    print("applied %d edits across %d proxies -> %s" % (n, len(data["edits"]), out))
    return out

def verify(out):
    with open(out, "rb") as f:
        m = py3d.P3D(f)
    lod = m.lods[min(range(len(m.lods)), key=lambda i: m.lods[i].resolution)]
    sels = list(lod.selections.keys())
    prox = [s for s in sels if s.startswith("proxy:")]
    keep = [s for s in ("woodup1", "zbytek") if s in sels]
    print("VERIFY %s: LOD0 sels=%d  proxies=%d  kept=%s" % (out, len(sels), len(prox), keep))
    pt_idx = {id(p): i for i, p in enumerate(lod.points)}
    for name in sorted(prox):
        sel = lod.selections[name]
        fcs = [fc for fc, w in (sel.faces or {}).items() if w > 0]
        if fcs:
            o = lod.points[fcs[0].vertices[0].point_index].coords
            print("   %-48s o=(%+.3f,%+.3f,%+.3f)" % (name.split("\\")[-1], o[0], o[1], o[2]))

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(2)
    out = apply_edits(sys.argv[1], sys.argv[2], sys.argv[3])
    if "--verify" in sys.argv:
        verify(out)
