# End-to-end: the model tools on a synthetic MLOD

This walkthrough chains three tools on a **synthetic** one-triangle
`.p3d`. There is no DayZ asset and no private mod file. Commands assume
the Agentic-Z repository root is the current directory and that the three
packages are on `PYTHONPATH`:

```text
set PYTHONPATH=scripts\tools\py3d;scripts\tools\dayz-model-preflight;scripts\tools\dayz-3d-viewer
```

Or, on one line, run the script that performs steps 1–3 and fails if
any check does not match:

```text
python scripts/dev/knowledge-pack/examples/end-to-end/run.py
```

Expected script output:

```text
1. wrote target.p3d (346 bytes)
2. preflight PASS
3. viewer wrote synthetic.glb + synthetic_viewer.html
OK
```

`run.py` writes under `work/` next to itself (gitignored). The
manual commands below do the same work in a directory you choose.

## 1. `py3d` writes a minimal MLOD

Create a visual LOD (resolution 0) with one triangle, a named
selection `Component01`, and a Memory LOD with `actionPos`:

```python
import py3d

visual = py3d.LOD()
visual.resolution = 0.0
for coords in ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 4.0, 6.0)):
    point = py3d.Point()
    point.coords = coords
    visual.points.append(point)
visual.facenormals.append((0.0, 0.0, 1.0))
face = py3d.Face(visual.points, visual.facenormals)
for index in (0, 1, 2):
    vertex = py3d.Vertex(visual.points, visual.facenormals)
    vertex.point_index = index
    vertex.normal_index = 0
    face.vertices.append(vertex)
visual.faces.append(face)
selection = visual.new_selection("Component01")
selection.points = {point: 1 for point in visual.points}
selection.faces = {face: 1}

memory = py3d.LOD()
memory.resolution = 1.0e15
memory.set_memory_point("actionPos", (0.0, 0.5, 0.0))

model = py3d.P3D()
model.lods.extend([visual, memory])
model.save("target.p3d")
```

Copy `target.p3d` to `source.p3d` so the preflight contract can name a
source model. Expected: a 346-byte MLOD, two LODs, one face.

```text
python -m dayz_3d_viewer p3d-to-glb target.p3d --info
```

Expected (keys sorted):

```json
{
  "file": "target.p3d",
  "lods": [
    {
      "faces": 1,
      "materials": [],
      "points": 3,
      "resolution": 0.0,
      "selections": ["Component01"],
      "textures": [],
      "type": "visual_0"
    },
    {
      "faces": 0,
      "materials": [],
      "points": 1,
      "resolution": 999999986991104.0,
      "selections": ["actionPos"],
      "textures": [],
      "type": "memory"
    }
  ],
  "num_lods": 2
}
```

The Memory LOD resolution prints as `1e15` in float64. That is the
same constant `py3d` writes.

## 2. `dayz-model-preflight` gates the file

`preflight.json` (next to `source.p3d`):

```json
{
  "schema_version": "dayz-model-preflight-v1",
  "scale": {
    "lod_index": 0,
    "expected_dimensions_m": [2.0, 4.0, 6.0],
    "tolerance_m": [0.01, 0.01, 0.01]
  },
  "bones": {
    "requirements": [
      {"lod_index": 0, "selections": ["Component01"]}
    ]
  },
  "winding": {
    "source_model": "source.p3d",
    "transform": [
      [1.0, 0.0, 0.0, 0.0],
      [0.0, 1.0, 0.0, 0.0],
      [0.0, 0.0, 1.0, 0.0],
      [0.0, 0.0, 0.0, 1.0]
    ],
    "position_tolerance_m": 1e-5,
    "faces": [
      {
        "source": {"lod_index": 0, "face_index": 0},
        "target": {"lod_index": 0, "face_index": 0}
      }
    ]
  }
}
```

```text
python -m dayz_model_preflight check target.p3d --contract preflight.json
```

Expected: exit 0, `"verdict":"PASS"`. `py3d.validate()` also emits
`WARN_MEMORY_POS_CENTER` on the Memory LOD (no `pos center` point).
That is a warning, not a failure; the contract itself is satisfied.

## 3. `dayz-3d-viewer` writes glb + HTML

```text
python -m dayz_3d_viewer build-viewer target.p3d --output out --name synthetic --mode embedded
```

Expected: exit 0, `out/synthetic.glb` and `out/synthetic_viewer.html`.
The glTF POSITION accessor has count 3; the index accessor has count 3
(one triangle). The HTML contains the baked `const M=` payload and the
jsDelivr URL for three.js 0.160.0. It must not contain a host path.

## 4. The other three tools do not fit this asset

| Tool | Why it is not in this chain |
|---|---|
| `dayz-odol-strict` | Inspects **binarized ODOL** v53–v55. This file is MLOD. There is no ODOL writer in this repository, so the synthetic model cannot be the input. |
| `dayz-animation-formats` | Reads and writes **RTM / SEAnim**. The triangle has no skeleton track. |
| `dayz-ui-lab` | Parses **`.layout`** widgets. This example has no UI. |

Use those tools when the asset is an ODOL, an animation, or a layout.
Do not invent an input just to tick the row.

## 5. Verify in-game (not run here)

There is no DayZ process in this walkthrough. The in-game check is
owned by `skills/dayz-mcp-verify` and the DayZ MCP bridge that
`docs/dayz-mcp.md` describes. After a real class exists, that skill is
the one that spawns it, orbits, and captures evidence.
Do not start DayZDiag from this example.
