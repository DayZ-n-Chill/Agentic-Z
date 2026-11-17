"""The command line: info, validate and diff.

The output schema is STABLE: these tests ARE the contract, and changing
it needs a version bump.
Exit codes: info 0/2 - validate 0/1/2 - diff 0/1/2.
"""

import os
import subprocess
import sys

from builders import build_cube_p3d, build_multilod_v2_p3d

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*args):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "py3d"] + list(args),
                          capture_output=True, text=True, env=env, cwd=REPO)


def write(fork, p3d, path):
    with open(str(path), "wb") as f:
        p3d.write(f)
    return str(path)


# ---- CLI-INFO --------------------------------------------------------

def test_cli_info_schema_cube(fork, tmp_path):
    """The stable schema, line by line, on the cube."""
    fx = write(fork, build_cube_p3d(fork), tmp_path / "cube.p3d")
    r = run_cli("info", fx)
    assert r.returncode == 0
    assert r.stdout.splitlines() == [
        "file: cube.p3d",
        "lods: 1",
        "lod.0.kind: visual",
        "lod.0.resolution: 1",
        "lod.0.points: 8",
        "lod.0.faces: 6",
        "lod.0.mass: none",
        "lod.0.selections: Component01(8p/6f)",
        "lod.0.selected: -",
        "lod.0.properties: -",
        "lod.0.textures: lf\\data\\stone_co.paa",
        "lod.0.materials: lf\\data\\stone.rvmat",
        "lod.0.uv_sets: 0",
        "summary.component01: no",
        "summary.mass_total: none",
    ]


def test_cli_info_evidence_fields_v2(fork, tmp_path):
    """The evidence fields: Component01, mass, memory points."""
    fx = write(fork, build_multilod_v2_p3d(fork), tmp_path / "v2.p3d")
    out = run_cli("info", fx).stdout
    assert "lod.1.kind: geometry" in out
    assert "lod.1.resolution: 1e+13" in out
    assert "summary.component01: yes" in out
    assert "summary.mass_total: 200" in out
    assert "lod.4.memory_points: pos center=(0,0,0);" \
           "box_placing_min=(-0.5,-0.5,-0.5);box_placing_max=(0.5,0.5,0.5);" \
           "dolly_axis_start=(0,-1,0);dolly_axis_end=(0,1,0)" in out


def test_cli_info_unreadable(fork, tmp_path):
    """A non-p3d file exits 2, and so does a file that does not exist."""
    bad = tmp_path / "bad.p3d"
    bad.write_bytes(b"ODOLnope")
    r = run_cli("info", str(bad))
    assert r.returncode == 2 and "error:" in r.stderr
    assert run_cli("info", str(tmp_path / "no.p3d")).returncode == 2


# ---- CLI-VAL ---------------------------------------------------------

def test_cli_validate_clean_and_broken(fork, tmp_path):
    """CLI-VAL: limpio exit 0 / winding roto exit 1 / no legible exit 2."""
    clean = write(fork, build_multilod_v2_p3d(fork), tmp_path / "ok.p3d")
    r = run_cli("validate", clean)
    assert r.returncode == 0
    assert r.stdout.splitlines() == ["findings: 0", "result: clean"]

    p3d = build_multilod_v2_p3d(fork)
    for fa in p3d.get_lod("geometry").faces:
        fa.vertices.reverse()
    broken = write(fork, p3d, tmp_path / "broken.p3d")
    r = run_cli("validate", broken)
    assert r.returncode == 1
    lines = r.stdout.splitlines()
    # Inverting the Geometry LOD raises TWO errors: the one relative to
    # the Visual LOD, and the absolute one against its own normals. They
    # are checked by content, not position: emission order is not a
    # contract.
    assert lines[0] == "findings: 2" and lines[-1] == "result: errors"
    emitted = [ln for ln in lines if ln.startswith("finding.")]
    assert any("ERROR ERR_WINDING_INVERTED lod=1 " in ln for ln in emitted), \
        emitted
    assert any("ERROR ERR_WINDING_VS_NORMALS lod=1 " in ln for ln in emitted), \
        emitted

    bad = tmp_path / "bad.p3d"
    bad.write_bytes(b"garbage")
    assert run_cli("validate", str(bad)).returncode == 2


def test_cli_validate_warn_only_exit0(fork, tmp_path):
    """WARNs without an ERROR exit 0 and report result: warnings."""
    p3d = build_multilod_v2_p3d(fork)
    del p3d.get_lod("geometry").properties["autocenter"]
    fx = write(fork, p3d, tmp_path / "warn.p3d")
    r = run_cli("validate", fx)
    assert r.returncode == 0
    assert r.stdout.splitlines()[-1] == "result: warnings"
    assert "WARN_AUTOCENTER_MISSING" in r.stdout


# ---- CLI-DIFF --------------------------------------------------------

def test_cli_diff_moved_memory_point(fork, tmp_path):
    """A cube against the same cube with one memory point moved exits 1, and
    the output lists EXACTLY that point."""
    a = write(fork, build_multilod_v2_p3d(fork), tmp_path / "a.p3d")
    p3d = build_multilod_v2_p3d(fork)
    p3d.get_lod("memory").set_memory_point("pos center", (0.0, 0.5, 0.0))
    b = write(fork, p3d, tmp_path / "b.p3d")
    r = run_cli("diff", a, b)
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        "diff.lod.4.memory.pos center: (0,0,0) != (0,0.5,0)",
        "total: 1",
    ]


def test_cli_diff_equal_and_categories(fork, tmp_path):
    """Identical files exit 0; LOD count, kind, counts, selections, properties
    and mass are all reported in the stable schema."""
    a = write(fork, build_multilod_v2_p3d(fork), tmp_path / "a.p3d")
    r = run_cli("diff", a, a)
    assert r.returncode == 0 and r.stdout.splitlines() == ["total: 0"]

    p3d = build_multilod_v2_p3d(fork)
    p3d.lods.pop()                                # nLODs
    p3d.get_lod("geometry").set_total_mass(180)   # mass
    p3d.get_lod("geometry").properties["class"] = "vehicle"  # property
    p3d.get_lod("visual").set_selection("extra", point_idx=[0])  # names
    b = write(fork, p3d, tmp_path / "b.p3d")
    out = run_cli("diff", a, b)
    assert out.returncode == 1
    lines = out.stdout.splitlines()
    assert "diff.lods.count: 5 != 4" in lines
    assert "diff.lod.0.selections.names: +a[] +b['extra']" in lines
    assert "diff.lod.1.property.class: 'house' != 'vehicle'" in lines
    assert "diff.lod.1.mass: 200 != 180" in lines
    assert lines[-1] == "total: 4"

    bad = tmp_path / "bad.p3d"
    bad.write_bytes(b"nope")
    assert run_cli("diff", a, str(bad)).returncode == 2
