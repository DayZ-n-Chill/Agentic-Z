#!/usr/bin/env python3
"""
DayZ P3D Audit Script — Complete model validator.
Catches all known silent killers for collision, targeting, animation, and paths.

Usage:
    python audit_p3d.py model.p3d [model2.p3d ...]
    python audit_p3d.py model.p3d --config path/to/config.cpp
    python audit_p3d.py model.p3d --model-cfg path/to/model.cfg
    python audit_p3d.py --scan-dir path/to/mod/  (scans all .p3d, config.cpp, .rvmat)

Requires: py3d (pip install git+https://github.com/KoffeinFlummi/py3d.git)
"""

import sys, os, re, glob, argparse

try:
    import py3d
except ImportError:
    print("ERROR: py3d not installed.")
    print("Run: pip install git+https://github.com/KoffeinFlummi/py3d.git")
    sys.exit(1)

# ============================================================================
# LOD classification
# ============================================================================
def classify_lod(resolution):
    # LOD resolution mapping. Standard Bohemia Arma/DayZ scheme uses ~6e15 for ViewGeometry
    # and ~7e15 for FireGeometry (see dayz-p3d-debinarizer/references/format_notes.md). Some
    # DayZ models in the wild also use ~7e13 (ViewGeo) and ~3e13 (FireGeo); accept both
    # ranges so the classifier matches either layout.
    if resolution < 1000:
        return "Visual"
    if 9e9 <= resolution <= 1.1e10:
        return "ShadowVolume"
    if 9.9e12 <= resolution <= 1.1e13:
        return "Geometry"
    if 1.9e13 <= resolution <= 2.1e13:
        return "GeoPhys"
    if (2.9e13 <= resolution <= 3.1e13) or (6.9e15 <= resolution <= 7.1e15):
        return "FireGeo"
    if (6.9e13 <= resolution <= 7.1e13) or (5.9e15 <= resolution <= 6.1e15):
        return "ViewGeo"
    if 9.9e14 <= resolution <= 1.1e15:
        return "Memory"
    if 1.9e15 <= resolution <= 2.1e15:
        return "LandContact"
    return f"Other({resolution:.1e})"

# ============================================================================
# P3D CHECKS
# ============================================================================

def check_required_lods(lod_map):
    """Check that required LODs exist."""
    issues = []
    if "Geometry" not in lod_map:
        issues.append(("CRITICAL", "Missing Geometry LOD (res ~1e13). No collision or action targeting possible."))
    if "Memory" not in lod_map:
        issues.append(("CRITICAL", "Missing Memory LOD (res ~1e15). No animation axes, no bounding data."))
    if "Visual" not in lod_map:
        issues.append(("CRITICAL", "Missing Visual LOD (res 0.0). Object will be invisible."))
    if "GeoPhys" not in lod_map:
        issues.append(("WARNING", "Missing GeoPhys LOD (res ~2e13). Player/vehicle physics collision may not work."))
    if "FireGeo" not in lod_map:
        issues.append(("NOTE", "Missing FireGeo LOD (res ~3e13). No ballistic damage zones."))
    return issues


def check_face_winding(lod):
    """Check all faces have outward-pointing normals."""
    issues = []
    if len(lod.points) == 0 or len(lod.faces) == 0:
        return issues
    n = len(lod.points)
    cx = sum(pt.coords[0] for pt in lod.points) / n
    cy = sum(pt.coords[1] for pt in lod.points) / n
    cz = sum(pt.coords[2] for pt in lod.points) / n
    inverted = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            continue
        v = [v.point.coords for v in verts]
        e1 = (v[1][0]-v[0][0], v[1][1]-v[0][1], v[1][2]-v[0][2])
        e2 = (v[2][0]-v[0][0], v[2][1]-v[0][1], v[2][2]-v[0][2])
        nx = e1[1]*e2[2] - e1[2]*e2[1]
        ny = e1[2]*e2[0] - e1[0]*e2[2]
        nz = e1[0]*e2[1] - e1[1]*e2[0]
        fcx = sum(c[0] for c in v) / len(v)
        fcy = sum(c[1] for c in v) / len(v)
        fcz = sum(c[2] for c in v) / len(v)
        dot = nx*(fcx-cx) + ny*(fcy-cy) + nz*(fcz-cz)
        if dot < 0:
            inverted += 1
    if inverted > 0:
        issues.append(("CRITICAL",
            f"{inverted}/{len(lod.faces)} faces have INVERTED winding (normals point inward). "
            f"Raycasts from outside pass through — zero collision. "
            f"Fix: swap vertices[1] and vertices[2] on each face."))
    return issues


def check_component_naming(lod):
    """Check Component01 uses correct case."""
    issues = []
    sels = list(lod.selections.keys())
    has_correct = 'Component01' in sels
    has_lowercase = 'component01' in sels
    has_any = any(s.lower().startswith('component') for s in sels)
    if has_lowercase and not has_correct:
        issues.append(("CRITICAL",
            "Found 'component01' (lowercase). Engine requires 'Component01' (uppercase C). "
            "Collision silently fails with wrong case."))
    elif not has_any:
        issues.append(("CRITICAL",
            "No Component selection found. Geometry LOD requires 'Component01' for collision."))
    elif not has_correct:
        found = [s for s in sels if s.lower().startswith('component')]
        issues.append(("WARNING", f"Component selection '{found[0]}' — verify exact case is 'Component01'."))
    return issues


def check_component_coverage(lod):
    """Check Component01 covers all vertices and faces."""
    issues = []
    if 'Component01' not in lod.selections:
        return issues
    sel = lod.selections['Component01']
    if len(sel.points) < len(lod.points):
        issues.append(("WARNING",
            f"Component01 covers {len(sel.points)}/{len(lod.points)} vertices. "
            f"Uncovered vertices won't participate in collision."))
    if len(sel.faces) < len(lod.faces):
        issues.append(("WARNING",
            f"Component01 covers {len(sel.faces)}/{len(lod.faces)} faces. "
            f"Uncovered faces won't register raycasts."))
    return issues


def check_autocenter_prop(lod):
    """Check autocenter=0 LOD property."""
    issues = []
    props = dict(lod.properties) if lod.properties else {}
    if 'autocenter' not in props:
        issues.append(("WARNING",
            "Missing 'autocenter=0' LOD property. For Inventory_Base items with "
            "autocenter=0 in config.cpp, this property must ALSO be in the LOD."))
    return issues


def check_watertight(lod):
    """Check mesh is closed."""
    issues = []
    edge_count = {}
    for face in lod.faces:
        pts = [id(v.point) for v in face.vertices]
        for j in range(len(pts)):
            edge = tuple(sorted([pts[j], pts[(j+1) % len(pts)]]))
            edge_count[edge] = edge_count.get(edge, 0) + 1
    boundary = sum(1 for c in edge_count.values() if c == 1)
    if boundary > 0:
        issues.append(("WARNING", f"{boundary} boundary edges — mesh not watertight (has holes)."))
    return issues


def check_degenerate_faces(lod):
    """Check for zero-area faces."""
    issues = []
    degen = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3:
            degen += 1; continue
        v = [v.point.coords for v in verts]
        e1 = (v[1][0]-v[0][0], v[1][1]-v[0][1], v[1][2]-v[0][2])
        e2 = (v[2][0]-v[0][0], v[2][1]-v[0][1], v[2][2]-v[0][2])
        area = ((e1[1]*e2[2]-e1[2]*e2[1])**2 + (e1[2]*e2[0]-e1[0]*e2[2])**2 + (e1[0]*e2[1]-e1[1]*e2[0])**2) ** 0.5
        if area < 1e-8:
            degen += 1
    if degen > 0:
        issues.append(("WARNING", f"{degen} degenerate (zero-area) faces won't register collision."))
    return issues


def check_memory_lod(lod):
    """Check Memory LOD for required points and structure."""
    issues = []
    sels = list(lod.selections.keys())

    # pos center
    if 'pos center' not in sels:
        issues.append(("WARNING",
            "Missing 'pos center' memory point. Engine auto-calculates bounding center, "
            "which may be wrong for tall/asymmetric objects. Add at (0,0,0)."))
    else:
        sel = lod.selections['pos center']
        for pt, w in sel.points.items():
            c = pt.coords
            if abs(c[0]) > 0.5 or abs(c[1]) > 0.5 or abs(c[2]) > 0.5:
                issues.append(("NOTE",
                    f"pos center at ({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f}) — "
                    f"for autocenter=0 items this should be near (0,0,0)."))

    # box_placing_min / box_placing_max
    has_min = 'box_placing_min' in sels
    has_max = 'box_placing_max' in sels
    if has_min != has_max:
        issues.append(("WARNING",
            f"Only one of box_placing_min/max found. Both are needed for hologram placement."))
    elif not has_min and not has_max:
        issues.append(("NOTE",
            "No box_placing_min/max points. Needed for deployable items with hologram placement."))

    # flag_mast_axis (if present, must have exactly 2 points)
    if 'flag_mast_axis' in sels:
        sel = lod.selections['flag_mast_axis']
        if len(sel.points) != 2:
            issues.append(("CRITICAL",
                f"flag_mast_axis has {len(sel.points)} points, MUST have exactly 2 "
                f"(start and end of animation translation axis)."))
        else:
            pts = list(sel.points.keys())
            p0, p1 = pts[0].coords, pts[1].coords
            dy = abs(p0[1] - p1[1])
            if dy < 0.1:
                issues.append(("WARNING",
                    f"flag_mast_axis points have only {dy:.3f}m Y separation — "
                    f"animation travel may be too small."))

    # Faces in Memory LOD (should be zero)
    if len(lod.faces) > 0:
        issues.append(("WARNING",
            f"Memory LOD has {len(lod.faces)} faces — should have 0. "
            f"Only single-vertex points belong in Memory LOD."))

    return issues


def check_visual_lod(lod, lod_map):
    """Check Visual LOD for animation selections and path issues."""
    issues = []
    sels = list(lod.selections.keys())

    # Check for animation selections (if Memory LOD has axes)
    if "Memory" in lod_map:
        mem_sels = list(lod_map["Memory"][1].selections.keys())
        for ms in mem_sels:
            if ms.endswith('_axis'):
                anim_name = ms.replace('_axis', '')
                if anim_name not in sels:
                    issues.append(("CRITICAL",
                        f"Memory LOD has '{ms}' axis but Visual LOD missing '{anim_name}' "
                        f"selection. Animation will silently do nothing."))
                else:
                    sel = lod.selections[anim_name]
                    if len(sel.points) == 0:
                        issues.append(("WARNING",
                            f"Visual LOD selection '{anim_name}' has 0 vertices — "
                            f"nothing will animate."))

    # Check for P:\ paths in face textures
    p_drive_count = 0
    for face in lod.faces:
        if face.texture and face.texture.upper().startswith('P:\\'):
            p_drive_count += 1
        if face.material and face.material.upper().startswith('P:\\'):
            p_drive_count += 1
    if p_drive_count > 0:
        issues.append(("NOTE",
            f"{p_drive_count} faces reference P:\\ drive paths in textures/materials. "
            f"These work in dev but break on distribution. Usually OK for MLOD source files."))

    # Autocenter impact analysis
    if len(lod.points) > 0:
        ys = [pt.coords[1] for pt in lod.points]
        centroid_y = sum(ys) / len(ys)
        if centroid_y > 1.0:
            issues.append(("NOTE",
                f"Vertex centroid at Y={centroid_y:.1f}m. Without autocenter=0, "
                f"model would sink ~{centroid_y:.1f}m into ground."))

    return issues


def check_p_drive_paths_in_file(filepath):
    """Check for P:\\ drive paths in text files (config.cpp, .rvmat)."""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            # Match P:\ or P:/ paths (case-insensitive)
            matches = re.findall(r'["\']?(P:[\\\/][^"\';\s]+)', line, re.IGNORECASE)
            for m in matches:
                issues.append(("WARNING",
                    f"Line {i}: Absolute P:\\ path '{m}' — breaks on other machines. "
                    f"Use game-relative path (remove 'P:\\' prefix)."))
    except Exception as e:
        issues.append(("ERROR", f"Cannot read {filepath}: {e}"))
    return issues


# ============================================================================
# MAIN AUDIT
# ============================================================================

def audit_p3d(filepath):
    """Full audit of one P3D file."""
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

    # Classify LODs
    for i, lod in enumerate(p.lods):
        lt = classify_lod(lod.resolution)
        lod_map[lt] = (i, lod)
        pts, fcs = len(lod.points), len(lod.faces)
        sels = list(lod.selections.keys())
        props = dict(lod.properties) if lod.properties else {}
        print(f"  LOD[{i}] {lt} (res={lod.resolution:.1e}): {pts}v {fcs}f sels={sels} props={props}")

    # Required LODs
    all_issues.extend(check_required_lods(lod_map))

    # Collision LODs
    for lt in ["Geometry", "GeoPhys", "FireGeo"]:
        if lt not in lod_map:
            continue
        idx, lod = lod_map[lt]
        print(f"\n  --- {lt} LOD[{idx}] ---")
        if len(lod.points) > 0:
            xs = [pt.coords[0] for pt in lod.points]
            ys = [pt.coords[1] for pt in lod.points]
            zs = [pt.coords[2] for pt in lod.points]
            print(f"  BBox: X=[{min(xs):.3f}..{max(xs):.3f}] Y=[{min(ys):.3f}..{max(ys):.3f}] Z=[{min(zs):.3f}..{max(zs):.3f}]")

        # Component01 is required only on Geometry LOD; running it on GeoPhys/FireGeo
        # produces false CRITICALs on valid vanilla models. face_winding removed entirely:
        # the centroid heuristic flags every Blender export (left-handed transform) per
        # SKILL.md "WINDING DIAGNOSTICS" section.
        if lt == "Geometry":
            check_fns = [check_component_naming, check_component_coverage,
                         check_autocenter_prop, check_watertight, check_degenerate_faces]
        else:
            check_fns = [check_autocenter_prop, check_watertight, check_degenerate_faces]
        for check_fn in check_fns:
            results = check_fn(lod)
            for sev, msg in results:
                print(f"  {sev}: {msg}")
                all_issues.append((sev, msg))

    # Memory LOD
    if "Memory" in lod_map:
        idx, lod = lod_map["Memory"]
        print(f"\n  --- Memory LOD[{idx}] ---")
        results = check_memory_lod(lod)
        for sev, msg in results:
            print(f"  {sev}: {msg}")
            all_issues.append((sev, msg))

    # Visual LOD
    if "Visual" in lod_map:
        idx, lod = lod_map["Visual"]
        print(f"\n  --- Visual LOD[{idx}] ---")
        results = check_visual_lod(lod, lod_map)
        for sev, msg in results:
            print(f"  {sev}: {msg}")
            all_issues.append((sev, msg))

    # Summary
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
    """Audit a text file for P:\\ paths."""
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
    """Scan entire mod directory for all auditable files."""
    print(f"\nScanning directory: {dirpath}")
    all_pass = True

    # P3D files
    p3d_files = glob.glob(os.path.join(dirpath, '**', '*.p3d'), recursive=True)
    p3d_files = [f for f in p3d_files if not f.endswith('.bak') and '.bak' not in f]
    for f in sorted(p3d_files):
        if not audit_p3d(f):
            all_pass = False

    # config.cpp
    cfg_files = glob.glob(os.path.join(dirpath, '**/config.cpp'), recursive=True)
    for f in sorted(cfg_files):
        if not audit_text_file(f, "config.cpp"):
            all_pass = False

    # .rvmat files
    rvmat_files = glob.glob(os.path.join(dirpath, '**', '*.rvmat'), recursive=True)
    for f in sorted(rvmat_files):
        if not audit_text_file(f, ".rvmat"):
            all_pass = False

    # model.cfg
    mcfg_files = glob.glob(os.path.join(dirpath, '**/model.cfg'), recursive=True)
    for f in sorted(mcfg_files):
        if not audit_text_file(f, "model.cfg"):
            all_pass = False

    return all_pass


def main():
    parser = argparse.ArgumentParser(description="DayZ P3D Audit — Complete Model Validator")
    parser.add_argument('files', nargs='*', help='.p3d files to audit')
    parser.add_argument('--config', help='config.cpp to check for path issues')
    parser.add_argument('--model-cfg', help='model.cfg to check')
    parser.add_argument('--scan-dir', help='Scan entire mod directory')
    parser.add_argument('--rvmat', nargs='*', help='.rvmat files to check')
    args = parser.parse_args()

    all_pass = True

    if args.scan_dir:
        if not scan_directory(args.scan_dir):
            all_pass = False
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

        if args.config:
            if not audit_text_file(args.config, "config.cpp"):
                all_pass = False

        if args.model_cfg:
            if not audit_text_file(args.model_cfg, "model.cfg"):
                all_pass = False

        for rv in (args.rvmat or []):
            if not audit_text_file(rv, ".rvmat"):
                all_pass = False

    print(f"\n{'='*70}")
    print(f"OVERALL: {'ALL PASSED' if all_pass else 'ISSUES FOUND — fix before building PBO'}")
    print(f"{'='*70}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
