# The 3D viewer tool: .p3d to .glb and an HTML page

Converts a mod's model, textures and materials into something a browser can show: a binary glTF file and an HTML page with orbit controls. The converter is the Python tool in `scripts/tools/dayz-3d-viewer`; this file is how to use it. Its test model is a push button with 328 vertices, 640 faces, 4 materials and DXT1 textures with LZO mipmaps.

Follow `skills/_shared/dayz-conventions.md`. The tool reads only the files you pass, so nothing here gates on `/dayz-preflight`. To convert a vanilla texture, pass its `P:\` path like any other file.

## Install

Run from the repository root:

```cmd
python -m pip install -e scripts/tools/py3d
python -m pip install -e "scripts/tools/dayz-3d-viewer[all]"
python -c "import py3d; assert getattr(py3d,'IS_DAYZ_FORK',False) and tuple(map(int,py3d.__version__.split('.')))>=(1,6,0), (py3d.__version__, py3d.__file__)"
```

- py3d is the DayZ fork in `scripts/tools/py3d`, 1.6.0 or later. Do not run `pip install py3d`: the PyPI package of that name is a point cloud library, and the tool refuses any py3d without `IS_DAYZ_FORK`. Uninstall another py3d first (`python -m pip uninstall py3d`), since it uses the same import name.
- `[all]` adds Pillow, which decodes PAA, and `lzokay`. Geometry-only conversion needs neither.
- Large PAA mipmaps are LZO compressed. `python-lzo` has no Windows wheel for Python 3.14, so the supported route is `lzokay` plus a shim, written once:

  ```cmd
  python -m dayz_3d_viewer install-lzo-shim
  ```

  It writes an `lzo.py` into the user site-packages so that `import lzo` calls `lzokay`. Skip it when no LZO compressed PAA has to be decoded. Without it, `paa-to-png` and `p3d-to-glb` stop on such a file with a one line message and exit code 2; `build-viewer` keeps going, lists the failed texture under `errors` and exits 1.

## Commands

All through `python -m dayz_3d_viewer`:

| Command | Module in the tool | What it does |
|---|---|---|
| `build-viewer` | `pipeline.py`, `viewer_template.py` | The whole pipeline: `.glb` plus the HTML page, in embedded or web mode. |
| `p3d-to-glb` | `p3d_to_gltf.py` | MLOD `.p3d` to `.glb` (geometry, textures, materials). `--info` prints the LODs, selections, textures and materials as JSON and converts nothing. |
| `paa-to-png` | `paa_to_png.py` | One `.paa` to `.png` (DXT1, DXT3, DXT5, RGBA and luminance-alpha types, with LZO or LZSS). |
| `parse-rvmat` | `rvmat_parser.py` | One or more `.rvmat` files to JSON: colors, specular, emissive, stage textures. |
| `install-lzo-shim` | `install_lzo_shim.py` | The LZO shim above. |

```cmd
python -m dayz_3d_viewer build-viewer model.p3d --textures tex --rvmats mat --name "My Model" --mode embedded -v
python -m dayz_3d_viewer p3d-to-glb model.p3d model.glb
python -m dayz_3d_viewer p3d-to-glb model.p3d --info
python -m dayz_3d_viewer paa-to-png base_co.paa base_co.png
python -m dayz_3d_viewer parse-rvmat housing.rvmat
```

`build-viewer` reads the model, collects the texture and material paths it names, looks for them in the folders given with `--textures` and `--rvmats`, converts the PAA files, parses the materials and writes `<name>.glb` and `<name>_viewer.html` into `--output` (default: an `output` folder next to the `.p3d`). It also makes a `textures` folder there for the converted PNG files, and prints a JSON summary with the paths and an `errors` list. `--no-viewer` stops after the `.glb`.

For a model inside `workspace\<ModName>\`, always pass `--output`, for example `--output output\<ModName>-viewer`: the default would put the viewer files inside the mod folder, where the next build packs them.

| Exit | Meaning |
|---|---|
| `0` | The conversion or parse finished. |
| `1` | The input is missing or is not an MLOD `.p3d` (a binarized ODOL model), or the conversion failed (`build-viewer`: the `errors` list is not empty). |
| `2` | Usage error, or an optional package is missing (Pillow, LZO) for `paa-to-png` or `p3d-to-glb`. The message is one line on stderr, not a traceback. `build-viewer` does not stop on a missing package: it lists each failed step under `errors` and exits 1. |

The same input gives the same `.glb` and `.html` bytes: neither file carries a timestamp or a path of the machine.

## Two viewer modes

Embedded mode (`--mode embedded`, the default) is for a chat artifact or any sandboxed frame. Geometry is baked into the HTML as typed arrays and textures as base64 PNG, because such a frame blocks `fetch()`, `XMLHttpRequest` and blob URLs. One file, nothing to load beside it.

Web mode (`--mode web`) is for a page that will be hosted. The HTML loads the separate `.glb` with `GLTFLoader`, so the two files stay apart and can be cached.

Both load Three.js 0.185.1 from the jsDelivr CDN as ES modules through an importmap. Three.js is not embedded, so a page needs a network to render. Before pinning another version or another way of loading it, read `tools-threejs-viewers.md`.

## From Python

When the user hands over `.p3d`, `.paa` and `.rvmat` files in a chat, the library calls give more control than the command line:

```python
import os
from dayz_3d_viewer import convert_paa_to_png, parse_rvmat
from dayz_3d_viewer import extract_geometry_for_viewer, generate_viewer_html

# 1. PAA textures to PNG
convert_paa_to_png('base_co.paa', 'base_co.png', verbose=True)

# 2. RVMAT files
rvmat_data = {}
for f in ['housing.rvmat', 'button.rvmat', 'led_off.rvmat']:
    rvmat_data[os.path.splitext(f)[0]] = parse_rvmat(f)

# 3. Geometry with materials and textures baked in
texture_map = {'base_co': 'base_co.png'}  # texture stem to png path
geo = extract_geometry_for_viewer('model.p3d', texture_map=texture_map, rvmat_data=rvmat_data)

# 4. The embedded page
generate_viewer_html(model_name='Push Button', mode='embedded', geometry_data=geo, output_path='viewer.html')

# or the web page, next to a .glb written by p3d_to_glb
generate_viewer_html(model_name='My Model', mode='web', glb_url='model.glb', output_path='viewer.html')
```

The public names are `convert_paa_to_png`, `parse_rvmat`, `extract_geometry_for_viewer`, `generate_viewer_html`, `p3d_to_glb` and `run_pipeline`.

## What the page offers

The embedded page (`mode='embedded'`) offers:

- Orbit controls: left button rotates, right button pans, wheel zooms; a camera reset.
- Toggles for a wireframe overlay, the grid and auto rotation; five background colors to cycle through.
- A panel with the vertex, triangle and material counts.
- ACES filmic tone mapping and four lights (key, fill, rim, ambient).
- Materials built from the RVMAT values: metalness and roughness from the specular keys, emissive materials for LEDs. It resizes with the window.

The web page (`mode='web'`) has the same orbit controls, camera reset, count panel and tone mapping, with these differences:

- No wireframe toggle; only the grid and auto rotation toggles.
- Four background colors to cycle through instead of five.
- Two lights (ambient and key) instead of four.
- Materials come from the `.glb` file as `p3d_to_glb` wrote them, not from RVMAT values in the page.

## Limits

- MLOD only. A binarized (ODOL) model, which every vanilla `.p3d` is, has to go through an external ODOL to MLOD converter first. Agentic-Z ships none.
- Colour texture only. Normal and specular maps are parsed from the RVMAT but not applied in the page.
- One LOD. The page shows the best visual LOD; there is no LOD switcher.
- Proxy triangles show as geometry, and a pilot view LOD (resolution 1100) is never chosen as the mesh.
- No PNG to PAA. Use `/dayz-pack-texture` for that direction.
- No states or animations yet. What the data for them is lies in `tools-3d-viewer-states.md`, and the plan for sliders and LED toggles in `tools-3d-viewer-states-build.md`.

## References

| Question | Open |
|---|---|
| Which PAA types decode, how is a PAA laid out, and why does an LZO texture fail? | `tools-3d-viewer-formats.md` |
| How does an RVMAT become a Three.js material, and what does `parse-rvmat` report? | `tools-3d-viewer-formats.md` |
| A flat colored model bakes with black holes and smudges. What to do instead? | `tools-3d-viewer-formats.md`, "Materials for flat colored models" |
| Which Three.js version and loading method can a generated page use, and why does it fail from `file://` or in a chat frame? | `tools-threejs-viewers.md` |
| How to build a page for placing crew proxies and memory points offline, and what makes such a page lose the user's work? | `tools-threejs-viewers.md`, "The fit editor pattern" and "Two defects that lose the user's placement" |
| How to test a generated page without downloading a headless browser? | `tools-threejs-viewers.md` |
| Where a model's moving parts and material states come from, and the maths of each animation | `tools-3d-viewer-states.md` |
| How the viewer would play `model.cfg` animations and swap LED materials (planned, not built) | `tools-3d-viewer-states-build.md` |
| What is wrong with the converter today? | `scripts/tools/dayz-3d-viewer/KNOWN-ISSUES.md` |
| The tool's own install notes and tests. | `scripts/tools/dayz-3d-viewer/README.md` |
