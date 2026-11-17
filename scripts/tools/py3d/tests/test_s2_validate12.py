"""validate() 1.2.0: one negative per finding code, and parity with
tools/audit_p3d.py."""

import io
import math
import os
import struct
import subprocess
import sys

import pytest

from builders import (CUBE_POINTS, CUBE_QUADS, add_proxy_triangle,
                      build_multilod_v2_p3d)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO, "tools", "audit_p3d.py")


def codes(findings):
    return sorted({f.code for f in findings})


def add_box(m, lod, scale, name=None, mass=None, offset=(0.0, 0.0, 0.0)):
    """Append a closed box to *lod*: the builders' unit cube scaled per
    axis and moved by *offset*, with its winding and normals, so a box
    centred on the origin keeps every winding check quiet. *name* gets (or
    creates) a selection holding the box's points and faces. Returns
    (points, faces)."""
    base = len(lod.points)
    pts = []
    for c in CUBE_POINTS:
        p = m.Point()
        p.coords = tuple(c[j] * scale[j] + offset[j] for j in range(3))
        p.mass = mass
        lod.points.append(p)
        pts.append(p)
    faces = []
    for quad, n in CUBE_QUADS:
        lod.facenormals.append(n)
        fa = m.Face(lod.points, lod.facenormals)
        for pi in quad:
            v = m.Vertex(lod.points, lod.facenormals)
            v.point_index = base + pi
            v.normal_index = len(lod.facenormals) - 1
            v.uv = (0.0, 0.0)
            fa.vertices.append(v)
        fa.texture = fa.material = ""
        lod.faces.append(fa)
        faces.append(fa)
    if name:
        sel = lod.new_selection(name)
        sel.points.update((p, 1) for p in pts)
        sel.faces.update((fa, 1) for fa in faces)
    return pts, faces


def select_all(lod, name):
    """*name* holds every point and face of *lod* (created if missing)."""
    sel = lod.new_selection(name)
    sel.points = {p: 1 for p in lod.points}
    sel.faces = {fa: 1 for fa in lod.faces}
    return sel


# A thin box across the Geometry cube, centred on the origin like it.
CROSS = (0.5, 2.0, 0.5)


# ---- mutators: each produces exactly the expected codes ----------

# These three mutants now ALSO emit the absolute check's codes
# (_check_winding_absolute). That is not duplicate noise: the
# relative one says "differs from the Visual LOD" and the absolute
# one says "contradicts its own normals", which are diagnosed and
# fixed differently. And in the case that motivated the fork -
# inverting EVERY LOD - the relative check stays quiet and the
# absolute one is the only one that speaks.
def mut_winding_inverted(m, p3d):
    for fa in p3d.get_lod("geometry").faces:
        fa.vertices.reverse()
    return ["ERR_WINDING_INVERTED", "ERR_WINDING_VS_NORMALS"]

def mut_winding_mixed(m, p3d):
    for fa in p3d.get_lod("geometry").faces[:2]:
        fa.vertices.reverse()
    return ["WARN_WINDING_MIXED", "WARN_WINDING_NORMAL_MISMATCH",
            "WARN_WINDING_EDGE_INCOHERENT"]

def mut_winding_lowconf(m, p3d):
    for fa in p3d.get_lod("visual").faces[:160]:
        fa.vertices.reverse()
    # one per collision LOD; the set collapses. A half-inverted
    # visual LOD also trips the absolute check on the visual itself.
    return ["WARN_WINDING_LOWCONF", "WARN_WINDING_NORMAL_MISMATCH",
            "WARN_WINDING_EDGE_INCOHERENT"]

# A collision LOD with faces and no component collides with nothing in
# game (measured 2026-10-02 with all three missing); each LOD is checked.
def mut_component_none(m, p3d):
    p3d.get_lod("geometry").selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_none_view(m, p3d):
    p3d.get_lod("view_geometry").selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_none_fire(m, p3d):
    p3d.get_lod("fire_geometry").selections.pop("Component01")
    return ["ERR_COMPONENT_NAMING"]

def mut_component_spelling(m, p3d):
    geo = p3d.get_lod("geometry")
    geo.selections["Component_01"] = geo.selections.pop("Component01")
    return ["WARN_COMPONENT_NAMING"]

def mut_component_newline(m, p3d):
    # "$" in re.match() accepts a trailing newline; fullmatch() does not
    geo = p3d.get_lod("geometry")
    geo.selections["Component01\n"] = geo.selections.pop("Component01")
    return ["WARN_COMPONENT_NAMING"]

def mut_component_coverage(m, p3d):
    geo = p3d.get_lod("geometry")
    sel = geo.selections["Component01"]
    first = next(iter(sel.points))
    del sel.points[first]
    return ["WARN_COMPONENT_COVERAGE"]

def mut_coverage_face_outside(m, p3d):
    # two components; one face of the second is in neither
    geo = p3d.get_lod("geometry")
    _, faces = add_box(m, geo, CROSS, "Component02", mass=25.0)
    del geo.selections["Component02"].faces[faces[0]]
    return ["WARN_COMPONENT_COVERAGE"]

def mut_coverage_lowercase(m, p3d):
    # the same gap, components named in lowercase (they collide alike)
    geo = p3d.get_lod("geometry")
    geo.selections["component01"] = geo.selections.pop("Component01")
    _, faces = add_box(m, geo, CROSS, "component02", mass=25.0)
    del geo.selections["component02"].faces[faces[0]]
    return ["WARN_COMPONENT_COVERAGE"]

def _cover_all_but_one_face(lod):
    sel = select_all(lod, "Component01")
    del sel.faces[lod.faces[0]]
    return ["WARN_COMPONENT_COVERAGE"]

def mut_coverage_view(m, p3d):
    return _cover_all_but_one_face(p3d.get_lod("view_geometry"))

def mut_coverage_fire(m, p3d):
    return _cover_all_but_one_face(p3d.get_lod("fire_geometry"))

# A closed part in no component beside a covered one: measured in game
# (2026-10-02) to collide with nothing, so an ERROR (1.10.0).
def mut_coverage_part_outside(m, p3d):
    add_box(m, p3d.get_lod("geometry"), CROSS, mass=25.0)
    return ["ERR_COMPONENT_COVERAGE"]

def mut_coverage_part_outside_view(m, p3d):
    add_box(m, p3d.get_lod("view_geometry"), CROSS)
    return ["ERR_COMPONENT_COVERAGE"]

def mut_coverage_part_outside_fire(m, p3d):
    add_box(m, p3d.get_lod("fire_geometry"), CROSS)
    return ["ERR_COMPONENT_COVERAGE"]

def mut_coverage_points_in_component(m, p3d):
    # the same box, its points in Component02 and its faces in none: a
    # part left out only in part, not measured
    geo = p3d.get_lod("geometry")
    pts, _ = add_box(m, geo, CROSS, mass=25.0)
    geo.new_selection("Component02").points.update((p, 1) for p in pts)
    return ["WARN_COMPONENT_COVERAGE"]

def mut_autocenter_missing(m, p3d):
    del p3d.get_lod("geometry").properties["autocenter"]
    return ["WARN_AUTOCENTER_MISSING"]

def mut_not_watertight(m, p3d):
    geo = p3d.get_lod("geometry")
    fa = geo.faces.pop()
    del geo.selections["Component01"].faces[fa]
    return ["WARN_NOT_WATERTIGHT"]

def mut_degenerate(m, p3d):
    geo = p3d.get_lod("geometry")
    fa = m.Face(geo.points, geo.facenormals)
    fa.texture = fa.material = ""
    for _ in range(3):
        v = m.Vertex(geo.points, geo.facenormals)
        v.point_index = 0
        v.normal_index = 0
        v.uv = (0.0, 0.0)
        fa.vertices.append(v)
    geo.faces.append(fa)
    geo.selections["Component01"].faces[fa] = 1
    # the degenerate face also counts as "not outward" in the
    # relative check, matching the original audit's behaviour
    return ["WARN_DEGENERATE_FACES", "WARN_WINDING_MIXED"]

def mut_memory_pos_center(m, p3d):
    mem = p3d.get_lod("memory")
    mem.selections["pos_center"] = mem.selections.pop("pos center")
    return ["WARN_MEMORY_POS_CENTER"]

def mut_memory_box_placing(m, p3d):
    p3d.get_lod("memory").selections.pop("box_placing_max")
    return ["WARN_MEMORY_BOX_PLACING"]

def mut_memory_axis_points(m, p3d):
    mem = p3d.get_lod("memory")
    mem.set_selection("flag_mast_axis", point_idx=[0])
    # the axis also requires a 'flag_mast' selection in the Visual LOD
    return ["ERR_MEMORY_AXIS_POINTS", "ERR_AXIS_SELECTION_MISSING"]

def mut_memory_axis_short(m, p3d):
    mem = p3d.get_lod("memory")
    a = mem.set_memory_point("mast_lo", (0.0, 0.0, 0.0))
    b = mem.set_memory_point("mast_hi", (0.0, 0.05, 0.0))
    sel = mem.new_selection("flag_mast_axis")
    sel.points = {a: 1, b: 1}
    p3d.get_lod("visual").set_selection("flag_mast", point_idx=[0, 1])
    return ["WARN_MEMORY_AXIS_SHORT"]

def mut_memory_has_faces(m, p3d):
    mem = p3d.get_lod("memory")
    mem.facenormals.append((0.0, 1.0, 0.0))
    fa = m.Face(mem.points, mem.facenormals)
    fa.texture = fa.material = ""
    for i in range(3):
        v = m.Vertex(mem.points, mem.facenormals)
        v.point_index = i
        v.normal_index = 0
        v.uv = (0.0, 0.0)
        fa.vertices.append(v)
    mem.faces.append(fa)
    return ["WARN_MEMORY_HAS_FACES"]

def mut_axis_selection_missing(m, p3d):
    p3d.get_lod("memory").set_selection("door_axis", point_idx=[0, 1])
    return ["ERR_AXIS_SELECTION_MISSING"]

def mut_axis_selection_empty(m, p3d):
    p3d.get_lod("memory").set_selection("door_axis", point_idx=[0, 1])
    p3d.get_lod("visual").set_selection("door")
    return ["WARN_AXIS_SELECTION_EMPTY"]

def mut_pdrive(m, p3d):
    p3d.get_lod("visual").faces[0].texture = "P:\\lf\\data\\stone_co.paa"
    return ["WARN_PDRIVE_PATH"]

def mut_kind_unknown(m, p3d):
    p3d.get_lod("fire_geometry").resolution = 5.5e14
    return ["WARN_LOD_KIND_UNKNOWN"]


CASES = [
    ("winding_inverted", mut_winding_inverted),
    ("winding_mixed", mut_winding_mixed),
    ("winding_lowconf", mut_winding_lowconf),
    ("component_none", mut_component_none),
    ("component_none_view", mut_component_none_view),
    ("component_none_fire", mut_component_none_fire),
    ("component_spelling", mut_component_spelling),
    ("component_newline", mut_component_newline),
    ("component_coverage", mut_component_coverage),
    ("coverage_face_outside", mut_coverage_face_outside),
    ("coverage_lowercase", mut_coverage_lowercase),
    ("coverage_view", mut_coverage_view),
    ("coverage_fire", mut_coverage_fire),
    ("coverage_part_outside", mut_coverage_part_outside),
    ("coverage_part_outside_view", mut_coverage_part_outside_view),
    ("coverage_part_outside_fire", mut_coverage_part_outside_fire),
    ("coverage_points_in_component", mut_coverage_points_in_component),
    ("autocenter_missing", mut_autocenter_missing),
    ("not_watertight", mut_not_watertight),
    ("degenerate", mut_degenerate),
    ("memory_pos_center", mut_memory_pos_center),
    ("memory_box_placing", mut_memory_box_placing),
    ("memory_axis_points", mut_memory_axis_points),
    ("memory_axis_short", mut_memory_axis_short),
    ("memory_has_faces", mut_memory_has_faces),
    ("axis_selection_missing", mut_axis_selection_missing),
    ("axis_selection_empty", mut_axis_selection_empty),
    ("pdrive", mut_pdrive),
    ("kind_unknown", mut_kind_unknown),
]


def test_val_pos_v2_clean(fork):
    """The complete v2 fixture produces no findings."""
    assert build_multilod_v2_p3d(fork).validate() == []


COLLISION_KINDS = ("geometry", "view_geometry", "fire_geometry")


@pytest.mark.parametrize("name", ["Component01", "component01",
                                  "COMPONENT01", "Component02"])
def test_val_component_name_any_case(fork, name):
    """In game (2026-10-02) component01 collided exactly like Component01,
    and binarize writes both as component01: "Component" and a number, in
    any case, raises nothing on any collision LOD. Up to 1.8.0 a
    lowercase component01 raised ERR_COMPONENT_NAMING."""
    p3d = build_multilod_v2_p3d(fork)
    for kind in COLLISION_KINDS:
        lod = p3d.get_lod(kind)
        lod.selections[name] = lod.selections.pop("Component01")
    assert p3d.validate() == []


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_missing_names_the_lod(fork, kind):
    """The ERROR sits on the LOD without a component, names its kind and
    says its collision is lost silently; it no longer says the case of
    the name matters."""
    p3d = build_multilod_v2_p3d(fork)
    lod = p3d.get_lod(kind)
    lod.selections.pop("Component01")
    index = next(i for i, l in enumerate(p3d.lods) if l is lod)
    found = [f for f in p3d.validate() if f.code == "ERR_COMPONENT_NAMING"]
    assert [(f.severity, f.lod) for f in found] == [("ERROR", index)]
    msg = found[0].msg
    assert msg.startswith("%s LOD: 6 face(s) and no ComponentNN selection"
                          % kind), msg
    # the measured case (none in any collision LOD) is said as measured,
    # one LOD missing it alone as not measured
    assert "in any of its collision LODs lost its collision silently" in msg
    assert "while the others have one was not measured" in msg
    assert "uppercase" not in msg.lower()


def test_val_component_mixed_names(fork):
    """One "Component" and a number is enough: next to component01, an
    irregular Component_01 raises nothing (the WARN is for a LOD whose
    component-like names are none of them "Component" and a number)."""
    p3d = build_multilod_v2_p3d(fork)
    for kind in COLLISION_KINDS:
        lod = p3d.get_lod(kind)
        lod.selections["component01"] = lod.selections.pop("Component01")
        lod.set_selection("Component_01", point_idx=[0])
    assert p3d.validate() == []


COMPONENT_CODES = {"ERR_COMPONENT_NAMING", "WARN_COMPONENT_NAMING"}
RESOLUTION = {"geometry": 1.0e13, "view_geometry": 6.0e15,
              "fire_geometry": 7.0e15}


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_not_required_without_own_faces(fork, kind):
    """A collision LOD with no faces (a Geometry LOD that only carries
    mass, the shape a worn item's has) or whose only face is a proxy
    triangle has no collision geometry of its own: no component finding,
    on each of the three kinds. The control: one face outside the proxy
    makes the same LOD raise the ERROR."""
    m = fork
    bare = m.LOD()
    bare.resolution = RESOLUTION[kind]
    pt = m.Point()
    pt.coords = (0.0, 0.0, 0.0)
    if kind == "geometry":
        pt.mass = 10.0
    bare.points.append(pt)
    proxied = m.LOD()
    proxied.resolution = RESOLUTION[kind]
    add_proxy_triangle(m, proxied, "proxy:\\dz\\data\\proxies\\flag.001")
    p3d = m.P3D()
    p3d.lods += [bare, proxied]
    assert not COMPONENT_CODES & set(codes(p3d.validate()))
    # the same builder, under a selection that is not a proxy: a face of
    # the LOD's own
    add_proxy_triangle(m, proxied, "glass", origin=(1.0, 1.0, 1.0))
    found = [f for f in p3d.validate() if f.code in COMPONENT_CODES]
    assert [(f.code, f.lod) for f in found] == [("ERR_COMPONENT_NAMING", 1)]
    assert found[0].msg.startswith(
        "%s LOD: 1 face(s) and no ComponentNN selection" % kind)


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_proxy_name_is_not_enough(fork, kind):
    """Faces are proxy triangles only when their 'proxy:...' selection has
    a proxy's shape (1 triangle and its 3 corners). A cube whose 8 points and 6
    quads sit under a proxy name is collision geometry with no component."""
    p3d = build_multilod_v2_p3d(fork)
    lod = p3d.get_lod(kind)
    lod.selections["proxy:\\dz\\data\\proxies\\flag.001"] = \
        lod.selections.pop("Component01")
    index = next(i for i, l in enumerate(p3d.lods) if l is lod)
    found = [f for f in p3d.validate() if f.code in COMPONENT_CODES]
    assert [(f.code, f.lod) for f in found] == [("ERR_COMPONENT_NAMING", index)]


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_val_component_proxy_points_are_its_corners(fork, kind):
    """A proxy selection's 3 points must be its triangle's corners: one
    that selects 3 other points does not make the triangle a proxy. The
    control is the same LOD before its selection is re-pointed."""
    m = fork
    lod = m.LOD()
    lod.resolution = RESOLUTION[kind]
    sel = add_proxy_triangle(m, lod, "proxy:\\dz\\data\\proxies\\flag.001")
    p3d = m.P3D()
    p3d.lods.append(lod)
    assert not COMPONENT_CODES & set(codes(p3d.validate()))
    others = []
    for xyz in ((4.0, 0.0, 0.0), (5.0, 0.0, 0.0), (4.0, 1.0, 0.0)):
        pt = m.Point()
        pt.coords = xyz
        lod.points.append(pt)
        others.append(pt)
    sel.points = {pt: 1 for pt in others}
    found = [f for f in p3d.validate() if f.code in COMPONENT_CODES]
    assert [(f.code, f.lod) for f in found] == [("ERR_COMPONENT_NAMING", 0)]


@pytest.mark.parametrize("name,mutate", CASES, ids=[c[0] for c in CASES])
def test_val_neg_code_1to1(fork, name, mutate):
    """Each negative fixture produces EXACTLY the expected codes."""
    p3d = build_multilod_v2_p3d(fork)
    expected = sorted(set(mutate(fork, p3d)))
    assert codes(p3d.validate()) == expected


@pytest.mark.parametrize("name,mutate", CASES, ids=[c[0] for c in CASES])
def test_val_audit_parity(fork, name, mutate, tmp_path):
    """The pruned audit (tools/audit_p3d.py, delegating to this library)
    reports the SAME findings, with severities mapped: ERROR to CRITICAL
    and exit 1, WARN to WARNING and exit 0."""
    p3d = build_multilod_v2_p3d(fork)
    expected = sorted(set(mutate(fork, p3d)))
    fx = tmp_path / ("%s.p3d" % name)
    with open(str(fx), "wb") as f:
        p3d.write(f)
    env = dict(os.environ, PYTHONPATH=REPO)
    r = subprocess.run([sys.executable, AUDIT, str(fx)],
                       capture_output=True, text=True, env=env, cwd=REPO)
    for code in expected:
        assert "[%s]" % code in r.stdout, (code, r.stdout)
        sev = "CRITICAL" if code.startswith("ERR_") else "WARNING"
        assert any(sev in ln and "[%s]" % code in ln
                   for ln in r.stdout.splitlines()), (code, r.stdout)
    has_err = any(c.startswith("ERR_") for c in expected)
    assert r.returncode == (1 if has_err else 0), r.stdout


def test_val_audit_parity_clean(fork, tmp_path):
    """The clean model passes the pruned audit: ALL PASSED, exit 0."""
    fx = tmp_path / "clean.p3d"
    with open(str(fx), "wb") as f:
        build_multilod_v2_p3d(fork).write(f)
    env = dict(os.environ, PYTHONPATH=REPO)
    r = subprocess.run([sys.executable, AUDIT, str(fx)],
                       capture_output=True, text=True, env=env, cwd=REPO)
    assert r.returncode == 0
    assert "ALL CHECKS PASSED" in r.stdout and "OVERALL: ALL PASSED" in r.stdout


# ---- WARN_COMPONENT_COVERAGE: the union of the components (1.9.0) -----
# ---- ERR_COMPONENT_COVERAGE: closed parts left out whole (1.10.0) ------

def coverage(findings):
    return [f for f in findings if f.code == "WARN_COMPONENT_COVERAGE"]


def coverage_err(findings):
    return [f for f in findings if f.code == "ERR_COMPONENT_COVERAGE"]


COVERAGE_CODES = {"ERR_COMPONENT_COVERAGE", "WARN_COMPONENT_COVERAGE"}


def test_coverage_pos_components_together(fork):
    """Each collision LOD holds two components that together cover every
    face: no finding. Up to 1.8.0 the Geometry LOD read 'Component01
    covers 8/16 vertices' and '6/12 faces'."""
    p3d = build_multilod_v2_p3d(fork)
    for kind, mass in (("geometry", 25.0), ("view_geometry", None),
                       ("fire_geometry", None)):
        lod = p3d.get_lod(kind)
        select_all(lod, "Component01")
        add_box(fork, lod, CROSS, "Component02", mass=mass)
    assert p3d.validate() == []


def test_coverage_pos_lowercase_components(fork):
    """Components named in lowercase count like 'ComponentNN'."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    geo.selections["component01"] = geo.selections.pop("Component01")
    add_box(fork, geo, CROSS, "component02", mass=25.0)
    assert p3d.validate() == []


def test_coverage_pos_loose_point_not_counted(fork):
    """A point that no face uses has nothing to collide with: no finding.
    Up to 1.8.0: 'Component01 covers 8/9 vertices'."""
    p3d = build_multilod_v2_p3d(fork)
    p = fork.Point()
    p.coords = (0.0, 0.0, 0.0)
    p.mass = 25.0
    p3d.get_lod("geometry").points.append(p)
    assert p3d.validate() == []


def _geometry_with_proxy(m):
    p3d = build_multilod_v2_p3d(m)
    geo = p3d.get_lod("geometry")
    add_proxy_triangle(m, geo, "proxy:\\dz\\data\\proxies\\flag.001",
                       origin=(0.0, 0.0, 0.2))
    for p in geo.points[-3:]:
        p.mass = 0.0
    return p3d, geo


def test_coverage_proxy_triangle_not_counted(fork):
    """A proxy triangle outside every component is not a face to cover.
    Up to 1.8.0: 'Component01 covers 8/11 vertices' and '6/7 faces'."""
    p3d, _ = _geometry_with_proxy(fork)
    assert coverage(p3d.validate()) == []


def test_coverage_counts_exclude_proxy_faces(fork):
    """With a face of its own outside every component, the proxy triangle
    stays out of the count: 1 of 6 faces, not of 7."""
    p3d, geo = _geometry_with_proxy(fork)
    del geo.selections["Component01"].faces[geo.faces[0]]
    (f,) = coverage(p3d.validate())
    assert f.lod == 1 and f.severity == "WARN"
    assert f.msg.startswith(
        "geometry LOD: 1 of its 6 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection."), f.msg


def test_coverage_proxy_named_box_counts(fork):
    """A whole box under a proxy name is not a proxy triangle: its faces
    are collision geometry and, in no component, a closed part left out
    whole (6 of 12 faces; up to 1.9.0 the WARN counted them)."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, CROSS, "proxy:\\dz\\data\\proxies\\crate.001",
            mass=25.0)
    findings = p3d.validate()
    assert coverage(findings) == []
    (f,) = coverage_err(findings)
    assert f.msg.startswith(
        "geometry LOD: 6 of its 12 face(s) (proxy triangles not counted) "
        "make up 1 closed part(s) with no face and no point in any "
        "ComponentNN selection."), f.msg


def test_coverage_empty_component_selection(fork):
    """A component selection that holds nothing is accepted by the naming
    check; coverage reads the LOD as in no component: the closed cube is a
    part left out whole (up to 1.9.0, the WARN with every face counted)."""
    p3d = build_multilod_v2_p3d(fork)
    sel = p3d.get_lod("geometry").selections["Component01"]
    sel.points = {}
    sel.faces = {}
    findings = p3d.validate()
    assert codes(findings) == ["ERR_COMPONENT_COVERAGE"]
    (f,) = coverage_err(findings)
    assert (f.severity, f.lod) == ("ERROR", 1)
    assert f.msg.startswith(
        "geometry LOD: 6 of its 6 face(s) (proxy triangles not counted) make "
        "up 1 closed part(s) with no face and no point in any ComponentNN "
        "selection."), f.msg


def test_coverage_empty_component_selection_open_piece(fork):
    """The same empty selection on a LOD whose only piece is open (the cube
    without one face): not a closed solid, so the WARN, every face and
    point counted."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    sel = geo.selections["Component01"]
    sel.points = {}
    sel.faces = {}
    geo.faces.pop()
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 5 of its 5 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection, nor are 8 of the 8 point(s) its faces "
        "use."), f.msg


def test_coverage_message_faces(fork):
    """One face of the second component in neither: the count is over
    both components' faces, and no point is counted (its points stay in
    Component02)."""
    p3d = build_multilod_v2_p3d(fork)
    mut_coverage_face_outside(fork, p3d)
    (f,) = coverage(p3d.validate())
    assert f.lod == 1
    assert f.msg.startswith(
        "geometry LOD: 1 of its 12 face(s) (proxy triangles not counted) "
        "are in no ComponentNN selection."), f.msg


def test_coverage_message_faces_and_points(fork):
    """The face and its four corners out of Component02: the corners are
    counted against the 16 points the faces use."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    _, faces = add_box(fork, geo, CROSS, "Component02", mass=25.0)
    sel = geo.selections["Component02"]
    del sel.faces[faces[0]]
    for v in faces[0].vertices:
        del sel.points[v.point]
    (f,) = coverage(p3d.validate())
    assert f.msg.startswith(
        "geometry LOD: 1 of its 12 face(s) (proxy triangles not counted) "
        "are in no ComponentNN selection, nor are 4 of the 16 point(s) its "
        "faces use."), f.msg


def test_coverage_message_points_only(fork):
    """Every face in a component but one of its points in none."""
    p3d = build_multilod_v2_p3d(fork)
    mut_component_coverage(fork, p3d)
    (f,) = coverage(p3d.validate())
    assert f.lod == 1
    assert f.msg.startswith(
        "geometry LOD: every face (proxy triangles not counted) is in a "
        "ComponentNN selection, but 1 of the 8 point(s) its faces use are "
        "in none."), f.msg


@pytest.mark.parametrize("kind,index", [("view_geometry", 2),
                                        ("fire_geometry", 3)])
def test_coverage_view_and_fire(fork, kind, index):
    """View and Fire are read like Geometry (up to 1.8.0, not at all)."""
    p3d = build_multilod_v2_p3d(fork)
    _cover_all_but_one_face(p3d.get_lod(kind))
    (f,) = coverage(p3d.validate())
    assert f.lod == index
    assert f.msg.startswith(
        "%s LOD: 1 of its 6 face(s) (proxy triangles not counted) are in no "
        "ComponentNN selection." % kind), f.msg


def test_coverage_zero_weight_is_not_cover(fork):
    """A zero weight is not written, so that face is in no component.
    (The in-memory round trip also reports the membership change.)"""
    p3d = build_multilod_v2_p3d(fork)
    sel = p3d.get_lod("geometry").selections["Component01"]
    sel.faces[next(iter(sel.faces))] = 0
    (f,) = coverage(p3d.validate())
    assert f.msg.startswith("geometry LOD: 1 of its 6 face(s)"), f.msg


def test_coverage_zero_point_weight_is_not_cover(fork):
    """The same for a point: every face is covered, one corner is not."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    geo.selections["Component01"].points[geo.points[0]] = 0
    (f,) = coverage(p3d.validate())
    assert f.msg.startswith(
        "geometry LOD: every face (proxy triangles not counted) is in a "
        "ComponentNN selection, but 1 of the 8 point(s) its faces use are "
        "in none."), f.msg


def test_coverage_fractional_weights_cover(fork):
    """Any nonzero weight is a member, in memory and once written and read
    back (MLOD stores a fractional weight as a nonzero byte)."""
    import io
    p3d = build_multilod_v2_p3d(fork)
    sel = p3d.get_lod("geometry").selections["Component01"]
    sel.points = {p: 0.5 for p in sel.points}
    sel.faces = {fa: 0.25 for fa in sel.faces}
    assert coverage(p3d.validate()) == []
    buf = io.BytesIO()
    p3d.write(buf)
    buf.seek(0)
    reread = fork.P3D(buf)
    weights = reread.get_lod("geometry").selections["Component01"].faces
    assert len(weights) == 6 and all(0 < w < 1 for w in weights.values())
    assert coverage(reread.validate()) == []


def test_coverage_silent_on_proxy_only_lod(fork):
    """A collision LOD that holds only a proxy triangle has no face of its
    own to cover, even with a component selection present. Up to 1.8.0,
    on the Geometry LOD: 'Component01 covers 0/3 vertices' and '0/1
    faces'."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    lod = fork.LOD()
    lod.resolution = geo.resolution
    lod.properties["autocenter"] = "0"
    add_proxy_triangle(fork, lod, "proxy:\\dz\\data\\proxies\\flag.001")
    lod.new_selection("Component01")
    p3d.lods[p3d.lods.index(geo)] = lod
    assert not COVERAGE_CODES & set(codes(p3d.validate()))


def test_coverage_silent_without_components(fork):
    """No component selection at all is ERR_COMPONENT_NAMING's finding;
    coverage adds nothing, though the cube is a closed part in no
    component."""
    p3d = build_multilod_v2_p3d(fork)
    p3d.get_lod("geometry").selections.pop("Component01")
    assert codes(p3d.validate()) == ["ERR_COMPONENT_NAMING"]


# ---- ERR_COMPONENT_COVERAGE (1.10.0): which faces are a closed part left
# out whole. In game (2026-10-02, dayz-p3d-audit killer #8) a closed box in
# no component beside a covered one collided with nothing; a part left out
# only in part, an open piece and a flat sheet were not measured and stay
# the WARN.

MEASURED = (
    "In game two such parts took no ray in the LODs they were left out of and "
    "no physics ray, and no log line said so: a box left out of every "
    "component of the Geometry, View and Fire LODs beside a covered box, "
    "which the player walked through, and a lever left out of the Geometry "
    "and Fire LODs (a component in View, hit there), whose knob did not stop "
    "a player walking into it. A part left out of one LOD alone, or beside "
    "component selections that hold nothing, was not measured, nor was "
    "weapon fire.")
NOT_MEASURED = (
    "Each lies in a part partly in a component, or in a piece that is open, "
    "wound inconsistently, flat, or too thin to count as solid at its "
    "distance from the origin; none of these was measured in game (closed "
    "parts left out whole are ERR_COMPONENT_COVERAGE).")
LOD_INDEX = {"geometry": 1, "view_geometry": 2, "fire_geometry": 3}
SMALL = (0.25, 0.25, 0.25)


def _mass(kind):
    return 25.0 if kind == "geometry" else None


def add_mesh(m, lod, coords, polys, mass=None):
    """Append points at *coords* and faces over them (*polys*: index
    tuples into *coords*), in no selection. Returns the faces."""
    base = len(lod.points)
    for c in coords:
        p = m.Point()
        p.coords = c
        p.mass = mass
        lod.points.append(p)
    lod.facenormals.append((0.0, 0.0, 1.0))
    faces = []
    for poly in polys:
        fa = m.Face(lod.points, lod.facenormals)
        for i in poly:
            v = m.Vertex(lod.points, lod.facenormals)
            v.point_index = base + i
            v.normal_index = len(lod.facenormals) - 1
            v.uv = (0.0, 0.0)
            fa.vertices.append(v)
        fa.texture = fa.material = ""
        lod.faces.append(fa)
        faces.append(fa)
    return faces


@pytest.mark.parametrize("kind", COLLISION_KINDS)
def test_coverage_err_closed_part_beside_covered(fork, kind):
    """A closed box in no component beside the covered cube: the ERROR on
    that LOD, and no WARN. Its message says which omissions were measured
    (all three LODs, or Geometry and Fire) and that one LOD alone was not.
    Up to 1.9.0 the WARN said this case was not measured."""
    p3d = build_multilod_v2_p3d(fork)
    add_box(fork, p3d.get_lod(kind), CROSS, mass=_mass(kind))
    findings = p3d.validate()
    assert codes(findings) == ["ERR_COMPONENT_COVERAGE"]
    (f,) = coverage_err(findings)
    assert (f.severity, f.lod) == ("ERROR", LOD_INDEX[kind])
    assert f.msg.startswith(
        "%s LOD: 6 of its 12 face(s) (proxy triangles not counted) make up 1 "
        "closed part(s) with no face and no point in any ComponentNN "
        "selection. %s Select each closed, convex part as its own "
        "ComponentNN" % (kind, MEASURED)), f.msg
    assert "expect them" not in f.msg


def test_coverage_err_after_write_and_read(fork):
    """The same model written and read back (float32 corners, component
    membership from the file): the same ERROR."""
    p3d = build_multilod_v2_p3d(fork)
    mut_coverage_part_outside(fork, p3d)
    buf = io.BytesIO()
    p3d.write(buf)
    buf.seek(0)
    (f,) = coverage_err(fork.P3D(buf).validate())
    assert f.msg.startswith("geometry LOD: 6 of its 12 face(s)"), f.msg


def test_coverage_err_counts_parts(fork):
    """Two closed parts left out, one finding: 12 of 18 faces, 2 parts."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, CROSS, mass=25.0)
    add_box(fork, geo, SMALL, mass=25.0, offset=(2.0, 0.0, 0.0))
    findings = p3d.validate()
    assert coverage(findings) == []
    (f,) = coverage_err(findings)
    assert f.msg.startswith(
        "geometry LOD: 12 of its 18 face(s) (proxy triangles not counted) "
        "make up 2 closed part(s)"), f.msg


def test_coverage_err_and_warn_on_one_lod(fork):
    """A closed part left out whole and one face of the cube left out of
    Component01: the ERROR counts the part, the WARN that face alone."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, CROSS, mass=25.0)
    del geo.selections["Component01"].faces[geo.faces[0]]
    findings = p3d.validate()
    (e,) = coverage_err(findings)
    assert e.msg.startswith(
        "geometry LOD: 6 of its 12 face(s) (proxy triangles not counted) "
        "make up 1 closed part(s)"), e.msg
    (w,) = coverage(findings)
    assert (w.severity, w.lod) == ("WARN", 1)
    assert w.msg.startswith(
        "geometry LOD: besides the closed part(s) of ERR_COMPONENT_COVERAGE, "
        "1 of its 12 face(s) (proxy triangles not counted) are in no "
        "ComponentNN selection. " + NOT_MEASURED), w.msg


def test_coverage_err_and_points_only_warn(fork):
    """A closed part left out whole and one cube corner left out of
    Component01: 'every face' in the WARN means every face but the part's,
    and its points are not counted again (1 of 16)."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, CROSS, mass=25.0)
    del geo.selections["Component01"].points[geo.points[0]]
    findings = p3d.validate()
    assert len(coverage_err(findings)) == 1
    (w,) = coverage(findings)
    assert w.msg.startswith(
        "geometry LOD: besides the closed part(s) of ERR_COMPONENT_COVERAGE, "
        "every face (proxy triangles not counted) is in a ComponentNN "
        "selection, but 1 of the 16 point(s) its faces use are in none."), \
        w.msg


def test_coverage_err_unwelded_part(fork):
    """A closed box whose faces each have their own four points (corners
    never merged) is one closed piece by position: the ERROR."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    coords, polys = [], []
    for quad, _ in CUBE_QUADS:
        polys.append(tuple(range(len(coords), len(coords) + 4)))
        coords += [tuple(CUBE_POINTS[i][j] * SMALL[j] + (2.0, 0.0, 0.0)[j]
                         for j in range(3)) for i in quad]
    add_mesh(fork, geo, coords, polys, mass=25.0)
    findings = p3d.validate()
    assert coverage(findings) == []
    (f,) = coverage_err(findings)
    assert f.msg.startswith(
        "geometry LOD: 6 of its 12 face(s) (proxy triangles not counted) "
        "make up 1 closed part(s)"), f.msg


def test_coverage_warn_face_left_out_of_a_part(fork):
    """One face of a covered box in no component: a part left out only in
    part, not measured, so the WARN; 1.9.0's 'expect them to take no part
    in collision' is gone."""
    p3d = build_multilod_v2_p3d(fork)
    mut_coverage_face_outside(fork, p3d)
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 1 of its 12 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection. " + NOT_MEASURED), f.msg
    assert "expect them" not in f.msg


def test_coverage_warn_points_in_component(fork):
    """A closed box whose points are in Component02 and whose faces are in
    none: partly in a component, the WARN (6 faces, no point)."""
    p3d = build_multilod_v2_p3d(fork)
    mut_coverage_points_in_component(fork, p3d)
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 6 of its 12 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection. Each lies"), f.msg


def test_coverage_warn_faces_in_component_points_not(fork):
    """A box whose faces but one are in Component02 and whose points are in
    none: a part partly in a component, the WARN (1 face, 8 corners)."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    _, faces = add_box(fork, geo, CROSS, mass=25.0)
    geo.new_selection("Component02").faces.update(
        (fa, 1) for fa in faces[1:])
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 1 of its 12 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection, nor are 8 of the 16 point(s) its faces "
        "use."), f.msg


def test_coverage_warn_one_point_in_component(fork):
    """One corner of the box in Component02 is enough to make the box a
    part partly in a component: the WARN, 7 of its 8 corners counted."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    pts, _ = add_box(fork, geo, CROSS, mass=25.0)
    geo.new_selection("Component02").points[pts[0]] = 1
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 6 of its 12 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection, nor are 7 of the 16 point(s) its faces "
        "use."), f.msg


def test_coverage_warn_stray_triangle(fork):
    """A stray triangle in no component (the vehicle Fire LOD of the 1.9.0
    impact run had two, 1 mm across) is not a closed solid: the WARN."""
    p3d = build_multilod_v2_p3d(fork)
    add_proxy_triangle(fork, p3d.get_lod("fire_geometry"), "glass",
                       origin=(2.0, 2.0, 2.0))
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.lod == 3
    assert f.msg.startswith(
        "fire_geometry LOD: 1 of its 7 face(s) (proxy triangles not counted) "
        "are in no ComponentNN selection, nor are 3 of the 11 point(s) its "
        "faces use."), f.msg


def test_coverage_warn_open_box(fork):
    """The box with one face missing is open: the WARN, 5 faces."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    _, faces = add_box(fork, geo, CROSS, mass=25.0)
    geo.faces.remove(faces[0])
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 5 of its 11 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection, nor are 8 of the 16 point(s)"), f.msg


def test_coverage_warn_flat_sheet(fork):
    """A flat quad modelled double-sided (the same four corners, wound both
    ways) closes every edge, once each way, but encloses no volume: not a
    closed solid, the WARN."""
    p3d = build_multilod_v2_p3d(fork)
    sheet = [(2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (3.0, 1.0, 0.0),
             (2.0, 1.0, 0.0)]
    add_mesh(fork, p3d.get_lod("geometry"), sheet,
             [(0, 1, 2, 3), (3, 2, 1, 0)], mass=25.0)
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith("geometry LOD: 2 of its 8 face(s)"), f.msg


def test_coverage_warn_closed_but_not_consistently_wound(fork):
    """A closed box with one face wound the other way: every edge is used
    twice, but not once each way; not counted as a closed solid, so the
    WARN (and the winding checks speak)."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    _, faces = add_box(fork, geo, CROSS, mass=25.0)
    faces[0].vertices.reverse()
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith("geometry LOD: 6 of its 12 face(s)"), f.msg


def test_coverage_warn_face_with_fewer_than_three_corners(fork):
    """A face with fewer than three corners (only buildable in memory: the
    reader takes 3 or 4) never makes its piece a closed solid: a closed box
    in no component plus a two-corner face across one of its sides is the
    WARN, 7 faces; a face with no corner alone is the WARN too, and does
    not break the check."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    pts, _ = add_box(fork, geo, SMALL, mass=25.0, offset=(2.0, 0.0, 0.0))
    side = CUBE_QUADS[0][0]
    add_mesh(fork, geo, [pts[side[0]].coords, pts[side[2]].coords], [(0, 1)],
             mass=25.0)
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith("geometry LOD: 7 of its 13 face(s)"), f.msg

    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    empty = fork.Face(geo.points, geo.facenormals)
    empty.texture = empty.material = ""
    geo.faces.append(empty)
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 1 of its 7 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection. Each lies"), f.msg


def test_coverage_warn_parts_sharing_an_edge(fork):
    """Two boxes in no component that share an edge make one piece whose
    shared edge is used by four faces: not a closed solid, the WARN."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, SMALL, mass=25.0, offset=(2.0, 0.0, 0.0))
    add_box(fork, geo, SMALL, mass=25.0, offset=(2.25, 0.25, 0.0))
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith("geometry LOD: 12 of its 18 face(s)"), f.msg


def test_coverage_warn_part_touching_a_covered_one(fork):
    """A closed box in no component whose corner sits on a corner of the
    covered cube (its own point, the same position) joins the cube's
    piece: partly in a component, the WARN."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, SMALL, mass=25.0, offset=(0.625, 0.625, 0.625))
    assert geo.points[-8].coords == geo.points[6].coords == (0.5, 0.5, 0.5)
    assert geo.points[-8] is not geo.points[6]
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith("geometry LOD: 6 of its 12 face(s)"), f.msg


# ---- review round 1 (1.10.0): a flat sheet anywhere, either winding, a
# part that is not convex, float32 positions, the thickness boundary.

def _rotation(axis, angle):
    """Rotation matrix (rows) about *axis* by *angle* radians."""
    n = math.sqrt(sum(a * a for a in axis))
    x, y, z = (a / n for a in axis)
    c, s = math.cos(angle), math.sin(angle)
    t = 1.0 - c
    return ((t * x * x + c, t * x * y - s * z, t * x * z + s * y),
            (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
            (t * x * z - s * y, t * y * z + s * x, t * z * z + c))


TURNED = _rotation((1.0, 2.0, 3.0), 0.7)
UNTURNED = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _place(local, centre, rot):
    return tuple(centre[i] + sum(rot[i][j] * local[j] for j in range(3))
                 for i in range(3))


def _box_mesh(half, centre, rot=TURNED):
    """The builders' cube with half-sizes *half*, turned by *rot* and moved
    to *centre*, wound as the cube is: (coords, quads)."""
    coords = [_place(tuple(2.0 * c[j] * half[j] for j in range(3)), centre,
                     rot) for c in CUBE_POINTS]
    return coords, [quad for quad, _ in CUBE_QUADS]


def _sheet_mesh(half, centre, rot=TURNED):
    """A flat quad modelled double-sided (the same four corners wound both
    ways), turned by *rot* and moved to *centre*."""
    a, b = half
    local = [(-a, -b, 0.0), (a, -b, 0.0), (a, b, 0.0), (-a, b, 0.0)]
    return ([_place(p, centre, rot) for p in local],
            [(0, 1, 2, 3), (3, 2, 1, 0)])


def _coverage_codes(findings):
    return sorted(f.code for f in findings if f.code in COVERAGE_CODES)


def _coverage_codes_written(fork, p3d):
    """Coverage codes of *p3d* written to an MLOD and read back."""
    buf = io.BytesIO()
    p3d.write(buf)
    buf.seek(0)
    return _coverage_codes(fork.P3D(buf).validate())


def _with_mesh(fork, mesh, kind="geometry"):
    p3d = build_multilod_v2_p3d(fork)
    add_mesh(fork, p3d.get_lod(kind), mesh[0], mesh[1], mass=_mass(kind))
    return p3d


def test_coverage_warn_reviewers_flat_sheet(fork):
    """Review round 1, F1: two coplanar quads wound both ways, corners exact
    in float32 near (62.5, 62.5, 62.5) and 1.8 mm apart. The volume summed
    from the model's origin cancelled into a 'solid' and raised the ERROR;
    summed from the piece's own corner it is flat: the WARN, in memory and
    once written."""
    a, u, v = (8195847, 8199705, 8199966), (30, 18, 45), (7, 30, 47)
    lattice = [a, tuple(a[j] + u[j] for j in range(3)),
               tuple(a[j] + 2 * u[j] + 3 * v[j] for j in range(3)),
               tuple(a[j] + v[j] for j in range(3))]
    coords = [tuple(x / 131072 for x in q) for q in lattice]
    assert all(struct.unpack("<f", struct.pack("<f", x))[0] == x
               for q in coords for x in q)
    p3d = _with_mesh(fork, (coords, [(0, 1, 2, 3), (3, 2, 1, 0)]))
    assert _coverage_codes(p3d.validate()) == ["WARN_COMPONENT_COVERAGE"]
    assert _coverage_codes_written(fork, p3d) == ["WARN_COMPONENT_COVERAGE"]


@pytest.mark.parametrize("offset", [0.0, 62.5, 1000.0])
def test_coverage_turned_and_moved_parts(fork, offset):
    """Off the axes and away from the origin, in memory and once written
    as float32: a 2 cm thick slab is a closed part left out whole (the
    ERROR), and a double-sided sheet of the same size never is (the WARN),
    though rounding lifts its corners off one plane."""
    centre = (3.0 + offset, offset, offset)
    for mesh, code in ((_box_mesh((0.5, 0.3, 0.01), centre),
                        "ERR_COMPONENT_COVERAGE"),
                       (_sheet_mesh((0.5, 0.3), centre),
                        "WARN_COMPONENT_COVERAGE")):
        p3d = _with_mesh(fork, mesh)
        assert _coverage_codes(p3d.validate()) == [code], (offset, code)
        assert _coverage_codes_written(fork, p3d) == [code], (offset, code)


def test_coverage_warn_one_covered_face_is_enough(fork):
    """A closed box with exactly one face in Component02 and no point in any
    component is a part partly in a component: the WARN for its other five
    faces and its eight corners."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    _, faces = add_box(fork, geo, CROSS, mass=25.0)
    geo.new_selection("Component02").faces[faces[0]] = 1
    findings = p3d.validate()
    assert coverage_err(findings) == []
    (f,) = coverage(findings)
    assert f.msg.startswith(
        "geometry LOD: 5 of its 12 face(s) (proxy triangles not counted) are "
        "in no ComponentNN selection, nor are 8 of the 16 point(s) its faces "
        "use."), f.msg


def test_coverage_err_either_winding(fork):
    """The box wound the other way round (every face reversed, like the
    inward winding of the measured lever) is a closed part left out whole
    as well: the volume's sign is not read."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    _, faces = add_box(fork, geo, CROSS, mass=25.0)
    for fa in faces:
        fa.vertices.reverse()
    (f,) = coverage_err(p3d.validate())
    assert f.msg.startswith(
        "geometry LOD: 6 of its 12 face(s) (proxy triangles not counted) "
        "make up 1 closed part(s)"), f.msg


def _l_prism_mesh(height, corner):
    """A closed prism on an L, which is not convex (as the measured lever, a
    knob and a bar, is not): the L (0,0) (2,0) (2,1) (1,1) (1,2) (0,2) in
    x/y, raised *height* along z from *corner*, each cap two quads, wound
    consistently. Its volume is 3 * height."""
    ell = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]
    coords = ([(corner[0] + x, corner[1] + y, corner[2]) for x, y in ell]
              + [(corner[0] + x, corner[1] + y, corner[2] + height)
                 for x, y in ell])
    bottom = [(0, 3, 2, 1), (0, 5, 4, 3)]
    top = [(6, 7, 8, 9), (6, 9, 10, 11)]
    sides = [(i, (i + 1) % 6, (i + 1) % 6 + 6, i + 6) for i in range(6)]
    return coords, bottom + top + sides


def test_coverage_err_part_not_convex(fork):
    """A closed part that is not convex, left out whole, is the ERROR: being
    convex is what a component needs, not what the omission is about."""
    p3d = _with_mesh(fork, _l_prism_mesh(0.5, (3.0, 0.0, 0.0)))
    (f,) = coverage_err(p3d.validate())
    assert f.msg.startswith(
        "geometry LOD: 10 of its 16 face(s) (proxy triangles not counted) "
        "make up 1 closed part(s)"), f.msg


def test_coverage_float32_positions_join_as_in_the_file(fork):
    """A closed box in no component whose corner lies 1e-9 m from a corner
    of the covered cube: a float32 holds both as one position, so the box
    joins the cube's piece (the WARN) in memory as it does once the model
    is written and read back."""
    p3d = build_multilod_v2_p3d(fork)
    geo = p3d.get_lod("geometry")
    add_box(fork, geo, SMALL, mass=25.0, offset=(0.625 + 1e-9, 0.625, 0.625))
    assert geo.points[-8].coords != geo.points[6].coords
    assert (struct.pack("<3f", *geo.points[-8].coords)
            == struct.pack("<3f", *geo.points[6].coords))
    assert _coverage_codes(p3d.validate()) == ["WARN_COMPONENT_COVERAGE"]
    assert _coverage_codes_written(fork, p3d) == ["WARN_COMPONENT_COVERAGE"]


@pytest.mark.parametrize("half,centre,code", [
    # 100 m x 1 mm x 1 mm: 0.5 mm thick (twice the volume over the area),
    # above 16 float32 steps at 50 m (0.1 mm): a solid
    ((50.0, 0.0005, 0.0005), (0.0, 3.0, 0.0), "ERR_COMPONENT_COVERAGE"),
    # 1 m x 1 m x 1 micrometre: below 16 steps at 1 m (1.9 micrometres)
    ((0.5, 0.5, 0.0000005), (0.0, 0.0, 0.75), "WARN_COMPONENT_COVERAGE"),
    # 10 cm x 10 cm x 0.5 micrometre at the origin: the 1 m floor still
    # calls it flat
    ((0.05, 0.05, 0.00000025), (0.0, 0.0, 0.0), "WARN_COMPONENT_COVERAGE"),
])
def test_coverage_thickness_boundary(fork, half, centre, code):
    """A closed piece is a solid when it is thicker than 16 float32 steps
    at its distance from the origin, at least 1 m: a long thin bar is one,
    a slab a micrometre thick is not."""
    p3d = _with_mesh(fork, _box_mesh(half, centre, rot=UNTURNED))
    assert _coverage_codes(p3d.validate()) == [code]


@pytest.mark.parametrize("base,u,v,k,l,step", [
    # review round 1 F1's sheet, near (62.5, 62.5, 62.5)
    ((8195847, 8199705, 8199966), (30, 18, 45), (7, 30, 47), 2, 3,
     2.0 ** -17),
    # near 1000 m and 2000 m from the origin
    ((16383974, 16384026, 16383994), (-48, 22, 8), (-48, 23, 10), 2, 3,
     2.0 ** -14),
    ((16383980, 16384031, 16384010), (37, -12, 25), (-9, 41, 13), 3, 1,
     2.0 ** -13),
])
def test_coverage_flat_sheet_thickness_is_zero(fork, base, u, v, k, l, step):
    """These exactly flat double-sided quads (corners on an integer lattice,
    exact in float32) have a thickness of exactly 0, 60 m to 2 km out: the
    volume is summed from the piece's own corner, not from the model's
    origin, whose sum cancels into a small number far out. Not every flat
    sheet gives exactly 0 (see the next test)."""
    lattice = [base, tuple(base[j] + u[j] for j in range(3)),
               tuple(base[j] + k * u[j] + l * v[j] for j in range(3)),
               tuple(base[j] + v[j] for j in range(3))]
    coords = [tuple(x * step for x in q) for q in lattice]
    assert all(struct.unpack("<f", struct.pack("<f", x))[0] == x
               for q in coords for x in q)
    lod = fork.LOD()
    faces = add_mesh(fork, lod, coords, [(0, 1, 2, 3), (3, 2, 1, 0)])
    thickness, reach = fork._piece_thickness(faces)
    assert thickness == 0.0 and reach > 60.0


def test_coverage_flat_sheet_residue_below_cutoff(fork):
    """Review round 2, N4: an exactly flat double-sided quad whose computed
    thickness is not exactly 0 (a residue of the sum, about 7e-17 m near
    955 m from the origin) stays far below the solid cutoff: the WARN."""
    a = (5887524, -7431202, 1760113)
    u = (405116, 647338, 908875)
    v = (376643, 939867, -31748)
    lattice = [a, tuple(a[j] + u[j] for j in range(3)),
               tuple(a[j] + 2 * u[j] + 3 * v[j] for j in range(3)),
               tuple(a[j] + v[j] for j in range(3))]
    coords = [tuple(x * 2.0 ** -13 for x in q) for q in lattice]
    assert all(struct.unpack("<f", struct.pack("<f", x))[0] == x
               for q in coords for x in q)
    lod = fork.LOD()
    faces = add_mesh(fork, lod, coords, [(0, 1, 2, 3), (3, 2, 1, 0)])
    thickness, reach = fork._piece_thickness(faces)
    cutoff = 16 * 2.0 ** -23 * reach
    assert thickness < 1e-9 * cutoff
    assert not fork._is_closed_solid(faces)
    p3d = _with_mesh(fork, (coords, [(0, 1, 2, 3), (3, 2, 1, 0)]))
    assert _coverage_codes(p3d.validate()) == ["WARN_COMPONENT_COVERAGE"]


def _box_oracle(dims):
    """Thickness of a box from its sizes alone: twice its volume over its
    area, abc / (ab + bc + ca)."""
    a, b, c = dims
    return a * b * c / (a * b + b * c + c * a)


@pytest.mark.parametrize("dims,centre", [
    ((1.0, 0.6, 0.005), (1500.0, 3.0, 0.0)),
    ((2.0, 2.0, 2.0), (0.0, 0.0, 3.0)),
    ((100.0, 0.001, 0.001), (0.0, 0.0, 0.0)),
    ((0.5, 0.25, 0.125), (62.5, 62.5, 62.5)),
])
def test_coverage_thickness_matches_box_oracle(fork, dims, centre):
    """Review round 2, N3: the thickness is twice the volume over the area,
    checked against the box's own sizes (not against the code's sums), and
    the reach is the largest coordinate, at least 1 m."""
    coords, quads = _box_mesh(tuple(d / 2.0 for d in dims), centre,
                              rot=UNTURNED)
    lod = fork.LOD()
    faces = add_mesh(fork, lod, coords, quads)
    thickness, reach = fork._piece_thickness(faces)
    assert thickness == pytest.approx(_box_oracle(dims), rel=1e-5)
    assert reach == pytest.approx(
        max(1.0, max(abs(x) for p in coords for x in p)), rel=1e-6)


@pytest.mark.parametrize("centre", [(1500.0, 3.0, 0.0), (0.0, 0.0, 0.75)])
@pytest.mark.parametrize("factor,code", [
    (0.9, "WARN_COMPONENT_COVERAGE"), (1.1, "ERR_COMPONENT_COVERAGE")])
def test_coverage_solid_cutoff_is_16_steps(fork, centre, factor, code):
    """Review round 2, N3: a slab 10 % thinner than 16 float32 steps at its
    distance from the origin (at least 1 m) is the WARN, one 10 % thicker the
    ERROR. The cutoff and the slab come from the sizes alone: a cutoff of 32
    steps, or a thickness taken as 3V/A instead of 2V/A, moves a side."""
    plate = (1.0, 0.6)
    reach = max(1.0, max(abs(centre[j]) + (plate + (0.0,))[j] / 2.0
                         for j in range(3)))
    target = factor * 16 * 2.0 ** -23 * reach
    # the slab thickness c whose oracle thickness abc/(ab+bc+ca) is target
    a, b = plate
    c = target * a * b / (a * b - target * (a + b))
    p3d = _with_mesh(fork, _box_mesh((a / 2.0, b / 2.0, c / 2.0), centre,
                                     rot=UNTURNED))
    assert _box_oracle((a, b, c)) == pytest.approx(target, rel=1e-9)
    assert _coverage_codes(p3d.validate()) == [code]


def test_coverage_warn_thin_closed_part_says_why(fork):
    """Review round 2, N1: the same closed 0.3 mm slab is a solid 3 m from
    the origin (the ERROR) and too thin for the cutoff 200 m out (the WARN),
    whose message says that a piece too thin to count as solid at its
    distance from the origin was not measured."""
    dims = (1.0, 0.6, 0.0003)
    half = tuple(d / 2.0 for d in dims)
    near = _with_mesh(fork, _box_mesh(half, (3.0, 3.0, 0.0), rot=UNTURNED))
    assert _coverage_codes(near.validate()) == ["ERR_COMPONENT_COVERAGE"]
    far = _with_mesh(fork, _box_mesh(half, (200.0, 3.0, 0.0), rot=UNTURNED))
    (f,) = coverage(far.validate())
    assert "or too thin to count as solid at its distance from the origin" \
        in f.msg, f.msg
