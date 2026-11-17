"""Case-insensitive material lookup, and the memory-point upsert."""

import pytest

from builders import build_cube_p3d, build_memory_lod, build_multilod_p3d
from helpers import read_p3d, write_bytes


# ---- materials ------------------------------------------------------------

def test_mat_pos_case_insensitive_lookup(fork):
    """A .p3d with lower-case materials, queried in UPPER case, returns faces."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    # three distinct lower-case materials, as DayZ stores them
    for i, fa in enumerate(lod.faces):
        fa.material = "lf\\data\\b_chrome_2.rvmat" if i < 2 else \
                      "lf\\data\\b_black_1.rvmat"
    got = lod.faces_for_material("LF\\DATA\\B_CHROME_2.RVMAT")
    assert len(got) == 2
    assert all(fa.material == "lf\\data\\b_chrome_2.rvmat" for fa in got)
    # the case-sensitive match finds nothing: the historical quirk
    assert [fa for fa in lod.faces
            if fa.material == "LF\\DATA\\B_CHROME_2.RVMAT"] == []


def test_mat_pos_faces_by_material_lower_keys(fork):
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    lod.faces[0].material = "LF\\data\\MIXED_Case.rvmat"
    groups = lod.faces_by_material()
    assert "lf\\data\\mixed_case.rvmat" in groups
    assert len(groups["lf\\data\\mixed_case.rvmat"]) == 1
    raw = lod.faces_by_material(lower=False)
    assert "LF\\data\\MIXED_Case.rvmat" in raw


# ---- memory points ------------------------------------------------------------

def test_mem_pos_upsert_idempotent(fork):
    """set_memory_point twice with the same name leaves one entry, at the last
    position."""
    p3d = fork.P3D()
    lod = build_memory_lod(fork, [("pos_center", (0.0, 0.0, 0.0))])
    p3d.lods.append(lod)
    n_points = len(lod.points)

    lod.set_memory_point("crewdriver", (1.0, 2.0, 3.0))
    lod.set_memory_point("crewdriver", (4.0, 5.0, 6.0))  # upsert, no duplica

    assert len(lod.points) == n_points + 1  # created only ONCE
    mps = lod.get_memory_points()
    assert mps["crewdriver"] == (4.0, 5.0, 6.0)
    assert len(lod.selections["crewdriver"].points) == 1

    # and it survives the round trip
    reread = read_p3d(fork, write_bytes(p3d))
    rmps = reread.lods[0].get_memory_points()
    assert rmps["crewdriver"] == (4.0, 5.0, 6.0)
    assert rmps["pos_center"] == (0.0, 0.0, 0.0)


def test_mem_neg_preexisting_duplicate_collapses(fork):
    """MEM-NEG: duplicado pre-existente (estilo vanilla) + set -> colapsa a 1."""
    p3d = fork.P3D()
    lod = build_memory_lod(fork, [])
    p3d.lods.append(lod)
    # a pre-existing duplicate: selection 'crewdriver' with TWO points
    a = fork.Point(); a.coords = (9.0, 9.0, 9.0); lod.points.append(a)
    b = fork.Point(); b.coords = (8.0, 8.0, 8.0); lod.points.append(b)
    dup = fork.Selection(lod.points, lod.faces)
    dup.points[a] = 1
    dup.points[b] = 1
    lod.selections["crewdriver"] = dup

    lod.set_memory_point("crewdriver", (1.0, 1.0, 1.0))

    sel = lod.selections["crewdriver"]
    assert len(sel.points) == 1  # colapsado, no 2 ni 3
    assert lod.get_memory_points()["crewdriver"] == (1.0, 1.0, 1.0)
    reread = read_p3d(fork, write_bytes(p3d))
    assert len(reread.lods[0].selections["crewdriver"].points) == 1
    assert reread.lods[0].get_memory_points()["crewdriver"] == (1.0, 1.0, 1.0)


def test_mem_get_excludes_non_point_selections(fork):
    """get_memory_points ignores selections with faces (proxies) or with more
    than one point."""
    p3d = build_multilod_p3d(fork)
    vis, geo, mem = p3d.lods
    assert "proxy:\\dz\\data\\proxies\\flag.001" not in vis.get_memory_points()
    assert "Component01" not in geo.get_memory_points()
    assert set(mem.get_memory_points()) == {
        "pos center", "dolly_axis_start", "dolly_axis_end"}
