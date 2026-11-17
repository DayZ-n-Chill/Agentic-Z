#!/usr/bin/env python3
r"""py3d command line.

    python -m py3d info     <p3d>      # readback kept as evidence
    python -m py3d validate <p3d>      # findings from P3D.validate()
    python -m py3d diff     <a> <b>    # check what an edit changed

The output schema is STABLE ("key: value" lines, pinned by the tests):
changing it is a contract change and needs a version bump.
1.6.0: `info` gained `lod.N.uv_sets` (ids separated by ';') and `diff`
compares the UV set ids per LOD (`diff.lod.N.uv_sets`).
1.7.0: `info` gained `lod.N.selected` (the editor's current selection as
`Np/Mf`, or `-` when the LOD carries no `#Selected#`) and `diff` reports it
under the same `diff.lod.N.selection.#Selected#.*` keys as a named one.

Exit codes:
    info:     0 ok                     | 2 input not readable
    validate: 0 clean (no ERROR)        | 1 ERRORs | 2 not readable
    diff:     0 equal | 1 different     | 2 input not readable

`info` is the readback a pipeline can keep as evidence (LODs, resolutions,
counts, Component01, materials); `diff` is for checking that an edit did
what it was meant to - within the limits KNOWN-ISSUES.md documents.
"""

import argparse
import os
import sys

from . import P3D, LOD_RESOLUTIONS  # noqa: F401  (stable surface)


def _fmt(x):
    return "%.6g" % x


def _fmt3(c):
    return "(%s,%s,%s)" % (_fmt(c[0]), _fmt(c[1]), _fmt(c[2]))


def _load(path):
    """(P3D, None) or (None, reason)."""
    if not os.path.isfile(path):
        return None, "file not found: %s" % path
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"MLOD":
                return None, "not an MLOD .p3d (ODOL or other): %s" % path
            f.seek(0)
            return P3D(f), None
    except Exception as e:  # a broken parse means unreadable input
        return None, "unreadable MLOD: %s (%s)" % (path, e)


def cmd_info(args):
    model, err = _load(args.file)
    if err:
        print("error: %s" % err, file=sys.stderr)
        return 2
    out = []
    out.append("file: %s" % os.path.basename(args.file))
    out.append("lods: %d" % len(model.lods))
    has_component01 = False
    mass_total = None
    for i, lod in enumerate(model.lods):
        k = lod.kind()
        out.append("lod.%d.kind: %s" % (i, k if k else "unknown"))
        out.append("lod.%d.resolution: %s" % (i, _fmt(lod.resolution)))
        out.append("lod.%d.points: %d" % (i, len(lod.points)))
        out.append("lod.%d.faces: %d" % (i, len(lod.faces)))
        m = lod.mass
        out.append("lod.%d.mass: %s" % (i, _fmt(m) if m is not None
                                        else "none"))
        if m is not None:
            mass_total = (mass_total or 0.0) + m
        sels = ";".join("%s(%dp/%df)" % (n, len(s.points), len(s.faces))
                        for n, s in lod.selections.items())
        out.append("lod.%d.selections: %s" % (i, sels or "-"))
        out.append("lod.%d.selected: %s" % (
            i, "-" if lod.selected is None else "%dp/%df" % (
                len(lod.selected.points), len(lod.selected.faces))))
        props = ";".join("%s=%s" % kv for kv in lod.properties.items())
        out.append("lod.%d.properties: %s" % (i, props or "-"))
        textures = sorted({fa.texture for fa in lod.faces if fa.texture})
        materials = sorted({fa.material for fa in lod.faces if fa.material})
        out.append("lod.%d.textures: %s" % (i, ";".join(textures) or "-"))
        out.append("lod.%d.materials: %s" % (i, ";".join(materials) or "-"))
        out.append("lod.%d.uv_sets: %s" % (
            i, ";".join(str(u) for u in lod.uv_set_ids())))
        if k == "geometry" and "Component01" in lod.selections:
            has_component01 = True
        if k == "memory":
            mps = ";".join("%s=%s" % (n, _fmt3(c))
                           for n, c in lod.get_memory_points().items())
            out.append("lod.%d.memory_points: %s" % (i, mps or "-"))
    out.append("summary.component01: %s" % ("yes" if has_component01
                                            else "no"))
    out.append("summary.mass_total: %s" % (_fmt(mass_total)
                                           if mass_total is not None
                                           else "none"))
    print("\n".join(out))
    return 0


def cmd_validate(args):
    model, err = _load(args.file)
    if err:
        print("error: %s" % err, file=sys.stderr)
        return 2
    findings = model.validate(normals_budget=args.normals_budget,
                              normals_severity=args.normals_severity)
    print("findings: %d" % len(findings))
    for j, f in enumerate(findings):
        lod = "-" if f.lod is None else str(f.lod)
        print("finding.%d: %s %s lod=%s %s" % (j, f.severity, f.code,
                                               lod, f.msg))
    errors = any(f.severity == "ERROR" for f in findings)
    print("result: %s" % ("errors" if errors
                          else ("warnings" if findings else "clean")))
    return 1 if errors else 0


def _diff_memory(a, b, i, diffs, tol=1e-4):
    ma = a.get_memory_points()
    mb = b.get_memory_points()
    for name in ma:
        if name not in mb:
            diffs.append("diff.lod.%d.memory.%s: only in a (%s)"
                         % (i, name, _fmt3(ma[name])))
            continue
        ca, cb = ma[name], mb[name]
        if any(abs(ca[j] - cb[j]) > tol for j in range(3)):
            diffs.append("diff.lod.%d.memory.%s: %s != %s"
                         % (i, name, _fmt3(ca), _fmt3(cb)))
    for name in mb:
        if name not in ma:
            diffs.append("diff.lod.%d.memory.%s: only in b (%s)"
                         % (i, name, _fmt3(mb[name])))


def _selection_map(lod):
    """Named selections plus the editor's current one under its tag name.

    `#Selected#` is anonymous on the model but has a named selection's
    layout, so the diff treats it as one more entry: an edit that drops it
    shows up as a missing name instead of being invisible.
    """
    sels = {}
    if lod.selected is not None:
        sels["#Selected#"] = lod.selected
    sels.update(lod.selections)
    return sels


def _diff_selections(a, b, i, diffs):
    a_sels, b_sels = _selection_map(a), _selection_map(b)
    na = list(a_sels.keys())
    nb = list(b_sels.keys())
    only_a = [n for n in na if n not in b_sels]
    only_b = [n for n in nb if n not in a_sels]
    if only_a or only_b:
        diffs.append("diff.lod.%d.selections.names: +a%r +b%r"
                     % (i, only_a, only_b))
    pt_a = {id(p): j for j, p in enumerate(a.points)}
    fc_a = {id(f): j for j, f in enumerate(a.faces)}
    pt_b = {id(p): j for j, p in enumerate(b.points)}
    fc_b = {id(f): j for j, f in enumerate(b.faces)}
    for n in na:
        if n not in b_sels:
            continue
        sa, sb = a_sels[n], b_sels[n]
        ia = sorted(pt_a[id(p)] for p in sa.points if id(p) in pt_a)
        ib = sorted(pt_b[id(p)] for p in sb.points if id(p) in pt_b)
        if ia != ib:
            diffs.append("diff.lod.%d.selection.%s.points: %d != %d "
                         "(membership)" % (i, n, len(ia), len(ib)))
        ja = sorted(fc_a[id(f)] for f in sa.faces if id(f) in fc_a)
        jb = sorted(fc_b[id(f)] for f in sb.faces if id(f) in fc_b)
        if ja != jb:
            diffs.append("diff.lod.%d.selection.%s.faces: %d != %d "
                         "(membership)" % (i, n, len(ja), len(jb)))


def cmd_diff(args):
    a, err = _load(args.a)
    if err:
        print("error: %s" % err, file=sys.stderr)
        return 2
    b, err = _load(args.b)
    if err:
        print("error: %s" % err, file=sys.stderr)
        return 2
    diffs = []
    if len(a.lods) != len(b.lods):
        diffs.append("diff.lods.count: %d != %d"
                     % (len(a.lods), len(b.lods)))
    for i in range(min(len(a.lods), len(b.lods))):
        la, lb = a.lods[i], b.lods[i]
        ka, kb = la.kind(), lb.kind()
        if ka != kb:
            diffs.append("diff.lod.%d.kind: %s != %s"
                         % (i, ka or "unknown", kb or "unknown"))
            continue
        if len(la.points) != len(lb.points):
            diffs.append("diff.lod.%d.points: %d != %d"
                         % (i, len(la.points), len(lb.points)))
        if len(la.faces) != len(lb.faces):
            diffs.append("diff.lod.%d.faces: %d != %d"
                         % (i, len(la.faces), len(lb.faces)))
        _diff_selections(la, lb, i, diffs)
        pa, pb = dict(la.properties), dict(lb.properties)
        for k in pa:
            if k not in pb:
                diffs.append("diff.lod.%d.property.%s: only in a" % (i, k))
            elif pa[k] != pb[k]:
                diffs.append("diff.lod.%d.property.%s: %r != %r"
                             % (i, k, pa[k], pb[k]))
        for k in pb:
            if k not in pa:
                diffs.append("diff.lod.%d.property.%s: only in b" % (i, k))
        ma, mb = la.mass, lb.mass
        if (ma is None) != (mb is None) or \
                (ma is not None and abs(ma - mb) > 1e-3):
            diffs.append("diff.lod.%d.mass: %s != %s"
                         % (i, _fmt(ma) if ma is not None else "none",
                            _fmt(mb) if mb is not None else "none"))
        ua, ub = la.uv_set_ids(), lb.uv_set_ids()
        if ua != ub:
            diffs.append("diff.lod.%d.uv_sets: %s != %s"
                         % (i, ";".join(map(str, ua)),
                            ";".join(map(str, ub))))
        if ka == "memory":
            _diff_memory(la, lb, i, diffs)
    for line in diffs:
        print(line)
    print("total: %d" % len(diffs))
    return 1 if diffs else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m py3d",
        description="py3d DayZ fork - info/validate/diff for MLOD .p3d")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_info = sub.add_parser("info", help="readback kept as evidence")
    p_info.add_argument("file")
    p_val = sub.add_parser("validate", help="P3D.validate()")
    p_val.add_argument("file")
    p_val.add_argument("--normals-budget", type=int, default=32768)
    p_val.add_argument("--normals-severity", default="WARN",
                       choices=("WARN", "ERROR"))
    p_diff = sub.add_parser("diff", help="compare two .p3d files")
    p_diff.add_argument("a")
    p_diff.add_argument("b")
    args = parser.parse_args(argv)
    return {"info": cmd_info, "validate": cmd_validate,
            "diff": cmd_diff}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
