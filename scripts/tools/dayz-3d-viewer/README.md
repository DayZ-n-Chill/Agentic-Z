# dayz-3d-viewer

Convert DayZ MLOD `.p3d` models, `.paa` textures and `.rvmat` materials
into a binary glTF (`.glb`) and a standalone Three.js HTML viewer.

The converter is the pack form of the `dayz-3d-viewer` skill. It reads
the DayZ py3d fork from `tools/py3d` (1.6.0 or later). It does not vendor a
wheel and it does not talk to the game.

## Requirements and install

```powershell
python -m pip install -e tools/py3d
python -m pip install -e tools/dayz-3d-viewer
```

PAA decoding needs Pillow. LZO-compressed DXT mipmaps (common on
256 px and larger Arma 2+ textures) need either `python-lzo` or
`lzokay` plus the shim below.

```powershell
python -m pip install -e "tools/dayz-3d-viewer[all]"
```

The imported `py3d` module must expose `IS_DAYZ_FORK is True` and a
semantic version of at least `1.6.0`. The unrelated PyPI package named
`py3d` is not compatible.

### LZO shim

`python-lzo` has no Windows Python 3.14 wheels. The tool therefore
treats LZO as an optional extra and ships `install-lzo-shim` as a
one-time environment helper, not as a conversion step:

```powershell
python -m pip install lzokay
python -m dayz_3d_viewer install-lzo-shim
```

That writes an `lzo.py` into user site-packages so `import lzo` calls
`lzokay`. Skip it if you do not decode LZO-compressed PAA files.

## Command line

```powershell
python -m dayz_3d_viewer p3d-to-glb model.p3d model.glb
python -m dayz_3d_viewer p3d-to-glb model.p3d --info
python -m dayz_3d_viewer paa-to-png base_co.paa base_co.png
python -m dayz_3d_viewer parse-rvmat housing.rvmat
python -m dayz_3d_viewer build-viewer model.p3d --textures ./tex --rvmats ./mat --name "My Model" --mode embedded -v
```

`build-viewer` writes `<name>.glb` and `<name>_viewer.html` into
`--output` (default: `./output` next to the `.p3d`). `--mode web`
points the HTML at the sibling `.glb` via `GLTFLoader`. `--mode
embedded` bakes typed arrays and base64 PNGs into the HTML so a
sandboxed iframe can render without `fetch`.

| Exit | Meaning |
|---:|---|
| `0` | Conversion or parse completed |
| `1` | The input was readable but conversion failed |
| `2` | Usage error or a declared extra is missing |

Missing Pillow or LZO is reported as a one-line message on stderr, not
as a traceback.

## Library API

Public names match the original skill scripts:

```python
from dayz_3d_viewer import (
    convert_paa_to_png,
    parse_rvmat,
    extract_geometry_for_viewer,
    generate_viewer_html,
    p3d_to_glb,
    run_pipeline,
)
```

## three.js (CDN, not bundled)

Generated HTML loads **three.js 0.160.0** and its `OrbitControls` /
`GLTFLoader` addons from jsDelivr:

`https://cdn.jsdelivr.net/npm/three@0.160.0/`

The tool does not embed three.js source. Opening the HTML without a
network will show a blank page. The classify viewer under
`skills/rip-vehicle-import` does the same for r128; see
`THIRD_PARTY_NOTICES.md`.

## Determinism

The same input produces the same `.glb` and `.html` bytes. Geometry is
packed little-endian; JSON uses sorted keys; neither artefact carries a
timestamp or a host path.

## What this tool does not do

- It does not encode PNG → PAA.
- It does not apply the PAA `SWIZ` tag to normal maps.
- It does not hide proxy triangles; they export as visible geometry.
- It classifies resolution 1100 (ViewPilot) as `shadow`, not as a
  view-pilot LOD. `find_best_visual_lod` will not pick it as the visual
  mesh. See `KNOWN-ISSUES.md`.
- ODOL (binarized) `.p3d` is out of scope. Debinarize first.

## Test

```powershell
python -m pytest -q tools/dayz-3d-viewer/tests
```
