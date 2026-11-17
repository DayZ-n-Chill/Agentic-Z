#!/usr/bin/env python3
"""
DayZ P3D Audit Script - Complete model validator (fork-delegated).

The model checks now live in py3d (the DayZ fork, >= 1.2.0) behind
P3D.validate(); this script keeps the CLI, the required-LOD scan and the
text-file checks. What was pruned:
  - LOD ids normalised to DayZ: ViewGeo=6e15, FireGeo=7e15; the
    GeoPhys/2e13 slot and the stale FireGeo~3e13 mentions are WITHDRAWN;
  - the absolute-centroid winding check is WITHDRAWN: the fork applies the
    RELATIVE cross-product check against the Visual LOD instead;
  - severities: ERROR -> CRITICAL, WARN -> WARNING.

Usage:
    python audit_p3d.py model.p3d [model2.p3d ...]
    python audit_p3d.py model.p3d --config path/to/config.cpp
    python audit_p3d.py model.p3d --model-cfg path/to/model.cfg
    python audit_p3d.py --scan-dir path/to/mod/

Requires: the py3d DayZ fork >= 1.2.0. NEVER `pip install py3d` - that
name on PyPI belongs to an unrelated library.
"""

import sys, os, re, glob, argparse

try:
    import py3d
except ImportError:
    print("ERROR: py3d (DayZ fork) not installed.")
    print("Install the vendored wheel: pip install --break-system-packages "
          "<skill>/wheels/py3d-*.whl")
    sys.exit(1)

if not getattr(py3d, "IS_DAYZ_FORK", False) or \
        tuple(int(x) for x in py3d.__version__.split(".")) < (1, 2, 0):
    print("ERROR: wrong py3d (%r, %s). This audit requires the DayZ fork "
          ">= 1.2.0 - NEVER `pip install py3d` (PyPI = point-cloud lib). "
          "Install the wheel vendored in the skill."
          % (getattr(py3d, "__version__", "?"),
             getattr(py3d, "__file__", "?")))
    sys.exit(1)

_SEV = {"ERROR": "CRITICAL", "WARN": "WARNING"}


def classify_lod(resolution):
    """Delegado al fork (mapa canonico DayZ, tolerancia relativa unica)."""
    kind = py3d.classify_lod_resolution(resolution)
    if kind is None:
        return "Other(%.1e)" % resolution
    return {
        "visual": "Visual", "shadowvolume": "ShadowVolume",
        "geometry": "Geometry", "memory": "Memory",
        "landcontact": "LandContact", "roadway": "Roadway",
        "paths": "Paths", "hitpoints": "HitPoints",
        "view_geometry": "ViewGeo", "fire_geometry": "FireGeo",
    }[kind]


def check_required_lods(lod_map):
    """LODs minimos (ids normalizados DayZ; GeoPhys retirado)."""
    issues = []
    if "Geometry" not in lod_map:
        issues.append(("CRITICAL", "Missing Geometry LOD (res ~1e13). No collision or action targeting possible."))
    if "Memory" not in lod_map:
        issues.append(("CRITICAL", "Missing Memory LOD (res ~1e15). No animation axes, no bounding data."))
    if "Visual" not in lod_map:
        issues.append(("CRITICAL", "Missing Visual LOD (res 0.0). Object will be invisible."))
    if "ViewGeo" not in lod_map:
        issues.append(("NOTE", "Missing ViewGeo LOD (res ~6e15). Action cursor raycasts (ObjIntersectView) have nothing to hit."))
    if "FireGeo" not in lod_map:
        issues.append(("NOTE", "Missing FireGeo LOD (res ~7e15). No ballistic damage zones."))
    return issues


def check_p_drive_paths_in_file(filepath):
    """Paths P:\\ en archivos de texto (config.cpp, .rvmat, model.cfg)."""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            matches = re.findall(r'["\']?(P:[\\\/][^"\';\s]+)', line, re.IGNORECASE)
            for m in matches:
                issues.append(("WARNING",
                    f"Line {i}: Absolute P:\\ path '{m}' - breaks on other machines. "
                    f"Use game-relative path (remove 'P:\\' prefix)."))
    except Exception as e:
        issues.append(("ERROR", f"Cannot read {filepath}: {e}"))
    return issues


def audit_p3d(filepath):
    """Full audit of one P3D file. True when there is no CRITICAL."""
    print(f"\n{'='*70}")
    print(f"AUDITING P3D: {filepath}")
    print(f"{'='*70}")

    try:
        with open(filepath, 'rb') as f:
            sig = f.read(4)
            if sig != b'MLOD':
                print(f"  ERROR: Not MLOD format (sig={sig}). Cannot audit ODOL. Provide source MLOD.")
                return False
            f.seek(0)
            p = py3d.P3D(f)
    except Exception as e:
        print(f"  ERROR: Failed to read: {e}")
        return False

    size = os.path.getsize(filepath)
    print(f"  Size: {size} bytes, LODs: {len(p.lods)}")

    all_issues = []
    lod_map = {}
    for i, lod in enumerate(p.lods):
        lt = classify_lod(lod.resolution)
        lod_map[lt] = (i, lod)
        sels = list(lod.selections.keys())
        props = dict(lod.properties) if lod.properties else {}
        print(f"  LOD[{i}] {lt} (res={lod.resolution:.1e}): "
              f"{len(lod.points)}v {len(lod.faces)}f sels={sels} props={props}")

    all_issues.extend(check_required_lods(lod_map))

    # Checks de modelo: delegados al fork (paridad depurada).
    for f in p.validate():
        sev = _SEV.get(f.severity, f.severity)
        lod_tag = "" if f.lod is None else "LOD[%d] " % f.lod
        all_issues.append((sev, "%s[%s] %s" % (lod_tag, f.code, f.msg)))

    for sev, msg in all_issues:
        print(f"  {sev}: {msg}")

    crits = sum(1 for s, _ in all_issues if s == "CRITICAL")
    warns = sum(1 for s, _ in all_issues if s == "WARNING")
    notes = sum(1 for s, _ in all_issues if s == "NOTE")
    print(f"\n  {'='*50}")
    if crits == 0 and warns == 0:
        print(f"  RESULT: ALL CHECKS PASSED ({notes} notes)")
    else:
        print(f"  RESULT: {crits} CRITICAL, {warns} WARNING, {notes} NOTE")
    return crits == 0


def audit_text_file(filepath, label="file"):
    print(f"\n{'='*70}")
    print(f"AUDITING {label}: {filepath}")
    print(f"{'='*70}")
    issues = check_p_drive_paths_in_file(filepath)
    for sev, msg in issues:
        print(f"  {sev}: {msg}")
    if not issues:
        print(f"  OK: No P:\\ paths found.")
    return len([s for s, _ in issues if s in ("CRITICAL", "WARNING")]) == 0


def scan_directory(dirpath):
    print(f"\nScanning directory: {dirpath}")
    all_pass = True
    p3d_files = glob.glob(os.path.join(dirpath, '**', '*.p3d'), recursive=True)
    p3d_files = [f for f in p3d_files if not f.endswith('.bak') and '.bak' not in f]
    for f in sorted(p3d_files):
        if not audit_p3d(f):
            all_pass = False
    for pattern, label in (('**/config.cpp', 'config.cpp'),
                           ('**/*.rvmat', '.rvmat'),
                           ('**/model.cfg', 'model.cfg')):
        for f in sorted(glob.glob(os.path.join(dirpath, pattern), recursive=True)):
            if not audit_text_file(f, label):
                all_pass = False
    return all_pass


def main():
    parser = argparse.ArgumentParser(description="DayZ P3D Audit - Complete Model Validator (py3d fork)")
    parser.add_argument('files', nargs='*', help='.p3d files to audit')
    parser.add_argument('--config', help='config.cpp to check for path issues')
    parser.add_argument('--model-cfg', help='model.cfg to check')
    parser.add_argument('--scan-dir', help='Scan entire mod directory')
    parser.add_argument('--rvmat', nargs='*', help='.rvmat files to check')
    args = parser.parse_args()

    all_pass = True
    if args.scan_dir:
        all_pass = scan_directory(args.scan_dir)
    else:
        for f in (args.files or []):
            if not os.path.exists(f):
                print(f"ERROR: File not found: {f}")
                all_pass = False
                continue
            if f.endswith('.p3d'):
                if not audit_p3d(f):
                    all_pass = False
            else:
                if not audit_text_file(f):
                    all_pass = False
        if args.config and not audit_text_file(args.config, "config.cpp"):
            all_pass = False
        if args.model_cfg and not audit_text_file(args.model_cfg, "model.cfg"):
            all_pass = False
        for rv in (args.rvmat or []):
            if not audit_text_file(rv, ".rvmat"):
                all_pass = False

    print(f"\n{'='*70}")
    print(f"OVERALL: {'ALL PASSED' if all_pass else 'ISSUES FOUND - fix before building PBO'}")
    print(f"{'='*70}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
