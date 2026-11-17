# dayz-layout-viewer

Parse a DayZ `.layout` and emit one self-contained `*.preview.html` with
**four viewports** (1080p 16:9, 1440p 16:9, ultrawide 21:9, 720p 16:9) plus
parser diagnostics. In it exact widgets keep their declared px at every
viewport while proportional widgets scale. The engine draws exact units as
1/1080 of the screen height (`dayz-ui-development` Rule 3, measured in game),
so off 1080p that difference is this model's, not the game's: the parser lays
exact units out as pixels (`tools/dayz-ui-lab/dayz_ui_lab/parse.py:772-775`). *(Corrected
2026-10-03: this called it the usual "looked right in the mockup, wrong
in-game" failure.)*

Geometry, attributes and diagnostics come from the pack format parser
`tools/dayz-ui-lab/dayz_ui_lab/parse.py` (`LayoutDoc`). This tool is **not**
`dayz-ui-lab/render.py`, which emits semantic scenario JSON, not an HTML
preview.

## What this is not

The HTML is a **structural approximation**. It is not the Enfusion widget
rasterizer. DayZDiag remains the golden reference for pixels, colour, fonts
and the live widget tree.

It does **not**:

- rasterize Metron / SDF bitmap font atlases (system fonts stand in);
- decode `.paa` / `.edds` (those textures render as a hatch, unless the
  attribute is a procedural `#(argb,…)color(…)`);
- apply script-side `SetColor` / `SetPos` / `SetText`;
- re-flow `GridSpacer` / `WrapSpacer` / `Scroll` children (authored
  `position`/`size` are shown; the engine overwrites those in-game);
- resolve `.styles` or imagesets;
- instantiate child layouts that script mounts at runtime;
- claim `right_ref` / `center_ref` / `bottom_ref` offset signs (those
  anchors are badged `assumed`).

Unknown in-string escapes (`gui\layouts\…`) fail closed in the pack parser;
this viewer does not recover them.

## Requirements and install

Stdlib only. It imports the sibling `tools/dayz-ui-lab` parser; run it from
the pack tree (or put that directory on `PYTHONPATH`). `dayz-ui-lab` is not
a pip extra of this tool and is not modified by it.

From the repository root, either use the script path (no install):

```powershell
python tools/dayz-layout-viewer/build_viewer.py gui/layouts/menu.layout
python tools/dayz-layout-viewer/build_viewer.py menu.layout -o menu.preview.html
python tools/dayz-layout-viewer/build_viewer.py menu.layout --layout-root gui/layouts
```

or install and invoke the module:

```powershell
python -m pip install -e tools/dayz-layout-viewer
python -m dayz_layout_viewer gui/layouts/menu.layout -o menu.preview.html
```

`--layout-root` only resolves the input path. It does not compose child
layouts.

Default output is `<input>.preview.html` next to the layout. The HTML needs
no server and no CDN.

| Exit | Meaning |
|---:|---|
| `0` | HTML written |
| `1` | The file was found but the pack parser rejected it |
| `2` | Usage error or the layout path was not found |

## Library API

```python
from dayz_layout_viewer import VIEWPORTS, build_preview_html, write_preview

html = build_preview_html(path)
write_preview(path, out_path)
```

`source.path` inside the embedded JSON is the layout **filename**, not a
host path.

## `visible 0`

The predecessor HTML emitter coerced `visible 0` to shown (`int(attr or 1)`
in Python: `0 or 1` is `1`). This viewer embeds the pack parser's
`geometry.visible` (boolean; `0` is `false`) and the page CSS hides
`.hidden-w` unless "show hidden" is checked. A unit test fails if that
contract regresses.

## Test

From this directory:

```powershell
python -m pytest -q tests
```
