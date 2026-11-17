#!/usr/bin/env python3
"""
Offline gate on the sections of a binarized vehicle model (ODOL): for each named
selection it prints the section table entries, textures, materials, vertices, UVs,
bone references and face areas, and says whether the engine can draw it. Reports
findings; never modifies files.

Usage:
    python gate_odol_sections.py MODEL.p3d [--selection NAME ...] [--lod RES ...]
                                 [--keyword WORD ...] [--backend-root DIR]

A selection added to a model by tooling can be present in every string table of
the binarized file and still never render. What decides is its section: the
selection must be sectional, own at least one section, and each of those sections
must carry the hidden-selection bit 0x20000 in its "special" flags. Pass the
selections to gate with --selection. With none, only the overview is printed
(version, LODs, skeleton bones, relevant textures and materials, proxies).

Exit codes:
    0  every gated selection is drawable in every gated LOD (or none was named)
    1  a model defect, one "FAIL:" line per defect on stderr
    2  no input, a missing or unreadable file, a LOD that is not in the model,
       or no ODOL parser backend

Reads only the file it is given, so it does not gate on /dayz-preflight.

The ODOL parser is an external backend (the modules bis_reader and odol_reader of
an ODOL to MLOD converter). It is not part of this repo. Point at its folder with
--backend-root or the environment variable DAYZ_ODOL_BACKEND_ROOT, the same
variable scripts/tools/dayz-odol-strict reads.
"""

import argparse
import math
import os
import struct
import sys

BACKEND_ENV = "DAYZ_ODOL_BACKEND_ROOT"
HIDDEN_SELECTION_BIT = 0x20000

# Third-person (0) and first-person (1100) visual LODs of a vehicle.
DEFAULT_LODS = (0.0, 1100.0)
# Substrings that mark a texture or material as worth listing in the overview.
DEFAULT_KEYWORDS = ("gps", "marker", "cluster", "screen", "argb", "color", "dashboard", "cab_screen")


class InputError(Exception):
    """A problem with the input or the environment, not with the model."""


def load_backend(backend_root=None):
    """Import the external ODOL parser. Returns (BisReader, LOD, ODOL_ModelInfo)."""
    root = backend_root or os.environ.get(BACKEND_ENV)
    if not root:
        raise InputError(
            f"no ODOL parser backend: pass --backend-root DIR or set {BACKEND_ENV} "
            "to the folder that holds bis_reader.py and odol_reader.py"
        )
    if not os.path.isfile(os.path.join(root, "odol_reader.py")):
        raise InputError(f"no odol_reader.py in backend root: {root}")
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from bis_reader import BisReader
        from odol_reader import LOD, ODOL_ModelInfo
    except ImportError as exc:
        raise InputError(f"cannot import the ODOL parser backend from {root}: {exc}") from exc
    return BisReader, LOD, ODOL_ModelInfo


def open_odol(path, bis_reader_cls, model_info_cls):
    """Read the ODOL header up to the end of the model info block."""
    reader = bis_reader_cls.from_file(path)
    idx = reader.data.find(b"ODOL")
    if idx < 0:
        raise InputError(f"no ODOL signature in {path} (an MLOD source model cannot be gated here)")
    reader.position = idx
    reader.read_ascii(4)
    ver = reader.read_uint32()
    reader.version = ver
    if ver >= 44:
        reader.use_lzo = True
    if ver >= 64:
        reader.use_compression_flag = True
    if ver >= 59:
        reader.read_uint32()
    if ver >= 58:
        reader.read_asciiz()
    n = reader.read_int32()
    ress = [reader.read_float() for _ in range(n)]
    mi = model_info_cls.read(reader, n)
    saved = reader.position
    file_size = len(reader.data)
    return reader, ver, n, ress, mi, saved, file_size


def find_table(data, n, saved, file_size):
    """Find the LOD address table (n start offsets, n end offsets, n flag bytes)
    after the model info block. A naive scan for the first plausible table hits a
    false positive, so every candidate is scored: a table whose largest end is at
    the end of the file and whose LODs chain (each end is the previous start) wins.
    Returns (score, offset, starts, ends, flags) or None."""

    def try_lod(pos):
        if pos + n * 9 > file_size:
            return None
        ls = [struct.unpack_from("<I", data, pos + i * 4)[0] for i in range(n)]
        le = [struct.unpack_from("<I", data, pos + n * 4 + i * 4)[0] for i in range(n)]
        pm = [data[pos + n * 8 + i] for i in range(n)]
        if any(s == 0 or s >= file_size or e > file_size or e < s for s, e in zip(ls, le)):
            return None
        if any(p not in (0, 1) for p in pm):
            return None
        return ls, le, pm

    best = None
    for off in range(saved, min(file_size - n * 9, saved + 200000) + 1):
        got = try_lod(off)
        if not got:
            continue
        ls, le, pm = got
        score = 0
        if max(le) >= file_size - 8:
            score += 100
        if all(le[i] == ls[i - 1] for i in range(1, n)):
            score += 50
        if all(ls[i] > ls[i + 1] for i in range(n - 1)):
            score += 20
        if all(ls[i] < ls[i + 1] for i in range(n - 1)):
            score += 20
        sizes = [le[i] - ls[i] for i in range(n)]
        if max(sizes) > 100000:
            score += 10
        if best is None or score > best[0]:
            best = (score, off, ls, le, pm)
    return best


def ns_by_name(lod, name):
    for ns in lod.named_selections:
        if ns.name.lower() == name.lower():
            return ns
    return None


def cover_map(lod):
    """Face index -> the sections that draw it."""
    cover = {}
    for si, sec in enumerate(lod.sections):
        for fi in sec.get_face_indices(lod.faces):
            cover.setdefault(fi, []).append(si)
    return cover


def tex_of(lod, sec):
    if 0 <= sec.texture_index < len(lod.textures):
        return lod.textures[sec.texture_index]
    return f"<tex {sec.texture_index}>"


def mat_of(lod, sec):
    if sec.material_index == -1:
        return sec.mat_name
    if 0 <= sec.material_index < len(lod.materials):
        return lod.materials[sec.material_index].material_name
    return f"<mat {sec.material_index}>"


def vxyz(lod, vi):
    v = lod.vertices[vi]
    return (v.x, v.y, v.z)


def uv(lod, vi):
    d = lod.uv_sets[0].uv_data
    return d[vi * 2], d[vi * 2 + 1]


def face_area(lod, idxs):
    """Area of a face in square metres, as a triangle fan."""
    o = vxyz(lod, idxs[0])
    area = 0.0
    for k in range(1, len(idxs) - 1):
        b = vxyz(lod, idxs[k])
        c = vxyz(lod, idxs[k + 1])
        ux, uy, uz = b[0] - o[0], b[1] - o[1], b[2] - o[2]
        vx, vy, vz = c[0] - o[0], c[1] - o[1], c[2] - o[2]
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        area += 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
    return area


def section_line(si, sec, nfaces=None):
    count = "" if nfaces is None else f" nfaces={nfaces}"
    return (
        f"sec[{si}] lower={sec.face_lower} upper={sec.face_upper}{count} min_bone={sec.min_bone} "
        f"bones={sec.bones_count} tex_i={sec.texture_index} special=0x{sec.special:08X} "
        f"mat_i={sec.material_index} aot={sec.area_over_tex}"
    )


def dump_sel(lod, name):
    """Print everything the section table says about one named selection."""
    ns = ns_by_name(lod, name)
    print(f"  {name}:", end=" ")
    if ns is None:
        print("MISSING")
        return
    print(
        f"faces={len(ns.selected_faces)} verts={len(ns.selected_vertices)} "
        f"sectional={ns.is_sectional} sections={list(ns.sections)}"
    )
    cover = cover_map(lod)
    fis = list(ns.selected_faces)
    vis = list(ns.selected_vertices)
    print(f"    selected_faces={fis}")
    print(f"    selected_verts n={len(vis)} {vis[:24]}")
    sec_hits = set()
    for fi in fis:
        sec_hits.update(cover.get(fi, []))
    print(f"    faces_in_sections {sorted(sec_hits)}")
    for si in sorted(set(list(ns.sections) + list(sec_hits))):
        if si < 0 or si >= len(lod.sections):
            print("    bad sec", si)
            continue
        sec = lod.sections[si]
        print("    " + section_line(si, sec, len(sec.get_face_indices(lod.faces))))
        print(f"           tex={tex_of(lod, sec)!r}")
        print(f"           mat={mat_of(lod, sec)!r}")
    bbmin = (lod.b_min.x, lod.b_min.y, lod.b_min.z)
    bbmax = (lod.b_max.x, lod.b_max.y, lod.b_max.z)
    us, vs = [], []
    inside = outside = 0
    for vi in vis:
        p = vxyz(lod, vi)
        u, v = uv(lod, vi)
        us.append(u)
        vs.append(v)
        inb = all(bbmin[k] <= p[k] <= bbmax[k] for k in range(3))
        inside += int(inb)
        outside += int(not inb)
        br = lod.vertex_bone_ref[vi] if vi < len(lod.vertex_bone_ref) else None
        print(
            f"    v[{vi}] xyz=({p[0]:.6f},{p[1]:.6f},{p[2]:.6f}) uv=({u:.6f},{v:.6f}) "
            f"in_bbox={inb} bone={None if br is None else br.pairs}"
        )
    if us:
        print(
            f"    UV U[{min(us):.6f},{max(us):.6f}] span={max(us) - min(us):.6f} "
            f"V[{min(vs):.6f},{max(vs):.6f}] span={max(vs) - min(vs):.6f}"
        )
    print(f"    verts_in_bbox {inside} out {outside}")
    for fi in fis:
        idxs = lod.faces[fi].vertex_indices
        print(f"    face[{fi}] n={len(idxs)} idx={idxs}")
        if len(idxs) >= 3:
            print(f"      area_mm2={face_area(lod, idxs) * 1e6:.4f}")


def selection_defects(lod, name, lod_label):
    """Why the engine cannot draw a named selection in this LOD, as text lines."""
    ns = ns_by_name(lod, name)
    if ns is None:
        return [f"LOD {lod_label}: selection {name} is missing"]
    found = []
    sections = list(ns.sections)
    if not ns.is_sectional:
        found.append(f"LOD {lod_label}: selection {name} is not sectional (list it in CfgModels sections[])")
    if not sections:
        found.append(f"LOD {lod_label}: selection {name} owns no section, so it has no draw call")
    for si in sections:
        if si < 0 or si >= len(lod.sections):
            found.append(f"LOD {lod_label}: selection {name} names section {si}, which does not exist")
            continue
        special = lod.sections[si].special
        if not special & HIDDEN_SELECTION_BIT:
            found.append(
                f"LOD {lod_label}: selection {name} section {si} has special=0x{special:08X} "
                f"without the hidden-selection bit 0x{HIDDEN_SELECTION_BIT:X} (never drawn)"
            )
    return found


def print_lod(lod, want, selections, keywords):
    print(
        f"\n======== ODOL {want} verts={len(lod.vertices)} faces={len(lod.faces)} "
        f"secs={len(lod.sections)} ns={len(lod.named_selections)}"
    )
    print(f"  bbox {lod.b_min}->{lod.b_max} r={lod.b_radius}")
    print(f"  or_hints=0x{lod.or_hints:08X} and_hints=0x{lod.and_hints:08X} special=0x{lod.special:08X}")
    u0 = lod.uv_sets[0]
    print(
        f"  uv0 disc={u0.is_discretized} U[{u0.min_u:.6f},{u0.max_u:.6f}] "
        f"V[{u0.min_v:.6f},{u0.max_v:.6f}] n={u0.n_vertices} fill={u0.default_fill}"
    )
    print("  relevant textures:")
    for ti, tex in enumerate(lod.textures):
        if any(word in tex.lower() for word in keywords):
            print(f"    tex[{ti}] {tex!r}")
    print("  relevant materials:")
    for mi, mat in enumerate(lod.materials):
        if any(word in mat.material_name.lower() for word in keywords):
            print(f"    mat[{mi}] {mat.material_name!r} em={mat.emissive} dif={mat.diffuse}")
    cover = cover_map(lod)
    uncovered = [fi for fi in range(len(lod.faces)) if fi not in cover]
    print(f"  uncovered_faces {len(uncovered)}")
    for name in selections:
        dump_sel(lod, name)
    print("  proxies", len(lod.proxies))
    for pr in lod.proxies:
        print(f"    proxy {pr.model!r} bone={pr.bone_index} sec={pr.section_index} nsel={pr.named_selection_index}")


def read_lods(path, wanted, backend_root=None):
    """Parse the wanted LODs of an ODOL. Returns (version, resolutions, model info, address table, {resolution: lod})."""
    bis_reader_cls, lod_cls, model_info_cls = load_backend(backend_root)
    try:
        reader, ver, n, ress, mi, saved, file_size = open_odol(path, bis_reader_cls, model_info_cls)
        best = find_table(reader.data, n, saved, file_size)
        if best is None:
            raise InputError(f"no LOD address table found in {path}")
        starts = best[2]
        lods = {}
        for want in wanted:
            if want not in ress:
                raise InputError(f"LOD {want} is not in {path}; its LODs are {ress}")
            reader.position = starts[ress.index(want)]
            lods[want] = lod_cls.read(reader, want)
    except InputError:
        raise
    except Exception as exc:  # the backend raises plain exceptions on a file it cannot read
        raise InputError(f"cannot parse {path}: {type(exc).__name__}: {exc}") from exc
    return ver, ress, mi, best, lods


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="gate_odol_sections.py",
        description="Gate the sections of named selections in a binarized vehicle model (ODOL).",
    )
    parser.add_argument("model", help="binarized .p3d taken out of the packed PBO")
    parser.add_argument("--selection", action="append", default=[], metavar="NAME",
                        help="named selection to dump and gate; repeat for more")
    parser.add_argument("--lod", action="append", type=float, default=[], metavar="RES",
                        help="LOD resolution to read; repeat for more (default: 0 and 1100)")
    parser.add_argument("--keyword", action="append", default=[], metavar="WORD",
                        help="substring that marks a texture, material or bone as relevant; repeat for more")
    parser.add_argument("--backend-root", metavar="DIR",
                        help=f"folder of the external ODOL parser (default: ${BACKEND_ENV})")
    return parser.parse_args(argv)


def main(argv=None):
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    wanted = args.lod or list(DEFAULT_LODS)
    keywords = tuple(word.lower() for word in args.keyword) or DEFAULT_KEYWORDS

    if not os.path.isfile(args.model):
        print(f"INPUT_ERROR: missing file: {args.model}", file=sys.stderr)
        return 2
    try:
        ver, ress, mi, best, lods = read_lods(args.model, wanted, args.backend_root)
    except InputError as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2

    print("ver", ver, "n", len(ress), "res", ress)
    skeleton = getattr(mi, "skeleton", None)
    print("skeleton", skeleton)
    if skeleton:
        names = {name.lower() for name in args.selection}
        for i, (bone, parent) in enumerate(skeleton.bones):
            low = bone.lower()
            if low in names or any(word in low for word in keywords):
                print(f"  bone[{i}] {bone!r} parent={parent!r}")
    print("best table score", best[0], "off", best[1])

    failures = []
    for want in wanted:
        print_lod(lods[want], want, args.selection, keywords)
        for name in args.selection:
            failures += selection_defects(lods[want], name, want)
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
