#!/usr/bin/env python3
"""
Alignment viewer, step 3: apply the adjustments JSON exported by the viewer to
the MLOD worn models, with the same math the page uses.

Usage:
    python apply_alignment_json.py --adjust <adjust.json> [--samples <samples.json>]
        [--combo abdomen=pelvis+spine] [--backup-dir <folder>] <worn_m.p3d> [<worn_f.p3d> ...]

adjust.json is what "Generate adjustments JSON" gives:
    {"leftarm": {"pivot": [x, y, z], "rot_deg": [rx, ry, rz], "offset": [ox, oy, oz]}, ...}

samples.json is optional and cross-checks the Euler convention before any file
is touched. It holds, per region, one weight-1 point before and after as the
live page computed it:
    {"leftarm": {"before": [x, y, z], "after": [x, y, z]}, ...}
A difference of 1e-4 m or more stops the run with exit 1.

A region is a bone selection, or a combined region given with --combo exactly
as in the extract step. Every LOD with points is adjusted, so the resolution
LODs stay in step. Each file is copied to the backup folder (default: _backups
next to it) before it is saved, and re-read after to confirm the point and
face counts.

Offline: reads and writes only the given files. Needs the DayZ fork of py3d
(scripts/tools/py3d); exits 2 when it is missing or too old.
"""
import argparse
import datetime
import json
import math
import os
import shutil
import sys
from pathlib import Path

PY3D_DIR = Path(__file__).resolve().parents[3] / "scripts" / "tools" / "py3d"
MIN_PY3D = (1, 6, 0)
SAMPLE_TOLERANCE = 1e-4
DEFAULT_COMBOS = {"abdomen": ["pelvis", "spine"]}  # the same default as alignment_viewer_extract.py


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


def euler_xyz_matrix(rx, ry, rz):
    """three.js Matrix4.makeRotationFromEuler with order "XYZ", as rows for v' = M @ v. Angles in degrees."""
    x, y, z = math.radians(rx), math.radians(ry), math.radians(rz)
    a, b = math.cos(x), math.sin(x)
    c, d = math.cos(y), math.sin(y)
    e, f = math.cos(z), math.sin(z)
    ae, af, be, bf = a * e, a * f, b * e, b * f
    return (
        (c * e, -c * f, d),
        (af + be * d, ae - bf * d, -b * c),
        (bf - ae * d, be + af * d, a * c),
    )


def region_target(base, adj):
    """Where the region transform puts a point: rotate around the pivot, then offset."""
    px, py, pz = adj["pivot"]
    m = euler_xyz_matrix(*adj["rot_deg"])
    ox, oy, oz = adj["offset"]
    x, y, z = base[0] - px, base[1] - py, base[2] - pz
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z + px + ox,
        m[1][0] * x + m[1][1] * y + m[1][2] * z + py + oy,
        m[2][0] * x + m[2][1] * y + m[2][2] * z + pz + oz,
    )


def apply_region(current, base, weight, adj):
    """Blend current toward the region target of base by weight, as the page's recompute() does."""
    target = region_target(base, adj)
    return tuple(current[i] + weight * (target[i] - current[i]) for i in range(3))


def cross_check(adjust, samples):
    """Largest difference between this math and the viewer's samples; prints one line per region."""
    max_err = 0.0
    for region, sample in samples.items():
        if region not in adjust:
            print("%-13s no adjustment for this sample; skipped" % region)
            continue
        before = tuple(sample["before"])
        got = apply_region(before, before, 1.0, adjust[region])
        err = max(abs(got[i] - sample["after"][i]) for i in range(3))
        max_err = max(max_err, err)
        print("%-13s expected %s got (%.6f, %.6f, %.6f)  err=%.2e" % (region, sample["after"], got[0], got[1], got[2], err))
    return max_err


def find_selection(lod, name):
    """The selection called name in any letter case, or None."""
    for sel_name, sel in lod.selections.items():
        if sel_name.lower() == name.lower():
            return sel
    return None


def region_points(lod, region, combos):
    """[(point, weight)] of a region in one LOD. A combo region adds its parts, capped at 1.0, as the extract step does."""
    acc = {}
    for part in combos.get(region, [region]):
        sel = find_selection(lod, part)
        if sel is None:
            continue
        for point, weight in sel.points.items():
            w = float(weight or 0)
            if w > 0:
                entry = acc.setdefault(id(point), [point, 0.0])
                entry[1] = min(1.0, entry[1] + w)
    return [(point, w) for point, w in acc.values()]


def adjust_lod(lod, adjust, combos):
    """Move the weighted points of one LOD. Regions apply in the order of the JSON, each from the original position."""
    moved = {}  # id(point) -> [point, original coords, current coords]
    for region, adj in adjust.items():
        for point, w in region_points(lod, region, combos):
            entry = moved.setdefault(id(point), [point, tuple(point.coords), tuple(point.coords)])
            entry[2] = apply_region(entry[2], entry[1], w, adj)
    for point, _base, current in moved.values():
        point.coords = current
    return len(moved)


def weighted_centroid(lod, region, combos):
    """Weight-averaged position of a region in one LOD, or None when the LOD holds none of it."""
    pairs = region_points(lod, region, combos)
    total = sum(w for _, w in pairs)
    if not total:
        return None
    return tuple(sum(point.coords[i] * w for point, w in pairs) / total for i in range(3))


def parse_combos(values):
    """['abdomen=pelvis+spine'] -> {'abdomen': ['pelvis', 'spine']}."""
    combos = {}
    for value in values:
        name, _, parts = value.partition("=")
        if not name or not parts:
            sys.exit("[FAIL]  --combo takes name=part+part, got %r" % value)
        combos[name.strip().lower()] = [p.strip().lower() for p in parts.split("+") if p.strip()]
    return combos


def apply_to_file(py3d, path, adjust, combos, backup_dir):
    """Back up, adjust, save and re-read one .p3d."""
    backup_dir = backup_dir or os.path.join(os.path.dirname(os.path.abspath(path)), "_backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    shutil.copy2(path, os.path.join(backup_dir, os.path.basename(path) + ".bak_pre_alignment_" + stamp))

    with open(path, "rb") as f:
        model = py3d.P3D(f)
    pre_counts = [(len(lod.points), len(lod.faces)) for lod in model.lods]
    first = next((lod for lod in model.lods if lod.points), None)
    before = {region: weighted_centroid(first, region, combos) for region in adjust} if first else {}

    moved = sum(adjust_lod(lod, adjust, combos) for lod in model.lods if lod.points)

    assert [(len(lod.points), len(lod.faces)) for lod in model.lods] == pre_counts
    model.save(path, verify=True)
    with open(path, "rb") as f:
        reread = py3d.P3D(f)
    assert [(len(lod.points), len(lod.faces)) for lod in reread.lods] == pre_counts

    print("%s: applied to %d points, saved and verified." % (os.path.basename(path), moved))
    first = next((lod for lod in reread.lods if lod.points), None)
    for region in adjust:
        after = weighted_centroid(first, region, combos) if first else None
        if before.get(region) and after:
            print("  %-13s centroid X %.3f -> %.3f" % (region, before[region][0], after[0]))
        else:
            print("  [WARN]  %s: no weighted selection in the first LOD; nothing moved there" % region)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Apply alignment viewer adjustments to MLOD worn models.")
    parser.add_argument("p3d", nargs="+", help="worn clothing models, MLOD; changed in place")
    parser.add_argument("--adjust", required=True, help="adjustments JSON exported by the viewer")
    parser.add_argument("--samples", help="cross-check JSON: per region one point before and after, from the live page")
    parser.add_argument("--combo", action="append", default=None, help="name=part+part, repeatable; the same ones as the extract step (default abdomen=pelvis+spine)")
    parser.add_argument("--backup-dir", help="where the pre-change copies go (default: _backups next to each file)")
    args = parser.parse_args(argv)

    with open(args.adjust, encoding="utf-8") as f:
        adjust = json.load(f)
    if args.samples:
        with open(args.samples, encoding="utf-8") as f:
            samples = json.load(f)
        max_err = cross_check(adjust, samples)
        if max_err >= SAMPLE_TOLERANCE:
            print("[FAIL]  Euler convention mismatch against the viewer: %g" % max_err, file=sys.stderr)
            return 1
        print("CROSS-CHECK PASS (max err %.2e)\n" % max_err)

    combos = parse_combos(args.combo) if args.combo is not None else DEFAULT_COMBOS
    py3d = load_py3d()
    for path in args.p3d:
        apply_to_file(py3d, path, adjust, combos, args.backup_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
