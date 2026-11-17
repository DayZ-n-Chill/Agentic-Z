"""export_objs_tri.py writes a triangulated OBJ with no loose geometry.

Needs Blender's Python API: run it with the `bpy` module installed
(pip install bpy) or from Blender's own Python. Skipped when bpy is missing.

Run with: python -m pytest skills/uv-clean-atlas/scripts/test_export_objs_tri.py
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

bpy = pytest.importorskip("bpy", reason="needs Blender's bpy module")

SCRIPT = Path(__file__).resolve().parent / "export_objs_tri.py"


def test_quad_becomes_two_triangles_and_the_loose_vertex_is_dropped(tmp_path, monkeypatch):
    # One quad plus one vertex that belongs to no face.
    mesh = bpy.data.meshes.new("uvca_probe")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (5, 5, 5)], [], [(0, 1, 2, 3)])
    mesh.update()
    probe = bpy.data.objects.new("uvca_probe", mesh)
    bpy.context.collection.objects.link(probe)

    out = tmp_path / "out" / "probe.obj"
    monkeypatch.setattr(sys, "argv", ["blender", "--", "uvca_probe", str(out)])
    runpy.run_path(str(SCRIPT), run_name="__main__")

    lines = out.read_text(encoding="utf-8").splitlines()
    vertices = [line for line in lines if line.startswith("v ")]
    faces = [line for line in lines if line.startswith("f ")]
    assert len(vertices) == 4, "the loose vertex must not be exported"
    assert len(faces) == 2, "the quad must be exported as two triangles"
    assert all(len(face.split()) == 4 for face in faces), "every face must be a triangle"
