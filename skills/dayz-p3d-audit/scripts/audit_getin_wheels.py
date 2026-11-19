#!/usr/bin/env python3
"""
Offline audit of vehicle .p3d models (MLOD): get-in memory points, seat selections
and wheel axis handedness. Reports findings; never modifies files.

Usage:
    python audit_getin_wheels.py MODEL.p3d [MODEL.p3d ...]

For each model it prints the LOD list, the get-in anchors found in the Memory LOD,
the direction of each wheel axis (left and right axes whose X sign differs are
mirrored, which predicts that one side spins backwards) and the seat selections
present in the Geometry, View Geometry and Fire Geometry LODs. Pass a known-good
car next to the car under test and compare the two blocks.

Exit codes:
    0  every required anchor, wheel axis and seat selection is present
    1  a model defect, one "FAIL:" line per defect on stderr
    2  no input, a missing or unreadable file, or py3d was not found

Reads only the files it is given, so it does not gate on /dayz-preflight.
Reads .p3d files with the DayZ fork of py3d kept in this repo at
scripts/tools/py3d, loaded by path; without that folder it uses an installed
py3d (../requirements.txt installs the repo copy, run from the repo root).
"""

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import skill_helpers as h  # noqa: E402

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
# The DayZ fork of py3d kept in this repo: the one py3d copy every skill uses.
REPO_FORK = Path(__file__).resolve().parents[3] / "scripts" / "tools" / "py3d" / "py3d" / "__init__.py"
_fork_module = None

LOD_NAMES = {1e13: "Geo", 1e15: "Mem", 2e15: "Land", 5e15: "Hit", 6e15: "View", 7e15: "Fire"}

# The two-seat roster of the reference car these checks were written against.
GETIN_MEM = ["crewdriver", "crewcodriver", "pos_driver", "pos_driver_dir",
             "pos_codriver", "pos_codriver_dir", "seat_con_1_1", "seat_con_2_1"]
SEAT_SEL = ["seat_driver", "seat_codriver", "seatback_driver", "seatback_codriver"]
WHEEL_AX = ["wheel_1_1_axis", "wheel_2_1_axis", "wheel_1_2_axis", "wheel_2_2_axis"]


def load_py3d():
    """py3d: the repo's DayZ fork when it is there, else the installed py3d.

    The fork is loaded from its file under a private module name, as
    /dayz-p3d-audit does. Exits 2 with a hint when neither is found.
    """
    global _fork_module
    if REPO_FORK.is_file():
        if _fork_module is None:
            _fork_module = h.load_module("py3d_dayz_fork_vehicles", REPO_FORK)
        return _fork_module
    try:
        import py3d
    except ImportError:
        print(f"{h.FAIL} py3d not found: the repo copy at {REPO_FORK.parents[1]} is missing "
              "and no py3d is installed.", file=sys.stderr)
        print("Restore that folder from the repo. To install it as a package, run from the repo root: "
              f'python -m pip install -r "{REQUIREMENTS}"', file=sys.stderr)
        sys.exit(2)
    return py3d


def lodname(res):
    """Short label of a LOD resolution. Resolutions on disk are not the round
    nominal values, so each is matched with a relative tolerance."""
    for value, name in LOD_NAMES.items():
        if abs(res - value) / value < 0.03:
            return name
    if res < 1e3:
        return f"Vis{int(round(res))}"
    return f"{res:.3g}"


def sel_points(lod, name):
    """Coordinates of a selection's points, or of its faces' points when the
    selection lists only faces. None when the selection does not exist."""
    sel = lod.selections.get(name)
    if not sel:
        return None
    pts = [p.coords for p in sel.points]
    if not pts:
        seen = {}
        for face in sel.faces:
            for vertex in face.vertices:
                seen[vertex.point_index] = lod.points[vertex.point_index].coords
        pts = list(seen.values())
    return pts


def centroid(pts):
    count = len(pts)
    return [sum(p[k] for p in pts) / count for k in range(3)]


def axis_dir(pts):
    """Unit direction of an axis memory selection (two points), rounded."""
    if len(pts) < 2:
        return None
    a, b = pts[0], pts[1]
    delta = [b[k] - a[k] for k in range(3)]
    length = math.sqrt(sum(x * x for x in delta)) or 1.0
    return [round(delta[k] / length, 3) for k in range(3)]


def memory_lod(model):
    return next((lod for lod in model.lods if abs(lod.resolution - 1e15) / 1e15 < 0.03), None)


def print_report(path, model):
    print("=" * 88)
    print(os.path.basename(path), "| LODs:", ", ".join(lodname(lod.resolution) for lod in model.lods))

    mem = memory_lod(model)
    if mem:
        print("  -- Memory LOD get-in anchors --")
        for name in GETIN_MEM:
            pts = sel_points(mem, name)
            if pts is None:
                print(f"     {name:18s} ABSENT")
            elif not pts:
                print(f"     {name:18s} EMPTY")
            else:
                c = centroid(pts)
                print(f"     {name:18s} OK  n={len(pts)} centroid=({c[0]:.2f},{c[1]:.2f},{c[2]:.2f})")
        print("  -- wheel axis handedness (X sign: mirrored if L/R differ) --")
        for name in WHEEL_AX:
            pts = sel_points(mem, name)
            if pts is None:
                print(f"     {name:18s} ABSENT")
            else:
                print(f"     {name:18s} dir={axis_dir(pts)} (n={len(pts)})")
    else:
        print("  NO Memory LOD")

    for lod in model.lods:
        label = lodname(lod.resolution)
        if label not in ("View", "Fire", "Geo"):
            continue
        present = [s for s in SEAT_SEL if s in lod.selections]
        print(f"  -- {label} seat selections present: {present}")


def defects(path, model):
    """The model defects of one parsed model, as text lines."""
    mem = memory_lod(model)
    if mem is None:
        return [f"{path}: missing Memory LOD"]
    found = []
    for name in GETIN_MEM:
        if not sel_points(mem, name):
            found.append(f"{path}: Memory selection {name} missing or empty")
    for name in WHEEL_AX:
        pts = sel_points(mem, name)
        if not pts or len(pts) < 2:
            found.append(f"{path}: wheel axis {name} needs at least two points")
    seat_lods = [lod for lod in model.lods if lodname(lod.resolution) in ("View", "Geo")]
    if not seat_lods:
        found.append(f"{path}: no ViewGeometry or Geometry LOD for seat selections")
    else:
        for name in SEAT_SEL:
            if not any(name in lod.selections for lod in seat_lods):
                found.append(f"{path}: seat selection {name} absent from View/Geometry")
    return found


def main(argv=None):
    paths = list(sys.argv[1:] if argv is None else argv)
    if any(arg in ("-h", "--help") for arg in paths):
        print(__doc__.strip())
        return 0
    if not paths:
        print("USAGE: audit_getin_wheels.py MODEL.p3d [MODEL.p3d ...]", file=sys.stderr)
        return 2

    # Parse every input before auditing. An unreadable input is not a model defect.
    for path in paths:
        if not os.path.isfile(path):
            print(f"INPUT_ERROR: missing file: {path}", file=sys.stderr)
            return 2
    py3d = load_py3d()
    parsed = {}
    for path in paths:
        try:
            with open(path, "rb") as handle:
                parsed[path] = py3d.P3D(handle)
        except Exception as exc:  # py3d raises plain exceptions on a file it cannot read
            print(f"INPUT_ERROR: cannot parse {path}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2

    failures = []
    for path, model in parsed.items():
        print_report(path, model)
        failures += defects(path, model)
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
