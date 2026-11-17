#!/usr/bin/env python3
"""
Alignment viewer, step 1: read a worn clothing model (MLOD .p3d) and write the
JSON the viewer page is built from.

Usage:
    python alignment_viewer_extract.py <worn.p3d> --out <folder>
        [--lod 0] [--regions leftarm,rightarm,...] [--combo abdomen=pelvis+spine]
        [--ghost <reference.p3d>] [--odol-backend <folder>]

The JSON (<folder>/align_data.json) holds the mesh of one visual LOD, one
weight list per region (a region is a bone selection, or several added
together with --combo), one pivot per region, and an optional "ghost" mesh
shown as a wireframe to fit against (a vanilla worn model such as
P:\\DZ\\characters\\tops\\chainmail_m.p3d).

A ghost that is a binarized ODOL .p3d needs an ODOL reader this repo does not
ship: pass its folder with --odol-backend or set DAYZ_ODOL_BACKEND_ROOT. The
folder must hold odol_reader.py with ODOL.from_file(path). An MLOD ghost is
read with py3d.

Offline: reads the given files and writes one JSON. Needs the DayZ fork of
py3d (scripts/tools/py3d); exits 2 when it is missing or too old.
"""
import argparse
import json
import os
import sys
from pathlib import Path

PY3D_DIR = Path(__file__).resolve().parents[2] / "scripts" / "tools" / "py3d"
MIN_PY3D = (1, 6, 0)

DEFAULT_REGIONS = ["leftarm", "rightarm", "leftforearm", "rightforearm", "leftupleg", "rightupleg"]
DEFAULT_COMBOS = {"abdomen": ["pelvis", "spine"]}
PIVOT_TOP_FRACTION = 0.85  # a region pivots around the centroid of its top 15 % (by height)


def load_py3d():
    """Import the DayZ fork of py3d, preferring the repo copy; exit 2 with a hint when unusable."""
    if PY3D_DIR.is_dir():
        sys.path.insert(0, str(PY3D_DIR))
    try:
        import py3d
    except ImportError:
        print("[FAIL]  py3d not installed. Run: python -m pip install -e scripts/tools/py3d", file=sys.stderr)
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


def mesh_arrays(lod):
    """Flat [x, y, z, ...] positions and triangle indices of a LOD (polygons are fanned)."""
    positions = []
    for point in lod.points:
        c = point.coords
        positions.extend([round(c[0], 5), round(c[1], 5), round(c[2], 5)])
    indices = []
    for face in lod.faces:
        vs = [v.point_index for v in face.vertices]
        for k in range(1, len(vs) - 1):
            indices.extend([vs[0], vs[k], vs[k + 1]])
    return positions, indices


def selection_weights(lod, name):
    """Per-point weight of the selection called name (any letter case); 0.0 where it has none."""
    point_index = {id(point): i for i, point in enumerate(lod.points)}
    out = [0.0] * len(lod.points)
    for sel_name, sel in lod.selections.items():
        if sel_name.lower() == name.lower():
            for point, weight in sel.points.items():
                out[point_index[id(point)]] = round(float(weight or 0), 3)
            break
    return out


def region_weights(lod, regions, combos):
    """(region names, one weight list per region). A combo region adds its parts, capped at 1.0."""
    names = list(regions) + list(combos)
    weights = [selection_weights(lod, name) for name in regions]
    for parts in combos.values():
        acc = [0.0] * len(lod.points)
        for part in parts:
            for i, w in enumerate(selection_weights(lod, part)):
                acc[i] = min(1.0, acc[i] + w)
        weights.append([round(v, 3) for v in acc])
    return names, weights


def region_pivots(lod, names, weights, combos):
    """Pivot per region: centroid of the highest 15 % of its weighted points; a combo uses all of them."""
    pts = [point.coords for point in lod.points]
    pivots = {}
    for region, region_w in zip(names, weights):
        idxs = [i for i, w in enumerate(region_w) if w > 0]
        if not idxs:
            continue
        ys = sorted(pts[i][1] for i in idxs)
        y_hi = ys[int(len(ys) * PIVOT_TOP_FRACTION)]
        top = idxs if region in combos else [i for i in idxs if pts[i][1] >= y_hi]
        n = len(top)
        pivots[region] = [round(sum(pts[i][axis] for i in top) / n, 4) for axis in range(3)]
    return pivots


def read_ghost(path, py3d, odol_backend):
    """(positions, indices) of the reference mesh: MLOD through py3d, ODOL through the external reader."""
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic == b"MLOD":
            f.seek(0)
            return mesh_arrays(py3d.P3D(f).lods[0])
    if magic != b"ODOL":
        sys.exit("[FAIL]  %s is neither an MLOD nor an ODOL .p3d" % path)
    backend = odol_backend or os.environ.get("DAYZ_ODOL_BACKEND_ROOT")
    if not backend:
        sys.exit(
            "[FAIL]  %s is a binarized ODOL model; pass --odol-backend <folder with odol_reader.py> "
            "or set DAYZ_ODOL_BACKEND_ROOT, or give an MLOD reference instead" % path
        )
    sys.path.insert(0, backend)
    from odol_reader import ODOL

    glod = ODOL.from_file(str(path)).lods[0]
    positions = []
    for v in glod.vertices:
        positions.extend([round(v.x, 5), round(v.y, 5), round(v.z, 5)])
    indices = []
    for face in glod.faces:
        vs = list(getattr(face, "vertex_indices", []) or [])
        for k in range(1, len(vs) - 1):
            indices.extend([vs[0], vs[k], vs[k + 1]])
    return positions, indices


def parse_combos(values):
    """['abdomen=pelvis+spine'] -> {'abdomen': ['pelvis', 'spine']}."""
    combos = {}
    for value in values:
        name, _, parts = value.partition("=")
        if not name or not parts:
            sys.exit("[FAIL]  --combo takes name=part+part, got %r" % value)
        combos[name.strip().lower()] = [p.strip().lower() for p in parts.split("+") if p.strip()]
    return combos


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract mesh, region weights and pivots for the alignment viewer.")
    parser.add_argument("p3d", help="worn clothing model, MLOD")
    parser.add_argument("--out", required=True, help="output folder; align_data.json is written there")
    parser.add_argument("--lod", type=int, default=0, help="index of the visual LOD to show (default 0)")
    parser.add_argument("--regions", help="comma-separated bone selections to adjust (default: arms, forearms, thighs)")
    parser.add_argument("--combo", action="append", default=None, help="name=part+part, repeatable (default abdomen=pelvis+spine)")
    parser.add_argument("--ghost", help="reference .p3d shown as a wireframe")
    parser.add_argument("--odol-backend", help="folder with odol_reader.py, for an ODOL ghost")
    args = parser.parse_args(argv)

    py3d = load_py3d()
    regions = [r.strip().lower() for r in args.regions.split(",") if r.strip()] if args.regions else DEFAULT_REGIONS
    combos = parse_combos(args.combo) if args.combo is not None else DEFAULT_COMBOS

    with open(args.p3d, "rb") as f:
        model = py3d.P3D(f)
    if not 0 <= args.lod < len(model.lods):
        sys.exit("[FAIL]  %s has %d LODs; --lod %d is out of range" % (args.p3d, len(model.lods), args.lod))
    lod = model.lods[args.lod]

    positions, indices = mesh_arrays(lod)
    names, weights = region_weights(lod, regions, combos)
    pivots = region_pivots(lod, names, weights, combos)
    ghost_positions, ghost_indices = read_ghost(args.ghost, py3d, args.odol_backend) if args.ghost else ([], [])

    data = {
        "armor": {"positions": positions, "indices": indices, "regions": names, "weights": weights, "pivots": pivots},
        "ghost": {"positions": ghost_positions, "indices": ghost_indices},
    }
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "align_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print("data written: %s (%d points, regions=%s)" % (out_path, len(lod.points), names))
    print("pivots:", json.dumps(pivots))
    missing = [name for name in names if name not in pivots]
    if missing:
        print("[WARN]  no weighted points for: %s" % ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
