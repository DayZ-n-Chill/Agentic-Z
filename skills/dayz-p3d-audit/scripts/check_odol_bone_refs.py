#!/usr/bin/env python3
"""
Which skeleton bone do the vertices of a section bind to in a binarized vehicle
model (ODOL)? A vertex bound to a bone whose hide animation starts at phase 1 is
invisible from spawn, whatever the material or the section says. Reports findings;
never modifies files.

Usage:
    python check_odol_bone_refs.py MODEL.p3d --texture SUBSTR [--texture SUBSTR ...]
                                   [--max-faces N] [--reference-texture SUFFIX]
                                   [--lod RES ...] [--backend-root DIR]

For each LOD it lists every section whose texture path contains one of the
--texture substrings (and, with --max-faces, has at most that many faces: a
witness quad is two), with the bone and weight of each of its vertices. With
--reference-texture it also prints the bone of the first vertex of a section that
is known to render (the first section with more than ten faces whose texture path
ends with SUFFIX), to compare against.

Exit codes:
    0  the report was printed
    2  no input, a missing or unreadable file, a LOD that is not in the model,
       or no ODOL parser backend

The script reports and does not judge: read the bone names against the model.cfg
animations of the model. Reads only the file it is given, so it does not gate on
/dayz-preflight. It uses the same external ODOL parser backend as
gate_odol_sections.py (--backend-root or DAYZ_ODOL_BACKEND_ROOT).
"""

import argparse
import importlib.util
import os
import sys
from pathlib import Path


def _load_gate():
    """Load gate_odol_sections.py from this folder under a name of its own."""
    name = "dayz_vehicles_gate_odol_sections"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / "gate_odol_sections.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def bone_names(lod, bones, vi, with_weight=True):
    """The bones one vertex is bound to, as text, or NONE/static."""
    br = lod.vertex_bone_ref[vi] if vi < len(lod.vertex_bone_ref) else None
    pairs = getattr(br, "pairs", None) if br else None
    if not pairs:
        return "NONE/static"
    names = []
    for bone, weight in pairs:
        name = bones[bone][0] if 0 <= bone < len(bones) else "?"
        names.append(f"{name}(b{bone},w{weight})" if with_weight else f"{name}(b{bone})")
    return ", ".join(names)


def report_lod(lod, want, bones, textures, max_faces, reference):
    print("\n=== LOD %.0f ===" % want)
    for si, sec in enumerate(lod.sections):
        tex = gate.tex_of(lod, sec).lower()
        hit = next((word for word in textures if word in tex), None)
        if hit is None:
            continue
        fis = sec.get_face_indices(lod.faces)
        if max_faces is not None and len(fis) > max_faces:
            continue
        vis = sorted({vi for fi in fis for vi in lod.faces[fi].vertex_indices})
        print("  %s sec[%d] faces=%s verts=%s" % (hit, si, fis, vis))
        for vi in vis:
            print("     v[%d] bone=%s" % (vi, bone_names(lod, bones, vi)))
    if not reference:
        return
    for si, sec in enumerate(lod.sections):
        fis = sec.get_face_indices(lod.faces)
        if gate.tex_of(lod, sec).lower().endswith(reference) and len(fis) > 10:
            vi = lod.faces[fis[0]].vertex_indices[0]
            print("  REFERENCE(renders) sec[%d] first vert bone=%s" % (si, bone_names(lod, bones, vi, False)))
            break


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="check_odol_bone_refs.py",
        description="List the skeleton bone of each vertex of the sections that use a texture, in a binarized model (ODOL).",
    )
    parser.add_argument("model", help="binarized .p3d taken out of the packed PBO")
    parser.add_argument("--texture", action="append", default=[], metavar="SUBSTR",
                        help="report sections whose texture path contains this; repeat for more")
    parser.add_argument("--max-faces", type=int, metavar="N",
                        help="report only sections with at most N faces")
    parser.add_argument("--reference-texture", metavar="SUFFIX",
                        help="also print the bone of a section that renders, found by the end of its texture path")
    parser.add_argument("--lod", action="append", type=float, default=[], metavar="RES",
                        help="LOD resolution to read; repeat for more (default: 0 and 1100)")
    parser.add_argument("--backend-root", metavar="DIR",
                        help=f"folder of the external ODOL parser (default: ${gate.BACKEND_ENV})")
    return parser.parse_args(argv)


def main(argv=None):
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if not args.texture:
        print("INPUT_ERROR: name at least one --texture SUBSTR", file=sys.stderr)
        return 2
    if not os.path.isfile(args.model):
        print(f"INPUT_ERROR: missing file: {args.model}", file=sys.stderr)
        return 2
    wanted = args.lod or list(gate.DEFAULT_LODS)
    try:
        _ver, _ress, mi, _best, lods = gate.read_lods(args.model, wanted, args.backend_root)
    except gate.InputError as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2

    skeleton = getattr(mi, "skeleton", None)
    bones = skeleton.bones if skeleton else []
    print("skeleton bones:", len(bones))
    textures = [word.lower() for word in args.texture]
    reference = args.reference_texture.lower() if args.reference_texture else None
    for want in wanted:
        report_lod(lods[want], want, bones, textures, args.max_faces, reference)
    return 0


if __name__ == "__main__":
    sys.exit(main())
