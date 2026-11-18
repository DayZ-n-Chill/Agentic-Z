#!/usr/bin/env python3
"""
make_fixtures.py - regenerate the fixtures of check_dayz_winding.py with py3d >= 1.8.0.

The model is the one of the inward-winding in-game test (DayZDiag 1.29.163709,
2026-10-01): an "F" in relief on a plate, authored in Blender space (right-handed, Z up, front -Y, faces
counter-clockwise seen from outside, outward normals); four closed boxes, 48 triangles. It is written the
three ways the test wrote it, under the file names the test used:

  mirror_b.p3d   py3d.blender_to_dayz() (inward winding)                    in game: solid, the F reads correctly
  mirror_a.p3d   transform(ROT_X_NEG90), every face reversed and
                 every normal negated (the old det=+1 recipe)        in game: solid, the F mirrored
  mirror_c.p3d   transform(ROT_X_NEG90) alone                        in game: inside-out, and mirrored

plus one variant that was not taken into the game:

  mirror_b_normals_out.p3d   mirror_b with every entry of the normal pool negated: the inward winding with
                             the normals stored OUTWARD, the state of the outward-normal recipe

The three in-game files come out byte for byte: IN_GAME_SHA256 holds the SHA-256 of the MLODs that were
binarized and looked at (scripts/tools/py3d/tests/test_s7_blender_to_dayz.py pins the same values). Nothing
is written unless all three match.

USAGE
  python make_fixtures.py                 # rewrite the fixtures next to this script
  python make_fixtures.py --out DIR       # write them somewhere else (the test compares the bytes)
  python make_fixtures.py --py3d PATH     # a py3d checkout to import instead of scripts/tools/py3d

It reads no game file and starts no DayZ tool, so it does not call /dayz-preflight.
"""
import argparse
import hashlib
import io
import os
import sys

IN_GAME_SHA256 = {
    "mirror_a.p3d": "b08372a6248d826aad7557827346af030b1d448e4e0d75da3afd0a67a0c16d27",
    "mirror_b.p3d": "f1be491df6304534f2100d053e972a9792b1780e026223408f5c200b465201d7",
    "mirror_c.p3d": "ac5f0f77f6d93db93226e631ed0b02c3492c6e13d815a621bd9ed82e2b4e1da8",
}

PLATE_TEXTURE = "dz\\data\\data\\beton1_co.paa"
GLYPH_TEXTURE = "dz\\data\\data\\black_co.paa"
# Blender space: x right, y depth (front = -y), z up.
BOXES = [
    ((-0.60, 0.00, 0.00), (0.60, 0.05, 1.40), PLATE_TEXTURE),   # plate
    ((-0.35, -0.08, 0.15), (-0.20, 0.00, 1.25), GLYPH_TEXTURE),  # F stem, on the left
    ((-0.20, -0.08, 1.10), (0.35, 0.00, 1.25), GLYPH_TEXTURE),   # F top arm, reaching +x
    ((-0.20, -0.08, 0.60), (0.20, 0.00, 0.75), GLYPH_TEXTURE),   # F middle arm, reaching +x
]
# Box corners 0-3 at z0, 4-7 at z1; each quad counter-clockwise seen from outside, with its outward normal.
QUADS = [
    ((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)),
    ((0, 1, 5, 4), (0, -1, 0)), ((2, 3, 7, 6), (0, 1, 0)),
    ((3, 0, 4, 7), (-1, 0, 0)), ((1, 2, 6, 5), (1, 0, 0)),
]
QUAD_AS_TRIANGLES = (((0, 1, 2), ((0, 1), (1, 1), (1, 0))),
                     ((0, 2, 3), ((0, 1), (1, 0), (0, 0))))


# scripts/tools/py3d under the repo root, four folders above skills/dayz-model-tools/scripts/winding_fixtures/
REPO_PY3D = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
    "scripts", "tools", "py3d")


def load_py3d(extra):
    # each path goes to the front, so the last one is searched first: --py3d wins over the repo copy
    for path in [REPO_PY3D] + ([extra] if extra else []):
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)
    import py3d
    version = tuple(map(int, py3d.__version__.split(".")))
    if not getattr(py3d, "IS_DAYZ_FORK", False) or version < (1, 8, 0):
        raise SystemExit("needs the py3d DayZ fork >= 1.8.0 (blender_to_dayz, ROT_X_NEG90); got %s from %s"
                         % (py3d.__version__, py3d.__file__))
    return py3d


def blender_model(py3d):
    """The chiral F in Blender space: one visual LOD at resolution 0.0."""
    p3d = py3d.P3D()
    lod = py3d.LOD()
    lod.resolution = 0.0
    for (x0, y0, z0), (x1, y1, z1), texture in BOXES:
        base = len(lod.points)
        for coords in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                       (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]:
            point = py3d.Point()
            point.coords = coords
            point.flags = 0
            lod.points.append(point)
        for quad, normal in QUADS:
            normal_index = len(lod.facenormals)
            lod.facenormals.append(tuple(float(c) for c in normal))
            for tri, uvs in QUAD_AS_TRIANGLES:
                face = py3d.Face(lod.points, lod.facenormals)
                face.flags = 0
                face.texture = texture
                face.material = ""
                for k, uv in zip(tri, uvs):
                    vertex = py3d.Vertex(lod.points, lod.facenormals)
                    vertex.point_index = base + quad[k]
                    vertex.normal_index = normal_index
                    vertex.uv = uv
                    face.vertices.append(vertex)
                lod.faces.append(face)
    p3d.lods.append(lod)
    return p3d


def negate_normal_pool(p3d):
    for lod in p3d.lods:
        for j, n in enumerate(lod.facenormals):
            lod.facenormals[j] = (-n[0], -n[1], -n[2])


def variants(py3d):
    b = blender_model(py3d)
    py3d.blender_to_dayz(b)
    a = blender_model(py3d)
    a.transform(py3d.ROT_X_NEG90)
    for lod in a.lods:
        for face in lod.faces:
            face.vertices.reverse()
    negate_normal_pool(a)
    c = blender_model(py3d)
    c.transform(py3d.ROT_X_NEG90)
    b_out = blender_model(py3d)
    py3d.blender_to_dayz(b_out)
    negate_normal_pool(b_out)
    return {"mirror_a.p3d": a, "mirror_b.p3d": b, "mirror_c.p3d": c, "mirror_b_normals_out.p3d": b_out}


def serialize(p3d):
    stream = io.BytesIO()
    p3d.write(stream)
    return stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--py3d", default=None)
    args = parser.parse_args()
    py3d = load_py3d(args.py3d)
    data = {name: serialize(p3d) for name, p3d in variants(py3d).items()}
    wrong = [name for name, digest in IN_GAME_SHA256.items()
             if hashlib.sha256(data[name]).hexdigest() != digest]
    if wrong:
        raise SystemExit("py3d %s from %s does not reproduce the in-game MLODs %s; nothing written"
                         % (py3d.__version__, py3d.__file__, ", ".join(wrong)))
    os.makedirs(args.out, exist_ok=True)
    for name, blob in data.items():
        with open(os.path.join(args.out, name), "wb") as stream:
            stream.write(blob)
        print("%s  %s  %d bytes" % (hashlib.sha256(blob).hexdigest(), name, len(blob)))


if __name__ == "__main__":
    main()
