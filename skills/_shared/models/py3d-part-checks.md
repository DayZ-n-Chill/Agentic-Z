# Part checks with py3d

py3d checks for a generated model's proxies, its selections across LODs and its collision LODs, and a runner that calls these and the shape checks of `py3d-shape-checks.md` in one go. They are quick checks while generating; `/dayz-p3d-audit` is the gate before a build.

Tool knowledge about MLOD files. The vanilla figures the checks lean on are cited where they appear; the functions use `classify_lod` from `py3d-reading.md`.

## Proxies

Each proxy selection must end in a three digit index, keep no `.p3d` before it, and hold one triangle in every visual LOD.

```python
def check_proxy_system(model):
    issues = []
    lod0 = model.lods[0]
    for name in [n for n in lod0.selections if n.startswith("proxy:")]:
        head, _, index = name.rpartition(".")
        if not head or not index.isdigit() or len(index) != 3:
            issues.append(f"PROXY NAME: '{name}' should end with a three digit index such as .001")
        elif head.lower().endswith(".p3d"):
            issues.append(f"PROXY NAME: '{name}' keeps .p3d before the index; write the path without it")

        for i, lod in enumerate(model.lods):
            if 0 <= lod.resolution < 10:                       # visual LODs
                if name not in lod.selections:
                    issues.append(f"PROXY MISSING in LOD {i} (res={lod.resolution}): '{name}'")
                    continue
                sel = lod.selections[name]
                pts = [p for p, w in sel.points.items() if w > 0]
                faces = [f for f, w in sel.faces.items() if w > 0]
                if len(pts) != 3 or len(faces) != 1:
                    issues.append(f"PROXY SHAPE in LOD {i}: expected 3 points and 1 face, "
                                  f"got {len(pts)} and {len(faces)}")
    return issues
```

It asks for the form without `.p3d`, which vanilla stores in 28,628 of its 28,775 proxy names (`proxies.md`, from the models under `P:\DZ\`; for example `proxy:\dz\gear\consumables\single_plank.000` in `P:\DZ\gear\camping\fence.p3d`) and which `add_proxy` writes. It does not check View Geometry, where an attachment proxy also belongs since 1.30 (`py3d-proxies.md`).

## Selections across LODs

```python
def check_selection_consistency(model):
    """Visual selections that a collision LOD lacks."""
    issues = []
    by_type = {classify_lod(l.resolution): set(l.selections) for l in model.lods}
    for name in by_type.get("Visual 0.0", set()):
        if name.startswith("proxy:") or name in ("zbytek", "AGGzbytek"):
            continue
        for kind in ("Geometry", "Fire Geometry", "View Geometry"):
            if kind in by_type and name not in by_type[kind]:
                issues.append(f"SELECTION MISSING: '{name}' is in the visual LOD but not in {kind}")
    return issues
```

Read its findings as questions, not errors. A selection that only swaps a texture (`camo`, an LED) or a part whose collision does not move has no reason to be in a collision LOD. A moving part that should block, be shot or be clicked while it moves does (`selections.md`).

## Collision LODs

Each collision LOD needs `autocenter=0` on a placed object built from scratch (`generated-model-rules.md`, "`autocenter=0` on every collision LOD") and a penetration material on every face (`generated-model-rules.md`, "A penetration material on every collision face"). The Geometry LOD also needs mass on every point and at least one `ComponentNN` selection.

```python
COLLISION_LODS = {
    "Geometry":     (0.99e13, 1.01e13),
    "LandContact":  (1.99e15, 2.01e15),
    "Roadway":      (2.99e15, 3.01e15),
    "Hitpoints":    (4.99e15, 5.01e15),
    "ViewGeometry": (5.99e15, 6.01e15),
    "FireGeometry": (6.99e15, 7.01e15),
}

def collision_label(r):
    return next((n for n, (lo, hi) in COLLISION_LODS.items() if lo < r < hi), None)

def check_geometry_properties(model):
    issues = []
    for lod in model.lods:
        label = collision_label(lod.resolution)
        if label is None:
            continue
        props = dict(lod.properties)
        if props.get("autocenter") != "0":
            issues.append(f"{label}: no autocenter=0 (found {props.get('autocenter', '(none)')!r}); "
                          f"the engine recentres this LOD by its box and moves the collision off the visible mesh")
        no_mat = sum(1 for f in lod.faces if not (f.material or "").strip())
        if no_mat:
            issues.append(f"{label}: {no_mat}/{len(lod.faces)} faces have no penetration material, "
                          f"for example 'dz\\\\data\\\\data\\\\penetration\\\\wood_desk.rvmat'")
        if label == "Geometry":
            if "class" not in props:
                issues.append("GEOMETRY: no 'class' property (usually 'house' for a static object)")
            no_mass = sum(1 for p in lod.points if p.mass is None or p.mass <= 0)
            if no_mass:
                issues.append(f"GEOMETRY: {no_mass}/{len(lod.points)} points have no mass")
            if not any(n.lower().startswith("component") for n in lod.selections):
                issues.append("GEOMETRY: no Component selection; at least Component01 is needed to collide")
    return issues
```

Two notes on what it asks for. The `class` property is for buildings and placed statics: 1,250 of the 10,626 vanilla models under `P:\DZ\` store `class` = `house`, and most vanilla gear stores no `class` at all (`named-properties.md`), so on an item ignore that finding. The `autocenter` rule is this pipeline's default for a placed object, not something every vanilla model carries, so read it against `named-properties.md` on a kit or a handheld item. The mass check counts a point whose mass is `None`, py3d's default, as having none.

## Running every check

```python
def validate_p3d(filepath):
    with open(filepath, "rb") as f:
        model = py3d.P3D(f)
    issues = []
    for check in (check_centering, check_axis_consistency, check_uv_range, check_face_winding,
                  check_proxy_system, check_selection_consistency, check_geometry_properties):
        issues.extend(check(model))
    print("ALL CHECKS PASSED" if not issues else "\n".join(f"[!] {i}" for i in issues))
    return issues
```

py3d's own `model.validate()` and `save(verify=True)` run alongside these; what their findings mean is in `py3d-assembly-rules.md`.
