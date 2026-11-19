# Proxies with py3d

How to write a proxy triangle into a parent model with py3d, what the triangle is made of, and how to write the minimal proxy model the selection points at. The config class that completes the proxy is in `proxy-attachment-config.md`; the rules for names and indexes are in `proxies.md`, and how a triangle becomes a position and facing is in `proxy-frames.md`.

Tool knowledge about the py3d in `scripts/tools/py3d`. Vanilla stores the name form written here: 28,628 of the 28,775 proxy names in the models under `P:\DZ\` have no `.p3d` before the index, for example `proxy:\dz\gear\consumables\single_plank.000` in `P:\DZ\gear\camping\fence.p3d` (`proxies.md`).

## How a proxy works

1. A tiny triangle sits in the visual LODs of the parent, and since 1.30 in View Geometry too (`dayz-1-30-models.md`).
2. Its face is the only member of a selection named `proxy:<addon path>\<proxy model>.NNN`, with the path written without `.p3d`.
3. The engine reads the triangle's position and facing and draws the attached item's model there.
4. A minimal proxy `.p3d` exists at the path the selection names.
5. A `CfgNonAIVehicles` class ties the `inventorySlot` to the proxy model.

## The short way: `add_proxy`

`LOD.add_proxy` writes the triangle, the selection and its name, and returns the name. It refuses a path that ends in `.p3d` and an index below 1.

```python
for lod in [lod0, lod1, lod2, view_lod]:
    lod.add_proxy("MyAddon\\data\\MySlot", index=1, origin=(0.0, 0.05, 0.0))
# selection: proxy:MyAddon\data\MySlot.001
```

`add_proxy` also takes `rotation` (rows x, y, z; the identity when left out) and `space` (`"raw"` or `"engine"`). Which one gives the pose you want in game is in `proxy-frames.md`. For a vehicle proxy always pass `rotation` and `scale` yourself (`py3d-assembly-rules.md`, "Vehicle proxies need their frame and scale set"). To fix proxies that already exist, use the proxy editor of `/dayz-model-tools` (`tools-proxy-align.md`).

## The long way, part by part

```python
from py3d import Point, Face, Vertex, Selection

proxy_sel_name = "proxy:MyAddon\\data\\MySlot.001"
proxy_center = (0.0, 0.05, 0.0)               # centre of the cradle or slot

# A right triangle with unequal legs: corner 0 is the position (the right angle),
# corner 1 the short leg (+Y, up), corner 2 the long leg (+Z, forward),
# the same triangle add_proxy writes.
proxy_pts_coords = [
    (proxy_center[0], proxy_center[1],         proxy_center[2]),
    (proxy_center[0], proxy_center[1] + 0.001, proxy_center[2]),
    (proxy_center[0], proxy_center[1],         proxy_center[2] + 0.002),
]
proxy_normal = (1.0, 0.0, 0.0)

for lod in [lod0, lod1, lod2]:
    pts = []
    for c in proxy_pts_coords:
        pt = Point(); pt.coords = c; pt.flags = 0
        lod.points.append(pt)
        pts.append(pt)

    lod.facenormals.append(proxy_normal)
    norm_idx = len(lod.facenormals) - 1

    face = Face(lod.points, lod.facenormals)
    face.flags = 0
    face.texture = ""                           # a proxy face has no texture or material
    face.material = ""
    for pobj in pts:
        v = Vertex(lod.points, lod.facenormals)
        v.point_index = lod.points.index(pobj)
        v.normal_index = norm_idx
        v.uv = (0.0, 0.0)
        face.vertices.append(v)
    lod.faces.append(face)

    sel = Selection(lod.points, lod.faces)
    for pobj in pts:
        sel.points[pobj] = 1
    sel.faces[face] = 1
    lod.selections[proxy_sel_name] = sel
```

The frame comes from the triangle's angles, not its vertex order, and a triangle with two equal legs (0.001 along +Y and along +Z, say) is ambiguous: the attached model can come out turned (`proxy-frames.md`, "Ambiguous triangles"). The legs above are unequal for that reason. `LOD.get_proxies` reads this triangle as unambiguous, with the same anchor and the same identity raw frame as the one `add_proxy` writes.

## A minimal proxy model

The engine needs a real `.p3d` at the proxy path. One tiny triangle and a Memory LOD with `ce_center` are enough:

```python
from py3d import P3D, LOD, Point, Face, Vertex, Selection

proxy = P3D()

lod = LOD(); lod.resolution = 0.0
p0 = Point(); p0.coords = (0.0, 0.0, 0.0)
p1 = Point(); p1.coords = (0.01, 0.0, 0.0)
p2 = Point(); p2.coords = (0.0, 0.01, 0.0)
lod.points.extend([p0, p1, p2])
lod.facenormals.append((0.0, 0.0, 1.0))
face = Face(lod.points, lod.facenormals)
face.texture = ""; face.material = ""
for i in range(3):
    v = Vertex(lod.points, lod.facenormals)
    v.point_index = i; v.normal_index = 0; v.uv = (0.0, 0.0)
    face.vertices.append(v)
lod.faces.append(face)
sel = Selection(lod.points, lod.faces)
for p in (p0, p1, p2):
    sel.points[p] = 1
sel.faces[face] = 1
lod.selections["zbytek"] = sel
proxy.lods.append(lod)

mem = LOD(); mem.resolution = 1.0e15
ce = Point(); ce.coords = (0.0, 0.0, 0.0)
mem.points.append(ce)
ce_sel = Selection(mem.points, mem.faces)
ce_sel.points[ce] = 1
mem.selections["ce_center"] = ce_sel
proxy.lods.append(mem)

with open("MySlot.p3d", "wb") as f:
    proxy.write(f)
```

`check_proxy_system` in `py3d-part-checks.md` checks the names and the triangles once the model is written.
