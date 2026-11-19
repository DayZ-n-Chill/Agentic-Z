#!/usr/bin/env python3
"""
DayZ P3D audit: validates MLOD .p3d models and scans config.cpp, model.cfg and
.rvmat files for absolute P-drive paths. Reports findings; never modifies files.

Usage:
    python audit_p3d.py model.p3d [model2.p3d ...]
    python audit_p3d.py model.p3d --config path/to/config.cpp
    python audit_p3d.py model.p3d --model-cfg path/to/model.cfg
    python audit_p3d.py --rvmat a.rvmat --rvmat b.rvmat  (repeat --rvmat once per file)
    python audit_p3d.py --scan-dir path/to/mod/  (scans all .p3d, config.cpp, .rvmat, model.cfg)

With a model.cfg (--model-cfg, or the nearest one under --scan-dir) each
animation in CfgModels > <model> > Animations is checked against the model.
The Geometry LOD autocenter property is only checked when the config.cpp
(--config, or the nearest one under --scan-dir) has a class with autocenter = 0.
The same config.cpp feeds the wheel-slot check of a wheeled vehicle body.

Gates on /dayz-preflight. Reads .p3d files with py3d: the DayZ fork kept in
this repo at scripts/tools/py3d when that folder is there, otherwise an
installed py3d (../requirements.txt installs that same repo copy as a package,
run from the repo root); exits 2 when neither is found. With the fork (1.6.0 or later) its P3D.validate() findings,
the winding checks among them, are added to this script's own.
"""

import sys, os, re, glob, argparse, importlib.util, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import skill_helpers as h  # noqa: E402


REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
# The DayZ fork of py3d kept in this repo: the one py3d copy every skill uses.
# A checkout without that folder falls back to an installed py3d.
REPO_FORK = Path(__file__).resolve().parents[3] / "scripts" / "tools" / "py3d" / "py3d" / "__init__.py"
FORK_MIN_VERSION = (1, 6, 0)
_fork_module = None


def load_py3d():
    """py3d: the repo's DayZ fork when it is there, else the installed py3d.

    The fork is loaded from its file under a private module name, so it never
    replaces a py3d another script in the same process imported. Exits 2 with
    an install hint when neither is found.
    """
    global _fork_module
    if REPO_FORK.is_file():
        if _fork_module is None:
            _fork_module = h.load_module("py3d_dayz_fork", REPO_FORK)
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


def fork_version(py3d):
    """The version of a DayZ fork of py3d as a tuple, or None for any other py3d."""
    if not getattr(py3d, "IS_DAYZ_FORK", False):
        return None
    try:
        return tuple(int(x) for x in str(py3d.__version__).split("."))
    except (AttributeError, ValueError):
        return None

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


def find_selection(lod, name):
    """The LOD selection called name, matched without case (None when absent).

    Used for every lookup by name: model.cfg animation selections and axes, and
    Memory LOD points such as 'pos center' and box_placing_min/max.
    """
    return next((s for k, s in lod.selections.items() if k.lower() == name.lower()), None)


def check_animations(anims, lod_map):
    """Check each model.cfg animation against the model: its selection in the Visual LOD,
    its axis (exactly 2 points) and its begin and end points in the Memory LOD."""
    issues = []
    visual = lod_map["Visual"][1] if "Visual" in lod_map else None
    memory = lod_map["Memory"][1] if "Memory" in lod_map else None
    find = find_selection

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

    DayZ scheme (Tier 2, skills/_shared/conventions/assets.md, "LOD
    canonical resolutions"): Visual < 1000, ShadowVolume 10000-19999 (10000
    shadow volume, 11000 shadow buffer), Geometry 1e13, GeoPhys 4e13 (the
    PhysX geometry), Memory 1e15, LandContact 2e15, ViewGeo 6e15, FireGeo 7e15.
    Roadway 3e15, Paths 4e15 and HitPoints 5e15 are named too (the vanilla
    scan in skills/_shared/models/lods.md counts them); no check runs on them.
    """
    if 2.9e15 <= resolution <= 3.1e15:
        return "Roadway"
    if 3.9e15 <= resolution <= 4.1e15:
        return "Paths"
    if 4.9e15 <= resolution <= 5.1e15:
        return "HitPoints"
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
    LOD table in skills/_shared/conventions/assets.md), so its absence is normal.
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
    """Check the Geometry LOD has a Component01 selection.

    Lowercase 'component01' is fine: every binarized vanilla model on P:\\
    stores it that way, so it is only a NOTE. Other spellings (COMPONENT01)
    are a WARNING to check, which does not fail the run."""
    issues = []
    sels = list(lod.selections.keys())
    has_correct = 'Component01' in sels
    wrong_case = [s for s in sels if s.lower() == 'component01' and s != 'Component01']
    has_any = any(s.lower().startswith('component') for s in sels)
    if wrong_case and not has_correct:
        if wrong_case[0] == 'component01':
            issues.append(("NOTE",
                "Found 'component01' (lowercase). That is fine: binarized vanilla models store it in "
                "lowercase too. Object Builder's own spelling is 'Component01'."))
        else:
            issues.append(("WARNING",
                f"Found '{wrong_case[0]}'. Vanilla models use 'Component01' (or 'component01' once "
                "binarized); rename it to 'Component01' to be safe."))
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
    pieces, so coverage is the union of every component, not Component01 alone.
    The match ignores case, since binarized models store 'component01'."""
    issues = []
    comps = [sel for name, sel in lod.selections.items() if re.fullmatch(r'component\d+', name, re.IGNORECASE)]
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


def config_sets_autocenter_zero(config_path, p3d_path):
    """True when a class whose model= is this p3d sets autocenter = 0.

    Only the classes that use this model count, so a kit sharing a config.cpp
    with a proxy that sets autocenter = 0 is not flagged. Both model and
    autocenter are inherited from parent classes defined in the same file.
    Raises OSError when config_path cannot be read, so the caller reports it
    instead of silently treating the model as not needing autocenter = 0.
    """
    if not config_path or not p3d_path:
        return False
    text = Path(config_path).read_text(encoding="utf-8", errors="ignore")

    classes = {}

    def collect(node):
        for key, child in node.classes.items():
            classes.setdefault(key, child)
            collect(child)

    collect(parse_cfg(text))

    def inherited(node, prop):
        seen = set()
        while node is not None and id(node) not in seen:
            seen.add(id(node))
            if prop in node.props:
                return node.props[prop]
            node = classes.get((node.parent or "").lower())
        return None

    target = Path(p3d_path).name.lower()
    for node in classes.values():
        model = inherited(node, "model")
        if model and model.replace("\\", "/").rsplit("/", 1)[-1].lower() == target \
                and inherited(node, "autocenter") == "0":
            return True
    return False


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
    footstep sounds can fail.

    Geometry, GeoPhys and FireGeo faces without a material are CRITICAL. ViewGeo
    faces are only a WARNING: View Geometry blocks sight and the action cursor,
    and BI models commonly leave its faces without a penetration material, so a
    missing one there is not known to break anything (references section 10)."""
    missing = sum(1 for face in lod.faces if not (face.material or "").strip())
    if not missing:
        return []
    if lod_type == "ViewGeo":
        return [("WARNING",
                 f"{missing}/{len(lod.faces)} faces in the ViewGeo LOD have no material. Usually fine; "
                 "assign a penetration .rvmat if the action cursor misses this object.")]
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


def face_area(coords):
    """Area of a polygon (triangle or quad) from its vertex coordinates.

    The whole polygon counts, not only its first three vertices: the quad is
    split into the fan triangles (v0, v1, v2) and (v0, v2, v3), whose normals are
    summed as vectors (Newell's method). A quad whose first three vertices lie
    on one line keeps its real area, and a quad that folds onto itself (a bow
    tie whose halves cancel) comes out as zero.
    """
    nx = ny = nz = 0.0
    x0, y0, z0 = coords[0]
    for (x1, y1, z1), (x2, y2, z2) in zip(coords[1:], coords[2:]):
        ax, ay, az = x1 - x0, y1 - y0, z1 - z0
        bx, by, bz = x2 - x0, y2 - y0, z2 - z0
        nx += ay * bz - az * by
        ny += az * bx - ax * bz
        nz += ax * by - ay * bx
    return 0.5 * (nx * nx + ny * ny + nz * nz) ** 0.5


def check_degenerate_faces(lod):
    """Check for zero-area faces, measured over the whole polygon (face_area)."""
    issues = []
    degen = 0
    for face in lod.faces:
        verts = face.vertices
        if len(verts) < 3 or face_area([v.point.coords for v in verts]) < 1e-8:
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

    def has(name):
        return find_selection(lod, name) is not None

    # pos center, for autocenter=0 items only. Names match without case, as in
    # the animation lookups, so 'Pos Center' counts.
    center = find_selection(lod, 'pos center')
    if wants_zero and center is None:
        issues.append(("WARNING",
            "Missing 'pos center' memory point. Engine auto-calculates bounding center, "
            "which may be wrong for tall/asymmetric objects. Add at (0,0,0)."))
    elif wants_zero:
        for pt, w in center.points.items():
            c = pt.coords
            if abs(c[0]) > 0.5 or abs(c[1]) > 0.5 or abs(c[2]) > 0.5:
                issues.append(("NOTE",
                    f"pos center at ({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f}): "
                    f"for autocenter=0 items this should be near (0,0,0)."))

    # box_placing_min / box_placing_max
    has_min = has('box_placing_min')
    has_max = has('box_placing_max')
    if has_min != has_max:
        issues.append(("WARNING",
            f"Only one of box_placing_min/max found. Both are needed for hologram placement."))
    elif not has_min and not has_geometry and not (
            has('boundingbox_min') and has('boundingbox_max')):
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

    # No autocenter advice here: config.cpp decides whether a model needs
    # autocenter = 0 (check_autocenter_prop), and kits and ordinary items must not use it.
    return issues


# ============================================================================
# WHOLE-MODEL CHECKS: vertex budget, vehicle body, needle triangles, wheel slots
# ============================================================================
# Each takes the whole model and names the LOD it found a problem in. The facts
# behind them are in references/killers-detail.md and references/vehicle-checks.md.

_DAMPER_RE = re.compile(r'damper', re.I)


def is_vehicle_body(p):
    """True for a wheeled-vehicle body: a model with a suspension 'damper' selection.

    A body carries selections such as 'wheel_1_1_damper' or 'wheel_1_1_damper_land';
    a wheel model that is only a proxy on the body does not. Keying on 'damper'
    keeps a lone wheel (which has 'wheel' selections) from counting as a body.
    """
    return any(_DAMPER_RE.search(name) for lod in p.lods for name in lod.selections)


def check_lod0_vertex_budget(p):
    """Check the most detailed Visual LOD against the 16-bit vertex ceiling.

    The script counts resolved vertices, the distinct (point, normal, uv) triples
    of the face corners, not the raw point or face-corner counts: a model with
    96,585 face corners that resolved to 22,143 vertices loaded fine. Over 65,535
    resolved vertices is CRITICAL. The real ceiling is per model and can be lower,
    because binarize splits vertices further than the triples show, so binarize is
    the gate. Raw counts over 65,536 with fewer resolved vertices are a WARNING, and
    so, separately, is a heavy LOD on a vehicle body, whose proxies add their own
    vertices in game. A single file cannot add the proxies up.
    """
    issues = []
    visual = [(lod.resolution, i, lod) for i, lod in enumerate(p.lods) if classify_lod(lod.resolution) == "Visual"]
    if not visual:
        return issues
    _, i, lod = min(visual, key=lambda item: item[:2])
    nverts, nidx, nnorm = len(lod.points), lod.num_vertices, len(lod.facenormals)
    resolved = {(v.point_index, v.normal_index, tuple(v.uv)) for face in lod.faces for v in face.vertices}
    nres = len(resolved)
    if nres > 65535:
        issues.append(("CRITICAL",
            f"LOD[{i}] Visual resolves to {nres} unique vertices (point x normal x uv), over the 65535 "
            f"of a 16-bit index: the model fails to load or renders invisible "
            f"(points={nverts}, face corners={nidx})."))
        return issues
    if nverts > 65536 or nidx > 65536:
        issues.append(("WARNING",
            f"LOD[{i}] Visual raw counts exceed 65536 (points={nverts}, face corners={nidx}) and it "
            f"resolves to {nres} unique vertices. The ceiling is per model and can be lower than 65535, "
            f"because binarize splits vertices further; binarize the model to know whether it loads."))
    if is_vehicle_body(p) and (nnorm > 16384 or nverts > 32768):
        issues.append(("WARNING",
            f"LOD[{i}] Visual is heavy for a vehicle body (points={nverts}, normals={nnorm}). The vertex "
            f"ceiling for the body plus every proxy placed on it is per model and lower than 65536 "
            f"(46133 resolved vertices on one measured helicopter); find it with binarize before "
            f"adding proxies."))
    return issues


def check_geometry_class_vehicle(p):
    """Check a wheeled vehicle body's Geometry LOD carries the named property class=vehicle.

    Every vanilla wheeled body under P:\\DZ\\vehicles\\wheeled\\ carries it. This is
    parity with vanilla only: leaving it out was tested in game and did not stop
    the wheels simulating (that is check_wheel_slot_firegeo's subject).
    """
    issues = []
    if not is_vehicle_body(p):
        return issues
    for i, lod in enumerate(p.lods):
        if classify_lod(lod.resolution) != "Geometry":
            continue
        props = dict(lod.properties) if lod.properties else {}
        if (props.get("class") or "").strip().lower() != "vehicle":
            issues.append(("CRITICAL",
                f"LOD[{i}] Geometry of a wheeled vehicle has no named property class=vehicle. Every "
                f"vanilla wheeled body carries it; add it to match (it is not what makes wheels "
                f"simulate: see the wheel-slot check)."))
    return issues


NEEDLE_MIN_AREA = 1e-6   # m^2
NEEDLE_MIN_RATIO = 1e-4  # area / longest edge^2
NEEDLE_LODS = ("Geometry", "FireGeo", "ViewGeo")
_COMPONENT_RE = re.compile(r"component\d+", re.I)
# py3d's proxy selection name: proxy:<path>.<index>, 'proxy:' in any case.
_PROXY_NAME_RE = re.compile(r"^proxy:(?P<path>.+)\.(?P<index>\d+)$", re.IGNORECASE)


def triangle_area_ratio(a, b, c):
    """Area of the triangle a, b, c (each an (x, y, z)) and that area over the
    square of its longest edge: sqrt(3)/4 = 0.433 for an equilateral triangle,
    the most it can be, and 0.0 when the three points coincide."""
    ab = [b[i] - a[i] for i in range(3)]
    ac = [c[i] - a[i] for i in range(3)]
    bc = [c[i] - b[i] for i in range(3)]
    cross = (ab[1] * ac[2] - ab[2] * ac[1],
             ab[2] * ac[0] - ab[0] * ac[2],
             ab[0] * ac[1] - ab[1] * ac[0])
    area = 0.5 * math.sqrt(sum(x * x for x in cross))
    longest = max(sum(x * x for x in e) for e in (ab, ac, bc))
    return area, (area / longest if longest > 0.0 else 0.0)


def needle_triangles(points, faces, min_area=NEEDLE_MIN_AREA, min_ratio=NEEDLE_MIN_RATIO):
    """The needle triangles of faces, as (face, corners, area, ratio).

    points is a sequence of (x, y, z) and faces a sequence of faces, each a
    sequence of indices into points. Each face is split into triangles from
    its first corner, so a quad (a, b, c, d) reads as (a, b, c) and (a, c, d).
    A triangle is a needle when its area is under min_area or its area over the
    square of its longest edge, the ratio, is under min_ratio. Needles come in
    the order of faces: face is a needle's position in faces and corners its
    three point indices.
    """
    found = []
    for n, face in enumerate(faces):
        for j in range(1, len(face) - 1):
            corners = (face[0], face[j], face[j + 1])
            area, ratio = triangle_area_ratio(*[points[k] for k in corners])
            if area < min_area or ratio < min_ratio:
                found.append((n, corners, area, ratio))
    return found


def _opposite_longest_edge(points, corners):
    """The corner of a triangle that faces its longest edge."""
    def d2(i, j):
        return sum((points[i][k] - points[j][k]) ** 2 for k in range(3))
    a, b, c = corners
    return max((d2(b, c), a), (d2(a, c), b), (d2(a, b), c))[1]


def proxy_triangles(lod):
    """ids of the proxy triangles of a LOD, by the rule py3d's DayZ fork uses.

    A proxy is a selection named proxy:<path>.<index> that holds exactly one
    face, a triangle, and as its points exactly that triangle's three corners.
    A selection under a proxy name with any other shape is not a proxy, and its
    faces are read like any other face.
    """
    out = set()
    for name, sel in lod.selections.items():
        if not _PROXY_NAME_RE.match(name):
            continue
        if len(sel.points) != 3 or len(sel.faces) != 1:
            continue
        face = next(iter(sel.faces))
        if len(face.vertices) != 3:
            continue
        corners = {id(vx.point) for vx in face.vertices}
        if len(corners) == 3 and corners == set(map(id, sel.points)):
            out.add(id(face))
    return out


def check_collision_needle_triangles(p):
    """Check the components of the Geometry, View and Fire LODs for needle triangles.

    Measured in DayZ 1.29: two convex hulls that each held one needle took no
    ray in geom, view or fire, and binarize said nothing. Built again without
    the point opposite each needle's longest edge, they took every ray. The
    engine's own limit lies between a ratio of 4.6e-7 (no hit) and 1.19e-4
    (hit); this check fails a triangle under NEEDLE_MIN_AREA or NEEDLE_MIN_RATIO.

    Every face of every ComponentNN selection is read (any case; a face at
    weight 0 is not in the selection, and proxy triangles are left out). A face
    in no component is the coverage check's subject, not this one's.
    """
    issues = []
    for i, lod in enumerate(p.lods):
        kind = classify_lod(lod.resolution)
        if kind not in NEEDLE_LODS:
            continue
        number = {id(pt): n for n, pt in enumerate(lod.points)}
        points = [pt.coords for pt in lod.points]
        index = {id(face): n for n, face in enumerate(lod.faces)}
        proxies = proxy_triangles(lod)
        for name, sel in lod.selections.items():
            if not _COMPONENT_RE.fullmatch(name):
                continue
            faces = sorted(((index[id(face)], face) for face, weight in sel.faces.items()
                            if weight and id(face) in index and id(face) not in proxies),
                           key=lambda item: item[0])
            corners = [[number[id(v.point)] for v in face.vertices] for _, face in faces]
            for n, tri, area, ratio in needle_triangles(points, corners):
                issues.append(("CRITICAL",
                    "LOD[%d] %s, %s, face %d: needle triangle (points %d, %d, %d), area %.2e m^2, "
                    "area/longest edge^2 %.2e (this check fails a triangle under %.0e m^2 or %.0e). "
                    "In game a convex hull holding one took no ray in geom, view or fire, and binarize "
                    "said nothing: build the hull again without point %d, the corner opposite the "
                    "longest edge (references/collision-mesh-hygiene.md, 'Needle triangles')."
                    % (i, kind, name, faces[n][0], tri[0], tri[1], tri[2], area, ratio,
                       NEEDLE_MIN_AREA, NEEDLE_MIN_RATIO, _opposite_longest_edge(points, tri))))
    return issues


def _class_body(text, header_re):
    """The text between the braces of the first class whose header matches header_re, or None."""
    m = re.search(header_re, text)
    if not m:
        return None
    start = text.find("{", m.start())
    if start < 0:
        return None
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:j]
    return None


def parse_wheel_selections(config_text):
    """The wheel-slot selections a vehicle config.cpp names, as (selections, slots, note).

    The config links them in two steps: SimulationModule > Axles > <axle> >
    Wheels > <side> has inventorySlot = "<slot>", and CfgSlots > Slot_<slot> has
    name = "<slot>" and selection = "<selection>". Vanilla keeps CfgSlots in
    P:\\scripts\\config.cpp, away from the vehicle classes, and a mod that reuses
    vanilla wheel slots has no CfgSlots of its own. The mapping cannot be read
    then; note says why, and nothing is failed.
    """
    text = strip_comments(config_text)
    axles = _class_body(text, r'class\s+Axles\b')
    if axles is None:
        return set(), set(), "no 'class Axles' block (not a wheeled-vehicle config, or an unusual layout)"
    slots = set(re.findall(r'inventorySlot\s*=\s*"([^"]+)"', axles))
    if not slots:
        return set(), set(), "the Axles block has no inventorySlot entries"
    cfgslots = _class_body(text, r'class\s+CfgSlots\b')
    mapped = {}
    if cfgslots is not None:
        for m in re.finditer(r'class\s+\w+\s*\{([^{}]*)\}', cfgslots):
            name = re.search(r'name\s*=\s*"([^"]+)"', m.group(1))
            selection = re.search(r'selection\s*=\s*"([^"]+)"', m.group(1))
            if name and selection:
                mapped[name.group(1)] = selection.group(1)
    sels = {mapped[slot] for slot in slots if slot in mapped}
    if sels:
        return sels, slots, ""
    if cfgslots is None:
        return set(), slots, ("this config.cpp has no CfgSlots block, so the slot to selection mapping "
                              "could not be read; check the wheel selections in the Fire Geometry LOD by hand")
    return set(), slots, ("CfgSlots has no slot named like a wheel inventorySlot, so the mapping could "
                          "not be read; check by hand")


def check_wheel_slot_firegeo(p, config_text):
    """Check each wheel-slot selection of a vehicle body exists in its Fire Geometry LOD.

    The engine binds a wheel slot to the model through the selection that
    CfgSlots names. When that selection is only in the visual LODs the wheel
    attaches as an item but never simulates: WheelCountPresent() stays 0 while
    WheelCount() is the full count, with no log line (measured in game on a
    custom quad). Runs only for a vehicle body and only with a config.cpp.
    """
    issues = []
    if not is_vehicle_body(p):
        return issues
    fire = [(i, lod) for i, lod in enumerate(p.lods) if classify_lod(lod.resolution) == "FireGeo"]
    if not fire:
        issues.append(("CRITICAL",
            "Wheeled vehicle body has no Fire Geometry LOD, so no wheel-slot selection can be found "
            "in it and the wheels will not simulate."))
        return issues
    sels, _slots, note = parse_wheel_selections(config_text)
    if not sels:
        if note:
            issues.append(("NOTE", f"Wheel-slot check not run: {note}."))
        return issues
    fi, fire_lod = fire[0]
    for sel in sorted(sels):
        found = find_selection(fire_lod, sel)
        if found is None:
            issues.append(("CRITICAL",
                f"Wheel-slot selection '{sel}' (from CfgSlots) is missing from Fire Geometry LOD[{fi}]. "
                f"The wheel will attach but not simulate (WheelCountPresent() = 0), with no log line. "
                f"Add the wheel proxy face of that LOD to a selection named '{sel}', keeping its "
                f"other selections."))
        elif len(found.faces) == 0:
            issues.append(("WARNING",
                f"Wheel-slot selection '{sel}' is in Fire Geometry LOD[{fi}] but holds 0 faces. "
                f"It must hold the wheel proxy face."))
    return issues


# ============================================================================
# py3d DayZ fork: P3D.validate()
# ============================================================================
_FORK_SEVERITY = {"ERROR": "CRITICAL", "WARN": "WARNING"}
# validate() findings this script already reports itself, by the LOD it checks
# them on. Ours know the config.cpp and model.cfg (autocenter, pos center), read
# whole polygons (degenerate faces) or grade the finding differently on purpose
# (P:\ paths on faces are a NOTE in a source model), so the fork's copy is dropped.
_FORK_COVERED = {
    "Geometry": {"ERR_COMPONENT_NAMING", "WARN_COMPONENT_NAMING", "WARN_COMPONENT_COVERAGE",
                 "WARN_AUTOCENTER_MISSING", "WARN_NOT_WATERTIGHT", "WARN_DEGENERATE_FACES"},
    "FireGeo": {"WARN_NOT_WATERTIGHT", "WARN_DEGENERATE_FACES"},
    "Memory": {"WARN_MEMORY_POS_CENTER", "WARN_MEMORY_BOX_PLACING", "WARN_MEMORY_HAS_FACES"},
    "Visual": {"WARN_PDRIVE_PATH"},
    "GeoPhys": {"WARN_LOD_KIND_UNKNOWN"},
}
# The fork guesses an animation's selection from the axis name (<name>_axis
# needs <name>). A rig may bind them under different names in model.cfg.
_FORK_AXIS_GUESS = {"ERR_AXIS_SELECTION_MISSING", "WARN_AXIS_SELECTION_EMPTY"}


def fork_findings(p, py3d, lod_map, model_cfg_checked=False):
    """The findings of the DayZ fork's P3D.validate(), as (severity, message).

    Returns None when py3d is not the DayZ fork at FORK_MIN_VERSION or later,
    so the caller can say the checks did not run. ERROR becomes CRITICAL and
    WARN becomes WARNING. A finding this script reports itself on the same LOD
    is dropped (_FORK_COVERED). The axis-name guess is dropped when model.cfg
    was checked, which reads the real binding, and is only a WARNING without one.
    """
    version = fork_version(py3d)
    if version is None or version < FORK_MIN_VERSION or not hasattr(p, "validate"):
        return None
    try:
        found = p.validate()
    except Exception as e:  # a model the validator cannot walk, such as an index out of its pool
        return [("WARNING", f"py3d validate() stopped: {e}. Its winding and component checks did not run.")]
    checked = {index: kind for kind, (index, _lod) in lod_map.items()}
    issues = []
    for f in found:
        if f.code in _FORK_COVERED.get(checked.get(f.lod), ()):
            continue
        severity = _FORK_SEVERITY.get(f.severity, f.severity)
        msg = f.msg
        if f.code in _FORK_AXIS_GUESS:
            if model_cfg_checked:
                continue
            if severity == "CRITICAL":
                severity = "WARNING"
            msg += (" (Guessed from the axis name; pass --model-cfg to check the selection and axis "
                    "each animation really names.)")
        lod_tag = "" if f.lod is None else f"LOD[{f.lod}] "
        issues.append((severity, f"{lod_tag}[{f.code}] {msg}"))
    return issues


# A double-quoted string, a /* */ comment or a // comment. Strings come first so a
# "//" inside one (url = "http://...") is kept, not read as a comment.
_TEXT_COMMENT = re.compile(r'"[^"\n]*"|/\*.*?\*/|//[^\n]*', re.S)


def strip_comments(text):
    """Blank out // and /* */ comments, keeping strings and line breaks.

    Each comment becomes the newlines it held, so line numbers stay correct.
    """
    def repl(m):
        tok = m.group(0)
        return tok if tok.startswith('"') else "\n" * tok.count("\n")
    return _TEXT_COMMENT.sub(repl, text)


def check_p_drive_paths_in_file(filepath):
    """Check for P:\\ drive paths in text files (config.cpp, .rvmat, model.cfg).

    Each one is a P-DRIVE finding, which fails the run. Paths that appear only
    in a comment are ignored: the engine never reads them.
    """
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = strip_comments(f.read()).split("\n")
        for i, line in enumerate(lines, 1):
            # Match P:\ or P:/ paths (case-insensitive), but not the "p://" inside a
            # URL such as url = "http://www.dayzgame.com" in CfgMods.
            matches = re.findall(r'(?<![A-Za-z0-9])(P:[\\\/][^"\';\s]+)', line, re.IGNORECASE)
            for m in matches:
                issues.append(("P-DRIVE",
                    f"Line {i}: Absolute P:\\ path '{m}': breaks on other machines "
                    f"and fails the run. Use game-relative path (remove 'P:\\' prefix)."))
    except Exception as e:
        issues.append(("ERROR", f"Cannot read {filepath}: {e}"))
    return issues


# ============================================================================
# MAIN AUDIT
# ============================================================================

def audit_p3d(filepath, model_cfg=None, config=None, tally=None):
    """Full audit of one P3D file.

    model_cfg is the model.cfg whose animations are checked; config is the
    config.cpp that decides whether the autocenter LOD property is needed.
    tally, when given, is a dict filled with this file's counts for the
    --scan-dir summary (see tally_issues).
    """
    if tally is None:
        tally = {}
    print(f"\n{'='*70}")
    print(f"AUDITING P3D: {filepath}")
    print(f"{'='*70}")

    try:
        with open(filepath, 'rb') as f:
            sig = f.read(4)
            if sig == b'ODOL':
                print(f"  {h.FAIL} Not MLOD format (sig={sig}): this is a binarized ODOL model, so it "
                      f"was not audited. Audit the MLOD source it was built from (the .p3d Object "
                      f"Builder saves; Addon Builder binarizes it into ODOL when packing the PBO).",
                      file=sys.stderr)
                tally["odol"] = 1
                return False
            if sig != b'MLOD':
                print(f"  {h.FAIL} Not MLOD format (sig={sig}): not a .p3d model this script can read.",
                      file=sys.stderr)
                tally["unreadable"] = 1
                return False
            f.seek(0)
            py3d = load_py3d()
            p = py3d.P3D(f)
    except Exception as e:
        print(f"  {h.FAIL} Failed to read: {e}", file=sys.stderr)
        tally["unreadable"] = 1
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
    # An unreadable config.cpp is an ERROR that fails the run, not a silent "no".
    try:
        wants_zero = config_sets_autocenter_zero(config, filepath)
    except OSError as e:
        wants_zero = False
        msg = f"Cannot read config {config}: {e}. The autocenter and pos center checks were skipped."
        print(f"  ERROR: {msg}")
        all_issues.append(("ERROR", msg))

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
        # running those checks on GeoPhys/FireGeo flags valid vanilla models. This script has no
        # winding check of its own: the centroid heuristic flags every Blender export (left-handed
        # transform). The DayZ fork's validate() adds winding findings below when it is in use;
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

    # Whole-model checks: the vertex budget, the vehicle body checks and needle triangles.
    # The wheel-slot check needs the config.cpp text; an unreadable one was reported above.
    print(f"\n  --- Whole model ---")
    results = check_lod0_vertex_budget(p) + check_geometry_class_vehicle(p) + check_collision_needle_triangles(p)
    if config:
        try:
            config_text = Path(config).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            config_text = None
        if config_text is not None:
            results += check_wheel_slot_firegeo(p, config_text)
    elif is_vehicle_body(p):
        print("  No config.cpp given (--config, or one near the model under --scan-dir): the wheel-slot "
              "selections of this vehicle body were not checked.")
    for sev, msg in results:
        print(f"  {sev}: {msg}")
        all_issues.append((sev, msg))

    # Animations named in model.cfg
    model_cfg_checked = False
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
            model_cfg_checked = text is not None
            print(f"  {len(anims)} animation(s) in {model_cfg}: {sorted(anims)}")
            for sev, msg in check_animations(anims, lod_map):
                print(f"  {sev}: {msg}")
                all_issues.append((sev, msg))

    # The DayZ fork's own validator: winding, component coverage, mass, normals budget.
    print(f"\n  --- py3d validate() ---")
    results = fork_findings(p, py3d, lod_map, model_cfg_checked)
    if results is None:
        print("  Not run: this py3d is not the DayZ fork (scripts/tools/py3d, 1.6.0 or later), so the "
              "winding checks were skipped. Check winding by hand (references/winding-methodology.md).")
    else:
        for sev, msg in results:
            print(f"  {sev}: {msg}")
            all_issues.append((sev, msg))

    # Summary
    tally.update(tally_issues(all_issues))
    crits = sum(1 for s, _ in all_issues if s == "CRITICAL")
    errors = sum(1 for s, _ in all_issues if s == "ERROR")
    warns = sum(1 for s, _ in all_issues if s == "WARNING")
    notes = sum(1 for s, _ in all_issues if s == "NOTE")
    print(f"\n  {'='*50}")
    if crits == 0 and errors == 0 and warns == 0:
        print(f"  RESULT: ALL CHECKS PASSED ({notes} notes)")
    elif errors:
        print(f"  RESULT: {crits} CRITICAL, {errors} ERROR, {warns} WARNING, {notes} NOTE")
    else:
        print(f"  RESULT: {crits} CRITICAL, {warns} WARNING, {notes} NOTE")
    return crits == 0 and errors == 0


def tally_issues(issues):
    """Count (severity, message) issues for the --scan-dir summary.

    'warning' counts only warnings that are not P:\\ paths, so the counts
    never overlap.
    """
    return {
        "critical": sum(1 for sev, _ in issues if sev == "CRITICAL"),
        "p_drive": sum(1 for sev, _ in issues if sev == "P-DRIVE"),
        "warning": sum(1 for sev, _ in issues if sev == "WARNING"),
        "unreadable": sum(1 for sev, _ in issues if sev == "ERROR"),
    }


def describe_tally(t):
    """Summary fragment for one failing file, e.g. '2 CRITICAL, 1 P:\\ path'."""
    if t.get("odol"):
        return "ODOL reject (binarized model; audit the source MLOD)"
    parts = []
    if t.get("critical"):
        parts.append(f"{t['critical']} CRITICAL")
    if t.get("p_drive"):
        parts.append(f"{t['p_drive']} P:\\ path(s)")
    if t.get("warning"):
        parts.append(f"{t['warning']} other WARNING")
    if t.get("unreadable"):
        parts.append("unreadable")
    return ", ".join(parts) or "failed"


def audit_text_file(filepath, label="file", tally=None):
    """Audit a text file for P:\\ paths."""
    print(f"\n{'='*70}")
    print(f"AUDITING {label}: {filepath}")
    print(f"{'='*70}")
    issues = check_p_drive_paths_in_file(filepath)
    for sev, msg in issues:
        print(f"  {sev}: {msg}")
    if not issues:
        print(f"  OK: No P:\\ paths found.")
    if tally is not None:
        tally.update(tally_issues(issues))
    return not any(sev in ("CRITICAL", "P-DRIVE", "ERROR") for sev, _ in issues)


def overall_line(odol, other):
    """Final verdict line from the count of ODOL rejects and of other failed files.

    An ODOL .p3d was never audited, so a run whose only failures are ODOL
    rejects says NOT AUDITED instead of claiming issues were found in it.
    """
    noun = "binarized ODOL .p3d file(s)"
    if not odol and not other:
        return "OVERALL: ALL PASSED"
    if not other:
        return f"OVERALL: NOT AUDITED: {odol} {noun}; audit the MLOD source instead"
    line = "OVERALL: ISSUES FOUND: fix before building PBO"
    if odol:
        line += f" ({odol} {noun} not audited)"
    return line


def scan_directory(dirpath):
    """Scan entire mod directory for all auditable files.

    Ends with a summary: one line of totals (CRITICAL findings, P:\\ paths,
    ODOL rejects), then one line per failing file, so a single binarized
    .p3d in the mod is named instead of hiding inside 'ISSUES FOUND'.
    Returns the tally of each failed file (empty when everything passed).
    """
    print(f"\nScanning directory: {dirpath}")
    results = []  # (path, passed, tally)

    # P3D files. A backup copy (model.bak.p3d, or anything under a *.bak folder) is skipped:
    # it is an older state of a model that is audited under its own name.
    for f in sorted(glob.glob(os.path.join(dirpath, '**', '*.p3d'), recursive=True)):
        if '.bak' in os.path.relpath(f, dirpath).lower():
            print(f"\nSkipping backup model: {f}")
            continue
        t = {}
        ok = audit_p3d(f, find_model_cfg(f, dirpath), find_model_cfg(f, dirpath, "config.cpp"), tally=t)
        results.append((f, ok, t))

    # config.cpp, .rvmat files, model.cfg
    for pattern, label in (('**/config.cpp', "config.cpp"), ('**/*.rvmat', ".rvmat"),
                           ('**/model.cfg', "model.cfg")):
        for f in sorted(glob.glob(os.path.join(dirpath, pattern), recursive=True)):
            t = {}
            ok = audit_text_file(f, label, tally=t)
            results.append((f, ok, t))

    failed = [(f, t) for f, ok, t in results if not ok]
    crit = sum(t.get("critical", 0) for _, t in failed)
    pdrive = sum(t.get("p_drive", 0) for _, t in failed)
    odol = sum(t.get("odol", 0) for _, t in failed)
    print(f"\n{'='*70}")
    print(f"SCAN SUMMARY: {len(failed)} of {len(results)} file(s) failed: "
          f"{crit} CRITICAL, {pdrive} P:\\ path(s), {odol} ODOL reject(s)")
    for f, t in failed:
        print(f"  {os.path.relpath(f, dirpath)}: {describe_tally(t)}")

    return [t for _, t in failed]


def main(argv=None):
    parser = argparse.ArgumentParser(description="DayZ P3D Audit: Complete Model Validator")
    parser.add_argument('files', nargs='*', help='.p3d files (or text files) to audit')
    parser.add_argument('--config', help='config.cpp to check for absolute P-drive paths '
                        '(also decides whether the Geometry LOD needs the autocenter property)')
    parser.add_argument('--model-cfg', help='model.cfg whose CfgModels animations are checked against '
                        'the .p3d (also scanned for absolute P-drive paths)')
    # action='append' (one file per flag), not nargs='*': a greedy list swallowed a following
    # model.p3d, which then only got the P:\ text scan and could pass without being audited.
    parser.add_argument('--rvmat', action='append', default=[], metavar='RVMAT',
                        help='.rvmat file to check for absolute P-drive paths (repeat for more)')
    parser.add_argument('--scan-dir', help='Scan a whole mod directory (ignores the other inputs)')
    args = parser.parse_args(argv)

    if not (args.files or args.config or args.model_cfg or args.rvmat or args.scan_dir):
        parser.error("nothing to audit: give .p3d files, --config, --model-cfg, --rvmat or --scan-dir")

    if args.scan_dir and not os.path.isdir(args.scan_dir):
        print(f"{h.FAIL} Directory not found: {args.scan_dir}", file=sys.stderr)
        sys.exit(1)

    h.gate_on_preflight()
    failed = []  # tally of each failed input; {"odol": 1} marks an ODOL reject

    if args.scan_dir:
        failed = scan_directory(args.scan_dir)
    else:
        targets = [(f, None) for f in args.files]
        if args.config:
            targets.append((args.config, "config.cpp"))
        if args.model_cfg:
            targets.append((args.model_cfg, "model.cfg"))
        targets.extend((rv, ".rvmat") for rv in args.rvmat)
        for f, label in targets:
            if not os.path.isfile(f):
                print(f"{h.FAIL} File not found: {f}", file=sys.stderr)
                failed.append({})
            elif label is None and f.lower().endswith('.p3d'):
                cfg = args.model_cfg if args.model_cfg and os.path.isfile(args.model_cfg) else None
                config = args.config if args.config and os.path.isfile(args.config) else None
                t = {}
                if not audit_p3d(f, cfg, config, tally=t):
                    failed.append(t)
            elif not audit_text_file(f, label or "file"):
                failed.append({})

    odol = sum(1 for t in failed if t.get("odol"))
    print(f"\n{'='*70}")
    print(overall_line(odol, len(failed) - odol))
    print(f"{'='*70}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
