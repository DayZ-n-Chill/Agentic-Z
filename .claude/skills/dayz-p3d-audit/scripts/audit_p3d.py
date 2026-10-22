#!/usr/bin/env python3
"""
DayZ P3D audit: validates MLOD .p3d models and scans config.cpp, model.cfg and
.rvmat files for absolute P-drive paths. Reports findings; never modifies files.

Usage:
    python audit_p3d.py model.p3d [model2.p3d ...]
    python audit_p3d.py model.p3d --config path/to/config.cpp
    python audit_p3d.py model.p3d --model-cfg path/to/model.cfg
    python audit_p3d.py --rvmat a.rvmat b.rvmat
    python audit_p3d.py --scan-dir path/to/mod/  (scans all .p3d, config.cpp, .rvmat, model.cfg)

With a model.cfg (--model-cfg, or the nearest one under --scan-dir) each
animation in CfgModels > <model> > Animations is checked against the model.
The Geometry LOD autocenter property is only checked when the config.cpp
(--config, or the nearest one under --scan-dir) has a class with autocenter = 0.

Gates on /dayz-preflight. Requires py3d for .p3d parsing
(python -m pip install -r ../requirements.txt); exits 2 when it is missing.
"""

import sys, os, re, glob, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import skill_helpers as h  # noqa: E402


REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


def load_py3d():
    """Import py3d, exiting 2 with an install hint if it is missing."""
    try:
        import py3d
    except ImportError:
        print(f"{h.FAIL} py3d not installed.")
        print(f'Run: python -m pip install -r "{REQUIREMENTS}"')
        sys.exit(2)
    return py3d

# ============================================================================
# model.cfg: CfgModels > <model> > Animations
# ============================================================================
_CFG_TOKEN = re.compile(r'"(?:[^"]|"")*"|[A-Za-z0-9_.\-+]+|[{}:;=\[\],]')


class CfgClass:
    """One class of a config file: its parent name, child classes and plain properties."""

    def __init__(self, name, parent=None):
        self.name, self.parent = name, parent
        self.classes = {}  # lower name -> CfgClass
        self.props = {}    # lower name -> str value (first value of an array)


def parse_cfg(text):
    """Parse config syntax (model.cfg, config.cpp) into a CfgClass tree.

    Comments and preprocessor lines are dropped; anything the parser does not
    understand is skipped, so a broken file gives a partial tree, not an error.
    """
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    text = re.sub(r'(?m)^\s*#.*$', ' ', text)
    toks = _CFG_TOKEN.findall(text)
    root = CfgClass("")
    stack = [root]
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if t == "}":
            if len(stack) > 1:
                stack.pop()
            i += 1
        elif t == "class" and i + 1 < n:
            name, j, parent = toks[i + 1], i + 2, None
            if j < n and toks[j] == ":" and j + 1 < n:
                parent, j = toks[j + 1], j + 2
            if j < n and toks[j] == "{":
                node = CfgClass(name, parent)
                stack[-1].classes[name.lower()] = node
                stack.append(node)
            i = j + 1
        elif i + 1 < n and toks[i + 1] in ("=", "["):
            j = i + 1
            while j < n and toks[j] != "=":
                j += 1
            value = None
            k = j + 1
            while k < n and toks[k] not in (";", "}"):
                if toks[k] not in ("{", ","):
                    value = toks[k][1:-1] if toks[k].startswith('"') else toks[k]
                    break
                k += 1
            stack[-1].props[t.lower()] = value
            while k < n and toks[k] != ";":
                k += 1
            i = k + 1
        else:
            i += 1
    return root


def model_animations(model_cfg_text, model_name):
    """The animations model.cfg gives a model, as {name: {selection, axis, begin, end, ...}}.

    Returns None when CfgModels has no class for the model. A model class without
    its own Animations uses its parent's, and an animation class inherits the
    properties of the animation it extends, as the engine resolves them.
    """
    models = parse_cfg(model_cfg_text).classes.get("cfgmodels")
    if models is None:
        return None
    node = models.classes.get(model_name.lower())
    if node is None:
        return None
    seen = set()
    while node is not None and "animations" not in node.classes and node.name.lower() not in seen:
        seen.add(node.name.lower())
        node = models.classes.get((node.parent or "").lower())
    if node is None or "animations" not in node.classes:
        return {}
    anims = node.classes["animations"].classes

    def props(anim, depth=0):
        base = anims.get((anim.parent or "").lower())
        merged = props(base, depth + 1) if base is not None and depth < 16 else {}
        merged.update(anim.props)
        return merged

    return {a.name: props(a) for a in anims.values()}


def check_animations(anims, lod_map):
    """Check each model.cfg animation against the model: its selection in the Visual LOD,
    its axis (exactly 2 points) and its begin and end points in the Memory LOD."""
    issues = []
    visual = lod_map["Visual"][1] if "Visual" in lod_map else None
    memory = lod_map["Memory"][1] if "Memory" in lod_map else None

    def find(lod, name):
        # Selection names match without case in model.cfg lookups.
        return next((s for k, s in lod.selections.items() if k.lower() == name.lower()), None)

    for anim, p in anims.items():
        sel = p.get("selection")
        if sel and visual is not None:
            found = find(visual, sel)
            if found is None:
                issues.append(("CRITICAL",
                    f"Animation '{anim}': Visual LOD has no '{sel}' selection. "
                    f"The animation will silently do nothing."))
            elif len(found.points) == 0:
                issues.append(("WARNING",
                    f"Animation '{anim}': Visual LOD selection '{sel}' has 0 vertices, nothing will animate."))
        if memory is None:
            continue
        axis = p.get("axis")
        if axis:
            found = find(memory, axis)
            if found is None:
                issues.append(("CRITICAL",
                    f"Animation '{anim}': Memory LOD has no '{axis}' axis selection."))
            elif len(found.points) != 2:
                issues.append(("CRITICAL",
                    f"Animation '{anim}': axis '{axis}' has {len(found.points)} points, MUST have exactly 2 "
                    f"(start and end of the axis)."))
        for key in ("begin", "end"):
            point = p.get(key)
            if point and find(memory, point) is None:
                issues.append(("CRITICAL",
                    f"Animation '{anim}': Memory LOD has no '{point}' point ({key} of the axis)."))
    return issues


def find_model_cfg(p3d_path, root, name="model.cfg"):
    """The model.cfg that binarize uses for a model: in its folder or the nearest parent, up to root.

    With name="config.cpp" it finds the nearest config.cpp the same way.
    """
    folder, root = Path(p3d_path).resolve().parent, Path(root).resolve()
    while True:
        cfg = folder / name
        if cfg.is_file():
            return str(cfg)
        if folder == root or folder.parent == folder:
            return None
        folder = folder.parent

# ============================================================================
# LOD classification
# ============================================================================
def classify_lod(resolution):
    """Map an MLOD resolution value to a LOD type name.

    DayZ scheme (Tier 2, .claude/skills/_shared/conventions/assets.md, "LOD
    canonical resolutions"): Visual < 1000, ShadowVolume 10000-19999 (10000
    shadow volume, 11000 shadow buffer), Geometry 1e13, GeoPhys 4e13 (the
    PhysX geometry), Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15.
    """
    if resolution < 1000:
        return "Visual"
    if 1e4 <= resolution < 2e4:
        return "ShadowVolume"
    if 9.9e12 <= resolution <= 1.1e13:
        return "Geometry"
    if 3.9e13 <= resolution <= 4.1e13:
        return "GeoPhys"
    if 6.9e15 <= resolution <= 7.1e15:
        return "FireGeo"
    if 5.9e15 <= resolution <= 6.1e15:
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
    """Check that required LODs exist and note missing recommended ones.

    GeoPhys (4e13) is not checked: few vanilla DayZ models ship one (see the
    LOD table in .claude/skills/_shared/conventions/assets.md), so its absence is normal.
    """
    issues = []
    if "Geometry" not in lod_map:
        issues.append(("CRITICAL", "Missing Geometry LOD (res ~1e13). No collision or action targeting possible."))
    if "Memory" not in lod_map:
        issues.append(("CRITICAL", "Missing Memory LOD (res ~1e15). No animation axes, no bounding data."))
    if "Visual" not in lod_map:
        issues.append(("CRITICAL", "Missing Visual LOD (res 0.0). Object will be invisible."))
    if "ViewGeo" not in lod_map:
        issues.append(("NOTE", "Missing ViewGeo LOD (res ~6e15). Vanilla interactive items carry one for "
                               "cursor/action raycasts; add it if actions don't appear on this object."))
    if "FireGeo" not in lod_map:
        issues.append(("NOTE", "Missing FireGeo LOD (res ~7e15). No ballistic damage zones."))
    return issues


def check_component_naming(lod):
    """Check Component01 uses correct case."""
    issues = []
    sels = list(lod.selections.keys())
    has_correct = 'Component01' in sels
    wrong_case = [s for s in sels if s.lower() == 'component01' and s != 'Component01']
    has_any = any(s.lower().startswith('component') for s in sels)
    if wrong_case and not has_correct:
        label = " (lowercase)" if wrong_case[0] == 'component01' else ""
        issues.append(("CRITICAL",
            f"Found '{wrong_case[0]}'{label}. Engine requires exactly 'Component01' (uppercase C, "
            "lowercase rest). Collision silently fails with wrong case."))
    elif not has_any:
        issues.append(("CRITICAL",
            "No Component selection found. Geometry LOD requires 'Component01' for collision."))
    elif not has_correct:
        found = [s for s in sels if s.lower().startswith('component')]
        issues.append(("WARNING", f"Component selection '{found[0]}': verify exact case is 'Component01'."))
    return issues


def check_component_coverage(lod):
    """Check the ComponentNN selections together cover all vertices and faces.

    A non-convex Geometry LOD is split into convex Component01..ComponentNN
    pieces, so coverage is the union of every component, not Component01 alone."""
    issues = []
    comps = [sel for name, sel in lod.selections.items() if re.fullmatch(r'Component\d+', name)]
    if not comps:
        return issues
    points = set().union(*(sel.points for sel in comps))
    faces = set().union(*(sel.faces for sel in comps))
    if len(points) < len(lod.points):
        issues.append(("WARNING",
            f"The Component selections cover {len(points)}/{len(lod.points)} vertices. "
            f"Uncovered vertices won't participate in collision."))
    if len(faces) < len(lod.faces):
        issues.append(("WARNING",
            f"The Component selections cover {len(faces)}/{len(lod.faces)} faces. "
            f"Uncovered faces won't register raycasts."))
    return issues


def config_sets_autocenter_zero(config_path):
    """True when some class in the config.cpp sets autocenter = 0."""
    if not config_path:
        return False
    try:
        text = Path(config_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    def walk(node):
        return node.props.get("autocenter") == "0" or any(walk(c) for c in node.classes.values())

    return walk(parse_cfg(text))


def check_autocenter_prop(lod, config_wants_zero=False):
    """Check autocenter=0 LOD property, needed only when config.cpp sets autocenter = 0.

    Kits and ordinary items must not use autocenter = 0, so a model whose config
    does not set it gets no finding.
    """
    issues = []
    if not config_wants_zero:
        return issues
    props = dict(lod.properties) if lod.properties else {}
    value = props.get('autocenter')
    if value is None:
        issues.append(("WARNING",
            "Missing 'autocenter=0' LOD property. For Inventory_Base items with "
            "autocenter=0 in config.cpp, this property must ALSO be in the LOD."))
    elif value != '0':
        issues.append(("WARNING",
            f"Geometry LOD has autocenter={value}, but config.cpp sets autocenter = 0. "
            "Set the 'autocenter=0' LOD property so the two agree."))
    return issues


def check_collision_materials(lod, lod_type):
    """Check every face of a collision LOD has a material (references/p3d-killers.md
    section 10). Without one the engine finds no surface: bullets pass through and
    footstep sounds and the action cursor can fail."""
    missing = sum(1 for face in lod.faces if not (face.material or "").strip())
    if not missing:
        return []
    return [("CRITICAL",
             f"{missing}/{len(lod.faces)} faces in the {lod_type} LOD have no material. Assign a "
             "penetration .rvmat (e.g. dz\\data\\data\\penetration\\wood_desk.rvmat) to every face.")]


def check_geometry_mass(lod):
    """Report the Geometry LOD mass (sum of point masses), the mass physics uses."""
    if not lod.mass:
        return [("NOTE", "Geometry LOD has no mass. Physics needs a mass on the Geometry LOD points.")]
    return [("NOTE", f"Geometry LOD mass: {lod.mass:.3f}")]


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
        issues.append(("WARNING", f"{boundary} boundary edges: mesh not watertight (has holes)."))
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


def check_memory_lod(lod, wants_zero=False, has_geometry=True):
    """Check Memory LOD for required points and structure.

    wants_zero (config.cpp sets autocenter = 0) gates the 'pos center' checks:
    references/p3d-killers.md section 5 applies them to autocenter=0 items only.
    has_geometry gates the box_placing note: the hologram uses the Geometry LOD
    bounding box first and box_placing_min/max only as a fallback (section 7).
    """
    issues = []
    sels = list(lod.selections.keys())

    # pos center, for autocenter=0 items only
    if wants_zero and 'pos center' not in sels:
        issues.append(("WARNING",
            "Missing 'pos center' memory point. Engine auto-calculates bounding center, "
            "which may be wrong for tall/asymmetric objects. Add at (0,0,0)."))
    elif wants_zero:
        sel = lod.selections['pos center']
        for pt, w in sel.points.items():
            c = pt.coords
            if abs(c[0]) > 0.5 or abs(c[1]) > 0.5 or abs(c[2]) > 0.5:
                issues.append(("NOTE",
                    f"pos center at ({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f}): "
                    f"for autocenter=0 items this should be near (0,0,0)."))

    # box_placing_min / box_placing_max
    has_min = 'box_placing_min' in sels
    has_max = 'box_placing_max' in sels
    if has_min != has_max:
        issues.append(("WARNING",
            f"Only one of box_placing_min/max found. Both are needed for hologram placement."))
    elif not has_min and not has_geometry and not (
            'boundingbox_min' in sels and 'boundingbox_max' in sels):
        issues.append(("NOTE",
            "No box_placing_min/max points and no Geometry LOD. Deployable items need one "
            "of them for hologram placement."))

    # Faces in Memory LOD (should be zero)
    if len(lod.faces) > 0:
        issues.append(("WARNING",
            f"Memory LOD has {len(lod.faces)} faces; it should have 0. "
            f"Only single-vertex points belong in Memory LOD."))

    return issues


def check_visual_lod(lod):
    """Check Visual LOD for path issues and placement. Animations are checked
    against model.cfg by check_animations."""
    issues = []

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
                    f"Line {i}: Absolute P:\\ path '{m}': breaks on other machines. "
                    f"Use game-relative path (remove 'P:\\' prefix)."))
    except Exception as e:
        issues.append(("ERROR", f"Cannot read {filepath}: {e}"))
    return issues


# ============================================================================
# MAIN AUDIT
# ============================================================================

def audit_p3d(filepath, model_cfg=None, config=None):
    """Full audit of one P3D file.

    model_cfg is the model.cfg whose animations are checked; config is the
    config.cpp that decides whether the autocenter LOD property is needed.
    """
    print(f"\n{'='*70}")
    print(f"AUDITING P3D: {filepath}")
    print(f"{'='*70}")

    try:
        with open(filepath, 'rb') as f:
            sig = f.read(4)
            if sig != b'MLOD':
                print(f"  {h.FAIL} Not MLOD format (sig={sig}). Cannot audit ODOL. Provide source MLOD.")
                return False
            f.seek(0)
            p = load_py3d().P3D(f)
    except Exception as e:
        print(f"  {h.FAIL} Failed to read: {e}")
        return False

    size = os.path.getsize(filepath)
    print(f"  Size: {size} bytes, LODs: {len(p.lods)}")

    all_issues = []
    lod_map = {}

    # Classify LODs. The first LOD of each type wins, so with several Visual
    # LODs (resolutions 0, 1, 2, ...) the audited one is LOD0, the highest detail.
    for i, lod in enumerate(p.lods):
        lt = classify_lod(lod.resolution)
        lod_map.setdefault(lt, (i, lod))
        pts, fcs = len(lod.points), len(lod.faces)
        sels = list(lod.selections.keys())
        props = dict(lod.properties) if lod.properties else {}
        print(f"  LOD[{i}] {lt} (res={lod.resolution:.1e}): {pts}v {fcs}f sels={sels} props={props}")

    # Required LODs
    all_issues.extend(check_required_lods(lod_map))

    # Decided once: gates the autocenter property and the 'pos center' checks.
    wants_zero = config_sets_autocenter_zero(config)

    # Collision LODs
    for lt in ["Geometry", "GeoPhys", "FireGeo", "ViewGeo"]:
        if lt not in lod_map:
            continue
        idx, lod = lod_map[lt]
        print(f"\n  --- {lt} LOD[{idx}] ---")
        if len(lod.points) > 0:
            xs = [pt.coords[0] for pt in lod.points]
            ys = [pt.coords[1] for pt in lod.points]
            zs = [pt.coords[2] for pt in lod.points]
            print(f"  BBox: X=[{min(xs):.3f}..{max(xs):.3f}] Y=[{min(ys):.3f}..{max(ys):.3f}] Z=[{min(zs):.3f}..{max(zs):.3f}]")

        # Component01 and the autocenter property belong only on the Geometry LOD;
        # running those checks on GeoPhys/FireGeo flags valid vanilla models. There is no winding check:
        # the centroid heuristic flags every Blender export (left-handed transform);
        # see references/winding-methodology.md for the manual method.
        # Every collision LOD needs a material on each face (killer 10); ViewGeo gets only that check.
        if lt == "Geometry":
            check_fns = [check_component_naming, check_component_coverage,
                         lambda g: check_autocenter_prop(g, wants_zero), check_geometry_mass, check_watertight,
                         check_degenerate_faces]
        elif lt == "ViewGeo":
            check_fns = []
        else:
            check_fns = [check_watertight, check_degenerate_faces]
        check_fns.append(lambda g, lt=lt: check_collision_materials(g, lt))
        for check_fn in check_fns:
            results = check_fn(lod)
            for sev, msg in results:
                print(f"  {sev}: {msg}")
                all_issues.append((sev, msg))

    # Memory LOD
    if "Memory" in lod_map:
        idx, lod = lod_map["Memory"]
        print(f"\n  --- Memory LOD[{idx}] ---")
        results = check_memory_lod(lod, wants_zero, "Geometry" in lod_map)
        for sev, msg in results:
            print(f"  {sev}: {msg}")
            all_issues.append((sev, msg))

    # Visual LOD
    if "Visual" in lod_map:
        idx, lod = lod_map["Visual"]
        print(f"\n  --- Visual LOD[{idx}] ---")
        results = check_visual_lod(lod)
        for sev, msg in results:
            print(f"  {sev}: {msg}")
            all_issues.append((sev, msg))

    # Animations named in model.cfg
    print(f"\n  --- Animations ---")
    if model_cfg is None:
        print("  No model.cfg given (--model-cfg, or one beside the model under --scan-dir); not checked.")
    else:
        try:
            text = Path(model_cfg).read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            text = None
            all_issues.append(("CRITICAL", f"Cannot read {model_cfg}: {e}"))
            print(f"  CRITICAL: Cannot read {model_cfg}: {e}")
        anims = model_animations(text, Path(filepath).stem) if text is not None else {}
        if anims is None:
            msg = f"{model_cfg} has no CfgModels class {Path(filepath).stem}; animations not checked."
            print(f"  NOTE: {msg}")
            all_issues.append(("NOTE", msg))
        else:
            print(f"  {len(anims)} animation(s) in {model_cfg}: {sorted(anims)}")
            for sev, msg in check_animations(anims, lod_map):
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
    return not any(sev in ("CRITICAL", "WARNING", "ERROR") for sev, _ in issues)


def scan_directory(dirpath):
    """Scan entire mod directory for all auditable files."""
    print(f"\nScanning directory: {dirpath}")
    all_pass = True

    # P3D files
    p3d_files = glob.glob(os.path.join(dirpath, '**', '*.p3d'), recursive=True)
    for f in sorted(p3d_files):
        if not audit_p3d(f, find_model_cfg(f, dirpath), find_model_cfg(f, dirpath, "config.cpp")):
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="DayZ P3D Audit: Complete Model Validator")
    parser.add_argument('files', nargs='*', help='.p3d files (or text files) to audit')
    parser.add_argument('--config', help='config.cpp to check for absolute P-drive paths '
                        '(also decides whether the Geometry LOD needs the autocenter property)')
    parser.add_argument('--model-cfg', help='model.cfg whose CfgModels animations are checked against '
                        'the .p3d (also scanned for absolute P-drive paths)')
    parser.add_argument('--rvmat', nargs='*', default=[], help='.rvmat files to check for absolute P-drive paths')
    parser.add_argument('--scan-dir', help='Scan a whole mod directory (ignores the other inputs)')
    args = parser.parse_args(argv)

    if not (args.files or args.config or args.model_cfg or args.rvmat or args.scan_dir):
        parser.error("nothing to audit: give .p3d files, --config, --model-cfg, --rvmat or --scan-dir")

    if args.scan_dir and not os.path.isdir(args.scan_dir):
        print(f"{h.FAIL} Directory not found: {args.scan_dir}")
        sys.exit(1)

    h.gate_on_preflight()
    all_pass = True

    if args.scan_dir:
        if not scan_directory(args.scan_dir):
            all_pass = False
    else:
        targets = [(f, None) for f in args.files]
        if args.config:
            targets.append((args.config, "config.cpp"))
        if args.model_cfg:
            targets.append((args.model_cfg, "model.cfg"))
        targets.extend((rv, ".rvmat") for rv in args.rvmat)
        for f, label in targets:
            if not os.path.isfile(f):
                print(f"{h.FAIL} File not found: {f}")
                all_pass = False
            elif label is None and f.lower().endswith('.p3d'):
                cfg = args.model_cfg if args.model_cfg and os.path.isfile(args.model_cfg) else None
                config = args.config if args.config and os.path.isfile(args.config) else None
                if not audit_p3d(f, cfg, config):
                    all_pass = False
            elif not audit_text_file(f, label or "file"):
                all_pass = False

    print(f"\n{'='*70}")
    print(f"OVERALL: {'ALL PASSED' if all_pass else 'ISSUES FOUND: fix before building PBO'}")
    print(f"{'='*70}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
